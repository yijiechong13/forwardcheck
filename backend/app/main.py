"""ForwardCheck API.

A thin HTTP layer. Verification logic lives in `app.pipeline`; this module owns
startup validation, CORS, rate limiting, and translating internal failures into
safe, non-leaking client errors. Provider exceptions and stack traces are
logged server-side and never serialised into a response.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.schemas import VerifyRequest, VerifyResponse
from app.pipeline.runner import run_verification
from app.services.llm_adapter import LLMError
from app.services.search_adapter import SearchError
from app.services.usage import BudgetExceeded

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("forwardcheck")

app = FastAPI(
    title="ForwardCheck SG API",
    description=(
        "Verifies forwarded public-interest claims by decomposing them into "
        "status claims, retrieving evidence, and producing claim-level "
        "verdicts with citations."
    ),
    version="0.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup validation: fail fast on misconfiguration, without leaking values.
# ---------------------------------------------------------------------------

@app.on_event("startup")
def _validate_configuration() -> None:
    problems = settings.validate_startup()
    for problem in problems:
        logger.error("configuration problem: %s", problem)
    if problems and settings.is_live:
        # Live mode with missing keys must not start half-configured.
        raise RuntimeError(
            "ForwardCheck is configured for live mode but required settings are "
            "missing. See the log lines above (values are never printed)."
        )


# ---------------------------------------------------------------------------
# Minimal per-client rate limiting (in-memory sliding window).
#
# Suitable for a single-process deployment; the abstraction point for anything
# bigger is this one function. Keyed by client host, 10 verifications/minute.
# ---------------------------------------------------------------------------

_WINDOW_SECONDS = 60
_MAX_REQUESTS_PER_WINDOW = 10
_request_log: dict[str, deque[float]] = defaultdict(deque)


def _rate_limited(client_key: str) -> bool:
    now = time.monotonic()
    window = _request_log[client_key]
    while window and now - window[0] > _WINDOW_SECONDS:
        window.popleft()
    if len(window) >= _MAX_REQUESTS_PER_WINDOW:
        return True
    window.append(now)
    return False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    """Configured/live/mock status. Booleans only — never key material."""
    problems = settings.validate_startup()
    return {
        "status": "ok" if not problems else "misconfigured",
        "mode": settings.mode,
        "live": settings.is_live,
        "providersConfigured": {
            "anthropic": settings.has_anthropic_key,
            "tavily": settings.has_tavily_key,
        },
        "model": settings.anthropic_model if settings.is_live else None,
        "problems": problems,
    }


@app.get("/config")
def config() -> dict:
    """Effective limits, for the dev panel. No secrets, no key material."""
    return {
        "mode": settings.mode,
        "budgets": {
            "maxClaims": settings.max_claims,
            "maxSearchRounds": settings.max_search_rounds,
            "maxSearchesTotal": settings.max_searches_total,
            "maxSourcesPerClaim": settings.max_sources_per_claim,
            "maxLlmCallsPerRequest": settings.max_llm_calls_per_request,
            "maxFetchesTotal": settings.max_fetches_total,
            "requestTimeoutSeconds": settings.request_timeout_seconds,
        },
        "model": settings.anthropic_model if settings.is_live else None,
        "cacheTtlSeconds": {
            "search": settings.cache_ttl_search_seconds,
            "page": settings.cache_ttl_page_seconds,
            "result": settings.cache_ttl_result_seconds,
        },
    }


@app.post("/verify", response_model=VerifyResponse, response_model_by_alias=True)
def verify(request: VerifyRequest, http_request: Request) -> VerifyResponse:
    message = request.message.strip()
    if len(message) < 12:
        raise HTTPException(
            status_code=422,
            detail="Message is too short to contain a checkable claim.",
        )

    client_key = http_request.client.host if http_request.client else "unknown"
    if _rate_limited(client_key):
        raise HTTPException(
            status_code=429,
            detail="Too many verification requests. Please wait a minute and try again.",
        )

    logger.info("verify: %d chars, mode=%s", len(message), settings.mode)
    try:
        return run_verification(message)
    except LLMError as exc:
        logger.error("verification failed: llm %s", exc.kind)
        raise HTTPException(status_code=502, detail=_SAFE_LLM_ERRORS.get(
            exc.kind, "The language-model provider is unavailable. Try again shortly."
        )) from exc
    except SearchError as exc:
        logger.error("verification failed: search %s", exc.kind)
        raise HTTPException(
            status_code=502,
            detail="The search provider is unavailable. Try again shortly.",
        ) from exc
    except BudgetExceeded as exc:
        # Normally absorbed inside the pipeline; reaching here means the very
        # first call was already over budget (misconfigured limits).
        logger.error("verification failed: budget %s", exc.limit_name)
        raise HTTPException(
            status_code=503,
            detail="This request exceeded the configured verification budget.",
        ) from exc


_SAFE_LLM_ERRORS = {
    "auth": "The server's language-model credentials are missing or invalid.",
    "permission": "The server's language-model credentials lack permission for this model.",
    "rate_limit": "The language-model provider is rate limiting. Try again shortly.",
    "timeout": "The language-model provider timed out. Try again shortly.",
    "malformed_output": "The language model returned an unusable response. Try again.",
}


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler: log the traceback, return a generic message."""
    logger.exception("unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred."},
    )
