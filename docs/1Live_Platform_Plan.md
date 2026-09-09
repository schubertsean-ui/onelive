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
- This chat closing is not a stop.
- Ticket A first. The Plan does not end at Ticket A.
- Do not replace desk_read.py or desk_publish.py with a stub.
- Do not merge PR #273.

## Sequence (do in order)

### Ticket A — populate (now)
A happening exists when a trusted door printed a title or listing URL.
Missing date, time, place, or year is a hole. It is not a hold.
Year never blocks. Do not invent 17:00. Night is a view filter.
PR #279. Merge when green and reader still >10KB. Then desk-ingest write=true doors=all. Count 1live.co.
Chronicle today ~179 is a step, not the Vision.

### Ticket B — density
1Live unique dated+placed must exceed the union of named public aggregators, deduped. Not a sum of site counts. PR #272 after A moves N.

### Ticket C — the card the visitor sees
Slots: date, time, title, category + subgenre, venue, street address, via, tickets cue, preview hook, spark line, price.
Incomplete fill is not a disqualifier. Never invent. Missing time still publishes.
PR #274 after A. Night is not a column.

### Ticket D — any locale
Locale is a query. CAPCOG is the test view, not the catalog border.
PR #258 / #263 after A.

### Ticket E — every pack door
Every public door writes. 12 of 26 doors still lack a catalog row. After A.

## Ticket A execution (this hour)

1. Keep the 54KB reader. Wire complete_house_year into _house_when.
2. Date and place cannot hold.
3. After plan(), apply_to_writes.
4. Merge only a green PR that still has the full reader.
5. desk-ingest write=true doors=all.
6. Count 1live.co and /tonight.
7. Then start Ticket B. Do not stop at A.
