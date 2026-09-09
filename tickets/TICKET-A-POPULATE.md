# Ticket A — Populate 1Live from every readable pack door

Founder approved 2026-09-08. PM chat executes. Do not merge #273.

## Vision this ticket serves
Every live activity is easy to find. A happening exists when a trusted door printed a title.

## Must-do
1. `worker/locale_pack/existence.py` — exists(door, title or listing_url).
2. `desk_publish.py` — hold_reason only none / no_title / fixture / class_d.
3. `registration_for` synthesizes a source from the pack door. Never refuse unlabeled.
4. `house_year.py` prefer-upcoming. Never None. Wire `_house_when` on the FULL reader.
5. Migration: `event.start_date`, `observation`, `happening_via`.
6. `promote.py` allows null start_time.
7. Feed Today/Tonight filters on start_date or clock-date. Night is not a column.
8. desk-ingest default doors=all. Fail if held_titled_n > 0.
9. Restore `tests/test_desk_read.py` breadth. CI: reader >10KB.
10. Every readable door in `sources/locale_packs/us-tx-capcog.json` registers.

## Must-not
- merge #273
- wire_desk_read.py / restore-desk-read.yml
- invent 17:00 as start_time
- warehouse / card rooms / night column
- Chronicle-only as done

## Done
PR green. Ingest write=true doors=all. 1live.co Showing N of M moved.
