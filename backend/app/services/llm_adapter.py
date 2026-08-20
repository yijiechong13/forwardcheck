"""LLM adapter.

The pipeline never imports an SDK directly. It asks this interface for two
things — a classification and a short generation — and the deterministic
implementation answers both without a network call or an API key.

Why the interface is shaped this way:

  * `classify()` returns a label from a **caller-supplied closed set**. An LLM
    that can return arbitrary text cannot be evaluated, and it cannot be swapped
    for rules. Constraining the output at the interface means the mock and the
    real implementation are interchangeable by construction.
  * `complete()` is only used for *prose*, never for verdicts. Verdicts come
    from `verdict.py`, which is deterministic and testable. Keeping generation
    away from the decision is what stops the system from talking itself into an
    answer the evidence does not support.

TODO(anthropic): implement AnthropicLLMAdapter.
  - pip install anthropic; client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
  - model: "claude-sonnet-5" for grading, "claude-haiku-4-5-20251001" for
    cheap classification calls
  - classify(): pass `labels` as a tool schema with an enum so the model
    cannot return anything outside the closed set, rather than parsing prose
  - complete(): use for claim decomposition and grade rationales, never for
    the verdict itself
  - always pass the evidence snippets in the prompt and instruct the model to
    answer only from them; the point of RAG is that the model does not rely
    on parametric memory for facts about a live case
  - compare against the deterministic baseline on the Phase 5 eval harness
    before making it the default (see EVAL_PLAN.md)
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from app.config import settings


class LLMAdapter(ABC):
    """Bounded LLM operations used by the pipeline."""

    @abstractmethod
    def classify(self, text: str, labels: list[str], *, instruction: str) -> str:
        """Return exactly one label from `labels`."""

    @abstractmethod
    def complete(self, prompt: str, *, max_tokens: int = 300) -> str:
        """Free-text generation. Prose only — never used to decide a verdict."""

    @property
    @abstractmethod
    def name(self) -> str: ...


class MockLLMAdapter(LLMAdapter):
    """Deterministic stand-in.

    Not a stub that returns fixed strings: it does real (if simple) work, by
    scoring keyword overlap between the text and each candidate label. That
    makes it a genuine baseline for the eval harness rather than a placeholder,
    and it means the pipeline behaves identically whether or not a key is set.
    """

    @property
    def name(self) -> str:
        return "mock"

    def classify(self, text: str, labels: list[str], *, instruction: str) -> str:
        if not labels:
            raise ValueError("classify() requires a non-empty label set")

        tokens = set(re.findall(r"[a-z]+", text.lower()))
        best_label, best_score = labels[0], -1.0

        for label in labels:
            label_tokens = set(re.findall(r"[a-z]+", label.lower().replace("_", " ")))
            if not label_tokens:
                continue
            overlap = len(tokens & label_tokens) / len(label_tokens)
            if overlap > best_score:
                best_label, best_score = label, overlap

        return best_label

    def complete(self, prompt: str, *, max_tokens: int = 300) -> str:
        # Deliberately inert. Any prose the MVP shows a user is written by
        # `verdict.py` from the actual grades, so a mock that invented text
        # here would only be able to make the output less accurate.
        return ""


class AnthropicLLMAdapter(LLMAdapter):  # pragma: no cover
    """Placeholder for the Anthropic Messages API implementation."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-5") -> None:
        self._api_key = api_key
        self._model = model

    @property
    def name(self) -> str:
        return f"anthropic:{self._model}"

    def classify(self, text: str, labels: list[str], *, instruction: str) -> str:
        raise NotImplementedError(
            "Anthropic adapter is not implemented. Run with FORWARDCHECK_LLM=mock "
            "(the default) — no API key is required."
        )

    def complete(self, prompt: str, *, max_tokens: int = 300) -> str:
        raise NotImplementedError(
            "Anthropic adapter is not implemented. Run with FORWARDCHECK_LLM=mock "
            "(the default) — no API key is required."
        )


def get_llm_adapter() -> LLMAdapter:
    if settings.llm_backend == "anthropic":  # pragma: no cover
        import os

        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            # Fail loudly rather than silently downgrading: a run that the
            # operator believes is LLM-backed but is silently rule-based would
            # invalidate any eval comparison drawn from it.
            raise RuntimeError(
                "FORWARDCHECK_LLM=anthropic but ANTHROPIC_API_KEY is not set."
            )
        return AnthropicLLMAdapter(key)
    return MockLLMAdapter()
