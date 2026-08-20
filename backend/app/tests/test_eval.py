"""Eval-harness assertions.

These turn EVAL_PLAN.md's targets into a failing build. The critical-error
assertion is the important one: raw accuracy can stay high while a dangerous
regression hides inside it, so the dangerous error classes are asserted at zero
separately.
"""

from __future__ import annotations

import pytest

from app.eval.harness import TARGETS, evaluate, load_dataset


@pytest.fixture(scope="module")
def report():
    return evaluate()


def test_dataset_is_well_formed():
    data = load_dataset()
    assert data["cases"], "eval dataset is empty"
    allowed = {"Supported", "Misleading", "False", "Outdated", "Insufficient evidence"}
    for case in data["cases"]:
        assert case["expectedOverallVerdict"] in allowed
        assert case["expectedClaims"], f"{case['id']} has no expected claims"
        for claim in case["expectedClaims"]:
            assert claim["verdict"] in allowed
            assert claim["gist"] and claim["statusType"]


def test_dataset_covers_abstention_and_a_true_message():
    """Without both, the harness cannot detect over- or under-confidence."""
    data = load_dataset()
    overalls = {case["expectedOverallVerdict"] for case in data["cases"]}
    assert "Insufficient evidence" in overalls, "no abstention case"
    assert "Supported" in overalls, "no true-message case"


def test_no_critical_errors(report):
    """No false endorsements and no unearned confidence. Must be zero."""
    assert report.critical_errors == [], "\n".join(report.critical_errors)


@pytest.mark.parametrize(("attribute", "label", "target"), TARGETS)
def test_metric_meets_target(report, attribute, label, target):
    value = getattr(report, attribute)
    assert value >= target, f"{label}: {value:.3f} < target {target:.2f}"


def test_every_gold_claim_is_extracted(report):
    """Decomposition recall is what upstream errors show up in first."""
    assert report.decomposition_recall >= 0.75


def test_out_of_scope_message_abstains(report):
    outcomes = [o for o in report.outcomes if o.case_id == "out-of-scope-abstain"]
    assert outcomes
    for outcome in outcomes:
        if outcome.matched:
            assert outcome.predicted_verdict == "Insufficient evidence"
