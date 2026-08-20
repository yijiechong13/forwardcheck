"""Search adapter — live web retrieval.

Unimplemented in MVP by design (PROJECT_SPEC.md: no live scraping), but the
interface exists so the pipeline has a defined seam to add it at, and so the
constraints that *must* apply to live search are written down before anyone
wires one in.

Those constraints are the interesting part of this file:

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
    tier: SourceTier


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
    def search(self, query: str, *, limit: int = 5) -> list[SearchResult]: ...

    @property
    @abstractmethod
    def is_live(self) -> bool: ...


class MockSearchAdapter(SearchAdapter):
    """Returns nothing. Live search is out of scope for the MVP.

    Returning an empty list rather than fabricated results is the honest
    behaviour: the pipeline then relies solely on the seeded corpus, and
    anything it cannot answer comes back as `Insufficient evidence` instead of
    being backed by an invented citation.
    """

    @property
    def is_live(self) -> bool:
        return False

    def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        return []


class WebSearchAdapter(SearchAdapter):  # pragma: no cover
    """Placeholder for the live web search implementation."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def is_live(self) -> bool:
        return True

    def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        raise NotImplementedError(
            "Live web search is not implemented. Run with FORWARDCHECK_SEARCH=mock "
            "(the default). See the TODO at the top of this module."
        )


def get_search_adapter() -> SearchAdapter:
    if settings.search_backend == "web":  # pragma: no cover
        import os

        key = os.environ.get("SEARCH_API_KEY")
        if not key:
            raise RuntimeError(
                "FORWARDCHECK_SEARCH=web but SEARCH_API_KEY is not set."
            )
        return WebSearchAdapter(key)
    return MockSearchAdapter()
