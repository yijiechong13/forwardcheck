# ForwardCheck SG — Learning Log

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

---

## Phase 3 — Deterministic pipeline

**What was built**
All seven nodes, the 19-document seeded corpus, and 25 pipeline tests. The three demo claims work
end to end with the verdicts the spec asks for.

**Files changed**
`backend/app/data/mock_sources.py`, `backend/app/pipeline/{normalise,decompose,route,retrieve,grade,freshness,verdict,runner}.py`,
`backend/app/services/retrieval_adapter.py`, `backend/app/tests/test_pipeline.py`.

**What RAG concept this phase teaches**

*Retrieval is the hard part, and lexical retrieval fails in a specific, learnable way.* Three
real bugs surfaced while building this, all of them retrieval bugs rather than reasoning bugs:

1. **Topical drift.** Querying with the claim alone matched "Rocky's owner has been charged"
   against cat-licensing documents, because "cat"/"animal" bridge unrelated clusters. Fixed by
   adding message-level context terms to every query, which anchors all claims to one event.
2. **Vocabulary mismatch on denials.** The document that settles the Rocky case says "no person
   has been charged" — phrased in official register, sharing almost no words with the forward.
   Pure BM25 will never retrieve it. This is the canonical case for dense retrieval; the
   deterministic stand-in is cluster-aware rebuttal expansion.
3. **Rank cutoff hiding the decisive document.** The statute defining the $5,000 *maximum* scored
   5th and fell outside `max_evidence_per_claim`, so the claim lost the only source that could
   distinguish "maximum" from "automatic". Fixed by guaranteeing the top exact-status match.

The general lesson: **a RAG system's failures are usually upstream of the model.** The grader was
never wrong in these cases — it was never shown the right document.

*A second lesson: the corpus must be able to not answer.* Two clusters deliberately stop one rung
short of the forwarded claim. If the evidence store can answer everything, abstention can never
be tested, and abstention is the behaviour that keeps the system honest.

**What to study next**
- Dense retrieval and hybrid search (reciprocal rank fusion) — bug 2 above is exactly what
  embeddings solve, and it is the strongest argument for adding pgvector.
- Cross-encoder reranking, which would replace the hand-tuned exact-status guarantee.
- NLI-based claim verification (entailment/contradiction), the learned version of `grade.py`.

**Trade-offs made**
- *Rules over an LLM.* Every verdict is explainable in one sentence and assertable in a test, and
  the app runs with no key. The cost is brittleness: `grade.py` recognises the escalation patterns
  it was taught, and a novel phrasing falls through to `does_not_answer`. That failure direction
  is deliberate — falling through to abstention is safe, falling through to support is not.
- *Cluster-aware retrieval expansion.* Honest about what it is: a stand-in for semantic search
  that works because the corpus is seeded and clustered. It would not survive a real corpus, and
  it is marked as such in the code.
- *Timeline restricted to the dominant cluster.* Found while testing: a weakly-matched document
  from the NS case was rendering "Charge ✓" on Rocky's timeline — a false confirmation sourced
  from an unrelated case, the exact error this product exists to prevent. Cheap guard, real bug.

---

## Phase 4 — Adapter-ready RAG structure

**What was built**
The three adapter interfaces with mock implementations, a domain allowlist for future live
search, `.env.example`, a `/config` endpoint, and 10 adapter contract tests.

**Files changed**
`backend/app/services/{llm_adapter,search_adapter}.py`, `backend/app/tests/test_adapters.py`,
`backend/.env.example`, `backend/app/main.py`.

**What RAG concept this phase teaches**

*Interfaces constrain what a model is allowed to do.* The important decision here is not that
there is an `LLMAdapter` — it is the shape of it. `classify()` takes a caller-supplied label set
and must return one of those labels; `complete()` is documented as prose-only and is never
allowed to produce a verdict. Verdicts stay in `verdict.py`, which is deterministic and testable.

That split is the difference between "RAG with an LLM in it" and "an LLM that sometimes reads
documents". If generation can decide the verdict, the system can talk itself into a conclusion
the evidence does not support — and you lose the ability to test it, because the output space is
unbounded.

*Allowlists are part of retrieval quality, not security theatre.* The verdict model rests on
tier weighting. A general web search returns pages with no defensible tier, so admitting them
means guessing an authority level, which corrupts every ranking downstream. Dropping
non-allowlisted domains is the cheaper and more honest option.

*Fail loudly on misconfiguration.* `FORWARDCHECK_LLM=anthropic` with no key raises rather than
silently falling back to mock. A run the operator believes is LLM-backed but is quietly
rule-based would invalidate any eval comparison drawn from it.

**What to study next**
- Anthropic tool-use with an enum schema — the mechanism that makes `classify()` genuinely closed
  rather than closed-by-prompt-instruction.
- Hybrid retrieval (RRF) for combining BM25 with pgvector, rather than replacing one with the other.
- Prompt caching, since every grading call would resend the same evidence snippets.

**Trade-offs made**
- *Mock adapters that do real work.* `MockLLMAdapter.classify()` scores keyword overlap instead of
  returning a constant, so it is a usable baseline for the eval harness. `MockLLMAdapter.complete()`
  deliberately returns "" — inventing prose there could only make the output less accurate, since
  everything user-visible is written from actual grades.
- *Unimplemented placeholders that raise.* `AnthropicLLMAdapter` and `WebSearchAdapter` exist as
  documented shapes with `NotImplementedError` bodies. They mark the seam and record the
  constraints without pretending to work.

---

## Phase 5 — Evaluation harness

**What was built**
A 6-case / 13-claim labelled dataset, a scoring harness computing the six EVAL_PLAN metrics,
a CLI report that gates on targets, and 11 eval tests. All targets met, zero critical errors.

**Files changed**
`backend/app/eval/harness.py`, `backend/app/tests/{eval_dataset.json,test_eval.py}`,
`backend/scripts/run_eval.py`, plus fixes in `retrieval_adapter.py`, `grade.py`, `verdict.py`.

**What RAG concept this phase teaches**

*The eval finds what testing does not.* Writing the harness immediately surfaced the worst bug in
the project: a message about **durian prices** returned **Supported**, cited to cat-licensing
documents. 42 unit tests were green at the time. The tests asserted behaviour on messages the
corpus covers; only the adversarial out-of-scope case exposed what happened when it did not.

The root cause is worth remembering, because it is a general RAG failure:
**score normalisation destroys the signal that nothing matched.** Retrieval normalised scores
against the best hit *in that query*, so the top result always scored 1.0 — whether it was a
perfect match or the least irrelevant document in the corpus. Relative relevance is not evidence
of relevance. The fix is an absolute floor before normalising, plus damping when the best raw
score is weak.

A second bug rode along: grading inferred support from ladder position alone ("deadline outranks
proposed, so it entails it"), without checking the document was about the same *matter*.
**Ladder position is not topical relevance.**

*Not all errors are equal.* The harness counts `critical_errors` separately — endorsing a false
claim, losing an escalation, or answering confidently where the gold label is abstain. Aggregate
accuracy would have let the durian bug hide behind a 92% average. It is asserted at zero.

**What to study next**
- RAGAS (faithfulness, answer relevance, context precision/recall) — the standard vocabulary for
  what this harness measures by hand.
- Calibration: whether the confidence numbers mean anything, which this eval does not yet test.
- Adversarial dataset construction — the two adversarial cases found more bugs than the three
  demo cases combined.

**Trade-offs made**
- *Six cases.* Enough to be a regression guard, nowhere near enough to be a generalisation
  estimate. Stated plainly in EVAL_PLAN.md rather than implied by a 100% score, which on a
  dataset this small mostly measures that the corpus was built for these cases.
- *Fuzzy claim matching by token overlap.* Necessary because the pipeline rewrites claims
  (subject carry-forward, scope splitting), so exact matching would measure phrasing rather than
  extraction. It will drift if wording changes substantially.
- *Targets that currently pass with headroom.* Deliberate: they are floors that catch regression,
  not stretch goals. The number that matters is critical errors at zero.

---

## Phase 6 — Polish

**What was built**
Rewrote the share-card corrections to state the actual correction rather than abstract status
language, added a backend-health indicator to the header, and finished the documentation set with
a demo script, screenshot instructions, roadmap, and stated limitations.

**Files changed**
`backend/app/pipeline/{grade,verdict}.py`, `frontend/src/app/page.tsx`, `README.md`.

**What RAG concept this phase teaches**
*The last mile is a product problem, not a retrieval problem.* The pipeline was already correct
when this phase started — every metric passed. But the share card said "source explicitly states
this status has not been reached", which is accurate and useless to someone in a group chat. The
fix was a lookup table mapping each denied status to a plain-language correction: "no conviction
has been recorded — the person has been charged but the case has not been decided".

That sentence *is* the product. Everything upstream — decomposition, ladders, retrieval, grading
— exists to be able to say it accurately. A verification system whose output nobody sends has
verified nothing.

**What to study next**
- Calibration: whether a claimed 0.86 confidence is right 86% of the time. Currently untested,
  and listed in the roadmap as such rather than quietly presented as meaningful.
- Human-subject evaluation: does a correction card actually change forwarding behaviour? No
  amount of retrieval accuracy answers that.

**Trade-offs made**
- *Hand-written rationales per status.* Clear and controllable, but a table that must be extended
  whenever a status is added. An LLM would generalise here — this is the strongest case in the
  codebase for `complete()`, and notably it is prose, not a verdict.
- *Stating limitations prominently in the README.* A 100% eval score on six cases invites
  overreading, so the README says plainly what the numbers do and do not mean.

---

## Scope change — ForwardCheck SG (Singapore-only, sharper positioning)

**What changed**
Two clarifications applied together: positioning narrowed to *public-status verification*
explicitly excluding scam/phishing detection, and jurisdiction narrowed to Singapore only.

Demo set restructured to **one example per status domain**, which is what the positioning
actually implies:

| Demo | Domain | Escalation it tests |
|---|---|---|
| HDB cat licensing | policy | maximum penalty → automatic fine; pet cats → all cats |
| Charged, or investigated? | legal | investigation → charge |
| Product recall | product safety | overseas → local; affected batch → whole line |
| Policy in force? | policy | passed → effective → enforced |

**Files changed**
`PROJECT_SPEC.md`, `DATA_SOURCES.md`, `ARCHITECTURE.md`, `EVAL_PLAN.md`, `README.md`,
`backend/app/models/status.py`, `backend/app/data/mock_sources.py`,
`backend/app/pipeline/{route,freshness}.py`, `backend/app/services/search_adapter.py`,
`backend/app/tests/{eval_dataset.json,test_adapters.py}`, `frontend/src/lib/{types,examples}.ts`,
`frontend/src/app/{page,layout}.tsx`, `frontend/src/components/InputPanel.tsx`.

**What RAG concept this phase teaches**

*Narrowing scope improves a RAG system measurably, not just aesthetically.* Dropping a
jurisdiction removed 8 domains from the allowlist and replaced a Malaysia cluster with two
Singapore ones. The corpus grew (19 → 23 documents) while the *ambiguity* shrank: there is now
one source hierarchy, so tier weighting means one thing, and every gold label can be checked
against a single set of authorities. Decomposition F1 rose from 0.897 to 0.941 — not because the
code got smarter, but because the eval set stopped straddling two regimes.

*One jurisdiction, but "Overseas" must survive.* The temptation was to delete every non-SG
jurisdiction. That would have broken a core check: refuting "recalled in Singapore" **requires**
evidence that the recall happened elsewhere. `Overseas` is a foil, not a second market, and the
enum comment says so — otherwise a future cleanup deletes it again.

*A timeline bug the new domains exposed.* The product-recall timeline initially showed no recall
at any stage. The claim "recalled in Singapore" retrieves the local advisories that refute it,
but never the overseas recall — the thing that actually happened. Drawing a timeline with
nothing found misrepresents the event as badly as the forward does, just in the other direction.
Fixed by letting the timeline include same-cluster documents no individual claim retrieved.

The general lesson: **per-claim retrieval and event-level narrative need different evidence
sets.** Grading asks "what speaks to this claim"; the timeline asks "what happened". Those are
not the same query, and using one answer for both loses information.

**What to study next**
- Whether the status ladders transfer across jurisdictions unchanged. The pipeline is
  jurisdiction-agnostic; only the corpus and allowlist are SG-specific, which suggests adding a
  second jurisdiction is a data problem rather than an architecture problem. Worth testing
  rather than assuming.
- Multilingual decomposition — Singapore forwards circulate in Chinese, Malay, and Tamil, and
  the regex-based decomposer is English-only by construction.

**Trade-offs made**
- *Kept Rocky as a Singapore case.* The brief suggested de-emphasising it as a Malaysia example,
  but its evidence cluster was already AVS/AGC — a Singapore case throughout. It is the cleanest
  demonstration of investigation-vs-charge in the corpus, so it stayed and was relabelled
  "Charged, or investigated?" to lead with the distinction rather than the animal.
- *Four examples instead of three.* Adds a row to the UI grid, but one demo per status domain
  means a reviewer sees all three ladders without typing anything.
- *`scamshield.gov.sg` retained in the allowlist.* It is a legitimate official SG source for
  checking whether an advisory exists. Annotated in-code as source authenticity, not scam
  detection, so the distinction survives the next reader.

---

## Refinement — scope and modality axes, five Singapore demo cases

**What was built**
Four new evidence clusters (CDC vouchers, vaping penalties, infant formula recall, calamine
recall), a `ClaimAxis` model, scope/modality grading rules, decomposition for compound and causal
claims, human-readable router labels, and 27 new tests. Corpus 23 → 38 documents; eval 7 → 10
cases, 16 → 24 gold claims.

**Files changed**
`backend/app/models/status.py`, `backend/app/data/mock_sources.py`,
`backend/app/pipeline/{decompose,route,grade,retrieve}.py`,
`backend/app/tests/{test_scope_modality.py,eval_dataset.json}`,
`frontend/src/lib/{examples,types,verdict}.ts`, `frontend/src/app/page.tsx`, all five docs.

**What RAG concept this phase teaches**

*Status was one axis of three.* The original model said a forwarded claim overstates the **stage**
an event reached. The five new cases showed that is a third of the problem. A claim can also
overstate **scope** (one batch → all products; per household → per person) and **modality**
(up to $5,000 on conviction → automatically fined). These are independent: *"anyone caught
automatically gets 10 years"* gets the status rung exactly right and is still false twice over.
A one-axis model passes those as Supported.

*The bug this exposed was structural, not a missing rule.* Grade rule 4 treated a matching
`status_asserted` as evidence the claim was **true**. It is not — it means the document is **on
topic**. A source labelled `eligibility` "supported" *PRs are also eligible* purely by being
about eligibility, and a news article containing the word "toxins" *because it was denying them*
supported *the product contains toxins*. Three false `Supported` verdicts, all from one
conflation.

Two guards fixed it, and both generalise beyond this corpus:

1. **Specificity requirement.** For scope-shaped statuses (`eligibility`, `recall_scope`,
   `deadline`, `penalty`) the specifics *are* the claim, so support additionally requires the
   claim's distinctive terms to appear in the source.
2. **Bounded/unbounded guard.** A source that bounds a fact ("three specified batches") can never
   *support* a claim that unbounds it ("all milk powder"), even when both carry the same status
   label. It refutes it.

*Lexical retrieval fails on vocabulary, not on relevance.* The formula cluster was invisible to
the claim "all NAN and Dumex **milk powder**" because the corpus said "infant **formula**" — zero
shared content words for two documents about the same event. The fix was making the mock
documents use the vocabulary real advisories use, which is realism rather than tuning: a real SFA
notice always names the product form. In production this is precisely what dense retrieval buys.

*Citations must come from the right case.* Three recall clusters share "recall", "batch",
"product"; "10 years jail" matches any statute with that maximum. Verdicts were right while
citing the wrong case — indefensible in a tool whose entire output is citations. Fixed by
resolving the cluster once from the whole message (which names its subject) and biasing claims
toward it. A new test asserts ≥50% of cited evidence shares one topic.

**What to study next**
- Natural Language Inference for the bounded/unbounded relation. Every scope rule here is a
  hand-written entailment pair, which is exactly what an NLI model learns.
- Quantifier scope in semantics — "all", "every", "any" are the linguistic core of this problem
  and there is real literature on parsing them.
- Reranking, which would replace the cluster-bias heuristic with something corpus-independent.

**Trade-offs made**
- *Scope rules as declarative pairs.* `_SCOPE_MISMATCHES` pairs claim-side over-generalisation
  with source-side bounding language in a table rather than scattering regexes through the
  grader. Readable and extendable, but still an enumeration — novel phrasing abstains.
- *Cluster bias down-weights rather than filters.* An out-of-cluster document can be the right
  evidence (an overseas recall refuting a local claim), so a strong cross-cluster match can still
  win. Filtering would have been simpler and wrong.
- *Two recall clusters instead of one.* Batch over-generalisation is the most common
  product-safety forward, and one instance is not enough to show a pattern holds rather than
  being fitted.
