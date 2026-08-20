"""Assembles and runs the verification graph."""

from __future__ import annotations

from datetime import datetime, timezone

from app.config import settings
from app.models.schemas import VerifyResponse
from app.pipeline.decompose import decompose
from app.pipeline.freshness import freshness
from app.pipeline.grade import grade
from app.pipeline.graph import Graph, PipelineState
from app.pipeline.normalise import normalise
from app.pipeline.retrieve import retrieve
from app.pipeline.route import route
from app.pipeline.verdict import verdict


def build_graph() -> Graph:
    """The verification graph.

    Linear by design: each node depends on everything before it, and there is
    no branch a forwarded message can take that skips a stage. Retrieval
    returning nothing is handled *inside* grade/verdict as an abstention rather
    than as an early exit, which keeps the trace complete and comparable across
    messages — you can always see that retrieval ran and found nothing.
    """
    return (
        Graph(name="forwardcheck-verification")
        .add_node("normalise", normalise)
        .add_node("decompose", decompose)
        .add_node("route", route)
        .add_node("retrieve", retrieve)
        .add_node("grade", grade)
        .add_node("freshness", freshness)
        .add_node("verdict", verdict)
    )


def run_pipeline(message: str) -> PipelineState:
    """Run the graph and return raw state. Used by tests and the eval harness."""
    return build_graph().run(PipelineState(raw_message=message))


def run_verification(message: str) -> VerifyResponse:
    # Mode dispatch: live mode runs the retrieval-grounded pipeline; mock mode
    # (the default) runs the deterministic pipeline over the seeded corpus.
    if settings.is_live:
        from app.pipeline.live import run_live_verification

        return run_live_verification(message)

    state = run_pipeline(message)

    if not state.claims:
        # Nothing checkable survived decomposition — say so rather than
        # inventing a verdict about a message with no verifiable content.
        return VerifyResponse(
            overall_verdict="Insufficient evidence",
            summary=(
                "No checkable factual claims were found in this message. "
                "ForwardCheck verifies statements about the status of events, "
                "such as charges, recalls, or policy changes."
            ),
            confidence=0.2,
            claims=[],
            evidence=[],
            timeline=[],
            shareable_correction=(
                "I ran this through a checker — there's no specific factual "
                "claim in it to verify."
            ),
            pipeline_trace=state.trace,
        )

    return VerifyResponse(
        overall_verdict=state.overall_verdict,
        summary=state.summary,
        confidence=state.confidence,
        last_checked=datetime.now(timezone.utc).isoformat(),
        claims=state.claims,
        evidence=state.evidence,
        timeline=state.timeline,
        shareable_correction=state.shareable_correction,
        pipeline_trace=state.trace,
    )
