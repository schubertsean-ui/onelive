#!/usr/bin/env python3
"""brain_eval — CLI for the OneLive brain memory eval harness.

SUMMARY: runs the labeled, deterministic memory benchmark (brain/eval/) against
the current brain (brain/) and prints a readable per-category scorecard plus the
overall accuracy, provenance-citation rate, and abstention-correctness. No LLM,
no network, no spend — the numbers are a measured, reproducible fact, which is
the whole point: "world-class brain" becomes something we MEASURE, not assert.

The recorded baselines (brain/eval/baselines.json) are a ONE-WAY RATCHET, the
same shape as tools/surface_regression_exam.py's per-page baselines: the gate
goes RED if ANY category's accuracy drops below its baseline. When the brain
improves, re-measure and RAISE the baseline in the same PR — it only ever goes
up. Gate-custody: evaluator-reviewed on the PR that adds it.

Exit codes (tools/README.md convention):
  0 = every category met or beat its recorded baseline;
  1 = at least one category REGRESSED below baseline (the ratchet fired);
  2 = the eval could not run (baselines missing/unreadable/malformed) — fail loud.

Usage:
  python tools/brain_eval.py
  python tools/brain_eval.py --baselines brain/eval/baselines.json
  python tools/brain_eval.py --show-misses   # also list each missed question
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

# Running as a script puts tools/ on sys.path[0], not the repo root; add the
# root so `brain.*` imports exactly as it does under pytest.
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from brain.eval.benchmark import CATEGORIES  # noqa: E402
from brain.eval.harness import MemoryEvalReport, run_benchmark  # noqa: E402

DEFAULT_BASELINES = _REPO_ROOT / "brain" / "eval" / "baselines.json"
_EPS = 1e-9  # float-safe ratio comparison (accuracies are ratios of integers)


def load_baselines(path: pathlib.Path) -> dict:
    """Load the recorded per-category baselines. Fail LOUD if absent/malformed —
    a ratchet with no floor proves nothing."""
    raw = pathlib.Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    cats = data.get("categories")
    if not isinstance(cats, dict) or not cats:
        raise ValueError(f"brain-eval baselines at {path} have no 'categories' "
                         f"map — refusing to treat that as a valid floor.")
    missing = [c for c in CATEGORIES if c not in cats]
    if missing:
        raise ValueError(f"brain-eval baselines at {path} are missing categories "
                         f"{missing} — every benchmark category needs a floor.")
    return data


def _print_scorecard(report: MemoryEvalReport, baselines: dict,
                     show_misses: bool) -> None:
    cats = baselines["categories"]
    print("=" * 78)
    print(" OneLive · brain memory eval (brain/eval/) · deterministic scorer")
    print(" no LLM · no network · no spend — these numbers are a measured fact")
    print("=" * 78)
    header = f"  {'STATUS':<7} {'CATEGORY':<20} {'SCORE':>7} {'ACC':>7} {'BASE':>7}"
    print(header)
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
    parser.add_argument("--baselines", type=pathlib.Path, default=DEFAULT_BASELINES,
                        help="recorded baseline floors (default: brain/eval/baselines.json)")
    parser.add_argument("--show-misses", action="store_true",
                        help="also list every question the brain missed")
    args = parser.parse_args(argv)

    try:
        baselines = load_baselines(args.baselines)
    except (OSError, ValueError) as exc:
        print(f"brain_eval: INVALID — cannot load baselines ({exc}); a ratchet "
              f"with no floor proves nothing.", file=sys.stderr)
        return 2

    report = run_benchmark()
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
            print(f"brain_eval: REGRESSION — {cat} accuracy {acc:.4f} dropped below "
                  f"its recorded baseline {base:.4f}. The brain got WORSE at this "
                  f"memory competency. Do not merge on red.", file=sys.stderr)
        return 1

    print("brain_eval: PASS — every category met or beat its recorded baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
