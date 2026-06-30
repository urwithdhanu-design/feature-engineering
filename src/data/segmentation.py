"""K-Means customer segmentation before model training."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.features.engineer import FEATURE_COLUMNS

SEGMENT_COLUMN = "customer_segment"

# Semantic names when n_clusters=3 (assigned by risk score after fitting)
THREE_CLUSTER_NAMES = ["reliable", "at_risk", "high_risk"]

SEGMENT_LABELS: dict[str, str] = {
    "reliable": "Low risk — consistent on-time payments, no arrears",
    "at_risk": "Medium risk — some missed or late payments, may have arrears",
    "high_risk": "High risk — frequent missed payments and arrears",
}

SEGMENT_NOTE = (
    "Behavioural K-Means segment from payment patterns. "
    "Not the same as age-based personas (Ethan/Jordan/Sarah)."
)


class CustomerSegmenter:
    """Fit K-Means on behavioural features and assign segment IDs."""

    def __init__(self, n_clusters: int = 3, random_state: int = 42) -> None:
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.kmeans: KMeans | None = None
        self.feature_columns = list(FEATURE_COLUMNS)
        self.segment_profiles: dict[int, dict[str, Any]] = {}
        self.cluster_id_to_name: dict[int, str] = {}

    def fit(self, features: pd.DataFrame) -> "CustomerSegmenter":
        X = features[self.feature_columns].fillna(0.0).values
        scaled = self.scaler.fit_transform(X)
        self.kmeans = KMeans(
            n_clusters=self.n_clusters,
            random_state=self.random_state,
            n_init=10,
        )
        labels = self.kmeans.fit_predict(scaled)
        self.segment_profiles = self._build_profiles(features, labels)
        self.cluster_id_to_name = self._assign_semantic_names(self.segment_profiles)
        for cid, profile in self.segment_profiles.items():
            name = self.cluster_id_to_name[cid]
            profile["cluster_id"] = cid
            profile["segment_name"] = name
            profile["segment_label"] = self.label_for_name(name)
        return self

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        if self.kmeans is None:
            raise RuntimeError("Segmenter not fitted. Call fit() first.")
        X = features[self.feature_columns].fillna(0.0).values
        scaled = self.scaler.transform(X)
        return self.kmeans.predict(scaled)

    def assign_segment_column(self, features: pd.DataFrame) -> pd.DataFrame:
        """Return features DataFrame with customer_segment column added."""
        out = features.copy()
        out[SEGMENT_COLUMN] = self.predict(features)
        return out

    def segment_info(self, cluster_id: int) -> dict[str, Any]:
        """UI-friendly segment metadata for a cluster id."""
        name = self.cluster_id_to_name.get(cluster_id, f"segment_{cluster_id}")
        profile = self.segment_profiles.get(cluster_id, {})
        return {
            "id": int(cluster_id),
            "name": name,
            "label": self.label_for_name(name),
            "n_clusters": self.n_clusters,
            "note": SEGMENT_NOTE,
            "profile": {
                "avg_missing_payments": profile.get("avg_missing_payments"),
                "avg_on_time_payments": profile.get("avg_on_time_payments"),
                "pct_has_arrears": profile.get("pct_has_arrears"),
            },
        }

    def label_for_name(self, name: str) -> str:
        if name in SEGMENT_LABELS:
            return SEGMENT_LABELS[name]
        return f"Customer segment '{name}' (cluster of {self.n_clusters})"

    def _risk_score(self, profile: dict[str, Any]) -> float:
        return (
            float(profile.get("avg_missing_payments", 0))
            + float(profile.get("pct_has_arrears", 0))
            - float(profile.get("avg_on_time_payments", 0)) * 0.25
        )

    def _assign_semantic_names(self, profiles: dict[int, dict[str, Any]]) -> dict[int, str]:
        """Map K-Means cluster ids to semantic names ordered by payment risk."""
        if not profiles:
            return {}
        ranked = sorted(profiles.keys(), key=lambda cid: self._risk_score(profiles[cid]))
        if self.n_clusters == 3 and len(ranked) == 3:
            names = THREE_CLUSTER_NAMES
        else:
            names = [f"segment_{i}" for i in range(len(ranked))]
        return {cid: names[i] for i, cid in enumerate(ranked)}

    def _build_profiles(self, features: pd.DataFrame, labels: np.ndarray) -> dict[int, dict[str, Any]]:
        profiles: dict[int, dict[str, Any]] = {}
        df = features.copy()
        df["_label"] = labels
        for cluster_id in range(self.n_clusters):
            subset = df[df["_label"] == cluster_id]
            if len(subset) == 0:
                continue
            profiles[int(cluster_id)] = {
                "count": int(len(subset)),
                "avg_utilization": round(float(subset["utilization"].mean()), 4),
                "avg_missing_payments": round(float(subset["missing_payments_last_6_cycles"].mean()), 4),
                "avg_on_time_payments": round(float(subset["on_time_payments_last_6_cycles"].mean()), 4),
                "avg_age": round(float(subset["age"].mean()), 1),
                "age_min": int(subset["age"].min()),
                "age_max": int(subset["age"].max()),
                "pct_direct_debit": round(float(subset["direct_debit_active_indicator"].mean()), 4),
                "pct_has_arrears": round(float(subset["has_arrears"].mean()), 4),
            }
        return profiles

    def save_profiles(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        export = {
            "n_clusters": self.n_clusters,
            "note": SEGMENT_NOTE,
            "segments": {
                str(cid): profile for cid, profile in self.segment_profiles.items()
            },
        }
        path.write_text(json.dumps(export, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def load_profiles(cls, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
