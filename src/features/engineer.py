"""Feature engineering from account JSON payloads."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.features.payment_history import derive_payment_stats

NUDGE_TYPES = [
    "reminder",
    "warning",
    "motivational",
    "reward_led",
    "direct_debit_setup",
    "none",
]

TONE_TYPES = ["professional_friendly", "casual_energetic", "supportive_clear"]

AGE_GROUP_MAP = {
    (0, 22): "gen_z",
    (23, 30): "young_adult",
    (31, 100): "mid_career",
}


def age_to_group(age: int) -> str:
    for (lo, hi), group in AGE_GROUP_MAP.items():
        if lo <= age <= hi:
            return group
    return "mid_career"


def enrich_account(account: dict[str, Any]) -> dict[str, Any]:
    """Add derived payment stats to an account record."""
    history = account.get("payment_history_string", "MMM")
    min_pay = float(account.get("minimum_payment_schedule_amount", 25.0))
    stats = derive_payment_stats(history, min_pay)
    enriched = {**account}
    for field in (
        "missing_payments_last_6_cycles",
        "on_time_payments_last_6_cycles",
        "payment_1_cycle_past_due_amount",
        "payment_2_cycle_past_due_amount",
        "payment_3_cycle_past_due_amount",
        "payment_4_cycle_past_due_amount",
        "payment_5_cycle_past_due_amount",
        "payment_6_cycle_past_due_amount",
        "payment_total_past_due_amount",
    ):
        enriched[field] = getattr(stats, field)
    enriched["_reward_qualifying_on_time_count"] = stats.reward_qualifying_on_time_count
    enriched["_has_arrears"] = stats.has_arrears
    enriched["_late_payments"] = stats.late_payments_last_6_cycles
    enriched["_early_payments"] = stats.early_payments_last_6_cycles
    enriched["_never_paid_cycles"] = stats.never_paid_cycles
    return enriched


def account_to_features(account: dict[str, Any]) -> dict[str, float]:
    """Convert account dict to numeric feature vector for ML models."""
    acc = enrich_account(account)
    history = acc.get("payment_history_string", "MMM")
    history_codes = {"M": 0, "D": 1, "L": 2, "X": 3, "N": 4}

    features: dict[str, float] = {
        "age": float(acc.get("age", 30)),
        "months_on_book_counter": float(acc.get("months_on_book_counter", 0)),
        "account_credit_limit_amount": float(acc.get("account_credit_limit_amount", 0)),
        "account_credit_limit_available_amount": float(
            acc.get("account_credit_limit_available_amount", 0)
        ),
        "utilization": _utilization(acc),
        "payment_total_due_amount": float(acc.get("payment_total_due_amount", 0)),
        "payment_current_due_amount": float(acc.get("payment_current_due_amount", 0)),
        "payment_total_past_due_amount": float(acc.get("payment_total_past_due_amount", 0)),
        "missing_payments_last_6_cycles": float(acc.get("missing_payments_last_6_cycles", 0)),
        "on_time_payments_last_6_cycles": float(acc.get("on_time_payments_last_6_cycles", 0)),
        "_late_payments": float(acc.get("_late_payments", 0)),
        "_never_paid_cycles": float(acc.get("_never_paid_cycles", 0)),
        "direct_debit_active_indicator": float(acc.get("direct_debit_active_indicator", 0)),
        "minimum_payment_schedule_amount": float(
            acc.get("minimum_payment_schedule_amount", 25.0)
        ),
        "reward_qualifying_on_time_count": float(
            acc.get("_reward_qualifying_on_time_count", 0)
        ),
        "has_arrears": float(acc.get("_has_arrears", False)),
        "account_status_open_indicator": float(acc.get("account_status_open_indicator", 1)),
    }

    for i, code in enumerate(history.ljust(3, "M")[:3]):
        features[f"cycle_{i + 1}_code"] = float(history_codes.get(code, 0))

    return features


def accounts_to_dataframe(accounts: list[dict[str, Any]]) -> pd.DataFrame:
    """Build feature DataFrame from a list of account records."""
    rows = [account_to_features(a) for a in accounts]
    return pd.DataFrame(rows).fillna(0.0)


def _utilization(acc: dict[str, Any]) -> float:
    limit = float(acc.get("account_credit_limit_amount", 1.0))
    balance = float(acc.get("current_balance_amount", 0.0))
    if limit <= 0:
        return 0.0
    return round(balance / limit, 4)


FEATURE_COLUMNS = [
    "age",
    "months_on_book_counter",
    "utilization",
    "payment_total_due_amount",
    "payment_current_due_amount",
    "payment_total_past_due_amount",
    "missing_payments_last_6_cycles",
    "on_time_payments_last_6_cycles",
    "_late_payments",
    "_never_paid_cycles",
    "direct_debit_active_indicator",
    "reward_qualifying_on_time_count",
    "has_arrears",
    "cycle_1_code",
    "cycle_2_code",
    "cycle_3_code",
]
