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
])
def test_full_suite_pytest_detection(line, expected):
    assert bfc._is_full_suite_pytest(line) is expected


def test_discovers_the_repos_real_full_suite_gates():
    # The live wiring: trust-gate and adversarial-review both run the whole
    # suite, which is WHY any failing test blocks the merge here.
    gates = bfc.full_suite_gates()
    assert "trust-gate.yml" in gates
    assert "adversarial-review.yml" in gates


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
