"""Generate JSON scenario files for all personas and payment history codes."""

from __future__ import annotations

import json
from pathlib import Path

from src.features.payment_history import SCENARIO_CODES, scenario_label, derive_payment_stats

ROOT = Path(__file__).resolve().parents[1]
PERSONAS_DIR = ROOT / "data" / "personas"
SCENARIOS_DIR = ROOT / "data" / "scenarios"

PERSONA_FILES = ["ethan.json", "jordan.json", "sarah.json"]

# Scenario-specific direct debit configuration for variety
DD_CONFIG: dict[str, tuple[str, int]] = {
    # Perfect payers often have DD
    "MMM": ("Full Payment", 1),
    "MMD": ("Full Payment", 1),
    "MDM": ("Minimum Payment", 1),
    # At-risk scenarios: no DD
    "default_risky": ("No Direct Debit", 0),
    "default_good": ("Full Payment", 1),
}


def _dd_for_scenario(code: str) -> tuple[str, int]:
    if code in DD_CONFIG:
        return DD_CONFIG[code]
    if any(c in code for c in ("X", "N", "L")):
        return DD_CONFIG["default_risky"]
    return DD_CONFIG["default_good"]


def build_account(persona: dict, history: str, row_index: int) -> dict:
    """Build a full account JSON for a persona + payment history scenario."""
    stats = derive_payment_stats(history)
    dd_type, dd_active = _dd_for_scenario(history)

    min_payment = 25.0
    total_due = round(min_payment * 9.5, 2) if stats.has_arrears else 237.5
    current_due = (
        round(stats.payment_total_past_due_amount + min_payment, 2)
        if stats.has_arrears
        else min_payment
    )
    balance = current_due
    limit = 4000.0 if persona["persona_id"] == "ethan" else (
        3500.0 if persona["persona_id"] == "jordan" else 6000.0
    )
    available = round(limit - balance, 2)

    display = persona["display_name"]
    label = scenario_label(history)

    return {
        "customerId": persona["customer_id_prefix"],
        "productId": persona["product_id"],
        "persona_scenario_name": f"Matrix row {row_index:03d} {display}: {label}",
        "persona_id": persona["persona_id"],
        "fresco_segment": persona["fresco_segment"],
        "age": persona["age"],
        "age_group": persona["age_group"],
        "tone": persona["tone"],
        "employment_status": persona["employment_status"],
        "marital_status": persona.get("marital_status"),
        "vulnerability_flag": persona["vulnerability_flag"],
        "brand_identifier": "LLOYDS",
        "brand_name": "Lloyds Bank",
        "account_open_date": "2025-01-15",
        "account_closed_date": None,
        "last_statement_date": "2026-02-25",
        "next_statement_date": "2026-03-25",
        "payment_due_date": "2026-04-09",
        "account_credit_limit_amount": limit,
        "account_credit_limit_cash_amount": round(limit * 0.225, 2),
        "account_credit_limit_available_amount": available,
        "credit_limit_offered_amount": limit,
        "account_status_open_indicator": 1,
        "payment_total_due_amount": total_due,
        "payment_current_due_amount": current_due,
        "payment_total_past_due_amount": stats.payment_total_past_due_amount,
        "payment_1_cycle_past_due_amount": stats.payment_1_cycle_past_due_amount,
        "payment_2_cycle_past_due_amount": stats.payment_2_cycle_past_due_amount,
        "payment_3_cycle_past_due_amount": stats.payment_3_cycle_past_due_amount,
        "payment_4_cycle_past_due_amount": stats.payment_4_cycle_past_due_amount,
        "payment_5_cycle_past_due_amount": stats.payment_5_cycle_past_due_amount,
        "payment_6_cycle_past_due_amount": stats.payment_6_cycle_past_due_amount,
        "direct_debit_type": dd_type,
        "direct_debit_active_indicator": dd_active,
        "months_on_book_counter": 3,
        "current_balance_amount": balance,
        "system_payment_cycle_due_code": "1",
        "payments_cycle_to_date_amount": balance if not stats.has_arrears else 0.0,
        "payment_history_string": history,
        "missing_payments_last_6_cycles": stats.missing_payments_last_6_cycles,
        "on_time_payments_last_6_cycles": stats.on_time_payments_last_6_cycles,
        "minimum_payment_schedule_amount": min_payment,
        "minimum_payment_schedule_percentage": 1.0,
    }


def generate_all() -> int:
    """Generate all scenario JSON files. Returns count of files written."""
    count = 0
    for persona_file in PERSONA_FILES:
        persona_path = PERSONAS_DIR / persona_file
        persona = json.loads(persona_path.read_text(encoding="utf-8"))
        persona_id = persona["persona_id"]
        out_dir = SCENARIOS_DIR / persona_id
        out_dir.mkdir(parents=True, exist_ok=True)

        for idx, code in enumerate(SCENARIO_CODES, start=1):
            account = build_account(persona, code, idx)
            out_path = out_dir / f"{code}.json"
            out_path.write_text(
                json.dumps(account, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            count += 1

    return count


if __name__ == "__main__":
    written = generate_all()
    print(f"Generated {written} scenario files across {len(PERSONA_FILES)} personas.")
