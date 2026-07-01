"""Nudge/risk alignment guardrails."""

from __future__ import annotations

from typing import Any

from src.guardrails.report import GuardrailCheck, GuardrailReport


def apply_alignment_guardrails(
    account: dict[str, Any],
    nudge_type: str,
    risk: dict[str, float],
    segment_name: str | None,
    report: GuardrailReport,
) -> str:
    """Ensure nudge severity aligns with payment risk and behavioural segment."""
    missed = float(risk.get("risk_missed_payment", 0))
    late = float(risk.get("risk_late_payment", 0))
    missing = int(account.get("missing_payments_last_6_cycles", 0))
    aligned = True
    action = None

    # Misalignment: high risk but weak nudge
    if (missed >= 0.7 or missing >= 2 or segment_name == "high_risk") and nudge_type in (
        "reminder",
        "direct_debit_setup",
    ):
        nudge_type = "warning"
        aligned = False
        action = "escalate_to_warning"

    # Misalignment: low risk but harsh nudge
    elif missed < 0.15 and late < 0.15 and missing == 0 and nudge_type == "warning":
        nudge_type = "reminder"
        aligned = False
        action = "downgrade_to_reminder"

    report.add(
        GuardrailCheck(
            name="risk_nudge_alignment",
            category="misalignment",
            passed=aligned,
            action=action,
            detail=f"nudge={nudge_type}, risk_missed={missed:.2f}, segment={segment_name}",
        )
    )

    return nudge_type
