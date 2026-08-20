"""Runtime configuration.

Every adapter defaults to `mock`, so the app runs with no API keys and no
external services. Real backends are opt-in via environment variables.
"""

from __future__ import annotations

import os


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip().lower()


class Settings:
    llm_backend: str = _env("FORWARDCHECK_LLM", "mock")
    retrieval_backend: str = _env("FORWARDCHECK_RETRIEVAL", "mock")
    search_backend: str = _env("FORWARDCHECK_SEARCH", "mock")

    #: Evidence older than this is treated as potentially stale by the
    #: freshness node. 18 months is long enough that a policy has usually
    #: moved on, short enough that primary legislation is not flagged daily.
    stale_threshold_days: int = int(os.environ.get("FORWARDCHECK_STALE_DAYS", "540"))

    #: Retrieval score below which evidence is discarded rather than graded.
    #: Set deliberately high: a weak lexical match is worse than no evidence,
    #: because it invites a confident verdict from an irrelevant document.
    retrieval_min_score: float = float(
        os.environ.get("FORWARDCHECK_MIN_SCORE", "0.28")
    )

    max_evidence_per_claim: int = int(os.environ.get("FORWARDCHECK_MAX_EVIDENCE", "4"))

    cors_origins: list[str] = os.environ.get(
        "FORWARDCHECK_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")

    @property
    def is_fully_mocked(self) -> bool:
        return (
            self.llm_backend == "mock"
            and self.retrieval_backend == "mock"
            and self.search_backend == "mock"
        )


settings = Settings()
