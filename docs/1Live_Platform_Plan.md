# 1Live Platform Plan v4

PM guiding document. Lives on master. Every agent reads this first.

Done is not a PR. Done is a person opening https://1live.co and seeing the activity.

## Vision

A world where every live activity is easy to find, fairly represented, and culturally valued. At scale: let culture grow without being stripped of its soul. 1Live is the ethical heartbeat of culture.

What it is: a system of record for what’s really on — any category, any locale, person, organization, group, activity, artist, performance, and place-first — a happening.

Map, not shop. No category weighting. Publishers trusted until proven wrong. On-device plans. Heartbeat = de-identified pulse. Beautiful + automagical. Anti-attention. Trust serves the vision. We send people to specialists. No pay-to-rank.

## Goals

1. Answer tonight in under 10 seconds.
2. Every real activity findable. Discovery never for sale.
3. Time given back.
4. Listed by default if it is on.
5. Places appear from activity, not payment.
6. Social validates, never defines.
7. No sponsored discovery.
8. Heartbeat is city pulse, not a person.

## Standing PM rule

- Never idle while 1live.co Showing N of M has not moved toward the public desks.
- Read this file on master before writing code.
- One chat = one ticket = one PR. Ticket A first: populate.
- Do not replace desk_read.py or desk_publish.py with a stub.
- After merge: desk-ingest write=true doors=all → open 1live.co and count.
- If the count did not move, the work failed. Keep going.
- Do not merge PR #273.

## Failure rule (permanent)

Every noticed failure, problem, issue, or deviation from this plan MUST be written with:
1. The failure in one sentence.
2. A world-class fix (the file and the change).
3. Immediate implementation of that fix.
4. Save to master when the reader is still the full module.

If the fix does not produce the Plan outcome, do not explain again. Name the new failure, name the next fix, implement it, save to master. Repeat until 1live.co Showing N of M moves.

A status note without a fix is itself a failure.

## Claude lock (must not diverge)

Claude may only work Ticket A until 1live.co N moves.

Allowed files:
- tools/desk_ingest.py (call apply_to_writes after plan())
- worker/locale_pack/desk_publish.py (edit in place; keep >10KB)
- worker/locale_pack/desk_read.py (edit _house_when only; keep >10KB)
- worker/locale_pack/existence.py
- worker/locale_pack/house_year.py
- worker/locale_pack/ticket_a_apply.py
- tests for those files only
- tickets/TICKET-A-POPULATE.md

Forbidden:
- stub, PLACEHOLDER, see-file, delete desk_read.py
- merge #273
- invent T17:00 or any minute a desk did not print
- hold a titled row for missing date, place, or year
- ingest.yml, warehouse, card rooms, ceremony, STATE, hats, Kaizen
- a second ticket, a second PR, a new locale
- rewriting the law files

## Ticket A

A happening exists when a readable trusted door printed a title or a listing URL.
Missing date, time, place, or year is a hole on the card. It is not a hold.
Yearless house date prefers the upcoming night. Printed 20xx wins. Year never blocks.
Do not invent 17:00. Night is a view filter, not a column.

## Execution

1. Keep the 54KB reader on master. Wire complete_house_year into _house_when.
2. desk_publish: date and place cannot hold. Pack door may register without a catalog JSON row.
3. desk_ingest: after plan(), call apply_to_writes.
4. Merge only a green PR that still has the full reader.
5. Run desk-ingest write=true doors=all.
6. Open 1live.co and 1live.co/tonight. Record Showing N of M.
7. Repeat until N moves. Chronicle today ~179 is a step, not the vision.
