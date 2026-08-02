# 1LIVE — Source Expansion Plan v1 (Government · Media · Multilingual)

**Status:** PLAN of record (research-backed, 2026-08-01). Consolidates three deep research
passes — government databases, local media outlets, and non-English/multilingual outlets — into
one prioritized build plan for the "phenomenal database" the founder directed: every licensed
station, periodical, monthly/weekly, student-radio station, approved festival/market, and the
government licensing/permit registries behind them. Maps to the existing `gov_open_data`
(Socrata) pathway and the harvest capability (`ONE_LIVE_HARVEST_AND_SUBSCRIBE_v1.md`).

**Honest baseline (why this exists):** the catalog has **180 sources**, but government
administrative/licensing databases are effectively **0 wired** (the `gov_open_data` importer's
dataset list is still a placeholder), and local media is thin (6 radio · 4 TV · 1 newspaper · 3
digital catalogued). This plan closes that.

**Legal posture (the load-bearing rule):** prefer **free, public, authoritative registries**;
a **name is a fact** (not copyrightable), so once we have an entity's name we ingest from its
**own public site** (local-first, gated) — never from a paywalled directory's compilation. We do
**not** rely on paid directories (Ulrich's, E&P); the free registries below cover the same
universe. Web-searching for long-tail groups and pulling their public pages is clean and
complementary. Everything still passes the corroboration gate — **AI never publishes**.

**Coverage is measured at the EVENT level — no venue is pre-excluded (founder correction,
2026-08-01).** A place is never disqualified for "not being a cultural venue." Any premises that
can host a gathering is a potential one-off cultural-event source — an anniversary party with a
special guest, an author reading in a shop, a street fair in a parking lot. That **once-a-year
moment is exactly when the place needs 1LIVE**, and those long-tail one-offs are the moat, not
noise. So the registries define a **universe to WATCH, never a list to prune** to an "obviously
cultural" subset. Consequences, binding on everything below:
- **Report coverage as events caught vs events that happened** (per city / per category), never
  as "% of cultural venues." A venue earns its listing by hosting an event; any venue can, sometimes.
- **Any NAICS/registry count (e.g. CBP NAICS 71/7224) is a market-SIZING proxy only** — never a
  gate on inclusion. Sizing the market ≠ selecting who to monitor.
- **The engineering problem is cheap long-tail monitoring + one-off detection** (first-party
  pages, newsletter/RSS harvest, municipal special-event permits) — not venue classification.

---

## Part A · Government data (the fast, mostly-free unlock)

**Platform fact that saves the most work:** `data.texas.gov`, `data.austintexas.gov`, and
`opendata.fcc.gov` are all **Socrata** — and our importer already speaks Socrata. Anything on
those hosts is a **config-only** add (dataset id + field_map into
`sources/gov_open_data_datasets.json`), no code.

Every source tagged **[ENUM]** (enumerates event-publishing entities → seed/discover) and/or
**[VERIFY]** (verifies facts: licensed entity, type, capacity → raises confidence). Access:
**A** = Socrata-native (config-only) · **B** = small new adapter · **C** = messy (portal/PDF/agreement).

### A1 · Wire NOW — Tier-A, config-only (no code; importer + tests + CI already exist)
1. **TABC Licenses** — `data.texas.gov` `kguh-7q9z` — every licensed bar/venue (trade name, owner, address, county, license type, status). **[ENUM]+[VERIFY]**. `where` → CAPCOG counties. (`tools/fetch_tabc.py`/`tabc_classify.py` already in-tree.)
2. **Comptroller Mixed-Beverage / Alcohol Sales** — `data.texas.gov` `34p3-r3x8` — every alcohol-by-the-drink establishment **+ monthly receipts** (a liveness/scale signal). **[ENUM]** + liveness.
3. **Austin Food Establishment Inspections** — `data.austintexas.gov` `ecmv-9xxi` — every permitted restaurant/bar/food-truck (name, address, type, score). **[ENUM]+[VERIFY]**.
4. **TDLR All Licenses** — `data.texas.gov` `7358-krk7` — occupational/business licensees (incl. pyro/combustibles relevant to festivals). **[VERIFY]**.
5. **Austin Construction / CO permits** — `data.austintexas.gov` `3syk-w9eu` — occupant-load / capacity proxy. **[VERIFY capacity]** (the hardest fact).

### A2 · Tier-B — one small adapter each, high value
6. **FCC LMS station DB (TX subset)** — `opendata.fcc.gov` `nsck-y87u` (Socrata mirror) / FM-AM-TV Query bulk — **the authoritative list of every licensed radio/TV station.** **[ENUM]+[VERIFY]**.
7. **IPEDS directory (TX)** — NCES / Urban Institute REST — every college/university/community college → student radio + campus calendars. **[ENUM]**.
8. **THC Atlas GIS** — museums + historic/state sites (shapefile→GeoJSON). **[ENUM]**.
9. **ArcGIS-Hub adapter (~1 day)** — unlocks **CAPCOG regional**, **Hays County**, **Round Rock GeoHub** and most other TX cities/counties the same "no per-city code" way Socrata unlocked the state. The second dominant TX gov platform. **[ENUM]+[VERIFY]**.
10. **Census County Business Patterns** — `api.census.gov` NAICS 71/7224 by county — coverage denominator / sizing. **[VERIFY/sizing]**.
11. **IMLS** Museum Universe + Public-Library Outlet files (static CSV seeds). **[ENUM]**.

### A3 · The leading-indicator layer — municipal event-permit registries (messy, most differentiated)
A special-event/festival/market permit is filed and approved **before** the event, naming
organizer + dates + location — a government-anchored *upcoming-event* feed. Reality: the approval
process is universal, open publication as data is rare.
- **City of Austin (ACE)** — special events via the Austin Center for Events; ROW/street-closure via the AB+C portal; food/market via Austin Public Health. No clean Socrata "approved special events" table found. **→ Founder action: request a standing data export from ACE** — the single best leading indicator in our home market.
- **Round Rock** publishes some permit layers (ArcGIS); **everyone else** (Georgetown, San Marcos, Cedar Park, Kyle, Buda, Dripping Springs, Bastrop, Lakeway, Fredericksburg) is application-PDF / vendor-portal / **council-agenda** only.
- **Realistic pipeline for Tier-C cities/counties:** harvest **Commissioners Court / city-council agendas** (mostly CivicPlus / BoardDocs / Legistar — predictable URLs, often iCal/RSS) → AI-extract "special event permit / street closure approved" line items → the normal gate as upcoming-event candidates. This is `ai_extract_triangulated` work, not `gov_open_data`.
- **TDA Certified Farmers Markets** — the registry of recurring markets. **[ENUM]** recurring events.

---

## Part B · Local media outlets (enumerate from free registries, ingest via RSS/newsletter)

**Enumerate authoritatively (all free/public unless noted):**
- **Radio & TV:** the **FCC** FM/AM/TV Query + LMS — every licensed station by community (call sign, licensee, service, coordinates). Cross-check format via **radio-locator.com**.
- **Newspapers/weeklies:** **Texas Press Association** county directory · **Medill State of Local News** county DB (catches digital-only + ethnic) · **USNPL**.
- **Student/college radio:** **IPEDS** (all colleges) + **College Broadcasters Inc.** / **Radio Survivor** directories.
- **Periodicals/monthlies:** **ISSN / Library of Congress** · USPS periodicals permits (PS Form 3526) · (Ulrich's/E&P are paid cross-checks, **not required**).

**Enumerable region-wide: ~185–250 outlets; ~105–130 that publish upcoming events.**

**Event-content channels (ingest cleanest first):**
- **Universities → Localist / ICS / JSON** (`/api/2/events` + per-calendar RSS/ICS) — the highest signal-to-noise for **talks & lectures**.
- **News/magazines → WordPress `/feed/`** RSS (test `/feed/`, `/events/feed/`).
- **Community Impact** → per-edition RSS (`communityimpact.com/rss-feeds/`) — ~9 Central-TX editions, one integration.
- **Newsletters** (Axios Austin, Do512 Weekly, station lists) → the inbound-email pipeline (Half B of the harvest spec). Substack also exposes `/feed`.
- **Broadcast TV "community calendars" + small commercial radio** → structured scrape, last.

**First batch (highest-value, feed-friendly):** Austin Chronicle events, Community Impact (all editions), CultureMap, KUT/KUTX/KMFA, Austin Monthly, Texas Monthly, Tribeza, Austin Family, Edible Austin, Austin Fit, Austin Monitor, Texas Tribune, Axios Austin; **universities** UT/Texas State/ACC/St. Edward's + **KVRX / KTSW**; **county weeklies** (Williamson County Sun, Hays Free Press, Fredericksburg Standard, DailyTrib, Bastrop Advertiser, San Marcos Daily Record, Taylor Press, Llano News, Fayette County Record, Giddings Times); TV (KXAN, Austin PBS), Statesman/Austin360.

---

## Part C · Non-English / multilingual (architect now, scale at expansion)

**Key methodology finding:** the **FCC carries no language/format field** (format isn't
regulated) — you cannot filter it for "Spanish." Enumerate by language by layering a
language source on the FCC call-sign universe:
- **radio-locator.com format filter** (Spanish/Regional-Mexican/Tejano/Ethnic) — free.
- **CUNY Center for Community Media** — **Latino Media Map** + **AAPI Media & Directory** (653 outlets, 54 languages), searchable by city/language/media type — the authoritative ethnic-media registries.
- **Ethnic Media Services** national directory (3,000+); **NAHP** (Hispanic); **3AF** (Asian); **Briscoe Center (UT)** Texas ethnic-newspaper list; Austin Public Library international-news guide.

**Decision (bake in now, cheap):** **`language` is a first-class field on every source/event/
content record** (default `en`), populated from radio-locator (broadcast) + the CCM/EMS/Briscoe
directories (print/digital). This makes the roster language-filterable from day one — what the
multi-city expansion needs. See the multilingual management principle below.

**Central Texas non-English now (~20–25 outlets):** Spanish radio (KLZT "La Z" 107.1, KLJA
"Amor" 107.7, KLQB "La Que Buena" 99.5, KELG, KTXZ); Spanish TV (Univision **KAKW**, Telemundo);
Spanish print/digital (El Mundo, La Voz de Austin, Que Onda, Austin Vida, ¡Ahora Sí!); Asian —
Asian South Austin + community-org newsletters. Feed-friendly first = the WordPress Spanish
weeklies (`/feed/`) + Univision/Telemundo "eventos" pages.

**Larger-market preview:** non-English roughly **doubles** the outlet count per metro — Houston
(Vietnamese + Chinese hub: Radio Saigon Houston, Southern Chinese Daily News…), DFW (Korean +
Vietnamese + Spanish Al Día), San Antonio (Spanish-dominant, La Prensa). Budget ~50–100+ ethnic
outlets per metro, enumerated via the CCM maps + EMS + NAHP + 3AF + Briscoe.

### Multilingual management principle (dual-language)
1. **Ingest any language natively** (the LLM extractor is multilingual — no extra service). Tag `language`.
2. **Original is the record; translation is a derived, labeled display layer** — never overwrites the source (Spark-Line faithfulness discipline).
3. **Facts are never translated** (venue/performer names, dates, addresses, ticket links stay verbatim); only descriptive prose is translated, machine-translations labeled, original one tap away.
4. **Display = the reader's choice**; a non-English event is **fully first-class — shown & findable, never hidden** for language.
5. **Discovery is cross-lingual** (an English search finds Spanish-tagged events and vice versa).
6. Trust rules carry over (disputed-shown across languages; MT never presented as the venue's own words).
- **Now (cheap):** the `language`-native data model. **Later (founder-gated):** the translation-display service + full multilingual UI (RTL/character sets, a translation API = spend) at larger-city expansion.

---

## Prioritized build sequence

1. **Gov Tier-A (config-only) — now:** fill `sources/gov_open_data_datasets.json` with datasets 1–5 (`where`-scoped to the 10 CAPCOG counties). Field names confirmed at wire-time on CI (where the importer runs). Turns "0 gov databases" into real authoritative venue data with no code.
2. **RSS/Localist/Community-Impact ingester** (harvest Half A) — the media first batch; universities' Localist for talks/lectures.
3. **ArcGIS-Hub adapter** — unlock CAPCOG/Hays/Round Rock (counties).
4. **FCC + IPEDS + CCM/EMS enumerators** → seed the media/station/college roster with `language` tags.
5. **Municipal permit / agenda-harvest program** (leading indicator) — + the founder's ACE export request.
6. **Inbound-email pipeline** (harvest Half B) — after the domain/identity decision — for newsletter-only outlets.

**Founder actions:** (1) request a standing special-events data export from the **Austin Center for Events**; (2) the harvest inbound-email domain + identity (per `HARVEST_AND_SUBSCRIBE_v1`); (3) the free YouTube Data API key (per `VERIFIED_PREVIEW_ENRICHMENT_v1`). Everything else the agent builds and gates.

---

## Appendix · Registries (the reproducible, free enumeration backbone)
FCC FM/AM/TV Query + LMS (`opendata.fcc.gov nsck-y87u`); `data.texas.gov` (TABC `kguh-7q9z`,
Alcohol Sales `34p3-r3x8`, TDLR `7358-krk7`); `data.austintexas.gov` (food `ecmv-9xxi`, permits
`3syk-w9eu`); Texas Press Association county directory; Medill State of Local News; USNPL; IPEDS
/ Urban Institute; College Broadcasters Inc.; ISSN (LOC); THC Atlas GIS; CAPCOG/Round Rock
ArcGIS Hub; Census CBP; IMLS; TDA Certified Farmers Markets; radio-locator; CUNY Center for
Community Media (Latino + AAPI maps); Ethnic Media Services; NAHP; 3AF; Briscoe Center. Grounds
on: `worker/importers/socrata.py`, `worker/importers/run_gov_import.py`,
`sources/gov_open_data_datasets.example.json`, `docs/strategy/ONE_LIVE_HARVEST_AND_SUBSCRIBE_v1.md`.
