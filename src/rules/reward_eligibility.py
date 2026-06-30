"""£20 reward eligibility rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.features.payment_history import derive_payment_stats


@dataclass
class RewardEligibility:
    eligible: bool
    on_time_payments_count: int
    payments_needed: int
    reasons: list[str]
    blockers: list[str]


REQUIRED_ON_TIME_PAYMENTS = 3
ELIGIBILITY_WINDOW_MONTHS = 6


def assess_reward_eligibility(account: dict[str, Any]) -> RewardEligibility:
    """
    Assess £20 reward eligibility per product Terms & Conditions.

    Qualifies when:
    - 3 contractual minimum payments on time within 6 months of opening
    - Account active with balance generating minimum payment due
    - No missed or late payments
    - Good standing: no arrears, no over-limit at payment due
    """
    reasons: list[str] = []
    blockers: list[str] = []

    months_on_book = int(account.get("months_on_book_counter", 0))
    history = account.get("payment_history_string", "MMM")
    min_pay = float(account.get("minimum_payment_schedule_amount", 25.0))
    stats = derive_payment_stats(history, min_pay)

    on_time_count = stats.reward_qualifying_on_time_count
    payments_needed = max(0, REQUIRED_ON_TIME_PAYMENTS - on_time_count)

    if account.get("account_status_open_indicator", 1) != 1:
        blockers.append("Account is not active")

    if months_on_book > ELIGIBILITY_WINDOW_MONTHS and on_time_count < REQUIRED_ON_TIME_PAYMENTS:
        blockers.append(
            f"Eligibility window ({ELIGIBILITY_WINDOW_MONTHS} months) exceeded "
            f"with only {on_time_count} qualifying payments"
        )

    if stats.late_payments_last_6_cycles > 0:
        blockers.append("Late payments on record")

    if stats.missing_payments_last_6_cycles > 0:
        blockers.append("Missed or never-paid cycles on record")

    if stats.has_arrears or float(account.get("payment_total_past_due_amount", 0)) > 0:
        blockers.append("Arrears outstanding")

    balance = float(account.get("current_balance_amount", 0))
    if balance <= 0:
        blockers.append("No balance — minimum payment not yet due")

    limit = float(account.get("account_credit_limit_amount", 1))
    if balance > limit:
        blockers.append("Over-limit at payment due point")

    if on_time_count >= REQUIRED_ON_TIME_PAYMENTS:
        reasons.append(
            f"{on_time_count} contractual on-time payments within eligibility window"
        )
    elif on_time_count > 0:
        reasons.append(
            f"{on_time_count} of {REQUIRED_ON_TIME_PAYMENTS} qualifying payments made — "
            f"{payments_needed} more needed"
        )

    eligible = len(blockers) == 0 and on_time_count >= REQUIRED_ON_TIME_PAYMENTS

    return RewardEligibility(
        eligible=eligible,
        on_time_payments_count=on_time_count,
        payments_needed=payments_needed,
        reasons=reasons,
        blockers=blockers,
    )
