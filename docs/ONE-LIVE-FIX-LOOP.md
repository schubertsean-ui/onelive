# 1Live Failure-Correction Process (non-violable)

Universal. Any failure. Any ticket. Any locale. Ceremony off.

## Proof

Step 11 is the Showing line on https://1live.co (or that locale). A commit is not proof.

## The loop (15 steps — do not skip)

1. **Find failure** — The current result is not Success as defined for this work.
2. **Determine why** — One cause.
3. **Define success** — Write the intended result for this failure before the change.
4. **Prescribe the fix** — One change that produces that result.
5. **Search the fix library** — `docs/fix-library/` on master.
6. **Reuse or create** — Existing fix wins. If it matches, apply it now.
7. **Apply** — Put the fix in the product file that causes the miss. No stub. No SEE_FILE. No wrapper.
8. **Confirm the change exists** — That file on master contains the fix. SHA named. The commit message must match the file.
9. **Publish to live** — Site, ingest, or both.
10. **Verify publish** — Production is running that change.
11. **Verify the failure is gone** — Open the live page. Read Showing N of M.
12. **Save the fix to the library** — Failure, cause, fix, SHA, live N.
13. **Verify the library entry** — On master and matches what shipped.
14. **If Success** — Stop.
15. **If not Success** — Return to step 1. Do not pile a second theory.

## When the cause is a hold (step 7)

If a product function sets `hold_reason` and that hold violates law:

1. Open the file that assigns `hold_reason`.
2. Delete that assignment.
3. Missing date or place becomes a hole, not a hold.
4. Do not add a second file that clears the hold later.
5. Do not invent a clock to dodge the hold.

Allowed holds only: no title and no listing URL; fixture; Class D wall; one unofficial social post; one desk stating two different clocks for the same row.

## Manner

Definer 1–4. Librarian 5, 12–13. Fixer 6–8. Publisher 9–11.
Definer is not Fixer. Nobody declares Success except step 11.

## Forbidden

- Rewriting these 15 steps to fit one ticket.
- Calling a green job Success.
- Starting step 6 before steps 3–5.
- A second fix while step 11 is still fail.
- Wrapping a hold instead of deleting it.
