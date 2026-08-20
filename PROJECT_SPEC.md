# ForwardCheck — Project Specification

## One-line

ForwardCheck verifies **forwarded news/status claims** circulating in Singapore and Malaysia
WhatsApp/Telegram groups, using a structured, agentic RAG-style evidence pipeline.

## What this is NOT

- Not a general-purpose chatbot.
- Not an "ask an LLM if this is true" wrapper.
- Not a universal internet fact-checker.

## What this IS

A **structured verification workflow** for a narrow, high-value failure mode:
**status escalation** in forwarded messages.

Forwarded messages rarely invent events from nothing. They usually take a *real* event and
**escalate its status** by one or more stages. ForwardCheck exists to catch exactly that.

### Status-escalation errors we target

| Real status | Forwarded (escalated) claim |
|---|---|
| investigated | charged |
| charged | convicted |
| convicted | sentenced (specific term) |
| maximum penalty | automatic sentence |
| overseas recall | Singapore/Malaysia recall |
| proposed policy | passed / enforced policy |
| advisory | ban |
| rumour / allegation | official confirmation |

## MVP scope

Singapore and Malaysia public-interest claims in three domains:

1. **Legal / news status** — arrested, investigated, charged, convicted, sentenced, released, bailed
2. **Product / public safety status** — recalled, banned, advisory, warning, overseas-only, local recall
3. **Policy / regulatory status** — proposed, passed, effective, enforced, deadline, fine

Anything outside these domains should be routed to `insufficient_evidence` rather than guessed at.

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
3. **Decompose** — split into atomic, individually checkable claims.
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
| `primary` | 1.00 | statutes, court records, gazette |
| `official` | 0.90 | gov.sg, AVS/NParks, HSA, SFA, PDRM, KPDN |
| `credible_news` | 0.65 | CNA, Straits Times, Bernama, The Star, FMT, NST |
| `secondary` | 0.30 | blogs, aggregators, social posts |

## Non-goals for MVP

- No authentication, no user accounts.
- No live scraping.
- No required API keys — the app runs fully offline in mock mode.
- No production deployment work.

## Honesty constraint

All bundled evidence is **seeded mock evidence**, clearly labelled as such in the API
(`isMock: true`) and in the UI. URLs are placeholders. ForwardCheck must never present a
fabricated citation as a real one.
