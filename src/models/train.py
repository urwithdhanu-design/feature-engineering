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

from src.features.engineer import (
    FEATURE_COLUMNS,
    accounts_to_dataframe,
    enrich_account,
)
from src.rules.nudge_rules import derive_nudge_type, derive_tone, derive_risk_labels

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


def prepare_training_data(
    accounts: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.DataFrame]:
    """Build features and labels from scenario accounts."""
    personas = load_personas()
    enriched = [enrich_account(a) for a in accounts]

    X = accounts_to_dataframe(enriched)[FEATURE_COLUMNS]

    nudge_labels = [derive_nudge_type(a) for a in enriched]
    tone_labels = [
        derive_tone(a, personas.get(a.get("persona_id", ""), {}))
        for a in enriched
    ]

    risk_rows = [derive_risk_labels(a) for a in enriched]
    y_risk = pd.DataFrame(risk_rows)

    return X, pd.Series(nudge_labels), pd.Series(tone_labels), y_risk


class ModelBundle:
    """Trained nudge, tone, and risk models."""

    def __init__(self) -> None:
        self.nudge_model: GradientBoostingClassifier | None = None
        self.tone_model: GradientBoostingClassifier | None = None
        self.risk_models: dict[str, GradientBoostingRegressor] = {}
        self.nudge_encoder = LabelEncoder()
        self.tone_encoder = LabelEncoder()
        self.feature_columns = FEATURE_COLUMNS

    def train(
        self,
        accounts: list[dict[str, Any]] | None = None,
        dataset_path: Path | None = None,
    ) -> dict[str, Any]:
        data_source = "custom"
        if accounts is None:
            accounts, data_source = load_training_data(dataset_path)
        X, y_nudge, y_tone, y_risk = prepare_training_data(accounts)

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

        return {
            "training_samples": len(accounts),
            "train_split_size": len(X_train),
            "test_split_size": len(X_test),
            "data_source": data_source,
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
            return pickle.load(f)

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


def train_and_save(dataset_path: Path | None = None) -> dict[str, Any]:
    bundle = ModelBundle()
    metrics = bundle.train(dataset_path=dataset_path)
    model_path = bundle.save()
    metrics["model_path"] = str(model_path)
    metrics_path = MODELS_DIR / "training_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics
