# Gotcha — a RECORD/memory row can itself go stale: verify a claimed mechanical block before obeying it

One-line: R-023/R-065 asserted "any STATE.md edit fails trust-gate" for ~2 weeks after that was no longer true — sessions obeyed a freeze that a later refactor had removed. Verify a claimed gate/block empirically before you let it stop you.

Retrieve this before deferring work because "a gate/record says I can't."

## What happened

STATE.md went ~50 merged PRs stale. The cited reason (R-023, echoed by R-065) was
that the armed-cron smoke binding classified STATE.md as runtime code, so any
STATE.md edit reds trust-gate until a fresh (sandbox-impossible) Actions smoke run.
Sessions therefore parked STATE.md updates into arcs/RECORD instead of editing it.

The belief was **stale**. On 2026-07-24 (Contract #20) `tools/arming_runtime.py`
replaced the coarse denylist with a precise import-closure classifier. STATE.md is
markdown, never imported by the ingest cron, so it is NOT in the runtime set — it
had been freely editable for two weeks. The freeze that stopped everyone no longer
existed; only its record did.

## Root cause

A RECORD row is a claim about a mechanism at the time it was written. When the
mechanism changes, the row does not update itself. Treating "the record says X" as
"X is true now" is the same error as treating a stale STATE.md as ground truth —
`docs/RECORD.md` rows are subject to the same disk-can-drift discipline as any
other claim.

## How it was caught

Empirically, in one command: `python tools/arming_runtime.py` lists the runtime
set — no `.md` file appears — and appending a line to STATE.md then running the
binding test shows STATE.md is not in the binding's diff. A claim that "editing
file F fails gate G" is directly testable; test it.

## The rule

Before you defer work because a gate or a record says you can't:
1. Read the ACTUAL current mechanism (the tool/test), not the record's description
   of it.
2. Reproduce the block if you can (edit the file, run the check). "Findings are
   claims until verified" (§1) applies to blockers too — a claimed obstacle is a
   claim.
3. If the record is wrong, fix the record in the same change (RECORD rows are
   corrected, never left to mislead the next session).
