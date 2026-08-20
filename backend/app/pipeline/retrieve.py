"""Node 4 — retrieve.

Two details here do most of the work:

**Message-level context.** Retrieving on the claim text alone loses the topic.
"The owner is already facing court action" shares no distinctive words with the
right cluster, and "cats will be fined" drifts toward any document mentioning
cats. Each query is therefore the claim text *plus* distinctive terms from the
whole normalised message, which anchors every claim to the same event.

**A real threshold.** Evidence scoring below `retrieval_min_score` is dropped
rather than passed on weakly. A poor lexical match is worse than nothing: it
invites the grader to produce a confident verdict from an irrelevant document.
Dropping it is what produces honest `Insufficient evidence` outcomes.
"""

from __future__ import annotations

import time
from collections import Counter

import re

from app.config import settings
from app.data.mock_sources import ALL_EVIDENCE, topic_of
from app.models.schemas import Evidence
from app.models.status import Jurisdiction
from app.pipeline.graph import PipelineState
from app.services.retrieval_adapter import get_retrieval_adapter, tokenise


def _message_context(message: str, limit: int = 12) -> str:
    """Distinctive terms from the whole message, used to anchor every query.

    Frequency-ordered rather than positional: the words repeated across a
    forwarded message are what identify the event it is about.
    """
    counts = Counter(tokenise(message))
    return " ".join(term for term, _ in counts.most_common(limit))


#: Documents that deny a status, keyed by the status they deny. Derived from
#: the same negation patterns the grader uses, so the two nodes cannot drift.
_DENIAL_PATTERNS: dict[str, str] = {
    "charge": (
        r"\bno\s+(?:person|one)\s+has\s+been\s+charged\b"
        r"|\bno\s+charges?\s+(?:have\s+)?been\s+(?:filed|brought|laid)\b"
        r"|\bdecision\s+on\s+charges\s+has\s+not\s+been\s+made\b"
    ),
    "conviction": (
        r"\bno\s+conviction\s+has\s+been\s+recorded\b"
        r"|\bhas\s+not\s+been\s+convicted\b|\bno\s+plea\s+has\s+been\s+taken\b"
    ),
    "sentence": (
        r"\bhas\s+not\s+passed\s+sentence\b|\bnot\s+been\s+sentenced\b"
    ),
    "local_recall": (
        r"\bno\s+recall\s+has\s+been\s+issued\s+locally\b"
        r"|\bhas\s+not\s+been\s+recalled\b"
    ),
    "ban": r"\bhas\s+not\s+been\s+(?:banned|prohibited)\b|\bis\s+not\s+a\s+ban\b",
}


def _find_cluster_rebuttal(
    claim, kept: list[tuple[Evidence, float]]
) -> tuple[Evidence, float] | None:
    """A same-cluster document that explicitly denies the claimed status."""
    pattern = _DENIAL_PATTERNS.get(claim.status_type)
    if not pattern or not kept:
        return None

    kept_ids = {doc.id for doc, _ in kept}
    # The cluster is whatever the retrieved documents belong to.
    clusters = {topic_of(doc) for doc, _ in kept}

    for doc in ALL_EVIDENCE:
        if doc.id in kept_ids or topic_of(doc) not in clusters:
            continue
        if re.search(pattern, f"{doc.title}. {doc.snippet}", re.IGNORECASE):
            # Scored at the threshold: it earned inclusion by relevance to the
            # question, not by lexical similarity, and should not outrank
            # documents that matched the claim directly.
            return (doc, settings.retrieval_min_score)
    return None


def retrieve(state: PipelineState) -> PipelineState:
    started = time.perf_counter()
    adapter = get_retrieval_adapter()
    context = _message_context(state.normalised_message or state.raw_message)

    per_claim: dict[str, list[str]] = {}
    dropped_below_threshold: dict[str, int] = {}
    expanded: dict[str, str] = {}

    for claim in state.claims:
        jurisdiction = (
            claim.jurisdiction
            if claim.jurisdiction != Jurisdiction.UNKNOWN.value
            else None
        )

        results = adapter.search(
            f"{claim.text} {context}",
            limit=settings.max_evidence_per_claim + 2,
            jurisdiction=jurisdiction,
            status_hint=claim.status_type,
        )

        above_threshold = [
            (doc, score)
            for doc, score in results
            if score >= settings.retrieval_min_score
        ]
        kept = above_threshold[: settings.max_evidence_per_claim]

        # Guarantee the best exact-status match survives the cut. A claim about
        # a penalty must see the statute that defines the penalty even when
        # several topically-closer documents outrank it — that statute is
        # usually the only thing that can distinguish "maximum" from
        # "automatic", which is the whole point of the check.
        exact = next(
            (
                pair
                for pair in above_threshold
                if pair[0].status_asserted == claim.status_type
            ),
            None,
        )
        if exact is not None and exact not in kept:
            kept = kept[: settings.max_evidence_per_claim - 1] + [exact]

        # Pull in a same-cluster document that explicitly denies the claimed
        # status, if one exists and lexical scoring missed it.
        #
        # This is the retrieval failure this corpus is designed to expose: the
        # document reading "no person has been charged" shares almost no
        # vocabulary with "Rocky's owner has been charged", because denials are
        # phrased in official register rather than the forward's wording. A
        # purely lexical retriever will never surface the one document that
        # settles the question. Cluster-aware expansion is the deterministic
        # stand-in for what a dense retriever would do here.
        rebuttal = _find_cluster_rebuttal(claim, kept)
        if rebuttal is not None:
            kept = kept[: settings.max_evidence_per_claim - 1] + [rebuttal]
            expanded[claim.id] = rebuttal[0].id

        dropped_below_threshold[claim.id] = len(results) - len(above_threshold)
        state.retrieved[claim.id] = kept
        per_claim[claim.id] = [doc.id for doc, _ in kept]

    # Deduplicate into the response-level evidence list, preserving best-first
    # order so the UI shows the strongest sources at the top.
    seen: set[str] = set()
    for claim in state.claims:
        for doc, _ in state.retrieved.get(claim.id, []):
            if doc.id not in seen:
                seen.add(doc.id)
                state.evidence.append(doc)

    state.add_step(
        node="retrieve",
        summary=(
            f"Retrieved {len(state.evidence)} unique document(s) across "
            f"{len(state.claims)} claim(s) from a corpus of {adapter.corpus_size()}"
        ),
        duration_ms=int((time.perf_counter() - started) * 1000),
        details={
            "perClaim": per_claim,
            "contextTerms": context,
            "corpusSize": adapter.corpus_size(),
            "minScore": settings.retrieval_min_score,
            "droppedBelowThreshold": dropped_below_threshold,
            "clusterExpansion": expanded,
        },
    )
    return state
