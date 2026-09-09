# Fix library taxonomy

Failure-type agnostic. Used at steps 5–6 and 12–13.
Every library entry is tagged with all four fields.

## Fields

1. **Surface** — where it broke
   - `site` — visitor page
   - `catalog` — database rows
   - `ingest` — walk / write job
   - `view` — filter / tab / sort (does not delete catalog)
   - `deploy` — master to live
   - `test` — CI or a test that encoded a bad rule
   - `process` — we skipped a required step
   - `data` — a field value is wrong or invented

2. **Symptom** — what a person or job sees
   - `missing` — should be there, is not
   - `wrong` — is there, is false
   - `blocked` — job or page cannot start
   - `invented` — we printed a fact no door printed
   - `stubbed` — a real module was replaced with a placeholder
   - `silent` — failed without saying so
   - `mismatch` — two names or two clocks for one fact

3. **Cause class** — one why
   - `gate` — a hold or required field hid a valid row
   - `parser` — we did not read what the door printed
   - `filter` — a view treated a row as ended or out of window
   - `import` — missing name or module
   - `timezone` — wrong IANA zone or UTC midnight as a day
   - `stub` — SEE_FILE or six-line stand-in
   - `config` — door, pack, or workflow input
   - `clock` — invented minute or invented duration
   - `identity` — two rows or one mash for one happening

4. **Locale** — `any` unless the fix is truly pack-specific. Default `any`.

## Match rule (step 5)

1. Tag the live failure with Surface + Symptom + Cause class.
2. Open `docs/fix-library/README.md` and scan IDs with those tags.
3. **Reuse** if an entry matches all three (and locale is `any` or this locale).
4. **Evaluate** if two of three match: same file? same probe? If yes, reuse and note the delta. If no, create.
5. **Create** if zero or one field matches. New ID `FL-NNN`. Fill `docs/fix-library/TEMPLATE.md`.

Do not reuse a view-filter fix for an ingest-import failure.
Do not create a new fix when FL-004 already says “restore the real module.”
