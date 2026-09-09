# Find aggregators for any locale

Austin names are **instances**, not the library.

| Role | Austin instance | What to find in any locale |
|---|---|---|
| Local editorial desk | Chronicle | Alt-weekly, newspaper, city magazine calendar |
| Local what’s-on | Do512 | City listings marketplace / “what’s on” site |
| Public media | KUTX | NPR / community radio concert or arts calendar |
| Global ticketing | Ticketmaster | Ticketmaster / AXS / Eventbrite / local primary ticketer |
| Tour graph | Bandsintown | Bandsintown / Songkick — artist tour dates for that city |
| Community marketplace | Meetup | Meetup / local groups |
| Civic | city calendar | City, county, library, parks, campus |
| Official place | venue ICS | The venue or presenter’s own calendar |

A locale is not ready when it has Chronicle. It is ready when each **role** that exists there has a door, or an honest hole (“no local desk found”).

## Process (every new locale, and a refresh of an old one)

1. Name the locale pack (`sources/locale_packs/<id>.json`). Timezone is the pack IANA zone.
2. Search for each role above. A search hit is a **lead**, not a listing.
3. Open the lead. Classify A–F. Do not enter a wall (D → claim only).
4. If it lists happenings, add it as a pack door: role, class, validated yes/no, start URL.
5. Prefer Class A (ICS, RSS, JSON-LD, public API). HTML if that is what they print.
6. Record the same role globally when the brand is global (Ticketmaster, Bandsintown, Meetup). One global door, filtered by locale — do not invent a new Ticketmaster per city.
7. Local roles must be found locally. Do not copy Chronicle into London.
8. Put the door in the Valid Source Library once. Reuse the flag.
9. Ingest that pack. Count the live page for that locale.
10. If a role is empty, keep the hole visible. Hunt again on the next cycle. Do not pretend the locale is complete.

## Queries that work in any language / city

Replace CITY:

- CITY events calendar
- CITY alternative weekly events
- CITY what to do this weekend
- CITY NPR concert calendar
- CITY city hall events
- CITY library events
- Ticketmaster CITY
- Bandsintown CITY
- Meetup CITY

A hit becomes a door only after a human-readable public list exists.

## Do not

- Treat the Austin six as the world set.
- Pay for placement.
- Bypass a wall.
- Pause ingest in Austin to hunt London.
- Use aggregator jargon as 1Live field names.

Law already on master: ONE-LIVE-LOCALE-LAUNCH.md. This file is the hunt inside step 2 of that law.
