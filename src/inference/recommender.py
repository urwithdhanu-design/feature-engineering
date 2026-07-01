"""End-to-end nudge recommendation for UI display."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.features.engineer import enrich_account
from src.guardrails.pipeline import run_input_guardrails, run_output_guardrails
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
    """Combines ML models, business rules, message templates, and guardrails."""

    def __init__(self, model_bundle: ModelBundle | None = None) -> None:
        self.bundle = model_bundle
        if self.bundle is None:
            model_path = ROOT / "models" / "model_bundle.pkl"
            if model_path.exists():
                self.bundle = ModelBundle.load(model_path)

    def recommend(self, account: dict[str, Any]) -> dict[str, Any]:
        account, guardrail_report = run_input_guardrails(account)
        enriched = enrich_account(account)
        persona = load_persona(enriched.get("persona_id", ""))

        if self.bundle:
            features = self.bundle.build_features([enriched])
            nudge_type = self.bundle.predict_nudge(features)
            tone = self.bundle.predict_tone(features)
            risk = self.bundle.predict_risk(features)
            segment_detail = self.bundle.predict_segment_detail(features)
        else:
            from src.features.engineer import accounts_to_dataframe
            from src.rules.nudge_rules import derive_risk_labels

            features = accounts_to_dataframe([enriched])
            nudge_type = derive_nudge_type(enriched)
            tone = derive_tone(enriched, persona)
            risk = derive_risk_labels(enriched)
            segment_detail = None

        reward = assess_reward_eligibility(enriched)
        dd_active = int(enriched.get("direct_debit_active_indicator", 0)) == 1

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

        draft = {
            "customerId": enriched.get("customerId"),
            "productId": enriched.get("productId"),
            "persona_id": enriched.get("persona_id"),
            "customer_segment": segment_detail,
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

        return run_output_guardrails(enriched, draft, guardrail_report)


def recommend_for_account(account: dict[str, Any]) -> dict[str, Any]:
    return NudgeRecommender().recommend(account)
