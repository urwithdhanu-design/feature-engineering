"""ML model training for nudge, tone, and payment risk prediction."""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from src.data.pipeline import model_feature_columns, prepare_training_pipeline
from src.data.segmentation import SEGMENT_COLUMN, SEGMENT_NOTE, CustomerSegmenter
from src.features.engineer import FEATURE_COLUMNS, accounts_to_dataframe, enrich_account
from src.data.cleaning import clean_account_for_inference

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = ROOT / "data" / "scenarios"
TRAINING_DIR = ROOT / "data" / "training"
MODELS_DIR = ROOT / "models"
PERSONAS_DIR = ROOT / "data" / "personas"
DEFAULT_SYNTHETIC_DATASET = TRAINING_DIR / "synthetic_5000_2mo.jsonl"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    accounts: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                accounts.append(json.loads(line))
    return accounts


def load_all_scenarios() -> list[dict[str, Any]]:
    """Load all persona scenario JSON files."""
    accounts: list[dict[str, Any]] = []
    for persona_dir in sorted(SCENARIOS_DIR.iterdir()):
        if not persona_dir.is_dir():
            continue
        for path in sorted(persona_dir.glob("*.json")):
            accounts.append(json.loads(path.read_text(encoding="utf-8")))
    return accounts


def load_training_data(dataset_path: Path | None = None) -> tuple[list[dict[str, Any]], str]:
    """Load training accounts; prefers large synthetic dataset when present."""
    path = dataset_path or DEFAULT_SYNTHETIC_DATASET
    if path.exists():
        return load_jsonl(path), str(path)
    return load_all_scenarios(), "data/scenarios (177 persona matrix files)"


def load_personas() -> dict[str, dict]:
    personas = {}
    for path in PERSONAS_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        personas[data["persona_id"]] = data
    return personas


class ModelBundle:
    """Trained nudge, tone, and risk models with K-Means segmenter."""

    def __init__(self) -> None:
        self.nudge_model: GradientBoostingClassifier | None = None
        self.tone_model: GradientBoostingClassifier | None = None
        self.risk_models: dict[str, GradientBoostingRegressor] = {}
        self.nudge_encoder = LabelEncoder()
        self.tone_encoder = LabelEncoder()
        self.segmenter: CustomerSegmenter | None = None
        self.feature_columns = model_feature_columns()
        self.n_clusters: int = 3

    def build_features(self, accounts: list[dict[str, Any]]) -> pd.DataFrame:
        """Clean, enrich, and attach K-Means segment for inference."""
        cleaned = [clean_account_for_inference(a) for a in accounts]
        enriched = [enrich_account(a) for a in cleaned]
        base = accounts_to_dataframe(enriched)[FEATURE_COLUMNS]
        if self.segmenter is None:
            base[SEGMENT_COLUMN] = 0
            return base[self.feature_columns]
        return self.segmenter.assign_segment_column(base)[self.feature_columns]

    def train(
        self,
        accounts: list[dict[str, Any]] | None = None,
        dataset_path: Path | None = None,
        n_clusters: int = 3,
    ) -> dict[str, Any]:
        data_source = "custom"
        if accounts is None:
            accounts, data_source = load_training_data(dataset_path)

        personas = load_personas()
        X, y_nudge, y_tone, y_risk, cleaning_report, segmenter = prepare_training_pipeline(
            accounts, personas, n_clusters=n_clusters
        )
        self.segmenter = segmenter
        self.n_clusters = n_clusters
        self.feature_columns = model_feature_columns()

        X_train, X_test, yn_train, yn_test, yt_train, yt_test, yr_train, yr_test = (
            train_test_split(X, y_nudge, y_tone, y_risk, test_size=0.2, random_state=42)
        )

        self.nudge_encoder.fit(y_nudge)
        self.tone_encoder.fit(y_tone)

        self.nudge_model = GradientBoostingClassifier(
            n_estimators=100, max_depth=4, random_state=42
        )
        self.nudge_model.fit(X_train, self.nudge_encoder.transform(yn_train))

        self.tone_model = GradientBoostingClassifier(
            n_estimators=100, max_depth=3, random_state=42
        )
        self.tone_model.fit(X_train, self.tone_encoder.transform(yt_train))

        risk_targets = ["risk_missed_payment", "risk_late_payment", "risk_minimum_only_payment"]
        risk_metrics: dict[str, float] = {}
        for target in risk_targets:
            model = GradientBoostingRegressor(n_estimators=80, max_depth=3, random_state=42)
            model.fit(X_train, yr_train[target])
            self.risk_models[target] = model
            preds = model.predict(X_test)
            mae = float(np.mean(np.abs(preds - yr_test[target].values)))
            risk_metrics[f"{target}_mae"] = round(mae, 4)

        nudge_acc = float(
            (self.nudge_model.predict(X_test) == self.nudge_encoder.transform(yn_test)).mean()
        )
        tone_acc = float(
            (self.tone_model.predict(X_test) == self.tone_encoder.transform(yt_test)).mean()
        )

        segment_profiles_path = MODELS_DIR / "segment_profiles.json"
        segmenter.save_profiles(segment_profiles_path)

        return {
            "training_samples": len(accounts),
            "samples_after_cleaning": cleaning_report.output_count,
            "train_split_size": len(X_train),
            "test_split_size": len(X_test),
            "data_source": data_source,
            "n_clusters": n_clusters,
            "cleaning": cleaning_report.to_dict(),
            "segment_profiles_path": str(segment_profiles_path),
            "nudge_accuracy": round(nudge_acc, 4),
            "tone_accuracy": round(tone_acc, 4),
            **risk_metrics,
        }

    def save(self, path: Path | None = None) -> Path:
        path = path or MODELS_DIR / "model_bundle.pkl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(self, f)
        return path

    @classmethod
    def load(cls, path: Path | None = None) -> "ModelBundle":
        path = path or MODELS_DIR / "model_bundle.pkl"
        with path.open("rb") as f:
            bundle = pickle.load(f)
        if not hasattr(bundle, "segmenter"):
            bundle.segmenter = None
        if not hasattr(bundle, "feature_columns"):
            bundle.feature_columns = model_feature_columns()
        return bundle

    def predict_nudge(self, features: pd.DataFrame) -> str:
        assert self.nudge_model is not None
        pred = self.nudge_model.predict(features[self.feature_columns])
        return self.nudge_encoder.inverse_transform(pred)[0]

    def predict_tone(self, features: pd.DataFrame) -> str:
        assert self.tone_model is not None
        pred = self.tone_model.predict(features[self.feature_columns])
        return self.tone_encoder.inverse_transform(pred)[0]

    def predict_risk(self, features: pd.DataFrame) -> dict[str, float]:
        result = {}
        for target, model in self.risk_models.items():
            result[target] = round(float(model.predict(features[self.feature_columns])[0]), 4)
        return result

    def predict_segment(self, features: pd.DataFrame) -> int:
        if self.segmenter is None:
            return 0
        return int(self.segmenter.predict(features[FEATURE_COLUMNS])[0])

    def predict_segment_detail(self, features: pd.DataFrame) -> dict[str, Any]:
        cluster_id = self.predict_segment(features)
        if self.segmenter is None:
            return {
                "id": cluster_id,
                "name": "unknown",
                "label": "Segmenter not loaded",
                "n_clusters": self.n_clusters,
                "note": SEGMENT_NOTE,
            }
        return self.segmenter.segment_info(cluster_id)


def train_and_save(
    dataset_path: Path | None = None,
    n_clusters: int = 3,
) -> dict[str, Any]:
    bundle = ModelBundle()
    metrics = bundle.train(dataset_path=dataset_path, n_clusters=n_clusters)
    model_path = bundle.save()
    metrics["model_path"] = str(model_path)
    metrics_path = MODELS_DIR / "training_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics
