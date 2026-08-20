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
