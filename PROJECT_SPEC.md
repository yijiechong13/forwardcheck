# ForwardCheck SG — Project Specification

## One-line

ForwardCheck SG is an agentic RAG web app that verifies forwarded public-interest claims by
decomposing them into status claims, retrieving official or credible evidence, and producing
source-backed verdicts with timelines.

## What this is NOT

- Not a general-purpose chatbot.
- Not an "ask an LLM if this is true" wrapper.
- Not a universal internet fact-checker.
- **Not a scam or phishing detector.** Detecting malicious intent in a conversation is a
  different problem with different signals. ForwardCheck asks only: *what is officially or
  credibly confirmed about this claim's status?*

## What this IS

A **public-status verification tool** for forwarded public-interest claims, built around one
narrow, high-value failure mode: **status escalation**.

Forwarded messages rarely invent an event from nothing. They usually take a *real* event and
**escalate its status** by one or more stages. ForwardCheck SG exists to catch exactly that.

## Scope: Singapore only

The MVP verifies Singapore public-interest claims. This is a deliberate narrowing: a single
jurisdiction means a controlled source hierarchy, a tractable retrieval corpus, and an
evaluation set that can actually be labelled with confidence.

`Overseas` remains a representable jurisdiction, because refuting "recalled in Singapore"
requires evidence that the recall happened somewhere else. It is a foil, not a second market.

## The three status domains

### 1. Legal / news status

`investigated` → `arrested` → `charged` → `convicted` → `sentenced`

Distinctions that must hold:
- investigated vs charged
- charged vs convicted
- convicted vs sentenced
- maximum penalty vs automatic sentence
- suspect vs owner vs officer vs victim

### 2. Policy / regulatory status

`proposed` → `passed` → `effective` → `deadline` → `enforced` → `penalty`

Distinctions that must hold:
- proposed vs passed
- announced vs in force vs enforced
- a real deadline vs a misleading one
- a real fine vs an automatic fine
- scope conditions — all cats vs pet cats, existing owners vs new owners

### 3. Product / public-safety status

`advisory` → `warning` → `overseas_recall` → `local_recall` → `ban`

Distinctions that must hold:
- recalled in Singapore vs recalled overseas only
- advisory vs recall vs ban
- affected batch vs whole product line
- confirmed official warning vs a news report about one

## Status-escalation errors we target

| Real status | Forwarded (escalated) claim |
|---|---|
| investigated | charged |
| charged | convicted |
| convicted | sentenced (specific term) |
| maximum penalty | automatic sentence or fine |
| overseas recall | Singapore recall |
| affected batch | whole product line |
| advisory | ban |
| proposed policy | passed policy |
| passed policy | in force / enforced |
| rumour / allegation | official confirmation |

## Verdict labels (closed set)

- `Supported`
- `Misleading`
- `False`
- `Outdated`
- `Insufficient evidence`

**Abstention is a first-class outcome.** The system must prefer `Insufficient evidence`
over fabricating a confident answer. This is measured explicitly in the eval harness.

## Core user flow

1. User pastes a forwarded message.
2. **Normalise** — strip forwarding cruft, emoji, "FORWARD TO ALL", normalise whitespace/dates.
3. **Decompose** — split into atomic, individually checkable status claims.
4. **Route** — classify each claim by status type + domain + jurisdiction.
5. **Retrieve** — pull candidate evidence from the (mock) evidence store.
6. **Grade** — supports / refutes / partially supports / does not answer, per claim.
7. **Freshness** — check evidence recency and status-timeline consistency.
8. **Verdict** — per-claim verdict + confidence, then an aggregate overall verdict.

## Output contract

```
POST /verify  { "message": "..." }
->
{
  "overallVerdict", "summary", "confidence", "lastChecked",
  "claims": [...], "evidence": [...], "timeline": [...],
  "shareableCorrection", "pipelineTrace": [...]
}
```

## Source priority

Evidence is ranked by authority tier, and a higher tier can override a lower one:

| Tier | Weight | Examples |
|---|---|---|
| `primary` | 1.00 | Singapore Statutes Online, court records |
| `official` | 0.90 | gov.sg, SPF, AGC, AVS/NParks, HSA, SFA, MOM, MOH |
| `credible_news` | 0.65 | CNA, The Straits Times, TODAY, Mothership, Mediacorp/Channel 8 |
| `secondary` | 0.30 | blogs, aggregators, social posts |

**Secondary and social sources are never treated as proof.** They may indicate that a claim is
circulating; they cannot establish that it is true.

## Source authenticity — a supporting check, not a feature

ForwardCheck may check whether an announcement or link is *official* (a real gov.sg page rather
than a lookalike), because that is part of establishing whether an announcement happened. This
is scoped to verifying officiality. It is **not** scam detection and is not positioned as such.

## Non-goals for MVP

- No authentication, no user accounts.
- No live scraping.
- No required API keys — the app runs fully offline in mock mode.
- No production deployment work.
- No scam/phishing risk engine.

## Honesty constraint

All bundled evidence is **seeded mock evidence**, clearly labelled as such in the API
(`isMock: true`) and in the UI. URLs are placeholders. ForwardCheck must never present a
fabricated citation as a real one.
