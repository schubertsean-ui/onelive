#!/usr/bin/env python3
"""plan_first_gate — OFF.

Founder 2026-09-07: ceremony (plan-first, Session Contract, session_reconcile)
was burning the Claude turn budget before any product file landed. Jobs died
on error_max_turns with no branch pushed.

This hook now always allows. Trust gates (trust_gate, lint, pytest, evaluator)
are unchanged. Do not re-wire deny without a founder line.
"""
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

REASON = "ceremony off (founder 2026-09-07): ticket first, not plan-first"


def state_has_open_plan(state_text):
    return True


def decide(hook_input, repo_root=REPO_ROOT, state_text=None):
    return "allow", REASON


def main():
    try:
        json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        pass
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": REASON,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
