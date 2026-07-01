"""Tests for FastAPI endpoints."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "model_bundle.pkl"

pytestmark = pytest.mark.skipif(
    not MODEL_PATH.exists(),
    reason="Trained model required — run: python main.py train",
)


@pytest.fixture
def client():
    from src.api.app import app

    with TestClient(app) as c:
        yield c


def _sample_account():
    return {
        "customerId": "CUST-API-001",
        "productId": "CARD-API-001",
        "age": 26,
        "payment_history_string": "MX",
        "payment_current_due_amount": 50.0,
        "payment_due_date": "2026-08-09",
        "current_balance_amount": 1320.0,
        "account_credit_limit_amount": 4500.0,
        "minimum_payment_schedule_amount": 25.0,
        "direct_debit_active_indicator": 0,
        "months_on_book_counter": 2,
        "account_status_open_indicator": 1,
    }


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True


def test_segments(client):
    r = client.get("/v1/segments")
    assert r.status_code == 200
    data = r.json()
    assert data["n_clusters"] == 3
    assert "segments" in data


def test_recommend(client):
    r = client.post("/v1/recommend", json=_sample_account())
    assert r.status_code == 200
    data = r.json()
    assert data["customerId"] == "CUST-API-001"
    assert data["nudge_type"] in (
        "reminder", "warning", "motivational", "reward_led", "direct_debit_setup", "none"
    )
    assert "customer_segment" in data
    assert data["customer_segment"]["name"] in ("reliable", "at_risk", "high_risk")


def test_recommend_batch(client):
    r = client.post(
        "/v1/recommend/batch",
        json={"accounts": [_sample_account(), _sample_account()]},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    assert len(data["results"]) == 2
