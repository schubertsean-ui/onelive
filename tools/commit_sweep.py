#!/usr/bin/env python3
"""Cross-commit sweep — higher-level gotchas across recent git history.

Pure stdlib (`git log`/`git show` via subprocess). Scans the last N commits
(default 15; `--n`/`--since`) for patterns invisible to a single-commit diff:
files churned repeatedly (possible instability), commits that touch
worker/ai/api/tools code with no matching test change, new migrations with no
matching new test file, a growing count of TODO/FIXME markers commit-over-
commit, and unusually large commits (churn over a threshold). Advisory by
default (exit 0 always); `--strict` makes findings fail the run (exit 1).
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field

REPO = pathlib.Path(__file__).resolve().parent.parent

CODE_DIRS = ("worker/", "ai/", "api/", "tools/")
TEST_DIR = "tests/"
MIGRATION_DIR = "supabase/migrations/"
LARGE_COMMIT_LINES = 400  # churn (insertions+deletions) considered "large"
CHURN_REPEAT_THRESHOLD = 3  # a file touched this many times in the window flags


@dataclass
class Findings:
    items: list[str] = field(default_factory=list)

    def add(self, msg: str) -> None:
        self.items.append(msg)

    def ok(self) -> bool:
        return not self.items


def _run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=30)
    if p.returncode != 0:
        raise RuntimeError(f"git command failed: {' '.join(cmd)}\n{p.stderr}")
    return p.stdout


def _commit_list(n: int, since: str | None) -> list[str]:
    cmd = ["git", "log", "--format=%H"]
    cmd += ["--since", since] if since else ["-n", str(n)]
    out = _run(cmd).strip()
    return out.splitlines() if out else []


def _commit_files(sha: str) -> list[str]:
    out = _run(["git", "show", "--name-only", "--format=", sha])
    return [l for l in out.splitlines() if l.strip()]


def _commit_stat(sha: str) -> tuple[int, int]:
    """Return (files_changed, total_churn_lines) for a commit via --shortstat."""
    out = _run(["git", "show", "--shortstat", "--format=", sha])
    m = re.search(r"(\d+) files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletions?\(-\))?", out)
    if not m:
        return 0, 0
    files = int(m.group(1) or 0)
    churn = int(m.group(2) or 0) + int(m.group(3) or 0)
    return files, churn


def _commit_subject(sha: str) -> str:
    return _run(["git", "log", "-1", "--format=%s", sha]).strip()


def _todo_count_at(sha: str) -> int:
    """Count TODO/FIXME/XXX occurrences in tracked files at a given commit."""
    try:
        out = _run(["git", "grep", "-I", "-c", "-E", r"(TODO|FIXME|XXX)", sha, "--"])
    except RuntimeError:
        return 0  # git grep exits non-zero when there are zero matches — not an error
    total = 0
    for line in out.splitlines():
        # format: <sha>:<path>:<count>
        parts = line.rsplit(":", 1)
        if len(parts) == 2 and parts[1].strip().isdigit():
            total += int(parts[1])
    return total


def check_churned_files(commits: list[str], findings: Findings) -> None:
    counter: Counter[str] = Counter()
    for sha in commits:
        for f in _commit_files(sha):
            counter[f] += 1
    for f, n in counter.most_common():
        if n >= CHURN_REPEAT_THRESHOLD:
            findings.add(
                f"CHURN: {f} touched in {n} of the last {len(commits)} commits — "
                f"possible instability or a change that keeps needing follow-up fixes."
            )


def check_code_without_tests(commits: list[str], findings: Findings) -> None:
    for sha in commits:
        files = _commit_files(sha)
        code_touched = [f for f in files if f.startswith(CODE_DIRS) and f.endswith(".py")]
        test_touched = [f for f in files if f.startswith(TEST_DIR)]
        if code_touched and not test_touched:
            subject = _commit_subject(sha)
            findings.add(
                f"NO-TEST-CHANGE: {sha[:8]} ({subject!r}) touches "
                f"{', '.join(code_touched[:4])}"
                f"{' ...' if len(code_touched) > 4 else ''} but no file under tests/."
            )


def check_migration_without_test(commits: list[str], findings: Findings) -> None:
    for sha in commits:
        files = _commit_files(sha)
        migrations = [f for f in files if f.startswith(MIGRATION_DIR) and f.endswith(".sql")]
        if not migrations:
            continue
        test_touched = [f for f in files if f.startswith(TEST_DIR)]
        if not test_touched:
            subject = _commit_subject(sha)
            findings.add(
                f"MIGRATION-NO-TEST: {sha[:8]} ({subject!r}) adds/changes "
                f"{', '.join(migrations)} with no corresponding tests/ file in the "
                f"same commit."
            )


def check_todo_growth(commits: list[str], findings: Findings) -> None:
    """Commits are newest-first from git log; walk oldest->newest to see if the
    TODO/FIXME/XXX count is trending up across the window (broken-window drift)."""
    if len(commits) < 2:
        return
    ordered = list(reversed(commits))  # oldest first
    first_count = _todo_count_at(ordered[0])
    last_count = _todo_count_at(ordered[-1])
    if last_count > first_count:
        findings.add(
            f"TODO-GROWTH: TODO/FIXME/XXX marker count grew from {first_count} "
            f"({ordered[0][:8]}) to {last_count} ({ordered[-1][:8]}) over the "
            f"window — broken-window drift (OPERATING_RULES SS1 'no deferred cleanup')."
        )


def check_large_commits(commits: list[str], findings: Findings) -> None:
    for sha in commits:
        files, churn = _commit_stat(sha)
        if churn >= LARGE_COMMIT_LINES:
            subject = _commit_subject(sha)
            findings.add(
                f"LARGE-COMMIT: {sha[:8]} ({subject!r}) churned {churn} lines "
                f"across {files} files (>= {LARGE_COMMIT_LINES}-line threshold) — "
                f"consider whether this should have been split for reviewability."
            )


CHECKS = [
    check_churned_files,
    check_code_without_tests,
    check_migration_without_test,
    check_todo_growth,
    check_large_commits,
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Cross-commit sweep over recent git history.")
    ap.add_argument("--n", type=int, default=15, help="Number of commits to scan (default 15).")
    ap.add_argument("--since", default=None, help="git --since spec (e.g. '2 weeks ago'); overrides --n.")
    ap.add_argument("--strict", action="store_true", help="Exit 1 if any finding is reported (default: advisory, exit 0).")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        commits = _commit_list(args.n, args.since)
    except RuntimeError as exc:
        print(f"commit_sweep.py: FAIL — could not read git history: {exc}", file=sys.stderr)
        return 1  # environment error is loud regardless of --strict

    if not commits:
        print("commit_sweep.py: no commits found in range — nothing to sweep.")
        return 0

    findings = Findings()
    for check in CHECKS:
        check(commits, findings)

    print(f"commit_sweep.py: scanned {len(commits)} commit(s) "
          f"({commits[-1][:8]}..{commits[0][:8]}).")
    if findings.ok():
        print("commit_sweep.py: OK — no cross-commit gotchas found.")
        return 0

    print(f"commit_sweep.py: {len(findings.items)} finding(s) "
          f"({'STRICT — will fail the run' if args.strict else 'advisory only'}):")
    for item in findings.items:
        print(f"  - {item}")

    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
