#!/usr/bin/env python3
"""Scored evaluation report.

    python scripts/run_eval.py            # summary
    python scripts/run_eval.py --verbose  # per-claim detail

Exits non-zero if any target is missed or any critical error occurs, so it can
gate CI.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.eval.harness import TARGETS, evaluate  # noqa: E402

BAR_WIDTH = 24


def bar(value: float) -> str:
    filled = round(value * BAR_WIDTH)
    return "█" * filled + "·" * (BAR_WIDTH - filled)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the ForwardCheck pipeline.")
    parser.add_argument("--verbose", action="store_true", help="per-claim detail")
    args = parser.parse_args()

    report = evaluate()

    print()
    print("  ForwardCheck evaluation")
    print(f"  adapters: llm={settings.llm_backend} "
          f"retrieval={settings.retrieval_backend} search={settings.search_backend}")
    print("  " + "─" * 66)

    failures: list[str] = []
    for attribute, label, target in TARGETS:
        value = getattr(report, attribute)
        passed = value >= target
        if not passed:
            failures.append(f"{label}: {value:.3f} < {target:.2f}")
        print(
            f"  {label:<24} {bar(value)} {value:6.1%}   "
            f"target {target:.0%}  {'PASS' if passed else 'FAIL'}"
        )

    print("  " + "─" * 66)
    print(
        f"  Overall verdict accuracy  {bar(report.overall_accuracy)} "
        f"{report.overall_accuracy:6.1%}   "
        f"({report.overall_correct}/{report.overall_total} messages)"
    )
    print(
        f"  Claims matched            {report.matched_claims}/{report.gold_claims} gold "
        f"({report.predicted_claims} predicted)"
    )
    print()

    if report.critical_errors:
        print(f"  ✗ {len(report.critical_errors)} CRITICAL ERROR(S)")
        for error in report.critical_errors:
            print(f"      {error}")
        print()
    else:
        print("  ✓ No critical errors "
              "(no false endorsements, no unearned confidence)")
        print()

    if args.verbose:
        print("  Per-claim outcomes")
        print("  " + "─" * 66)
        current_case = None
        for outcome in report.outcomes:
            if outcome.case_id != current_case:
                current_case = outcome.case_id
                print(f"\n  {current_case}")
            if not outcome.matched:
                print(f"    ✗ NOT EXTRACTED  {outcome.gold_gist}")
                continue
            mark = "✓" if outcome.verdict_correct else "✗"
            print(f"    {mark} {outcome.gold_verdict:<22} "
                  f"predicted {outcome.predicted_verdict}")
            print(f"      gold: {outcome.gold_gist}")
            print(f"      pred: {outcome.predicted_text}")
            if outcome.is_critical_error:
                print(f"      CRITICAL: {outcome.critical_reason}")
        print()

    if failures or report.critical_errors:
        print("  RESULT: FAIL")
        for failure in failures:
            print(f"    - {failure}")
        print()
        return 1

    print("  RESULT: PASS — all targets met")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
