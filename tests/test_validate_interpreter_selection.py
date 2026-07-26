"""`tools/validate` must not report an environment fault as a code fault.

BAR row G5 is graded **MET** on the claim "one documented command, 0 manual
steps; **0 red rows that mean 'environment incomplete'**". It was not quite true.
`bootstrap_dev.sh` puts the venv OUTSIDE the repo and ends by printing
`PATH="$VENV/bin:$PATH" bash tools/validate`; run the gate without that prefix and
the system interpreter — which on this image cannot import `_cffi_backend` — takes
three checks red (`pytest`, `blocking_failure_check`, `perf`). Same column, same
colour, same word FAIL as a regression. `env_preflight` describes the problem, but
only after a five-minute run has already reported failure.

Measured, not asserted from memory: that is exactly what happened in this session
on 2026-07-26, and the identical tree came back all-PASS the moment the venv was on
PATH. The evidence is the two runs at 22:53:46Z (FAIL) and 22:59:21Z (INCOMPLETE —
every check PASS, only the pre-existing R-002 skip and the commit_sweep advisory)
against the SAME `git_head: 274facb`.

**Why these tests execute the block instead of grepping it.** The R-081 lesson
from earlier in this same PR: a text assertion on a shell conditional passes
whether or not the conditional works, and the negative case that looked like
coverage was refused for the wrong reason. So the region is lifted by sentinel
and run by bash against stub interpreters.

**And why this cannot loosen a gate**, which matters because touching `validate` is
the most gate-adjacent edit there is: the block only ever moves `$PY` to an
interpreter that CAN import the test dependencies. That makes more checks execute,
never fewer, and it touches no threshold, no verdict, no exit code and no skip
accounting — asserted below rather than promised.
"""
from __future__ import annotations

import pathlib
import subprocess

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_VALIDATE = _ROOT / "tools" / "validate"

_BEGIN = "--- interpreter-selection:begin ---"
_END = "--- interpreter-selection:end ---"

# What the block probes for. Kept here so a test failure names the real reason
# rather than "the stub said no".
_PROBE_MODULES = "cryptography.hazmat.primitives.asymmetric.ec"


def _block() -> str:
    """The interpreter-selection region, lifted verbatim between its sentinels."""
    lines = _VALIDATE.read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines) if _BEGIN in ln)
    end = next(i for i, ln in enumerate(lines[start:], start) if _END in ln)
    block = "\n".join(lines[start + 1:end])
    assert 'PY="${PYTHON:-python3}"' in block and "ONELIVE_VENV" in block, (
        "the sentinel-delimited region no longer contains the interpreter "
        "selection — the markers moved and this whole file is now vacuous")
    return block


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
         env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Execute the real block with stubs, and print the interpreter it settled on.

    `venv_works=None` means there is no venv at all — the fresh-clone-without-
    bootstrap case, where the behaviour must be unchanged from before this block
    existed.
    """
    home = tmp_path / "home"
    binadd = tmp_path / "bin"
    _stub(binadd / "python3", works=system_works)
    if venv_works is not None:
        _stub(home / ".venvs" / "onelive" / "bin" / "python", works=venv_works)

    env = {
        "PATH": f"{binadd}:/usr/bin:/bin",
        "HOME": str(home),
        "STUB_LOG": str(tmp_path / "calls.log"),
    }
    env.update(env_extra or {})
    script = "set -u\n" + _block() + '\necho "SELECTED=$PY"\n'
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                          timeout=60, env=env)


def _selected(proc: subprocess.CompletedProcess) -> str:
    line = next((ln for ln in proc.stdout.splitlines()
                 if ln.startswith("SELECTED=")), None)
    assert line is not None, f"block did not complete: {proc.stdout}{proc.stderr}"
    return line.split("=", 1)[1]


# ------------------------------------------------------- the defect this closes
def test_a_broken_default_interpreter_falls_back_to_the_bootstrapped_venv(tmp_path):
    """THE regression. Without this, the run goes red for an environment reason."""
    proc = _run(tmp_path, system_works=False, venv_works=True)
    assert _selected(proc).endswith("/.venvs/onelive/bin/python"), (
        "the system interpreter cannot import the test dependencies and a working "
        "venv exists, but the gate stuck with the broken one — three checks will "
        "now report FAIL with the environment as the cause")


def test_the_fallback_is_ANNOUNCED_and_not_silent(tmp_path):
    """Running something other than what the operator typed is opacity unless it
    is said out loud — and the message has to name the override, or the next
    person debugging a deliberate `PYTHON=` choice has no thread to pull."""
    proc = _run(tmp_path, system_works=False, venv_works=True)
    assert "cannot import the test dependencies" in proc.stdout
    assert ".venvs/onelive/bin/python" in proc.stdout
    assert "PYTHON=" in proc.stdout, "the message must name the override"


# --------------------------------------------- the properties that must NOT move
def test_an_explicit_PYTHON_always_wins(tmp_path):
    """The override is the escape hatch that keeps this from being a policy.

    Someone testing the gate under a deliberately minimal interpreter — which is
    how R-058's preflight was verified — must get the interpreter they asked for,
    even when it is the broken one and a working venv sits right there.
    """
    chosen = _stub(tmp_path / "explicit" / "python3", works=False)
    proc = _run(tmp_path, system_works=False, venv_works=True,
                env_extra={"PYTHON": str(chosen)})
    assert _selected(proc) == str(chosen), (
        "an explicit PYTHON= was overridden — a deliberate interpreter choice "
        "must never be second-guessed, or the block becomes policy rather than "
        "a convenience")


def test_a_WORKING_default_interpreter_is_left_alone(tmp_path):
    """Without this the test above is vacuous: a block that always substituted the
    venv would satisfy it. The venv here is deliberately the BROKEN one, so a
    substitution would be caught even if it happened to be harmless."""
    proc = _run(tmp_path, system_works=True, venv_works=False)
    assert _selected(proc) == "python3", (
        "the default interpreter can run the suite and was replaced anyway")


def test_no_venv_present_changes_nothing(tmp_path):
    """A fresh clone that has not been bootstrapped must behave exactly as it did
    before this block existed: keep `python3`, let the checks report what they
    report, let `env_preflight` name the cause. Inventing an interpreter that is
    not there would be worse than the problem."""
    proc = _run(tmp_path, system_works=False, venv_works=None)
    assert _selected(proc) == "python3"
    assert proc.returncode == 0, (
        "the selection block must never itself fail the run — it is a choice of "
        "interpreter, not a check")


def test_an_UNUSABLE_venv_is_not_selected(tmp_path):
    """A half-built venv — bootstrap interrupted, dependencies not installed — must
    not be preferred over the default. Both are broken; swapping one for the other
    changes the failure message and fixes nothing, and would hide the real cause."""
    proc = _run(tmp_path, system_works=False, venv_works=False)
    assert _selected(proc) == "python3", (
        "a venv that also cannot import the dependencies was selected anyway")


def test_ONELIVE_VENV_is_honoured(tmp_path):
    """`bootstrap_dev.sh` reads `ONELIVE_VENV` for the venv location, so this must
    read the same variable or the two disagree on a non-default setup."""
    custom = tmp_path / "elsewhere"
    _stub(custom / "bin" / "python", works=True)
    proc = _run(tmp_path, system_works=False, venv_works=None,
                env_extra={"ONELIVE_VENV": str(custom)})
    assert _selected(proc) == str(custom / "bin" / "python")


def test_the_block_touches_NOTHING_that_decides_a_verdict():
    """Static, and deliberately so: this is the "no gate was weakened" claim for
    this edit, and it is about what the code CANNOT do, which no execution shows.

    An interpreter choice is legitimate. Reaching a threshold, a skip allowance or
    an exit code from inside it would be a gate change wearing a convenience's
    clothes — and it is exactly the shape a future "while I'm in here" edit takes.
    """
    block = _block()
    forbidden = ("STRICT", "ALLOW_SKIPS", "QUICK", "ANY_FAIL", "ANY_SKIP",
                 "ANY_ADVISORY", "RESULTS", "record ", "run_check", "run_advisory",
                 "exit ")
    present = sorted(token for token in forbidden if token in block)
    assert not present, (
        f"the interpreter-selection block references verdict machinery: {present}. "
        f"It may choose an interpreter and nothing else — anything here that can "
        f"change a check's outcome, the skip accounting or the exit code is a "
        f"gate-threshold change and is founder-crucial (CLAUDE.md)")


def test_the_probe_names_the_submodule_and_not_the_top_level_package():
    """R-058's lesson, in the one place it can regress silently.

    `import cryptography` SUCCEEDS on the broken install — the failure is inside
    `hazmat.primitives.asymmetric.ec`, which is the submodule PyJWT reaches. A
    probe of the top-level package would report a healthy environment and this
    whole block would never fire, while still passing every execution test above
    because the stubs do not care what they are asked to import.
    """
    block = _block()
    assert _PROBE_MODULES in block, (
        f"the probe must import {_PROBE_MODULES} — the top-level `cryptography` "
        f"package imports fine on the exact broken install this exists for, so a "
        f"shallower probe makes the fallback dead code")
    assert "pytest" in block, "an interpreter without pytest cannot run the suite"


@pytest.mark.parametrize("doc", ["docs/BAR.md"])
def test_the_G5_row_no_longer_claims_more_than_is_true(doc):
    """The bar row graded this MET while the footgun was live. The row keeps its
    grade — the claim is now actually true — but it must SAY which mechanism makes
    it true, or the next reader has no way to check."""
    text = (_ROOT / doc).read_text(encoding="utf-8")
    g5 = next(ln for ln in text.splitlines() if ln.startswith("| G5 |"))
    assert "interpreter" in g5.lower(), (
        "BAR G5's mechanism column does not mention interpreter selection, so the "
        "row's '0 red rows that mean environment incomplete' still rests on "
        "env_preflight alone — which describes the fault after a failed run "
        "rather than preventing it")
