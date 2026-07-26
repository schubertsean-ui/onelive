"""Tests for tools/env_preflight.py — telling an incomplete environment from bad code.

v1 done-criterion 3 / BAR G5 / R-058. Four gate rows used to go red in a default
environment for reasons that were not code, and nothing distinguished them from a
real regression.

The property these tests protect hardest is the one that would turn this from a
lens into a loophole: **the preflight must never change a verdict.** It always exits
0, and it must not be reachable as a way to make a failing check look acceptable.
Making a real failure report as an environment fault is a gate relaxation, which
`CLAUDE.md` reserves to the founder.
"""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "env_preflight", _ROOT / "tools" / "env_preflight.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


EP = _load()


# ---------------------------------------------------- it must never gate
def test_it_always_exits_zero_even_when_the_environment_is_broken(monkeypatch, capsys):
    """The whole design rests on this: a lens, never a gate."""
    monkeypatch.setattr(EP, "missing_imports",
                        lambda: [("xdist", "pytest-xdist"), ("yaml", "PyYAML")])
    monkeypatch.setattr(EP, "is_shallow", lambda: True)
    assert EP.main() == 0
    out = capsys.readouterr().out
    assert "MISSING-TOOL" in out and "UNPROVABLE-HERE" in out
    assert "do NOT change the gate's verdict" in out


def test_it_exits_zero_when_everything_is_present(monkeypatch, capsys):
    monkeypatch.setattr(EP, "missing_imports", lambda: [])
    monkeypatch.setattr(EP, "is_shallow", lambda: False)
    assert EP.main() == 0
    assert "about the CODE" in capsys.readouterr().out


def test_it_is_wired_into_validate_as_informational_not_as_a_check():
    """`run_check` would make it blocking. It must be called bare with `|| true`."""
    text = (_ROOT / "tools" / "validate").read_text(encoding="utf-8")
    assert "tools/env_preflight.py" in text
    assert 'run_check "env_preflight"' not in text, \
        "wiring it as a run_check would make an incomplete environment BLOCK, " \
        "which is not what MISSING-TOOL means"
    assert 'run_advisory "env_preflight"' not in text, \
        "advisory rows make validate INCOMPLETE (exit 2) — also wrong for this"
    line = next(ln for ln in text.splitlines() if "tools/env_preflight.py" in ln)
    assert "|| true" in line, f"must not be able to fail the gate: {line!r}"


# ------------------------------------------------- the two fault classes
def test_missing_imports_reports_the_installable_name_not_the_import_name():
    """psycopg2-binary/psycopg2, PyYAML/yaml, PyJWT/jwt — guessing is wrong often
    enough that the mapping has to be explicit, or the fix instruction is useless."""
    assert EP.DEV_IMPORTS["yaml"] == "PyYAML"
    assert EP.DEV_IMPORTS["jwt"] == "PyJWT[crypto]"
    assert EP.DEV_IMPORTS["psycopg2"] == "psycopg2-binary"
    assert EP.DEV_IMPORTS["xdist"] == "pytest-xdist"


def test_every_declared_import_appears_in_requirements_dev():
    """The preflight and the install file must not drift apart — a package the
    preflight demands but the bootstrap never installs is an unfixable red row."""
    req = (_ROOT / "requirements-dev.txt").read_text(encoding="utf-8").lower()
    for name, dist in EP.DEV_IMPORTS.items():
        base = dist.split("[")[0].lower()
        assert base in req, f"{name} maps to {dist}, which requirements-dev.txt lacks"


def test_a_locatable_but_UNIMPORTABLE_module_counts_as_missing(monkeypatch, tmp_path):
    """The 2026-07-26 escape, as a test.

    This tool used `importlib.util.find_spec`, which answers "can the module be
    LOCATED". It printed "every dev dependency importable — any red row below is
    about the CODE" while three gate rows were red because `import jwt` raised: a
    broken distro `cryptography` was perfectly locatable and panicked on import.
    A module that exists and does not work must be reported, or this file is the
    false-confidence gate it was written to prevent.
    """
    (tmp_path / "ep_locatable_but_broken.py").write_text(
        "raise RuntimeError('locatable, not importable')\n", encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    # find_spec's answer — the OLD basis — is that this module is present.
    assert importlib.util.find_spec is not None  # the weaker question exists
    probe = subprocess.run(
        [sys.executable, "-c",
         "import importlib.util,sys;"
         "print(importlib.util.find_spec('ep_locatable_but_broken') is not None)"],
        capture_output=True, text=True, cwd=str(tmp_path))
    assert probe.stdout.strip() == "True", (
        "the fixture is wrong — this module must be LOCATABLE for the test to "
        f"discriminate: {probe.stderr}")
    # ...and the tool must still call it missing.
    assert EP._imports_cleanly("ep_locatable_but_broken") is False
    monkeypatch.setitem(EP.DEV_IMPORTS, "ep_locatable_but_broken", "nope-pkg")
    assert dict(EP.missing_imports()).get("ep_locatable_but_broken") == "nope-pkg"


def test_the_cryptography_probe_targets_the_submodule_the_code_actually_imports():
    """`import cryptography` succeeded on the broken image; the submodule PyJWT
    reaches for did not. Probing the shallow name is what let the lie through."""
    assert "cryptography.hazmat.primitives.asymmetric.ec" in EP.DEV_IMPORTS
    assert "cryptography" not in EP.DEV_IMPORTS, (
        "a bare top-level cryptography probe passes on an installation whose Rust "
        "bindings are unusable — that is the exact false pass of 2026-07-26")


def test_an_import_probe_that_cannot_even_run_reports_missing(monkeypatch):
    """Unanswerable is never optimistic — same discipline as is_shallow()'s None."""
    def boom(*a, **k):
        raise OSError("no interpreter")
    monkeypatch.setattr(EP.subprocess, "run", boom)
    assert EP._imports_cleanly("pytest") is False


def test_missing_imports_finds_a_package_that_is_genuinely_absent(monkeypatch):
    monkeypatch.setitem(EP.DEV_IMPORTS, "definitely_not_installed_xyz", "nope-pkg")
    found = dict(EP.missing_imports())
    assert found.get("definitely_not_installed_xyz") == "nope-pkg"


def test_missing_imports_is_empty_in_this_environment_or_names_real_gaps():
    # Whatever the answer, every entry must be a declared dev dependency rather
    # than an invented one.
    for name, dist in EP.missing_imports():
        assert EP.DEV_IMPORTS[name] == dist


def test_shallow_detection_returns_none_rather_than_guessing(monkeypatch):
    """An unanswerable question is None — never a confident False, which would
    hide a genuinely shallow clone behind a clean report."""
    def boom(*a, **k):
        raise OSError("git not on PATH")
    monkeypatch.setattr(EP.subprocess, "run", boom)
    assert EP.is_shallow() is None

    monkeypatch.setattr(EP.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "boom"))
    assert EP.is_shallow() is None


def test_shallow_detection_parses_git_output(monkeypatch):
    for out, expected in (("true\n", True), ("false\n", False)):
        monkeypatch.setattr(
            EP.subprocess, "run",
            lambda *a, _o=out, **k: subprocess.CompletedProcess(a, 0, _o, ""))
        assert EP.is_shallow() is expected


def test_an_unanswerable_shallow_check_is_still_reported(monkeypatch):
    monkeypatch.setattr(EP, "is_shallow", lambda: None)
    monkeypatch.setattr(EP, "missing_imports", lambda: [])
    _tools, unprovable = EP.report()
    assert unprovable and "could not ask git" in unprovable[0]


def test_the_shallow_row_names_the_test_it_affects_and_calls_it_correct():
    """A newcomer reading a red arming-binding row must learn it is BY DESIGN."""
    import types
    stub = types.SimpleNamespace()
    original = EP.is_shallow
    try:
        EP.is_shallow = lambda: True
        _tools, unprovable = EP.report()
    finally:
        EP.is_shallow = original
    assert unprovable
    row = unprovable[0]
    assert "test_arming_smoke_binding" in row
    assert "fails CLOSED by design" in row and "R-036" in row
    del stub


# ------------------------------------------------------------ bootstrap
def test_the_bootstrap_script_exists_and_installs_the_declared_file():
    script = _ROOT / "tools" / "bootstrap_dev.sh"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "requirements-dev.txt" in text
    assert "--unshallow" in text, "a fresh shallow clone must be repaired too"
    assert "env_preflight.py" in text, "it should prove its own work at the end"


def test_the_venv_the_bootstrap_creates_is_ACTUALLY_gitignored():
    """The script's docstring said ".venv, which is gitignored" and nothing in
    `.gitignore` matched it. `git add -A` after a bootstrap therefore staged 3,979
    files and 874k lines of vendored wheels — a documented property that was simply
    not true, in the one file a newcomer runs first."""
    patterns = {line.strip() for line in
                (_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()}
    assert ".venv/" in patterns, \
        "bootstrap_dev.sh creates ./.venv and calls it gitignored — make that true"
    # And the claim in the script must stay tied to the mechanism.
    text = (_ROOT / "tools" / "bootstrap_dev.sh").read_text(encoding="utf-8")
    assert "gitignored" in text, \
        "if the script stops claiming this, drop the claim from this test too"


def test_the_bootstrap_venv_is_hermetic():
    """`--system-site-packages` let a BROKEN system package satisfy a declared
    requirement, so pip skipped installing a good one and three gate rows went red
    (2026-07-26). Inheriting the system's packages inherits the system's faults.

    The assertion is on the `python -m venv` invocation only: the phrase still
    appears in this file's comments, which explain why it is gone, and in the
    rebuild check below that detects venvs left over from the old recipe.
    """
    text = (_ROOT / "tools" / "bootstrap_dev.sh").read_text(encoding="utf-8")
    creations = [ln for ln in text.splitlines()
                 if "-m venv" in ln and not ln.lstrip().startswith("#")]
    assert creations, "no venv creation line found — this test is checking nothing"
    for line in creations:
        assert "--system-site-packages" not in line, (
            f"the venv must be hermetic: {line.strip()!r}")


def test_the_bootstrap_replaces_a_venv_left_over_from_the_old_recipe():
    """A developer who ran the old script has a poisoned venv on disk. Reusing it
    would silently keep the fault, and "delete your .venv" is manual work the
    charter says to automate away rather than ask for."""
    text = (_ROOT / "tools" / "bootstrap_dev.sh").read_text(encoding="utf-8")
    assert "include-system-site-packages" in text, (
        "nothing detects an inherited-site-packages venv, so re-running the "
        "bootstrap would not repair one")
    assert "rm -rf" in text, "detection with no rebuild is just a nicer error message"
