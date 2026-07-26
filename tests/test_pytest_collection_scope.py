"""`pytest.ini`'s collection narrowing must hide ONLY inert template tests.

Evaluator blocker (PR #75, CLASS:self-weakenable-gate): `pytest.ini` sets
`testpaths = tests` and `norecursedirs = templates …`, which changes the
repository's collection surface. A prose justification is not a gate — if a
real OneLive test file ever lands outside `tests/`, the narrowing would
silently stop running it and every suite would still report green. That is
the exact shape of a self-weakenable gate: the thing being narrowed is also
the thing that would have complained.

This test binds the narrowing to a checkable claim: every `test_*.py` in the
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


def _all_test_files() -> list[Path]:
    out = []
    for p in ROOT.rglob("test_*.py"):
        rel = p.relative_to(ROOT)
        if any(part in IGNORED_TREES for part in rel.parts):
            continue
        out.append(rel)
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
