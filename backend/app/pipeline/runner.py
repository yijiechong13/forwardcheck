"""Assembles and runs the verification graph.

Phase 2: returns a structurally valid stub response so the frontend can be
wired to a real endpoint. Phase 3 replaces the stub with the seven real nodes;
the signature and response shape do not change.
"""

from __future__ import annotations

from app.models.schemas import (
    Claim,
    EvidenceGrade,
    GradeLabel,
    TimelineEntry,
    Verdict,
    VerifyResponse,
)
from app.models.status import Domain, Jurisdiction, StatusType
from app.pipeline.graph import Graph, PipelineState


def build_graph() -> Graph:
    """The verification graph. Nodes are added in Phase 3."""
    return Graph(name="forwardcheck-verification")


def run_verification(message: str) -> VerifyResponse:
    state = PipelineState(raw_message=message)
    state = build_graph().run(state)
    return _stub_response(state)


def _stub_response(state: PipelineState) -> VerifyResponse:
    """Placeholder output — replaced by the real pipeline in Phase 3.

    Returns a deliberately abstaining verdict rather than a confident one:
    a stub that claims certainty is the exact failure this project exists to
    prevent, and it would make the UI look right while being wrong.
    """
    preview = state.raw_message.strip()
    claim_text = (preview[:120] + "…") if len(preview) > 120 else preview

    claim = Claim(
        id="c1",
        text=claim_text,
        source_span=claim_text,
        status_type=StatusType.UNKNOWN,
        domain=Domain.UNKNOWN,
        jurisdiction=Jurisdiction.UNKNOWN,
        verdict=Verdict.INSUFFICIENT,
        confidence=0.1,
        key_reason=(
            "Backend skeleton is live but the verification pipeline is not "
            "implemented yet (Phase 3)."
        ),
        evidence_ids=[],
        grades=[
            EvidenceGrade(
                evidence_id="none",
                label=GradeLabel.DOES_NOT_ANSWER,
                rationale="No retrieval has run.",
                score=0.0,
            )
        ],
    )

    return VerifyResponse(
        overall_verdict=Verdict.INSUFFICIENT,
        summary=(
            "The API is connected, but claim extraction and evidence retrieval "
            "are not implemented yet. No verdict can be given."
        ),
        confidence=0.1,
        claims=[claim],
        evidence=[],
        timeline=[
            TimelineEntry(
                stage=StatusType.UNKNOWN,
                label="Pipeline not implemented",
                date=None,
                found=False,
                description="Status timeline is constructed in Phase 3.",
                evidence_ids=[],
            )
        ],
        shareable_correction=(
            "ForwardCheck could not verify this message — the verification "
            "pipeline is still being built. Please do not treat this as a result."
        ),
        pipeline_trace=state.trace,
    )
