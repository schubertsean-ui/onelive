#!/usr/bin/env python3
"""plan_first_banner — SessionStart hook: put the working rules in-context.

Prints the §4a plan-first checklist and the Construction Loop stage order at
the start of every Claude Code session in this repo, so the rules do not
depend on the agent choosing to read them (KAIZEN 2026-08-03
build-before-plan). Always exits 0 — the banner informs; the PreToolUse gate
(tools/plan_first_gate.py) enforces.
"""
BANNER = """\
[plan-first] 1Live session rules (mechanical reminder — OPERATING_RULES §4a + CLAUDE.md):
1. Run `python tools/session_reconcile.py` FIRST; do not trust STATE.md before it.
2. Contract-first: write the Session Contract to STATE.md before any work.
3. PLAN-FIRST (§4a): no substantive build until a plan with WHAT / HOW / WHY /
   WHY-IT-MATTERS / EXPECTED OUTCOMES is presented to and APPROVED by the founder.
   The PreToolUse gate blocks product-file edits until an OPEN contract carries
   those five fields. STATUS: OPEN while building; close it at session end.
4. Construction Loop order (charter item 4): contract -> premortem -> MEMORY
   RETRIEVAL BEFORE design acceptance (cite docs/memory/RED_CLASSES.md matches)
   -> scored path -> small batches -> validate -> evaluator. Retrieval comes
   BEFORE the build, not when construction_gate demands it at validate.
5. Founder-crucial interrupts only: money / new services / legal / trust-invariant
   changes / gate relaxations / go-live / credentials. Everything else: decide,
   log the decision record, proceed — with the plan on the record.
6. When two rules collide (e.g. autonomous posture vs §4a): SURFACE the tension
   to the founder; never resolve it silently toward execution."""

if __name__ == "__main__":
    print(BANNER)
