#!/usr/bin/env python3
"""plan_first_gate (plugin edition) — PreToolUse hook enforcing plan-first.

Portable generalization of onelive's tools/plan_first_gate.py: the target
repo root comes from CLAUDE_PROJECT_DIR (set by Claude Code for hooks) with a
cwd fallback, so the same plugin binds every lane's repo it is enabled in.

Rule enforced (1Live OPERATING_RULES §4a, founder-directed 2026-08-02;
mechanized 2026-08-03 founder "Approve"): edits to product files are DENIED
unless the repo's state file carries an OPEN Session Contract containing the
five plan fields — WHAT / HOW / WHY / WHY-IT-MATTERS / EXPECTED OUTCOMES —
as uppercase labels. Bookkeeping surfaces stay writable so the contract
itself can always be written. Unreadable state file = fail closed. Paths
outside the repo (scratchpad/temp) are allowed.

Per-repo overrides via an optional `.plan-first.json` at the repo root:
  {
    "state_file": "STATE.md",             // default
    "extra_bookkeeping": ["docs/notes/"]  // appended to the defaults
  }
A malformed config fails CLOSED (deny with the parse error) — a broken
override must never silently widen the gate.
"""
import json
import os
import re
import sys

DEFAULT_STATE_FILE = "STATE.md"

DEFAULT_BOOKKEEPING = (
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
    ".plan-first.json",
)

# Uppercase labels on purpose — lowercase prose must not satisfy the gate.
FIELD_PATTERNS = (
    r"\bWHAT\b",
    r"\bHOW\b",
    r"\bWHY\b",
    # Founder-canonical phrasing is WHY-THAT-WHY-MATTERS ("why THAT 'why'
    # matters" — why the stated reason matters; founder-corrected 2026-08-03);
    # WHY-IT-MATTERS is accepted as the common shorthand. Either satisfies.
    r"\bWHY[- ]THAT[- ]WHY[- ]MATTERS\b|\bWHY[- ]IT[- ]MATTERS\b",
    r"\bEXPECTED[- ]OUTCOMES?\b",
)
OPEN_MARKER = re.compile(r"^STATUS:\s*OPEN\b", re.MULTILINE)
SECTION_SPLIT = re.compile(r"^## Session Contract\b", re.MULTILINE)


def repo_root():
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def load_config(root):
    """Return (state_file, bookkeeping_tuple) or raise ValueError on a
    malformed config — the caller turns that into a fail-closed deny."""
    path = os.path.join(root, ".plan-first.json")
    if not os.path.exists(path):
        return DEFAULT_STATE_FILE, DEFAULT_BOOKKEEPING
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)  # json.JSONDecodeError is a ValueError
    if not isinstance(cfg, dict):
        raise ValueError(".plan-first.json must be a JSON object")
    state_file = cfg.get("state_file", DEFAULT_STATE_FILE)
    extra = cfg.get("extra_bookkeeping", [])
    if not isinstance(state_file, str) or not isinstance(extra, list) or \
            not all(isinstance(e, str) for e in extra):
        raise ValueError(".plan-first.json: state_file must be a string and "
                         "extra_bookkeeping a list of strings")
    bookkeeping = DEFAULT_BOOKKEEPING + (state_file,) + tuple(extra)
    return state_file, bookkeeping


def state_has_open_plan(state_text):
    for part in SECTION_SPLIT.split(state_text)[1:]:
        body = part.split("\n## ", 1)[0]
        if not OPEN_MARKER.search(body):
            continue
        if all(re.search(p, body) for p in FIELD_PATTERNS):
            return True
    return False


def decide(hook_input, root=None, state_text=None):
    root = root or repo_root()
    tool_input = hook_input.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not path:
        return "allow", "no file path in tool input"

    abspath = os.path.abspath(path)
    try:
        rel = os.path.relpath(abspath, root)
    except ValueError:
        return "allow", "outside repo"
    if rel.startswith(".."):
        return "allow", "outside repo (scratchpad/temp)"
    rel = rel.replace(os.sep, "/")

    try:
        state_file, bookkeeping = load_config(root)
    except (ValueError, OSError) as exc:
        return "deny", f"plan-first gate: malformed .plan-first.json ({exc}) — fail closed."

    for prefix in bookkeeping:
        if rel == prefix or (prefix.endswith("/") and rel.startswith(prefix)):
            return "allow", f"bookkeeping surface ({prefix})"

    if state_text is None:
        try:
            with open(os.path.join(root, state_file), encoding="utf-8") as f:
                state_text = f.read()
        except OSError as exc:
            return "deny", (
                f"{state_file} unreadable ({exc}) — fail closed: cannot verify "
                "an open plan-first contract exists."
            )

    if state_has_open_plan(state_text):
        return "allow", "open Session Contract with the five plan fields found"

    return "deny", (
        f"plan-first gate: '{rel}' is a product file, and {state_file} has no "
        "OPEN Session Contract carrying the five plan fields (WHAT / HOW / WHY "
        "/ WHY-IT-MATTERS / EXPECTED OUTCOMES). Write the contract with its "
        "plan, present the plan to the founder for approval, then build. "
        "Bookkeeping files remain writable so you can do exactly that."
    )


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
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
