# 1Live Fix Loop (non-violable)

Universal. Any locale. Any ticket. Ceremony off.

Done is a person opening https://1live.co (or that locale’s live view) and seeing the activity.
GitHub green is not done. Master is not live.

## Success (Ticket B and every later ticket)

Right: 100% of the counted union of that locale’s public aggregators is on 1Live.
Wrong: anything less.
Same title + when + place = one happening.

## The loop (15 steps — do not skip)

1. **Find failure** — Compare live N to the union for that locale. If live < 100% of the union, it is a failure. Name expected vs actual.
2. **Determine why** — One cause. Catalog hole, view hide, deploy miss, or invented clock. Not a list of theories.
3. **Define success** — Write the number that must appear on the live page. Example: Today = Chronicle today union for this locale.
4. **Prescribe the fix** — One change that produces that number. File or step. No second ticket.
5. **Search the fix library** — `docs/fix-library/` on master. If this failure already has a named fix, use it.
6. **Reuse or create** — Existing fix wins. New fix only if the library has no match. New fix gets a name.
7. **Apply** — Put the fix in the product code. No stub. No SEE_FILE. Do not invent a clock or a duration.
8. **Confirm the change exists** — The file on master contains the fix. SHA named.
9. **Publish to live** — Vercel ships master. If the hole is catalog, desk-ingest write=true doors=all for that locale pack.
10. **Verify publish** — Production is running that SHA (or the ingest run finished). Not “we pushed.”
11. **Verify the failure is gone** — Open the live page. Count. Pass only if success from step 3 is true.
12. **Save the fix to the library** — One page in `docs/fix-library/`: failure, cause, fix, SHA, live result.
13. **Verify the library entry** — That page is on master and matches what shipped.
14. **If success** — Stop.
15. **If not success** — Do not pile a second theory. Return to step 1 with the new actual N.

## Who does which steps

- Definer: 1–4
- Librarian: 5, 12–13
- Fixer: 6–8
- Publisher: 9–11
- Anyone may run 14–15. Nobody may declare success except step 11.

Definer is not Fixer.

## World-class add-ons (do not skip these either)

- Write success (step 3) **before** any patch.
- One cause, one fix, one count. Toyota stop-the-line.
- Search known fixes before writing code. SRE runbook first.
- Separate “deployed” (step 10) from “bar recovered” (step 11). Stripe / Google SRE.
- Blameless library: record what hid the row, not who typed.
- Locale is device or search. Timezone is that locale pack. Austin is the test pack, not the product.

## Forbidden

- Calling a green job success.
- Stubbing desk_read.py or desk_publish.py.
- Inventing a start time or a duration.
- Starting step 6 before steps 3–5.
- A second fix while step 11 is still fail.
