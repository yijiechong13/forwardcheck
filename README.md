# ForwardCheck

**Verify forwarded news claims before you pass them on.**

ForwardCheck checks forwarded WhatsApp/Telegram messages about Singapore and Malaysia
public-interest events, using a structured, agentic RAG-style evidence pipeline.

It is **not** a chatbot. It is a verification workflow built around one specific failure mode:
**status escalation**.

---

## The problem

Forwarded messages rarely invent an event from nothing. They take a *real* event and push its
status one or more rungs up a ladder:

| What actually happened | What the forward says |
|---|---|
| under investigation | **charged** |
| charged | **convicted** |
| maximum penalty is $5,000 | **you will be fined $5,000** |
| recalled overseas | **recalled in Singapore** |
| policy proposed | **policy in force** |
| advisory issued | **banned** |
| allegation | **officially confirmed** |

A generic fact-checker answers "true or false?" about the whole message — which is the wrong
question, because these messages are usually *partly* true. ForwardCheck decomposes the message
into atomic claims and gives each one its own verdict, evidence, and confidence.

## Status: Phase 1 (frontend mock UI)

The full result interface is built and running against static mock data. Backend follows in
Phase 2; see [LEARNING_LOG.md](LEARNING_LOG.md) for the running build log.

## Running the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 and load one of the three seeded examples.

## Documentation

| Document | What it covers |
|---|---|
| [PROJECT_SPEC.md](PROJECT_SPEC.md) | Scope, verdict vocabulary, output contract |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Pipeline graph, adapters, design decisions |
| [EVAL_PLAN.md](EVAL_PLAN.md) | Metrics, targets, critical-error definitions |
| [DATA_SOURCES.md](DATA_SOURCES.md) | Source authority tiers, SG/MY agencies, seeded evidence |
| [LEARNING_LOG.md](LEARNING_LOG.md) | Per-phase build log and RAG concepts |

## Tech stack

**Frontend** — Next.js, TypeScript, Tailwind CSS, black/grey/white design
**Backend** — FastAPI, Python, modular pipeline services
**RAG** — internal LangGraph-style graph abstraction, adapter interfaces for LLM / retrieval / search

## Running locally

Setup instructions land with Phase 1 (frontend) and Phase 2 (backend). The app is designed to
run **with no API keys** — all adapters default to mock mode.

## Evidence honesty

All bundled evidence is **seeded mock evidence**, hand-written to resemble real advisories and
labelled `isMock: true` in the API and UI. URLs are placeholders. ForwardCheck never presents a
fabricated citation as a real one.

## License

MIT
