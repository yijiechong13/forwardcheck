"""Status ladders — the core domain model.

A forwarded claim is usually not invented. It takes a real event and asserts a
*higher rung* than the evidence supports. Encoding status as an ordered ladder
turns "escalation" from a vibe into a computable property: the claim's rung
index is greater than the best-supported evidence rung index.
"""

from __future__ import annotations

from enum import Enum


class Domain(str, Enum):
    LEGAL = "legal"
    PRODUCT_SAFETY = "product_safety"
    POLICY = "policy"
    UNKNOWN = "unknown"


class ClaimAxis(str, Enum):
    """What *kind* of overstatement a claim can make.

    Status escalation (charged -> convicted) was the original model, but the
    demo corpus made clear it is one axis of three. A forwarded claim can also
    overstate:

      * SCOPE     — who or what is covered ("all products" vs one batch,
                    "every individual" vs per household, "all cats" vs pet cats)
      * MODALITY  — how certain or automatic a consequence is ("will be fined
                    $5,000" vs "liable on conviction to a fine up to $5,000")

    These are independent. "Everyone automatically gets jailed for 10 years"
    overstates scope AND modality while getting the status rung right, and a
    system that only models rungs will pass it as Supported.
    """

    STATUS = "status"
    SCOPE = "scope"
    MODALITY = "modality"


class StatusType(str, Enum):
    # --- Legal ladder ---
    ALLEGATION = "allegation"
    INVESTIGATION = "investigation"
    ARREST = "arrest"
    STATEMENT = "statement"
    CHARGE = "charge"
    CONVICTION = "conviction"
    SENTENCE = "sentence"
    RELEASE = "release"
    BAIL = "bail"

    # --- Product safety ladder ---
    ADVISORY = "advisory"
    WARNING = "warning"
    OVERSEAS_RECALL = "overseas_recall"
    LOCAL_RECALL = "local_recall"
    BAN = "ban"

    # --- Policy ladder ---
    PROPOSED = "proposed"
    PASSED = "passed"
    EFFECTIVE = "effective"
    ENFORCED = "enforced"
    DEADLINE = "deadline"
    PENALTY = "penalty"

    # --- Scope / eligibility (cuts across domains) ---
    ELIGIBILITY = "eligibility"
    RECALL_SCOPE = "recall_scope"

    UNKNOWN = "unknown"


class Jurisdiction(str, Enum):
    """Where a claim or document applies.

    MVP is Singapore-only. OVERSEAS is retained and load-bearing: the
    overseas-recall vs local-recall distinction is one of the escalations this
    product exists to catch, so evidence about other markets must be
    representable in order to refute a claim of a Singapore recall.
    """

    SINGAPORE = "Singapore"
    OVERSEAS = "Overseas"
    UNKNOWN = "Unknown"


# Ordered rungs per domain. Index = severity/finality of the asserted status.
# RELEASE and BAIL are intentionally absent: they are *de-escalations* and must
# never be treated as a higher rung than a charge.
LEGAL_LADDER: list[StatusType] = [
    StatusType.ALLEGATION,
    StatusType.INVESTIGATION,
    StatusType.ARREST,
    StatusType.STATEMENT,
    StatusType.CHARGE,
    StatusType.CONVICTION,
    StatusType.SENTENCE,
]

PRODUCT_SAFETY_LADDER: list[StatusType] = [
    StatusType.ADVISORY,
    StatusType.WARNING,
    StatusType.OVERSEAS_RECALL,
    StatusType.LOCAL_RECALL,
    StatusType.BAN,
]

POLICY_LADDER: list[StatusType] = [
    StatusType.PROPOSED,
    StatusType.PASSED,
    StatusType.EFFECTIVE,
    StatusType.DEADLINE,
    StatusType.ENFORCED,
    StatusType.PENALTY,
]

#: Eligibility sits on the policy ladder for domain purposes but is not a rung:
#: "who qualifies" is a scope question, not a stage of a policy's life.
POLICY_SCOPE_STATUSES: list[StatusType] = [StatusType.ELIGIBILITY]

LADDERS: dict[Domain, list[StatusType]] = {
    Domain.LEGAL: LEGAL_LADDER,
    Domain.PRODUCT_SAFETY: PRODUCT_SAFETY_LADDER,
    Domain.POLICY: POLICY_LADDER,
}

# Which domain each status belongs to, derived from the ladders above.
STATUS_DOMAIN: dict[StatusType, Domain] = {
    status: domain for domain, rungs in LADDERS.items() for status in rungs
}
STATUS_DOMAIN[StatusType.RELEASE] = Domain.LEGAL
STATUS_DOMAIN[StatusType.BAIL] = Domain.LEGAL
STATUS_DOMAIN[StatusType.ELIGIBILITY] = Domain.POLICY
STATUS_DOMAIN[StatusType.RECALL_SCOPE] = Domain.PRODUCT_SAFETY


def rung(status: StatusType, domain: Domain | None = None) -> int:
    """Position of `status` on its ladder, or -1 if it is not a ranked rung."""
    if domain is not None and domain in LADDERS:
        ladder = LADDERS[domain]
        return ladder.index(status) if status in ladder else -1
    for ladder in LADDERS.values():
        if status in ladder:
            return ladder.index(status)
    return -1


def is_escalation(claimed: StatusType, supported: StatusType) -> bool:
    """True when `claimed` sits above `supported` on the same ladder.

    Cross-domain pairs return False: comparing a legal charge to a policy
    deadline is meaningless, and guessing there would produce noise.
    """
    claimed_domain = STATUS_DOMAIN.get(claimed)
    supported_domain = STATUS_DOMAIN.get(supported)
    if claimed_domain is None or claimed_domain != supported_domain:
        return False
    claimed_rung = rung(claimed, claimed_domain)
    supported_rung = rung(supported, supported_domain)
    if claimed_rung < 0 or supported_rung < 0:
        return False
    return claimed_rung > supported_rung


#: Human-facing router labels, shown in the claims table.
STATUS_LABEL: dict[StatusType, str] = {
    StatusType.ALLEGATION: "Allegation",
    StatusType.INVESTIGATION: "Investigation",
    StatusType.ARREST: "Arrest",
    StatusType.STATEMENT: "Official statement",
    StatusType.CHARGE: "Charge",
    StatusType.CONVICTION: "Conviction",
    StatusType.SENTENCE: "Sentence",
    StatusType.RELEASE: "Release",
    StatusType.BAIL: "Bail",
    StatusType.ADVISORY: "Advisory",
    StatusType.WARNING: "Warning",
    StatusType.OVERSEAS_RECALL: "Overseas recall",
    StatusType.LOCAL_RECALL: "Singapore recall",
    StatusType.BAN: "Ban",
    StatusType.RECALL_SCOPE: "Recall scope",
    StatusType.PROPOSED: "Proposed",
    StatusType.PASSED: "Passed",
    StatusType.EFFECTIVE: "In effect",
    StatusType.DEADLINE: "Policy deadline",
    StatusType.ENFORCED: "Enforcement",
    StatusType.PENALTY: "Penalty",
    StatusType.ELIGIBILITY: "Eligibility scope",
    StatusType.UNKNOWN: "Unclassified",
}


def human_label(status: StatusType) -> str:
    return STATUS_LABEL.get(status, status.value.replace("_", " ").capitalize())
