# 1Live Failure-Correction Process (non-violable)

Universal. Any failure. Any ticket. Any locale. Ceremony off.

This process does not belong to Ticket B. Ticket B has a bar. Other tickets have other bars. The process is how any miss is corrected.

## The loop (15 steps — do not skip, do not specialize)

1. **Find failure** — The current result is not Success as defined for this work.
2. **Determine why** — One cause.
3. **Define success** — Write the intended result for *this* failure. It may be a count, a page behavior, a file on master, a deploy, or any other observable. Write it before the patch.
4. **Prescribe the fix** — One change that produces that result.
5. **Search the fix library** — `docs/fix-library/` on master. Reuse if this failure already has a named fix.
6. **Reuse or create** — Existing fix wins. New fix only if there is no match.
7. **Apply** — Put the fix in the product. No stub. No SEE_FILE.
8. **Confirm the change exists** — The file on master contains the fix. SHA named.
9. **Publish to live** — Ship what must be on the live system for this failure (site, ingest, or both).
10. **Verify publish** — Production is running that change. Not “we pushed.”
11. **Verify the failure is gone** — The live system now matches success from step 3.
12. **Save the fix to the library** — Failure, cause, fix, SHA, live result.
13. **Verify the library entry** — That page is on master and matches what shipped.
14. **If Success** — Stop.
15. **If not Success** — Return to step 1. Do not pile a second theory.

## Manner (how we staff it — not extra steps)

- Definer: 1–4
- Librarian: 5, 12–13
- Fixer: 6–8
- Publisher: 9–11
- Definer is not Fixer.
- Nobody may declare Success except step 11.

## Ticket bars are not this process

Example only — Ticket B’s Success definition is: 100% of that locale’s counted aggregator union is on 1Live. That is a bar. It is not step 3 of the process. Step 3 always writes Success for the failure in front of you.

## Forbidden

- Rewriting these 15 steps to fit one ticket.
- Calling a green job Success.
- Starting step 6 before steps 3–5.
- A second fix while step 11 is still fail.
