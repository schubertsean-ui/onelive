#!/usr/bin/env python3
"""brain_held_out_eval — the BLIND judge for the OneLive brain memory eval.

SUMMARY: runs the HELD-OUT (hidden) memory benchmark (brain/eval/held_out.py +
brain/eval/held_out_pages.json) against the current brain (brain/) and prints a
per-category scorecard, exiting 0 (every category met its floor) / 1 (a category
regressed below floor) / 2 (the eval could not run). Same deterministic scorer as
tools/brain_eval.py — no LLM, no network, no spend.

WHY A SECOND, HELD-OUT EVAL (the anti-gaming point):
  tools/brain_eval.py scores the VISIBLE benchmark (brain/eval/benchmark.py),
  which is committed and readable. A self-optimizing agent could overfit those
  exact questions and post a fake improvement. This eval scores a DISJOINT set
  (no shared question text or gold answer), so a brain that merely memorized the
  visible questions does NOT pass here — overfitting the dev set is caught.

AUTHORITY vs DEV MIRROR (read this before trusting a local green):
  Running THIS file locally is a DEV MIRROR — useful, but NOT the trust anchor,
  because the same PR that changes the brain can also change this script, the
  held-out corpus, or the scorer. The AUTHORITY is the BASE-owned run in
  .github/workflows/brain-held-out-eval.yml (pull_request_target): it scores the
  PR HEAD's brain using the BASE ref's copy of the held-out set + scorer, so a PR
  cannot grade itself. Mirrors the golden-set exam pattern (the ai/ exam
  runner + .github/workflows/extraction-eval.yml).

The floors (brain/eval/held_out_pages.json -> baselines.categories) are a ONE-WAY
RATCHET: when the brain improves, RE-MEASURE and RAISE the floor in the same PR
(it only ever goes up). Gate-custody: evaluator-reviewed on the PR that adds it.

Exit codes (tools/README.md convention):
  0 = every category met or beat its recorded floor;
  1 = at least one category REGRESSED below its floor (the ratchet fired);
  2 = the eval could not run (corpus/floors missing/unreadable/malformed) — loud.

Usage:
  python tools/brain_held_out_eval.py
  python tools/brain_held_out_eval.py --show-misses   # also list each miss
"""
from __future__ import annotations

import argparse
import pathlib
import sys

# Running as a script puts tools/ on sys.path[0], not the repo root; add the
# root so `brain.*` imports exactly as it does under pytest.
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from brain.eval.benchmark import CATEGORIES  # noqa: E402
from brain.eval.harness import MemoryEvalReport  # noqa: E402

_EPS = 1e-9  # float-safe ratio comparison (accuracies are ratios of integers)


def _print_scorecard(report: MemoryEvalReport, baselines: dict,
                     show_misses: bool) -> None:
    cats = baselines["categories"]
    print("=" * 78)
    print(" OneLive · brain memory eval — HELD-OUT (hidden) set · blind judge")
    print(" disjoint from the visible benchmark · deterministic · no LLM/net/spend")
    print(" authority = BASE-run .github/workflows/brain-held-out-eval.yml")
    print("=" * 78)
    print(f"  {'STATUS':<7} {'CATEGORY':<20} {'SCORE':>7} {'ACC':>7} {'FLOOR':>7}")
    print(f"  {'-' * 7} {'-' * 20} {'-' * 7} {'-' * 7} {'-' * 7}")
    for cat in CATEGORIES:
        cs = report.per_category[cat]
        base = float(cats[cat])
        ok = cs.accuracy + _EPS >= base
        status = "PASS" if ok else "FAIL"
        score = f"{cs.n_correct}/{cs.n_total}"
        print(f"  {status:<7} {cat:<20} {score:>7} {cs.accuracy:>7.4f} {base:>7.4f}")
    print("-" * 78)
    print(f"  overall accuracy         : {report.overall_accuracy:.4f} "
          f"({sum(1 for r in report.results if r.correct)}/{report.n_total})")
    print(f"  provenance citation rate : {report.provenance_citation_rate:.4f}")
    print(f"  abstention correctness   : {report.abstention_correctness:.4f}")
    print("-" * 78)
    if show_misses:
        misses = [r for r in report.results if not r.correct]
        if not misses:
            print("  no missed questions.")
        for r in misses:
            print(f"  MISS [{r.category}] {r.id}: {r.text}")
        print("-" * 78)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--show-misses", action="store_true",
                        help="also list every question the brain missed")
    args = parser.parse_args(argv)

    # Import inside main so a corpus/import problem surfaces as a clean exit 2
    # (loud), not an import-time traceback that a caller might misread.
    try:
        from brain.eval.held_out import (
            HeldOutError,
            held_out_baselines,
            run_held_out,
        )
        baselines = held_out_baselines()
    except Exception as exc:  # HeldOutError or an import-time failure
        # A held-out eval that cannot even load its hidden set / floors must
        # FAIL LOUD — never look like a pass (fail closed).
        name = type(exc).__name__
        print(f"brain_held_out_eval: INVALID — cannot load the held-out "
              f"benchmark ({name}: {exc}); a blind judge with no test set or no "
              f"floor proves nothing.", file=sys.stderr)
        return 2

    try:
        report = run_held_out()
    except HeldOutError as exc:
        print(f"brain_held_out_eval: INVALID — held-out run failed ({exc}).",
              file=sys.stderr)
        return 2

    _print_scorecard(report, baselines, args.show_misses)

    cats = baselines["categories"]
    regressed = []
    for cat in CATEGORIES:
        acc = report.per_category[cat].accuracy
        base = float(cats[cat])
        if acc + _EPS < base:
            regressed.append((cat, acc, base))

    if regressed:
        for cat, acc, base in regressed:
            print(f"brain_held_out_eval: REGRESSION — {cat} accuracy {acc:.4f} "
                  f"dropped below its recorded held-out floor {base:.4f}. The "
                  f"brain got WORSE at this memory competency on the HIDDEN set "
                  f"(this is NOT game-able by overfitting the visible questions). "
                  f"Do not merge on red.", file=sys.stderr)
        return 1

    print("brain_held_out_eval: PASS — every category met or beat its recorded "
          "held-out floor (hidden set; overfitting the visible set would not "
          "achieve this).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
