# 1Live Failure-Correction Process (non-violable)

Founder 2026-09-09. Outranks chat habit. Coverage Law still outranks scope.
Operating Law still outranks ceremony. This file outranks how a defect is closed.

Universal. Any failure. Any ticket. Any locale.
Tickets run continuously. Alignment checks are independent of tickets.

This process does not belong to Ticket B. Ticket B has a bar.
Success for a miss is written in step 3 for *that* miss.

Global-core Vision: ONE-LIVE-VISION.md plus the 2026-09-08 statement of what 1Live is.
Goals: docs/1Live_Platform_Plan.md. Success catalog: docs/ONE-LIVE-SUCCESS.md.

## The loop (15 steps — do not skip)

1. Find failure — current result is not Success as defined for this work.
2. Determine why — one cause.
3. Define success — the intended result for *this* failure. Write it before the patch.
4. Prescribe the fix — one change that produces that result.
5. Search the fix library — docs/fix-library/ on master.
6. Reuse or create — existing fix wins. New fix only if there is no match.
7. Apply — no stub. No SEE_FILE. No invented clock.
8. Confirm the change exists — file on master. SHA named.
9. Publish to live — ship what this failure needs (site, ingest, or both).
10. Verify publish — production is running that change.
11. Verify the failure is gone — live system matches step 3.
12. Save the fix to the library — failure, cause, fix, SHA, live result.
13. Verify the library entry is on master.
14. If Success — stop.
15. If not Success — return to step 1. Do not pile a second theory.

## Manner (not extra steps)

Definer: 1–4. Librarian: 5, 12–13. Fixer: 6–8. Publisher: 9–11.
M (Monitor): hourly Vision + Goals alignment. Independent of tickets. Does not patch.
Definer is not Fixer. Nobody declares Success except step 11.
GitHub green is not Success. On master is not live.
