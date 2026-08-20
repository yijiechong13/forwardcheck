# ForwardCheck SG

**Verify forwarded claims before you pass them on.**

[github.com/yijiechong13/forwardcheck](https://github.com/yijiechong13/forwardcheck)

ForwardCheck SG is an agentic RAG web app that verifies forwarded public-interest claims by
decomposing them into status claims, retrieving official or credible evidence, and producing
source-backed verdicts with timelines.

It is **not** a chatbot, not an "ask an LLM if this is true" wrapper, and **not a scam or
phishing detector**. It answers one question: *what is officially or credibly confirmed about
this claim's status?*

Scope is **Singapore only** — one jurisdiction gives a controlled source hierarchy and an
evaluation set that can be labelled with confidence.

---

## The problem

Forwarded messages rarely invent an event from nothing. They take a *real* event and push its
status one or more rungs up a ladder:

| What actually happened | What the forward says |
|---|---|
| under investigation | **charged** |
| charged | **convicted** |
| maximum penalty is $5,000 | **you will be fined $5,000** |
| recalled overseas, specific batches | **recalled in Singapore, whole product** |
| policy passed in Parliament | **policy in force, fines start now** |
| advisory issued | **banned** |
| allegation | **officially confirmed** |

A generic fact-checker answers "true or false?" about the whole message — which is the wrong
question, because these messages are usually *partly* true. Telling someone their message is
"false" when the deadline in it is real gets the fact-check dismissed entirely.

ForwardCheck SG decomposes the message into atomic status claims and gives each one its own
verdict, evidence, and confidence.

### The three status domains

| Domain | Ladder | Example distinction |
|---|---|---|
| **Legal / news** | investigated → arrested → charged → convicted → sentenced | maximum penalty vs automatic sentence |
| **Policy / regulatory** | proposed → passed → effective → deadline → enforced | passed vs in force; all cats vs pet cats |
| **Product / public safety** | advisory → warning → overseas recall → local recall → ban | Singapore recall vs overseas-only; batch vs whole line |

### What it actually does

Paste this in:

> ⚠️ URGENT ⚠️ From 1 Sept, HDB cat owners with more than 2 cats will be fined $5,000 and AVS
> will remove the extra cats. All cats, including community cats, must be licensed by 31 Aug.
> Please forward to all cat owners 🐱🙏

And it returns:

| Claim | Verdict | Why |
|---|---|---|
| Cats must be licensed by 31 Aug | **Supported** | The licensing deadline is genuine |
| Owners with >2 cats will be fined $5,000 | **Misleading** | $5,000 is the *maximum* court penalty, not an automatic fine |
| AVS will remove the extra cats | **Misleading** | Source states owners will not be required to give up their animals |
| Community cats must be licensed | **Misleading** | Licensing covers owned pet cats; community cats are out of scope |

Plus a status timeline showing which stages the evidence actually reaches, and a share-ready
correction for the group chat it came from.

## Verdict vocabulary

Five labels, closed set: `Supported` · `Misleading` · `False` · `Outdated` · `Insufficient evidence`

**Abstention is a first-class outcome.** The system prefers "Insufficient evidence" over
inventing an answer, and the eval harness measures whether it actually does.

## Source hierarchy

| Tier | Sources |
|---|---|
| **Primary** | Singapore Statutes Online, court records |
| **Official** | gov.sg, SPF, AGC, AVS/NParks, HSA, SFA, MOM, MOH, ICA, CSA, MND, MINDEF |
| **Credible news** | CNA, The Straits Times, TODAY, Mothership, Mediacorp/Channel 8 |
| **Not proof** | blogs, aggregators, social posts, forwarded screenshots |

Secondary and social sources can show a claim is circulating; they never establish it is true.
Non-allowlisted domains are dropped rather than admitted at a guessed tier.

---

## Running locally

Two terminals. **No API keys required** — every adapter defaults to mock mode.

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**. API docs at http://localhost:8000/docs.

If the header shows "API OFFLINE", the backend is not running.

## Tests and evaluation

```bash
cd backend
.venv/bin/python -m pytest app/tests -v
```

```bash
cd backend && .venv/bin/python scripts/run_eval.py --verbose
```

The eval report scores six metrics against the targets in [EVAL_PLAN.md](EVAL_PLAN.md) and exits
non-zero if any target is missed or any **critical error** occurs — a critical error being a false
endorsement, a lost escalation, or a confident answer where the evidence does not support one.

Current: 56 tests passing, 7 eval cases across all three status domains, all targets met,
zero critical errors.

---

## Demo script

A four-minute walkthrough for a live demo. One example per status domain.

**1. Cat licensing** *(policy scope and penalty)*
Load the first example, verify. Point out the overall verdict is **Misleading**, not False —
one claim is genuinely **Supported**. This is the core argument for per-claim verdicts: calling
the whole message false would be its own inaccuracy, and would get the correction ignored.
The escalation badge reads `maximum penalty → automatic consequence`.

**2. Charged, or investigated?** *(the legal ladder)*
Load the second example. Nothing here is Supported — the evidence has an investigation and an
AGC review, and states no one has been charged. Open the **share card**: *"no one has been
charged — the case is still at the investigation or review stage"* is the distinction the whole
product exists to make. Scroll to the **timeline**: investigation and statement filled, charge
and conviction drawn as explicitly missing.

**3. Product recall** *(jurisdiction and scope)*
Load the third example. Two escalations at once — the recall was **overseas**, and it covered
**specific batches**, not the whole line. The timeline is the clearest artefact here: it shows
`Overseas recall ✓` and `Local recall ✗`. Something real happened; it just did not happen here.

**4. Policy in force?** *(the policy ladder)*
Load the fourth example. The law genuinely passed — and stops there. Timeline shows
`Proposed ✓ · Passed ✓ · In effect ✗ · Enforced ✗`. "Fines start immediately" asserts two rungs
the evidence never reaches.

**5. Developer trace**
Expand it on any result. Seven nodes, the evidence IDs each retrieved, and the rule that
produced the verdict. Point out `retrieve` → `clusterExpansion`: the document that settles the
Rocky case says "no person has been charged", which shares almost no vocabulary with the claim,
and pure lexical retrieval never finds it.

**6. Out of scope** *(the honesty check)*
Type something the corpus does not cover — durian prices, a made-up policy. It returns
**Insufficient evidence**, not a guess. This case is in the eval set precisely because an
earlier version got it wrong: it returned "Supported", cited to cat-licensing documents.

---

## Architecture

```
Next.js UI  ──POST /verify──>  FastAPI
                                  │
        normalise → decompose → route → retrieve → grade → freshness → verdict
                                  │
                    adapters: LLM · Retrieval · Search   (all mock by default)
```

Seven nodes, each `(state) -> state`, each appending a trace step. See
[ARCHITECTURE.md](ARCHITECTURE.md) for why a graph rather than a single prompt, and what the LLM
is and is not allowed to decide.

### Documentation

| Document | What it covers |
|---|---|
| [PROJECT_SPEC.md](PROJECT_SPEC.md) | Scope, verdict vocabulary, output contract |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Pipeline graph, adapters, design decisions |
| [EVAL_PLAN.md](EVAL_PLAN.md) | Metrics, targets, critical-error definitions |
| [DATA_SOURCES.md](DATA_SOURCES.md) | Authority tiers, SG/MY agencies, seeded evidence |
| [LEARNING_LOG.md](LEARNING_LOG.md) | Per-phase build log, RAG concepts, bugs found |

The learning log is the most useful file for understanding *why* the system looks like this —
it records the three retrieval bugs found during development and what each one teaches.

## Tech stack

**Frontend** — Next.js 16, TypeScript, Tailwind v4, monochrome design, light/dark
**Backend** — FastAPI, Pydantic v2, modular pipeline services
**RAG** — internal LangGraph-shaped graph, BM25 lexical retrieval with tier weighting, adapter
interfaces for Anthropic / pgvector / web search

## Evidence honesty

All bundled evidence is **seeded mock data**, hand-written to resemble real advisories and
labelled `isMock: true` in the API and the UI. URLs are placeholders. ForwardCheck SG never presents
a fabricated citation as a real one, and the test suite asserts it.

## Screenshots

To capture screenshots for a portfolio or README:

1. Start both servers, open http://localhost:3000.
2. Load the **HDB cat licensing** example and verify — it shows the widest range of verdicts on
   one screen (Supported + Misleading + escalation badges).
3. Capture the overall verdict card and claims table together.
4. Scroll to the **timeline** and capture it separately — the "NOT FOUND IN AVAILABLE EVIDENCE"
   markers are the most distinctive thing in the UI.
5. Expand the **developer trace** and capture one node's JSON detail.
6. Repeat in light and dark mode (the page follows your OS setting).

Save to `docs/screenshots/` and reference them here.

---

## Roadmap

| Next | Why it matters |
|---|---|
| **Anthropic API adapter** | Replace rule-based decomposition and grading. The rules are the control — the LLM ships only if it beats them on critical errors and abstention recall. |
| **pgvector + hybrid retrieval** | Fixes the documented failure where official denials ("no person has been charged") share no vocabulary with the claim. The strongest argument for embeddings in this codebase. |
| **Live web search** | Domain allowlist and tier mapping already exist in `search_adapter.py`. |
| **Telegram bot frontend** | Meet the message where it actually circulates — forward straight to a bot. |
| **Second jurisdiction** | The ladders and pipeline are jurisdiction-agnostic; only the corpus and allowlist are SG-specific. Adding one is a data problem, not an architecture problem. |
| **OCR for screenshots** | Most forwards arrive as screenshots, not text. |
| **Source freshness monitoring** | Re-check cached verdicts when a source updates; a charge becoming a conviction should invalidate the old answer. |
| **Confidence calibration** | The confidence numbers are currently uncalibrated heuristics. They should be measured before they are trusted. |

## Known limitations

- Evidence is seeded, so retrieval quality is measured against a corpus built for these cases.
  The eval numbers are **regression guards, not a generalisation estimate**.
- Rule-based grading recognises the escalation patterns it was taught; novel phrasing falls
  through to `does_not_answer`. That direction is deliberate — falling through to abstention is
  safe, falling through to support is not.
- English only. Singapore Chinese/Malay/Tamil forwards are out of MVP scope.
- Singapore only. The status ladders generalise, but the corpus and source hierarchy do not.
- Cluster-aware retrieval expansion works because the corpus is seeded and clustered. It would
  not survive a real corpus, and it is marked as such in the code.

## License

MIT
