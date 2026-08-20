"""Per-request usage metering and hard budget enforcement.

Two distinct things are counted, because conflating them lets retries spend
money invisibly:

  * **Logical operations** — how many decompositions/gradings/searches the
    pipeline asked for. This is what the pipeline reasons about.
  * **Provider requests** — how many HTTP requests were actually sent to a
    paid provider, including retries. This is what gets billed.

Hard limits constrain **provider requests**, not logical operations. A
transient failure that triggers a retry consumes budget exactly as it
consumes money. Charging once per logical operation (the earlier design)
meant a retry could issue a second billable request without being counted.

Never stores prompt contents, message text, URLs, or key material — counts only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import settings


class BudgetExceeded(Exception):
    """A hard per-request limit was reached.

    Not retried and not swallowed at the call site: the pipeline treats it as
    "stop spending and work with what we have", which downstream becomes
    abstention rather than an error page.
    """

    def __init__(self, limit_name: str, limit: int) -> None:
        self.limit_name = limit_name
        self.limit = limit
        super().__init__(f"budget exceeded: {limit_name} (limit {limit})")


@dataclass
class UsageMeter:
    # --- logical operations requested by the pipeline ---
    llm_operations: int = 0
    search_operations: int = 0

    # --- actual billable provider requests, retries included ---
    llm_requests: int = 0
    llm_retries: int = 0
    search_requests: int = 0
    search_retries: int = 0
    fetches: int = 0

    input_tokens: int = 0
    output_tokens: int = 0
    cache_hits: int = 0
    mode: str = field(default_factory=lambda: settings.mode)
    #: One line per extra spend decision, e.g. why a second search round ran.
    decisions: list[str] = field(default_factory=list)
    #: True when this whole response was replayed from cache.
    served_from_cache: bool = False

    # ---------------------------------------------------- logical operations

    def begin_llm_operation(self) -> None:
        """Record that the pipeline wants one logical LLM operation.

        Budget is not charged here — `charge_llm_request` does that per actual
        request. This is checked separately so a caller cannot start an
        operation it has no budget to make even one request for.
        """
        if self.llm_requests >= settings.max_llm_calls_per_request:
            raise BudgetExceeded("llm_requests", settings.max_llm_calls_per_request)
        self.llm_operations += 1

    def begin_search_operation(self) -> None:
        if self.search_requests >= settings.max_searches_total:
            raise BudgetExceeded("search_requests", settings.max_searches_total)
        self.search_operations += 1

    # ------------------------------------------- billable provider requests

    def charge_llm_request(self, *, is_retry: bool = False) -> None:
        """Call immediately BEFORE sending a request to the LLM provider."""
        if self.llm_requests >= settings.max_llm_calls_per_request:
            raise BudgetExceeded("llm_requests", settings.max_llm_calls_per_request)
        self.llm_requests += 1
        if is_retry:
            self.llm_retries += 1

    def charge_search_request(self, *, is_retry: bool = False) -> None:
        """Call immediately BEFORE sending a request to the search provider."""
        if self.search_requests >= settings.max_searches_total:
            raise BudgetExceeded("search_requests", settings.max_searches_total)
        self.search_requests += 1
        if is_retry:
            self.search_retries += 1

    def charge_fetch(self) -> None:
        if self.fetches >= settings.max_fetches_total:
            raise BudgetExceeded("fetches", settings.max_fetches_total)
        self.fetches += 1

    def can_retry_llm(self) -> bool:
        """Whether budget remains for one more LLM request."""
        return self.llm_requests < settings.max_llm_calls_per_request

    def can_retry_search(self) -> bool:
        return self.search_requests < settings.max_searches_total

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
            "servedFromCache": self.served_from_cache,
            # Logical operations the pipeline requested.
            "llmOperations": self.llm_operations,
            "searchOperations": self.search_operations,
            # Actual billable provider requests, retries included.
            "llmRequests": self.llm_requests,
            "llmRetries": self.llm_retries,
            "searchRequests": self.search_requests,
            "searchRetries": self.search_retries,
            "fetches": self.fetches,
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "cacheHits": self.cache_hits,
            "decisions": self.decisions,
        }
