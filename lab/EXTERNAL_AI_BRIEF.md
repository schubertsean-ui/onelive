# Brief for an external AI engineer

Hand this whole file to another AI (ChatGPT, Gemini, Grok, a different Claude
session — whatever you like) along with repository access. It is written to be
self-contained: someone who has never seen this codebase should be able to do
the work from it.

The prompt to paste is at the bottom. Everything above it is the context that
prompt refers to.

---

## 1. The product, in one paragraph

1LIVE is a live-events discovery site for Austin and the surrounding Hill
Country. It crawls venue, festival, civic and producer websites, extracts the
events they publish, passes them through a verification gate, and shows the
survivors on a public feed at `1live.co/tonight`. The site is currently behind
a stealth gate. There is also a licensed lane (Ticketmaster and similar) which
works fine and is not the subject of this brief.

## 2. What is wrong, measured

| | rows | with a usable future date |
|---|---|---|
| licensed lane (Ticketmaster/ics/jsonld) | 1,644 | 1,359 |
| **the crawler pipeline** | **2,215** | **1** |

2,214 of 2,215 crawled events have **no date at all**. The public feed filters
by date range and PostgREST drops NULLs from a range filter, so essentially
nothing the crawler finds is visible to a user. Every one of those rows passed
a trust gate and is labelled `confirmed`.

The owner diagnosed the root cause himself, correctly:

> "your main problem is you are doing a poor job investigating each web page
> and then clicking through to find the details"

The crawler fetches **one** URL per source, splits the returned text into
blocks, and asks a model to pull events out of the blob. It never finds a
site's events section, never opens an individual event's page, never follows a
ticketing link. Meanwhile the event pages state everything plainly — e.g.
`acllive.com/event/2026-08-06-masego-at-8-pm` reads
`THURSDAY AUGUST 6, 2026` / `8:00 PM`, and the date is also on the listing card
and in the URL slug.

## 3. What you are being asked to build

> "a perfect extraction or ingestion of every event, date, time, specifics,
> notes, descriptions, specials, etc that are on a site that will be and are
> translated to 1 live"

Concretely, for each site in the proving set: every event the site publishes,
with **title, date, start time, venue/location, description, price, and any
specials or notes** — ingested into the real database and visible on the live
site, staying correct when the source changes.

## 4. The four blockers you will hit immediately

Full evaluation in `docs/ops/CODE_EVALUATION_2026-08-06.md`. The four that
will stop you on day one:

**a) The extraction schema cannot hold what is being asked for — and the gap is bigger than dates.**
`worker/ai_models.py` defines the entire set of fields the extractor may
return: title, start_time, end_time, venue_name, city, artist_names,
ticket_link, rsvp_link, is_private_rsvp, private_access, notes. There is **no
price, no description, no category, no image**. Price columns exist on the
public `event` table (migration 0010) and are never filled by this path. Fix
this first or nothing else matters.

**b) Structured data is found and then destroyed.**
`worker/segment.py:252` (`_jsonld_event_text`) locates schema.org `Event`
JSON-LD — the typed object with `startDate` as an ISO timestamp — keeps only
name/startDate/location/url, **flattens them into a pipe-joined string**, and
hands that string to a model to re-extract. It discards `offers` (price),
`description`, `endDate`, `performer`, `image`, `eventStatus`, `doorTime`.
Reading those fields directly is free, exact, and cannot hallucinate.

**c) Nothing asserts that a published event is visible.**
20 validate checks, 1,953 tests, a golden exam, a trust gate and a non-Claude
adversarial review panel all pass on 2,214 invisible events. There is no test
anywhere that asks "can a user see this row?"

**d) A live trust defect in date parsing.**
`'September 4-27'` and `'SEPT 04-27'` both normalize to **2027-09-04** — the
range end is read as a year, and the guard designed to prevent invented dates
passes it because both of its probes agree. Meanwhile a fully-qualified range
(`'Fri, Sep 4, 2026 – Sun, Sep 27, 2026'`) is refused outright as unparseable,
so theatre runs and festivals are dropped wholesale.

## 4a. What "100% of the data" means — the target schema

Do not work from prose. Completeness is defined by three real consumers:

* **the card** — `web/lib/licensed.ts:48` `LicensedEvent`, the single shape
  both the licensed lane and the crawler lane render into. **26 fields.**
* **search** — the feed filters on `area`, `free`, `price`, `when`,
  `category`, `subsegment`.
* **analysis** — segment rollups, cost per verified event, freshness.

**The current extraction schema fills 7 of the card's 26 fields.** It cannot
supply `area`, `price`, or `is_free` — three of the six filters the product
offers. So even a perfect fix to the date problem leaves every crawled event
priceless, image-less and half-unfilterable, displayed beside Ticketmaster
rows that carry all of it.

**REQUIRED, group 1:** title · start_time · end_time · venue_name ·
venue_city · venue_address · venue_area · category · subsegment · price_min ·
price_max · currency · is_free · ticket_url · description · image_url · the
event's OWN page url.

**REQUIRED, group 2** (founder-ratified 2026-08-06, verbatim: *"Tier b is
required"* — previously "where the source states it", now the same standard and
the same threshold as group 1): performer · door_time · age_restriction ·
on_sale_status · **event_status — cancelled / postponed / rescheduled** ·
organizer · venue lat/lng/url/phone · series name for a run · specials (the
free-text offer, e.g. "$5 tacos before 7").

`event_status` is the one with teeth: it is discarded today, which means a
cancelled show stays on the site reading as live. That is a worse failure than
never listing it.

**ANALYSIS** (computed, not extracted): supply segment · size tier · which
extraction tier won · recurrence rule and whether a row is an expanded
occurrence · first_seen / last_verified · capacity.

**The one thing "required" does not mean:** never invent a field. A silent
source yields an honest null; a stated value we drop is a defect. Required
means we must capture what the source publishes, not manufacture what it
doesn't.

Nearly all of Tier A and much of Tier B is present in schema.org `Event`
JSON-LD — `offers.price`, `offers.availability`, `description`, `image`,
`endDate`, `performer`, `doorTime`, `location.address`, `location.geo`,
`eventStatus` — and the current code discards every one of them (see blocker
b). Getting these is mostly a matter of not throwing them away.

**Scoring:** field recall = fields correctly extracted ÷ fields the source
actually publishes, per field, against a hand-built fixture. A site that
states no price is not penalised; a site that states one and loses it is.
Target: **≥98% on both required groups**, 100% correctness on
cancelled/postponed marking, and **zero** fields asserted that the source does
not state.

## 5. The architecture you are replacing, and the one proposed

**Today:** `fetch(one url)` → `segment text into blocks` → `model call per
block` → candidate → gate → promote → feed.

**Proposed** (full plan in `lab/PLAN.md`) — an escalation ladder that pays for
a model only where a site publishes nothing structured:

| Tier | Method | Model cost |
|---|---|---|
| 0 | schema.org JSON-LD / microdata, read as **typed fields** | $0 |
| 1 | machine feeds the site already publishes (`.ics`, RSS, JSON) | $0 |
| 2 | enumerate event links → open each detail page → deterministic parse | $0 |
| 3 | model reads **one event detail page** (not a blob) | cheap tier |
| 4 | browser render, then re-enter at tier 0 | render time |
| 5 | follow the ticketing platform (Ludus, Tixr, Eventbrite, See Tickets…) | as above |

You are not obliged to adopt this. If you have a better architecture, say so
and justify it. But **start with a $0 census** of how many sites tiers 0–2
already serve, because that number governs the entire cost profile and costs
nothing to learn.

## 6. The proving set

62 sites: two representatives of each of the 23 ratified supply segments, plus
16 chosen by the owner. The full table is in `lab/PLAN.md` §3. It deliberately
spans hard cases: JS-rendered sites (ACL Live), theatre runs with off-domain
ticketing (Bastrop Opera House / Ludus), aggregators, civic calendar software,
wineries and breweries with recurring weekly events and ticketed tastings, and
artist tour pages.

## 7. Constraints that are not negotiable

- **Budget: $100 total model spend.** Log real token usage per call and compute
  cost from published prices. Report at $10/25/40/50/75/90. Hard stop at $100.
- **Cheapest capable model per stage.** Reading an explicit date off a detail
  page is the easiest extraction task in the system; do not spend a frontier
  model on it.
- **Never invent a fact.** The product's core promise is that a date on the
  site was stated by the source. Refusing to store a value is always correct;
  guessing one is never correct. A single fabricated date fails the whole run.
- **Generalize.** One pipeline for all sites. Per-site adapters are a finding
  to report, not a shortcut to take.
- **Testing ground only.** Work on branch `claude/crawler-lab`, directory
  `lab/`. Do not modify `worker/`, `web/`, `ai/`, the gates, or pipeline
  workflows without explicit approval.
- **Prove, don't assert.** Build hand-written ground-truth fixtures per site
  *before* extraction runs, and score precision/recall/field-accuracy against
  them. Show every miss and every wrong value.

## 8. Things about this repo that will waste your time if nobody warns you

- **The dev sandbox has no outbound network.** Every real-site test must run
  from GitHub Actions. You cannot curl a venue page locally.
- **`tools/validate` runs 20 checks and 1,953 tests** and is a precondition for
  the adversarial-review workflow. If validate fails, the review never runs.
- **`staleness_check` fails any branch that does not edit `STATE.md`** whenever
  master has moved since STATE.md was last touched. This silently blocks CI.
- **Any change to one of 29 "runtime" files** (see `tools/arming_runtime.py`)
  invalidates `docs/evidence/ARMING_SMOKE_RUN.json` and turns trust-gate and
  adversarial-review red until a fresh ingest run is dispatched against the
  branch head and re-bound in a commit. PR #189 has 21 superseded re-arm runs.
- **`ingest.yml` shares one concurrency slot with the production cron.**
  Dispatch once and leave it; a second dispatch cancels the first.
- **`construction_gate` matches trigger words anywhere in the diff content**,
  so a document *about* defects trips every class it names (45 on a recent
  commit). Advisory, non-blocking, safe to ignore — but alarming if unexpected.
- **The golden exam is red by design** on any PR touching
  `worker/ai_extract.py`. That specific red is an enumerated exception.

## 9. Reference map

| Path | What it is |
|---|---|
| `docs/ops/CODE_EVALUATION_2026-08-06.md` | Full A–Z evaluation with severities and a ranked fix list |
| `docs/ops/CRAWLER_DEPTH_DIAGNOSIS_2026-08-06.md` | How the root cause was found, with evidence |
| `lab/PLAN.md` | Proposed plan: ladder, 62-site set, 10 decisions, acceptance criteria, budget |
| `docs/RECORD.md` R-081/082/083/084 | Open defects: fabricated year, exam never re-runs, bad catalog URLs, unmeasured cause split |
| `worker/orchestrator.py` | The per-source loop (fetch → sensor → segment → extract → gate) |
| `worker/segment.py` | Blob splitting + the JSON-LD flattening defect |
| `worker/ai_extract.py` | Model extraction, one call per block |
| `worker/ai_models.py` | The extraction schema (missing fields) |
| `worker/datetime_normalize.py` | Date refusal logic (sound, except ranges) |
| `worker/fetch/render_fetch.py` | Headless renderer + its too-narrow trigger |
| `worker/gating.py` / `promote.py` | Trust gate and publication |
| `web/lib/promoted.ts` | How the public feed reads events (the date filter that hides everything) |
| `tools/sample_dateless.py` | Read-only diagnostic that produced the numbers above |

---

# THE PROMPT — paste everything below into the other AI

```
You are taking over an event-extraction engine that does not work. Read the
brief in lab/EXTERNAL_AI_BRIEF.md and the evaluation in
docs/ops/CODE_EVALUATION_2026-08-06.md before writing any code. Do not
re-derive the diagnosis; it is measured and cited.

THE PROBLEM
A crawler pipeline has published 2,215 events. 2,214 of them have no date, so
the public feed cannot display them. The cause is that the crawler fetches ONE
url per site and never opens an individual event's page, where sites state the
date, time and price plainly.

WHAT I WANT BUILT
For every site in the 62-site proving set (lab/PLAN.md section 3): extract
every event the site publishes, with title, date, start time, venue/location,
description, price, and any specials or notes the source states. Ingest them
into the real database. Prove all four stages work: reading, extraction,
ingestion, and updating when the source changes.

FIX THESE FIRST — they are hours of work each and they block everything else:
1. worker/ai_models.py fills only 7 of the 26 fields the card contract
   (web/lib/licensed.ts:48 LicensedEvent) requires. It has no price, is_free,
   category, subsegment, area, address, image or description — so crawled
   events cannot be filtered by area, price or free, which are three of the
   six filters the product offers. Extend the schema to the full required list in
   section 4a of the brief (both groups — group 2 is required, not optional), through the candidate table and the promote
   INSERT. This is a precondition, not a follow-up.
2. worker/segment.py:252 finds schema.org JSON-LD, keeps 4 of ~12 fields,
   flattens it to a pipe-joined string, and pays a model to re-read it. Read
   the typed fields directly instead. This is free, exact, and gives you price
   and description on every site that publishes them.
3. Nothing asserts that a published event is visible to a user. 2,214
   invisible events passed 20 gates and 1,953 tests. Add that assertion.
4. 'SEPT 04-27' parses to 2027-09-04 — the range end is read as a year and the
   anti-fabrication guard passes it. Fix it. A fully-qualified range like
   'Fri, Sep 4, 2026 - Sun, Sep 27, 2026' is refused entirely; fix that too.

THEN build detail-page navigation: find a site's events page, enumerate the
individual event links, open each one, and extract from the page that states
the facts. Render with a browser when the fetched HTML has no event links and
no structured data. Follow the ticketing platform one hop when a venue defers
showtimes to it.

HARD RULES
- $100 total model spend, hard stop. Log real token usage per call, compute
  cost from published prices, and report at $10/25/40/50/75/90.
- Use the cheapest model that meets the bar at every stage. Escalate only
  after a measured failure, and record why.
- NEVER invent a fact. Refusing to store a value is always correct; guessing
  one never is. One fabricated date fails the entire run.
- Build ground-truth fixtures by hand from the rendered pages BEFORE running
  extraction, and score precision, recall and per-field accuracy against them.
  Show every miss and every wrong value. Numbers, not assertions.
- One generic pipeline. If a site needs bespoke handling, report it as a
  finding rather than special-casing it.
- Work on branch claude/crawler-lab under lab/. Do not merge anything.
- Start with a $0 census: how many of the 62 sites publish schema.org JSON-LD,
  a machine-readable feed, or plainly-enumerable event links? That number
  decides the whole cost profile and costs nothing to learn.

THINGS THAT WILL WASTE YOUR TIME IF YOU DON'T KNOW THEM
- The dev sandbox has no outbound network. Real-site tests run from GitHub
  Actions only.
- tools/validate (20 checks, 1,953 tests) gates the review workflow; if it
  fails, the review never runs.
- staleness_check fails any branch that doesn't edit STATE.md when master has
  moved.
- Changing any of 29 "runtime" files (tools/arming_runtime.py) invalidates
  docs/evidence/ARMING_SMOKE_RUN.json and turns two checks red until a fresh
  ingest run is dispatched and re-bound.
- ingest.yml shares one concurrency slot with the production cron; dispatch
  once and leave it.

DELIVER
1. The census: how many sites each tier serves.
2. A results table: 62 sites x method used x precision/recall/field accuracy
   against hand-built ground truth, with every failure shown.
3. Proof of reading, extraction, ingestion and updates, including events
   visible on the live site.
4. The spend ledger and the final figure.
5. A written recommendation of what to adopt and what to discard, and why.

Disagree with anything in the plan if you have a better answer, and say why.
Do not narrate progress. Come back when it works, when you hit a budget
checkpoint, or when you hit something that genuinely needs a human decision
(money, legal, a change to what counts as verified, credentials).
```
