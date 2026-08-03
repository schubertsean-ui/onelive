# Decision — the complete-reading gate: read the governing docs IN FULL before acting

One-line: Rule Zero is a hard gate — read `OPERATING_RULES.md`, `CLAUDE.md`, `CODING_CONVENTIONS.md`, STATE.md, TODOS.md, and any doc the contract points at COMPLETELY, end to end, before building/fixing/answering/merging; a partial read counts as no read.

**Date:** 2026-08-02 (session-opening ritual, reinforced by the 2026-08-03 kickoff). **Authority:** founder-directed (the session-open ritual + `docs/OPERATING_RULES.md` §1 "no research without the primary source" and the Rule Zero opening ritual).

## Why this exists

The recurring, expensive failure mode is acting on a FRAGMENT: reading the first
screen of a doc (or a summary of it), forming a picture, and proceeding — then
discovering the load-bearing constraint was three sections down. The disk holds
the truth; a partial read of the disk is a partial truth, which in this repo is
indistinguishable from a wrong one.

## The gate

Before ANY substantive action in a session:

1. Read the governing canon in full — not the first N lines, not a search hit, the
   whole file. If a file is large (STATE.md is ~800 lines of accreted contracts),
   page through ALL of it; the current contract is often at the top but the
   binding history and open deferrals are not.
2. Confirm in writing what was read completely vs skimmed vs delegated. Honesty
   about coverage is part of the gate — "I read it" must be true.
3. If a primary source can't be accessed, STOP that thread and say so (§1
   primary-source gate) rather than proceeding on a secondary reconstruction.

## What "in full" buys

The 2026-08-03 reconciliation session found the queue's "P0 TOP OF QUEUE" item
(Step 6 golden-set gate) had been RESOLVED for two weeks, and that STATE.md's
"frozen" status was a stale belief — both discoverable only by reading widely and
verifying, not by trusting the top of one doc. Fragment-reading would have had the
agent redo finished work or repeat the freeze myth.

## Transferable rule

Reading is not optional and not partial. If you have not read the whole governing
doc, you do not yet know the constraint — act as if the unread part contains the
one thing that changes your plan, because in this repo it usually does.
