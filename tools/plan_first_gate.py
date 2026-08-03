#!/usr/bin/env python3
"""plan_first_gate — PreToolUse hook enforcing OPERATING_RULES §4a mechanically.

SUMMARY: Claude Code invokes this before every Write/Edit (see
.claude/settings.json). It DENIES edits to non-bookkeeping repo files unless
STATE.md carries an OPEN Session Contract containing the five §4a plan fields
(WHAT · HOW · WHY · WHY-IT-MATTERS · EXPECTED OUTCOMES). Bookkeeping files are
exempt so the contract itself, the ledgers, and session-close records can
always be written (founder-approved exemption, 2026-08-03 "Approve").

Origin: KAIZEN 2026-08-03 build-before-plan (founder-caught) — the plan-first
rule's only prior mechanism (construction_gate) fires at validate, the END of a
build; a start-of-work rule needs a start-of-work mechanism. This gate is a
pure tightening: it blocks more, relaxes nothing, and cannot be satisfied by
anything except writing the plan to the record.

Contract: reads the hook JSON on stdin; emits a PreToolUse permissionDecision
JSON on stdout. Fails CLOSED — an unreadable STATE.md denies. Paths outside
the repo (scratchpad, temp) are allowed: the rule governs the record, not
scratch work.

Honest limit (stated in the ledger row and to the founder): this binds Claude
Code sessions in THIS repository. It cannot bind other repositories or other
products; each lane installs its own copy deliberately.
"""
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Bookkeeping surfaces stay writable with no open plan: the contract itself,
# the append-only records, and harness config. Everything else is the product
# and requires the §4a plan on the record first.
BOOKKEEPING = (
    "STATE.md",
    "TODOS.md",
    "docs/ONE_LIVE_CHANGE_LOG.md",
    "docs/RECORD.md",
    "docs/FRICTION_LOG.md",
    "docs/AGENT_FEEDBACK.md",
    "docs/memory/",
    "docs/metrics/",
    "docs/session_arcs/",
    ".claude/",
)

# A contract section satisfies §4a when it is OPEN and carries all five plan
# fields as UPPERCASE labels (case-sensitive on purpose — lowercase "what" in
# ordinary prose must not satisfy the gate). WHY-IT-MATTERS accepts hyphenated
# or spaced spelling; EXPECTED OUTCOMES accepts singular/plural.
FIELD_PATTERNS = (
    r"\bWHAT\b",
    r"\bHOW\b",
    r"\bWHY\b",
    r"\bWHY[- ]IT[- ]MATTERS\b",
    r"\bEXPECTED[- ]OUTCOMES?\b",
)
OPEN_MARKER = re.compile(r"^STATUS:\s*OPEN\b", re.MULTILINE)
SECTION_SPLIT = re.compile(r"^## Session Contract\b", re.MULTILINE)


def state_has_open_plan(state_text):
    """True iff some Session Contract section is OPEN and carries all five
    §4a fields."""
    parts = SECTION_SPLIT.split(state_text)[1:]  # drop preamble
    # Each part runs to the next contract heading; trim at the next H2 that
    # is NOT a contract (split already consumed contract headings).
    for part in parts:
        body = part.split("\n## ", 1)[0]
        if not OPEN_MARKER.search(body):
            continue
        if all(re.search(p, body) for p in FIELD_PATTERNS):
            return True
    return False


def decide(hook_input, repo_root=REPO_ROOT, state_text=None):
    """Return (decision, reason). decision is 'allow' or 'deny'."""
    tool_input = hook_input.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not path:
        return "allow", "no file path in tool input"

    abspath = os.path.abspath(path)
    try:
        rel = os.path.relpath(abspath, repo_root)
    except ValueError:  # different drive (Windows) — outside the repo
        return "allow", "outside repo"
    if rel.startswith(".."):
        return "allow", "outside repo (scratchpad/temp)"
    rel = rel.replace(os.sep, "/")

    for prefix in BOOKKEEPING:
        if rel == prefix or (prefix.endswith("/") and rel.startswith(prefix)):
            return "allow", f"bookkeeping surface ({prefix})"

    if state_text is None:
        try:
            with open(os.path.join(repo_root, "STATE.md"), encoding="utf-8") as f:
                state_text = f.read()
        except OSError as exc:
            return "deny", (
                f"STATE.md unreadable ({exc}) — fail closed: cannot verify an "
                "open §4a plan exists."
            )

    if state_has_open_plan(state_text):
        return "allow", "open Session Contract with the five §4a plan fields found"

    return "deny", (
        f"plan-first gate (OPERATING_RULES §4a): '{rel}' is a product file, and "
        "STATE.md has no OPEN Session Contract carrying the five plan fields "
        "(WHAT / HOW / WHY / WHY-IT-MATTERS / EXPECTED OUTCOMES). Write the "
        "contract with its plan to STATE.md, present the plan to the founder "
        "for approval, then build. Bookkeeping files (STATE.md, TODOS.md, "
        "ledgers, memory) remain writable so you can do exactly that."
    )


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
        # Malformed hook payload: fail closed with a diagnosable message.
        decision, reason = "deny", f"plan_first_gate: unreadable hook input ({exc})"
    else:
        decision, reason = decide(hook_input)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
