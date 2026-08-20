# ForwardCheck — Architecture

## System shape

```
                 ┌─────────────────────────────┐
   forwarded     │  Next.js frontend (TS/Tail)  │
   message  ───► │  InputPanel → results views  │
                 └──────────────┬───────────────┘
                                │ POST /verify
                 ┌──────────────▼───────────────┐
                 │  FastAPI  app/main.py        │
                 └──────────────┬───────────────┘
                                │
                 ┌──────────────▼───────────────┐
                 │  Pipeline graph (8 nodes)    │
                 │  normalise → decompose →     │
                 │  route → retrieve → grade →  │
                 │  freshness → verdict         │
                 └──────────────┬───────────────┘
                                │
                 ┌──────────────▼───────────────┐
                 │  Adapters (swappable)        │
                 │  LLM / Retrieval / Search    │
                 │  default = MOCK, no keys     │
                 └──────────────────────────────┘
```

## Why a pipeline, not a prompt

A single "is this true?" prompt gives you one opaque answer with no auditable middle.
ForwardCheck instead runs a **graph of small, individually testable nodes**. Each node has a
typed input and a typed output, appends a `PipelineTrace` step, and can be evaluated on its own.

This buys three things that matter for this problem:

1. **Per-claim granularity.** A forwarded message is usually *partly* true. One overall verdict
   destroys that information; a per-claim table preserves it.
2. **Auditability.** The dev panel shows which evidence IDs were retrieved and why each verdict
   was chosen. This is the difference between a demo and a system you can debug.
3. **Swappability.** Every external dependency sits behind an adapter, so the deterministic MVP
   and a future LLM-backed version share the same graph and the same tests.

## Pipeline nodes

| Node | File | Responsibility |
|---|---|---|
| normalise | `pipeline/normalise.py` | strip forwarding cruft/emoji, normalise dates + whitespace |
| decompose | `pipeline/decompose.py` | split into atomic checkable claims |
| route | `pipeline/route.py` | assign status type, domain, jurisdiction; drop non-checkable |
| retrieve | `pipeline/retrieve.py` | lexical retrieval over the evidence store, per claim |
| grade | `pipeline/grade.py` | supports / refutes / partial / no-answer, per (claim, evidence) |
| freshness | `pipeline/freshness.py` | evidence recency + status-timeline consistency |
| verdict | `pipeline/verdict.py` | per-claim verdict + confidence, aggregate overall verdict |

State flows through a single `PipelineState` object (`pipeline/graph.py`). This is a deliberate
LangGraph-shaped abstraction: nodes are `(state) -> state` functions registered on a `Graph`, so
porting to real LangGraph later is a mechanical change, not a rewrite.

## Adapters

| Adapter | Interface | Mock implementation | Future real implementation |
|---|---|---|---|
| `llm_adapter.py` | `LLMAdapter.complete()` / `.classify()` | deterministic rules | Anthropic Messages API |
| `retrieval_adapter.py` | `RetrievalAdapter.search()` | in-memory BM25-ish lexical | PostgreSQL + pgvector |
| `search_adapter.py` | `SearchAdapter.search()` | seeded, returns no live hits | Brave/Tavily + allowlist |

Selection is by env var, defaulting to mock:

```
FORWARDCHECK_LLM=mock|anthropic
FORWARDCHECK_RETRIEVAL=mock|pgvector
FORWARDCHECK_SEARCH=mock|web
```

## Key design decisions

**Deterministic core, LLM as an upgrade.** The MVP's grading is rule-based. That is not a
placeholder for lack of an API key — it is the reference implementation the eval harness scores
against. When the Anthropic adapter lands, we can measure whether it actually beats the rules.

**Status ladder as a first-class model.** `models/status.py` encodes legal/policy/safety status
as an ordered ladder. "Escalation" is then a computable property: the claim asserts a rung the
evidence does not reach. This is what makes the product more than keyword matching.

**Closed verdict vocabulary.** Five labels only. Free-text verdicts cannot be evaluated.

**Abstention is a real branch.** If retrieval returns nothing above threshold, the verdict is
`Insufficient evidence`. The eval harness scores abstention explicitly so that "confidently
wrong" regressions are visible.

**Mock evidence is labelled at the type level.** `EvidenceDoc.isMock` is a required field, not a
convention, so the UI cannot accidentally present sample evidence as real.
