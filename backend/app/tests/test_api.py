"""API contract tests.

These assert the *shape* of the response, not the verdicts — verdict quality is
the eval harness's job (Phase 5). Keeping them separate means the contract
tests stay green while the pipeline internals change.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID_MESSAGE = (
    "From 1 Sept, HDB cat owners with more than 2 cats will be fined $5,000."
)


def test_health_reports_mock_mode():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mode"] == "mock"
    assert body["live"] is False


def test_health_never_leaks_key_material():
    """Provider status must be booleans, never values."""
    body = client.get("/health").json()
    text = str(body)
    for provider, configured in body["providersConfigured"].items():
        assert isinstance(configured, bool)
    assert "sk-" not in text and "tvly-" not in text


def test_verify_returns_full_contract():
    response = client.post("/verify", json={"message": VALID_MESSAGE})
    assert response.status_code == 200
    body = response.json()

    for key in (
        "overallVerdict",
        "summary",
        "confidence",
        "lastChecked",
        "claims",
        "evidence",
        "timeline",
        "shareableCorrection",
        "pipelineTrace",
        "mockNotice",
    ):
        assert key in body, f"missing response key: {key}"


def test_verdict_is_from_the_closed_vocabulary():
    response = client.post("/verify", json={"message": VALID_MESSAGE})
    allowed = {
        "Supported",
        "Misleading",
        "False",
        "Outdated",
        "Insufficient evidence",
    }
    body = response.json()
    assert body["overallVerdict"] in allowed
    for claim in body["claims"]:
        assert claim["verdict"] in allowed


def test_confidence_is_a_probability():
    body = client.post("/verify", json={"message": VALID_MESSAGE}).json()
    assert 0.0 <= body["confidence"] <= 1.0
    for claim in body["claims"]:
        assert 0.0 <= claim["confidence"] <= 1.0


def test_short_message_is_rejected():
    assert client.post("/verify", json={"message": "hi"}).status_code == 422


def test_empty_message_is_rejected():
    assert client.post("/verify", json={"message": ""}).status_code == 422


def test_all_evidence_is_labelled_mock():
    """Nothing bundled may present itself as a real citation."""
    body = client.post("/verify", json={"message": VALID_MESSAGE}).json()
    for doc in body["evidence"]:
        assert doc["isMock"] is True


def test_message_length_limit_matches_the_frontend():
    """The API cap and the UI's MAX_CHARS must agree.

    If they drift, the UI either truncates input the API would accept, or lets
    through input the API rejects with a confusing 422.
    """
    import re
    from pathlib import Path

    from app.models.schemas import MAX_MESSAGE_CHARS

    panel = (
        Path(__file__).resolve().parents[3]
        / "frontend" / "src" / "components" / "InputPanel.tsx"
    )
    if not panel.exists():
        pytest.skip("frontend not present in this checkout")
    match = re.search(r"const MAX_CHARS = (\d+)", panel.read_text())
    assert match, "MAX_CHARS not found in InputPanel.tsx"
    assert int(match.group(1)) == MAX_MESSAGE_CHARS


def test_message_over_the_limit_is_rejected():
    response = client.post("/verify", json={"message": "x" * 5000})
    assert response.status_code == 422
