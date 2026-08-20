"""Runtime configuration.

One master switch, FORWARDCHECK_MODE:

  * ``mock`` (default) — deterministic pipeline over the seeded corpus. No
    network calls, no API keys, $0. This is what tests and CI run.
  * ``live`` — Anthropic-backed decomposition and grading, Tavily search, and
    real page fetching. Requires ANTHROPIC_API_KEY and TAVILY_API_KEY, and
    fails at startup if they are missing rather than silently degrading.

Keys are read from the environment, which may be populated from an untracked
``backend/.env`` file. Key VALUES are never logged, echoed, or returned by any
endpoint; only presence booleans are exposed.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env if present. override=False: a variable already exported in
# the shell wins over the file, which is the least surprising precedence.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


def _env_int(name: str, default: int, lo: int, hi: int) -> int:
    """Bounded integer from the environment.

    Out-of-range values raise instead of being clamped: a silently clamped
    budget is a budget the operator believes is different from the one that
    is actually enforced.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got {raw!r}") from exc
    if not (lo <= value <= hi):
        raise RuntimeError(f"{name}={value} outside allowed range [{lo}, {hi}]")
    return value


class Settings:
    # ------------------------------------------------------------------ mode
    mode: str = _env("FORWARDCHECK_MODE", "mock").lower()

    # Legacy per-adapter switches, kept so existing tests and tooling work.
    # FORWARDCHECK_MODE takes precedence when set to "live".
    llm_backend: str = _env("FORWARDCHECK_LLM", "mock").lower()
    retrieval_backend: str = _env("FORWARDCHECK_RETRIEVAL", "mock").lower()
    search_backend: str = _env("FORWARDCHECK_SEARCH", "mock").lower()

    # -------------------------------------------------------------- providers
    anthropic_model: str = _env("ANTHROPIC_MODEL", "claude-haiku-4-5")

    # ---------------------------------------------------------- hard budgets
    # Every limit is enforced per verification request. Defaults are chosen so
    # a single request costs cents, not dollars, on the default model.
    max_claims: int = _env_int("FORWARDCHECK_MAX_CLAIMS", 6, 1, 12)
    max_search_rounds: int = _env_int("FORWARDCHECK_MAX_SEARCH_ROUNDS", 2, 1, 3)
    max_searches_total: int = _env_int("FORWARDCHECK_MAX_SEARCHES_TOTAL", 8, 1, 24)
    max_sources_per_claim: int = _env_int("FORWARDCHECK_MAX_SOURCES_PER_CLAIM", 3, 1, 8)
    max_llm_calls_per_request: int = _env_int(
        "FORWARDCHECK_MAX_LLM_CALLS_PER_REQUEST", 3, 1, 6
    )
    request_timeout_seconds: int = _env_int(
        "FORWARDCHECK_REQUEST_TIMEOUT_SECONDS", 20, 5, 120
    )
    max_fetches_total: int = _env_int("FORWARDCHECK_MAX_FETCHES_TOTAL", 8, 1, 24)

    # ------------------------------------------------------------- fetching
    fetch_timeout_seconds: float = 8.0
    fetch_max_bytes: int = 1_500_000
    fetch_max_redirects: int = 3

    # -------------------------------------------------------------- chunking
    chunk_max_chars: int = _env_int("FORWARDCHECK_CHUNK_MAX_CHARS", 1400, 300, 6000)
    chunk_overlap_chars: int = _env_int("FORWARDCHECK_CHUNK_OVERLAP", 150, 0, 1000)

    # --------------------------------------------------------------- caching
    cache_dir: Path = Path(
        _env("FORWARDCHECK_CACHE_DIR", str(Path(__file__).resolve().parents[1] / ".cache"))
    )
    cache_ttl_search_seconds: int = _env_int(
        "FORWARDCHECK_CACHE_TTL_SEARCH", 6 * 3600, 60, 7 * 24 * 3600
    )
    cache_ttl_page_seconds: int = _env_int(
        "FORWARDCHECK_CACHE_TTL_PAGE", 48 * 3600, 60, 30 * 24 * 3600
    )
    cache_ttl_result_seconds: int = _env_int(
        "FORWARDCHECK_CACHE_TTL_RESULT", 30 * 60, 0, 24 * 3600
    )

    # -------------------------------------------- deterministic-pipeline knobs
    stale_threshold_days: int = int(os.environ.get("FORWARDCHECK_STALE_DAYS", "540"))
    retrieval_min_score: float = float(os.environ.get("FORWARDCHECK_MIN_SCORE", "0.28"))
    max_evidence_per_claim: int = int(os.environ.get("FORWARDCHECK_MAX_EVIDENCE", "4"))

    cors_origins: list[str] = os.environ.get(
        "FORWARDCHECK_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")

    # ------------------------------------------------------------- derived
    @property
    def is_live(self) -> bool:
        return self.mode == "live"

    @property
    def has_anthropic_key(self) -> bool:
        """Presence only. The value is never read outside the SDK client."""
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    @property
    def has_tavily_key(self) -> bool:
        return bool(os.environ.get("TAVILY_API_KEY"))

    @property
    def is_fully_mocked(self) -> bool:
        return not self.is_live and (
            self.llm_backend == "mock"
            and self.retrieval_backend == "mock"
            and self.search_backend == "mock"
        )

    def validate_startup(self) -> list[str]:
        """Return a list of configuration problems. Empty means healthy.

        Live mode with missing keys is an error, not a downgrade: a run the
        operator believes is live but is quietly mock would invalidate any
        conclusion drawn from it.
        """
        problems: list[str] = []
        if self.mode not in ("mock", "live"):
            problems.append(
                f"FORWARDCHECK_MODE must be 'mock' or 'live', got {self.mode!r}"
            )
        if self.is_live:
            if not self.has_anthropic_key:
                problems.append("live mode requires ANTHROPIC_API_KEY (set it in backend/.env)")
            if not self.has_tavily_key:
                problems.append("live mode requires TAVILY_API_KEY (set it in backend/.env)")
        if self.chunk_overlap_chars >= self.chunk_max_chars:
            problems.append("FORWARDCHECK_CHUNK_OVERLAP must be smaller than FORWARDCHECK_CHUNK_MAX_CHARS")
        return problems


settings = Settings()
