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
