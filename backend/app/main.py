"""ForwardCheck API.

A thin HTTP layer. All verification logic lives in `app.pipeline`, so the graph
can be exercised in tests and the eval harness without going through FastAPI.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.schemas import VerifyRequest, VerifyResponse
from app.pipeline.runner import run_verification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("forwardcheck")

app = FastAPI(
    title="ForwardCheck SG API",
    description=(
        "Verifies forwarded public-interest claims by decomposing them into "
        "status claims, retrieving official or credible Singapore evidence, and "
        "producing source-backed verdicts with timelines. All bundled evidence "
        "is seeded sample data."
    ),
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "mode": "mock" if settings.is_fully_mocked else "partial-live",
        "adapters": {
            "llm": settings.llm_backend,
            "retrieval": settings.retrieval_backend,
            "search": settings.search_backend,
        },
    }


@app.get("/config")
def config() -> dict:
    """Effective configuration, for the dev panel and for debugging a run.

    Surfaced because a verdict is only interpretable if you know which
    adapters produced it — a rule-based run and an LLM-backed run are not
    comparable, and the difference must never be invisible.
    """
    from app.services.retrieval_adapter import get_retrieval_adapter

    return {
        "adapters": {
            "llm": settings.llm_backend,
            "retrieval": settings.retrieval_backend,
            "search": settings.search_backend,
        },
        "corpusSize": get_retrieval_adapter().corpus_size(),
        "evidenceIsMock": True,
        "retrievalMinScore": settings.retrieval_min_score,
        "maxEvidencePerClaim": settings.max_evidence_per_claim,
        "staleThresholdDays": settings.stale_threshold_days,
    }


@app.post("/verify", response_model=VerifyResponse, response_model_by_alias=True)
def verify(request: VerifyRequest) -> VerifyResponse:
    """Run a forwarded message through the verification pipeline."""
    message = request.message.strip()
    if len(message) < 12:
        raise HTTPException(
            status_code=422,
            detail="Message is too short to contain a checkable claim.",
        )

    logger.info("verify: %d chars", len(message))
    return run_verification(message)
