"""In-request evidence ranking for live retrieval.

Hybrid in the honest sense: lexical relevance plus deterministic boosts for
exact entity / date / amount matches, claim-status compatibility, source
authority, jurisdiction and freshness. There are no embeddings — nothing here
is semantic, and the README must not describe it as such.

Ordering principle: authority multiplies relevance, it never substitutes for
it. A relevant secondary source outranks an unrelated official page because an
irrelevant page scores ~0 lexical relevance and no multiplier can rescue it.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from app.models.llm_schemas import ExtractedClaim
from app.models.schemas import SourceTier, TIER_WEIGHT
from app.pipeline.chunk import Chunk
from app.services.retrieval_adapter import tokenise


def _lexical_overlap(claim_tokens: set[str], text: str) -> float:
    if not claim_tokens:
        return 0.0
    chunk_tokens = set(tokenise(text))
    return len(claim_tokens & chunk_tokens) / len(claim_tokens)


def _exact_match_boost(claim: ExtractedClaim, text: str) -> float:
    """Reward passages containing the claim's exact anchors."""
    lowered = text.lower()
    boost = 1.0
    for amount in claim.amounts:
        if amount and amount.lower() in lowered:
            boost += 0.35
    for entity in (claim.organisations + claim.entities)[:6]:
        if entity and len(entity) > 2 and entity.lower() in lowered:
            boost += 0.2
    for value in claim.dates:
        if value and value.lower() in lowered:
            boost += 0.2
    return min(boost, 2.2)


def _freshness_factor(published_at: str | None) -> float:
    """Newer documents get a mild edge; undated ones a mild discount."""
    if not published_at:
        return 0.9
    try:
        published = datetime.fromisoformat(published_at.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            published = datetime.strptime(published_at[:10], "%Y-%m-%d").date()
        except ValueError:
            return 0.9
    age_days = (date.today() - published).days
    if age_days < 0:
        return 0.9
    if age_days <= 180:
        return 1.1
    if age_days <= 720:
        return 1.0
    return 0.85


def rank_chunks(
    claim: ExtractedClaim, chunks: list[Chunk], *, limit: int
) -> list[tuple[Chunk, float]]:
    claim_tokens = set(tokenise(claim.claim_text))
    scored: list[tuple[Chunk, float]] = []
    seen_text: set[str] = set()

    for chunk in chunks:
        # Deduplicate materially identical passages across URLs.
        fingerprint = re.sub(r"\W+", "", chunk.text.lower())[:400]
        if fingerprint in seen_text:
            continue
        seen_text.add(fingerprint)

        relevance = _lexical_overlap(claim_tokens, chunk.text)
        if relevance <= 0.05:
            continue  # authority cannot rescue an irrelevant page

        score = relevance
        score *= _exact_match_boost(claim, chunk.text)
        try:
            score *= TIER_WEIGHT[SourceTier(chunk.tier)]
        except ValueError:
            score *= TIER_WEIGHT[SourceTier.SECONDARY]
        score *= _freshness_factor(chunk.published_at)
        if not chunk.from_full_page:
            score *= 0.6  # snippet-only evidence is weak by construction
        scored.append((chunk, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]
