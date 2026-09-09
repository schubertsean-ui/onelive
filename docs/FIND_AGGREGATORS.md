# Find, assess, validate aggregators (any locale)

Austin names are instances. Roles are the library.
A locale is ready when every role that exists there has a door, or an honest hole.
This process is non-violable the same way `docs/ONE-LIVE-FIX-LOOP.md` is. Do not skip steps.
Ingest on the test pack does not pause.

## How this process starts

Any one of these kicks it off. No extra ceremony.

1. A person searches a city 1Live does not have a pack for.
2. M or Goal 2 misses (live N below that locale’s union, or a role is empty).
3. Ticket G (all locales) or Ticket F (pack door with no catalog row).
4. Founder names a locale or a missing role.
5. A new global brand appears that covers many cities (one door, locale filter).
6. Refresh: a pack older than the hunt cycle, or a door 403/404 (we failed, not “no events”).

## Government (do not collapse)

Civic is several doors when they print different lists:

- City calendar
- County / regional council calendar
- Parks and recreation
- Library
- Special district (utility, transit, downtown)
- State / national park unit in that locale

One “civic” row is only enough if one page really lists all of those. CAPCOG as a council is a test *filter*, not automatically a calendar door.

## Locale library — what we do and do not build

Do **not** pre-build every U.S. city, town, and county as a 1Live project.

A locale exists when someone searches it or the device is there. Then we add a pack file.
Identity later may reuse public geo ids (ISO country, Who’s On First / GeoNames). That is a lookup, not a second product.

Pack shape: `sources/locale_packs/<id>.json` with IANA zone + doors.
Parent chain may be city → county → region → state → country. Views filter. Catalog does not delete.

## Roles

| # | Role | What it lists | Austin instance only |
|---|---|---|---|
| 1 | Local editorial desk | City calendar under a masthead | Chronicle EventSearch |
| 2 | Local what’s-on | City listings marketplace | Do512 |
| 3 | Public media | Radio / TV / weekly arts calendar | KUTX |
| 4 | Civic — city | City hall calendar | Round Rock / San Marcos / … |
| 5 | Civic — county / region | County or COG calendar | Hole |
| 6 | Civic — parks | Parks and rec | Hole |
| 7 | Civic — library | Library events | Austin Public Library |
| 8 | Campus | University / school district | UT Austin |
| 9 | Global ticketing | Tickets for that city | Eventbrite; Ticketmaster is D |
| 10 | Local ticketing | Regional primary ticketer | AXS is D |
| 11 | Tour graph | Artist dates through that city | Bandsintown |
| 12 | Community marketplace | Groups, meetups, classes | Meetup |
| 13 | Official place | Venue / presenter own calendar | per happening |
| 14 | Official artist | Artist own dates | per happening |
| 15 | Sports | League, team, stadium | Hole |
| 16 | Film | Cinema / festival film | Hole |
| 17 | Museums / galleries | Exhibition calendars | Hole |
| 18 | Markets / recurring civic | Farmers markets | Hole |
| 19 | Tourism board | Visitor bureau | Visit Austin |
| 20 | Festival organizer | Festival own program | Hole |
| 21 | Open data | City ICS / JSON | Hole |
| 22 | Other | Residual | Class D social |

## The 15 steps (do not skip)

1. Name the locale — pack id + IANA zone.
2. List roles — needed / not applicable / hole.
3. Search the catalog first — reuse global doors.
4. Search the open web for missing roles — hit = lead.
5. Open the lead — public only. Wall = D.
6. Classify A–F.
7. Assess list — public happenings a person can read?
8. Assess coverage — this locale or a filter for it?
9. Assess authority — desk / ticketer / civic / official / marketplace / unofficial.
10. Validate once — yes or no. Do not re-judge every row.
11. Record the door on the pack.
12. Record validated doors in `sources/valid_sources.json`.
13. Ingest that door or pack.
14. Count that locale on 1live.co.
15. Hole or next role. If live did not move, Fix Process on that miss.

CAPCOG run: `docs/CAPCOG_ROLE_SCORECARD.md`.
