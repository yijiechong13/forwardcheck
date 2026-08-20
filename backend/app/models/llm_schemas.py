"""Pydantic schemas for every structured LLM interaction.

These are passed to ``client.messages.parse(output_format=...)`` so the model's
JSON is validated by the SDK before the pipeline ever sees it. A response that
does not fit the schema raises, and the caller decides between one retry and a
safe fallback — malformed text is never accepted, and a verdict is never
invented from an unparseable reply.

Field constraints double as budget enforcement: ``max_length`` on the claims
list means even a misbehaving model cannot hand the pipeline more work than
the per-request budget allows.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Claim decomposition (+ query planning, same call — one LLM call, two jobs)
# ---------------------------------------------------------------------------

StatusTypeLiteral = Literal[
    "allegation", "investigation", "arrest", "statement", "charge",
    "conviction", "sentence", "release", "bail",
    "advisory", "warning", "overseas_recall", "local_recall", "ban",
    "recall_scope",
    "proposed", "passed", "effective", "enforced", "deadline", "penalty",
    "eligibility",
    "unknown",
]

DomainLiteral = Literal["legal", "product_safety", "policy", "unknown"]


class ExtractedClaim(BaseModel):
    claim_text: str = Field(min_length=8, max_length=300)
    #: Exact substring of the original message this claim came from. Validated
    #: against the message after parsing — a claim with no supporting span is
    #: discarded as a hallucinated extraction.
    source_span: str = Field(min_length=4, max_length=400)
    entities: list[str] = Field(default_factory=list, max_length=8)
    organisations: list[str] = Field(default_factory=list, max_length=6)
    locations: list[str] = Field(default_factory=list, max_length=4)
    dates: list[str] = Field(default_factory=list, max_length=6)
    amounts: list[str] = Field(default_factory=list, max_length=6)
    status_type: StatusTypeLiteral = "unknown"
    domain: DomainLiteral = "unknown"
    jurisdiction: Literal["Singapore", "Overseas", "Unknown"] = "Singapore"
    searchable: bool = True
    reason_not_searchable: str = ""
    #: 1–2 targeted queries for this claim, planned in the same call so query
    #: planning does not cost a second request.
    search_queries: list[str] = Field(default_factory=list, max_length=2)


class DecompositionResult(BaseModel):
    claims: list[ExtractedClaim] = Field(max_length=6)
    #: Non-factual content that was set aside (forward appeals, opinions,
    #: questions). Recorded for the trace, never verified.
    non_factual_content: list[str] = Field(default_factory=list, max_length=6)


# ---------------------------------------------------------------------------
# Evidence grading — batched: all (claim, passage) pairs in one call
# ---------------------------------------------------------------------------

class EvidenceGradeItem(BaseModel):
    claim_id: str
    evidence_id: str
    relationship: Literal[
        "supports", "refutes", "partially_supports", "does_not_answer"
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    matched_aspects: list[str] = Field(default_factory=list, max_length=6)
    contradicted_aspects: list[str] = Field(default_factory=list, max_length=6)
    missing_aspects: list[str] = Field(default_factory=list, max_length=6)
    temporal_status: Literal["current", "outdated", "unclear"] = "unclear"
    rationale: str = Field(max_length=400)
    #: Short exact excerpt from the evidence passage that grounds the grade.
    quoted_span: str = Field(default="", max_length=300)


class GradingResult(BaseModel):
    grades: list[EvidenceGradeItem] = Field(max_length=48)
    #: For claims whose evidence was insufficient or conflicting: one refined
    #: query each, so a second retrieval round costs no extra LLM call.
    refined_queries: dict[str, str] = Field(default_factory=dict)
