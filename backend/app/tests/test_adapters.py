"""Adapter contract tests.

The point of the adapter layer is that mock and real implementations are
interchangeable. These tests pin the parts of the contract that make that true:
closed-set outputs, honest empty results, and no key required to run.
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.models.schemas import SourceTier
from app.services.llm_adapter import MockLLMAdapter, get_llm_adapter
from app.services.retrieval_adapter import MockRetrievalAdapter, get_retrieval_adapter
from app.services.search_adapter import (
    SOURCE_ALLOWLIST,
    MockSearchAdapter,
    get_search_adapter,
    tier_for_domain,
)


def test_defaults_require_no_api_keys():
    assert settings.is_fully_mocked
    assert isinstance(get_llm_adapter(), MockLLMAdapter)
    assert isinstance(get_retrieval_adapter(), MockRetrievalAdapter)
    assert isinstance(get_search_adapter(), MockSearchAdapter)


def test_mock_llm_adapter_refuses_to_impersonate_the_llm():
    """Mock mode never consults an LLM adapter. If a refactor routes the live
    pipeline to the mock adapter, it must fail loudly rather than produce
    rule-based output labelled as LLM-backed."""
    from app.services.llm_adapter import LLMError
    from app.services.usage import UsageMeter

    adapter = MockLLMAdapter()
    with pytest.raises(LLMError):
        adapter.decompose("some message", UsageMeter())
    with pytest.raises(LLMError):
        adapter.grade("some prompt", UsageMeter())


def test_search_returns_nothing_rather_than_inventing_results():
    """An empty result is what keeps 'Insufficient evidence' honest."""
    from app.services.usage import UsageMeter

    assert MockSearchAdapter().search("cat licensing singapore", UsageMeter()) == []
    assert MockSearchAdapter().is_live is False


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.avs.nparks.gov.sg/page", SourceTier.OFFICIAL),
        ("https://sso.agc.gov.sg/Act/ABA1965", SourceTier.PRIMARY),
        ("https://www.channelnewsasia.com/singapore/x", SourceTier.CREDIBLE_NEWS),
        ("https://mothership.sg/2026/x", SourceTier.CREDIBLE_NEWS),
        ("https://random-blog.example.com/post", None),
    ],
)
def test_allowlist_assigns_a_known_tier_or_rejects(url, expected):
    assert tier_for_domain(url) == expected


def test_allowlist_is_singapore_only():
    """MVP scope: no non-Singapore jurisdictions in the source hierarchy."""
    for domain in SOURCE_ALLOWLIST:
        assert not domain.endswith(".my"), f"non-SG domain in allowlist: {domain}"


def test_social_sources_are_never_allowlisted():
    """Secondary/social sources must not be usable as proof."""
    for url in (
        "https://www.facebook.com/groups/x",
        "https://t.me/somechannel",
        "https://x.com/someone/status/1",
        "https://someblog.wordpress.com/post",
    ):
        assert tier_for_domain(url) is None


def test_retrieval_scores_are_normalised():
    adapter = MockRetrievalAdapter()
    results = adapter.search("cat licensing deadline", limit=5)
    assert results
    for _, score in results:
        assert 0.0 <= score <= 1.0


def test_retrieval_returns_nothing_for_an_unrelated_query():
    assert MockRetrievalAdapter().search("quantum chromodynamics lattice") == []
