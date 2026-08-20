# ForwardCheck — Learning Log

A running record of what was built, what it teaches, and what to study next.

---

## Phase 0 — Project setup

**What was built**
Empty repo → structured project: git repository, backend/frontend folder skeleton, and the five
planning documents that constrain everything after them.

**Files changed**
`PROJECT_SPEC.md`, `ARCHITECTURE.md`, `EVAL_PLAN.md`, `DATA_SOURCES.md`, `LEARNING_LOG.md`,
`README.md`, `.gitignore`, `backend/app/**` (empty package dirs), `frontend/`.

**What RAG concept this phase teaches**
*Scope discipline.* The most common failure in RAG projects is an unbounded retrieval target —
"check any claim" means the corpus is the internet and the eval set is undefinable. By writing
PROJECT_SPEC.md first and restricting the system to **status verification in three domains
across two jurisdictions**, retrieval becomes tractable and evaluation becomes possible.

Also: *writing EVAL_PLAN.md before any code.* Defining the metric first stops the system from
being tuned to whatever it happens to do.

**What to study next**
- The LangGraph state-graph model (nodes, edges, typed state) before writing `graph.py`.
- BM25 vs dense retrieval, and why lexical retrieval is a reasonable MVP for a small corpus.

**Trade-offs made**
- *Docs before code.* Slower start, but the verdict vocabulary and output contract are fixed
  before anything depends on them.
- *Two jurisdictions, three domains.* Deliberately narrow. Breadth is the enemy of a measurable
  retrieval system.
- *Mock-first, keyless.* The app must run for a reviewer with no credentials. Cost: the MVP's
  intelligence is rule-based, so the rules must be good enough to be a real baseline.

---

## Phase 1 — Frontend mock UI

**What was built**
The complete result interface, running against a static fixture with no backend. Header, input
panel with seeded examples, overall verdict card, expandable claims table, evidence cards,
status timeline, shareable correction with copy, and a collapsible pipeline trace.

**Files changed**
`frontend/src/lib/{types,examples,mockData,verdict}.ts`,
`frontend/src/components/{ui,InputPanel,OverallVerdict,ClaimsTable,EvidenceCards,Timeline,ShareCorrection,PipelineTrace}.tsx`,
`frontend/src/app/{page,layout}.tsx`, `frontend/src/app/globals.css`, `frontend/next.config.ts`.

**What RAG concept this phase teaches**
*The output contract is the design.* Building the UI first forces you to decide exactly what a
RAG system must return before you build the retrieval. Rendering `EvidenceGrade`, `isEscalation`,
and a `found: false` timeline stage means the pipeline is now obliged to produce them — the
interface became the specification.

It also makes *abstention* visible as a design problem. "Insufficient evidence" needs a place to
live on screen, with a confidence bar that reads as low rather than as failure. Systems that do
not design for abstention end up avoiding it.

**What to study next**
- Faithfulness vs answer-relevance metrics (RAGAS), and how citation-linking constrains output.
- Why per-claim decomposition beats whole-document QA for verification tasks.

**Trade-offs made**
- *Static fixture over a live backend.* Lets the UI be finished and reviewed independently, at
  the cost of one throwaway `handleVerify` that Phase 2 replaces.
- *Tailwind v4 CSS-first theming.* Tokens live in `globals.css` via `@theme` rather than a JS
  config. Fewer files, but less familiar if you have only used Tailwind v3.
- *Monochrome with desaturated verdict accents.* Restraint reads as credible for a
  verification tool; the cost is that verdicts rely on text as much as colour, so labels are
  always spelled out rather than shown as a colour alone.

---

## Phase 2 — FastAPI backend skeleton

**What was built**
A running API with `/health` and `/verify`, the full Pydantic schema layer, the status-ladder
domain model, the graph abstraction, and seven contract tests. The frontend now calls the real
endpoint instead of a static import.

**Files changed**
`backend/app/{main,config}.py`, `backend/app/models/{schemas,status}.py`,
`backend/app/pipeline/{graph,runner}.py`, `backend/app/tests/test_api.py`,
`backend/requirements.txt`, `frontend/src/lib/api.ts`, `frontend/src/app/page.tsx`.

**What RAG concept this phase teaches**
*State-graph pipelines.* `graph.py` is a deliberately small version of what LangGraph gives you:
a typed state object, nodes as `(state) -> state` functions, and automatic trace capture. Writing
it by hand makes the pattern legible — a RAG pipeline is a sequence of state transformations,
each individually testable, not one opaque call.

Also *the honest stub*. The Phase 2 placeholder returns `Insufficient evidence` with confidence
0.1, not a plausible fake verdict. A stub that fabricates confidence makes the UI look finished
while being exactly the failure the product exists to prevent — and it hides the gap from you.

**What to study next**
- BM25 scoring and why tier weighting is applied after relevance, not blended into it.
- Pydantic alias generators, and where a typed contract stops errors the compiler cannot see.

**Trade-offs made**
- *Hand-rolled graph over importing LangGraph.* Zero dependencies and total legibility now;
  we give up branching, retries, and checkpointing, which is why the abstraction keeps
  LangGraph's shape so adopting it later is mechanical.
- *`use_enum_values=True`.* Responses carry plain strings, so the client needs no enum decoding.
  Cost: server-side code reads `.value` strings back out of dumped models rather than enums.
- *Contract tests separate from verdict quality.* These tests assert shape only. Verdict accuracy
  is deliberately deferred to the Phase 5 eval harness, so pipeline changes do not churn them.
