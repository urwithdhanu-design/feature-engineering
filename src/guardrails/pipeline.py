"""Guardrail pipeline orchestration."""

from __future__ import annotations

from typing import Any

from src.guardrails.alignment import apply_alignment_guardrails
from src.guardrails.input_safety import sanitize_account_input
from src.guardrails.output_safety import apply_output_guardrails
from src.guardrails.policy import apply_policy_guardrails
from src.guardrails.report import GuardrailReport
from src.rules.reward_eligibility import assess_reward_eligibility


def run_input_guardrails(account: dict[str, Any]) -> tuple[dict[str, Any], GuardrailReport]:
    report = GuardrailReport()
    sanitized = sanitize_account_input(account, report)
    return sanitized, report


def run_output_guardrails(
    account: dict[str, Any],
    draft: dict[str, Any],
    report: GuardrailReport,
) -> dict[str, Any]:
    """Apply policy, alignment, and output safety checks to a draft recommendation."""
    reward = assess_reward_eligibility(account)

    segment = draft.get("customer_segment") or {}
    segment_name = segment.get("name") if isinstance(segment, dict) else None

    nudge_type = draft["nudge_type"]
    tone = draft["tone"]
    risk = draft["payment_risk"]
    message = draft["message"]

    nudge_type, tone, show_nudge = apply_policy_guardrails(
        account, nudge_type, tone, reward, report
    )

    nudge_type = apply_alignment_guardrails(
        account, nudge_type, risk, segment_name, report
    )

    message = apply_output_guardrails(message, nudge_type, tone, report)

    result = {**draft}
    result["nudge_type"] = nudge_type
    result["tone"] = tone
    result["message"] = message
    result["show_nudge"] = show_nudge and nudge_type != "none"
    result["guardrails"] = report.to_dict()
    return result
