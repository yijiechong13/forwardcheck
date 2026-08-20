"""Retrieval adapter.

The interface is the point of this file. `MockRetrievalAdapter` implements
lexical (BM25-style) scoring over the in-memory seeded corpus; a future
`PgVectorRetrievalAdapter` implements the same two methods against Postgres +
pgvector, and no pipeline code changes.

TODO(pgvector): implement PgVectorRetrievalAdapter.
  - table: evidence(id, title, publisher, tier, jurisdiction, published_at,
           url, snippet, status_asserted, embedding vector(1024))
  - query: embed the claim, then
           SELECT ... ORDER BY embedding <=> $1 LIMIT k
  - hybrid: combine dense similarity with this BM25 score (reciprocal rank
           fusion) rather than replacing it — lexical matching is what catches
           exact status words like "convicted", which is precisely what this
           product cares about and what dense retrieval tends to smooth over.
"""

from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from collections import Counter

from app.config import settings
from app.data.mock_sources import ALL_EVIDENCE, topic_of
from app.models.schemas import Evidence, TIER_WEIGHT, SourceTier

_TOKEN = re.compile(r"[a-z0-9$][a-z0-9'$,.-]*")

# Very common words carry no retrieval signal but do inflate scores.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at", "for",
    "with", "by", "from", "is", "are", "was", "were", "be", "been", "being",
    "has", "have", "had", "will", "would", "shall", "should", "may", "might",
    "can", "could", "must", "that", "this", "these", "those", "it", "its",
    "as", "if", "than", "then", "there", "their", "they", "he", "she", "his",
    "her", "who", "which", "what", "all", "any", "no", "not", "more", "up",
}


def tokenise(text: str) -> list[str]:
    return [
        token.strip(".,")
        for token in _TOKEN.findall(text.lower())
        if token not in _STOPWORDS and len(token) > 1
    ]


#: Statuses that answer a question about each other. A document asserting a
#: charge is highly relevant to a claim of conviction (it is the adjacent rung),
#: and a statute defining a penalty answers a claim about a fine.
_RELATED_STATUS: dict[str, tuple[str, ...]] = {
    "investigation": ("allegation", "arrest", "charge", "statement"),
    "arrest": ("investigation", "charge", "allegation"),
    "charge": ("conviction", "sentence", "arrest", "investigation"),
    "conviction": ("charge", "sentence"),
    "sentence": ("charge", "conviction", "penalty"),
    "statement": ("investigation", "charge", "allegation"),
    "penalty": ("sentence", "enforced", "effective"),
    "effective": ("deadline", "passed", "enforced", "penalty"),
    "deadline": ("effective", "passed"),
    "passed": ("proposed", "effective"),
    "proposed": ("passed",),
    "enforced": ("penalty", "effective"),
    "advisory": ("warning", "overseas_recall", "local_recall", "ban"),
    "warning": ("advisory", "local_recall", "ban"),
    "overseas_recall": ("local_recall", "advisory", "ban"),
    "local_recall": ("overseas_recall", "ban", "advisory"),
    "ban": ("local_recall", "advisory", "warning"),
}


class RetrievalAdapter(ABC):
    """Retrieve candidate evidence for a claim."""

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        limit: int = 4,
        jurisdiction: str | None = None,
        status_hint: str | None = None,
    ) -> list[tuple[Evidence, float]]:
        """Return (document, score) pairs, best first. Score in [0, 1]."""

    @abstractmethod
    def corpus_size(self) -> int: ...


class MockRetrievalAdapter(RetrievalAdapter):
    """BM25-style lexical retrieval over the seeded in-memory corpus.

    Lexical rather than dense on purpose: with 19 documents, embeddings would
    add a dependency and an API key without improving recall, and exact status
    terms ("convicted", "advisory") are exactly what must match precisely.
    """

    K1 = 1.5  # term-frequency saturation
    B = 0.75  # length normalisation

    #: Raw BM25 floor below which the corpus is treated as not covering the
    #: query at all. Without this, relative normalisation would rank the least
    #: irrelevant document as a perfect match.
    MIN_ABSOLUTE_SCORE = 2.0

    #: Raw BM25 score representing a genuinely strong match. Best-hit scores
    #: below this damp the whole result set proportionally.
    WEAK_MATCH_SCORE = 6.0

    def __init__(self, corpus: list[Evidence] | None = None) -> None:
        self._corpus = corpus if corpus is not None else ALL_EVIDENCE
        self._docs: dict[str, list[str]] = {}
        for doc in self._corpus:
            # Title and asserted status are weighted by repetition — a cheap
            # field-boost that keeps the scorer to one code path.
            text = (
                f"{doc.title} {doc.title} {doc.snippet} "
                f"{doc.publisher} {doc.status_asserted} {doc.status_asserted}"
            )
            self._docs[doc.id] = tokenise(text)

        self._avg_len = (
            sum(len(t) for t in self._docs.values()) / len(self._docs)
            if self._docs
            else 0.0
        )
        self._df = Counter()
        for tokens in self._docs.values():
            self._df.update(set(tokens))
        self._n = len(self._docs)

    def corpus_size(self) -> int:
        return self._n

    def _idf(self, term: str) -> float:
        df = self._df.get(term, 0)
        # BM25 IDF with +1 smoothing so a term in every doc scores ~0, not negative.
        return math.log(1 + (self._n - df + 0.5) / (df + 0.5))

    def _bm25(self, query_tokens: list[str], doc_id: str) -> float:
        doc_tokens = self._docs[doc_id]
        if not doc_tokens:
            return 0.0
        counts = Counter(doc_tokens)
        length = len(doc_tokens)
        score = 0.0
        for term in query_tokens:
            tf = counts.get(term, 0)
            if not tf:
                continue
            numerator = tf * (self.K1 + 1)
            denominator = tf + self.K1 * (
                1 - self.B + self.B * length / (self._avg_len or 1)
            )
            score += self._idf(term) * numerator / denominator
        return score

    def search(
        self,
        query: str,
        *,
        limit: int = 4,
        jurisdiction: str | None = None,
        status_hint: str | None = None,
    ) -> list[tuple[Evidence, float]]:
        query_tokens = tokenise(query)
        if not query_tokens:
            return []

        raw: list[tuple[Evidence, float]] = []
        for doc in self._corpus:
            score = self._bm25(query_tokens, doc.id)

            # Status-aware boost. A claim about a *penalty* should surface the
            # statute that defines the penalty even when they share few words,
            # and a claim about a *charge* should prefer the charge/investigation
            # cluster over an unrelated document that happens to say "animal".
            # Applied as a multiplier on an existing lexical hit rather than as
            # a way to introduce documents the query never matched.
            if status_hint and score > 0:
                if doc.status_asserted == status_hint:
                    score *= 1.6
                elif status_hint in _RELATED_STATUS.get(doc.status_asserted, ()):
                    score *= 1.25

            if score <= 0:
                continue

            # Authority is applied *after* relevance, never blended into it:
            # an authoritative document about the wrong topic is still wrong.
            score *= TIER_WEIGHT[SourceTier(doc.tier)]

            # Mild boost for a matching jurisdiction; never a hard filter, since
            # an overseas source can be the very evidence that refutes a claim
            # of a local recall.
            if jurisdiction and doc.jurisdiction == jurisdiction:
                score *= 1.15

            raw.append((doc, score))

        if not raw:
            return []

        # Normalise to [0, 1] against the best hit so downstream thresholds are
        # stable regardless of query length.
        #
        # Relative normalisation alone is dangerous: it makes the top hit score
        # 1.0 even when *nothing* matched, so a query about durian prices scored
        # cat-licensing documents at 1.0 and the grader duly "supported" it.
        # An absolute floor is applied first — below it, the corpus genuinely
        # does not cover the query and the honest answer is no results at all.
        best = max(score for _, score in raw)
        if best < self.MIN_ABSOLUTE_SCORE:
            return []

        scored = [(doc, score / best) for doc, score in raw] if best > 0 else raw

        # Dampen the whole result set when even the best match is weak, so a
        # marginal top hit cannot present itself as a perfect one.
        if best < self.WEAK_MATCH_SCORE:
            damping = best / self.WEAK_MATCH_SCORE
            scored = [(doc, score * damping) for doc, score in scored]

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:limit]

    def topic_distribution(self, results: list[tuple[Evidence, float]]) -> dict:
        return dict(Counter(topic_of(doc) for doc, _ in results))


class PgVectorRetrievalAdapter(RetrievalAdapter):
    """Placeholder for the Postgres + pgvector implementation."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def search(
        self,
        query: str,
        *,
        limit: int = 4,
        jurisdiction: str | None = None,
        status_hint: str | None = None,
    ):
        raise NotImplementedError(
            "pgvector retrieval is not implemented. Run with "
            "FORWARDCHECK_RETRIEVAL=mock (the default)."
        )

    def corpus_size(self) -> int:
        raise NotImplementedError


def get_retrieval_adapter() -> RetrievalAdapter:
    if settings.retrieval_backend == "pgvector":  # pragma: no cover
        import os

        return PgVectorRetrievalAdapter(os.environ.get("DATABASE_URL", ""))
    return MockRetrievalAdapter()
