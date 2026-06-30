"""Payment history encoding and account state derivation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PaymentCode = Literal["M", "D", "L", "X", "N"]

PAYMENT_CODE_LABELS: dict[str, str] = {
    "M": "Paid on time",
    "D": "Paid early",
    "L": "Paid late",
    "X": "Missed payment",
    "N": "Never paid",
}

# All 59 payment-history scenarios from the specification matrix.
SCENARIO_CODES: list[str] = [
    "MMM", "MMD", "MML", "MMX", "MMN", "MDM", "MDD", "MDL", "MDX", "MDN",
    "LMM", "LLL",
    "XMX", "XMN", "XDM", "XDD", "XDL", "XDX", "XDN", "XLM", "XLD", "XLL",
    "XLX", "XLN", "XXM", "XXD", "XXL", "XXX", "XXN", "XNM", "XND", "XNL",
    "XNX", "XNN",
    "NMM", "NMD", "NML", "NMX", "NMN", "NDM", "NDD", "NDL", "NDX", "NDN",
    "NLM", "NLD", "NLL", "NLX", "NLN", "NXM", "NXD", "NXL", "NXX", "NXN",
    "NNM", "NND", "NNL", "NNX", "NNN",
]


@dataclass(frozen=True)
class PaymentHistoryStats:
    """Derived counters from a payment history string."""

    payment_history_string: str
    missing_payments_last_6_cycles: int
    on_time_payments_last_6_cycles: int
    late_payments_last_6_cycles: int
    early_payments_last_6_cycles: int
    never_paid_cycles: int
    payment_1_cycle_past_due_amount: float
    payment_2_cycle_past_due_amount: float
    payment_3_cycle_past_due_amount: float
    payment_4_cycle_past_due_amount: float
    payment_5_cycle_past_due_amount: float
    payment_6_cycle_past_due_amount: float
    payment_total_past_due_amount: float
    has_arrears: bool
    reward_qualifying_on_time_count: int


def scenario_label(history: str) -> str:
    """Human-readable label for a payment history string."""
    parts = [PAYMENT_CODE_LABELS[c] for c in history]
    return " / ".join(parts)


def _cycle_past_due(code: str, min_payment: float, running_arrears: float) -> tuple[float, float]:
    """Return (cycle_past_due, updated_running_arrears) for one cycle."""
    if code in ("M", "D"):
        return 0.0, 0.0
    if code == "L":
        late_portion = round(min_payment * 0.5, 2)
        return late_portion, late_portion
    if code == "X":
        new_arrears = round(running_arrears + min_payment, 2)
        return new_arrears, new_arrears
    # N — never paid; arrears accumulate
    new_arrears = round(running_arrears + min_payment, 2)
    return new_arrears, new_arrears


def derive_payment_stats(
    history: str,
    min_payment: float = 25.0,
    cycles_in_window: int = 6,
) -> PaymentHistoryStats:
    """
    Derive payment counters and rolling past-due amounts from a history string.

    History is ordered oldest → newest (cycle 1 → cycle 3 for a 3-char string).
    Counters reflect only observed cycles; older slots in the 6-cycle window are
    treated as pre-account (zero past-due, not counted toward on-time/missing).
    """
    observed = history

    missing = sum(1 for c in observed if c in ("X", "N"))
    on_time = sum(1 for c in observed if c in ("M", "D"))
    late = sum(1 for c in observed if c == "L")
    early = sum(1 for c in observed if c == "D")
    never = sum(1 for c in observed if c == "N")

    # Reward-qualifying: contractual minimum on time (M only, not early)
    reward_on_time = sum(1 for c in observed if c == "M")

    running = 0.0
    cycle_dues: list[float] = []
    for code in observed:
        due, running = _cycle_past_due(code, min_payment, running)
        cycle_dues.append(due)

    # Pad to 6-cycle window with zeros for pre-account cycles
    while len(cycle_dues) < cycles_in_window:
        cycle_dues.insert(0, 0.0)
    cycle_dues = cycle_dues[-cycles_in_window:]

    total_past_due = round(running, 2)

    return PaymentHistoryStats(
        payment_history_string=history,
        missing_payments_last_6_cycles=missing,
        on_time_payments_last_6_cycles=on_time,
        late_payments_last_6_cycles=late,
        early_payments_last_6_cycles=early,
        never_paid_cycles=never,
        payment_1_cycle_past_due_amount=cycle_dues[0],
        payment_2_cycle_past_due_amount=cycle_dues[1],
        payment_3_cycle_past_due_amount=cycle_dues[2],
        payment_4_cycle_past_due_amount=cycle_dues[3],
        payment_5_cycle_past_due_amount=cycle_dues[4],
        payment_6_cycle_past_due_amount=cycle_dues[5],
        payment_total_past_due_amount=total_past_due,
        has_arrears=total_past_due > 0,
        reward_qualifying_on_time_count=reward_on_time,
    )
