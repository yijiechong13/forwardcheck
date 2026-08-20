"""Node 5 — grade.

Judges each (claim, document) pair as supports / refutes / partially_supports /
does_not_answer. This is where the product's actual opinion lives.

The grader looks for four things, in priority order:

1. **Explicit negation.** A document saying "no person has been charged" refutes
   a claim of a charge outright. Cheap to detect and the strongest signal there is.
2. **Status-rung comparison.** If the claim asserts a rung above what the
   document asserts, that is an escalation — the document supports the *event*
   but refutes the *status*, which is `partially_supports`, not `supports`.
3. **Maximum-vs-automatic framing.** "Liable to a fine not exceeding $5,000"
   refutes "you will be fined $5,000". This distinction is the single most
   common escalation in forwarded messages about penalties.
4. **Lexical overlap.** Only after the above, as a weak fallback.

A deliberate bias runs through all of it: when a document does not clearly
address a claim, the grade is `does_not_answer`, not a hedged support. Silence
must not be read as agreement.
"""

from __future__ import annotations

import re
import time

from app.models.schemas import Evidence, EvidenceGrade, GradeLabel
from app.models.status import STATUS_DOMAIN, StatusType, is_escalation, rung
from app.pipeline.graph import PipelineState
from app.services.retrieval_adapter import tokenise

# Phrases that explicitly deny a status has been reached.
_NEGATION_PATTERNS: list[tuple[str, tuple[StatusType, ...]]] = [
    (r"\bno\s+(?:person|one)\s+has\s+been\s+charged\b|\bno\s+charges?\s+(?:have\s+been\s+)?"
     r"(?:been\s+)?(?:filed|brought|laid)\b|\bhas\s+not\s+been\s+charged\b"
     r"|\bdecision\s+on\s+charges\s+has\s+not\s+been\s+made\b",
     (StatusType.CHARGE,)),
    (r"\bno\s+conviction\s+has\s+been\s+recorded\b|\bhas\s+not\s+been\s+convicted\b"
     r"|\bno\s+plea\s+has\s+been\s+taken\b|\bhas\s+not\s+entered\s+a\s+plea\b",
     (StatusType.CONVICTION,)),
    (r"\bhas\s+not\s+passed\s+sentence\b|\bno\s+sentence\s+has\s+been\b"
     r"|\bnot\s+been\s+sentenced\b", (StatusType.SENTENCE,)),
    (r"\bno\s+recall\s+has\s+been\s+issued\s+locally\b|\bhas\s+not\s+been\s+recalled\b"
     r"|\bnot\s+distributed\s+in\b|\bdoes\s+not\s+extend\s+to\b",
     (StatusType.LOCAL_RECALL,)),
    (r"\bhas\s+not\s+been\s+(?:banned|prohibited)\b|\bremains\s+available\s+for\s+sale\b"
     r"|\bis\s+not\s+a\s+ban\b", (StatusType.BAN,)),
    (r"\bwill\s+not\s+be\s+required\s+to\s+give\s+up\b|\bwill\s+not\s+remove\b"
     r"|\bnot\s+required\s+to\s+be\s+licensed\b|\bare\s+not\s+required\s+to\b",
     (StatusType.ENFORCED, StatusType.EFFECTIVE)),
]

# "Maximum penalty" framing — refutes any claim of an automatic consequence.
_MAXIMUM_FRAMING = re.compile(
    r"\bnot\s+exceeding\b|\bmaximum\s+penalty\b|\bup\s+to\s+(?:a\s+)?(?:fine|\$|\d)"
    r"|\bliable\s+on\s+conviction\b|\bis\s+a\s+maximum\b|\bmay\s+impose\b"
    r"|\bis\s+not\s+(?:a\s+)?(?:fixed|automatic)\b|\bcase\s+by\s+case\b"
    r"|\bnot\s+automatic\b|\bdetermined\s+by\s+the\s+court\b",
    re.IGNORECASE,
)

# Claim-side markers of an automatic/universal consequence.
_AUTOMATIC_CLAIM = re.compile(
    r"\bwill\s+be\s+fined\b|\bwill\s+be\s+jailed\b|\bautomatic(?:ally)?\b"
    r"|\ball\s+\w+\s+will\b|\bevery\b|\bmust\s+pay\b|\bwill\s+face\b",
    re.IGNORECASE,
)

# Scope-narrowing statements, e.g. licensing applies only to owned pet cats.
_SCOPE_LIMIT = re.compile(
    r"\bapplies\s+(?:only\s+)?to\b|\bare\s+not\s+required\b|\bdo\s+not\s+require\b"
    r"|\bis\s+limited\s+to\b|\blimited\s+to\s+the\b|\bonly\s+applies\b"
    r"|\bseparate\s+\w+\s+programme\b",
    re.IGNORECASE,
)

_UNIVERSAL_SCOPE = re.compile(
    r"\ball\s+\w+\s+must\b|\bevery\s+\w+\s+must\b|\ball\s+ns\s+defaulters\b"
    r"|\bincluding\s+community\s+cats\b",
    re.IGNORECASE,
)

#: Subjects a source may explicitly place *outside* a rule's scope, paired with
#: the phrasing that excludes them. A claim about an excluded subject is
#: refuted by the exclusion even though the two share most of their wording —
#: "community cats must be licensed" vs "community cats ... are not required to
#: be licensed" differ by one clause that lexical overlap alone would miss.
_EXCLUDED_SUBJECTS: list[tuple[str, str]] = [
    (
        r"\bcommunity\s+cats?\b",
        r"\bcommunity\s+cats?\b[^.]{0,80}?\b(?:are\s+not\s+required|do\s+not\s+require"
        r"|not\s+required\s+to\s+be\s+licensed|separate\s+\w+\s+programme)\b",
    ),
    (
        r"\bstray\s+(?:cats?|dogs?)\b",
        r"\bstray\s+(?:cats?|dogs?)\b[^.]{0,80}?\bnot\s+required\b",
    ),
]


def _overlap(claim_text: str, doc: Evidence) -> float:
    claim_tokens = set(tokenise(claim_text))
    doc_tokens = set(tokenise(f"{doc.title} {doc.snippet}"))
    if not claim_tokens:
        return 0.0
    return len(claim_tokens & doc_tokens) / len(claim_tokens)


def _grade_pair(
    claim_text: str,
    claim_status: StatusType,
    doc: Evidence,
    retrieval_score: float,
) -> EvidenceGrade:
    snippet = f"{doc.title}. {doc.snippet}"
    doc_status = StatusType(doc.status_asserted)
    overlap = _overlap(claim_text, doc)

    # 1. Explicit negation of the claimed status.
    for pattern, statuses in _NEGATION_PATTERNS:
        if claim_status in statuses and re.search(pattern, snippet, re.IGNORECASE):
            return EvidenceGrade(
                evidence_id=doc.id,
                label=GradeLabel.REFUTES,
                rationale=(
                    f"Source explicitly states this status has not been reached, "
                    f"contradicting the claim of {claim_status.value.replace('_', ' ')}."
                ),
                score=min(0.95, 0.7 + retrieval_score * 0.25),
            )

    # 2. Maximum-penalty framing vs an automatic-consequence claim.
    if _AUTOMATIC_CLAIM.search(claim_text) and _MAXIMUM_FRAMING.search(snippet):
        return EvidenceGrade(
            evidence_id=doc.id,
            label=GradeLabel.REFUTES,
            rationale=(
                "Source describes this as a maximum penalty decided case by case, "
                "not the automatic consequence the claim asserts."
            ),
            score=min(0.92, 0.68 + retrieval_score * 0.24),
        )

    # 3a. The claim's subject is one the source explicitly places out of scope.
    for subject_pattern, exclusion_pattern in _EXCLUDED_SUBJECTS:
        if re.search(subject_pattern, claim_text, re.IGNORECASE) and re.search(
            exclusion_pattern, snippet, re.IGNORECASE
        ):
            return EvidenceGrade(
                evidence_id=doc.id,
                label=GradeLabel.REFUTES,
                rationale=(
                    "Source explicitly places this group outside the scope of "
                    "the rule the claim applies to them."
                ),
                score=min(0.94, 0.7 + retrieval_score * 0.24),
            )

    # 3b. The claim universalises what the source limits.
    if _UNIVERSAL_SCOPE.search(claim_text) and _SCOPE_LIMIT.search(snippet):
        return EvidenceGrade(
            evidence_id=doc.id,
            label=GradeLabel.REFUTES,
            rationale=(
                "Source limits the scope of this rule, while the claim applies it "
                "to everyone."
            ),
            score=min(0.9, 0.65 + retrieval_score * 0.25),
        )

    # 4. Status-rung comparison.
    if STATUS_DOMAIN.get(claim_status) == STATUS_DOMAIN.get(doc_status):
        if is_escalation(claim_status, doc_status):
            # The document confirms the event but at a lower rung: it supports
            # the underlying story while contradicting the asserted status.
            return EvidenceGrade(
                evidence_id=doc.id,
                label=GradeLabel.PARTIALLY_SUPPORTS,
                rationale=(
                    f"Source confirms the matter reached "
                    f"'{doc_status.value.replace('_', ' ')}' but does not support "
                    f"'{claim_status.value.replace('_', ' ')}'."
                ),
                score=min(0.85, 0.55 + retrieval_score * 0.3),
            )
        if doc_status == claim_status and overlap >= 0.25:
            return EvidenceGrade(
                evidence_id=doc.id,
                label=GradeLabel.SUPPORTS,
                rationale=(
                    f"Source asserts the same status "
                    f"('{doc_status.value.replace('_', ' ')}') for this matter."
                ),
                score=min(0.95, 0.6 + retrieval_score * 0.35),
            )
        if (
            rung(claim_status) >= 0
            and rung(doc_status) > rung(claim_status)
            # Entailment only holds if the document is about the same matter.
            # Without this check, any document at a later rung "supports" any
            # earlier-rung claim — which let cat-licensing notices support a
            # claim about durian price controls purely because 'deadline'
            # outranks 'proposed'. Ladder position is not topical relevance.
            and overlap >= 0.25
        ):
            # Document is *ahead* of the claim: it supports the claim's status
            # having been passed. (Sentenced implies charged.)
            return EvidenceGrade(
                evidence_id=doc.id,
                label=GradeLabel.SUPPORTS,
                rationale=(
                    f"Source reports a later stage "
                    f"('{doc_status.value.replace('_', ' ')}'), which entails the "
                    f"claimed status."
                ),
                score=min(0.85, 0.55 + retrieval_score * 0.3),
            )

    # 5. Weak lexical fallback — support only on strong overlap.
    if overlap >= 0.45 and retrieval_score >= 0.5:
        return EvidenceGrade(
            evidence_id=doc.id,
            label=GradeLabel.PARTIALLY_SUPPORTS,
            rationale=(
                "Source discusses the same matter but does not directly address "
                "the specific status claimed."
            ),
            score=min(0.6, 0.35 + retrieval_score * 0.25),
        )

    # 6. Default: silence is not agreement.
    return EvidenceGrade(
        evidence_id=doc.id,
        label=GradeLabel.DOES_NOT_ANSWER,
        rationale="Source does not address this claim either way.",
        score=round(min(0.4, retrieval_score * 0.4), 3),
    )


def grade(state: PipelineState) -> PipelineState:
    started = time.perf_counter()
    tally: dict[str, int] = {label.value: 0 for label in GradeLabel}

    for claim in state.claims:
        grades: list[EvidenceGrade] = []
        for doc, score in state.retrieved.get(claim.id, []):
            result = _grade_pair(
                claim.text, StatusType(claim.status_type), doc, score
            )
            grades.append(result)
            tally[result.label] += 1

        # Strongest signal first, so the UI and the verdict node agree on which
        # piece of evidence mattered most.
        grades.sort(key=lambda g: g.score, reverse=True)
        claim.grades = grades
        claim.evidence_ids = [
            g.evidence_id for g in grades if g.label != GradeLabel.DOES_NOT_ANSWER
        ]

    state.add_step(
        node="grade",
        summary=(
            f"Graded {sum(tally.values())} (claim, source) pair(s): "
            f"{tally['supports']} supports, {tally['refutes']} refutes, "
            f"{tally['partially_supports']} partial, "
            f"{tally['does_not_answer']} silent"
        ),
        duration_ms=int((time.perf_counter() - started) * 1000),
        details={
            "tally": tally,
            "perClaim": {
                c.id: {g.evidence_id: g.label for g in c.grades} for c in state.claims
            },
        },
    )
    return state
