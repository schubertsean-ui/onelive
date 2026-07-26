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


# ── a MENTION is not an INVOCATION (#73 r9) ─────────────────────────────────
# Gate-evidence custody fails in the REASSURING direction here: a false
# credit reports a failing suite as blocked by a workflow that only talks
# about the runner. These are the negative cases the r9 evaluator named.

@pytest.mark.parametrize("line", [
    'echo "bash tools/validate"',
    "echo 'bash tools/validate'",
    'echo "run tools/validate now"',
    '# bash tools/validate',
    'echo "see tools/validate for details"',
])
def test_quoted_or_commented_runner_mentions_are_not_gates(line):
    assert bfc._invokes_full_suite_runner(line) is False


@pytest.mark.parametrize("line", [
    'echo "python -m pytest"',
    "echo 'python -m pytest -q'",
    'echo "the suite runs via python -m pytest"',
])
def test_quoted_pytest_mentions_are_not_invocations(line):
    assert bfc._is_full_suite_pytest(line) is False


@pytest.mark.parametrize("line", [
    "bash tools/validate --allow-skips",
    "run: bash tools/validate",
    "./tools/validate",
    "sh tools/validate && echo done",
])
def test_real_runner_invocations_are_still_credited(line):
    assert bfc._invokes_full_suite_runner(line) is True


# ── UNQUOTED mentions are not invocations either (#73 r10) ──────────────────
# r9 stripped quoted spans, which left the harder case open: `echo $PY -m
# pytest` has the SAME token shape as tools/validate's real
# `run_check "label" "$PY" -m pytest -q`, because the interpreter is an
# argument in both. The first token now decides, from an allow-list.

@pytest.mark.parametrize("line", [
    "echo $PY -m pytest",
    "printf %s $PY -m pytest",
    "echo python -m pytest -q",
    "ls python -m pytest",
])
def test_unquoted_pytest_mentions_are_not_invocations(line):
    assert bfc._is_full_suite_pytest(line) is False


@pytest.mark.parametrize("line", [
    'run_check "pytest (full suite)" "$PY" -m pytest -q',
    "python -m pytest -q",
    "run: python -m pytest -q",
    "$PYTHON -m pytest",
    "python -m pytest -q 2>&1 | tee pytest.log",
])
def test_real_pytest_invocations_survive_the_command_position_rule(line):
    assert bfc._is_full_suite_pytest(line) is True


def test_an_unknown_wrapper_fails_CONSERVATIVELY():
    """An unrecognised command word yields False, so the tool credits FEWER
    gates than reality. Under-crediting understates how much a failure
    blocks; over-crediting would claim protection that does not exist —
    which is exactly what the r10 version did for wrapper forms, while its
    comment claimed the opposite."""
    assert bfc._is_full_suite_pytest("weirdrunner $PY -m pytest -q") is False
    assert bfc._segment_runs_full_suite_pytest("weirdrunner $PY -m pytest") is False


# ── ALLOWED-WRAPPER DECOYS (#73 r11, attacker-smuggle seat) ─────────────────
# The r10 rule checked only that a segment's FIRST token was an allowed
# wrapper, then credited any later `-m pytest`. Every line below executed
# NOTHING yet was counted as a blocking full-suite gate — the smuggle path
# being: change tools/validate's `run_check "…" "$PY" -m pytest -q` to
# `run_check "…" echo -m pytest -q`, and the suite silently stops running
# while this detector still reports the runner as a gate.

@pytest.mark.parametrize("decoy", [
    'run_check "pytest (full suite)" echo -m pytest -q',
    "bash -c echo $PY -m pytest",
    "time echo $PY -m pytest",
    "sudo echo -m pytest",
    "env FOO=-m pytest true",
    "xargs echo $PY -m pytest",
])
def test_an_allowed_wrapper_does_not_launder_a_decoy_command(decoy):
    assert bfc._is_full_suite_pytest(decoy) is False


@pytest.mark.parametrize("real", [
    'run_check "pytest (full suite)" "$PY" -m pytest -q',
    "env CI=1 python -m pytest -q",
    "python -m pytest -q 2>&1 | tee pytest.log",
    "python -m pytest",
])
def test_wrappers_still_credit_a_REAL_interpreter_invocation(real):
    assert bfc._is_full_suite_pytest(real) is True


def test_a_quoted_VALUE_survives_while_a_quoted_LABEL_is_dropped():
    """r11 self-caught: deleting every quoted span removed `"$PY"` itself —
    the interpreter in validate's real line — and broke detection of a
    genuinely blocking gate. Spans are now judged by content."""
    assert bfc._normalise('run_check "a label" "$PY" -m pytest').split() == \
        ["run_check", "$PY", "-m", "pytest"]
    assert "pytest" not in bfc._normalise('echo "python -m pytest"')
