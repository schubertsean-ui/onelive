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
_NARROWING = ("-k", "-m", "--ignore", "--deselect")


# pytest must appear as an INVOCATION, not merely as a word (e.g.
# "pip install pytest" installs it, it does not run the suite). Accepted forms:
# any `-m pytest …` module invocation, or a bare `pytest …` that starts a
# command (line start, after `run:`, or after a shell separator).
#
# `-m pytest` is matched WITHOUT requiring a literal `python` before it
# (#73 r7): shell runners invoke the interpreter through a variable —
# tools/validate runs `"$PY" -m pytest -q` — and a pattern anchored on the
# literal word `python` silently missed it, which under-reported a real
# blocking gate. `-m pytest` is the precise semantic ("run pytest as a
# module") and stays strict where it matters: `pip install pytest` has no
# `-m` and still does not match.
_INVOCATION = re.compile(
    r"(?:-m\s+pytest|(?:^|[|;&]|\brun:\s*)\s*pytest)\b")

# Commands that EXECUTE what follows them, e.g. `run_check "label" "$PY" -m
# pytest -q` in tools/validate. A wrapper may PRECEDE the interpreter; it
# never substitutes for it.
# ONLY commands whose next non-flag argument IS the command to execute.
# NARROWED at #73 r12 (evaluator): the r11 list also carried bash/sh/zsh and
# poetry/uv/pipenv/hatch/tox, and none of those have that shape —
# `bash $PY -m pytest` runs $PY as a SCRIPT FILE (pytest never starts), and
# `poetry run pytest` puts a subcommand where this walk expects the
# interpreter. Consuming them unconditionally let a line that merely
# RESEMBLES an invocation be credited, which is this class again. They were
# speculative additions never needed by any workflow here: the repo's only
# indirection is tools/validate's `run_check`. Dropping them under-credits
# `poetry run pytest` if it ever appears — the safe direction, and a
# deliberate re-add would come with its own semantics test.
_EXEC_WRAPPERS = frozenset({
    "run_check", "exec", "time", "env", "sudo", "xargs", "nice",
})
_INTERPRETER = re.compile(r"^(?:[\w./-]*python[\w.]*|\$\{?[A-Z_]*PY[A-Z_]*\}?)$")
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Shell separators start a NEW command, so each segment is judged alone.
_SEGMENT = re.compile(r"(?:&&|\|\||[;|&])")


def _segment_runs_full_suite_pytest(seg: str) -> bool:
    """True if THIS command segment actually executes an unfiltered pytest.

    #73 r11, attacker-smuggle seat. The r10 version checked only that the
    segment's FIRST token was an allowed wrapper, then credited any later
    `-m pytest`. That is smuggleable, and the r10 comment claiming it "fails
    conservatively" was false for wrapper forms — all of these were credited
    while executing nothing:
        run_check "pytest (full suite)" echo -m pytest -q
        bash -c echo $PY -m pytest
        time echo $PY -m pytest
        sudo echo -m pytest
    The rule now walks the segment: leading wrappers and VAR=value
    assignments are consumed, and what remains must BE the interpreter
    immediately followed by the `-m pytest` tokens (or a bare `pytest`
    command). A decoy like `echo` is not a wrapper and not an interpreter,
    so it terminates the walk and the segment earns nothing.
    """
    toks = seg.split()
    if toks and toks[0] == "run:":            # YAML `run: python -m pytest`
        toks = toks[1:]
    i = 0
    while i < len(toks) and (toks[i] in _EXEC_WRAPPERS or _ASSIGNMENT.match(toks[i])):
        i += 1
    if i >= len(toks):
        return False
    head, rest = toks[i], toks[i + 1:]
    if _INTERPRETER.match(head):
        # `python -m pytest …` — the -m and pytest must be their own tokens
        # immediately after the interpreter, never a substring elsewhere.
        if len(rest) < 2 or rest[0] != "-m" or rest[1] != "pytest":
            return False
        args = rest[2:]
    elif head == "pytest":
        args = rest
    else:
        return False                          # a decoy command, or not pytest
    # args is a TOKEN LIST here, so match by prefix — `--ignore=tests/x` is
    # one token and plain membership would miss it (#73 r11, self-caught by
    # running the case table rather than reading the diff).
    if any(a == flag or a.startswith(flag + "=") for a in args for flag in _NARROWING):
        return False
    # A bare path argument (tests/…, a file) narrows it; flags (-q) do not.
    return all(tok.startswith("-") or tok.isdigit() for tok in args)


def _normalise(line: str) -> str:
    """Prepare a line for segment analysis.

    Quoted spans are handled by CONTENT, not deleted wholesale (#73 r11 —
    deleting them removed `"$PY"`, the interpreter in tools/validate's real
    invocation, and broke detection of a genuinely blocking gate):
      * a quoted span containing whitespace is a LABEL or message — dropped,
        so `echo "python -m pytest"` keeps nothing to credit;
      * a whitespace-free quoted span is a VALUE — unquoted in place, so
        `run_check "label" "$PY" -m pytest` keeps its interpreter.
    Redirections are then removed so `2>&1` is not mistaken for a shell
    separator by the segment split.
    """
    def _span(m):
        inner = m.group(2)
        return inner if inner and not re.search(r"\s", inner) else " "

    line = re.sub(r"""(['"])(.*?)\1""", _span, line)
    return re.sub(r"\s\d?>>?\s*\S+", " ", line)


def _is_full_suite_pytest(line: str) -> bool:
    s = line.strip()
    if "pytest" not in s or s.startswith("#"):
        return False
    s = _normalise(s)
    if "pytest" not in s:
        return False
    return any(_segment_runs_full_suite_pytest(seg) for seg in _SEGMENT.split(s))


# A workflow can run the full suite INDIRECTLY, by invoking a repo runner
# script that runs it (adversarial-review.yml calls `bash tools/validate`,
# whose own blocking `pytest (full suite)` check reds the job on any failing
# test). Discovering only DIRECT invocations would under-report such a gate
# as non-blocking — dangerous in the reassuring direction, since the tool's
# whole job is to say which gates a failing test reds.
#
# The indirection is RESOLVED, never asserted: a runner counts only if its
# OWN text satisfies the same _is_full_suite_pytest predicate. So if
# tools/validate ever stops running an unfiltered suite, this discovery drops
# it automatically and the report narrows to the truth. Nothing here is a
# hardcoded claim that validate runs tests; it is read from validate.
_RUNNER_SCRIPTS = ("tools/validate",)


def _runner_runs_full_suite(rel_path: str) -> bool:
    """True if a repo runner script itself invokes an unfiltered full suite."""
    try:
        text = (_ROOT / rel_path).read_text(encoding="utf-8")
    except OSError:
        return False  # unreadable runner proves nothing — do not credit it
    return any(_is_full_suite_pytest(ln) for ln in text.splitlines())


# A MENTION is not an INVOCATION (#73 r9, evaluator): `echo "bash
# tools/validate"` or a comment quoting the command must never be credited
# as a gate. Gate-evidence custody fails in the reassuring direction here —
# a false credit reports a failing suite as blocked by a workflow that only
# TALKS about the runner. So the runner must sit in command position:
# at line start, after `run:`, or after a shell separator — and never
# inside quotes.
_RUNNER_INVOCATION = re.compile(
    r"(?:^|[|;&]|\brun:\s*)\s*(?:(?:ba|z|d)?sh|source|\.)?\s*\.?/?(%s)\b"
    % "|".join(re.escape(r) for r in _RUNNER_SCRIPTS))


def _invokes_full_suite_runner(line: str) -> bool:
    s = line.strip()
    if s.startswith("#"):
        return False
    # Strip quoted spans first: anything inside quotes is data, not a command.
    unquoted = re.sub(r"""(['"]).*?\1""", "", s)
    m = _RUNNER_INVOCATION.search(unquoted)
    if not m:
        return False
    return _runner_runs_full_suite(m.group(1))


def full_suite_gates() -> list:
    """Workflow files whose jobs run an UNFILTERED full-suite pytest, directly
    or through a repo runner script that does. Read from the workflow and
    runner files themselves, never hardcoded — if CI changes, so does this."""
    gates = []
    if not _WORKFLOWS.is_dir():
        return gates
    for wf in sorted(_WORKFLOWS.glob("*.yml")):
        try:
            text = wf.read_text(encoding="utf-8")
        except OSError:
            continue
        lines = text.splitlines()
        if any(_is_full_suite_pytest(ln) for ln in lines) or \
                any(_invokes_full_suite_runner(ln) for ln in lines):
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
