# KAIZEN LEDGER — append-only measures (docs/KAIZEN.md)

> **KERNEL DOC — project-agnostic, inherited verbatim.** The conventions, the
> table shapes, and the M-measure definitions are kernel. The ROWS are project
> data and start empty. Text in `[square brackets]` is a placeholder.

Greppable summary: one row per merged PR (M1 rounds-to-green, M2 catches by
gate/class, M5 est. cost), plus event rows for M3 escapes (immediately),
M4 gate-gap fixes, M6 po harvests. Rows are never edited after append —
corrections get a new row referencing the old. Trends quoted in the weekly
founder digest in plain language.

## Measures recorded here (definitions in docs/KAIZEN.md)

| ID | Measure | World-class direction |
|---|---|---|
| M1 | Evaluator rounds-to-green per PR | falling trend |
| M2 | Defects caught, by gate and by class | repeat-classes → 0 |
| M3 | Escaped defects (found after merge/deploy) | 0, always |
| M4 | Gate-gap fixes shipped (a catch that produced a new/tightened gate) | steady > 0 |
| M5 | Cost per merged PR (evaluator calls + CI minutes, est.) | falling at flat quality |
| M6 | Po-sourced ideas surviving gates | > 0 over time |
| M7 | The quality ratchet (docs/KAIZEN.md — its own section, not a column here) | one-way tighten |
| M8 | Yellow-hat validated upside | asserted→validated conversion rising |

## Append-only conventions (mechanically relied on by `tools/kaizen_trends.py`)

1. **Class tokens are single kebab-case tokens** immediately before "×N" in the
   M2 column (`empty-env ×1`, never "empty env issues ×1"); REUSE the exact
   token for a repeat. A bare single word counts as a class ONLY if it is in
   `tools/kaizen_trends.py`'s declared short-token registry; any other bare word before ×N
   is prose and must use a plain x ("records x4"). Matching is exact-token plus
   containment families (`empty-env` ⊂ `fail-open-empty-env`).
2. **A class fix is marked** by naming the class token in the fixing row's M4
   column — no marker, no credit, the repeat alarm keeps firing. Markers are
   EPOCH-scoped, never permanent waivers: a marker covers catches at-or-before
   its own row only; ANY catch of the family in a later row alarms immediately
   as a post-fix recurrence and demands a root cause plus a NEW marker row.
3. **M3 escape rows carry the escape token** — `tools/kaizen_trends.py`
   counts that token's occurrences ANYWHERE in this file, so its exact
   spelling is documented in `docs/KAIZEN.md` and deliberately NOT written
   here: a ledger that quotes the token would count itself as an escape.
4. **Rows are never edited after append.** Corrections land as a NEW row that
   references the row it corrects; backfilled markers for already-shipped fixes
   land the same way.

## PR rows

| Date | PR | M1 rounds | M2 catches (gate: class × n) | M4 gate-gaps closed | M5 est. cost | Notes |
|---|---|---|---|---|---|---|
| 2026-07-24 | genesis — kernel v1 extraction (not a merged PR of this project) | 0 | 0 — nothing has been reviewed yet; this row exists so the meter has a parseable baseline and can never read an EMPTY ledger as a CLEAN one | 0 | 0 | Seed row, dated to kernel v1's ratification. It exists because an EMPTY ledger is unparseable and the meter must never read empty as clean. Do not edit it; append per merged PR from here. Two deviations are OPEN in docs/RECORD.md (no project trust gate, evaluator unwired) — the honest starting state of any fresh instantiation. |

## Class watch (M2 repeat classes — these must trend to zero)

One bullet per class family that has been caught more than once. Each bullet
names: where it was seen (dates/PRs), how the gate response has escalated so
far, and what the STRUCTURAL fix is if it appears again. A class family at
three catches with no structural-fix marker is an alarm, not a note.

- *(none yet — the empty kernel template)*

## M3 escapes (absolute-zero goal)

| Date | What escaped | Where found | Root cause | Gate-gap closed |
|---|---|---|---|---|

*(No rows: zero escapes. Leave this table EMPTY rather than writing a
"none yet" placeholder — the meter counts rows, so a placeholder reads as a
real escape. An escape row is only ever appended when one actually happens.)*

## M6 po harvests

| Date | Decision/plan | Provocations run | Ideas surviving gates |
|---|---|---|---|
| — | none recorded to date | | |

## M8 Yellow-hat validated upside (docs/hats/yellow.md)

| Date | Decision | Upside argued | Validated (what shipped and performed) |
|---|---|---|---|
| — | none recorded to date | | |
