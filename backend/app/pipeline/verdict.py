"""Node 7 — verdict.

Turns grades into verdicts, per claim and then overall, and writes the
share-ready correction.

The decision rules are intentionally explicit rather than a learned score, so
that every verdict can be explained in one sentence in the UI and asserted in
the eval harness. The ordering encodes a bias toward caution:

  * A refutation outweighs support. If an official source says the status was
    not reached, the claim is not `Supported` no matter how much surrounding
    material matches.
  * A claim that escalates a real event is `Misleading`, not `False`. The event
    happened; the status is wrong. Collapsing that into "False" is itself a
    misrepresentation, and it is what makes people distrust fact-checks.
  * Anything without qualifying evidence is `Insufficient evidence`. There is no
    path from "no evidence" to a confident verdict.
"""

from __future__ import annotations

import time
from datetime import date, datetime

from app.config import settings
from app.models.schemas import Claim, GradeLabel, Verdict
from app.models.status import STATUS_DOMAIN, StatusType, is_escalation
from app.pipeline.graph import PipelineState

#: Grades at or below this score are too weak to carry a confident verdict.
_WEAK_GRADE = 0.45


def _decide_claim(claim: Claim, stale_ids: set[str]) -> tuple[Verdict, float, str]:
    """Return (verdict, confidence, one-sentence reason) for a single claim."""
    grades = [g for g in claim.grades if g.label != GradeLabel.DOES_NOT_ANSWER]

    if not grades:
        return (
            Verdict.INSUFFICIENT,
            0.25,
            "No retrieved source addresses this claim, so it cannot be verified "
            "either way.",
        )

    refutes = [g for g in grades if g.label == GradeLabel.REFUTES]
    supports = [g for g in grades if g.label == GradeLabel.SUPPORTS]
    partials = [g for g in grades if g.label == GradeLabel.PARTIALLY_SUPPORTS]

    strongest = max(grades, key=lambda g: g.score)
    if strongest.score < _WEAK_GRADE:
        return (
            Verdict.INSUFFICIENT,
            0.3,
            "The available sources touch on this topic but none address the "
            "specific claim clearly enough to support a verdict.",
        )

    # --- Refuted ---
    if refutes:
        best_refute = max(refutes, key=lambda g: g.score)
        confidence = min(0.93, 0.55 + best_refute.score * 0.4)

        # An escalation of a real event is misleading, not fabricated.
        if partials or supports or claim.is_escalation:
            return (
                Verdict.MISLEADING,
                confidence,
                best_refute.rationale,
            )
        return (Verdict.FALSE, confidence, best_refute.rationale)

    # --- Escalation without an explicit refutation ---
    # The evidence confirms a lower rung and is silent on the claimed one.
    # Reporting this as Supported is the single worst failure mode here.
    if partials and not supports:
        best_partial = max(partials, key=lambda g: g.score)
        if claim.is_escalation:
            return (
                Verdict.MISLEADING,
                min(0.85, 0.5 + best_partial.score * 0.35),
                best_partial.rationale,
            )
        return (
            Verdict.INSUFFICIENT,
            min(0.55, 0.3 + best_partial.score * 0.25),
            "Sources cover this matter but do not confirm the specific status "
            "claimed.",
        )

    # --- Supported ---
    if supports:
        best_support = max(supports, key=lambda g: g.score)
        confidence = min(0.94, 0.55 + best_support.score * 0.4)

        # Support resting only on stale evidence is reported as Outdated.
        supporting_ids = {g.evidence_id for g in supports}
        if supporting_ids and supporting_ids.issubset(stale_ids):
            return (
                Verdict.OUTDATED,
                confidence * 0.85,
                "The only supporting sources are older than the freshness "
                "threshold; the status may have changed since.",
            )

        if partials:
            confidence *= 0.92
        return (Verdict.SUPPORTED, confidence, best_support.rationale)

    return (
        Verdict.INSUFFICIENT,
        0.3,
        "Evidence is inconclusive for this claim.",
    )


def _mark_escalations(state: PipelineState) -> None:
    """Flag claims asserting a rung above the best-supported evidence rung."""
    for claim in state.claims:
        claim_status = StatusType(claim.status_type)
        if STATUS_DOMAIN.get(claim_status) is None:
            continue

        # If any retrieved source asserts the claimed status directly, the claim
        # is not an escalation regardless of what other, lower-rung documents
        # say. Without this check a correct claim ("cats must be licensed by 31
        # Aug", confirmed by the licensing notice) is flagged as an escalation
        # merely because the pool also contains documents about the policy
        # being in effect — and a true claim would be reported as Misleading.
        if any(
            doc.status_asserted == claim.status_type
            for doc, _ in state.retrieved.get(claim.id, [])
        ):
            continue

        best_supported: StatusType | None = None
        for doc, _ in state.retrieved.get(claim.id, []):
            doc_status = StatusType(doc.status_asserted)
            if STATUS_DOMAIN.get(doc_status) != STATUS_DOMAIN.get(claim_status):
                continue
            if is_escalation(claim_status, doc_status):
                # Track the highest rung the evidence actually reaches.
                if best_supported is None or is_escalation(doc_status, best_supported):
                    best_supported = doc_status

        # A universal claim ("all defaulters are automatically jailed") is an
        # escalation of scope even when the rung matches.
        universal = getattr(claim, "_is_universal", False)

        if best_supported is not None:
            claim.is_escalation = True
            claim.escalation_from = best_supported.value.replace("_", " ")
            claim.escalation_to = claim_status.value.replace("_", " ")
        elif universal and claim_status in (
            StatusType.SENTENCE,
            StatusType.PENALTY,
            StatusType.ENFORCED,
            StatusType.BAN,
        ):
            claim.is_escalation = True
            claim.escalation_from = "case-by-case outcome"
            claim.escalation_to = "automatic consequence"


#: Overall verdict from the mix of claim verdicts. Order matters — the first
#: matching rule wins, and the strictest rules come first.
def _overall(claims: list[Claim]) -> tuple[Verdict, float]:
    if not claims:
        return (Verdict.INSUFFICIENT, 0.2)

    verdicts = [Verdict(c.verdict) for c in claims]
    confidences = [c.confidence for c in claims]
    mean_confidence = sum(confidences) / len(confidences)

    has_false = Verdict.FALSE in verdicts
    has_misleading = Verdict.MISLEADING in verdicts
    has_supported = Verdict.SUPPORTED in verdicts
    has_outdated = Verdict.OUTDATED in verdicts
    all_insufficient = all(v == Verdict.INSUFFICIENT for v in verdicts)

    if all_insufficient:
        return (Verdict.INSUFFICIENT, min(mean_confidence, 0.4))

    # A message that is partly true and partly escalated is Misleading, which is
    # the most common and most important outcome for forwarded claims.
    if has_false and not has_supported and not has_misleading:
        return (Verdict.FALSE, mean_confidence)
    if has_false or has_misleading:
        return (Verdict.MISLEADING, mean_confidence)
    if has_outdated and not has_supported:
        return (Verdict.OUTDATED, mean_confidence)
    if has_supported:
        return (Verdict.SUPPORTED, mean_confidence)
    return (Verdict.INSUFFICIENT, min(mean_confidence, 0.4))


def _write_summary(claims: list[Claim], overall: Verdict) -> str:
    supported = [c for c in claims if c.verdict == Verdict.SUPPORTED.value]
    wrong = [
        c
        for c in claims
        if c.verdict in (Verdict.MISLEADING.value, Verdict.FALSE.value)
    ]
    unknown = [c for c in claims if c.verdict == Verdict.INSUFFICIENT.value]

    parts: list[str] = []
    if overall == Verdict.SUPPORTED:
        parts.append("The checkable claims in this message are supported by the available evidence.")
    elif overall == Verdict.INSUFFICIENT:
        parts.append(
            "There is not enough evidence in the available sources to verify this message."
        )
    elif overall == Verdict.FALSE:
        parts.append("The available evidence contradicts this message.")
    elif overall == Verdict.OUTDATED:
        parts.append("This message describes a status that has since moved on.")
    else:
        parts.append(
            "This message mixes accurate information with claims that overstate "
            "the actual status."
        )

    if supported:
        parts.append(
            f"{len(supported)} claim{'s' if len(supported) > 1 else ''} "
            f"check{'' if len(supported) > 1 else 's'} out: "
            + "; ".join(c.text.rstrip('.') for c in supported[:2])
            + "."
        )
    if wrong:
        parts.append(
            f"{len(wrong)} claim{'s do' if len(wrong) > 1 else ' does'} not: "
            + "; ".join(c.text.rstrip('.') for c in wrong[:2])
            + "."
        )
    if unknown:
        parts.append(
            f"{len(unknown)} claim{'s' if len(unknown) > 1 else ''} could not be "
            f"verified from the available sources."
        )
    return " ".join(parts)


def _write_correction(claims: list[Claim], overall: Verdict) -> str:
    """A short reply sized for a group chat."""
    supported = [c for c in claims if c.verdict == Verdict.SUPPORTED.value]
    wrong = [
        c
        for c in claims
        if c.verdict in (Verdict.MISLEADING.value, Verdict.FALSE.value)
    ]
    unknown = [c for c in claims if c.verdict == Verdict.INSUFFICIENT.value]

    if overall == Verdict.SUPPORTED:
        return (
            "Checked this — the claims in this message line up with the official "
            "sources. Safe to keep, but always check the date before forwarding."
        )
    if overall == Verdict.INSUFFICIENT:
        return (
            "Checked this — I couldn't find official sources confirming this. "
            "That doesn't make it false, but there's nothing to back it up yet. "
            "Best not to forward until it's confirmed."
        )

    lines = ["Checked this before forwarding:"]
    for claim in supported[:2]:
        lines.append(f"✓ TRUE: {claim.text.rstrip('.')}.")
    for claim in wrong[:3]:
        lines.append(f"✗ NOT ACCURATE: {claim.text.rstrip('.')} — {claim.key_reason}")
    for claim in unknown[:1]:
        lines.append(f"? UNCONFIRMED: {claim.text.rstrip('.')}.")
    lines.append("Please don't forward the original as-is.")
    return " ".join(lines)


def verdict(state: PipelineState) -> PipelineState:
    started = time.perf_counter()
    stale_ids = set(state.stale_evidence_ids)

    _mark_escalations(state)

    for claim in state.claims:
        decided, confidence, reason = _decide_claim(claim, stale_ids)
        # `.value`, not the enum: the model is configured with
        # use_enum_values, so fields set after construction must be plain
        # strings too or the response serialises as "Verdict.MISLEADING".
        claim.verdict = decided.value
        claim.confidence = round(confidence, 2)
        claim.key_reason = reason

    overall, overall_confidence = _overall(state.claims)
    state.overall_verdict = overall.value
    state.confidence = round(overall_confidence, 2)
    state.summary = _write_summary(state.claims, overall)
    state.shareable_correction = _write_correction(state.claims, overall)

    # Attach claim links to the evidence cards so the UI can show, per source,
    # which claim it supports or refutes.
    for doc in state.evidence:
        supports_ids, refutes_ids = [], []
        for claim in state.claims:
            for grade_result in claim.grades:
                if grade_result.evidence_id != doc.id:
                    continue
                if grade_result.label in (
                    GradeLabel.SUPPORTS,
                    GradeLabel.PARTIALLY_SUPPORTS,
                ):
                    supports_ids.append(claim.id)
                elif grade_result.label == GradeLabel.REFUTES:
                    refutes_ids.append(claim.id)
        doc.supports_claim_ids = supports_ids
        doc.refutes_claim_ids = refutes_ids

    escalations = [c.id for c in state.claims if c.is_escalation]
    state.add_step(
        node="verdict",
        summary=(
            f"Overall {overall.value} — "
            f"{len(escalations)} escalation(s) detected across "
            f"{len(state.claims)} claim(s)"
        ),
        duration_ms=int((time.perf_counter() - started) * 1000),
        details={
            "perClaim": {c.id: c.verdict for c in state.claims},
            "escalations": escalations,
            "overallRule": (
                "all insufficient -> Insufficient; any false/misleading -> "
                "Misleading (False only when nothing is supported); "
                "otherwise Supported"
            ),
            "meanConfidence": state.confidence,
        },
    )
    return state
