"""`tools/validate` must not report an environment fault as a code fault.

BAR G5 is graded MET on "0 red rows that mean 'environment incomplete'". That was not
true: `bootstrap_dev.sh` ends by printing a `PATH=`-prefixed command, and running the
gate without that prefix took `pytest`, `blocking_failure_check` and `perf` red on a
system interpreter that cannot import `_cffi_backend`. Same word FAIL as a regression.
Measured, not asserted: the same tree (`git_head 274facb`) read FAIL at 22:53:46Z and
all-PASS at 22:59:21Z with the venv on PATH.

Tests EXECUTE the block against stub interpreters rather than grepping it — the R-081
lesson from this same PR: a text assertion on a shell conditional passes whether or not
the conditional works.

Why this cannot loosen a gate: the block only ever moves `$PY` to an interpreter that
CAN import the test dependencies, so more checks execute, never fewer. Asserted below,
not promised.
"""
from __future__ import annotations

import pathlib
import re
import subprocess

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_VALIDATE = _ROOT / "tools" / "validate"

_BEGIN = "--- interpreter-selection:begin ---"
_END = "--- interpreter-selection:end ---"

# The submodule PyJWT actually reaches. Probing top-level `cryptography` passes on the
# exact broken install this exists for.
_PROBE_MODULES = "cryptography.hazmat.primitives.asymmetric.ec"


def _block() -> str:
    """The interpreter-selection region, lifted verbatim between its sentinels."""
    lines = _VALIDATE.read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines) if _BEGIN in ln)
    end = next(i for i, ln in enumerate(lines[start:], start) if _END in ln)
    block = "\n".join(lines[start + 1:end])
    assert 'PY="${PYTHON:-python3}"' in block and "ONELIVE_VENV" in block, (
        "the sentinel-delimited region no longer contains the interpreter selection — "
        "the markers moved and this whole file is now vacuous")
    return block


def bootstrap_venv_dir() -> str:
    """Where `bootstrap_dev.sh` ACTUALLY creates the venv, read from the script.

    `CLASS:bootstrap-validate-venv-drift` (r4). The first version of this file
    hard-coded `$HOME/.venvs/onelive` — a path bootstrap never creates — so nine tests
    passed over a fallback that could not fire. Restating a value proves the value you
    restated; deriving it proves the integration.
    """
    text = (_ROOT / "tools" / "bootstrap_dev.sh").read_text(encoding="utf-8")
    match = re.search(r'^VENV="([^"]+)"', text, re.MULTILINE)
    assert match, "no VENV assignment in tools/bootstrap_dev.sh — this extractor is blind"
    return match.group(1)


def _stub(path: pathlib.Path, *, works: bool) -> pathlib.Path:
    """A fake interpreter that either can or cannot import the probe modules."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/bin/sh\n"
        f"echo \"$0 $*\" >> \"$STUB_LOG\"\n"
        f"exit {0 if works else 1}\n",
        encoding="utf-8")
    path.chmod(0o755)
    return path


def _run(tmp_path: pathlib.Path, *, system_works: bool, venv_works: bool | None,
         repo_venv_works: bool | None = None,
         env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Execute the real block with stubs; print the interpreter it settled on.

    `None` for either venv means that venv is absent. `$0` points inside a FAKE REPO so
    the block's own `dirname/..` derivation runs for real — faking the answer would
    leave the thing that was wrong in r4 untested.
    """
    home = tmp_path / "home"
    binadd = tmp_path / "bin"
    fake_repo = tmp_path / "fakerepo"
    (fake_repo / "tools").mkdir(parents=True, exist_ok=True)
    _stub(binadd / "python3", works=system_works)
    if venv_works is not None:
        _stub(home / ".venvs" / "onelive" / "bin" / "python", works=venv_works)
    if repo_venv_works is not None:
        _stub(fake_repo / ".venv" / "bin" / "python", works=repo_venv_works)

    env = {
        "PATH": f"{binadd}:/usr/bin:/bin",
        "HOME": str(home),
        "STUB_LOG": str(tmp_path / "calls.log"),
    }
    env.update(env_extra or {})
    script = "set -u\n" + _block() + '\necho "SELECTED=$PY"\n'
    return subprocess.run(
        ["bash", "-c", script, str(fake_repo / "tools" / "validate")],
        capture_output=True, text=True, timeout=60, env=env)


def _selected(proc: subprocess.CompletedProcess) -> str:
    line = next((ln for ln in proc.stdout.splitlines()
                 if ln.startswith("SELECTED=")), None)
    assert line is not None, f"block did not complete: {proc.stdout}{proc.stderr}"
    return line.split("=", 1)[1]


def test_the_REPO_LOCAL_venv_from_bootstrap_dev_is_found(tmp_path):
    """The r4 blocker, executed: bootstrap writes `$REPO_ROOT/.venv` and the fallback
    must reach it, deriving the repo root the way the block does."""
    proc = _run(tmp_path, system_works=False, venv_works=None, repo_venv_works=True)
    assert _selected(proc) == str(tmp_path / "fakerepo" / ".venv" / "bin" / "python"), (
        "the venv the documented one-command bootstrap creates was not found — the gate "
        "still goes red for an environment reason after that command")


def test_the_repo_local_venv_WINS_over_the_home_one(tmp_path):
    """Both present: prefer what the documented command produced. A stale `$HOME` venv
    from another checkout silently winning is how the r4 miss went unnoticed."""
    proc = _run(tmp_path, system_works=False, venv_works=True, repo_venv_works=True)
    assert _selected(proc) == str(tmp_path / "fakerepo" / ".venv" / "bin" / "python")


def test_a_broken_default_interpreter_falls_back_to_a_working_venv(tmp_path):
    """THE regression. Without this the run goes red for an environment reason."""
    proc = _run(tmp_path, system_works=False, venv_works=True)
    assert _selected(proc).endswith("/.venvs/onelive/bin/python")


def test_the_fallback_is_ANNOUNCED_and_not_silent(tmp_path):
    """Running something other than what the operator typed is opacity unless said out
    loud, and the message must name the override or a deliberate `PYTHON=` choice has no
    thread to pull."""
    proc = _run(tmp_path, system_works=False, venv_works=True)
    assert "cannot import the test dependencies" in proc.stdout
    assert ".venvs/onelive/bin/python" in proc.stdout
    assert "PYTHON=" in proc.stdout


def test_an_explicit_PYTHON_always_wins(tmp_path):
    """The escape hatch that keeps this a convenience rather than a policy: testing the
    gate under a deliberately minimal interpreter is how R-058's preflight was
    verified."""
    chosen = _stub(tmp_path / "explicit" / "python3", works=False)
    proc = _run(tmp_path, system_works=False, venv_works=True, repo_venv_works=True,
                env_extra={"PYTHON": str(chosen)})
    assert _selected(proc) == str(chosen)


def test_a_WORKING_default_interpreter_is_left_alone(tmp_path):
    """Without this the test above is vacuous. The venv here is deliberately the BROKEN
    one, so a substitution is caught even if it happened to be harmless."""
    proc = _run(tmp_path, system_works=True, venv_works=False)
    assert _selected(proc) == "python3"


def test_no_venv_present_changes_nothing(tmp_path):
    """A fresh un-bootstrapped clone must behave exactly as before this block existed:
    keep `python3`, let `env_preflight` name the cause. Inventing an absent interpreter
    would be worse than the problem."""
    proc = _run(tmp_path, system_works=False, venv_works=None)
    assert _selected(proc) == "python3"
    assert proc.returncode == 0, "the selection block must never itself fail the run"


def test_an_UNUSABLE_venv_is_not_selected(tmp_path):
    """A half-built venv must not be preferred: both are broken, so swapping them
    changes the message and hides the real cause."""
    proc = _run(tmp_path, system_works=False, venv_works=False)
    assert _selected(proc) == "python3"


def test_ONELIVE_VENV_is_honoured(tmp_path):
    """`bootstrap_dev.sh` reads `ONELIVE_VENV`, so this must read the same variable or
    the two disagree on a non-default setup."""
    custom = tmp_path / "elsewhere"
    _stub(custom / "bin" / "python", works=True)
    proc = _run(tmp_path, system_works=False, venv_works=None,
                env_extra={"ONELIVE_VENV": str(custom)})
    assert _selected(proc) == str(custom / "bin" / "python")


def test_REPO_ROOT_is_already_set_before_the_selection_block_runs():
    """Closes the gap the executed tests structurally cannot cover.

    The block resolves `${REPO_ROOT:-<derive>}`. Under `bash -c` REPO_ROOT is unset, so
    every test above takes the DERIVE branch — production's branch is never run by them.
    Asserting the ORDER is what makes those tests transferable.
    """
    text = _VALIDATE.read_text(encoding="utf-8")
    assert text.index('REPO_ROOT="$(cd ') < text.index(_BEGIN), (
        "tools/validate assigns REPO_ROOT after the selection block, so the block "
        "re-derives it at runtime — move the assignment back above the block")


def test_validate_looks_where_bootstrap_actually_creates_the_venv():
    """The r4 integration, bound. Static, because what matters is that two files agree
    on a path — an execution test with stubs cannot notice both being pointed at the
    same wrong place."""
    venv = bootstrap_venv_dir()
    block = _block()
    if "REPO_ROOT" in venv:
        assert '"$_repo_root/.venv/bin/python"' in block, (
            f"bootstrap_dev.sh creates the venv at {venv} but the fallback does not "
            f"look in the repo — the documented command still leaves the gate red")
    else:
        assert "ONELIVE_VENV" in block, (
            f"bootstrap creates the venv at {venv}; the fallback does not consult "
            f"ONELIVE_VENV, so the two disagree on the location")


def test_the_block_touches_NOTHING_that_decides_a_verdict():
    """The "no gate was weakened" claim for this edit, and it is about what the code
    CANNOT do, which no execution shows. Reaching a threshold, a skip allowance or an
    exit code from inside an interpreter choice is a gate change wearing a
    convenience's clothes — the shape a "while I'm in here" edit takes."""
    block = _block()
    forbidden = ("STRICT", "ALLOW_SKIPS", "QUICK", "ANY_FAIL", "ANY_SKIP",
                 "ANY_ADVISORY", "RESULTS", "record ", "run_check", "run_advisory",
                 "exit ")
    present = sorted(token for token in forbidden if token in block)
    assert not present, (
        f"the interpreter-selection block references verdict machinery: {present}. It "
        f"may choose an interpreter and nothing else — anything that can change an "
        f"outcome, the skip accounting or the exit code is a gate-threshold change and "
        f"is founder-crucial (CLAUDE.md)")


def test_the_probe_names_the_submodule_and_not_the_top_level_package():
    """R-058's lesson in the one place it regresses silently: `import cryptography`
    SUCCEEDS on the broken install, so a shallower probe makes the fallback dead code
    while still passing every execution test above — the stubs do not care what they
    are asked to import."""
    block = _block()
    assert _PROBE_MODULES in block, f"the probe must import {_PROBE_MODULES}"
    assert "pytest" in block, "an interpreter without pytest cannot run the suite"


@pytest.mark.parametrize("doc", ["docs/BAR.md"])
def test_the_G5_row_names_the_mechanism(doc):
    """The row keeps its MET grade — the claim is now true — but must say which
    mechanism makes it true, or the next reader cannot check it."""
    text = (_ROOT / doc).read_text(encoding="utf-8")
    g5 = next(ln for ln in text.splitlines() if ln.startswith("| G5 |"))
    assert "interpreter" in g5.lower(), (
        "BAR G5's mechanism column does not mention interpreter selection, so its "
        "'0 red rows' claim still rests on env_preflight alone — which describes the "
        "fault after a failed run rather than preventing it")
