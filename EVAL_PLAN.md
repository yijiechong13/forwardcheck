# ForwardCheck SG — Evaluation Plan

A verification system that is never measured is just a demo. This plan defines what "working"
means before the implementation exists.

## Dataset

`backend/app/tests/eval_dataset.json` — each case has the raw forwarded message plus expected
extracted claims, status routing, verdicts, and whether citations are required.

Ten cases, 24 gold claims. Demo messages are **synthetic forwarded-style claims derived from
real Singapore public information**, not captured private messages.

| Case | Axis it stresses |
|---|---|
| `cat-licensing` | modality (maximum vs automatic) + scope (pet vs community cats) |
| `cdc-vouchers` | scope (household vs individual), form (vouchers vs cash), abstention (PRs, deadline) |
| `vaping-penalties` | modality (statutory maximum vs automatic jail) |
| `formula-recall` | scope (batch vs all brands) + invented reason |
| `calamine-recall` | scope (one batch vs all bottles) |
| `product-recall` | jurisdiction (overseas vs Singapore) |
| `policy-stage` | status (passed vs in force vs enforced) |
| `ns-enlistment` | status (arrest vs charge vs conviction vs sentence) |
| `rocky-case` | status (investigation vs charge) |
| `out-of-scope-abstain` | abstention on an uncovered topic |
| `accurate-forward` | a true message that must **not** be flagged |

Coverage spans all three axes and all three domains, so a regression in any one fails the build
rather than being averaged away. Two cases exist purely to catch over-confidence in each
direction: abstaining when the corpus is silent, and *not* flagging an accurate message.

## Metrics

### 1. Claim decomposition
Did we extract the right atomic claims? Scored as F1 over fuzzy-matched claim texts.
**Target: ≥ 0.75 F1.** Over-splitting is penalised as much as under-splitting.

### 2. Routing accuracy
For matched claims, is `statusType`/`domain` correct? **Target: ≥ 0.80 accuracy.**
Routing errors are upstream errors — they poison retrieval, so they are tracked separately.

### 3. Verdict accuracy
Per-claim verdict against the gold label. **Target: ≥ 0.75 exact match.**

Note that some gold labels are deliberately `Insufficient evidence` (PR eligibility, the invented
Sunday deadline). Those are not "unknowns the system failed to resolve" — they are the correct
answer, and predicting a confident verdict there is a **critical error**.

Not all errors cost the same:

| Error | Severity | Why |
|---|---|---|
| gold `False` → predicted `Supported` | **critical** | endorses a false forward |
| gold `Misleading` → predicted `Supported` | **critical** | loses the escalation |
| gold anything → predicted `Insufficient evidence` | tolerable | cautious, not harmful |
| gold `Insufficient evidence` → predicted confident | **critical** | fabricated confidence |

The harness reports a separate **critical-error count**, which must be **0** on the seeded set.

### 4. Citation presence
Any claim with a non-abstaining verdict must cite ≥ 1 evidence ID.
**Target: 100%.** A confident verdict with no citation is a hallucination by construction.

### 5. Abstention behaviour
For cases whose gold label is `Insufficient evidence`, does the system actually abstain?
**Target: ≥ 0.90 recall.** This is the metric that keeps the system honest.

### 6. Escalation detection
Specifically for claims marked as status escalations in the dataset, is the verdict one of
`Misleading` / `False`? **Target: 100%** on seeded cases — this is the product's core promise.

## Running

```bash
cd backend && python -m pytest app/tests -v        # unit + eval assertions
python scripts/run_eval.py                          # scored report
```

`run_eval.py` prints a per-metric table and exits non-zero if any target is missed, so it can
gate CI later.

## Known limitations of this eval

- Small dataset (single digits of cases) — these are **regression guards**, not generalisation
  estimates. No claim is made about unseen messages.
- Evidence is mock, so retrieval quality is measured against a store built for these cases.
- Fuzzy claim matching is token-overlap based and will drift if wording changes substantially.

## When the LLM adapter lands

Run the same harness with `FORWARDCHECK_LLM=anthropic` and compare against the deterministic
baseline. The rule-based pipeline is the control. If the LLM does not beat it on critical
errors and abstention recall, it does not ship.
