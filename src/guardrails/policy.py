"""Business policy guardrails (reward, vulnerability, account status)."""

from __future__ import annotations

from typing import Any

from src.guardrails.report import GuardrailCheck, GuardrailReport
from src.rules.reward_eligibility import RewardEligibility, assess_reward_eligibility


def apply_policy_guardrails(
    account: dict[str, Any],
    nudge_type: str,
    tone: str,
    reward: RewardEligibility,
    report: GuardrailReport,
) -> tuple[str, str, bool]:
    """
    Enforce business-policy overrides.

    Returns (nudge_type, tone, show_nudge).
    """
    show_nudge = True
    vulnerability = str(account.get("vulnerability_flag", "N")).upper() == "Y"
    account_open = int(account.get("account_status_open_indicator", 1)) == 1

    # Goal alignment: closed account → no nudge
    if not account_open:
        show_nudge = False
        report.add(
            GuardrailCheck(
                name="goal_closed_account",
                category="goal_misalignment",
                passed=False,
                action="suppress_nudge",
                detail="Account not open — nudge suppressed",
            )
        )

    # Goal alignment: reward_led only when rules say eligible
    if nudge_type == "reward_led" and not reward.eligible:
        nudge_type = "motivational"
        report.add(
            GuardrailCheck(
                name="goal_reward_misalignment",
                category="goal_misalignment",
                passed=False,
                action="downgrade_reward_led_to_motivational",
                detail="Reward-led nudge blocked — customer not eligible",
            )
        )
    elif reward.eligible and nudge_type != "reward_led":
        nudge_type = "reward_led"
        report.add(
            GuardrailCheck(
                name="goal_reward_override",
                category="goal_misalignment",
                passed=True,
                action="force_reward_led",
                detail="Eligible customer — reward-led nudge enforced",
            )
        )

    # Bias / fairness: vulnerable customers get supportive tone, softer nudge
    if vulnerability:
        tone = "supportive_clear"
        if nudge_type == "warning":
            nudge_type = "motivational"
        report.add(
            GuardrailCheck(
                name="bias_vulnerability",
                category="bias",
                passed=True,
                action="vulnerability_soften_tone_and_nudge",
                detail="Vulnerable customer — supportive tone, warning avoided",
            )
        )
    else:
        report.add(
            GuardrailCheck(
                name="bias_vulnerability",
                category="bias",
                passed=True,
                detail="Standard tone policy applied",
            )
        )

    return nudge_type, tone, show_nudge
