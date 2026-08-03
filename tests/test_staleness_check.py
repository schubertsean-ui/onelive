"""Tests for tools/staleness_check.py — the STATE.md disk-truth guard.

Every case runs the REAL tool against a REAL temporary git repo (no mocks of
git), so the gate is proven to fail on a stale marker and pass on a fresh one —
§9.6 "a gate that cannot fail proves nothing". The tool derives its repo root
from its own location, so each test copies it into <tmp>/tools/ and runs it
there against a <tmp> git history.
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
"""


def _git(repo: pathlib.Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def _init_repo(repo: pathlib.Path, n_commits: int) -> list[str]:
    """Create a git repo with n_commits linear commits; return their shas
    (oldest first)."""
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.test")
    _git(repo, "config", "user.name", "t")
    shas = []
    for i in range(n_commits):
        (repo / f"f{i}.txt").write_text(str(i))
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", f"c{i}")
        shas.append(_git(repo, "rev-parse", "HEAD"))
    return shas


def _install_tool(repo: pathlib.Path) -> pathlib.Path:
    (repo / "tools").mkdir(exist_ok=True)
    dest = repo / "tools" / "staleness_check.py"
    shutil.copy2(_REAL_TOOL, dest)
    return dest


def _write_state(repo: pathlib.Path, block: dict) -> None:
    (repo / "STATE.md").write_text(
        _STATE_TEMPLATE.format(json_block=json.dumps(block, indent=2)))


def _run(repo: pathlib.Path, *extra: str) -> subprocess.CompletedProcess:
    tool = repo / "tools" / "staleness_check.py"
    return subprocess.run([sys.executable, str(tool), *extra],
                          capture_output=True, text=True, check=False)


def test_fresh_marker_at_head_passes(tmp_path):
    repo = tmp_path / "r"
    shas = _init_repo(repo, 3)
    _install_tool(repo)
    _write_state(repo, {"reconciled_through_commit": shas[-1]})
    r = _run(repo)
    assert r.returncode == 0, r.stderr
    assert "OK" in r.stdout


def test_marker_within_threshold_passes(tmp_path):
    repo = tmp_path / "r"
    shas = _init_repo(repo, 6)
    _install_tool(repo)
    # marker is 3 commits behind HEAD, threshold 5 → OK
    _write_state(repo, {"reconciled_through_commit": shas[2]})
    r = _run(repo, "--max-commits", "5")
    assert r.returncode == 0, r.stderr


def test_marker_too_far_behind_is_stale(tmp_path):
    repo = tmp_path / "r"
    shas = _init_repo(repo, 8)
    _install_tool(repo)
    # marker is 7 commits behind HEAD, threshold 3 → STALE (exit 1)
    _write_state(repo, {"reconciled_through_commit": shas[0]})
    r = _run(repo, "--max-commits", "3")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "STALE" in r.stderr


def test_marker_not_ancestor_is_stale(tmp_path):
    repo = tmp_path / "r"
    _init_repo(repo, 2)
    base = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")  # default branch name
    # Create a diverged branch, get its tip, then return to the base branch.
    _git(repo, "checkout", "-q", "-b", "side")
    (repo / "side.txt").write_text("x")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "side")
    side_sha = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", base)
    _install_tool(repo)  # install last so it's present on the checked-out branch
    _write_state(repo, {"reconciled_through_commit": side_sha})
    r = _run(repo)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "not an ancestor" in r.stderr


def test_missing_marker_field_is_indeterminate(tmp_path):
    repo = tmp_path / "r"
    _init_repo(repo, 2)
    _install_tool(repo)
    _write_state(repo, {"git": {"head": "x"}})  # no reconciled_through_commit
    r = _run(repo)
    assert r.returncode == 2, r.stdout + r.stderr


def test_malformed_marker_is_indeterminate(tmp_path):
    repo = tmp_path / "r"
    _init_repo(repo, 2)
    _install_tool(repo)
    _write_state(repo, {"reconciled_through_commit": "not-a-sha"})
    r = _run(repo)
    assert r.returncode == 2, r.stdout + r.stderr


def test_marker_absent_from_clone_is_indeterminate(tmp_path):
    repo = tmp_path / "r"
    _init_repo(repo, 2)
    _install_tool(repo)
    # A syntactically valid sha that does not exist in this repo → fail closed.
    _write_state(repo, {"reconciled_through_commit": "0" * 40})
    r = _run(repo)
    assert r.returncode == 2, r.stdout + r.stderr


def test_no_ground_truth_block_is_indeterminate(tmp_path):
    repo = tmp_path / "r"
    _init_repo(repo, 2)
    _install_tool(repo)
    (repo / "STATE.md").write_text("# STATE with no ground truth block\n")
    r = _run(repo)
    assert r.returncode == 2, r.stdout + r.stderr
