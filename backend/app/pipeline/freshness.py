"""Node 6 — freshness.

Two jobs:

**Staleness.** Evidence older than the configured threshold is flagged. A claim
whose only support is stale evidence should not be reported as confidently
current — that is how `Outdated` verdicts arise rather than false `Supported`ones.

**Status timeline.** Builds the chronological ladder for the message's dominant
domain, marking each rung found or missing. The missing rungs are the point: the
visible gap between "charged" and "convicted" is usually the whole story.
"""

from __future__ import annotations

import time
from collections import Counter
from datetime import date, datetime

from app.config import settings
from app.data.mock_sources import ALL_EVIDENCE, topic_of
from app.models.schemas import Evidence, TimelineEntry
from app.models.status import (
    Domain,
    LADDERS,
    STATUS_DOMAIN,
    StatusType,
    human_label,
)
from app.pipeline.graph import PipelineState

#: Prose for each rung, used when no evidence was found for it.
_ABSENT_DESCRIPTION: dict[StatusType, str] = {
    StatusType.ALLEGATION: "No allegation on record in the available evidence.",
    StatusType.INVESTIGATION: "No investigation reported in the available evidence.",
    StatusType.ARREST: "No arrest reported in the available evidence.",
    StatusType.STATEMENT: "No official statement found in the available evidence.",
    StatusType.CHARGE: "No charge has been filed according to the available evidence.",
    StatusType.CONVICTION: "No conviction recorded in the available evidence.",
    StatusType.SENTENCE: "No sentence passed according to the available evidence.",
    StatusType.PROPOSED: "No proposal stage found in the available evidence.",
    StatusType.PASSED: "No record that this was passed or announced.",
    StatusType.EFFECTIVE: "No record that this has taken effect.",
    StatusType.DEADLINE: "No deadline stated in the available evidence.",
    StatusType.ENFORCED: "No enforcement action found in the available evidence.",
    StatusType.PENALTY: "No penalty imposed according to the available evidence.",
    StatusType.ADVISORY: "No advisory found in the available evidence.",
    StatusType.WARNING: "No warning found in the available evidence.",
    StatusType.OVERSEAS_RECALL: "No overseas recall found in the available evidence.",
    StatusType.LOCAL_RECALL: "No local recall found in the available evidence.",
    StatusType.BAN: "No ban found in the available evidence.",
}


def _parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _dominant_domain(state: PipelineState) -> Domain:
    """The domain most of the claims belong to; ties resolve to the first."""
    counts = Counter(
        c.domain for c in state.claims if c.domain != Domain.UNKNOWN.value
    )
    if not counts:
        return Domain.UNKNOWN
    return Domain(counts.most_common(1)[0][0])


def freshness(state: PipelineState) -> PipelineState:
    started = time.perf_counter()
    today = date.today()

    # --- Staleness ---
    ages: dict[str, int] = {}
    for doc in state.evidence:
        published = _parse_date(doc.published_at)
        if published is None:
            continue
        age_days = (today - published).days
        ages[doc.id] = age_days
        if age_days > settings.stale_threshold_days:
            state.stale_evidence_ids.append(doc.id)

    # --- Timeline ---
    domain = _dominant_domain(state)
    ladder = LADDERS.get(domain, [])

    # Restrict the timeline to the message's dominant evidence cluster.
    #
    # This guard is essential, not cosmetic. Retrieval returns a pool of
    # documents across the whole corpus, and a weakly-matched document from an
    # unrelated case can assert a status the actual event never reached — which
    # would render a "Charge ✓" on the timeline sourced from someone else's
    # case. That is exactly the false confirmation this product exists to
    # prevent, so the timeline is built only from documents that carry the
    # weight of the message's own cluster.
    cluster_weights: Counter[str] = Counter()
    for claim in state.claims:
        for doc, score in state.retrieved.get(claim.id, []):
            cluster_weights[topic_of(doc)] += score
    dominant_cluster = (
        cluster_weights.most_common(1)[0][0] if cluster_weights else None
    )

    timeline_docs = [
        doc
        for doc in state.evidence
        if dominant_cluster is None or topic_of(doc) == dominant_cluster
    ]

    # Include same-cluster documents the *timeline* needs even when no single
    # claim retrieved them. A claim of "recalled in Singapore" retrieves the
    # local advisories that refute it, but the overseas recall — the thing that
    # actually happened — may never surface against that claim. Omitting it
    # would draw a timeline showing no recall anywhere, which misrepresents the
    # event just as badly as the forward does.
    if dominant_cluster is not None:
        known = {doc.id for doc in timeline_docs}
        for doc in ALL_EVIDENCE:
            if doc.id not in known and topic_of(doc) == dominant_cluster:
                timeline_docs.append(doc)

    # Best (earliest) document asserting each rung, from the dominant cluster.
    by_status: dict[str, list[Evidence]] = {}
    for doc in timeline_docs:
        by_status.setdefault(doc.status_asserted, []).append(doc)

    timeline: list[TimelineEntry] = []
    for stage in ladder:
        docs = by_status.get(stage.value, [])
        if docs:
            docs = sorted(docs, key=lambda d: d.published_at)
            timeline.append(
                TimelineEntry(
                    stage=stage,
                    label=human_label(stage),
                    date=docs[0].published_at,
                    found=True,
                    description=docs[0].title,
                    evidence_ids=[d.id for d in docs],
                )
            )
        else:
            timeline.append(
                TimelineEntry(
                    stage=stage,
                    label=human_label(stage),
                    date=None,
                    found=False,
                    description=_ABSENT_DESCRIPTION.get(
                        stage, "Not found in the available evidence."
                    ),
                    evidence_ids=[],
                )
            )

    state.timeline = timeline

    found_count = sum(1 for entry in timeline if entry.found)
    state.add_step(
        node="freshness",
        summary=(
            f"{len(state.stale_evidence_ids)} stale source(s); timeline covers "
            f"{found_count}/{len(timeline)} stage(s) of the {domain.value} ladder"
        ),
        duration_ms=int((time.perf_counter() - started) * 1000),
        details={
            "domain": domain.value,
            "dominantCluster": dominant_cluster,
            "timelineDocs": [d.id for d in timeline_docs],
            "staleThresholdDays": settings.stale_threshold_days,
            "staleEvidenceIds": state.stale_evidence_ids,
            "evidenceAgeDays": ages,
            "stagesFound": [e.stage for e in timeline if e.found],
            "stagesMissing": [e.stage for e in timeline if not e.found],
        },
    )
    return state
