"""End-to-end nudge recommendation for UI display."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.features.engineer import account_to_features, accounts_to_dataframe, enrich_account
from src.messages.templates import format_message, message_scenario_key
from src.models.train import ModelBundle
from src.rules.nudge_rules import derive_nudge_type, derive_tone
from src.rules.reward_eligibility import assess_reward_eligibility

ROOT = Path(__file__).resolve().parents[2]
PERSONAS_DIR = ROOT / "data" / "personas"


def load_persona(persona_id: str) -> dict[str, Any] | None:
    path = PERSONAS_DIR / f"{persona_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


class NudgeRecommender:
    """Combines ML models, business rules, and message templates."""

    def __init__(self, model_bundle: ModelBundle | None = None) -> None:
        self.bundle = model_bundle
        if self.bundle is None:
            model_path = ROOT / "models" / "model_bundle.pkl"
            if model_path.exists():
                self.bundle = ModelBundle.load(model_path)

    def recommend(self, account: dict[str, Any]) -> dict[str, Any]:
        enriched = enrich_account(account)
        persona = load_persona(enriched.get("persona_id", ""))

        features = accounts_to_dataframe([enriched])

        if self.bundle:
            nudge_type = self.bundle.predict_nudge(features)
            tone = self.bundle.predict_tone(features)
            risk = self.bundle.predict_risk(features)
        else:
            nudge_type = derive_nudge_type(enriched)
            tone = derive_tone(enriched, persona)
            from src.rules.nudge_rules import derive_risk_labels
            risk = derive_risk_labels(enriched)

        reward = assess_reward_eligibility(enriched)
        dd_active = int(enriched.get("direct_debit_active_indicator", 0)) == 1

        # Rule overrides for critical cases
        if reward.eligible:
            nudge_type = "reward_led"
        elif not dd_active and nudge_type == "reminder" and reward.payments_needed > 0:
            nudge_type = "direct_debit_setup"

        scenario_key = message_scenario_key(
            nudge_type=nudge_type,
            reward_eligible=reward.eligible,
            reward_near=reward.payments_needed <= 2 and not reward.blockers,
            has_missing=int(enriched.get("missing_payments_last_6_cycles", 0)) > 0,
            dd_active=dd_active,
        )

        reward_info = {
            "eligible": reward.eligible,
            "on_time_payments_count": reward.on_time_payments_count,
            "payments_needed": reward.payments_needed,
            "reasons": reward.reasons,
            "blockers": reward.blockers,
        }

        message = format_message(
            tone=tone,
            nudge_type=nudge_type,
            scenario_key=scenario_key,
            account=enriched,
            reward_info=reward_info,
        )

        return {
            "customerId": enriched.get("customerId"),
            "productId": enriched.get("productId"),
            "persona_id": enriched.get("persona_id"),
            "payment_history_string": enriched.get("payment_history_string"),
            "nudge_type": nudge_type,
            "tone": tone,
            "message": message,
            "message_scenario": scenario_key,
            "payment_risk": risk,
            "reward_eligibility": reward_info,
            "direct_debit": {
                "active": dd_active,
                "type": enriched.get("direct_debit_type"),
            },
            "show_nudge": nudge_type != "none",
        }


def recommend_for_account(account: dict[str, Any]) -> dict[str, Any]:
    return NudgeRecommender().recommend(account)
