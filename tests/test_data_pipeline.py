"""Tests for data cleaning and K-Means segmentation."""

import pandas as pd

from src.data.cleaning import clean_account, clean_accounts
from src.data.pipeline import prepare_training_pipeline
from src.data.segmentation import SEGMENT_COLUMN, CustomerSegmenter
from src.features.engineer import FEATURE_COLUMNS, accounts_to_dataframe, enrich_account


def _sample_account(**overrides):
    base = {
        "customerId": "CUST001",
        "payment_history_string": "MM",
        "age": 25,
        "account_credit_limit_amount": 5000.0,
        "current_balance_amount": 1000.0,
        "payment_current_due_amount": 25.0,
        "minimum_payment_schedule_amount": 25.0,
        "direct_debit_active_indicator": 0,
        "months_on_book_counter": 2,
        "account_status_open_indicator": 1,
    }
    base.update(overrides)
    return base


def test_clean_account_fixes_negative_balance():
    acc = clean_account(_sample_account(current_balance_amount=-100.0))
    assert acc is not None
    assert acc["current_balance_amount"] == 0.0


def test_clean_account_drops_invalid_history():
    assert clean_account(_sample_account(payment_history_string="ABC")) is None
    assert clean_account(_sample_account(payment_history_string="")) is None


def test_clean_accounts_deduplicates():
    accounts = [
        _sample_account(customerId="CUST001"),
        _sample_account(customerId="CUST001"),
        _sample_account(customerId="CUST002"),
    ]
    cleaned, report = clean_accounts(accounts)
    assert len(cleaned) == 2
    assert report.duplicates_removed == 1


def test_kmeans_adds_segment_column():
    import random

    rng = random.Random(42)
    accounts = [
        _sample_account(
            customerId=f"CUST{i:03d}",
            payment_history_string=rng.choice(["MM", "ML", "XX", "MX", "NN"]),
            current_balance_amount=rng.uniform(200, 5000),
        )
        for i in range(80)
    ]
    enriched = [enrich_account(a) for a in accounts]
    features = accounts_to_dataframe(enriched)[FEATURE_COLUMNS]
    segmenter = CustomerSegmenter(n_clusters=3)
    segmenter.fit(features)
    out = segmenter.assign_segment_column(features)
    assert SEGMENT_COLUMN in out.columns
    assert len(segmenter.cluster_id_to_name) >= 1
    info = segmenter.segment_info(int(out[SEGMENT_COLUMN].iloc[0]))
    assert info["name"] in ("reliable", "at_risk", "high_risk") or info["name"].startswith("segment_")
    assert "label" in info
    assert info["n_clusters"] == 3


def test_prepare_training_pipeline_runs():
    accounts = [_sample_account(customerId=f"CUST{i:04d}") for i in range(50)]
    X, y_nudge, y_tone, y_risk, report, segmenter = prepare_training_pipeline(
        accounts, personas={}, n_clusters=3
    )
    assert len(X) == 50
    assert SEGMENT_COLUMN in X.columns
    assert report.output_count == 50
    assert segmenter.kmeans is not None
