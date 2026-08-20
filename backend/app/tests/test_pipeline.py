"""Pipeline behaviour tests.

These assert the properties the product promises, not exact wording, so the
tests survive prompt/rule tuning:

  * status rungs are distinguished (charged != convicted != sentenced)
  * escalations are never reported as Supported
  * absent evidence produces abstention, not a confident guess
  * every confident verdict cites at least one source
"""

from __future__ import annotations

import pytest

from app.models.schemas import GradeLabel, Verdict
from app.models.status import StatusType, is_escalation
from app.pipeline.decompose import decompose
from app.pipeline.graph import PipelineState
from app.pipeline.normalise import normalise
from app.pipeline.route import route
from app.pipeline.runner import run_verification

CAT_MESSAGE = (
    "⚠️ URGENT ⚠️ From 1 Sept, HDB cat owners with more than 2 cats will be "
    "fined $5,000 and AVS will remove the extra cats. All cats, including "
    "community cats, must be licensed by 31 Aug. Please forward to all cat owners 🐱🙏"
)
NS_MESSAGE = (
    "BREAKING: Amos Yee has been sentenced to 3 years jail in Singapore after "
    "being deported from the US. He was arrested at Changi Airport and convicted "
    "under the Enlistment Act for NS offences. This means all NS defaulters who "
    "return from overseas will automatically be jailed. Forward this."
)
ROCKY_MESSAGE = (
    "Rocky's owner has been charged with animal abuse after the dog died during "
    "an enforcement operation. The owner is already facing court action. Forward this."
)


# --------------------------------------------------------------------------
# normalise
# --------------------------------------------------------------------------

def test_normalise_strips_forwarding_appeals_and_emoji():
    state = normalise(PipelineState(raw_message=CAT_MESSAGE))
    text = state.normalised_message.lower()
    assert "forward" not in text
    assert "urgent" not in text
    assert "🐱" not in state.normalised_message
    # The substance must survive.
    assert "licensed" in text and "$5,000" in state.normalised_message


def test_normalise_records_what_it_removed():
    state = normalise(PipelineState(raw_message=CAT_MESSAGE))
    assert state.normalisation_notes["hadForwardAppeal"] is True
    assert state.normalisation_notes["charsAfter"] < state.normalisation_notes["charsBefore"]


# --------------------------------------------------------------------------
# decompose
# --------------------------------------------------------------------------

def test_decompose_splits_arrested_and_convicted_into_separate_claims():
    """The whole product depends on these getting different verdicts."""
    state = decompose(normalise(PipelineState(raw_message=NS_MESSAGE)))
    texts = [t.lower() for t, _ in state.claim_drafts]
    assert any("arrested" in t and "convicted" not in t for t in texts)
    assert any("convicted" in t and "arrested" not in t for t in texts)


def test_decompose_splits_scope_appositive():
    """'All X, including Y, must Z' is two claims with different answers."""
    state = decompose(normalise(PipelineState(raw_message=CAT_MESSAGE)))
    texts = [t.lower() for t, _ in state.claim_drafts]
    assert any("community cats" in t for t in texts)
    assert any("community" not in t and "licensed" in t for t in texts)


def test_decompose_drops_non_checkable_fragments():
    state = decompose(normalise(PipelineState(raw_message=CAT_MESSAGE)))
    for text, _ in state.claim_drafts:
        assert "please" not in text.lower()


# --------------------------------------------------------------------------
# route
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("He was convicted under the Enlistment Act.", StatusType.CONVICTION),
        ("He was arrested at Changi Airport.", StatusType.ARREST),
        ("The man has been charged in court.", StatusType.CHARGE),
        ("He was sentenced to 3 years jail.", StatusType.SENTENCE),
        ("Police are investigating the matter.", StatusType.INVESTIGATION),
        ("The product has been banned nationwide.", StatusType.BAN),
        ("An advisory was issued to consumers.", StatusType.ADVISORY),
    ],
)
def test_route_assigns_the_right_status_rung(message, expected):
    state = route(decompose(normalise(PipelineState(raw_message=message))))
    assert state.claims, f"no claim extracted from {message!r}"
    assert state.claims[0].status_type == expected.value


def test_route_detects_singapore_jurisdiction():
    state = route(decompose(normalise(PipelineState(raw_message=NS_MESSAGE))))
    assert any(c.jurisdiction == "Singapore" for c in state.claims)


# --------------------------------------------------------------------------
# status ladder
# --------------------------------------------------------------------------

def test_escalation_is_directional():
    assert is_escalation(StatusType.CONVICTION, StatusType.CHARGE)
    assert not is_escalation(StatusType.CHARGE, StatusType.CONVICTION)


def test_release_is_not_an_escalation_of_charge():
    """A de-escalation must never be scored as an escalation."""
    assert not is_escalation(StatusType.RELEASE, StatusType.CHARGE)


# --------------------------------------------------------------------------
# end-to-end behaviour
# --------------------------------------------------------------------------

def test_ns_message_distinguishes_arrest_from_conviction():
    result = run_verification(NS_MESSAGE)
    by_status = {c.status_type: c for c in result.claims}

    assert by_status["arrest"].verdict == Verdict.SUPPORTED.value
    # Conviction and sentence are absent from the corpus by design.
    assert by_status["conviction"].verdict != Verdict.SUPPORTED.value
    assert by_status["sentence"].verdict != Verdict.SUPPORTED.value


def test_rocky_message_never_confirms_a_charge():
    """Evidence has investigation and a statement only — no charge exists."""
    result = run_verification(ROCKY_MESSAGE)
    for claim in result.claims:
        assert claim.verdict != Verdict.SUPPORTED.value

    charge_stage = next(e for e in result.timeline if e.stage == "charge")
    assert charge_stage.found is False


def test_cat_message_supports_the_real_deadline():
    result = run_verification(CAT_MESSAGE)
    assert any(c.verdict == Verdict.SUPPORTED.value for c in result.claims), (
        "the licensing deadline is genuinely real and must be reported as such"
    )


def test_cat_message_rejects_the_automatic_fine():
    result = run_verification(CAT_MESSAGE)
    penalty = next(c for c in result.claims if c.status_type == "penalty")
    assert penalty.verdict in (Verdict.MISLEADING.value, Verdict.FALSE.value)


def test_escalations_are_never_reported_as_supported():
    """The core promise: an escalated status must not come back Supported."""
    for message in (CAT_MESSAGE, NS_MESSAGE, ROCKY_MESSAGE):
        for claim in run_verification(message).claims:
            if claim.is_escalation:
                assert claim.verdict != Verdict.SUPPORTED.value, (
                    f"escalation reported as Supported: {claim.text!r}"
                )


def test_confident_verdicts_always_cite_evidence():
    """A confident verdict with no citation is a hallucination by construction."""
    for message in (CAT_MESSAGE, NS_MESSAGE, ROCKY_MESSAGE):
        for claim in run_verification(message).claims:
            if claim.verdict != Verdict.INSUFFICIENT.value:
                assert claim.evidence_ids, f"uncited verdict: {claim.text!r}"


def test_off_topic_message_abstains():
    """Out of scope must abstain rather than guess."""
    result = run_verification(
        "The price of durian in Geylang has doubled since last year according to my uncle."
    )
    assert result.overall_verdict == Verdict.INSUFFICIENT.value


def test_pipeline_trace_covers_every_node():
    result = run_verification(CAT_MESSAGE)
    nodes = [step.node for step in result.pipeline_trace]
    assert nodes == [
        "normalise",
        "decompose",
        "route",
        "retrieve",
        "grade",
        "freshness",
        "verdict",
    ]


def test_all_evidence_is_labelled_mock():
    for doc in run_verification(CAT_MESSAGE).evidence:
        assert doc.is_mock is True


def test_grades_use_the_closed_label_set():
    allowed = {label.value for label in GradeLabel}
    for claim in run_verification(NS_MESSAGE).claims:
        for grade_result in claim.grades:
            assert grade_result.label in allowed
