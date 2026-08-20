"""Live-pipeline behaviour, exercised entirely offline.

Fake LLM and search adapters stand in for Anthropic and Tavily, and page
fetching is stubbed, so these tests cost $0 and make no network calls while
exercising the real orchestration: decomposition validation, retrieval,
batched grading, the bounded refinement loop, budget enforcement, abstention,
and deterministic aggregation.
"""

from __future__ import annotations

import pytest

import app.pipeline.live as live
from app.models.llm_schemas import (
    DecompositionResult,
    EvidenceGradeItem,
    ExtractedClaim,
    GradingResult,
)
from app.models.schemas import Verdict
from app.pipeline.chunk import Chunk
from app.pipeline.live import run_live_verification
from app.services.llm_adapter import LLMError
from app.services.search_adapter import SearchResult
from app.models.schemas import SourceTier
from app.services.usage import UsageMeter


MESSAGE = (
    "From 1 Sept, HDB cat owners with more than 2 cats will automatically be "
    "fined $5,000. All cats must be licensed by 31 Aug. Forward to everyone."
)


def _claim(text, span, queries, status="penalty", searchable=True, **kw):
    return ExtractedClaim(
        claim_text=text,
        source_span=span,
        status_type=status,
        domain="policy",
        jurisdiction="Singapore",
        searchable=searchable,
        search_queries=queries,
        **kw,
    )


class FakeLLM:
    """Scriptable adapter: decomposition result + a queue of grading results."""

    name = "fake:test"

    def __init__(self, decomposition, gradings):
        self._decomposition = decomposition
        self._gradings = list(gradings)
        self.grade_prompts: list[str] = []

    def decompose(self, message, meter):
        meter.begin_llm_operation()
        meter.charge_llm_request()
        return self._decomposition

    def grade(self, pairs_prompt, meter):
        meter.begin_llm_operation()
        meter.charge_llm_request()
        self.grade_prompts.append(pairs_prompt)
        if not self._gradings:
            raise AssertionError("grade called more times than scripted")
        return self._gradings.pop(0)


class FakeSearch:
    is_live = True

    def __init__(self, results_by_query=None, default=None):
        self._by_query = results_by_query or {}
        self._default = default if default is not None else []
        self.queries: list[str] = []

    def search(self, query, meter, *, limit=5):
        meter.begin_search_operation()
        meter.charge_search_request()
        self.queries.append(query)
        for needle, results in self._by_query.items():
            if needle in query:
                return results
        return self._default


def _result(url, title, snippet, tier=SourceTier.OFFICIAL):
    return SearchResult(
        title=title, url=url, snippet=snippet, published_at="2026-06-01",
        tier=tier, publisher="nparks.gov.sg", provider_score=0.9, query="q",
    )


@pytest.fixture
def wire(monkeypatch, tmp_path):
    """Install fakes and disable the result cache; returns an installer."""
    monkeypatch.setattr("app.config.settings.cache_ttl_result_seconds", 0)

    def install(llm, search, pages: dict[str, list[tuple[str, str]]]):
        monkeypatch.setattr(live, "get_llm_adapter", lambda: llm)
        monkeypatch.setattr(live, "get_search_adapter", lambda: search)

        def fake_fetch(url, meter, http_client=None):
            meter.charge_fetch()
            if url not in pages:
                from app.services.fetch import FetchError
                raise FetchError("status_404")
            from app.services.fetch import FetchedPage
            return FetchedPage(url=url, title="Page", blocks=pages[url])

        monkeypatch.setattr(live, "fetch_page", fake_fetch)

    return install


GOOD_PAGE = [
    ("heading", "Cat licensing penalties"),
    ("text", "A person who contravenes the licensing requirement is liable on "
             "conviction to a fine not exceeding $5,000. The penalty is a maximum "
             "determined by the court, not an automatic fine. Cats must be "
             "licensed by 31 Aug under the scheme."),
]


def _grade(cid, eid, rel, conf=0.9, contradicted=(), temporal="current"):
    return EvidenceGradeItem(
        claim_id=cid, evidence_id=eid, relationship=rel, confidence=conf,
        contradicted_aspects=list(contradicted), temporal_status=temporal,
        rationale="Maximum on conviction, not automatic." if rel == "refutes" else "Matches the claim.",
        quoted_span="fine not exceeding $5,000",
    )


def test_happy_path_grades_and_aggregates(wire):
    llm = FakeLLM(
        DecompositionResult(claims=[
            _claim("HDB cat owners with more than 2 cats will automatically be fined $5,000.",
                   "automatically be fined $5,000", ["site:nparks.gov.sg cat fine"]),
            _claim("All cats must be licensed by 31 Aug.",
                   "licensed by 31 Aug", ["site:nparks.gov.sg cat licensing deadline"],
                   status="deadline"),
        ], non_factual_content=["Forward to everyone."]),
        gradings=[GradingResult(grades=[
            _grade("c1", "e1", "refutes", contradicted=["modality: up to vs automatic"]),
            _grade("c2", "e1", "supports"),
        ])],
    )
    search = FakeSearch(default=[_result("https://x.gov.sg/a", "Licensing", "snippet")])
    wire(llm, search, {"https://x.gov.sg/a": GOOD_PAGE})

    response = run_live_verification(MESSAGE)

    by_id = {c.id: c for c in response.claims}
    assert by_id["c1"].verdict == Verdict.MISLEADING.value
    assert by_id["c2"].verdict == Verdict.SUPPORTED.value
    assert response.overall_verdict == Verdict.MISLEADING.value
    # Live evidence is real, not mock, and carries the actual URL.
    assert all(not e.is_mock for e in response.evidence)
    assert response.evidence[0].url.startswith("https://x.gov.sg/")


def test_non_abstaining_verdicts_cite_evidence(wire):
    llm = FakeLLM(
        DecompositionResult(claims=[_claim(
            "Cats must be licensed by 31 Aug.", "licensed by 31 Aug",
            ["q1"], status="deadline")]),
        gradings=[GradingResult(grades=[_grade("c1", "e1", "supports")])],
    )
    wire(llm, FakeSearch(default=[_result("https://x.gov.sg/a", "t", "s")]),
         {"https://x.gov.sg/a": GOOD_PAGE})
    response = run_live_verification(MESSAGE)
    for claim in response.claims:
        if claim.verdict != Verdict.INSUFFICIENT.value:
            assert claim.evidence_ids


def test_no_search_results_abstains(wire):
    llm = FakeLLM(
        DecompositionResult(claims=[_claim(
            "Cats must be licensed by 31 Aug.", "licensed by 31 Aug", ["q"])]),
        gradings=[],  # grading must never be called with zero pairs
    )
    wire(llm, FakeSearch(default=[]), {})
    response = run_live_verification(MESSAGE)
    assert response.claims[0].verdict == Verdict.INSUFFICIENT.value
    assert response.overall_verdict == Verdict.INSUFFICIENT.value


def test_refinement_round_runs_only_when_insufficient(wire):
    """Round 1 grades everything does_not_answer -> refined query -> round 2."""
    llm = FakeLLM(
        DecompositionResult(claims=[_claim(
            "Cats must be licensed by 31 Aug.", "licensed by 31 Aug",
            ["first query"], status="deadline")]),
        gradings=[
            GradingResult(
                grades=[_grade("c1", "e1", "does_not_answer", conf=0.2)],
                refined_queries={"c1": "cat licensing deadline site:nparks.gov.sg"},
            ),
            GradingResult(grades=[_grade("c1", "e2", "supports")]),
        ],
    )
    search = FakeSearch(results_by_query={
        "first query": [_result("https://x.gov.sg/weak", "Weak", "unrelated")],
        "nparks": [_result("https://x.gov.sg/strong", "Strong", "s")],
    })
    wire(llm, search, {
        "https://x.gov.sg/weak": [("text", "Cats are licensed. Unrelated filler about the licensing scheme for cats and more cats.")],
        "https://x.gov.sg/strong": GOOD_PAGE,
    })
    response = run_live_verification(MESSAGE)
    assert response.claims[0].verdict == Verdict.SUPPORTED.value
    # The refined query was actually used, and the trace explains why.
    assert any("nparks" in q for q in search.queries)
    refine_steps = [s for s in response.pipeline_trace if s.node == "retrieve.refine"]
    assert refine_steps and "no qualifying evidence" in refine_steps[0].summary


def test_search_rounds_are_hard_capped(wire, monkeypatch):
    """Evidence stays insufficient forever -> exactly max_search_rounds rounds."""
    llm = FakeLLM(
        DecompositionResult(claims=[_claim(
            "Cats must be licensed by 31 Aug.", "licensed by 31 Aug", ["q"])]),
        gradings=[
            GradingResult(grades=[_grade("c1", "e1", "does_not_answer", conf=0.1)],
                          refined_queries={"c1": "refined"}),
            GradingResult(grades=[_grade("c1", "e2", "does_not_answer", conf=0.1)],
                          refined_queries={"c1": "refined again"}),
            # A third grading call would raise AssertionError in FakeLLM.
        ],
    )
    pages = {
        f"https://x.gov.sg/{i}": [("text", "Cats licensing scheme text about licensed cats filler." * 3)]
        for i in range(4)
    }
    search = FakeSearch(results_by_query={
        "q": [_result("https://x.gov.sg/0", "a", "s")],
        "refined": [_result("https://x.gov.sg/1", "b", "s")],
    })
    wire(llm, search, pages)
    response = run_live_verification(MESSAGE)
    assert response.claims[0].verdict == Verdict.INSUFFICIENT.value
    grade_steps = [s for s in response.pipeline_trace if s.node == "grade"]
    assert len(grade_steps) == 2  # max_search_rounds, no more


def test_llm_budget_enforced_across_calls(wire, monkeypatch):
    monkeypatch.setattr("app.config.settings.max_llm_calls_per_request", 1)
    llm = FakeLLM(
        DecompositionResult(claims=[_claim(
            "Cats must be licensed by 31 Aug.", "licensed by 31 Aug", ["q"])]),
        gradings=[GradingResult(grades=[_grade("c1", "e1", "supports")])],
    )
    wire(llm, FakeSearch(default=[_result("https://x.gov.sg/a", "t", "s")]),
         {"https://x.gov.sg/a": GOOD_PAGE})
    response = run_live_verification(MESSAGE)
    # Decompose consumed the only allowed call; grading was skipped; abstain.
    assert response.claims[0].verdict == Verdict.INSUFFICIENT.value
    usage = next(s for s in response.pipeline_trace if s.node == "usage")
    assert usage.details["llmRequests"] == 1


def test_llm_failure_falls_back_to_deterministic_decomposition(wire):
    class FailingLLM:
        name = "fake:failing"
        def decompose(self, message, meter):
            meter.begin_llm_operation()
            meter.charge_llm_request()
            raise LLMError("provider", "status 500")
        def grade(self, prompt, meter):
            raise LLMError("provider")

    wire(FailingLLM(), FakeSearch(default=[]), {})
    response = run_live_verification(MESSAGE)
    # Deterministic fallback extracted claims; with no search results they abstain.
    assert response.claims, "fallback decomposition produced no claims"
    assert all(c.verdict == Verdict.INSUFFICIENT.value for c in response.claims)
    assert any(s.node == "decompose.fallback" for s in response.pipeline_trace)


def test_auth_errors_propagate_instead_of_degrading(wire):
    class AuthFailLLM:
        name = "fake:auth"
        def decompose(self, message, meter):
            raise LLMError("auth")
        def grade(self, prompt, meter):
            raise LLMError("auth")

    wire(AuthFailLLM(), FakeSearch(default=[]), {})
    with pytest.raises(LLMError):
        run_live_verification(MESSAGE)


def test_hallucinated_source_spans_are_dropped(wire):
    llm = FakeLLM(
        DecompositionResult(claims=[
            _claim("Cats must be licensed by 31 Aug.", "licensed by 31 Aug", ["q"]),
            _claim("The minister resigned yesterday over this.",
                   "the minister resigned yesterday", ["q2"]),  # span not in message
        ]),
        gradings=[GradingResult(grades=[_grade("c1", "e1", "supports")])],
    )
    wire(llm, FakeSearch(default=[_result("https://x.gov.sg/a", "t", "s")]),
         {"https://x.gov.sg/a": GOOD_PAGE})
    response = run_live_verification(MESSAGE)
    texts = [c.text for c in response.claims]
    assert not any("minister" in t for t in texts)


def test_invented_grade_pairs_are_ignored(wire):
    llm = FakeLLM(
        DecompositionResult(claims=[_claim(
            "Cats must be licensed by 31 Aug.", "licensed by 31 Aug", ["q"])]),
        gradings=[GradingResult(grades=[
            _grade("c1", "e1", "supports"),
            _grade("c9", "e7", "refutes"),  # pair the pipeline never created
        ])],
    )
    wire(llm, FakeSearch(default=[_result("https://x.gov.sg/a", "t", "s")]),
         {"https://x.gov.sg/a": GOOD_PAGE})
    response = run_live_verification(MESSAGE)
    assert response.claims[0].verdict == Verdict.SUPPORTED.value
    assert {c.id for c in response.claims} == {"c1"}


def test_failed_fetch_keeps_snippet_as_weak_evidence(wire):
    llm = FakeLLM(
        DecompositionResult(claims=[_claim(
            "Cats must be licensed by 31 Aug.", "licensed by 31 Aug", ["q"])]),
        gradings=[GradingResult(grades=[_grade("c1", "e1", "supports", conf=0.8)])],
    )
    search = FakeSearch(default=[_result(
        "https://x.gov.sg/blocked", "Licensing deadline",
        "Cats must be licensed by 31 Aug under the licensing scheme for cats.")])
    wire(llm, search, {})  # every fetch 404s
    response = run_live_verification(MESSAGE)
    assert response.evidence and response.evidence[0].from_full_page is False


def test_outdated_only_support_returns_outdated(wire):
    llm = FakeLLM(
        DecompositionResult(claims=[_claim(
            "Cats must be licensed by 31 Aug.", "licensed by 31 Aug", ["q"],
            status="deadline")]),
        gradings=[GradingResult(grades=[
            _grade("c1", "e1", "supports", temporal="outdated"),
        ])],
    )
    wire(llm, FakeSearch(default=[_result("https://x.gov.sg/a", "t", "s")]),
         {"https://x.gov.sg/a": GOOD_PAGE})
    response = run_live_verification(MESSAGE)
    assert response.claims[0].verdict == Verdict.OUTDATED.value


def test_usage_summary_is_present_and_safe(wire):
    llm = FakeLLM(
        DecompositionResult(claims=[_claim(
            "Cats must be licensed by 31 Aug.", "licensed by 31 Aug", ["q"])]),
        gradings=[GradingResult(grades=[_grade("c1", "e1", "supports")])],
    )
    wire(llm, FakeSearch(default=[_result("https://x.gov.sg/a", "t", "s")]),
         {"https://x.gov.sg/a": GOOD_PAGE})
    response = run_live_verification(MESSAGE)
    usage = next(s for s in response.pipeline_trace if s.node == "usage")
    assert set(usage.details) >= {
        "llmOperations", "llmRequests", "llmRetries",
        "searchOperations", "searchRequests", "searchRetries",
        "fetches", "inputTokens", "outputTokens", "cacheHits", "mode",
    }
    assert "ANTHROPIC" not in str(usage.details)


def test_conflicting_sources_trigger_refinement_reason(wire):
    llm = FakeLLM(
        DecompositionResult(claims=[_claim(
            "Cats must be licensed by 31 Aug.", "licensed by 31 Aug", ["q"],
            status="deadline")]),
        gradings=[
            GradingResult(grades=[
                _grade("c1", "e1", "supports", conf=0.8),
                _grade("c1", "e2", "refutes", conf=0.8),
            ], refined_queries={"c1": "authoritative check"}),
            GradingResult(grades=[_grade("c1", "e3", "supports", conf=0.9)]),
        ],
    )
    search = FakeSearch(results_by_query={
        "q": [_result("https://x.gov.sg/a", "A", "s"), _result("https://x.gov.sg/b", "B", "s")],
        "authoritative": [_result("https://x.gov.sg/c", "C", "s")],
    })
    wire(llm, search, {
        "https://x.gov.sg/a": GOOD_PAGE,
        "https://x.gov.sg/b": [("text", "The licensing deadline for cats was different, cats licensing detail text here.")],
        "https://x.gov.sg/c": [("text", "Official: cats must be licensed by 31 Aug. Licensing scheme confirmed for cats.")],
    })
    response = run_live_verification(MESSAGE)
    refine = [s for s in response.pipeline_trace if s.node == "retrieve.refine"]
    assert refine and "conflict" in refine[0].summary
