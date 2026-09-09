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

- Ticket B is paused until the founder says resume.
- Do not replace desk_read.py or desk_publish.py with a stub.
- Do not merge PR #273.
- Do not invent a start time. Do not invent a duration.
- Aggregator jargon is not 1Live taxonomy. Diverse doors in. One card out.

## Translator (many → one)

1Live is the one. Every door maps into:

- title
- when (start date + optional start time)
- place
- kind
- via

## When (binding on all current and future work)

Two facts. One happening.

1. **Start date** — the calendar day the door printed. Enough to list.
2. **Start time** — only if the door printed a clock.
3. **End date / end time** — optional. Missing end is not ended and not a hold.
4. **Timezone** — IANA zone on the locale pack (and later the place). Not a hardcoded city. CAPCOG test pack is America/Chicago. London is Europe/London. A new locale is a new pack file.
5. **Today** is a view filter: that locale’s calendar day. It does not decide what is in the database.
6. **Year** is current unless that page or site prints a year. Year is not a gate.
7. Night is a view filter, not a field.
8. Existence = trusted readable door + title or listing URL. Date, time, place, year, end cannot hold.

Code: `apply_to_writes` after every `plan()`. `web/lib/when.ts` owns date-only vs datetime. Date-only is that locale day, not UTC midnight.

## Ticket order

A — Populate. Trusted door + title is enough.
B — Density. PAUSED.
C — Card slots. Holes allowed.
D — Place is a query.
E — Gather.
F — Pack doors without a catalog JSON row.
G — All locales, all kinds.
