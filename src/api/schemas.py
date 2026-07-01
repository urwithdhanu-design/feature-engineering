"""Pydantic schemas for the FastAPI layer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AccountInput(BaseModel):
    """Customer account payload for nudge recommendation."""

    model_config = ConfigDict(extra="allow")

    customerId: str = Field(..., examples=["CUST55001"])
    productId: str | None = None
    age: int | None = Field(None, ge=18, le=100)
    payment_history_string: str = Field(..., examples=["MX", "MM", "M"])
    payment_current_due_amount: float = Field(..., ge=0)
    payment_due_date: str = Field(..., examples=["2026-08-09"])
    current_balance_amount: float = Field(..., ge=0)
    account_credit_limit_amount: float = Field(..., gt=0)
    minimum_payment_schedule_amount: float = Field(25.0, ge=0)
    direct_debit_active_indicator: int = Field(0, ge=0, le=1)
    direct_debit_type: str | None = None
    months_on_book_counter: int | None = Field(None, ge=0)
    account_status_open_indicator: int = Field(1, ge=0, le=1)
    persona_id: str | None = None


class BatchRecommendRequest(BaseModel):
    accounts: list[AccountInput] = Field(..., min_length=1, max_length=100)


class SegmentProfile(BaseModel):
    model_config = ConfigDict(extra="allow")

    cluster_id: int | None = None
    segment_name: str | None = None
    segment_label: str | None = None
    count: int | None = None
    avg_missing_payments: float | None = None
    avg_on_time_payments: float | None = None
    pct_has_arrears: float | None = None
    avg_age: float | None = None
    age_min: int | None = None
    age_max: int | None = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    n_clusters: int | None = None


class SegmentsResponse(BaseModel):
    n_clusters: int
    note: str | None = None
    segments: dict[str, Any]


class RecommendResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    customerId: str | None = None
    productId: str | None = None
    persona_id: str | None = None
    customer_segment: dict[str, Any] | None = None
    payment_history_string: str | None = None
    nudge_type: str
    tone: str
    message: str
    message_scenario: str | None = None
    payment_risk: dict[str, float]
    reward_eligibility: dict[str, Any]
    direct_debit: dict[str, Any]
    show_nudge: bool
    guardrails: dict[str, Any] | None = None


class BatchRecommendResponse(BaseModel):
    count: int
    results: list[RecommendResponse]
