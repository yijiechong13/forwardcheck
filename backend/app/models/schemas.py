"""API schemas for the /verify contract.

Serialised with camelCase aliases so the Next.js client can consume responses
directly with no mapping layer. `frontend/src/lib/types.ts` mirrors this file.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.status import Domain, Jurisdiction, StatusType


def _camel(field: str) -> str:
    head, *rest = field.split("_")
    return head + "".join(word.capitalize() for word in rest)


class ApiModel(BaseModel):
    """Base: snake_case in Python, camelCase on the wire, both accepted in."""

    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        use_enum_values=True,
    )


class Verdict(str, Enum):
    """The closed verdict vocabulary. Free-text verdicts cannot be evaluated."""

    SUPPORTED = "Supported"
    MISLEADING = "Misleading"
    FALSE = "False"
    OUTDATED = "Outdated"
    INSUFFICIENT = "Insufficient evidence"


class SourceTier(str, Enum):
    PRIMARY = "primary"
    OFFICIAL = "official"
    CREDIBLE_NEWS = "credible_news"
    SECONDARY = "secondary"


#: Retrieval scores are multiplied by these, so an official advisory outranks a
#: news summary of that advisory, which outranks a blog summary of the news.
TIER_WEIGHT: dict[SourceTier, float] = {
    SourceTier.PRIMARY: 1.0,
    SourceTier.OFFICIAL: 0.9,
    SourceTier.CREDIBLE_NEWS: 0.65,
    SourceTier.SECONDARY: 0.3,
}


class GradeLabel(str, Enum):
    SUPPORTS = "supports"
    REFUTES = "refutes"
    PARTIALLY_SUPPORTS = "partially_supports"
    DOES_NOT_ANSWER = "does_not_answer"


class EvidenceGrade(ApiModel):
    evidence_id: str
    label: GradeLabel
    rationale: str
    score: float = Field(ge=0.0, le=1.0)


class Claim(ApiModel):
    id: str
    text: str
    source_span: str
    status_type: StatusType
    domain: Domain
    jurisdiction: Jurisdiction
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    key_reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    grades: list[EvidenceGrade] = Field(default_factory=list)
    is_escalation: bool = False
    escalation_from: str | None = None
    escalation_to: str | None = None


class Evidence(ApiModel):
    id: str
    title: str
    publisher: str
    tier: SourceTier
    jurisdiction: Jurisdiction
    published_at: str
    url: str
    snippet: str
    status_asserted: StatusType
    #: True for seeded sample documents, False for live-retrieved evidence.
    #: Required, not conventional, so the UI cannot accidentally present
    #: sample data as a real citation (or vice versa).
    is_mock: bool = True
    #: False when the page fetch failed and only the search snippet was
    #: available — the UI marks such evidence as weaker.
    from_full_page: bool = True
    supports_claim_ids: list[str] = Field(default_factory=list)
    refutes_claim_ids: list[str] = Field(default_factory=list)


class TimelineEntry(ApiModel):
    stage: StatusType
    label: str
    date: str | None = None
    found: bool
    description: str
    evidence_ids: list[str] = Field(default_factory=list)


class PipelineStep(ApiModel):
    step: int
    node: str
    summary: str
    duration_ms: int
    details: dict = Field(default_factory=dict)


class VerifyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


class VerifyResponse(ApiModel):
    overall_verdict: Verdict
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    last_checked: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    claims: list[Claim] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    shareable_correction: str
    pipeline_trace: list[PipelineStep] = Field(default_factory=list)
    mock_notice: str = (
        "Evidence shown is seeded sample data for demonstration. "
        "URLs are placeholders, not real citations."
    )
