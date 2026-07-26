#!/usr/bin/env python3
"""Judge a Lighthouse run and an axe run against the BAR's experience numbers.

v1 done-criterion 4 / BAR E1–E4 and P2. Today **nothing** measures the part users
actually touch: load time, INP, CLS and WCAG 2.2 AA. This is the judge; the
measuring is done by `.github/workflows/experience_metrics.yml`, which runs on a
GitHub runner because that is where a browser and open egress both exist.

**The load bar is 2.0 s, not 2.5 s.** The brief's number is 2.0 s; Core Web Vitals'
2.5 s is the floor of external acceptability. **The stricter number wins** — that is
a tightening, not a relaxation, and it is why this tool carries its own constant
rather than deferring to Lighthouse's built-in scoring.

**A missing measurement is never a pass.** If a metric is absent from the report,
that is EXIT 2 (tool error), not a silent skip — a gate that reports success over a
metric it never read is the false-confidence class this repo keeps catching.

Exit codes (`tools/README.md`): 0 = every measured metric within bar; 1 = at least
one outside bar; 2 = could not judge (missing file, unparseable, absent metric).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

# metric key in Lighthouse's audits -> (human name, bar, unit, bar row)
# Values are the BAR's numbers, not Lighthouse's default scoring curves.
THRESHOLDS: dict[str, tuple[str, float, str, str]] = {
    "largest-contentful-paint": ("LCP (load)", 2000.0, "ms", "E1 / P2"),
    "cumulative-layout-shift": ("CLS (visual stability)", 0.1, "", "E3"),
    "total-blocking-time": ("TBT (INP proxy in lab runs)", 200.0, "ms", "E2"),
}

# WCAG 2.2 AA: any violation is a failure. There is no "acceptable number" of
# accessibility violations in a bar that says AA.
MAX_AXE_VIOLATIONS = 0


class JudgeError(Exception):
    """Could not judge — never reported as a pass."""


def _read_json(path: pathlib.Path) -> dict:
    if not path.is_file():
        raise JudgeError(f"{path} does not exist — nothing was measured")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise JudgeError(f"{path} is not readable JSON: {exc}") from exc


def judge_lighthouse(report: dict) -> list[tuple[str, float, float, str, bool]]:
    """Return (name, measured, bar, bar_row, within_bar) for each threshold."""
    audits = report.get("audits")
    if not isinstance(audits, dict):
        raise JudgeError("Lighthouse report has no `audits` object")
    rows = []
    for key, (name, bar, unit, bar_row) in THRESHOLDS.items():
        audit = audits.get(key)
        if not isinstance(audit, dict) or audit.get("numericValue") is None:
            # Absent metric is a tool error, never a quiet skip.
            raise JudgeError(
                f"Lighthouse report has no numeric value for {key!r} ({name}) — "
                f"refusing to report a verdict over a metric that was not measured")
        measured = float(audit["numericValue"])
        rows.append((f"{name} [{unit or 'ratio'}]", measured, bar, bar_row,
                     measured <= bar))
    return rows


def judge_axe(report: object) -> tuple[int, list[str]]:
    """Return (violation count, one summary line per violation)."""
    # @axe-core/cli emits a LIST of page results; the library emits one object.
    pages = report if isinstance(report, list) else [report]
    total, lines = 0, []
    for page in pages:
        if not isinstance(page, dict) or "violations" not in page:
            raise JudgeError(
                "axe report has no `violations` key — refusing to report an "
                "accessibility verdict from a shape this tool does not understand")
        violations = page["violations"]
        if not isinstance(violations, list):
            raise JudgeError(
                "axe report's `violations` is not a list — refusing to count an "
                "accessibility total out of a shape this tool does not understand")
        for violation in violations:
            # A non-dict entry would make `violation.get` raise AttributeError,
            # which escapes as a crash instead of the JudgeError this tool promises
            # (reviewer nit, gemini seat, PR #80). Every unreadable report must
            # arrive as exit 2, never a traceback and never a silent count.
            if not isinstance(violation, dict):
                raise JudgeError(
                    f"axe report contains a non-object violation entry "
                    f"({type(violation).__name__}) — the report shape changed; "
                    f"refusing to report an accessibility verdict from it")
            total += 1
            nodes = violation.get("nodes") or []
            lines.append(
                f"{violation.get('id', '?')} ({violation.get('impact', 'unknown')} "
                f"impact, {len(nodes)} node(s)): "
                f"{violation.get('help', 'no description')}")
    return total, lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lighthouse", type=pathlib.Path, required=True)
    ap.add_argument("--axe", type=pathlib.Path, required=True)
    args = ap.parse_args(argv)

    try:
        lh_rows = judge_lighthouse(_read_json(args.lighthouse))
        axe_count, axe_lines = judge_axe(_read_json(args.axe))
    except JudgeError as exc:
        print(f"experience_thresholds: ERROR — {exc}", file=sys.stderr)
        return 2

    print("| Metric | Measured | Bar | BAR row | Verdict |")
    print("|---|---|---|---|---|")
    failures = []
    for name, measured, bar, bar_row, ok in lh_rows:
        print(f"| {name} | {measured:.1f} | ≤ {bar:.1f} | {bar_row} | "
              f"{'WITHIN BAR' if ok else 'OUTSIDE BAR'} |")
        if not ok:
            failures.append(f"{name}: {measured:.1f} > {bar:.1f} ({bar_row})")
    a11y_ok = axe_count <= MAX_AXE_VIOLATIONS
    print(f"| WCAG 2.2 AA violations | {axe_count} | ≤ {MAX_AXE_VIOLATIONS} | E4 | "
          f"{'WITHIN BAR' if a11y_ok else 'OUTSIDE BAR'} |")
    for line in axe_lines:
        print(f"  - {line}")
    if not a11y_ok:
        failures.append(f"{axe_count} WCAG 2.2 AA violation(s) (E4)")

    print()
    if failures:
        print(f"experience_thresholds: {len(failures)} metric(s) OUTSIDE BAR — this is "
              f"v1 done-criterion 4 not yet met, measured rather than assumed:")
        for line in failures:
            print(f"  - {line}")
        print("  The load bar is the brief's 2.0 s, deliberately stricter than Core "
              "Web Vitals' 2.5 s. Do not widen it — that is founder-crucial.")
        return 1
    print("experience_thresholds: OK — every measured metric is within bar "
          "(BAR E1–E4, P2). v1 done-criterion 4's machine half is met for this run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
