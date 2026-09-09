# How to use the fix library

For every agent and every coder. Bound to the 15-step process.
Library lives on master: `docs/fix-library/`.

## Access

1. Read `docs/ONE-LIVE-FIX-LOOP.md` (the 15 steps).
2. Read `docs/fix-library/TAXONOMY.md` (the tags).
3. Read `docs/fix-library/README.md` (the index).
4. Open a matching `FL-NNN` page if one exists.

There is no other library. Do not invent a second index.

## Find (step 5)

Tag the failure (Surface, Symptom, Cause class, Locale).
Scan the README table for those tags.
Open candidate pages. Read Failure / Cause / Fix / Step 11 result.

## Evaluate

Ask only:
- Is this the same Surface?
- Is this the same Symptom?
- Is this the same Cause class?
- Did that fix’s step-11 probe pass last time?

Reuse when all three tags match.
Evaluate when two match.
Create when fewer match.

## Select vs create (step 6)

- Reuse: apply the named fix as written. Do not rewrite it mid-flight.
- Create: copy `docs/fix-library/TEMPLATE.md` to `docs/fix-library/FL-NNN-short-name.md`. Assign the next ID. Fill tags + Success probe first.
- Never create a fix that is “stub the file.” That is forbidden.

## After live verify (steps 12–13)

Update the FL page with SHA and step-11 result.
Update the README row.
Confirm both files are on master.
