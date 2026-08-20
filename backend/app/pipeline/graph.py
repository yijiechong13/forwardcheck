"""A minimal LangGraph-shaped pipeline abstraction.

Why hand-roll this instead of importing LangGraph now:

  * The MVP needs one linear path with no branching or cycles, and a 60-line
    runner makes that path completely legible to a reader.
  * No dependency is needed for the app to run.
  * The shape — typed state object, `(state) -> state` nodes registered on a
    graph, automatic trace capture — is deliberately the same, so swapping in
    real LangGraph later is a mechanical change rather than a rewrite.

Every node appends a `PipelineStep`, which is what powers the dev/eval panel.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

from app.models.schemas import Claim, Evidence, PipelineStep, TimelineEntry


@dataclass
class PipelineState:
    """State threaded through every node.

    Nodes mutate this in place and return it. Each field is written by exactly
    one node, which keeps data flow easy to follow.
    """

    raw_message: str

    # normalise
    normalised_message: str = ""
    normalisation_notes: dict = field(default_factory=dict)

    # decompose: (claim_text, source_sentence) pairs, before classification
    claim_drafts: list[tuple[str, str]] = field(default_factory=list)

    # route -> retrieve -> grade -> verdict
    claims: list[Claim] = field(default_factory=list)

    # retrieve: claim_id -> [(evidence, score)]
    retrieved: dict[str, list[tuple[Evidence, float]]] = field(default_factory=dict)

    # evidence actually cited, deduplicated, in retrieval order
    evidence: list[Evidence] = field(default_factory=list)

    # freshness
    stale_evidence_ids: list[str] = field(default_factory=list)

    # verdict
    overall_verdict: str = ""
    summary: str = ""
    confidence: float = 0.0
    timeline: list[TimelineEntry] = field(default_factory=list)
    shareable_correction: str = ""

    # observability
    trace: list[PipelineStep] = field(default_factory=list)

    def add_step(self, node: str, summary: str, duration_ms: int, details: dict) -> None:
        self.trace.append(
            PipelineStep(
                step=len(self.trace) + 1,
                node=node,
                summary=summary,
                duration_ms=duration_ms,
                details=details,
            )
        )


class Node(Protocol):
    """A pipeline node: takes state, mutates it, returns it.

    Nodes must not raise for ordinary "no result" cases — an empty retrieval is
    a valid outcome that downstream nodes turn into `Insufficient evidence`.
    """

    __name__: str

    def __call__(self, state: PipelineState) -> PipelineState: ...


@dataclass
class Graph:
    """Registers nodes and runs them in order, timing each one."""

    name: str
    nodes: list[tuple[str, Callable[[PipelineState], PipelineState]]] = field(
        default_factory=list
    )

    def add_node(
        self, name: str, fn: Callable[[PipelineState], PipelineState]
    ) -> "Graph":
        self.nodes.append((name, fn))
        return self

    def run(self, state: PipelineState) -> PipelineState:
        for name, fn in self.nodes:
            started = time.perf_counter()
            before = len(state.trace)
            state = fn(state)
            elapsed_ms = int((time.perf_counter() - started) * 1000)

            # Nodes normally record their own step (they know what to report).
            # Backfill timing so a node that forgets still shows up in the trace.
            if len(state.trace) == before:
                state.add_step(name, "completed", elapsed_ms, {})
            else:
                state.trace[-1].duration_ms = max(elapsed_ms, state.trace[-1].duration_ms)
        return state
