"""FastAPI application for credit card nudge recommendations."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import (
    AccountInput,
    BatchRecommendRequest,
    BatchRecommendResponse,
    HealthResponse,
    RecommendResponse,
    SegmentsResponse,
)
from src.inference.recommender import NudgeRecommender

ROOT = Path(__file__).resolve().parents[2]
SEGMENT_PROFILES_PATH = ROOT / "models" / "segment_profiles.json"
MODEL_PATH = ROOT / "models" / "model_bundle.pkl"

_recommender: NudgeRecommender | None = None


def get_recommender() -> NudgeRecommender:
    if _recommender is None:
        raise HTTPException(status_code=503, detail="Recommender not initialised")
    return _recommender


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _recommender
    if not MODEL_PATH.exists():
        raise RuntimeError(
            f"Model not found at {MODEL_PATH}. Run: python main.py train"
        )
    _recommender = NudgeRecommender()
    yield
    _recommender = None


app = FastAPI(
    title="Credit Card Nudge API",
    description=(
        "ML-powered nudge recommendations for credit card payment behaviour. "
        "Returns nudge type, tone, message, payment risk, and reward eligibility."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness check and model status."""
    rec = _recommender
    n_clusters = None
    if rec and rec.bundle and rec.bundle.segmenter:
        n_clusters = rec.bundle.n_clusters
    return HealthResponse(
        status="ok",
        model_loaded=rec is not None and rec.bundle is not None,
        n_clusters=n_clusters,
    )


@app.get("/v1/segments", response_model=SegmentsResponse, tags=["segments"])
def list_segments() -> SegmentsResponse:
    """Return named K-Means behavioural segment profiles."""
    if not SEGMENT_PROFILES_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Segment profiles not found. Run: python main.py train",
        )
    data = json.loads(SEGMENT_PROFILES_PATH.read_text(encoding="utf-8"))
    return SegmentsResponse(
        n_clusters=data.get("n_clusters", 0),
        note=data.get("note"),
        segments=data.get("segments", {}),
    )


@app.post("/v1/recommend", response_model=RecommendResponse, tags=["recommendations"])
def recommend(account: AccountInput) -> RecommendResponse:
    """
    Get nudge recommendation for a single customer account.

    Applies data cleaning, feature engineering, K-Means segment assignment,
    ML prediction, business rules, and message templating.
    """
    rec = get_recommender()
    payload = account.model_dump(exclude_none=True)
    result = rec.recommend(payload)
    return RecommendResponse(**result)


@app.post(
    "/v1/recommend/batch",
    response_model=BatchRecommendResponse,
    tags=["recommendations"],
)
def recommend_batch(body: BatchRecommendRequest) -> BatchRecommendResponse:
    """Get nudge recommendations for up to 100 customers in one request."""
    rec = get_recommender()
    results: list[RecommendResponse] = []
    for account in body.accounts:
        payload = account.model_dump(exclude_none=True)
        result = rec.recommend(payload)
        results.append(RecommendResponse(**result))
    return BatchRecommendResponse(count=len(results), results=results)
