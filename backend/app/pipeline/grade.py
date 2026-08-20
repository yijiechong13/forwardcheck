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
from dataclasses import dataclass

from app.models.schemas import Evidence, EvidenceGrade, GradeLabel
from app.models.status import STATUS_DOMAIN, StatusType, is_escalation, rung
from app.pipeline.graph import PipelineState
from app.services.retrieval_adapter import tokenise

#: Claim-side quantifiers asserting that a fact covers everything of its kind.
_UNBOUNDED_QUANTIFIER = re.compile(
    r"\ball\b|\bevery\b|\bwhole\b|\bentire\b|\bany\s+\w+\s+(?:product|brand)\b",
    re.IGNORECASE,
)

#: Source-side language bounding a fact to a subset.
_BOUNDED_SOURCE = re.compile(
    r"\bspecified\s+batches\b|\bspecific\s+batches\b|\bsingle\s+batch\b"
    r"|\bone\s+batch\b|\blimited\s+to\b|\bbatch\s+numbers?\s+(?:and|listed)\b"
    r"|\bother\s+batches\b|\bnot\s+affected\b|\bthree\s+specified\b"
    r"|\bonly\s+the\s+listed\b",
    re.IGNORECASE,
)

#: Source language denying a contaminant or substituting the real reason.
_SUBSTANCE_DENIAL: list[str] = [
    r"\bno\s+evidence\s+of\s+toxin\b",
    r"\bdid\s+not\s+identify\s+any\s+contamination\b",
    r"\brecall\s+was\s+precautionary\b",
    r"\brelated\s+to\s+packaging,?\s+not\s+to\s+the\s+contents\b",
    r"\bover\s+toxins?\b[^.]{0,60}\binaccurate\b",
    r"\bthose\s+claims\s+are\s+inaccurate\b",
]


@dataclass(frozen=True)
class _ScopeMismatch:
    """A bounded source fact set against an unbounded claim."""

    claim_pattern: str
    source_pattern: str
    rationale: str


#: The scope/modality mismatches this product exists to catch. Each pairs
#: claim-side over-generalisation with the source-side language that bounds it.
_SCOPE_MISMATCHES: list[_ScopeMismatch] = [
    # "all products" vs "affected batches only"
    _ScopeMismatch(
        claim_pattern=(
            r"\b(?:all|every|whole|entire)\s+(?:batches|products|bottles|items|"
            r"packs|stock|brands?|range|lines?)\b"
            r"|\ball\s+\w+\s+(?:powder|lotion|formula|products?)\b"
            r"|\bthrow\s+away\s+all\b|\bdiscard\s+all\b|\bavoid\s+all\b"
        ),
        source_pattern=(
            r"\blimited\s+to\s+the\s+batch\b|\bonly\s+the\s+(?:listed\s+)?batch"
            r"|\bspecified\s+batches\b|\bsingle\s+batch\b|\bthree\s+specified\b"
            r"|\bother\s+batches\b[^.]{0,60}\bnot\s+(?:affected|subject)\b"
            r"|\bare\s+not\s+affected\b|\bnot\s+advised\s+to\s+discard\b"
            r"|\bdo\s+not\s+need\s+to\s+be\s+discarded\b"
            r"|\bno\s+brand-wide\s+recall\b"
        ),
        rationale=(
            "Source limits the recall to specific batches. Other batches and "
            "products are not affected"
        ),
    ),
    # "every individual" vs "per household"
    _ScopeMismatch(
        claim_pattern=(
            r"\bevery\s+(?:singaporean|citizen|person|adult|resident)\b"
            r"|\beach\s+(?:singaporean|citizen|person)\b|\bper\s+(?:person|individual)\b"
            r"|\beveryone\s+(?:will\s+)?(?:get|receives?)\b"
        ),
        source_pattern=(
            r"\bper\s+household\b|\bevery\s+singaporean\s+household\b"
            r"|\ballocated\s+per\s+household\b|\bnot\s+per\s+individual\b"
            r"|\bgiven\s+per\s+singaporean\s+household\b"
            r"|\brather\s+than\s+to\s+each\s+person\b"
        ),
        rationale=(
            "Source allocates this per household, not to each individual"
        ),
    ),
    # "cash" vs "vouchers"
    _ScopeMismatch(
        claim_pattern=r"\bcash\b",
        source_pattern=(
            r"\bnot\s+a\s+cash\s+payout\b|\bcannot\s+be\s+withdrawn\b"
            r"|\bnot\s+cash\b|\bare\s+digital\s+vouchers\b"
            r"|\bexchanged\s+for\s+cash\b"
        ),
        rationale=(
            "Source states these are vouchers redeemed at merchants, not a cash "
            "payout"
        ),
    ),
    # "everyone / all offenders" vs offence-specific penalties
    _ScopeMismatch(
        claim_pattern=(
            r"\banyone\s+caught\b|\ball\s+(?:users|offenders)\b"
            r"|\beveryone\s+(?:will|caught)\b|\bsame\s+penalty\b"
        ),
        source_pattern=(
            r"\btreated\s+differently\s+from\b|\bpenalties\s+differ\s+by\b"
            r"|\bdealt\s+with\s+by\s+composition\b"
            r"|\bmay\s+be\s+referred\s+for\s+cessation\b"
            r"|\bsubstantially\s+heavier\s+penalties\b"
        ),
        rationale=(
            "Source states penalties differ by offence type; possession and use "
            "are treated differently from import and supply"
        ),
    ),
]


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

#: Plain-language corrections for each denied status. These reach the user
#: directly through the shareable correction card.
_NEGATION_RATIONALE: dict[StatusType, str] = {
    StatusType.CHARGE: (
        "Source states no one has been charged — the case is still at the "
        "investigation or review stage"
    ),
    StatusType.CONVICTION: (
        "Source states no conviction has been recorded — the person has been "
        "charged but the case has not been decided"
    ),
    StatusType.SENTENCE: (
        "Source states no sentence has been passed — the court has not decided "
        "the case"
    ),
    StatusType.LOCAL_RECALL: (
        "Source states there has been no local recall — the affected batches "
        "were not sold here"
    ),
    StatusType.BAN: (
        "Source states the product has not been banned and remains on sale"
    ),
    StatusType.ENFORCED: (
        "Source states owners will not be required to give up their animals"
    ),
    StatusType.EFFECTIVE: "Source states this requirement does not apply as claimed",
}

# "Maximum penalty" framing — refutes any claim of an automatic consequence.
_MAXIMUM_FRAMING = re.compile(
    r"\bnot\s+exceeding\b|\bmaximum\s+penalty\b|\bup\s+to\s+(?:a\s+)?(?:fine|\$|\d)"
    r"|\bliable\s+on\s+conviction\b|\bis\s+a\s+maximum\b|\bmay\s+impose\b"
    r"|\bis\s+not\s+(?:a\s+)?(?:fixed|automatic)\b|\bcase\s+by\s+case\b"
    r"|\bnot\s+automatic\b|\bdetermined\s+by\s+the\s+court\b"
    r"|\bmaximum\s+available\s+to\s+the\s+court\b|\bmaximum\s+penalties\b"
    r"|\bliable\s+to\s+a\s+fine\b|\bdoes\s+not\s+follow\s+from\b"
    r"|\bincreases?\s+the\s+maximum\b",
    re.IGNORECASE,
)

# Claim-side markers of an automatic/universal consequence.
_AUTOMATIC_CLAIM = re.compile(
    r"\bwill\s+be\s+fined\b|\bwill\s+be\s+jailed\b|\bautomatic(?:ally)?\b"
    r"|\ball\s+\w+\s+will\b|\bevery\b|\bmust\s+pay\b|\bwill\s+face\b"
    r"|\bwill\s+(?:go\s+to\s+jail|receive)\b|\banyone\s+caught\b"
    r"|\bthe\s+(?:jail\s+term|fine|penalty)\s+is\b",
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


#: Statuses whose claims are *about* specific details — who qualifies, which
#: batch, what substance, which deadline. For these, a document sharing the
#: status label says nothing about whether the specific claim is true, so
#: support additionally requires the claim's distinctive terms to appear.
_SPECIFICITY_REQUIRED = {
    StatusType.ELIGIBILITY,
    StatusType.RECALL_SCOPE,
    StatusType.DEADLINE,
    StatusType.PENALTY,
}

#: Words too common to distinguish one claim from another within a cluster.
_LOW_SIGNAL = {
    "singapore", "product", "products", "claim", "claims", "also", "must",
    "will", "given", "get", "gets", "are", "is", "the", "this", "that",
    "eligible", "recalled", "recall", "affected", "batch", "batches",
}


def _claim_terms_present(claim_text: str, doc: Evidence) -> bool:
    """Do the claim's distinctive terms actually appear in the source?

    Distinctive = not a stopword and not a term shared by every document in
    this topic. If a claim has no distinctive terms at all we return True, so
    that generic-but-on-topic claims still resolve via the normal rules rather
    than silently abstaining.
    """
    claim_tokens = {
        t for t in tokenise(claim_text) if t not in _LOW_SIGNAL and len(t) > 2
    }
    if not claim_tokens:
        return True
    doc_tokens = set(tokenise(f"{doc.title} {doc.snippet}"))
    return bool(claim_tokens & doc_tokens)


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
                # State the actual correction, not that "a status was not
                # reached". This rationale is what ends up in the share card,
                # and a person reading it in a group chat needs to know what is
                # true instead — abstract status language helps nobody.
                rationale=_NEGATION_RATIONALE.get(
                    claim_status,
                    f"Source states this has not reached the "
                    f"'{claim_status.value.replace('_', ' ')}' stage.",
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

    # 2a. Explicit denial of a substance or reason claim.
    #
    # Checked before term-overlap logic because a source that *denies* a
    # contaminant names it: "claims it contains toxins are inaccurate" contains
    # the word "toxins". Lexical presence cannot distinguish an assertion from
    # its denial, so the denial has to be matched directly.
    for pattern in _SUBSTANCE_DENIAL:
        if re.search(pattern, snippet, re.IGNORECASE) and re.search(
            r"\bcontains?\b|\btoxins?\b|\bcontaminat", claim_text, re.IGNORECASE
        ):
            return EvidenceGrade(
                evidence_id=doc.id,
                label=GradeLabel.REFUTES,
                rationale=(
                    "Source states there is no such contamination and gives a "
                    "different reason for the recall"
                ),
                score=min(0.93, 0.68 + retrieval_score * 0.25),
            )

    # 2b. Scope and quantifier mismatches.
    #
    # These four checks share one shape: the source states a *bounded* fact and
    # the claim asserts an *unbounded* one. Related evidence is not enough —
    # a document about the right topic that states a narrower scope refutes the
    # broader claim rather than partially supporting it, which is the single
    # most common way a product-safety or benefits forward goes wrong.
    for check in _SCOPE_MISMATCHES:
        if re.search(check.claim_pattern, claim_text, re.IGNORECASE) and re.search(
            check.source_pattern, snippet, re.IGNORECASE
        ):
            return EvidenceGrade(
                evidence_id=doc.id,
                label=GradeLabel.REFUTES,
                rationale=check.rationale,
                score=min(0.94, 0.68 + retrieval_score * 0.26),
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
            # Status agreement means the document is *on topic*, not that it
            # agrees with the claim. A source about eligibility does not
            # support "PRs are eligible" merely by being about eligibility.
            #
            # For scope-shaped statuses the specifics are the entire content of
            # the claim, so a shared label is far too weak a basis for support.
            # Requiring the claim's distinctive terms to actually appear in the
            # source is what stops "contains toxins" being supported by a
            # document that says the opposite.
            if claim_status in _SPECIFICITY_REQUIRED and not _claim_terms_present(
                claim_text, doc
            ):
                return EvidenceGrade(
                    evidence_id=doc.id,
                    label=GradeLabel.DOES_NOT_ANSWER,
                    rationale=(
                        "Source covers this topic but does not state the "
                        "specific detail claimed."
                    ),
                    score=round(min(0.4, retrieval_score * 0.4), 3),
                )
            # An unbounded claim is never *supported* by a bounded source, even
            # when both describe the same status. "All milk powder has been
            # recalled" and "three specified batches have been recalled" are
            # both local_recall claims; treating the second as support for the
            # first is how a real recall becomes a false all-clear in reverse.
            if _UNBOUNDED_QUANTIFIER.search(claim_text) and _BOUNDED_SOURCE.search(
                snippet
            ):
                return EvidenceGrade(
                    evidence_id=doc.id,
                    label=GradeLabel.REFUTES,
                    rationale=(
                        "Source confirms a recall but limits it to specific "
                        "batches, not the whole product or brand"
                    ),
                    score=min(0.93, 0.66 + retrieval_score * 0.26),
                )
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
