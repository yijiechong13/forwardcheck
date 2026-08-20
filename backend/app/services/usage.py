"""Per-request usage metering and hard budget enforcement.

Every provider call site checks the meter *before* spending money, and records
what it actually spent afterwards. The meter is created per verification
request and its summary goes into the pipeline trace, so every response shows
what it cost in calls and tokens.

Never stores prompt contents, message text, or key material — counts only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import settings


class BudgetExceeded(Exception):
    """A hard per-request limit was reached.

    Deliberately not retried and not swallowed at the call site: the pipeline
    treats it as "stop spending and work with what we have", which downstream
    turns into abstention rather than an error page.
    """

    def __init__(self, limit_name: str, limit: int) -> None:
        self.limit_name = limit_name
        self.limit = limit
        super().__init__(f"budget exceeded: {limit_name} (limit {limit})")


@dataclass
class UsageMeter:
    llm_calls: int = 0
    searches: int = 0
    fetches: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hits: int = 0
    mode: str = field(default_factory=lambda: settings.mode)
    #: One line per extra spend decision, e.g. why a second search round ran.
    decisions: list[str] = field(default_factory=list)

    # ---------------------------------------------------------- enforcement

    def charge_llm_call(self) -> None:
        if self.llm_calls >= settings.max_llm_calls_per_request:
            raise BudgetExceeded("llm_calls", settings.max_llm_calls_per_request)
        self.llm_calls += 1

    def charge_search(self) -> None:
        if self.searches >= settings.max_searches_total:
            raise BudgetExceeded("searches", settings.max_searches_total)
        self.searches += 1

    def charge_fetch(self) -> None:
        if self.fetches >= settings.max_fetches_total:
            raise BudgetExceeded("fetches", settings.max_fetches_total)
        self.fetches += 1

    # ------------------------------------------------------------ recording

    def record_tokens(self, input_tokens: int | None, output_tokens: int | None) -> None:
        self.input_tokens += input_tokens or 0
        self.output_tokens += output_tokens or 0

    def record_cache_hit(self) -> None:
        self.cache_hits += 1

    def record_decision(self, reason: str) -> None:
        self.decisions.append(reason)

    # -------------------------------------------------------------- summary

    def summary(self) -> dict:
        """Safe to expose to the client. No prompts, no keys, no URLs."""
        return {
            "mode": self.mode,
            "llmCalls": self.llm_calls,
            "searches": self.searches,
            "fetches": self.fetches,
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "cacheHits": self.cache_hits,
            "decisions": self.decisions,
        }
