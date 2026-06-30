"""Training pipeline orchestration: clean → features → segment → train."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.data.cleaning import CleaningReport, clean_accounts
from src.data.segmentation import SEGMENT_COLUMN, CustomerSegmenter
from src.features.engineer import FEATURE_COLUMNS, accounts_to_dataframe, enrich_account
from src.rules.nudge_rules import derive_nudge_type, derive_tone, derive_risk_labels


def model_feature_columns() -> list[str]:
    """Feature columns used by ML models (includes K-Means segment)."""
    return FEATURE_COLUMNS + [SEGMENT_COLUMN]


def prepare_training_pipeline(
    accounts: list[dict[str, Any]],
    personas: dict[str, dict],
    n_clusters: int = 3,
) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.DataFrame, CleaningReport, CustomerSegmenter]:
    """
    Full pre-train pipeline:
    1. Data cleaning
    2. Feature engineering
    3. K-Means segmentation
    4. Label generation
    """
    cleaned, cleaning_report = clean_accounts(accounts)
    enriched = [enrich_account(a) for a in cleaned]

    base_features = accounts_to_dataframe(enriched)[FEATURE_COLUMNS]

    segmenter = CustomerSegmenter(n_clusters=n_clusters)
    segmenter.fit(base_features)
    X = segmenter.assign_segment_column(base_features)

    nudge_labels = pd.Series([derive_nudge_type(a) for a in enriched])
    tone_labels = pd.Series(
        [derive_tone(a, personas.get(a.get("persona_id", ""), {})) for a in enriched]
    )
    y_risk = pd.DataFrame([derive_risk_labels(a) for a in enriched])

    return X, nudge_labels, tone_labels, y_risk, cleaning_report, segmenter
