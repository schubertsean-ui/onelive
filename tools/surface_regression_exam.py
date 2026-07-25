#!/usr/bin/env python3
"""surface_regression_exam — CLI for the automated surface regression-exam.

SUMMARY: runs the labeled corpus (ai/golden/surface/pages.json) through the REAL
extraction surface (worker/segment.py + worker/ai_extract.extract_candidates)
with a RECORDED provider (no network, no model, no spend) and FAILS LOUD if event
recall drops below any page's measured baseline or any fabrication appears. This
is a deterministic, free no-regression guard on the un-certified SURFACE code —
NOT a certification (the attended golden-exam remains the sole authority for the
certified prompt/model — see docs/RECORD.md R-035). See ai/surface_exam.py for the design
and docs/RECORD.md R-035 for scope.

Exit codes (tools/README.md convention):
  0 = every page met its baseline recall with zero fabrications;
  1 = at least one recall REGRESSION or FABRICATION (the guard fired);
  2 = the exam could not run (corpus missing/unreadable/malformed) — fail loud.

Usage:
  python tools/surface_regression_exam.py
  python tools/surface_regression_exam.py --pages ai/golden/surface/pages.json
  python tools/surface_regression_exam.py --min-recall-floor 0.5
"""
from __future__ import annotations

import argparse
import pathlib
import sys

# Running as a script puts tools/ on sys.path[0], not the repo root; add the
# root so `ai.*` / `worker.*` import exactly as they do under pytest.
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ai.surface_exam import (  # noqa: E402  (path bootstrap must precede import)
    DEFAULT_PAGES_PATH,
    DEFAULT_RECALL_FLOOR,
    load_pages,
    run_surface_exam,
)


def _print_report(report) -> None:
    print("=" * 78)
    print(" OneLive · surface regression-exam (segment.py + ai_extract fan-out)")
    print(" recorded provider · no network · no model · no spend")
    print("=" * 78)
    header = f"  {'STATUS':<7} {'PAGE':<44} {'RECALL':>7} {'BASE':>7} {'REC/EXP':>9} {'FAB':>4}"
    print(header)
    print(f"  {'-' * 7} {'-' * 44} {'-' * 7} {'-' * 7} {'-' * 9} {'-' * 4}")
    for p in report.pages:
        status = "PASS" if p.ok else "FAIL"
        recexp = f"{p.recovered_count}/{p.expected_count}"
        print(f"  {status:<7} {p.id:<44} {p.recall:>7.4f} {p.baseline_recall:>7.4f} "
              f"{recexp:>9} {len(p.fabrications):>4}")
    print("-" * 78)
    for p in report.pages:
        if not p.recall_ok:
            print(f"  REGRESSION: {p.id} recovered {p.recovered_count}/{p.expected_count} "
                  f"events (recall {p.recall:.4f}) below its baseline bar "
                  f"{p.effective_bar:.4f} — the extraction surface got WORSE at "
                  f"recovering events on this page.", file=sys.stderr)
        for fab in p.fabrications:
            print(f"  FABRICATION: {p.id} produced an event matching no labeled "
                  f"event: {fab}", file=sys.stderr)
    print(f"  min_recall_floor={report.min_recall_floor}  "
          f"pages={len(report.pages)}  fabrications={report.fabrication_count}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pages", type=pathlib.Path, default=DEFAULT_PAGES_PATH,
                        help="labeled corpus (default: ai/golden/surface/pages.json)")
    parser.add_argument("--min-recall-floor", type=float, default=DEFAULT_RECALL_FLOOR,
                        help="absolute recall floor applied under the per-page "
                             "baseline ratchet (default 0.0 — a no-op; raising it "
                             "only makes the exam stricter)")
    args = parser.parse_args(argv)

    if not (0.0 <= args.min_recall_floor <= 1.0):
        print(f"surface_regression_exam: INVALID — --min-recall-floor must be in "
              f"[0,1], got {args.min_recall_floor}.", file=sys.stderr)
        return 2
    try:
        pages = load_pages(args.pages)
        report = run_surface_exam(pages, min_recall_floor=args.min_recall_floor)
    except (OSError, ValueError) as exc:
        print(f"surface_regression_exam: INVALID — cannot run the exam ({exc}); a "
              f"guard that cannot run proves nothing.", file=sys.stderr)
        return 2

    _print_report(report)

    if report.ok:
        print("surface_regression_exam: PASS — every page met its baseline recall "
              "with zero fabrications.")
        return 0
    print("surface_regression_exam: FAIL — extraction surface regressed "
          f"({len(report.regressions)} recall regression(s), "
          f"{report.fabrication_count} fabrication(s)). Do not merge on red.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
