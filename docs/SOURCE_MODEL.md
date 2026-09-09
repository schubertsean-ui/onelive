# 1Live source model

How activities enter 1Live. Universal. Runs beside ingest. Does not pause Ticket B.

Vision: every activity anywhere. Validated door → one statement publishes.
Valid Source Library: `sources/valid_sources.json` + pack doors + `sources/master_sources_catalog_120.json`.

## What 1Live has now

| Path | What it is | Status |
|---|---|---|
| Desk ingest | Public HTML/ICS from pack doors | Running. Chronicle often held |
| Source catalog | Name, URL, class | Exists |
| Valid library | validated = promote on 1 | FL-005, just landed |
| Owner claim | Venue/artist/organizer submit | Designed, not the default river |
| Search / gather | Locale is a query | Law exists; Ticket E paused-not-paused continuous |
| Social / Class D | Claim only | Correct — do not crawl walls |

Translator out: title / when / place / kind / via.

## What the best aggregators actually do

**Google Events**
- Prefer the organizer, venue, artist, and primary ticketer pages.
- Read schema.org/Event (JSON-LD) as Class A.
- Crawl the rest of the web and consolidate duplicates (title+when+place).
- Official site wins field disputes. They do not wait for two newspapers.

**Bandsintown**
- Artist can claim and edit.
- Ticketing partners auto-import (Ticketmaster, AXS, Eventbrite, See Tickets…).
- Venue/promoter feeds fill holes.
- Artist can delay publish; partners still import. One happening.

**Eventbrite / Meetup**
- Organizer-owned listing is the source of truth for that door.
- Other sites copy them. 1Live should read the organizer, not the copy.

**Do512 / local desks**
- Editorial desk + venue submit. One trusted desk is enough for a city river.

Shared pattern: **many doors in, one card out. Official/validated first. Owner can correct. Never pay-to-rank.**

## Gaps vs that bar

1. Promote still treated some validated desks like hearsay (FL-005).
2. Date-only held instead of published with a hole.
3. No live owner-claim door on the default river.
4. Class A (ICS/JSON-LD) underused vs HTML walk.
5. Directory pages (Do512 /venues) were confused with happening permalinks.

## Recommended workflow (continuous)

1. **Register** the door once in the Valid Source Library (class + validated yes/no).
2. **Read** Class A first (ICS, RSS, JSON-LD, public API). HTML if no A.
3. **Translate** to title / when / place / kind / via. Year is not a gate. End is optional.
4. **Dedupe** title + when + place = one happening. Add via, do not mint a second row.
5. **Promote** if the door is validated. Two vias only for social/invalidated.
6. **Claim** — owner may add or correct a field. That is mutation evidence for THAT field.
7. **Show** — Today is a filter. Catalog keeps the row.
8. **Watch** — M hourly vs Vision/Goals. Miss → 15-step process. Ingest keeps walking.

## Red team (what breaks this)

| Attack | What happens | Change we keep |
|---|---|---|
| Treat every aggregator as hearsay | Union never publishes | Validated class promotes on 1 |
| Second database of “valid sources” | Drift vs the pack | One library, three files |
| Owner claim overwrites a printed field with no evidence | Mutation violation | Claim wins only same-page or second validated door |
| Schema.org only | Desks without JSON-LD vanish | A then B |
| Google Places / invented address | Trust break | Never invent |
| Pay partners to rank | Vision shrink | Refuse |
| Pause ingest to write this doc | 16 stays 16 | Ingest stays on |

## Incorporate

- FL-005 is the promote rule.
- Pack doors stay the locale list.
- Owner claim is Ticket-shaped work, not a new product.
- Class A readers get priority on the next ingest pass for each door that has ICS/JSON-LD.
- M and Witness keep counting 1live.co. Docs are not Success.
