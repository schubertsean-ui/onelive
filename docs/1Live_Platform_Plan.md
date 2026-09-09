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
- Ticket A first. Ticket A is not the last ticket. Ticket B is paused until the founder says resume.
- Do not replace desk_read.py or desk_publish.py with a stub.
- After merge: desk-ingest write=true doors=all → open 1live.co and count.
- Do not merge PR #273.

## Clock rule (universal — every aggregator, every input)

This applies to Chronicle, Do512, KUTX, Eventbrite, Meetup, ICS, JSON-LD, RSS, civic calendars, claims, and any later door.

1. A happening exists when a trusted readable door printed a title or a listing URL.
2. Start date or start time is enough to date the row.
3. End time and duration are optional. Never hold, drop, or mark ended for a missing end.
4. Yearless month+day uses complete_house_year (upcoming). Printed 20xx wins. Year never blocks.
5. Do not invent 17:00 or any minute the door did not print.
6. Do not invent a 3-hour duration.
7. A dated row with no end stays on the view through the end of its America/Chicago calendar day.
8. Night is a view filter, not a column.

Code path: `apply_to_writes` after every `plan()`. Existence ignores when/place/end.

## Ticket order (entire Plan)

A — Populate. Trusted door + title is enough. Date/place/year/end cannot hold.
B — Density bar. PAUSED.
C — Card the visitor sees. Holes allowed. PR #274.
D — Place is a query. PR #258.
E — Gather. PR #263.
F — Pack doors register without a catalog JSON row. PR #262.
G — All locales, all kinds.
