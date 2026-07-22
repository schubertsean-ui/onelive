"""The .claude/ scanner exclusion is safe ONLY while nothing tracked lives there.

trust_gate and deferral_scan skip ".claude" (transient parallel-agent
worktrees — gitignored scratch clones whose full repo copies duplicate
every allowlisted file at non-allowlisted paths, PR #51). That exclusion
would be a fail-open hole if code could be COMMITTED under .claude/ and
thereby escape the repo-wide invariant sweeps: .gitignore governs only
untracked files, so a force-added file would be tracked, executed by
nothing, reviewed by nobody's scanner. This gate closes the hole: every
tracked path under .claude/ must match the enumerated prose-only
allowlist (agent definitions, .claude/agents/*.md — no executable or
scannable code shape), and the ignore rule that keeps the scratch trees
untracked must stay present. Committing anything else under .claude/
fails the suite — the exclusion and this guard are a pair; neither ships
without the other.
"""

from __future__ import annotations

import pathlib
import re
import subprocess

REPO = pathlib.Path(__file__).resolve().parent.parent

# The ONLY tracked shapes permitted under .claude/: prose agent
# definitions. They carry no executable/scannable code (trust_gate sweeps
# .py; deferral_scan's jurisdiction is code comments), and any change to
# them still reaches the adversarial review via the raw PR diff, which has
# no path filter — visibility does not depend on the scanners.
_TRACKED_ALLOWLIST = re.compile(r"^\.claude/agents/[^/]+\.md$")


def test_tracked_dot_claude_files_are_prose_agent_definitions_only():
    out = subprocess.run(
        ["git", "ls-files", ".claude"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    offenders = [
        line
        for line in out.splitlines()
        if line and not _TRACKED_ALLOWLIST.match(line)
    ]
    assert offenders == [], (
        f"tracked file(s) under .claude/ outside the prose-agent-definition "
        f"allowlist — the scanner exclusion (trust_gate/deferral_scan "
        f"SKIP_PARTS) would hide them from every repo-wide invariant sweep, "
        f"so committing them is forbidden: {offenders}"
    )


def test_gitignore_keeps_worktrees_untracked():
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert ".claude/worktrees/" in gitignore.splitlines(), (
        ".gitignore lost the .claude/worktrees/ rule — agent scratch trees "
        "would land in git status and pressure a commit that "
        "test_no_tracked_files_under_dot_claude forbids"
    )
