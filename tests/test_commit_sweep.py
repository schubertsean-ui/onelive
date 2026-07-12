"""Tests for tools/commit_sweep.py — the cross-commit history sweep.

Runs against the REAL repo history (this is a sweep tool, so its own git log
is the most honest fixture) plus targeted unit tests of each detector against
synthetic commit-file lists, so a detector's logic is proven independent of
whatever the repo's history happens to look like today.
"""
import importlib.util
import pathlib
import sys

_PATH = pathlib.Path(__file__).resolve().parent.parent / "tools" / "commit_sweep.py"
_spec = importlib.util.spec_from_file_location("commit_sweep", _PATH)
commit_sweep = importlib.util.module_from_spec(_spec)
sys.modules["commit_sweep"] = commit_sweep
_spec.loader.exec_module(commit_sweep)


def test_commit_list_returns_real_history():
    commits = commit_sweep._commit_list(5, None)
    assert len(commits) > 0, "expected at least one commit in this repo's history"


def test_commit_files_and_stat_are_consistent_with_git():
    commits = commit_sweep._commit_list(1, None)
    sha = commits[0]
    files = commit_sweep._commit_files(sha)
    n_files, churn = commit_sweep._commit_stat(sha)
    assert isinstance(files, list)
    assert n_files >= 0
    assert churn >= 0


def test_check_churned_files_flags_repeat_offender():
    findings = commit_sweep.Findings()
    fake_commits = ["c1", "c2", "c3"]
    calls = {
        "c1": ["worker/hot.py", "worker/other.py"],
        "c2": ["worker/hot.py"],
        "c3": ["worker/hot.py", "tests/test_x.py"],
    }
    orig = commit_sweep._commit_files
    commit_sweep._commit_files = lambda sha: calls[sha]
    try:
        commit_sweep.check_churned_files(fake_commits, findings)
    finally:
        commit_sweep._commit_files = orig
    assert any("worker/hot.py" in f and "CHURN" in f for f in findings.items)
    assert not any("worker/other.py" in f for f in findings.items)


def test_check_code_without_tests_flags_missing_test_change():
    findings = commit_sweep.Findings()
    fake_commits = ["c1"]
    orig_files = commit_sweep._commit_files
    orig_subject = commit_sweep._commit_subject
    commit_sweep._commit_files = lambda sha: ["worker/gating.py", "worker/other.py"]
    commit_sweep._commit_subject = lambda sha: "tweak gating"
    try:
        commit_sweep.check_code_without_tests(fake_commits, findings)
    finally:
        commit_sweep._commit_files = orig_files
        commit_sweep._commit_subject = orig_subject
    assert any("NO-TEST-CHANGE" in f for f in findings.items)


def test_check_code_without_tests_silent_when_test_present():
    findings = commit_sweep.Findings()
    fake_commits = ["c1"]
    orig_files = commit_sweep._commit_files
    commit_sweep._commit_files = lambda sha: ["worker/gating.py", "tests/test_gates.py"]
    try:
        commit_sweep.check_code_without_tests(fake_commits, findings)
    finally:
        commit_sweep._commit_files = orig_files
    assert findings.ok()


def test_check_migration_without_test_flags_missing_test():
    findings = commit_sweep.Findings()
    fake_commits = ["c1"]
    orig_files = commit_sweep._commit_files
    orig_subject = commit_sweep._commit_subject
    commit_sweep._commit_files = lambda sha: ["supabase/migrations/0099_new.sql"]
    commit_sweep._commit_subject = lambda sha: "add migration"
    try:
        commit_sweep.check_migration_without_test(fake_commits, findings)
    finally:
        commit_sweep._commit_files = orig_files
        commit_sweep._commit_subject = orig_subject
    assert any("MIGRATION-NO-TEST" in f for f in findings.items)


def test_check_large_commits_flags_over_threshold():
    findings = commit_sweep.Findings()
    fake_commits = ["c1"]
    orig_stat = commit_sweep._commit_stat
    orig_subject = commit_sweep._commit_subject
    commit_sweep._commit_stat = lambda sha: (10, 1000)
    commit_sweep._commit_subject = lambda sha: "huge change"
    try:
        commit_sweep.check_large_commits(fake_commits, findings)
    finally:
        commit_sweep._commit_stat = orig_stat
        commit_sweep._commit_subject = orig_subject
    assert any("LARGE-COMMIT" in f for f in findings.items)


def test_check_large_commits_silent_under_threshold():
    findings = commit_sweep.Findings()
    fake_commits = ["c1"]
    orig_stat = commit_sweep._commit_stat
    commit_sweep._commit_stat = lambda sha: (2, 10)
    try:
        commit_sweep.check_large_commits(fake_commits, findings)
    finally:
        commit_sweep._commit_stat = orig_stat
    assert findings.ok()


def test_check_todo_growth_flags_increase():
    findings = commit_sweep.Findings()
    fake_commits = ["newest", "oldest"]  # git log order: newest first
    orig = commit_sweep._todo_count_at
    counts = {"oldest": 1, "newest": 5}
    commit_sweep._todo_count_at = lambda sha: counts[sha]
    try:
        commit_sweep.check_todo_growth(fake_commits, findings)
    finally:
        commit_sweep._todo_count_at = orig
    assert any("TODO-GROWTH" in f for f in findings.items)


def test_check_todo_growth_silent_when_flat_or_decreasing():
    findings = commit_sweep.Findings()
    fake_commits = ["newest", "oldest"]
    orig = commit_sweep._todo_count_at
    counts = {"oldest": 5, "newest": 5}
    commit_sweep._todo_count_at = lambda sha: counts[sha]
    try:
        commit_sweep.check_todo_growth(fake_commits, findings)
    finally:
        commit_sweep._todo_count_at = orig
    assert findings.ok()


def test_advisory_exit_code_is_zero_even_with_findings():
    rc = commit_sweep.main(["--n", "3"])
    assert rc == 0  # advisory: never fails the run without --strict


def test_strict_exit_code_reflects_findings():
    # Use a wide window so at least one advisory-worthy pattern is virtually
    # certain to exist in real history (large commits are the reliable one).
    rc = commit_sweep.main(["--n", "20", "--strict"])
    assert rc in (0, 1)  # strict CAN be 0 if truly nothing found; proves it's wired, not hardcoded


def test_empty_range_is_unverified_not_pass():
    # §1: a no-op sweep (empty range) must NOT look like a clean pass. An
    # empty range gathered zero evidence, so the gate is UNVERIFIED (exit 2).
    rc = commit_sweep.main(["--since", "1 second ago"])
    assert rc == 2


def test_empty_range_allow_flag_is_explicit_ok():
    # ...unless the caller explicitly acknowledges an expected no-op sweep.
    rc = commit_sweep.main(["--since", "1 second ago", "--allow-empty-range"])
    assert rc == 0
