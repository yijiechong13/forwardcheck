"""Security invariants: no key material may ever leave the backend.

These run with realistically-shaped fake keys in the environment and assert
that no endpoint response contains them. A regression here is a credential
leak, so the assertions are on the serialised response body rather than on
individual fields.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

FAKE_ANTHROPIC = "sk-ant-fake000000000000000000000000000000"
FAKE_TAVILY = "tvly-fake00000000000000000000000000"

MESSAGE = "From 1 Sept, HDB cat owners with more than 2 cats will be fined $5,000."


@pytest.fixture
def client_with_fake_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_ANTHROPIC)
    monkeypatch.setenv("TAVILY_API_KEY", FAKE_TAVILY)
    return TestClient(app)


@pytest.mark.parametrize("path", ["/health", "/config"])
def test_get_endpoints_never_return_key_material(client_with_fake_keys, path):
    body = json.dumps(client_with_fake_keys.get(path).json())
    assert FAKE_ANTHROPIC not in body
    assert FAKE_TAVILY not in body
    assert "sk-ant-" not in body and "tvly-" not in body


def test_verify_never_returns_key_material(client_with_fake_keys):
    body = json.dumps(client_with_fake_keys.post("/verify", json={"message": MESSAGE}).json())
    assert FAKE_ANTHROPIC not in body and FAKE_TAVILY not in body


def test_health_reports_provider_status_as_booleans(client_with_fake_keys):
    configured = client_with_fake_keys.get("/health").json()["providersConfigured"]
    assert set(configured) == {"anthropic", "tavily"}
    assert all(isinstance(v, bool) for v in configured.values())


def test_usage_summary_contains_no_prompt_or_key_data():
    """The trace is client-visible; it must carry counts, not content."""
    from app.services.usage import UsageMeter

    meter = UsageMeter()
    meter.charge_llm_call()
    meter.record_tokens(100, 50)
    summary = json.dumps(meter.summary())
    assert "sk-" not in summary and "tvly-" not in summary
    assert set(meter.summary()) == {
        "mode", "llmCalls", "searches", "fetches",
        "inputTokens", "outputTokens", "cacheHits", "decisions",
    }


def test_internal_errors_do_not_leak_details(monkeypatch):
    """A provider exception must become a generic message, not a stack trace."""
    from app.services.llm_adapter import LLMError

    def boom(message):
        raise LLMError("auth", f"key {FAKE_ANTHROPIC} rejected")

    monkeypatch.setattr("app.main.run_verification", boom)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/verify", json={"message": MESSAGE})
    body = json.dumps(response.json())
    assert response.status_code == 502
    assert FAKE_ANTHROPIC not in body
    assert "Traceback" not in body


def test_env_example_contains_only_placeholders():
    """The committed template must never carry a real key."""
    from pathlib import Path

    example = Path(__file__).resolve().parents[2] / ".env.example"
    if not example.exists():
        pytest.skip(".env.example not present")
    text = example.read_text()
    assert "sk-ant-" not in text
    assert "tvly-" not in text
    assert "your_anthropic_api_key" in text


# ---------------------------------------------------------------------------
# Cost safety: the test suite must never be able to spend money
# ---------------------------------------------------------------------------

def test_test_suite_runs_in_mock_mode_regardless_of_env():
    """conftest forces mock, so a live .env cannot make pytest spend money."""
    from app.config import settings

    assert settings.mode == "mock"


def test_real_provider_keys_are_cleared_at_collection():
    """conftest strips real keys at import, so no live client can be built.

    Asserted against the flag conftest records at collection time rather than
    the live environment, because individual tests legitimately inject
    clearly-fake keys via monkeypatch.
    """
    from app.tests.conftest import KEYS_CLEARED

    assert KEYS_CLEARED, "real provider keys were visible to the test suite"


def test_live_smoke_script_requires_explicit_flag():
    """The only paid path must refuse to run without --yes-spend-money."""
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).resolve().parents[2] / "scripts" / "live_smoke.py"
    result = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, timeout=60
    )
    assert result.returncode != 0
    assert "yes-spend-money" in result.stdout
