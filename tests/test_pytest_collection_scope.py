"""`pytest.ini`'s collection narrowing must hide ONLY inert template tests.

Evaluator blocker (PR #75, CLASS:self-weakenable-gate): `pytest.ini` sets
`testpaths = tests` and `norecursedirs = templates …`, which changes the
repository's collection surface. A prose justification is not a gate — if a
real OneLive test file ever lands outside `tests/`, the narrowing would
silently stop running it and every suite would still report green. That is
the exact shape of a self-weakenable gate: the thing being narrowed is also
the thing that would have complained.

This test binds the narrowing to a checkable claim: every file matching ANY of
pytest's collection patterns (`test_*.py` AND `*_test.py`) in the
repository is either COLLECTED (under `tests/`) or DELIBERATELY EXCLUDED for
a reason enumerated here — never silently dropped.

Honest limit: this proves no test FILE is invisible to the runner. It cannot
prove a collected file's tests are meaningful (that is `tools/test_audit.py`'s
job), and it says nothing about test quality.
"""

from __future__ import annotations

import configparser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Directories excluded from collection ON PURPOSE, each with the reason it is
# inert to OneLive. Adding an entry here is a deliberate, reviewable act.
EXCLUDED_TREES = {
    "templates": (
        "staged, inert template content (see templates/*/STAGING_NOTE.md). Its "
        "tools/ package shadows OneLive's `tools` during collection, and its "
        "self-tests are written to run in the template's OWN checkout, not here."
    ),
}

# Individual files that MATCH pytest's test_*.py pattern but are TOOLS, not
# suites. They are exercised by their own tests under tests/.
TOOL_FILES_NAMED_LIKE_TESTS = {
    "tools/test_audit.py",
}

IGNORED_TREES = {".git", "node_modules", ".venv", "venv", "__pycache__"}


# BOTH of pytest's default `python_files` patterns, not just the first (PR #75
# r11, class self-weakenable-gate). Scanning only `test_*.py` left the guard
# blind to `*_test.py`: someone could add `worker/sneaky_test.py`, which pytest
# collected BEFORE pytest.ini narrowed the scope and silently drops after, and
# this guard would still pass. A compensating control that misses half the
# pattern set is a control that cannot fail on half the cases.
#
# Derived from pytest's own config where available, so a project that widens
# `python_files` automatically widens this guard instead of quietly outgrowing
# it; the defaults are the fallback, never a narrower hand-written list.
def _collection_patterns() -> list[str]:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "pytest.ini")
    declared = ""
    if cfg.has_section("pytest"):
        declared = cfg.get("pytest", "python_files", fallback="").strip()
    patterns = declared.split() if declared else ["test_*.py", "*_test.py"]
    assert patterns, "no collection patterns resolved — the guard would scan nothing"
    return patterns


def _all_test_files() -> list[Path]:
    out = set()
    for pattern in _collection_patterns():
        for p in ROOT.rglob(pattern):
            rel = p.relative_to(ROOT)
            if any(part in IGNORED_TREES for part in rel.parts):
                continue
            out.add(rel)
    return sorted(out)


def test_pytest_ini_declares_the_narrowing_it_relies_on():
    """The config must actually say what the prose claims."""
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "pytest.ini")
    assert cfg.has_section("pytest"), "pytest.ini lost its [pytest] section"
    assert cfg.get("pytest", "testpaths").split() == ["tests"]
    norecurse = cfg.get("pytest", "norecursedirs").split()
    for tree in EXCLUDED_TREES:
        assert tree in norecurse, (
            f"{tree!r} is documented here as deliberately excluded but is not "
            "in pytest.ini's norecursedirs — the two must not drift"
        )


def unaccounted_test_files(files: list[Path]) -> list[str]:
    """THE predicate. Both the live check and its red-case demonstration call
    this — evaluator blocker (r3): a negative test that re-implements the rule
    inline stays green even when the real rule breaks."""
    unaccounted = []
    for rel in files:
        posix = rel.as_posix()
        if rel.parts[0] == "tests":
            continue                                   # collected
        if rel.parts[0] in EXCLUDED_TREES:
            continue                                   # excluded, with a reason
        if posix in TOOL_FILES_NAMED_LIKE_TESTS:
            continue                                   # a tool, not a suite
        unaccounted.append(posix)
    return unaccounted


def test_every_test_file_is_collected_or_deliberately_excluded():
    """No test file may be invisible to the runner without a stated reason."""
    unaccounted = unaccounted_test_files(_all_test_files())

    assert not unaccounted, (
        "test file(s) live outside tests/ and outside every declared exclusion, "
        "so pytest.ini's narrowing silently drops them and the suite still "
        f"reports green: {unaccounted}. Either move them under tests/, or add "
        "the tree to EXCLUDED_TREES here AND to pytest.ini's norecursedirs "
        "with the reason it is inert."
    )


def test_the_excluded_tree_really_does_hold_tests_we_are_skipping():
    """Prove the exclusion is load-bearing, not decorative.

    If `templates/` held no tests at all, this file would be asserting
    nothing and would quietly rot into a false-confidence gate the day the
    staged template is transported out. When that happens this test fails
    LOUDLY, which is the signal to delete the exclusion, not to weaken it.
    """
    staged = [p for p in _all_test_files() if p.parts[0] == "templates"]
    assert staged, (
        "templates/ no longer contains any test files — the pytest.ini "
        "exclusion is now dead weight. If the staged template was transported "
        "out, remove 'templates' from norecursedirs and from EXCLUDED_TREES "
        "above (and delete this test) in the same change."
    )


def test_gate_goes_red_on_a_silently_dropped_test_file():
    """Demonstrate the REAL predicate fails on the defect shape.

    Calls `unaccounted_test_files` — the same function the live check uses —
    so breaking the rule breaks this demonstration too.
    """
    assert unaccounted_test_files([Path("worker/test_sneaky.py")]) == [
        "worker/test_sneaky.py"
    ]
    # And the three accounted-for shapes must NOT be flagged by that same
    # function, or the live check would be vacuous in the other direction.
    assert unaccounted_test_files([
        Path("tests/test_gates.py"),
        Path("templates/universal-kernel/tests/test_kernel_integrity.py"),
        Path("tools/test_audit.py"),
    ]) == []


def test_gate_goes_red_when_a_real_repo_file_would_be_dropped():
    """Strongest form: run the predicate over the LIVE tree with the
    exclusions emptied — every staged template test must then be reported,
    proving the live scan reaches real files and is not silently empty."""
    real = _all_test_files()
    assert real, "the repository scan found no test files at all"
    saved = dict(EXCLUDED_TREES)
    try:
        EXCLUDED_TREES.clear()
        flagged = unaccounted_test_files(real)
    finally:
        EXCLUDED_TREES.update(saved)
    assert any(f.startswith("templates/") for f in flagged), (
        "with exclusions removed the predicate must flag the staged template "
        "tests; it did not, so the live scan is not reaching them"
    )


def test_the_guard_covers_every_pattern_pytest_would_collect(tmp_path, monkeypatch):
    """A guard blind to `*_test.py` cannot fail on `*_test.py` (r11 finding).

    Proven by construction rather than asserted: drop a file matching each
    pattern outside `tests/` and confirm the predicate reports BOTH."""
    import tests.test_pytest_collection_scope as mod
    fake = tmp_path / "repo"
    (fake / "worker").mkdir(parents=True)
    (fake / "worker" / "test_sneaky.py").write_text("def test_x(): pass\n")
    (fake / "worker" / "sneaky_test.py").write_text("def test_y(): pass\n")
    (fake / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")
    monkeypatch.setattr(mod, "ROOT", fake)
    found = {str(p) for p in mod._all_test_files()}
    assert found == {"worker/test_sneaky.py", "worker/sneaky_test.py"}, found
    assert mod.unaccounted_test_files(mod._all_test_files()), (
        "both files sit outside tests/ and neither is an accounted tool file, so "
        "the guard must report them")


def test_the_patterns_come_from_config_when_declared(tmp_path, monkeypatch):
    """A project that widens python_files widens this guard automatically."""
    import tests.test_pytest_collection_scope as mod
    fake = tmp_path / "repo"; fake.mkdir()
    (fake / "pytest.ini").write_text("[pytest]\npython_files = check_*.py\n")
    monkeypatch.setattr(mod, "ROOT", fake)
    assert mod._collection_patterns() == ["check_*.py"]
