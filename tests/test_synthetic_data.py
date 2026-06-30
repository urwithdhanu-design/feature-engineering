"""Tests for synthetic training data generation."""

import json
from pathlib import Path

from scripts.generate_synthetic_training_data import build_synthetic_customer, generate_dataset
from src.models.train import load_training_data

ROOT = Path(__file__).resolve().parents[1]


def test_synthetic_customer_has_two_months():
    import random

    rng = random.Random(99)
    record = build_synthetic_customer(1, rng, history_months=2)
    assert len(record["payment_history_string"]) == 2
    assert record["payment_history_months"] == 2
    assert len(record["payment_history"]) == 2
    assert record["months_on_book_counter"] == 2


def test_generate_small_dataset(tmp_path):
    path = generate_dataset(count=10, history_months=2, output_name="test_10.jsonl")
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 10
    first = json.loads(lines[0])
    assert first["synthetic"] is True
    assert "payment_history" in first


def test_load_training_data_prefers_synthetic():
    accounts, source = load_training_data()
    if (ROOT / "data" / "training" / "synthetic_5000_2mo.jsonl").exists():
        assert len(accounts) == 5000
        assert "synthetic_5000_2mo.jsonl" in source
