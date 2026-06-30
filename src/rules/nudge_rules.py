"""Rule-based nudge selection and label generation for training."""

from __future__ import annotations

from typing import Any

from src.features.engineer import NUDGE_TYPES, TONE_TYPES, age_to_group
from src.rules.reward_eligibility import assess_reward_eligibility


def derive_nudge_type(account: dict[str, Any]) -> str:
    """Derive optimal nudge type from account state (training label / fallback)."""
    reward = assess_reward_eligibility(account)
    dd_active = int(account.get("direct_debit_active_indicator", 0)) == 1
    missing = int(account.get("missing_payments_last_6_cycles", 0))
    late = int(account.get("_late_payments", 0))
    past_due = float(account.get("payment_total_past_due_amount", 0))
    history = account.get("payment_history_string", "MMM")
    never = int(account.get("_never_paid_cycles", 0))

    if reward.eligible:
        return "reward_led"

    if not dd_active and missing == 0 and late == 0 and past_due == 0:
        if reward.payments_needed > 0 and reward.payments_needed <= 2:
            return "reward_led"
        return "direct_debit_setup"

    if missing >= 2 or never >= 1 or past_due >= 50:
        return "warning"

    if missing == 1 or late >= 1 or history.endswith(("L", "X", "N")):
        return "motivational"

    if past_due > 0:
        return "warning"

    if reward.payments_needed > 0 and not reward.blockers:
        return "reward_led"

    return "reminder"


def derive_tone(account: dict[str, Any], persona: dict[str, Any] | None = None) -> str:
    """Map age/persona to messaging tone."""
    if persona and persona.get("tone"):
        return persona["tone"]
    age = int(account.get("age", 30))
    group = age_to_group(age)
    tone_map = {
        "gen_z": "casual_energetic",
        "young_adult": "professional_friendly",
        "mid_career": "supportive_clear",
    }
    return tone_map.get(group, "supportive_clear")


def derive_risk_labels(account: dict[str, Any]) -> dict[str, float]:
    """Derive payment risk probabilities (training labels) from payment history."""
    history = account.get("payment_history_string", "MMM")
    missing = int(account.get("missing_payments_last_6_cycles", 0))
    late = int(account.get("_late_payments", 0))
    never = int(account.get("_never_paid_cycles", 0))
    past_due = float(account.get("payment_total_past_due_amount", 0))

    # Base risk from most recent cycle behaviour
    last_code = history[-1] if history else "M"

    risk_missed = 0.05
    risk_late = 0.08
    risk_min_only = 0.15

    if last_code == "X":
        risk_missed = 0.85
        risk_late = 0.55
        risk_min_only = 0.70
    elif last_code == "N":
        risk_missed = 0.92
        risk_late = 0.40
        risk_min_only = 0.75
    elif last_code == "L":
        risk_missed = 0.35
        risk_late = 0.72
        risk_min_only = 0.55
    elif last_code == "M":
        risk_missed = 0.06
        risk_late = 0.10
        risk_min_only = 0.20
    elif last_code == "D":
        risk_missed = 0.03
        risk_late = 0.05
        risk_min_only = 0.12

    risk_missed += missing * 0.08 + never * 0.12
    risk_late += late * 0.10
    risk_min_only += (past_due > 0) * 0.15

    return {
        "risk_missed_payment": min(round(risk_missed, 4), 0.99),
        "risk_late_payment": min(round(risk_late, 4), 0.99),
        "risk_minimum_only_payment": min(round(risk_min_only, 4), 0.99),
    }
