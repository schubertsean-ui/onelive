# Find aggregators for any locale

Chronicle, Do512, Ticketmaster, Bandsintown, Meetup, KUTX are **examples in the CAPCOG test pack**. They are not the world library.

1Live needs the same *roles* in every locale, then fills the names that play those roles there.

Does not pause ingest.

## Roles (universal — not brand names)

| Role | What it is | CAPCOG example only |
|---|---|---|
| Local desk | City listings calendar under its own masthead | Austin Chronicle EventSearch |
| Local marketplace | City “what’s on” site | Do512 |
| Local radio / weekly | Station or alt-weekly concert/activity calendar | KUTX |
| Civic / university | City, library, campus calendar | (pack row if present) |
| Ticketing | Sells or lists tickets for that locale | Ticketmaster, Eventbrite |
| Tour graph | Artist tour dates that pass through the locale | Bandsintown, Songkick |
| Community marketplace | Groups and meetups | Meetup |
| Owner calendars | Venue / artist / presenter official pages | found per happening |
| Human claim | Class E / F | not a crawl |

A locale pack is complete for density only when each role either has a validated door or is marked “none found after search.”

## Process (any city, any country)

1. Locale = searched city or device city + IANA zone. New pack file. Do not copy Austin brand names into the new pack.
2. Open existing master catalog (`sources/master_sources_catalog_120.json`) and Valid Source Library. Reuse a global door (ticketing, tour graph, Meetup-class) if it already covers that locale.
3. Search for the missing roles:
   - “{city} events calendar”
   - “{city} things to do”
   - “{city} concert calendar”
   - city / tourism / library calendar
   - local newspaper + “events”
   - local public radio + “calendar”
4. For each candidate: class A–F. Wall = D, claim only. No login bypass.
5. One human validation: established desk / ticketer / official calendar → validated = yes. Unofficial blog or social → no.
6. Write the door into that locale pack + `sources/valid_sources.json` if validated.
7. Ingest that door. Count 1live.co for that locale.
8. Union bar = unique happenings across the doors that exist for that locale, not a copied Austin number.

## What not to do

- Hardcode Chronicle / Do512 as if they exist in London.
- Treat the six named brands as the complete library.
- Build a second database. Pack + valid_sources + master catalog are the library.
- Pause ingest on the test pack to hunt other cities.

## Already on master (do not ignore)

- `sources/locale_packs/us-tx-capcog.json` — test pack doors
- `sources/master_sources_catalog_120.json`
- `docs/TAM_CAPCOG.md` / `docs/FINDER_CAPCOG.md` — CAPCOG instance of this process
- `docs/VALID_SOURCES.md` / `docs/SOURCE_MODEL.md`

This file is the universal process. CAPCOG files are one run of it.
