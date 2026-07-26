#!/usr/bin/env python3
"""Classify every failing test by its BLOCKING EFFECT, not by its history.

Founder directive (2026-07-25), after I mislabeled a merge-blocking failure:
"Learn from this and generalize it so if this kind of failure — or similar —
happens again it is caught immediately."

THE DEFECT THIS PREVENTS. The `test_arming_smoke_binding` failure was reported
for hours as "pre-existing" and "operational" — language that reads as cosmetic —
when it was in fact the thing blocking the merge. Two rationalizations did the
damage, and BOTH are formally invalid in this repo:

  1. "It's PRE-EXISTING."  Age is not an exemption. A gate does not care when a
     failure started; it cares that the suite is red now.
  2. "It's RECORDED as R-###."  docs/RECORD.md exists to make deviations VISIBLE
     (charter: "no silent deferrals"). Recording a failure never converts it into
     a passing one. Recorded ≠ non-blocking.

THE MECHANICAL RULE. This repo's required gates — `trust-gate.yml` and
`adversarial-review.yml` — each run an UNFILTERED full-suite `python -m pytest`.
Therefore ANY failing test reds BOTH required gates, and there is no such thing
as a "non-blocking" test failure here. That is not a judgement call; it is read
off the workflow files, so it stays true if the workflows change (and if a
workflow ever narrows its pytest invocation, this tool reports fewer gates —
it never assumes).

WHAT THIS TOOL DOES. Discovers the full-suite gate workflows, runs (or ingests)
the test results, and for every failure prints the exact list of required checks
that failure turns RED — then exits non-zero. The output is deliberately worded
so a failure cannot be summarized as a footnote: it names the blocked gates and
states the merge consequence.

Usage:
    python tools/blocking_failure_check.py             # run pytest, classify
    python tools/blocking_failure_check.py --report F  # classify a saved -q report
    python tools/blocking_failure_check.py --list-gates
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_WORKFLOWS = _ROOT / ".github" / "workflows"

# A pytest invocation is FULL-SUITE (every test runs, so any failure reds it)
# unless it narrows the selection with a path argument, -k, -m, or --ignore.
# Substring matching is deliberate and load-bearing: it catches every SPELLING
# of a narrowing option — `--ignore-glob` via `--ignore`, `-mperf` via `-m` —
# without enumerating them. #73 r13 replaced this with exact/`=`-prefix
# matching and silently un-rejected both; reverted at r14.
#
# ADDED at #73 r14 (evaluator): `--collect-only` runs NO tests and `--lf` /
# `--last-failed` runs a cached subset, so crediting either as an unfiltered
# full suite would report protection that is not there. This was a genuine
# pre-existing gap, not a regression.
_NARROWING = ("-k", "-m", "--ignore", "--deselect",
              "--collect-only", "--co", "--lf", "--last-failed", "--ff",
              "--failed-first", "--stepwise", "--sw")


# pytest must appear as an INVOCATION, not merely as a word (e.g.
# "pip install pytest" installs it, it does not run the suite). Accepted forms:
# `python -m pytest …`, or a bare `pytest …` that starts a command (line start,
# after `run:`, or after a shell separator).
_INVOCATION = re.compile(
    r"(?:python[0-9.]*\s+-m\s+pytest|(?:^|[|;&]|\brun:\s*)\s*pytest)\b")


def _is_full_suite_pytest(line: str) -> bool:
    s = line.strip()
    if "pytest" not in s or s.lstrip().startswith("#"):
        return False
    m = _INVOCATION.search(s)
    if not m:
        return False
    # Inspect only the arguments that follow the invocation.
    after = s[m.end():]
    # A pipe/redirect ends the invocation's arguments (e.g. "| tee pytest.log").
    after = re.split(r"[|>;&]", after)[0]
    if any(flag in after for flag in _NARROWING):
        return False
    # A bare path argument (tests/…, a file) narrows it; flags (-q) do not.
    for tok in after.split():
        if not tok.startswith("-") and not tok.isdigit():
            return False
    return True


def full_suite_gates() -> list:
    """Workflow files whose jobs run an UNFILTERED full-suite pytest. Read from
    the workflow files themselves, never hardcoded — if CI changes, so does this."""
    gates = []
    if not _WORKFLOWS.is_dir():
        return gates
    for wf in sorted(_WORKFLOWS.glob("*.yml")):
        try:
            text = wf.read_text(encoding="utf-8")
        except OSError:
            continue
        if any(_is_full_suite_pytest(ln) for ln in text.splitlines()):
            gates.append(wf.name)
    return gates


def _run_pytest() -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no"],
        cwd=str(_ROOT), capture_output=True, text=True,
    )
    return proc.stdout + proc.stderr


def failing_tests(report: str) -> list:
    """Test ids from a pytest -q report's 'FAILED …' / 'ERROR …' summary lines."""
    out = []
    for ln in report.splitlines():
        m = re.match(r"^(FAILED|ERROR)\s+(\S+)", ln.strip())
        if m:
            out.append(m.group(2))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", help="path to a saved `pytest -q` report to classify "
                                     "instead of running the suite")
    ap.add_argument("--list-gates", action="store_true",
                    help="print the discovered full-suite gate workflows and exit 0")
    args = ap.parse_args(argv)

    gates = full_suite_gates()

    if args.list_gates:
        print("full-suite gate workflows (any failing test reds these):")
        for g in gates or ["  (none discovered)"]:
            print(f"  - {g}")
        return 0

    if args.report:
        path = pathlib.Path(args.report)
        if not path.exists():
            print(f"blocking_failure_check: report {path} not found — failing closed.",
                  file=sys.stderr)
            return 2
        report = path.read_text(encoding="utf-8", errors="replace")
    else:
        report = _run_pytest()

    failures = failing_tests(report)
    if not failures:
        print("blocking_failure_check: OK — no failing tests, no gate is blocked.")
        return 0

    if not gates:
        # No full-suite gate found: still a failure, but say so precisely rather
        # than claiming a blocking effect we cannot evidence.
        print(f"blocking_failure_check: {len(failures)} failing test(s), but NO "
              f"full-suite gate workflow was discovered — verify CI wiring before "
              f"treating these as non-blocking.", file=sys.stderr)
        for t in failures:
            print(f"  - {t}", file=sys.stderr)
        return 1

    print("blocking_failure_check: MERGE-BLOCKING TEST FAILURE(S)", file=sys.stderr)
    print("", file=sys.stderr)
    for t in failures:
        print(f"  FAILING: {t}", file=sys.stderr)
    print("", file=sys.stderr)
    print(f"  These turn the following REQUIRED check(s) RED: {', '.join(gates)}",
          file=sys.stderr)
    print("  Each runs an UNFILTERED full-suite pytest, so ANY failing test blocks "
          "the merge.", file=sys.stderr)
    print("", file=sys.stderr)
    print("  NOT valid reasons to downgrade this to a footnote:", file=sys.stderr)
    print("    * 'it is PRE-EXISTING'  — age is not an exemption; the gate is red now.",
          file=sys.stderr)
    print("    * 'it is RECORDED as R-###' — RECORD.md makes a deviation VISIBLE; it "
          "never makes a failing test pass. Recorded != non-blocking.", file=sys.stderr)
    print("", file=sys.stderr)
    print("  Report it as a BLOCKER with its remedy, or fix it. Do not describe it "
          "as 'operational', 'cosmetic', or 'pre-existing' without stating, in the "
          "same breath, that it blocks the merge.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
