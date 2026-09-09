# Find · assess · validate aggregators (any locale)

Same shape as the Failure-Correction Process: numbered actions, do not skip.
Austin names are instances. Roles are the library.

## Roles (the hunt list)

Not a kind list. A role is “who publishes a calendar.” If a role does not exist in that city, record a hole.

| # | Role | What you are looking for |
|---|---|---|
| 1 | Local editorial desk | Newspaper, alt-weekly, city magazine events |
| 2 | Local what’s-on | City listings site |
| 3 | Public media | Radio/TV arts or concert calendar |
| 4 | Civic | City, county, parks, library official calendar |
| 5 | Campus | University / school district public events |
| 6 | Tourism | Visit-city / DMO calendar |
| 7 | Ticketing | Ticketmaster, Eventbrite, AXS, local box office |
| 8 | Tour graph | Bandsintown, Songkick — artists in that city |
| 9 | Community | Meetup and local groups |
| 10 | Official place | Venue or presenter’s own calendar |
| 11 | Official artist/org | Artist, company, congregation, club own dates |
| 12 | Sports | Team, league, rec department |
| 13 | Film | Cinema / festival calendar |
| 14 | Markets | Farmers market / night market series |
| 15 | Festival series | Named festival that publishes a program |

This list is the default hunt. If a city has another public calendar that lists happenings, that is Role 16: Other publisher. Add it. Do not drop it because it was not in the table.

Coverage Law still wins: every activity, any locale. Roles help you hunt. They do not shrink the catalog.

## The process (15 actions — do not skip)

1. **Name the locale** — pack id + IANA timezone. Device or searched city.
2. **Walk every role** — use the table. Mark each: found / hole / does-not-exist-here.
3. **Search** — queries below. A hit is a lead, not a listing.
4. **Open the lead** — human-readable public page. Do not enter a wall.
5. **Classify** — A structured open · B public HTML · C visual later · D wall (claim only) · E owner claim · F human report.
6. **Assess** — Does it list happenings with a title? Public without login? Same host as the publisher? If no title list, it is not a door.
7. **Validate** — Established desk, official place/org, civic, licensed ticketer, or already in the Valid Source Library → validated = yes. One unofficial social post → no.
8. **Register globally or locally** — Ticketmaster stays one global door + locale filter. Chronicle-class stays in that pack only.
9. **Write the pack door** — id, url, role, class A–F, validated yes/no, via.
10. **Write the catalog row** — `sources/master_sources_catalog_120.json` name + base_url + category. No unlabeled door.
11. **Flag once** — validated lives on that row. Do not re-judge Chronicle every ingest.
12. **Ingest** — desk-ingest write=true for that pack. Prefer Class A on the door if it has ICS/JSON-LD.
13. **Count live** — open 1live.co for that locale. Green job is not Success.
14. **Record holes** — empty role stays visible. Hunt again next cycle.
15. **If Success for this locale’s found doors** — stop the hunt. If the live union is still short — Failure-Correction Process. Do not start a second city to avoid the miss.

## How to search (any language)

Replace CITY:

- CITY events calendar
- CITY alternative weekly events / CITY newspaper events
- CITY what to do this weekend
- CITY NPR OR radio concert calendar
- CITY city hall events / CITY parks events / CITY library events
- CITY university events
- Visit CITY events
- Ticketmaster CITY / Eventbrite CITY
- Bandsintown CITY / Songkick CITY
- Meetup CITY
- CITY farmers market / CITY film festival / CITY sports calendar

A hit becomes a door only after step 6 passes.

## How to assess (step 6 checklist)

- Public list of happenings: yes/no
- Title visible: yes/no
- Login/paywall/bot wall: if yes → Class D, stop fetch
- Structured feed (ICS/RSS/JSON-LD/API): Class A preferred
- Only a blog with no dates: not a door
- Directory of venues with no dates: place census, not a happening door

## How to validate (step 7 checklist)

Validated = yes when any one is true:
- Official venue, artist, presenter, or organizer
- Established local desk or public media
- Civic / campus / library calendar
- Licensed ticketing or established tour graph
- Already flagged in `sources/valid_sources.json` or the catalog

Validated = no when the only evidence is:
- One unofficial social post
- SEO scrape
- A wall we did not enter

Two sources are required only when validated = no.

## Do not

- Treat the Austin six as the world set.
- Pay for a door.
- Bypass a wall.
- Pause Austin ingest to hunt another city.
- Invent a URL.
- Use the role name as a 1Live kind.
