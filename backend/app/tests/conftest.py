"""Test-suite safety net: the test run is ALWAYS mock, never paid.

Without this, a developer whose backend/.env sets FORWARDCHECK_MODE=live would
spend real money simply by running pytest — the exact outcome the cost rules
forbid. Mode is forced to mock before app.config is imported, and provider keys
are cleared from the environment so a live client cannot be constructed even by
accident.

Live behaviour is still fully covered: app/tests/test_live_pipeline.py drives
the live orchestrator with fake adapters. The only paid path in the repository
is scripts/live_smoke.py, which is not collected by pytest and requires an
explicit flag.
"""

from __future__ import annotations

import os

import pytest

# Applied at import time, before app.config reads the environment.
os.environ["FORWARDCHECK_MODE"] = "mock"
os.environ["FORWARDCHECK_LLM"] = "mock"
os.environ["FORWARDCHECK_RETRIEVAL"] = "mock"
os.environ["FORWARDCHECK_SEARCH"] = "mock"
#: Recorded before clearing, so a test can assert the suite started clean.
KEYS_PRESENT_AT_COLLECTION = {
    name: bool(os.environ.get(name))
    for name in ("ANTHROPIC_API_KEY", "TAVILY_API_KEY")
}
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("TAVILY_API_KEY", None)

#: True once the real keys have been stripped from this process.
KEYS_CLEARED = not any(
    os.environ.get(name) for name in ("ANTHROPIC_API_KEY", "TAVILY_API_KEY")
)


@pytest.fixture(autouse=True)
def _forbid_paid_mode(monkeypatch):
    """Keep every test in mock mode even if one mutates settings."""
    monkeypatch.setattr("app.config.settings.mode", "mock", raising=False)
