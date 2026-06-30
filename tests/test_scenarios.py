"""Tests for payment history derivation and scenario generation."""

import json
from pathlib import Path

import pytest

from src.features.payment_history import SCENARIO_CODES, derive_payment_stats, scenario_label
from src.rules.reward_eligibility import assess_reward_eligibility

ROOT = Path(__file__).resolve().parents[1]


def test_scenario_count():
    assert len(SCENARIO_CODES) == 59


def test_mmm_perfect_payer():
    stats = derive_payment_stats("MMM")
    assert stats.missing_payments_last_6_cycles == 0
    assert stats.on_time_payments_last_6_cycles == 3
    assert stats.payment_total_past_due_amount == 0.0


def test_xxx_high_arrears():
    stats = derive_payment_stats("XXX")
    assert stats.missing_payments_last_6_cycles == 3
    assert stats.payment_total_past_due_amount > 0


def test_scenario_label():
    assert "Paid on time" in scenario_label("MMM")
    assert "Missed payment" in scenario_label("XXM")


def test_reward_eligibility_mmm():
    account = {
        "payment_history_string": "MMM",
        "months_on_book_counter": 3,
        "account_status_open_indicator": 1,
        "current_balance_amount": 237.5,
        "account_credit_limit_amount": 4000.0,
        "minimum_payment_schedule_amount": 25.0,
    }
    result = assess_reward_eligibility(account)
    assert result.eligible is True
    assert result.on_time_payments_count == 3


def test_reward_blocked_by_miss():
    account = {
        "payment_history_string": "MML",
        "months_on_book_counter": 3,
        "account_status_open_indicator": 1,
        "current_balance_amount": 237.5,
        "account_credit_limit_amount": 4000.0,
        "minimum_payment_schedule_amount": 25.0,
    }
    result = assess_reward_eligibility(account)
    assert result.eligible is False
    assert "Late payments" in " ".join(result.blockers)


def test_all_scenario_files_exist():
    scenarios_dir = ROOT / "data" / "scenarios"
    for persona in ("ethan", "sarah", "jordan"):
        for code in SCENARIO_CODES:
            path = scenarios_dir / persona / f"{code}.json"
            assert path.exists(), f"Missing {path}"


def test_scenario_json_schema_fields():
    path = ROOT / "data" / "scenarios" / "ethan" / "MMM.json"
    account = json.loads(path.read_text(encoding="utf-8"))
    required = [
        "customerId", "payment_history_string", "persona_scenario_name",
        "age", "tone", "direct_debit_type", "missing_payments_last_6_cycles",
    ]
    for field in required:
        assert field in account
