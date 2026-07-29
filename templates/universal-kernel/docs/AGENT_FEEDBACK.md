# AGENT_FEEDBACK — friction the harness caused, recorded at session close

> **KERNEL DOC — project-agnostic, inherited verbatim.** The RULES are
> kernel; the ENTRIES are project data and start empty. Project specifics
> belong in `OVERLAY.md`.

Greppable summary: the standing log where each session records what the
HARNESS made harder than it needed to be — missing tooling, confusing docs,
a gate that fired for the wrong reason, a manual step repeated for the third
time. `docs/OPERATING_RULES.md`'s weekly Kaizen loop ingests this file and
fixes the top items; `docs/SESSION_START.md`'s close step appends to it.

This is deliberately NOT the defect ledger. Defects in the product go to the
Kaizen ledger; deviations from the bar go to `docs/RECORD.md`. This file is
about the *system that builds the system* — friction that costs sessions
time without producing a defect.

## Rules

- **Append, never rewrite.** Entries are dated and kept; a fixed entry gets
  a follow-up line naming the fix, not a deletion.
- **Concrete over general.** "The reconcile step needed a DSN nobody
  documented" beats "setup is confusing."
- **Name the cost.** Minutes lost, or the wrong turn it caused. Friction
  without a cost is a preference, and preferences are not evidence.
- **A third repetition is a rule, not a complaint.** Anything logged three
  times becomes a queued fix with an owner and a trigger, per the weekly
  loop. Logging it a fourth time is the escape.

## Entries

*(none yet — append below at session close, newest last)*

<!--
### YYYY-MM-DD — <one-line friction>
**What happened:** …
**Cost:** …
**Proposed fix (if any):** …  **Repeat count:** 1st | 2nd | 3rd → queue it
-->
