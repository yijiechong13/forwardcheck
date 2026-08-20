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
    title="ForwardCheck API",
    description=(
        "Structured verification of forwarded news and status claims for "
        "Singapore and Malaysia. All bundled evidence is seeded sample data."
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
