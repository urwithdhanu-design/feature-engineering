"""Generate large synthetic training datasets with configurable history length."""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.features.payment_history import PAYMENT_CODE_LABELS, derive_payment_stats

ROOT = Path(__file__).resolve().parents[1]
TRAINING_DIR = ROOT / "data" / "training"

PAYMENT_CODES = ["M", "D", "L", "X", "N"]
# Realistic distribution: mostly on-time, some risk
CODE_WEIGHTS = [0.40, 0.10, 0.15, 0.20, 0.15]

DD_TYPES = ["Full Payment", "Minimum Payment", "No Direct Debit"]

SEGMENTS = [
    ("Working Singles & Couples", "Early career"),
    ("Young Starters", "Student / Part-time"),
    ("Established Families", "Established professional"),
    ("Mid-life Professionals", "Established professional"),
    ("Pre-retirement", "Senior professional"),
]


def _age_tone_persona(age: int) -> tuple[str, str | None]:
    if age <= 22:
        return "casual_energetic", "jordan"
    if age <= 30:
        return "professional_friendly", "ethan"
    return "supportive_clear", "sarah"


def _random_history(length: int, rng: random.Random) -> str:
    return "".join(rng.choices(PAYMENT_CODES, weights=CODE_WEIGHTS, k=length))


def _month_labels(history: str, anchor: date) -> list[dict[str, str]]:
    """Build per-month payment records for the last N cycles."""
    rows: list[dict[str, str]] = []
    for i, code in enumerate(history):
        month_date = anchor - timedelta(days=30 * (len(history) - 1 - i))
        rows.append(
            {
                "cycle": str(i + 1),
                "statement_month": month_date.strftime("%Y-%m"),
                "code": code,
                "label": PAYMENT_CODE_LABELS[code],
            }
        )
    return rows


def build_synthetic_customer(
    index: int,
    rng: random.Random,
    history_months: int = 2,
) -> dict[str, Any]:
    """Build one synthetic customer with N months of payment history."""
    history = _random_history(history_months, rng)
    stats = derive_payment_stats(history)

    age = rng.randint(18, 55)
    tone, persona_id = _age_tone_persona(age)
    segment, employment = rng.choice(SEGMENTS)

    limit = round(rng.uniform(1500, 8000), 2)
    utilization = rng.uniform(0.05, 0.95)
    balance = round(limit * utilization, 2)
    min_payment = max(25.0, round(balance * 0.01, 2))

    dd_type = rng.choice(DD_TYPES)
    dd_active = 0 if dd_type == "No Direct Debit" else 1

    if stats.has_arrears:
        current_due = round(stats.payment_total_past_due_amount + min_payment, 2)
    else:
        current_due = min_payment

    anchor = date(2026, 6, 25)
    open_date = anchor - timedelta(days=30 * history_months)

    return {
        "customerId": f"CUST{index:05d}",
        "productId": f"CARD{index:05d}",
        "synthetic": True,
        "payment_history_months": history_months,
        "payment_history": _month_labels(history, anchor),
        "persona_id": persona_id,
        "fresco_segment": segment,
        "age": age,
        "tone": tone,
        "employment_status": employment,
        "marital_status": None,
        "vulnerability_flag": "N",
        "brand_identifier": "LLOYDS",
        "brand_name": "Lloyds Bank",
        "account_open_date": open_date.isoformat(),
        "account_closed_date": None,
        "last_statement_date": anchor.isoformat(),
        "next_statement_date": (anchor + timedelta(days=30)).isoformat(),
        "payment_due_date": (anchor + timedelta(days=45)).isoformat(),
        "account_credit_limit_amount": limit,
        "account_credit_limit_cash_amount": round(limit * 0.25, 2),
        "account_credit_limit_available_amount": round(limit - balance, 2),
        "credit_limit_offered_amount": limit,
        "account_status_open_indicator": 1,
        "payment_total_due_amount": round(current_due + rng.uniform(0, 500), 2),
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
        "months_on_book_counter": history_months,
        "current_balance_amount": balance,
        "system_payment_cycle_due_code": "1",
        "payments_cycle_to_date_amount": 0.0 if stats.has_arrears else balance,
        "payment_history_string": history,
        "missing_payments_last_6_cycles": stats.missing_payments_last_6_cycles,
        "on_time_payments_last_6_cycles": stats.on_time_payments_last_6_cycles,
        "minimum_payment_schedule_amount": min_payment,
        "minimum_payment_schedule_percentage": 1.0,
    }


def generate_dataset(
    count: int = 5000,
    history_months: int = 2,
    seed: int = 42,
    output_name: str | None = None,
) -> Path:
    """Write synthetic customers to JSONL. Returns output path."""
    rng = random.Random(seed)
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    name = output_name or f"synthetic_{count}_{history_months}mo.jsonl"
    out_path = TRAINING_DIR / name

    with out_path.open("w", encoding="utf-8") as f:
        for i in range(1, count + 1):
            record = build_synthetic_customer(i, rng, history_months=history_months)
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return out_path


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    accounts: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                accounts.append(json.loads(line))
    return accounts


if __name__ == "__main__":
    path = generate_dataset(count=5000, history_months=2)
    print(f"Generated 5000 synthetic customers (2 months each) -> {path}")
