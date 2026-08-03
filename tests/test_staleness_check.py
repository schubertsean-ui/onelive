"""Tests for tools/staleness_check.py — the STATE.md disk-truth guard (v2).

v2 measures the real invariant with ZERO tolerance and no magic number: drift =
commits on origin/master since STATE.md was last modified there. The build fails
the moment master advances past the last STATE.md update. Every case runs the REAL
tool against REAL temporary git repos with a real `origin` remote — the gate is
proven to fail on stale master and pass when the tip is a STATE-touching commit
(§9.6 "a gate that cannot fail proves nothing").
"""
import json
import pathlib
import shutil
import subprocess
import sys

_REAL_TOOL = pathlib.Path(__file__).resolve().parent.parent / "tools" / "staleness_check.py"

_STATE_TEMPLATE = """# STATE (test fixture)

<!-- GROUND_TRUTH:BEGIN -->
```json
{json_block}
```
<!-- GROUND_TRUTH:END -->

rev {rev}
"""


def _git(repo: pathlib.Path, *args: str, check=True) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True, check=check)
    return r.stdout.strip()


def _write_state(work: pathlib.Path, marker: str, rev: str = "x") -> None:
    (work / "STATE.md").write_text(_STATE_TEMPLATE.format(
        json_block=json.dumps({"reconciled_through_commit": marker}, indent=2),
        rev=rev))


def _setup(tmp_path):
    """Bare origin + working clone with the tool installed and an initial
    STATE.md pushed to origin/master. Returns (work, first_sha)."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    _git(work, "config", "user.email", "t@t.test")
    _git(work, "config", "user.name", "t")
    _git(work, "checkout", "-q", "-b", "master")
    (work / "tools").mkdir()
    shutil.copy2(_REAL_TOOL, work / "tools" / "staleness_check.py")
    (work / "seed.txt").write_text("0")
    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "c0")
    first = _git(work, "rev-parse", "HEAD")
    # C1 touches STATE.md; marker points at C0 (a real ancestor).
    _write_state(work, first, rev="1")
    _git(work, "add", "STATE.md")
    _git(work, "commit", "-q", "-m", "state update")
    _git(work, "push", "-q", "origin", "master")
    return work, first


def _advance(work: pathlib.Path, touch_state: bool, marker: str | None = None):
    if touch_state:
        _write_state(work, marker or _git(work, "rev-parse", "HEAD"),
                     rev=_git(work, "rev-list", "--count", "HEAD"))
        _git(work, "add", "STATE.md")
        _git(work, "commit", "-q", "-m", "state update")
    else:
        p = work / f"f{_git(work, 'rev-list', '--count', 'HEAD')}.txt"
        p.write_text("x")
        _git(work, "add", ".")
        _git(work, "commit", "-q", "-m", "non-state change")
    _git(work, "push", "-q", "origin", "master")


def _run(work: pathlib.Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(work / "tools" / "staleness_check.py"), *extra],
        capture_output=True, text=True, check=False)


def test_tip_touches_state_passes(tmp_path):
    work, _ = _setup(tmp_path)
    r = _run(work)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OK" in r.stdout


def test_master_advanced_without_state_is_stale(tmp_path):
    work, _ = _setup(tmp_path)
    _advance(work, touch_state=False)  # one merge that does NOT touch STATE.md
    r = _run(work)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "STALE" in r.stderr and "advanced 1" in r.stderr


def test_branch_updating_state_passes_when_master_drifted(tmp_path):
    # Chicken-and-egg: the reconciling branch must pass even though master is behind.
    work, first = _setup(tmp_path)
    _advance(work, touch_state=False)          # origin/master drift 1; HEAD == that commit
    _write_state(work, first, rev="reconcile")  # this branch updates STATE.md (unpushed)
    _git(work, "add", "STATE.md")
    _git(work, "commit", "-q", "-m", "reconcile STATE")
    r = _run(work)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "reconciling at merge" in r.stdout


def test_branch_not_updating_state_fails_when_master_drifted(tmp_path):
    work, _ = _setup(tmp_path)
    _advance(work, touch_state=False)          # origin/master drift 1; HEAD == that commit
    (work / "z.txt").write_text("z")           # a non-STATE commit on the branch
    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "z")
    r = _run(work)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "does not update STATE.md" in r.stderr


def test_two_non_state_commits_report_drift_two(tmp_path):
    work, _ = _setup(tmp_path)
    _advance(work, touch_state=False)
    _advance(work, touch_state=False)
    r = _run(work)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "advanced 2" in r.stderr


def test_state_update_after_drift_restores_current(tmp_path):
    work, _ = _setup(tmp_path)
    _advance(work, touch_state=False)      # drift 1
    _advance(work, touch_state=True)       # STATE updated again → drift 0
    r = _run(work)
    assert r.returncode == 0, r.stdout + r.stderr


def test_tolerance_override_allows_drift(tmp_path):
    work, _ = _setup(tmp_path)
    _advance(work, touch_state=False)      # drift 1
    assert _run(work).returncode == 1
    assert _run(work, "--max-drift", "1").returncode == 0


def test_marker_not_ancestor_of_master_is_stale(tmp_path):
    work, _ = _setup(tmp_path)
    # A commit on a diverged branch, never pushed to origin/master.
    _git(work, "checkout", "-q", "-b", "side")
    (work / "side.txt").write_text("x")
    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "side")
    side = _git(work, "rev-parse", "HEAD")
    _git(work, "checkout", "-q", "master")
    _write_state(work, side)  # marker off master's history (not committed/pushed)
    r = _run(work)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "not an ancestor" in r.stderr


def test_missing_marker_field_is_indeterminate(tmp_path):
    work, _ = _setup(tmp_path)
    (work / "STATE.md").write_text(
        "# STATE\n<!-- GROUND_TRUTH:BEGIN -->\n```json\n{}\n```\n<!-- GROUND_TRUTH:END -->\n")
    assert _run(work).returncode == 2


def test_malformed_marker_is_indeterminate(tmp_path):
    work, _ = _setup(tmp_path)
    _write_state(work, "not-a-sha")
    assert _run(work).returncode == 2


def test_marker_absent_from_clone_is_indeterminate(tmp_path):
    work, _ = _setup(tmp_path)
    _write_state(work, "0" * 40)
    assert _run(work).returncode == 2


def test_no_ground_truth_block_is_indeterminate(tmp_path):
    work, _ = _setup(tmp_path)
    (work / "STATE.md").write_text("# STATE with no ground truth block\n")
    assert _run(work).returncode == 2
