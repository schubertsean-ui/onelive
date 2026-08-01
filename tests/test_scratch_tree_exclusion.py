"""The .claude scanner exclusion is safe ONLY while tracked code cannot hide in it.

trust_gate and deferral_scan skip any path carrying a ".claude"
COMPONENT — at any depth, because SKIP_PARTS matches path components
(transient parallel-agent worktrees are gitignored scratch clones whose
full repo copies duplicate every allowlisted file at non-allowlisted
paths, PR #51). That exclusion would be a fail-open hole if code could
be COMMITTED under any .claude directory and thereby escape the
repo-wide invariant sweeps: .gitignore governs only untracked files, so
a force-added file would be tracked, executed by nothing, reviewed by
nobody's scanner.

This gate closes the hole at the exclusion's TRUE scope (pre-attack
finding, PR #51: the first version checked only the root .claude/ while
the scanners skip the component at any depth — a guard narrower than
the surface it compensates is a false-confidence gate): every tracked
path in the repository containing a ".claude" component must match the
enumerated prose-only allowlist (root agent definitions,
.claude/agents/*.md — no executable or scannable code shape). And the
pairing is literal, not prose: this suite asserts ".claude" is present
in BOTH scanners' SKIP_PARTS, so dropping either side of the
exclusion/guard pair fails here.
"""

from __future__ import annotations

import pathlib
import re
import subprocess

REPO = pathlib.Path(__file__).resolve().parent.parent

# The ONLY tracked shape permitted to carry a .claude component: root
# prose agent definitions. They hold no executable/scannable code
# (trust_gate sweeps .py; deferral_scan's jurisdiction is code
# comments), and any change to them still reaches the adversarial
# review via the raw PR diff, which has no path filter.
_TRACKED_ALLOWLIST = re.compile(r"^\.claude/agents/[^/]+\.md$")


def tracked_offenders(ls_files_lines: list[str]) -> list[str]:
    """Tracked paths the scanner exclusion would hide from every sweep."""
    return [
        line
        for line in ls_files_lines
        if line
        and ".claude" in pathlib.PurePosixPath(line).parts
        and not _TRACKED_ALLOWLIST.match(line)
    ]


def test_no_tracked_path_hides_behind_the_claude_exclusion():
    # -z: NUL-delimited RAW paths. Plain `git ls-files` QUOTES unusual
    # pathnames (embedded newline, non-ASCII) by default, so a force-added
    # ".claude/evil\n.py" would reach splitlines() as quoted fragments in
    # which no literal .claude component survives — the guard would pass
    # while the scanners skip the file (evaluator r4: a fail-open hole in
    # the compensating guard itself). NUL framing has no quoting mode.
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    offenders = tracked_offenders(out.split("\0"))
    assert offenders == [], (
        f"tracked file(s) carry a .claude path component outside the "
        f"prose-agent-definition allowlist — the scanner exclusion "
        f"(trust_gate/deferral_scan SKIP_PARTS) hides them from every "
        f"repo-wide invariant sweep, so committing them is forbidden: "
        f"{offenders}"
    )


def test_guard_flags_nested_claude_paths_not_just_root():
    """The pre-attack defect shape: a tracked file under a NESTED .claude
    directory (worker/.claude/evil.py) evaded the root-only first guard
    while both scanners skipped it."""
    lines = [
        "worker/.claude/evil.py",
        "tools/.claude/x.py",
        ".claude/worktrees/agent-x/worker/promote.py",
        ".claude/evil.md",
        ".claude/agents/gate-verifier.md",  # allowlisted
        "worker/run_once.py",               # ordinary path, no component
    ]
    assert tracked_offenders(lines) == [
        "worker/.claude/evil.py",
        "tools/.claude/x.py",
        ".claude/worktrees/agent-x/worker/promote.py",
        ".claude/evil.md",
    ]


def test_allowlisted_agent_definitions_pass():
    assert tracked_offenders([".claude/agents/gate-verifier.md"]) == []


def test_newline_pathname_cannot_evade_the_component_check():
    """The r4 evasion shape: with NUL framing, a pathname containing a
    raw newline arrives as ONE string and its .claude component is seen.
    (Under quoted+splitlines parsing it arrived as fragments and vanished.)"""
    raw_nul_output = ".claude/evil\n.py\0worker/run_once.py\0"
    assert tracked_offenders(raw_nul_output.split("\0")) == [
        ".claude/evil\n.py"
    ]


def test_exclusion_and_guard_are_literally_paired():
    """Prose said 'neither ships without the other' — make it mechanism
    (pre-attack nit): dropping ".claude" from either scanner's SKIP_PARTS
    fails here, not just in a comment. Checked by AST literal parse of
    each file's SKIP_PARTS assignment — the file as written, no import
    side effects."""
    import ast

    for tool in ("trust_gate", "deferral_scan"):
        tree = ast.parse(
            (REPO / "tools" / f"{tool}.py").read_text(encoding="utf-8")
        )
        skip_parts = None
        for node in ast.walk(tree):
            # Accept plain and annotated assignment (r4 nit: an AnnAssign
            # refactor must not read as "lost SKIP_PARTS").
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "SKIP_PARTS"
                for t in node.targets
            ):
                skip_parts = ast.literal_eval(node.value)
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "SKIP_PARTS"
                and node.value is not None
            ):
                skip_parts = ast.literal_eval(node.value)
        assert skip_parts is not None, f"tools/{tool}.py lost SKIP_PARTS?"
        assert ".claude" in skip_parts, (
            f"tools/{tool}.py lost the '.claude' SKIP_PARTS entry — the "
            f"exclusion/guard pair is broken (this guard exists BECAUSE of "
            f"that exclusion; remove both together or neither)"
        )


def test_gitignore_keeps_worktrees_untracked():
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert ".claude/worktrees/" in gitignore.splitlines(), (
        ".gitignore lost the .claude/worktrees/ rule — agent scratch trees "
        "would land in git status and pressure a commit that the tracked-"
        "path guard forbids"
    )
