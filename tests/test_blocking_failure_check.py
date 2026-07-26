"""Tests for tools/blocking_failure_check.py — the control that stops a
merge-blocking test failure from being reported as a footnote.

Founder directive (2026-07-25): "Learn from this and generalize it so if this
kind of failure — or similar — happens again it is caught immediately." The
generalized rule: in this repo BOTH required gates run an unfiltered full-suite
pytest, so ANY failing test blocks the merge; "pre-existing" and "recorded as
R-###" are not exemptions.
"""
import importlib.util
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location(
        "blocking_failure_check", _ROOT / "tools" / "blocking_failure_check.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


bfc = _mod()


# ── full-suite detection (the rule is READ from CI, never hardcoded) ─────────

@pytest.mark.parametrize("line,expected", [
    ("run: python -m pytest -q", True),
    ("python -m pytest -q 2>&1 | tee pytest.log", True),
    ("python -m pytest", True),
    ("python -m pytest -q tests/test_gates.py", False),   # path narrows it
    ("python -m pytest -q -k 'not slow'", False),          # -k narrows it
    ("python -m pytest -q -m perf", False),                # -m narrows it
    ("python -m pytest -q --ignore=tests/x", False),       # --ignore narrows it
    ("# python -m pytest -q", False),                      # a comment
    ("pip install pytest", False),                         # not an invocation
    # A shell runner reaching the interpreter through a variable — the exact
    # form in tools/validate, missed until #73 r7 by a `python`-anchored
    # pattern, which under-reported a genuinely blocking gate.
    ('run_check "pytest (full suite)" "$PY" -m pytest -q', True),
    ('run_check "perf benchmarks" "$PY" -m pytest -q -m perf', False),
    ("$PYTHON -m pytest", True),
])
def test_full_suite_pytest_detection(line, expected):
    assert bfc._is_full_suite_pytest(line) is expected


def test_discovers_the_repos_real_full_suite_gates():
    # The live wiring: trust-gate and adversarial-review both run the whole
    # suite, which is WHY any failing test blocks the merge here.
    gates = bfc.full_suite_gates()
    assert "trust-gate.yml" in gates
    # adversarial-review.yml reaches the suite INDIRECTLY, via `bash
    # tools/validate` — it stopped invoking pytest itself at #73 r7 when a
    # duplicate full-suite run was removed. Discovery must still find it,
    # because a failing test still reds that job.
    assert "adversarial-review.yml" in gates


# ── indirect discovery through a runner script ──────────────────────────────

def test_a_workflow_that_only_calls_validate_is_still_discovered():
    """The r7 regression this exists to prevent: removing a workflow's direct
    pytest line must not silently reclassify it as non-blocking."""
    assert bfc._invokes_full_suite_runner("          bash tools/validate --allow-skips")
    assert bfc._invokes_full_suite_runner("run: bash tools/validate")


def test_the_real_validate_script_is_what_makes_that_true():
    """Discovery RESOLVES the indirection rather than asserting it — the
    credit comes from tools/validate's own text, read live."""
    assert bfc._runner_runs_full_suite("tools/validate")


def test_an_unreadable_or_narrowed_runner_earns_no_credit(monkeypatch):
    """Fail-closed: if the runner cannot be read, or stops running an
    unfiltered suite, the workflow must DROP off the blocking list rather
    than keep a stale credit."""
    assert bfc._runner_runs_full_suite("tools/does-not-exist") is False
    monkeypatch.setattr(bfc, "_runner_runs_full_suite", lambda _r: False)
    assert bfc._invokes_full_suite_runner("bash tools/validate") is False


def test_a_commented_out_runner_call_is_not_an_invocation():
    assert bfc._invokes_full_suite_runner("# bash tools/validate") is False


# ── failure parsing + exit contract ─────────────────────────────────────────

def test_parses_failed_and_error_lines():
    report = (
        "....F..\n"
        "FAILED tests/test_a.py::test_one - AssertionError: boom\n"
        "ERROR tests/test_b.py::test_two\n"
        "1 failed, 3 passed\n"
    )
    assert bfc.failing_tests(report) == [
        "tests/test_a.py::test_one", "tests/test_b.py::test_two"]


def test_green_report_exits_zero(tmp_path):
    rep = tmp_path / "r.txt"
    rep.write_text("1558 passed, 30 skipped in 54s\n")
    assert bfc.main(["--report", str(rep)]) == 0


def test_any_failure_exits_nonzero_and_names_the_blocked_gates(tmp_path, capsys):
    rep = tmp_path / "r.txt"
    rep.write_text("FAILED tests/test_x.py::test_y - AssertionError\n1 failed\n")
    rc = bfc.main(["--report", str(rep)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "MERGE-BLOCKING" in err
    assert "trust-gate.yml" in err and "adversarial-review.yml" in err
    # The two invalid downgrades must be refused IN THE OUTPUT — this is the
    # whole point: the wording cannot be softened into a footnote.
    assert "PRE-EXISTING" in err
    assert "Recorded != non-blocking" in err


def test_missing_report_fails_closed(tmp_path):
    assert bfc.main(["--report", str(tmp_path / "nope.txt")]) == 2


def test_list_gates_is_informational_and_exits_zero(capsys):
    assert bfc.main(["--list-gates"]) == 0
    assert "trust-gate.yml" in capsys.readouterr().out


def test_it_is_wired_into_validate():
    # A control nobody runs is not a control.
    assert "blocking_failure_check" in (_ROOT / "tools" / "validate").read_text()
