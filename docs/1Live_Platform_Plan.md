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
- Ticket A first. Ticket A is not the last ticket.
- Do not replace desk_read.py or desk_publish.py with a stub.
- After merge: desk-ingest write=true doors=all → open 1live.co and count.
- If the count did not move, the work failed. Keep going.
- Do not merge PR #273.

## Ticket order (entire Plan)

A — Populate. Trusted door + title is enough. Date/place/year cannot hold. Wire apply_to_writes. Ingest doors=all. N moves. Chronicle ~179 is a step.
B — Density bar. 1Live unique dated+placed > union of named public aggregators, deduped. PR #272.
C — Card the visitor sees. Slots: date, time, title, category + subgenre, venue, street, via, tickets cue, preview hook, spark line, price. Holes allowed. Two rooms after rows exist. PR #274.
D — Place is a query. Locale is typed, not a catalog border. PR #258.
E — Gather. First visitor in a thin place starts one bounded pipe. PR #263.
F — Pack doors register without a catalog JSON row. PR #262.
G — All locales, all kinds. CAPCOG is a test filter. Heartbeat pulse. On-device plans. No pay-to-rank.

Start B only after A ingest is running. Do not shrink Vision to Chronicle.

## Ticket A now

A happening exists when a readable trusted door printed a title or a listing URL.
Missing date, time, place, or year is a hole on the card. It is not a hold.
Yearless house date prefers the upcoming occurrence. Printed 20xx wins. Year never blocks.
Do not invent 17:00. Night is a view filter, not a column.

Vehicle: PR #279. Grok is the builder. Claude is not required.

## Execution this hour

1. Green #279 with the 54KB reader still present.
2. Squash-merge.
3. desk-ingest write=true doors=all.
4. Count 1live.co and /tonight.
5. If N moved, open Ticket B. If not, fix the next hold and ingest again.
