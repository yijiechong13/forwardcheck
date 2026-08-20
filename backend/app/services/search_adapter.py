"""Search adapter — live web retrieval via Tavily, plus the domain tier map.

Constraints that apply to live search:

**Domain allowlist, not a general web search.** ForwardCheck SG ranks sources by
authority. A general search API returns content farms and SEO pages that would
enter the corpus with no defensible tier, and the whole verdict model rests on
tier weighting. `SOURCE_ALLOWLIST` maps domains to tiers, so anything retrieved
has a known authority before it is graded.

**Freshness matters more than usual.** For status claims the *newest*
authoritative document wins: a conviction supersedes a charge. Live results must
carry a reliable date or be treated as undated and heavily discounted.

**A live result is not automatically better than a seeded one.** The mock
adapter returns nothing rather than pretending, so `Insufficient evidence` stays
honest when search is off.

TODO(web-search): implement WebSearchAdapter.
  - provider: Brave Search API or Tavily (both return dates and snippets)
  - filter results to SOURCE_ALLOWLIST before they reach the pipeline
  - fetch and extract the page body; the snippet alone is usually too short to
    grade a status claim against
  - cache aggressively by URL — government advisories change rarely and the
    same claims get forwarded for months
  - respect robots.txt and rate limits
  - never let a live result silently outrank a primary source: tier first,
    recency second
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.config import settings
from app.models.schemas import SourceTier

#: Domain -> authority tier. Singapore only for the MVP. Only these may enter
#: the evidence pool from live search. Everything else is dropped rather than added as "secondary", because
#: an unknown source with a guessed tier corrupts the ranking that every verdict
#: depends on. See DATA_SOURCES.md.
SOURCE_ALLOWLIST: dict[str, SourceTier] = {
    # --- Singapore: primary ---
    "sso.agc.gov.sg": SourceTier.PRIMARY,
    "judiciary.gov.sg": SourceTier.PRIMARY,
    # --- Singapore: official ---
    "gov.sg": SourceTier.OFFICIAL,
    "factually.gov.sg": SourceTier.OFFICIAL,
    "police.gov.sg": SourceTier.OFFICIAL,
    "agc.gov.sg": SourceTier.OFFICIAL,
    "mha.gov.sg": SourceTier.OFFICIAL,
    "mom.gov.sg": SourceTier.OFFICIAL,
    "ica.gov.sg": SourceTier.OFFICIAL,
    "moh.gov.sg": SourceTier.OFFICIAL,
    "hsa.gov.sg": SourceTier.OFFICIAL,
    "sfa.gov.sg": SourceTier.OFFICIAL,
    "nparks.gov.sg": SourceTier.OFFICIAL,
    "avs.nparks.gov.sg": SourceTier.OFFICIAL,
    "csa.gov.sg": SourceTier.OFFICIAL,
    # Listed as an official SG source for verifying whether an advisory exists.
    # This is source authenticity, not scam detection — see PROJECT_SPEC.md.
    "scamshield.gov.sg": SourceTier.OFFICIAL,
    "mindef.gov.sg": SourceTier.OFFICIAL,
    "mnd.gov.sg": SourceTier.OFFICIAL,
    "mti.gov.sg": SourceTier.OFFICIAL,
    # --- Credible news (Singapore) ---
    "channelnewsasia.com": SourceTier.CREDIBLE_NEWS,
    "straitstimes.com": SourceTier.CREDIBLE_NEWS,
    "todayonline.com": SourceTier.CREDIBLE_NEWS,
    "mothership.sg": SourceTier.CREDIBLE_NEWS,
    "mediacorp.sg": SourceTier.CREDIBLE_NEWS,
    "8world.com": SourceTier.CREDIBLE_NEWS,
}


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    published_at: str | None
    #: Tier from the domain allowlist; SECONDARY when the domain is unknown.
    #: Unknown domains are kept (unlike the pre-live design) because live
    #: verification of developing events sometimes rests on credible pages the
    #: allowlist has not catalogued — but SECONDARY weighting means they can
    #: never outrank an official source, and grading treats them as weak.
    tier: SourceTier
    publisher: str = ""
    provider_score: float = 0.0
    query: str = ""


def tier_for_domain(url: str) -> SourceTier | None:
    """Tier for a URL, or None if the domain is not allowlisted."""
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    if host in SOURCE_ALLOWLIST:
        return SOURCE_ALLOWLIST[host]
    # Match parent domains so subdomains inherit their parent's tier.
    for domain, tier in SOURCE_ALLOWLIST.items():
        if host.endswith(f".{domain}"):
            return tier
    return None


class SearchAdapter(ABC):
    @abstractmethod
    def search(
        self, query: str, meter, *, limit: int = 5
    ) -> list[SearchResult]: ...

    @property
    @abstractmethod
    def is_live(self) -> bool: ...


class MockSearchAdapter(SearchAdapter):
    """Returns nothing. Mock mode verifies against the seeded corpus only.

    Returning an empty list rather than fabricated results is the honest
    behaviour: anything the seeded corpus cannot answer comes back as
    `Insufficient evidence` instead of being backed by an invented citation.
    """

    @property
    def is_live(self) -> bool:
        return False

    def search(self, query: str, meter, *, limit: int = 5) -> list[SearchResult]:
        return []


class SearchError(Exception):
    """A search-provider failure the pipeline should absorb, not crash on."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
        super().__init__(f"search error: {kind}")


class TavilySearchAdapter(SearchAdapter):
    """Tavily search API (https://docs.tavily.com), via httpx.

    Why Tavily: purpose-built for retrieval pipelines — returns clean snippets,
    relevance scores and (often) publication dates, without HTML scraping of a
    results page. The adapter interface hides it, so swapping providers later
    touches only this class.

    Cost discipline: every call charges the UsageMeter first, and identical
    queries are served from the TTL cache. The API key is read from the
    environment by name and sent only as an Authorization header — never
    logged or returned.
    """

    _ENDPOINT = "https://api.tavily.com/search"
    _TRANSIENT = {429, 500, 502, 503, 504}

    def __init__(self, http_client=None) -> None:
        import os

        import httpx

        key = os.environ.get("TAVILY_API_KEY")
        if not key:
            raise RuntimeError(
                "TAVILY_API_KEY is not set. Add it to backend/.env for live mode."
            )
        self._client = http_client or httpx.Client(
            timeout=settings.request_timeout_seconds,
            headers={"Authorization": f"Bearer {key}"},
        )
        self._cache = None  # created lazily so tests can run without a cache dir

    @property
    def is_live(self) -> bool:
        return True

    def _get_cache(self):
        if self._cache is None:
            from app.services.cache import search_cache

            self._cache = search_cache()
        return self._cache

    def search(self, query: str, meter, *, limit: int = 5) -> list[SearchResult]:
        import time as _time

        cache = self._get_cache()
        cache_key = {"provider": "tavily", "q": query, "limit": limit}
        cached = cache.get(cache_key)
        if cached is not None:
            meter.record_cache_hit()
            return [self._to_result(item, query) for item in cached]

        meter.charge_search()

        payload = {
            "query": query,
            "search_depth": "basic",
            "max_results": limit,
            "include_raw_content": False,
        }

        attempts = 0
        while True:
            attempts += 1
            try:
                response = self._client.post(self._ENDPOINT, json=payload)
            except Exception as exc:  # connection/timeout
                if attempts == 1:
                    _time.sleep(1.0)
                    continue
                raise SearchError("timeout") from exc

            if response.status_code in (401, 403):
                # Never retried, never cached.
                raise SearchError("auth")
            if response.status_code in self._TRANSIENT and attempts == 1:
                _time.sleep(2.0 if response.status_code == 429 else 1.0)
                continue
            if response.status_code != 200:
                raise SearchError(f"provider_status_{response.status_code}")
            break

        try:
            body = response.json()
            raw_results = body.get("results", [])
            assert isinstance(raw_results, list)
        except Exception as exc:
            # Malformed response: fail this search, do not cache the failure.
            raise SearchError("malformed_response") from exc

        normalised = [
            {
                "title": str(item.get("title") or "")[:300],
                "url": str(item.get("url") or ""),
                "snippet": str(item.get("content") or "")[:1500],
                "published_at": item.get("published_date") or None,
                "score": float(item.get("score") or 0.0),
            }
            for item in raw_results
            if item.get("url")
        ]

        cache.set(cache_key, normalised)
        return [self._to_result(item, query) for item in normalised]

    @staticmethod
    def _to_result(item: dict, query: str) -> SearchResult:
        from urllib.parse import urlparse

        url = item["url"]
        tier = tier_for_domain(url)
        return SearchResult(
            title=item["title"],
            url=url,
            snippet=item["snippet"],
            published_at=item.get("published_at"),
            tier=tier if tier is not None else SourceTier.SECONDARY,
            publisher=(urlparse(url).hostname or "unknown").removeprefix("www."),
            provider_score=float(item.get("score") or 0.0),
            query=query,
        )


def get_search_adapter() -> SearchAdapter:
    if settings.is_live:
        return TavilySearchAdapter()
    return MockSearchAdapter()
