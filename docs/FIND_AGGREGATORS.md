# Find, assess, validate aggregators (any locale)

Austin names are instances. Roles are the library.
A locale is ready when every role that exists there has a door, or an honest hole.
This process is non-violable the same way `docs/ONE-LIVE-FIX-LOOP.md` is. Do not skip steps.
Ingest on the test pack does not pause.

## Roles (use these; add Other, do not collapse)

| # | Role | What it lists | Austin instance only |
|---|---|---|---|
| 1 | Local editorial desk | City calendar under a masthead | Chronicle EventSearch |
| 2 | Local what’s-on | City listings marketplace | Do512 |
| 3 | Public media | Radio / TV / weekly arts calendar | KUTX |
| 4 | Civic | City, county, parks, library | city calendar |
| 5 | Campus | University / school district | campus calendar |
| 6 | Global ticketing | Tickets for that city | Ticketmaster, Eventbrite |
| 7 | Local ticketing | Regional primary ticketer | — |
| 8 | Tour graph | Artist dates through that city | Bandsintown, Songkick |
| 9 | Community marketplace | Groups, meetups, classes | Meetup |
| 10 | Official place | Venue / presenter / organizer own calendar | venue ICS |
| 11 | Official artist | Artist own dates | artist site / claim |
| 12 | Sports | League, team, stadium | — |
| 13 | Film | Cinema / festival film listings | — |
| 14 | Museums / galleries | Exhibition and program calendars | — |
| 15 | Markets / recurring civic | Farmers markets, standing civic | — |
| 16 | Tourism board | Visitor bureau calendar | — |
| 17 | Festival organizer | Festival’s own program | — |
| 18 | Open data | City ICS / JSON / CKAN | — |
| 19 | Other | Residual. Do not drop. Do not invent a 20th ontology. | — |

If a role does not exist in that locale after a real search, write `none found` and the query used. That is a hole, not “no events.”

## The 15 steps (do not skip)

1. **Name the locale** — pack id + IANA zone. Device or searched city. Not Austin copied.
2. **List roles** — the table above. Mark each: needed / not applicable.
3. **Search the catalog first** — `sources/master_sources_catalog_120.json`, `sources/valid_sources.json`, existing packs. Reuse a global door (ticketing, tour graph, Meetup-class). Do not mint a second Ticketmaster.
4. **Search the open web for missing roles** — use the query list. A hit is a **lead**, never a listing.
5. **Open the lead** — public page only. If login / paywall / bot wall → Class D. Stop. Claim only.
6. **Classify** — A structured (ICS, RSS, JSON-LD, public API) / B public HTML / C visual later / D wall / E owner claim / F human report.
7. **Assess list** — Does this page print happenings a person can read (title, and usually a when or a place)? If no public list, it is not a door.
8. **Assess coverage** — Does it cover this locale (or a filter for this locale)? Global brands stay one door with a locale filter.
9. **Assess authority** — Established desk, ticketer, civic, official venue/artist, or named marketplace → candidate for validated. Unofficial social, SEO scrape, one person’s blog → unvalidated.
10. **Validate once** — Write `validated: yes` or `no` on the door. Do not re-judge every row. Invalidate later only on evidence the door is wrong.
11. **Record the door** — pack row: role, class A–F, validated, start URL, timezone from the pack. Prefer Class A start URL when they publish one.
12. **Record the library** — if validated, add `sources/valid_sources.json`. One library. Not a second database.
13. **Ingest** — `desk-ingest write=true` for that door or pack.
14. **Count live** — open that locale on 1live.co. Green job is not Success.
15. **Hole or next role** — if the live count did not move, start the Fix Process on that miss. If the role is empty, keep the hole and hunt the next role. Do not call the locale complete.

## How to search (step 4)

Replace CITY. Use the local language.

- CITY events calendar
- CITY alternative weekly events / CITY newspaper events
- CITY what to do this weekend / CITY what’s on
- CITY NPR / radio concert calendar
- CITY city hall events / CITY parks events / CITY library events
- CITY university events
- CITY tourism events
- CITY farmers market
- CITY film times / CITY museum exhibitions
- CITY sports calendar
- Ticketmaster CITY / Eventbrite CITY
- Bandsintown CITY / Songkick CITY
- Meetup CITY

## How to assess (steps 5–9)

Write one line per lead:

- URL
- Role
- Class A–F
- Public list? yes/no
- Wall? yes/no
- Locale filter exists? yes/no
- Authority: desk / ticketer / civic / official / marketplace / unofficial

If wall = yes → D. Do not fetch.
If public list = no → not a door.
If unofficial only → unvalidated. Do not promote on 1.

## How to validate (step 10)

Validated = yes when **one** of these is true:

- Established local desk or public media under its own masthead
- Civic / campus official calendar
- Primary ticketer or named marketplace the pack recorded
- Official venue, artist, presenter, organizer calendar or claim
- Global tour graph the pack recorded

Validated = no when:

- One unofficial social post
- SEO scrape / link farm
- Door we did not enter
- Extractor guess

Two sources are only required when the only evidence is unvalidated.

## Do not

- Copy Chronicle into another city.
- Treat the Austin six as the world set.
- Pay for a door to be validated.
- Bypass a wall.
- Invent a clock to make a lead look complete.
- Pause Austin ingest to hunt another city.
