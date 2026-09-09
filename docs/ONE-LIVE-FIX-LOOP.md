# 1Live Fix Loop (non-violable)

Universal. Any locale. Any ticket. Any failure type. Ceremony off.

This file is the process. It does not name a product bar.
Each ticket writes its own Success definition (step 3).
Ticket B's Success is in docs/TICKET_B.md. Do not copy that bar into these steps.

GitHub green is not done. Master is not live.
Done for a defect is whatever step 3 wrote, measured on the real surface that defect owns
(live site, ingest start, a file on master, a deploy SHA).

## The loop (15 steps — do not skip, do not specialize)

1. **Find failure** — Compare current state to Success as defined for this defect. If it is not Success, it is a failure. Name expected vs actual.
2. **Determine why** — One cause. Timeboxed. Not a list of theories.
3. **Define success** — Write the measurable result that means this failure is gone. The probe depends on the failure type (a live count, a job that starts, a file that is not a stub, a deploy SHA). Write it before any patch.
4. **Prescribe the fix** — One change that produces that result. File or step. No second ticket.
5. **Search the fix library** — `docs/fix-library/` on master. If this failure already has a named fix, use it.
6. **Reuse or create** — Existing fix wins. New fix only if the library has no match. New fix gets a name.
7. **Apply** — Put the fix in the product. No stub. No SEE_FILE. Do not invent facts the door did not print.
8. **Confirm the change exists** — The file on master contains the fix. SHA named.
9. **Publish to live** — Vercel ships master. If the hole is catalog, ingest for that locale pack.
10. **Verify publish** — Production is running that SHA (or the ingest run finished). Not “we pushed.”
11. **Verify the failure is gone** — Run the step-3 probe. Pass only if that Success is true.
12. **Save the fix to the library** — One page in `docs/fix-library/`: failure, cause, fix, SHA, probe result.
13. **Verify the library entry** — That page is on master and matches what shipped.
14. **If success** — Stop.
15. **If not success** — Do not pile a second theory. Return to step 1 with the new actual.

## Who does which steps

- Definer: 1–4
- Librarian: 5, 12–13
- Fixer: 6–8
- Publisher: 9–11
- Anyone may run 14–15. Nobody may declare success except step 11.

Definer is not Fixer.

## World-class add-ons (do not skip these either)

- Write success (step 3) **before** any patch.
- One cause, one fix, one probe. Toyota stop-the-line.
- Search known fixes before writing code. SRE runbook first.
- Separate “deployed” (step 10) from “probe recovered” (step 11).
- Blameless library: record what failed, not who typed.
- Locale is device or search. Timezone is that locale pack. Austin is the test pack, not the product.

## Forbidden

- Putting a ticket-specific bar inside these 15 steps.
- Calling a green job success.
- Stubbing a real module.
- Inventing a start time or a duration.
- Starting step 6 before steps 3–5.
- A second fix while step 11 is still fail.
