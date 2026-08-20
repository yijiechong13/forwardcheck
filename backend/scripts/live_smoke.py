#!/usr/bin/env python3
"""Opt-in live smoke test. COSTS REAL MONEY. Never run by pytest or CI.

    FORWARDCHECK_MODE=live python scripts/live_smoke.py --yes-spend-money

Runs exactly ONE verification of one seeded message through the live pipeline:
at most 3 LLM calls and 8 searches under the default budgets. Prints verdicts,
citations and the usage summary. Never prints prompts or key material.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MESSAGE = (
    "From 1 Sept, HDB cat owners with more than 2 cats will automatically be "
    "fined $5,000 and AVS will remove the extra cats. All cats, including "
    "community cats, must be licensed by 31 Aug. Forward to all cat owners."
)


def main() -> int:
    parser = argparse.ArgumentParser(description="One paid live verification.")
    parser.add_argument(
        "--yes-spend-money", action="store_true",
        help="Required. Confirms you accept the provider cost of one request.",
    )
    parser.add_argument("--message", default=MESSAGE, help="Override the test message.")
    args = parser.parse_args()

    if not args.yes_spend_money:
        print("Refusing to run without --yes-spend-money. This makes paid provider calls.")
        return 2

    from app.config import settings

    if not settings.is_live:
        print("FORWARDCHECK_MODE is not 'live'. Set it (and the keys) in backend/.env.")
        return 2
    problems = settings.validate_startup()
    if problems:
        for p in problems:
            print(f"config problem: {p}")
        return 2

    print(f"mode=live model={settings.anthropic_model}")
    print(f"budgets: llm<={settings.max_llm_calls_per_request} "
          f"searches<={settings.max_searches_total} fetches<={settings.max_fetches_total}")
    print("verifying one message...\n")

    from app.pipeline.live import run_live_verification

    result = run_live_verification(args.message)

    print(f"OVERALL: {result.overall_verdict} (confidence {result.confidence})\n")
    for claim in result.claims:
        print(f"  {claim.verdict:22} {claim.text}")
        print(f"      reason: {claim.key_reason[:140]}")
        print(f"      cites:  {', '.join(claim.evidence_ids) or '-'}")
    print("\nEVIDENCE:")
    for doc in result.evidence:
        origin = "full page" if doc.from_full_page else "snippet only"
        print(f"  {doc.id} [{doc.tier}/{origin}] {doc.publisher} — {doc.title[:70]}")
        print(f"      {doc.url}")
    usage = next((s for s in result.pipeline_trace if s.node == "usage"), None)
    if usage:
        print(f"\nUSAGE: {usage.details}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
