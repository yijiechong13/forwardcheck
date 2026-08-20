"""Scope and modality mismatch tests.

Status escalation (charged -> convicted) was the original model. These tests
cover the other two axes a forwarded claim can overstate:

  * SCOPE    — "all products" vs one batch, "every individual" vs per household
  * MODALITY — "will be fined $5,000" vs "up to $5,000 on conviction"

Each is asserted as a *property* rather than an exact string, so the tests
survive rule tuning but fail if the distinction is lost.
"""

from __future__ import annotations

import pytest

from app.models.schemas import Verdict
from app.pipeline.runner import run_verification

CAT = (
    "From 1 Sept, HDB cat owners with more than 2 cats will automatically be "
    "fined $5,000 and AVS will remove the extra cats. All cats, including "
    "community cats, must be licensed by 31 Aug."
)
CDC = (
    "Every Singaporean will get $500 CDC vouchers in cash this month, "
    "including PRs. Must claim by Sunday or lose it."
)
VAPE = (
    "From 1 May 2026, anyone caught with vapes or Kpods will automatically go "
    "to jail for 10 years."
)
FORMULA = (
    "All NAN and Dumex milk powder in Singapore has been recalled because it "
    "contains toxins. Don't buy any."
)
CALAMINE = "Guardian calamine lotion contains cadmium. Throw away all bottles immediately."

ALL_CASES = [CAT, CDC, VAPE, FORMULA, CALAMINE]

NOT_SUPPORTED = (
    Verdict.MISLEADING.value,
    Verdict.FALSE.value,
    Verdict.INSUFFICIENT.value,
)


def _claim_matching(result, *needles: str):
    """The first claim whose text contains all needles."""
    for claim in result.claims:
        lowered = claim.text.lower()
        if all(n.lower() in lowered for n in needles):
            return claim
    raise AssertionError(
        f"no claim matching {needles}; got {[c.text for c in result.claims]}"
    )


# --------------------------------------------------------------------------
# Decomposition coverage
# --------------------------------------------------------------------------

def test_cat_message_splits_pet_from_community_cats():
    """The deadline is real for pet cats and false for community cats."""
    result = run_verification(CAT)
    community = _claim_matching(result, "community cats")
    general = next(
        c
        for c in result.claims
        if "licensed" in c.text.lower() and "community" not in c.text.lower()
    )
    assert general.verdict == Verdict.SUPPORTED.value
    assert community.verdict in NOT_SUPPORTED


def test_cdc_message_separates_amount_form_and_eligibility():
    result = run_verification(CDC)
    assert len(result.claims) >= 4, [c.text for c in result.claims]
    _claim_matching(result, "cash")
    _claim_matching(result, "PRs")


def test_recall_message_separates_scope_from_reason():
    result = run_verification(FORMULA)
    _claim_matching(result, "recalled")
    _claim_matching(result, "toxins")


def test_composition_and_directive_claims_are_extracted():
    """"Contains cadmium" and "throw away all bottles" are both checkable."""
    result = run_verification(CALAMINE)
    _claim_matching(result, "cadmium")
    _claim_matching(result, "throw away")


# --------------------------------------------------------------------------
# Modality: "up to $X" never supports "automatic $X"
# --------------------------------------------------------------------------

def test_automatic_fine_is_not_supported_by_a_maximum_penalty():
    fine = _claim_matching(run_verification(CAT), "fined", "$5,000")
    assert fine.verdict in NOT_SUPPORTED
    assert fine.evidence_ids


def test_automatic_jail_is_not_supported_by_a_statutory_maximum():
    result = run_verification(VAPE)
    for claim in result.claims:
        assert claim.verdict in NOT_SUPPORTED, (
            f"automatic-penalty claim reported as Supported: {claim.text!r}"
        )


# --------------------------------------------------------------------------
# Scope: bounded sources never support unbounded claims
# --------------------------------------------------------------------------

def test_batch_recall_does_not_support_all_products():
    recalled = _claim_matching(run_verification(FORMULA), "recalled")
    assert recalled.verdict in NOT_SUPPORTED
    assert recalled.evidence_ids


def test_single_batch_does_not_support_discarding_all_bottles():
    directive = _claim_matching(run_verification(CALAMINE), "throw away")
    assert directive.verdict in NOT_SUPPORTED


def test_household_allocation_does_not_support_every_individual():
    per_person = _claim_matching(run_verification(CDC), "every singaporean")
    assert per_person.verdict in NOT_SUPPORTED


def test_vouchers_are_not_supported_as_cash():
    cash = _claim_matching(run_verification(CDC), "cash")
    assert cash.verdict in NOT_SUPPORTED


# --------------------------------------------------------------------------
# Abstention: silence is not confirmation
# --------------------------------------------------------------------------

def test_unstated_eligibility_abstains():
    """The corpus says "Singaporean households" and is silent on PRs."""
    prs = _claim_matching(run_verification(CDC), "PRs")
    assert prs.verdict == Verdict.INSUFFICIENT.value


def test_invented_deadline_abstains():
    deadline = _claim_matching(run_verification(CDC), "sunday")
    assert deadline.verdict == Verdict.INSUFFICIENT.value


# --------------------------------------------------------------------------
# Cross-cutting invariants
# --------------------------------------------------------------------------

@pytest.mark.parametrize("message", ALL_CASES)
def test_every_non_abstaining_verdict_cites_evidence(message):
    for claim in run_verification(message).claims:
        if claim.verdict != Verdict.INSUFFICIENT.value:
            assert claim.evidence_ids, f"uncited verdict: {claim.text!r}"


@pytest.mark.parametrize("message", ALL_CASES)
def test_citations_come_from_the_message_topic(message):
    """A right verdict citing the wrong case is indefensible in a citation tool."""
    from app.data.mock_sources import EVIDENCE_BY_ID, topic_of

    result = run_verification(message)
    topics = [topic_of(EVIDENCE_BY_ID[doc.id]) for doc in result.evidence]
    assert topics, "no evidence retrieved"
    dominant = max(set(topics), key=topics.count)
    share = topics.count(dominant) / len(topics)
    assert share >= 0.5, f"citations scattered across topics: {topics}"


@pytest.mark.parametrize("message", ALL_CASES)
def test_all_five_demo_cases_are_flagged(message):
    """Every seeded demo overstates something; none may pass as Supported."""
    assert run_verification(message).overall_verdict in NOT_SUPPORTED
