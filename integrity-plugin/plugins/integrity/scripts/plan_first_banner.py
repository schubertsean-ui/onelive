#!/usr/bin/env python3
"""plan_first_banner (plugin edition) — SessionStart hook.

Injects the operating-integrity rules into every session's opening context so
they never depend on the agent choosing to read them. The banner informs; the
PreToolUse gate (plan_first_gate.py) enforces. Always exits 0.

The full rule set with sources lives in the plugin's charter:
charter/OPERATING_INTEGRITY_CHARTER.md — read it when any rule here needs
its context or verbatim founder anchor.
"""
BANNER = """\
[integrity] Operating rules (mechanical reminder — full charter with sources:
integrity plugin charter/OPERATING_INTEGRITY_CHARTER.md):
1. PLAN-FIRST: no substantive build until a plan (WHAT / HOW / WHY /
   WHY-IT-MATTERS / EXPECTED OUTCOMES) is presented to and APPROVED by the
   founder. The PreToolUse gate blocks product-file edits until the repo's
   STATE file carries an OPEN Session Contract with those five fields.
2. Contract-first: write the Session Contract to the STATE file before work;
   reconcile state against ground truth before trusting it; disk is truth.
3. Proceed on RATIFIED work without asking; interrupt ONLY for founder-crucial
   items (money / new services / legal / trust-invariant changes / gate
   relaxations / go-live / credentials) — and interrupt BEFORE the work.
4. Never end a reply with a dangling "want me to…?" offer — execute in-scope
   work or put it in the plan. No option-menus for the agent's own decisions.
5. Event-driven, never polling: no timers/self-check-ins; bound every API
   list/log call; one signal per question.
6. Honesty floor: never a guessed number; deferrals recorded same-commit;
   copy never outruns the status registry; counts cited by command, not typed.
7. Communicate in the founder's format: WHAT · HOW · WHY · WHY-IT-MATTERS ·
   EXPECTED OUTCOMES; plain language; alternatives named; tradeoffs stated;
   direct links; ONE consolidated ask list.
8. When two rules collide, SURFACE the tension to the founder — never resolve
   it silently toward execution."""

if __name__ == "__main__":
    print(BANNER)
