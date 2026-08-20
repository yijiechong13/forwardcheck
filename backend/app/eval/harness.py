"""Evaluation harness.

Scores the pipeline against `tests/eval_dataset.json` on the metrics defined in
EVAL_PLAN.md. Importable so both pytest and the CLI report use identical logic —
a metric that is computed two different ways is a metric you cannot trust.

The design decision worth noting: **errors are not weighted equally.** Reporting
a false claim as `Supported` endorses a forward; reporting a supported claim as
`Insufficient evidence` is merely unhelpful. The harness therefore tracks a
separate `critical_errors` count, and that is the number that gates the build —
raw accuracy would let a dangerous regression hide behind a good average.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.pipeline.runner import run_verification
from app.services.retrieval_adapter import tokenise

DATASET_PATH = Path(__file__).resolve().parents[1] / "tests" / "eval_dataset.json"

#: Token-overlap threshold for matching a predicted claim to a gold claim.
#: Fuzzy because the pipeline rewrites claims (subject carry-forward, scope
#: splitting) and exact string matching would measure phrasing, not extraction.
_MATCH_THRESHOLD = 0.34

ABSTAIN = "Insufficient evidence"


def load_dataset(path: Path | None = None) -> dict:
    with open(path or DATASET_PATH) as handle:
        return json.load(handle)


def _similarity(a: str, b: str) -> float:
    """Asymmetric overlap: how much of the gold gist appears in the prediction."""
    gold_tokens = set(tokenise(a))
    pred_tokens = set(tokenise(b))
    if not gold_tokens:
        return 0.0
    return len(gold_tokens & pred_tokens) / len(gold_tokens)


@dataclass
class ClaimOutcome:
    case_id: str
    gold_gist: str
    matched: bool
    predicted_text: str | None = None
    gold_verdict: str = ""
    predicted_verdict: str | None = None
    gold_status: str = ""
    predicted_status: str | None = None
    verdict_correct: bool = False
    status_correct: bool = False
    is_critical_error: bool = False
    critical_reason: str = ""
    citation_ok: bool = True


@dataclass
class EvalReport:
    # decomposition
    matched_claims: int = 0
    gold_claims: int = 0
    predicted_claims: int = 0
    # routing / verdicts
    status_correct: int = 0
    verdict_correct: int = 0
    # abstention
    abstain_expected: int = 0
    abstain_achieved: int = 0
    # escalation
    escalation_expected: int = 0
    escalation_flagged: int = 0
    # citations
    citation_required: int = 0
    citation_present: int = 0
    # overall verdicts
    overall_correct: int = 0
    overall_total: int = 0

    critical_errors: list[str] = field(default_factory=list)
    outcomes: list[ClaimOutcome] = field(default_factory=list)

    # ---- derived metrics -------------------------------------------------

    @property
    def decomposition_precision(self) -> float:
        return self.matched_claims / self.predicted_claims if self.predicted_claims else 0.0

    @property
    def decomposition_recall(self) -> float:
        return self.matched_claims / self.gold_claims if self.gold_claims else 0.0

    @property
    def decomposition_f1(self) -> float:
        p, r = self.decomposition_precision, self.decomposition_recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def routing_accuracy(self) -> float:
        return self.status_correct / self.matched_claims if self.matched_claims else 0.0

    @property
    def verdict_accuracy(self) -> float:
        return self.verdict_correct / self.matched_claims if self.matched_claims else 0.0

    @property
    def abstention_recall(self) -> float:
        return (
            self.abstain_achieved / self.abstain_expected
            if self.abstain_expected
            else 1.0
        )

    @property
    def escalation_recall(self) -> float:
        return (
            self.escalation_flagged / self.escalation_expected
            if self.escalation_expected
            else 1.0
        )

    @property
    def citation_rate(self) -> float:
        return (
            self.citation_present / self.citation_required
            if self.citation_required
            else 1.0
        )

    @property
    def overall_accuracy(self) -> float:
        return self.overall_correct / self.overall_total if self.overall_total else 0.0


def _classify_critical(gold_verdict: str, predicted_verdict: str) -> str | None:
    """Return a reason string if this error class is dangerous, else None.

    Three classes are critical, all variations on unearned confidence:
      * endorsing something the evidence contradicts
      * losing an escalation by calling it Supported
      * answering confidently where the gold label says we cannot know
    """
    if gold_verdict == predicted_verdict:
        return None
    if gold_verdict in ("False", "Misleading") and predicted_verdict == "Supported":
        return f"endorsed a {gold_verdict.lower()} claim as Supported"
    if gold_verdict == ABSTAIN and predicted_verdict not in (ABSTAIN,):
        return f"answered '{predicted_verdict}' where evidence is insufficient"
    if gold_verdict == "Supported" and predicted_verdict in ("False", "Misleading"):
        return f"flagged a true claim as {predicted_verdict}"
    return None


def evaluate(dataset: dict | None = None) -> EvalReport:
    data = dataset or load_dataset()
    report = EvalReport()

    for case in data["cases"]:
        result = run_verification(case["message"])
        predicted = result.claims

        report.overall_total += 1
        if result.overall_verdict == case["expectedOverallVerdict"]:
            report.overall_correct += 1
        else:
            reason = _classify_critical(
                case["expectedOverallVerdict"], result.overall_verdict
            )
            if reason:
                report.critical_errors.append(f"[{case['id']}] overall: {reason}")

        report.predicted_claims += len(predicted)
        report.gold_claims += len(case["expectedClaims"])

        used: set[int] = set()
        for gold in case["expectedClaims"]:
            outcome = ClaimOutcome(
                case_id=case["id"],
                gold_gist=gold["gist"],
                matched=False,
                gold_verdict=gold["verdict"],
                gold_status=gold["statusType"],
            )

            if gold["verdict"] == ABSTAIN:
                report.abstain_expected += 1
            if gold.get("isEscalation"):
                report.escalation_expected += 1

            # Greedy best match among unused predictions.
            best_index, best_score = -1, 0.0
            for index, claim in enumerate(predicted):
                if index in used:
                    continue
                score = _similarity(gold["gist"], claim.text)
                if score > best_score:
                    best_index, best_score = index, score

            if best_index < 0 or best_score < _MATCH_THRESHOLD:
                report.outcomes.append(outcome)
                continue

            used.add(best_index)
            claim = predicted[best_index]
            outcome.matched = True
            outcome.predicted_text = claim.text
            outcome.predicted_verdict = claim.verdict
            outcome.predicted_status = claim.status_type
            report.matched_claims += 1

            if claim.status_type == gold["statusType"]:
                report.status_correct += 1
                outcome.status_correct = True

            if claim.verdict == gold["verdict"]:
                report.verdict_correct += 1
                outcome.verdict_correct = True
            else:
                reason = _classify_critical(gold["verdict"], claim.verdict)
                if reason:
                    outcome.is_critical_error = True
                    outcome.critical_reason = reason
                    report.critical_errors.append(
                        f"[{case['id']}] {gold['gist']!r}: {reason}"
                    )

            if gold["verdict"] == ABSTAIN and claim.verdict == ABSTAIN:
                report.abstain_achieved += 1
            if gold.get("isEscalation") and claim.is_escalation:
                report.escalation_flagged += 1

            if gold.get("requiresCitation"):
                report.citation_required += 1
                # A non-abstaining verdict must cite at least one source.
                if claim.verdict == ABSTAIN or claim.evidence_ids:
                    report.citation_present += 1
                else:
                    outcome.citation_ok = False
                    report.critical_errors.append(
                        f"[{case['id']}] {gold['gist']!r}: confident verdict with no citation"
                    )

            report.outcomes.append(outcome)

    return report


#: Targets from EVAL_PLAN.md. (metric attribute, label, minimum)
TARGETS: list[tuple[str, str, float]] = [
    ("decomposition_f1", "Claim decomposition F1", 0.75),
    ("routing_accuracy", "Routing accuracy", 0.80),
    ("verdict_accuracy", "Verdict accuracy", 0.75),
    ("citation_rate", "Citation presence", 1.00),
    ("abstention_recall", "Abstention recall", 0.90),
    ("escalation_recall", "Escalation detection", 1.00),
]
