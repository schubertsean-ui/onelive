# CAPCOG TAM — entities, aggregators, doors, and how to open closed ones

Docs-only. Total addressable **entities** (not dollars) across every category the
founder named — venue, presenter, group, civic, education, market, other — plus a
map of the platforms that name them (aggregators) and a repeatable method for
turning a closed door into an open one without ever scraping a login this tick.

Music is the proving ground; nothing here is music-shaped. The schema (11 columns,
type enum, ingest_rec enum, clear-the-door ladder) is written so a lecture series, a
farmers market, a Meetup group, a gallery exhibition, or a club night fits the same
row and the same ladder as a concert — no later migration.

**Companion doc:** `docs/domain_recipes.md` is the per-cultural-domain cookbook
(seed desks/registries, a write-only query pack, and the honest CAPCOG hole for
each of the 22 domains plus an always-open `other/raw` row). That grid is a
**starter seed, not a cap** — an unmapped happening still lists, tagged
`other/raw`, never refused; a repeated unmatched shape is the trigger to add a new
recipe row, not a reason to force-fit or drop it. Category is assigned **per
happening**, never pinned to a whole venue/presenter/group — a place that programs
more than one domain gets tagged per event.

**Honest method note, stated once so every row below can be read against it:**
`WebFetch` was tried against 4 different domains this session (a gallery, an author's
own site, a city calendar, a market operator) and returned `EGRESS_BLOCKED` on all
four — the same sandboxed-outbound-fetch constraint prior sessions hit (`sources/README.md`'s
ranks 77–114 expansion, "WebFetch is blocked in this environment"). `WebSearch` is not
blocked. So: every row already in `sources/master_sources_catalog_120.json` was
vetted by a real fetch in whatever session added it (unchanged here); every NEW row
below was found by `WebSearch` only and is labeled `found_unverified` — a real,
plausible door, not a confirmed one. Per Coverage Law ("the extractor guessing is
never a door"), nothing here is upgraded to `official`/`fetch`-ready on a search
snippet alone. Confirming these is the next session's first cheap win once the
network opens.

## Legend

**type** — what kind of thing this is to a visitor, independent of who runs it:

| type | meaning |
| --- | --- |
| venue | a fixed physical place with its own calendar |
| presenter | an individual or rotating cast who performs/speaks/exhibits *without* being a fixed venue (chef, visual artist, professor, author, speaker, personality, band) |
| group | an organization, ensemble, team, or produced annual program not tied to one site (orchestra, sports team, festival, standing speaker series) |
| civic | a government body's own calendar (city, county, library system) |
| education | a school/university's own calendar |
| market | a recurring market (farmers, maker, night) |
| other | doesn't fit the other six honestly (a claim-intake mechanism, a hackerspace collective, a multi-site market operator) |

**how_found** — `catalog` (already committed, censused in `docs/CENSUS_CAPCOG.md`) or
`web_search` (new this session, unverified by fetch).

**bucket** — Coverage Law's A–F (`worker/sourcing/source_class.py::classify_entry()`
for catalog rows; a plausible bucket B for new public-HTML leads, left blank where no
page was even proposed).

**ingest_rec** — what a human/agent does with this row next:

| ingest_rec | meaning |
| --- | --- |
| official | first-party page, ready to fetch when its bucket is A/B |
| aggregator | resolve this entity through an aggregator we already hold rather than a hand-picked URL |
| harbor | resolves through OUR OWN existing intake — the shared listings inbox / `/ops/claim` flow (see "What Harbor means" below); **not a new service** |
| claim | needs a person to run the existing `/ops/claim` flow |
| blocked_now | a shelf, not a deletion — see the clear-the-door ladder |

**clear_state** — `in_catalog` (already resolved) / `found_unverified` (new lead,
not fetch-confirmed) / `blocked_now` (a real hole, see retry_paths).

**Precedence, stated once so an automated consumer never gets this backwards:**
`ingest_rec` is a RECOMMENDATION (what this row's door looks like); `clear_state`
is the GATE (whether that door has actually been confirmed). A row can carry
`ingest_rec: official` while `clear_state: found_unverified` — that pairing means
"this looks like a first-party page," not "this is ready to fetch." Any future
importer reading this CSV must key its ready/not-ready decision on `clear_state`,
never on `ingest_rec` alone (evaluator finding, PR #220 openai/attacker-smuggle
seat — real and worth stating explicitly rather than left implicit).

## What "Harbor" means here

The ticket names "Harbor/claim" as a stage below finder queries and publisher cover.
There is no new service called Harbor in this repo (checked — the word appears
nowhere else except two unrelated fixture/prompt strings). Harbor is this session's
name for a door that **already exists**: the shared listings inbox + `/ops/claim`
flow documented in `docs/CENSUS_CAPCOG.md`'s "Newsletter path" section
(`worker/claim/intake.py`, `api/claims.py`, one shared inbox foldered by source, no
per-venue account). "Manual subscribe to OUR listings inbox is a valid path" (Must-do
4) is exactly that mechanism. Using it needs no new tool, credential, or Must-not
violation — it is the harbor a hole ties up in when public search and publisher
cover both come back empty.

---

## Table 1 — TAM entities

**Base:** 142 of the catalog's 180 rows are graded `official` (a real first-party
entity, not a platform) in `docs/CENSUS_CAPCOG.md` — mapped mechanically into this
table's `type` column below and carried in full inside `docs/TAM_CAPCOG.csv`. They are
**not reproduced row-by-row here**: `docs/CENSUS_CAPCOG.md` is already the live,
correct document for their bucket/grade, and copying 142 rows by hand into a new
schema is exactly the kind of drift risk the census itself was built to avoid. The
other 38 catalog rows (21 aggregator_lead + 4 social + 12 trusted_publisher + 1
unknown) are platforms, not entities — they live in Table 2 instead.

Catalog-derived type distribution (142 rows, mapped by category/entity_type — full
rule table in "Method: mapping the catalog into TAM type" below):

| type | count | notable |
| --- | --- | --- |
| venue | 110 | every club/hall/museum/brewery/winery row |
| group | 22 | SXSW + 9 more festivals, 6 performing-arts ensembles, 3 sports teams, HAAM, Austin History Center Association |
| education | 3 | UT Austin, Texas State, Austin Community College |
| civic | 3 | Visit Austin Events, Austin Public Library, City of Austin Events |
| other | 3 | the 2 claim-intake mechanisms + Google Calendar OAuth |
| market | 1 | SFC Farmers' Market |
| **presenter** | **0** | **the gap this session exists to start closing — zero presenter-type rows anywhere in the 180-row catalog** |

### New rows this session (25)

Every row below is `how_found: web_search`, unverified by fetch unless noted. Full
detail (other_doors, retry_paths, review_after, why) is in `docs/TAM_CAPCOG.csv` —
cells here are shortened for readability.

**Presenter (6)** — see "Presenters" section below for the subtype-by-subtype story.

| name | subtype | official_or_list_url | bucket | ingest_rec | clear_state |
| --- | --- | --- | --- | --- | --- |
| The Loren at Lady Bird Lake — Guest Chef Series | chef | thelorenhotels.com/austin/cuisine/guest-chef-series | B | official | found_unverified |
| Environmental Science Institute — Hot Science, Cool Talks | professor | esi.utexas.edu/community-engagement/hot-science-cool-talks | B | official | found_unverified |
| [HOLE] Independent touring band, own site | band | — | — | aggregator | blocked_now |
| [HOLE] Independent author, own appearances page | author | — | — | aggregator | blocked_now |
| [HOLE] Independent visual artist / gallery calendar | visual artist | — | — | aggregator | blocked_now |
| [HOLE] Independent comedian/personality show | personality | — | — | aggregator | blocked_now |

**Group (2)**

| name | official_or_list_url | bucket | ingest_rec | clear_state | why |
| --- | --- | --- | --- | --- | --- |
| Austin Forum on Technology & Society | austinforum.org | B | official | found_unverified | monthly public speaker series, own site |
| Meetup — New To Austin Community | meetup.com/enjoyable-events-around-town | B | aggregator | found_unverified | names a real group via the already-catalogued Meetup lead |

**Civic (10)** — fills 5 CAPCOG counties (Hays, Williamson, Bastrop, Burnet, Caldwell)
that had zero civic rows before this session; 4 more holes named rather than guessed.

| name | county | official_or_list_url | ingest_rec | clear_state |
| --- | --- | --- | --- | --- |
| City of Round Rock | Williamson | roundrocktexas.gov/events/ | official | found_unverified |
| City of San Marcos | Hays | sanmarcostx.gov/Calendar | official | found_unverified |
| City of Kyle | Hays | cityofkyle.gov/.../community-events | official | found_unverified |
| City of Bastrop | Bastrop | connect.cityofbastrop.org/bastroptx | official | found_unverified |
| City of Marble Falls | Burnet | marblefallstx.gov/733/Events | official | found_unverified |
| City of Lockhart | Caldwell | cityoflockhart.gov/Calendar.aspx | official | found_unverified |
| [HOLE] City of Georgetown | Williamson | — | blocked_now | blocked_now |
| [HOLE] City of Buda | Hays | — | blocked_now | blocked_now |
| [HOLE] City of Pflugerville (general calendar) | Williamson | — | blocked_now | blocked_now |
| [HOLE] City of Llano | Llano | — | blocked_now | blocked_now |

**Education (2)**

| name | official_or_list_url | ingest_rec | clear_state |
| --- | --- | --- | --- |
| Southwestern University (Georgetown) | southwestern.edu/calendar | official | found_unverified |
| [HOLE] St. Edward's / Concordia Texas / Huston-Tillotson | — | blocked_now | blocked_now |

**Market (3)** + **Other (2)**

| name | type | official_or_list_url | ingest_rec | clear_state | why |
| --- | --- | --- | --- | --- | --- |
| Pflugerville Pfarmers Market | market | pflugervilletx.gov/717/Pfarmers-Market | official | found_unverified | city-run, cleanest new market door |
| Wolf Ranch Farmers Market (Georgetown) | market | — | aggregator | found_unverified | resolves through its operator, below |
| Lakeline Plaza Farmers Market (Cedar Park) | market | — | aggregator | found_unverified | resolves through its operator, below |
| Always Fun Markets | other | alwaysfunmarkets.com | official | found_unverified | multi-site market *operator*, not one market |
| ATX Hackerspace | other | wiki.atxhs.org | official | found_unverified | weekly public open house; already surfaced via catalogued Do512 |

**Full CSV union:** `docs/TAM_CAPCOG.csv` = 142 catalog rows + 25 new rows = **167
rows**, all 11 columns, round-trip-parses clean through Python's `csv` module (same
check `docs/CENSUS_CAPCOG.csv` used).

---

## Table 2 — Aggregators

Grade vocabulary for this table only (narrower than the census's 5-value grade,
matching the founder's ticket exactly):

| grade | meaning |
| --- | --- |
| trusted_publisher | a newsroom/broadcast desk, OR a tourism-board/chamber-of-commerce calendar — ONE-LIVE-TRUST.md explicitly lists "tourism board" as a trusted civic door, so these are graded up from a plain directory, not down to one |
| marketplace | a platform where many independent organizers/artists/venues publish or register their own data (ticketing, RSVP, campus-calendar SaaS, an open identity spine) |
| social | a social-platform API (Instagram/Facebook/TikTok/YouTube) |
| scraper | a directory/search product that compiles other people's listings without being any of the above — lead only, never the listing |

**use_as** — `listings + TAM expansion` (its own coverage counts, and it names new
entities) or `lead only` (Coverage Law: never the listing itself, only a pointer to
one).

### Already catalogued (33 — see `docs/CENSUS_CAPCOG.md` for full detail, not repeated here)

| surface | examples | grade | use_as |
| --- | --- | --- | --- |
| desks | Austin Chronicle, KUTX, KUT, KOOP, KLBJ, 101X, ACL Radio, KVUE, KXAN, CBS Austin, FOX 7, CultureMap (12) | trusted_publisher | listings + TAM expansion |
| marketplace | Ticketmaster, Eventbrite, AXS, DICE, See Tickets, Tixr, TicketWeb, Universe, SeatGeek, StubHub, Do512, Bandsintown, Songkick, Spotify, SoundCloud, Linktree, Resident Advisor, Meetup, MusicBrainz (19) | marketplace | listings + TAM expansion (most bucket D → lead only in practice; see CENSUS next_action) |
| social | Instagram, Facebook, TikTok, YouTube (4) | social | lead only |
| scraper | Bing, DuckDuckGo (2, benchmark-only) | scraper | lead only |

### New this session (7)

| name | public door | grade | use_as | why |
| --- | --- | --- | --- | --- |
| Community Impact (San Marcos–Buda–Kyle edition, and other CAPCOG editions) | communityimpact.com | trusted_publisher | listings + TAM expansion | hyperlocal newspaper chain covering exactly the Hays-county gap the existing 12 desks don't reach; each metro has its own edition |
| Localist | localist.com | marketplace | TAM expansion | the campus-calendar platform UT Austin and (confirmed this session) Southwestern both run on — checking which other CAPCOG campuses use it beats guessing each one's URL individually |
| CivicEngage / RecDesk (municipal calendar SaaS pattern) | e.g. cityoflockhart.gov/Calendar.aspx (CivicEngage), cityofbastroptx.recdesk.com (RecDesk) | marketplace | TAM expansion | same logic as Localist, for cities instead of campuses — one vendor relationship, many sibling towns |
| 101 Highland Lakes / Hill Country Passport | 101highlandlakes.com/events, hillcountrypassport.com/events | trusted_publisher | listings + TAM expansion | regional visitor-bureau calendar naming Marble Falls, Burnet, Llano, Kingsland, Johnson City, Spicewood, Buchanan Dam, Tow in one place |
| Bastrop Regional Chamber of Commerce / Visit Bastrop | bastropchamber.com, visitbastrop.com/events | trusted_publisher | listings + TAM expansion | chamber/tourism-board calendar for a county with one civic row |
| NFMD (National Farmers Market Directory) | nfmd.org | scraper | lead only | named 3 real markets; never cite it as the listing itself |
| LocalHarvest.org | localharvest.org | scraper | lead only | same pattern as NFMD |

**Deliberately not added (verify before grading, don't guess):** Nextdoor and Patch
were not searched this session — their current event-listing features weren't
confirmed, so grading them here would be exactly the guess Must-do #5 forbids. Listed
under proposed queries below instead.

**Eventbrite nuance, worth stating once:** the Eventbrite *API* is class D
(credentialed, already blocked-D in the census). Eventbrite's *public organizer
pages* (like `austinforum`'s own Eventbrite page, used as an `other_door` above) are
plain class B and lead-only — useful for finding an organizer's name, never usable as
the listing. Two different surfaces on the same brand; graded differently on purpose.

---

## Presenters (Must-do 3)

Subtype-by-subtype, what actually resolves and what doesn't:

- **Chef** — The Loren at Lady Bird Lake's Guest Chef Series (own page, rotating
  cast, monthly cadence per search result). Real finding: independent pop-up chefs
  without a hosting venue are hard to verify without a fetch (bookings usually run
  through Tock/Resy, not a page we can read); the hosted-series pattern is the
  reliable door for this subtype.
- **Professor** — Hot Science, Cool Talks (UT's Environmental Science Institute):
  free, public, long-running, own page, and separately reachable via UT's
  already-catalogued Localist feed. The strongest presenter example found this
  session.
- **Speaker** — Austin Forum on Technology & Society: monthly, free, public, own
  site. Classified as `group` (a standing nonprofit) rather than `presenter` in the
  table since it's an organization presenting a rotating cast, but it is the door
  that fills this subtype.
- **Author** — [HOLE]. BookPeople, the Austin Public Library's "Meet the Author,"
  and the Texas Book Festival are ALL already catalogued and absorb the bulk of
  literary presenting in CAPCOG. One candidate independent author site
  (`oscarcasares.com`) surfaced in search but its events page could not be
  fetch-confirmed this session (`WebFetch` egress-blocked) — left as a hole with a
  proposed query rather than asserted.
- **Visual artist** — [HOLE]. Same shape as author: Blanton, The Contemporary
  Austin, and Mexic-Arte (already catalogued) plus the City of Austin's "People's
  Gallery" at City Hall (civic, already catalogued) cover most public exhibition
  access. One gallery lead (`wallyworkmangallery.com`) found, not fetch-confirmed.
- **Personality** — [HOLE]. Cap City Comedy Club, The Hideout Theatre, and The
  Velveeta Room (all three already catalogued) absorb almost all of this subtype in
  CAPCOG; no independent personality page was found.
- **Band** — [HOLE], and the most instructive one. Searched three real CAPCOG-based
  touring acts (Black Pumas, Gary Clark Jr., Shakey Graves). Results were dominated
  by domains like `shakeygravestour2026.us` and `shakeygravestour2027.us` —
  SEO ticket-reseller sites that are **indistinguishable from a genuine artist site
  in a search result** without loading the page, and `WebFetch` is blocked this
  session. Per ONE-LIVE-TRUST.md ("the extractor guessing is never a door"), none of
  these is listed as `official`. Recommendation: resolve touring artists through the
  aggregators already in the catalog (Bandsintown, Songkick, MusicBrainz) rather
  than hand-picking "official" URLs from search — that is exactly what those three
  rows are already there for.

**Confirms the ticket's own warning:** "Social-alone does not publish by itself" —
every presenter subtype that resolved cleanly this session (chef series, lecture
series, speaker series) had a real page beyond a bare Instagram/Facebook profile;
every subtype that stayed a hole (band, author, artist, personality) either had no
independent page at all or nothing this session could verify was one.

---

## Clear-the-door order (Must-do 4)

**Five intakes, one ladder.** The rungs below are the ORDER you try things in; the
founder's five-intake framing (registries, desks/marketplaces, finder queries —
write only — Harbor/claim, and a future "own-on-1Live" self-serve path not yet
built) names the CHANNELS. Full rung-to-intake mapping lives in
`docs/domain_recipes.md` so the two documents share one table instead of two that
can drift.

The ladder, as specified, with what each rung means in practice:

1. **Public list** — does the entity already publish a list anywhere (own site,
   even a plain "upcoming shows" page)? If yes, done — it's a TAM row today.
2. **Finder queries** — a targeted search (not a paid API) for the entity's own
   site. This is where this session's presenter/civic/market holes below all
   currently sit.
3. **Publisher cover** — does an already-trusted desk/publisher/aggregator already
   name it (Austin Chronicle, Community Impact, KUTX, a campus Localist feed, a
   regional visitor bureau)? If yes, that's the door for now, even if it's not the
   entity's own page — it still means the entity EXISTS per ONE-LIVE-TRUST.md
   ("one trusted door is enough to exist").
4. **Harbor/claim** — can the entity self-serve into the existing shared listings
   inbox or `/ops/claim` flow? (See "What Harbor means" above — this is our own
   existing intake, not a new service.)
5. **One outreach** — a single, short, human-sent message per the existing
   `docs/ops/VENUE_CLAIM_OUTREACH.md` copy rules (never "we have your calendar,"
   never implying a relationship that doesn't exist). Not sent by this session —
   Must-do 4's "one outreach" is a per-hole action for whoever owns outreach next,
   not a mass mailing to invent here.
6. **blocked_now, with a review date** — a shelf, not a deletion. The entity's row
   stays in the TAM table forever; only its `ingest_rec` and `review_after` change.

**Stop rule, honored throughout this session:** no login was scraped at any rung —
every hole below stopped at rung 2 (finder queries) or rung 3 (publisher cover)
because that's as far as a `WebSearch`-only, `WebFetch`-blocked session can honestly
go. Nothing was dropped; every hole is a named row above with a `blocked_now`
`ingest_rec` and a `review_after` of "next sourcing session with live network
access."

**Worked example (band presenter):** rung 1 — no independent list found. Rung 2 —
finder queries ran, returned SEO farms, not real doors. Rung 3 — publisher cover
exists (Bandsintown/Songkick/MusicBrainz, already catalogued) — **this is where the
ladder actually resolves for most touring bands**: the aggregator-lead classes ARE
the publisher-cover rung, already built, already catalogued. Rung 4 (Harbor) applies
if a specific band ever wants to self-claim; rung 5 (outreach) and rung 6
(blocked_now) don't apply because rung 3 already closed the hole for the *category*.
The [HOLE] row in Table 1 records that one specific band's *own* site is still open,
not that the band is unreachable.

**Worked example (City of Georgetown civic):** rung 1 — no city calendar found
directly. Rung 2 — finder queries returned only `visit.georgetown.org` (a tourism
site, not the city's own calendar) — a publisher-cover candidate, but this session
did not fetch-confirm it covers city-run events specifically, so it's not yet
promoted to a row. Rung 6 — `blocked_now`, `review_after: next sourcing session`,
`retry_paths: site:georgetown.org events calendar`.

---

## Holes & proposed search queries (Must-do 5)

Every hole this session found, with the next concrete query — none of these were
run this session (cap: existing catalog + resolver-able aggregator names only):

**Civic**
- Georgetown (Williamson): `site:georgetown.org events calendar`
- Buda (Hays): `site:cityofbudatx.gov events calendar`
- Pflugerville general calendar (Williamson): `site:pflugervilletx.gov events calendar`
- Llano (Llano): `site:llanotx.us OR "City of Llano Texas" events calendar`
- Fredericksburg (Gillespie — heavily covered for wineries, not for its own civic calendar): `site:fbgtx.org events calendar`
- New Braunfels (Comal) / Boerne (Kendall) — Hill Country expansion counties with
  near-zero coverage of any kind: `"City of New Braunfels" events calendar`,
  `"City of Boerne Texas" events calendar`

**Education**
- St. Edward's University: `"St. Edward's University" events calendar Localist`
- Concordia University Texas: `"Concordia University Texas" events calendar`
- Huston-Tillotson University: `"Huston-Tillotson University" events calendar`

**Presenter**
- Band: `"<specific CAPCOG-based band>" site:<candidate-domain>` then **fetch-confirm
  before trusting** — this session's finding is that the query alone is not enough;
  the fetch is the actual gate.
- Author: `oscarcasares.com events` (fetch-confirm the candidate already found)
- Visual artist: `wallyworkmangallery.com exhibitions` (fetch-confirm the candidate
  already found)
- Personality: `"Austin" comedian OR podcast "live taping" series -site:capcitycomedy.com -site:hideouttheatre.com -site:thevelveetaroom.com`

**Market**
- Wolf Ranch / Lakeline Plaza market-specific pages: `alwaysfunmarkets.com` fetch, to
  see if either site has its own dedicated URL beyond the operator's homepage
- Sun City Wilco Farmers Market (Georgetown, Tuesdays) and the Cedar Park "Bell
  District" market mentioned in search snippets: neither got its own row this
  session (only mentioned in passing, not independently confirmed) —
  `"Sun City" Georgetown farmers market official`, `"Bell District" Cedar Park
  market schedule`

**Aggregator**
- Nextdoor and Patch: verify their CURRENT event-listing features exist and are
  public before grading either (not done this session — see "Deliberately not
  added" above).

---

## Method: mapping the catalog into TAM type

For the 142 `official`-grade catalog rows, `type` was assigned mechanically by
category, with named overrides where the catalog's own fields don't match a
visitor-facing type (same precedent as `docs/CENSUS_CAPCOG.md`'s Do512/Resident
Advisor overrides):

- `university_calendar` → education; `library_calendar` → civic; `festival_feed` →
  group; `claimed_upload`/`email_opt_in`/`calendar_feed` → other (intake mechanisms,
  not destinations).
- `city_calendar` → civic by default, EXCEPT: a name containing "Farmers' Market" →
  market (1 row: SFC Farmers' Market); a name naming a specific single-site
  attraction (museum, cultural center, sculpture garden, a named park/square) →
  venue (7 rows: Carver Museum, AARC, Nature & Science Center, Ney Museum, Republic
  Square, Waterloo Greenway, Mueller Austin) — these are run by the city but are
  physical destinations, not the city's general calendar.
- `venue_calendar` → venue by default, EXCEPT when `entity_type == "org"`: those 16
  rows are hand-classified (too short a list to risk a keyword miss) — 12 stay
  `group` (performing-arts ensembles: Austin Symphony, Ballet Austin, Austin Opera,
  Austin Chamber Music Center, Golden Hornet, Tapestry Dance Company; sports teams:
  Round Rock Express, Austin FC, Austin Spurs; produced annual events: Rodeo Austin,
  treated like its festival_feed siblings; nonprofits without a single visiting
  site: Austin History Center Association, HAAM) and 4 move to `venue` because
  they're single-site museums/libraries despite the catalog's "org" entity_type
  (Bullock Texas State History Museum, LBJ Presidential Library, Thinkery, UMLAUF
  Sculpture Garden & Museum).
- Aggregator-shaped grades (`aggregator_lead`, `social`, `unknown`) and
  `trusted_publisher` are excluded from the TAM entity table entirely — they
  populate Table 2 instead.

This rule table plus the 25 new rows were assembled by a scratch script (not
committed — a one-time snapshot generator, same as the census's own precedent) that
reused the live `classify_entry()` for bucket and a hand-written, spot-checked rule
table for `type`; every one of the 16 org-row overrides and both city_calendar
keyword exceptions was read individually, not pattern-matched blind.

## Provenance

See also `docs/domain_recipes.md` for the per-cultural-domain seed/query-pack/hole
table (added at the founder's mid-session addendum, folded into this same PR).

`docs/TAM_CAPCOG.csv` is the single source of truth for row counts; this document's
tables are derived from it and re-check on any future update to the CSV, not the
other way around. The 142 catalog-derived rows trace to
`sources/master_sources_catalog_120.json` exactly as `docs/CENSUS_CAPCOG.md` already
documents (no source added, removed, or re-scored by this session). The 25 new rows
and 7 new aggregator rows trace to `WebSearch` results returned in this session
(2026-09-04) and are marked `found_unverified` throughout — see the honest method
note at the top of this document before treating any of them as more than a lead.
