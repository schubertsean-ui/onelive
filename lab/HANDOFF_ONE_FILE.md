# 1LIVE — Complete handoff for an external AI engineer

**ONE FILE. Everything needed is below. Paste the whole thing.**

Assembled 2026-08-06 from `lab/EXTERNAL_AI_BRIEF.md`,
`lab/PIPELINE_COMPONENTS.md` and `lab/PLAN.md` in the repo
`schubertsean-ui/onelive`. If you have repository access, those files and
`docs/ops/CODE_EVALUATION_2026-08-06.md` hold the same content with full
citations. If you do not, this file is self-contained.

---

# START HERE — THE INSTRUCTION

You are taking over an event-extraction engine that does not work. Read this
entire document before writing code. The diagnosis is measured and cited — do
not re-derive it.

**The problem:** a crawler has published 2,215 events. 2,214 have no date, so
the public feed cannot display them. It fetches ONE url per site and never
opens an individual event's page, where sites state the date, time and price
plainly.

**What to build:** for every site in the proving set (Part 4), extract every
event the site publishes with every required field (Part 3), ingest it into
the real database, and prove four things work — reading, extraction,
ingestion, and updating when the source changes.

**Fix these first. Hours of work each, and they block everything else:**

1. `worker/ai_models.py` fills only 7 of the 26 fields the card contract
   requires. No price, is_free, category, subsegment, area, address, image or
   description — so crawled events cannot be filtered by area, price or free,
   three of the six filters the product offers. Extend the schema to the full
   required list in Part 3, through the candidate table and the promote INSERT.
2. `worker/segment.py:252` finds schema.org JSON-LD, keeps 4 of ~12 fields,
   flattens it to a pipe-joined string, and pays a model to re-read it. Read
   the typed fields directly. Free, exact, and it hands you most of Part 3.
3. Nothing asserts that a published event is visible to a user. 2,214
   invisible events passed 20 gates and 1,953 tests. Add that assertion.
4. `'SEPT 04-27'` parses to **2027-09-04** — the range end is read as a year
   and the anti-fabrication guard passes it. A fully-qualified range
   (`'Fri, Sep 4, 2026 - Sun, Sep 27, 2026'`) is refused entirely. Fix both.

**Then** build detail-page navigation: find a site's events page, enumerate the
event links, open each one, extract from the page that states the facts.
Render with a browser when the fetched HTML has no event links and no
structured data. Follow the ticketing platform one hop when a venue defers
showtimes to it.

**Hard rules**
- $100 total model spend, hard stop. Log real token usage per call, compute
  cost from published prices, report at $10/25/40/50/75/90.
- Cheapest model that meets the bar at every stage. Escalate only after a
  measured failure, and record why.
- **NEVER invent a fact.** Refusing to store a value is always correct;
  guessing one never is. One fabricated date fails the entire run.
- Build ground-truth fixtures by hand from the rendered pages BEFORE running
  extraction. Score precision, recall and per-field accuracy against them.
  Show every miss and every wrong value. Numbers, not assertions.
- One generic pipeline. A site needing bespoke handling is a finding to
  report, not a shortcut to take.
- Work on branch `claude/crawler-lab` under `lab/`. Merge nothing.
- **Start with a $0 census:** how many of the sites publish schema.org
  JSON-LD, a machine-readable feed, or plainly-enumerable event links? That
  number decides the whole cost profile and costs nothing to learn.

**What you must hand back, and how it will be judged** — Part 4, section 10 is
the RETURN CONTRACT. Read it before you start; it changes how you work. In
short: your output is not a report, it is evidence a third party can re-verify
without trusting you. Commit the page snapshots you scored against. Write
ground truth by hand before extraction runs. Give every asserted field value a
provenance that can be found in the snapshot — one value that cannot be is a
fabrication, and one fabrication fails the whole run. No summarizing, no
assuming, no quoting a number you have not just recomputed. Your scores will be
independently recomputed, your ground truth re-derived for a random sample, and
the live feed read directly to confirm visibility. **A holdout set of sites you
will never see will be run against your engine unchanged** — build for the
general case, not for the list.

**Deliver**
1. The census: how many sites each method serves.
2. A results table: every site x method used x precision/recall/field accuracy
   against hand-built ground truth, with every failure shown.
3. Proof of reading, extraction, ingestion and updates, including events
   visible on the live site.
4. The spend ledger and the final figure.
5. A written recommendation of what to adopt and what to discard, and why.

Disagree with anything here if you have a better answer, and say why. Do not
narrate progress. Come back when it works, at a budget checkpoint, or when
something genuinely needs a human decision.

---





# PART 1-4 — CONTEXT, BLOCKERS, TARGET SCHEMA, PROVING SET, RETURN CONTRACT


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

## 10. THE RETURN CONTRACT — what you must hand back, and how it will be judged

Read this before you start, because it changes how you work. Your output is not
a report; it is **evidence that a third party can independently re-verify
without trusting you**. Anything that cannot be re-verified will be discarded
regardless of how good it looks.

### 10.1 Artifacts you must produce (exact paths, machine-readable)

| Path | Contents |
|---|---|
| `lab/snapshots/<site_id>/<page>.html` | The exact bytes you scored against. Committed. Without these nothing you claim can be checked. |
| `lab/truth/<site_id>.json` | Hand-built ground truth: every event on that page, every field the page states, written BEFORE extraction ran, with the URL and the timestamp you read it. |
| `lab/results/census.json` | Per site: structured data present (y/n, which), machine feed present (y/n, which), event links enumerable (y/n, count), render required (y/n), final URL after redirects, HTTP status, bytes. |
| `lab/results/extraction.json` | Per site, per event, **per field**: the value, the method that produced it (`jsonld` / `feed` / `html` / `model` / `derived`), and its **provenance** — the JSON path, CSS selector, or byte offset in the snapshot it came from, plus the source URL. |
| `lab/results/scores.json` | Per site, per field: true positives, false positives, false negatives, precision, recall. Computed, not asserted. |
| `lab/results/failures.jsonl` | One line per miss or wrong value: expected, got, the raw snippet from the snapshot, and your classification of why. |
| `lab/results/ingestion.json` | Rows written to the database: event ids, the tag identifying them as proof rows, and a **read-back from the public feed API** showing each one visible with its fields. |
| `lab/results/updates.json` | The seeded change test: the three changes made (moved / cancelled / added), before and after state, and what the database and feed showed. |
| `lab/spend.jsonl` | One line per model call: model id, input tokens, output tokens, unit prices used, computed cost, running total. |
| `lab/RECOMMENDATION.md` | What to adopt into `worker/`, what to discard, and why — each claim citing an artifact above. |

### 10.2 Evidence rules — non-negotiable

1. **No summarizing.** Report raw counts and raw values. "Most sites worked" is
   not a result; `47/62` with the list of the 15 is.
2. **No assuming.** If something is unknown, write `UNKNOWN` and the reason.
   An unknown that is stated is fine; an unknown presented as a fact is a
   failed run.
3. **No reliance on memory.** Re-read the artifact every time you cite it.
   Never quote a number you have not just recomputed.
4. **No making things up.** Every asserted field value must be locatable in the
   committed snapshot at the provenance you recorded. A value that cannot be
   found there is a fabrication, and fabrication fails the whole run — not
   that field, the run.
5. **Ground truth is written first.** If you author or amend a truth fixture
   after seeing extractor output, say so explicitly on that fixture. An
   unmarked post-hoc edit invalidates the site's score.
6. **Every number must be reproducible** by running your scorer over your
   snapshots and your fixtures with no network access.

### 10.3 How your work will be judged — the adjudication protocol

Stated in advance so it cannot be argued with afterwards.

1. **Independent re-scoring.** Your snapshots and fixtures will be re-scored
   with a *different* scorer. If the numbers differ materially from
   `scores.json`, your scores are void and the re-score stands.
2. **Ground-truth audit.** Your fixtures are a self-graded exam — you wrote
   both the answers and the test. Truth will be independently re-derived for a
   **random sample of sites** from your committed snapshots. Systematic
   disagreement voids the fixture set and the run is repeated.
3. **Provenance audit.** A random sample of asserted field values will be
   checked against the snapshot at the cited provenance. **Any value not found
   there fails the run.**
4. **Visibility proof.** The public feed will be read directly to confirm the
   ingested events are actually visible with their fields. This is the check
   whose absence let 2,214 invisible events pass every gate in this repo.
5. **Cost audit.** Spend is recomputed from `spend.jsonl`. A total that does
   not reconcile is treated as an unmeasured run.
6. **Adversarial pass.** Your recommendation goes to a non-Claude review panel
   before adoption.
7. **HOLDOUT TEST — declared now so you do not tune to the set.** A number of
   sites are being held back that are **not** in the proving set and will not
   be shown to you. Your engine will be run against them unchanged. If
   performance on the holdout is materially worse than on the proving set, the
   engine is overfitted and will not be adopted no matter how good the
   in-sample numbers are. Build for the general case.

### 10.4 The adopt / discard criteria — decided before your results exist

**Adopted** only if ALL hold:
- meets the acceptance thresholds in §4a and the plan's §7;
- **zero fabrications** in the provenance audit;
- holdout performance within a small margin of in-sample;
- simpler than the code it replaces, or with the added complexity justified by
  a measured failure it fixes;
- cost per verified event inside budget;
- no trust relaxation required to pass.

**Discarded** if ANY hold:
- per-site special-casing standing in for generalization;
- thresholds met by narrowing the denominator (e.g. dropping hard sites);
- claims that cannot be re-verified from the committed artifacts;
- a gate, threshold or definition of "verified" had to be weakened.

**Escalated to the founder, never decided by an agent:** anything touching
money, legal posture, credentials, what counts as verified, or a gate
threshold.

### 10.5 How adoption will be proved to serve the stated vision

Each objective, in the founder's own words, is bound to one measurable. A
recommendation is adopted only when its column moves.

| Objective (founder's words) | Measurable | Today |
|---|---|---|
| *"my site live and full of thousands of events"* | count of **visible, future-dated** events on the live feed | **1** |
| *"every event, date, time, specifics, notes, descriptions, specials"* | field recall across both required groups, where the source states the field | unmeasured; schema can hold ~7 of 26 |
| Cards that look like a product | % of published events carrying every required card field | ~0% (no price, image, description) |
| Search that works | % of published events filterable by `area`, `price`, `free` | **0%** |
| Data analysis | funnel exists end-to-end: sources → fetched → events → candidates → gate → promoted → **visible** | no funnel |
| Trust | fabricated fields; cancelled events shown as live | 1 known fabrication path (R-081); cancellation discarded entirely |
| Cost discipline | $ per verified event | unmeasured |

A change that improves an internal metric while leaving the "visible events"
column at 1 has not accomplished anything, and will be recorded as such.

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

DELIVER — see the RETURN CONTRACT in section 10. Summary of the rules:
- Commit the page snapshots you scored against. Without them nothing you claim
  can be verified, and unverifiable claims are discarded.
- Write ground truth BY HAND, BEFORE extraction runs. If you amend a fixture
  after seeing output, mark it; an unmarked post-hoc edit voids that site.
- Every asserted field value must carry provenance (JSON path, selector, or
  byte offset in the snapshot) and must be findable there. A value that is not
  is a fabrication, and one fabrication fails the entire run.
- No summarizing ("most sites worked" is not a result — give 47/62 and name
  the 15). No assuming (write UNKNOWN and why). No quoting a number you have
  not just recomputed. No making things up.
- Your scores will be independently re-computed from your artifacts, your
  ground truth will be re-derived for a random sample, a random sample of
  field values will be checked against provenance, and the live feed will be
  read directly to confirm visibility.
- A HOLDOUT SET of sites you will never see will be run against your engine
  unchanged. If it performs materially worse there, the engine is overfitted
  and will not be adopted. Build for the general case, not for the list.

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



# PART 5 — THE PIPELINE, STAGE BY STAGE

recalled. Where a stage does not exist, it says **MISSING** rather than
describing what it would do if it did.

**Legend** — ✅ works · ⚠️ exists but defective · ❌ missing entirely

---

## The 19 stages

| # | Stage | Today |
|---|---|---|
| 1 | Source discovery (search) | ⚠️ |
| 2 | Source qualification | ❌ |
| 3 | Entry-point resolution | ❌ |
| 4 | Scheduling & budget | ✅ |
| 5 | Acquisition (fetch) | ⚠️ |
| 6 | Rendering | ⚠️ |
| 7 | Listing enumeration | ❌ |
| 8 | Detail acquisition | ❌ |
| 9 | Structured-data harvest | ⚠️ |
| 10 | Model extraction | ⚠️ |
| 11 | Normalization | ⚠️ |
| 12 | Identity, dedupe & occurrence expansion | ⚠️ |
| 13 | Enrichment | ⚠️ |
| 14 | Candidate persistence | ⚠️ |
| 15 | Corroboration | ✅ |
| 16 | Gate / verification | ⚠️ |
| 17 | Promotion (publishing) | ⚠️ |
| 18 | Serving (the read path) | ⚠️ |
| 19 | Freshness, change detection & retirement | ❌ |
| 20 | Measurement & analysis | ⚠️ |

Nineteen numbered stages, twenty rows — measurement is numbered 20 because it
sits across all of them rather than after them.

---

# PART ONE — SEARCHING (finding the supply)

## 1. Source discovery — ⚠️ built, never run at scale

**Job:** find websites that publish events we don't yet know about.

**Today:** `tools/scan_new_sources.py`, `tools/discover_eventbrite_orgs.py`,
`tools/search_discover_eventbrite.py` exist. The Brave search lane and
`source-scan.yml` are on unmerged PR #187. The launch sweep has never run.

**Defect:** 180 sources in the committed catalog, 266 enabled in production —
86 seeded directly to the database and never audited. **Nine of the 23
ratified supply segments have no representative at all** (recurring-scene
organizers, social-dance, bands, solo musicians, DJs, comedians, visual
artists).

**Done looks like:** every segment has coverage proportional to its real supply;
new sources arrive continuously; each carries segment + size tier at birth.

**Measure:** sources per segment vs estimated population; new qualified sources
per week.

## 2. Source qualification — ❌ MISSING

**Job:** before a URL enters the crawl set, prove it resolves to a page that
actually lists events, and classify it.

**Today: nothing does this.** The consequence, measured from our own published
rows: The Parish crawls `brushystreet.com` (a different venue), Vulcan Gas and
Stubb's crawl site roots, "Eventbrite API" crawls developer documentation, ACL
Live crawls `acl-live.com` while the catalog says `acllive.com`. (R-083)

**Done looks like:** a URL cannot enter the crawl set until a probe confirms
event-like content; a source that stops yielding events raises an alarm rather
than quietly producing nothing.

**Measure:** % of sources yielding ≥1 event per cycle. Today's figure is
unmeasured, which is itself the finding.

---

# PART TWO — READING (getting the page)

## 3. Entry-point resolution — ❌ MISSING

**Job:** given `stubbsaustin.com`, find `stubbsaustin.com/shows`.

**Today: nothing.** We fetch whatever URL the source row holds. If it's a
homepage, we extract a homepage.

**Done looks like:** from any page on a domain, locate the events/calendar
section by link text, URL pattern, sitemap, or nav structure.

**Measure:** % of sources where the resolved entry point differs from the
stored URL — that number is the size of the R-083 problem.

## 4. Scheduling & budget — ✅ works

`ingest.yml` cron `9,29,49 * * * *`, `MAX_SOURCES: 30`, dead-man ping, Sentry,
spend capped at the console. Full cycle ≈ 3 hours over 266 sources.

**Watch:** stages 7 and 8 multiply fetches per source. The cap and cadence need
re-deriving against that — a founder decision because it is a money decision.

## 5. Acquisition (fetch) — ⚠️ works, one page only

**Today:** `worker/fetch/http_fetch.py` — conditional requests (ETag /
If-Modified-Since), 2s minimum interval per host, honest User-Agent, attempt
rows recorded for rotation. `paginate.py` follows *next-page* links.

**Defect:** pagination goes **wide, never deep**. Nothing follows an *event*
link. We can read pages 1–5 of a calendar that tells us nothing useful on any
of them.

## 6. Rendering — ⚠️ exists, wrong trigger

**Today:** `worker/fetch/render_fetch.py` is a working headless renderer.

**Defect:** `should_render()` fires **only** when the sensor flags
`boilerplate_only`. A JavaScript shell shipping normal nav and footer text
does not trip it, so we extract the shell as content. This is the ACL Live
failure: 81 rows, mostly untitled, all dateless.

**Fix direction:** render when the page yields no event links *and* no
structured data — a positive test for missing content rather than a
recogniser for one flavour of emptiness.

## 7. Listing enumeration — ❌ MISSING

**Job:** from a calendar page, produce the list of individual event URLs.

**Today: nothing.** This is the missing link between "we have the calendar" and
"we can read each event."

**Done looks like:** ordinary HTML parsing (no model call) yields N event URLs;
zero URLs is a signal to render (stage 6) or to flag the source.

## 8. Detail acquisition — ❌ MISSING

**Job:** fetch each event's own page — where sites state the facts plainly.
`acllive.com/event/2026-08-06-masego-at-8-pm` reads
`THURSDAY AUGUST 6, 2026 / 8:00 PM`.

**Today: nothing.** This is the founder's root-cause diagnosis, and the single
most consequential missing component in the system.

**Also missing: the one-hop follow off-domain.** Bastrop states a run and says
*"For specific show days and times please click the button below"*, pointing at
`bohtickets.ludus.com`. Most independent venues outsource ticketing, so the
real showtimes are routinely one hop away and we never take it.

---

# PART THREE — EXTRACTING (turning a page into facts)

## 9. Structured-data harvest — ⚠️ present and then destroyed

**Today:** `worker/segment.py:212-281` finds schema.org `Event` JSON-LD, keeps
`name`, `startDate`, `location`, `url`, **flattens them into a pipe-joined
string**, and hands that string to a model to re-extract.

**Discarded at this step:** `offers` (price), `description`, `endDate`,
`performer`, `image`, `eventStatus`, `doorTime`, `organizer`,
`location.address`, `location.geo`.

Three defects in one function: we pay for data that was free, we degrade an ISO
timestamp into a substring, and we drop most of the target schema.

**This is the highest-value fix in the codebase.** Reading the typed fields
directly is cheaper, exact, and cannot hallucinate.

**Also missing:** `.ics` / RSS / JSON feeds that sites already publish.

## 10. Model extraction — ⚠️ pointed at the wrong input

**Today:** `worker/ai_extract.py`, one call per "event block", ≤50 per page.

**Defect:** the input is a heuristically-split blob (`worker/segment.py`, 394
lines). Every ambiguity downstream — the entire `date_callback` machinery of
PR #189, eight review rounds, six variants of one defect class — exists to
repair ambiguity this split creates. **Those ambiguities do not exist on a
detail page.**

**Done looks like:** the model is the *last* resort, reading one event page,
and most sites never reach it.

## 11. Normalization — ⚠️ dates only, and ranges are broken

**Today:** `worker/datetime_normalize.py` is sound in design — it refuses to
store a timestamp unless the string evidences a full calendar date, and it
accepts every full-date form tested.

**Defects:**
- A fully-qualified range is refused outright: `'Fri, Sep 4, 2026 – Sun, Sep
  27, 2026'` → `unparseable`. Theatre runs, gallery shows, antique fairs and
  multi-day festivals are dropped wholesale.
- A year-less range is silently mis-parsed with the range end **as the year**:
  `'SEPT 04-27'` → **2027-09-04**. Both probes agree, so the anti-fabrication
  guard passes it. (R-081 — a live fabrication risk.)
- **No normalization exists at all** for price, currency, address, geo,
  timezone, or performer names.

## 12. Identity, dedupe & occurrence expansion — ⚠️ partial and biased

**Today:** `worker/triangulate.py` has real cross-source matching
(`same_event`, token/venue Jaccard, start-time tolerance).

**Defects:**
- `worker/promote.py:132` — `dups = find_possible_duplicates(...) if
  start_time else []`. A **dated** event is duplicate-checked and can be
  refused; a **dateless** event skips the check and always publishes. The
  publication path is biased toward publishing exactly what cannot be shown.
- **No production/performance distinction.** A run of twelve performances has
  no representation. Five segments are affected.
- **No recurrence model.** "Live music every Thursday 6–9pm" is one sentence
  meaning ~52 events, and nothing understands it. This is how taprooms,
  neighbourhood bars and open-mic scenes publish.

## 13. Enrichment — ⚠️ thin, and it's where search dies

**Today:** `resolve_venue_id` / `resolve_artist_ids` create placeholder rows;
`card_fields` guesses `category` from title keywords + a curated per-source
`cultural_domain` hint.

**Missing:** `venue_area` (the feed's most-used filter, 29 references),
geocoding, artist identity refs, supply-segment and size-tier tagging.

**Consequence:** a discovered event cannot be filtered by **area**, **price**
or **free** — three of the six filters the product offers.

## 14. Candidate persistence — ⚠️ works, schema too narrow

**Today:** `worker/candidate_store.py` writes the row and preserves refused
claims under `_provenance.unstored_datetime_claims`. The replay log records
every stage's input/output digests — this is what made today's diagnosis
possible.

**Defect:** `AIEventExtraction` (`worker/ai_models.py`) defines **eleven**
fields and can fill about **seven of the card's twenty-six**. No price, no
description, no category, no image, no area. What was asked for cannot be
stored.

---

# PART FOUR — PUBLISHING

## 15. Corroboration — ✅ works

`worker/triangulate.py` + `worker/authority.py`: cross-source agreement,
source-class weighting, first-party vs third-party. PR #193 made the gate and
the publish policy agree on the founder's one-source ruling.

## 16. Gate / verification — ⚠️ passes things it should not

**Today:** `worker/gating.py` (142 lines) — corroboration counts, anchor
classes, fail-closed on unknown classes.

**Defects:**
- **No date requirement.** The word `start_time` does not appear in the file.
- **No completeness requirement.** A row with a title and nothing else passes.
- **No visibility requirement** — see stage 18.

## 17. Promotion (publishing) — ⚠️ works, carries too little

**Today:** `worker/promote.py` → canonical `event`; `worker/autopromote.py` is
the only scheduled publisher, behind a founder-flipped flag. Measured: 292
examined, 292 promoted, 0 held, 0 errors.

**Defect:** it copies only what the candidate has, which is seven fields. The
`event` table has had `price_min`/`price_max` since migration 0010 and this
path has never filled one.

## 18. Serving (the read path) — ⚠️ the mismatch nobody caught

**Today:** `web/lib/promoted.ts` reads `event` and reshapes it into
`LicensedEvent` — the same 26-field card contract the licensed lane uses.
Filters: `status`, and `start_time` `gte`/`lte`.

**Defect:** PostgREST drops NULLs from a range filter, so **a dateless event is
published, gated, labelled `confirmed`, and invisible**.

**2,214 events passed every gate in this repo and no user can see one of them.**
Twenty validate checks, 1,953 tests, a golden exam, a trust gate and a
non-Claude adversarial panel — not one asks *"can a person see this row?"*
That is a missing test, not a missing opinion.

---

# PART FIVE — KEEPING IT TRUE

## 19. Freshness, change detection & retirement — ❌ MISSING

**Today:** conditional fetch exists (`not_modified` handled at
`orchestrator.py:341`), so we can tell a page changed. **Nothing acts on what
changed.**

**Missing entirely:**
- Re-extract on change and reconcile against existing rows.
- **Cancellation and postponement.** `eventStatus` is discarded at stage 9. A
  cancelled show stays on the site looking live — a trust failure worse than
  absence.
- Retirement of past events; delisting when a source drops an event.
- Any test proving an update propagates. This has never been proved.

**Done looks like:** a source edits a time, and the site reflects it on the
next cycle; a cancellation is shown as cancelled, never silently removed.

---

# PART SIX — ANALYZING

## 20. Measurement & analysis — ⚠️ instruments exist, no funnel

**Today:** the replay log records every stage; `tools/db_scope_report.py`
produces a real scope report; `prove_feed.yml` samples the live feed;
`tools/sample_dateless.py` (built today) splits the published set by date
usability. Kaizen ledger and reviewer scorecard track the *process*.

**Defect:** none of it is a **funnel**. There is no per-cycle view of: sources
attempted → pages fetched → events found → candidates created → gate pass/hold
→ promoted → **visible on the site**. Had that existed, the 2,214 would have
been obvious weeks ago at the last column.

**Missing analysis:**
- Coverage by supply segment (9 of 23 have no source at all).
- Cost per verified event — the metric the charter governs the pipeline by.
- Freshness distribution — how stale is the average listed event.
- Field completeness per source — which sites give us price, which don't.
- The 50:1 discovered-to-API ratio, currently 0 because the numerator is
  invisible.

---

# The dependency order that follows from this

Stages don't fail independently, and fixing them out of order wastes work.

1. **14 + 9** — extend the schema, stop discarding JSON-LD. *Everything
   downstream is capped by what a candidate can carry, and most of the target
   fields are already on the page.*
2. **18** — add the visibility assertion. *Without it, every later fix is
   unverifiable in the way that matters.*
3. **11** — fix range parsing and the fabricated year. *Live trust defect;
   independent of everything else.*
4. **7 + 8 + 6** — enumeration, detail pages, corrected render trigger. *The
   root cause. Also dissolves most of stage 10's difficulty.*
5. **2 + 3** — qualify sources, resolve entry points. *A crawler that navigates
   from the wrong site still ends up in the wrong place.*
6. **13** — enrichment: area, geo, category. *Search is dead without it.*
7. **12** — production/performance and recurrence. *Five segments.*
8. **19** — updates, cancellations, retirement. *Correctness over time.*
9. **20** — the funnel. *Arguably first: it is small, and it makes every other
   item measurable instead of argued.*
10. **1** — scale discovery. *Only worth doing once the engine works, or we
    multiply garbage.*

Items 1–3 are hours of work each and address more of the stated goal than any
crawler change. Item 4 is the architecture. Items 9 and 3 could be done today.



# PART 6 — THE FULL PLAN OF RECORD (decisions, acceptance criteria, budget)


## 0. Objectives (unchanged, quoted from canon)

These have not moved and this plan is measured against them, not against
itself.

**CLAUDE.md, Current mission:** *"Ship the live site behind the stealth gate:
Steps 5→10 of the critical path — schedule ingestion … extraction with
eval-harness thresholds, gate→candidate flow, admin review, implement the
ratified design direction on /tonight (feed+filters+detail), Clerk allowlist
gate, Vercel deploy, founder go/no-go."*

**Founder's standing question (2026-08-06):** *"When will this ever end and I
get my site live and full of thousands of events?"*

**Founder's root-cause diagnosis (2026-08-06), which this plan implements:**
*"your main problem is you are doing a poor job investigating each web page and
then clicking through to find the details."*

**Definition of done for THIS work:** for every site in the proving set, we
extract every event the site publishes, with date, start time, venue/location,
description, price and any specials or notes the source states — and those
events appear on the live (stealth) site, stay correct when the source
changes, and cost less than the cap.

## 1. What is already established (do not re-derive)

Measured today; citations in `docs/ops/CRAWLER_DEPTH_DIAGNOSIS_2026-08-06.md`.

| Fact | Evidence |
|---|---|
| 2,215 pipeline events published; **2,214 have no date**; 0 past; 1 future | prove-feed run 31069431885 |
| The gate is no longer the bottleneck (292/292 promoted, 0 held) | autopromote run 31067808019 |
| `datetime_normalize` accepts every full-date form tested — not the bug | local test, §3 of the diagnosis |
| `promote` copies `start_time` verbatim — not the bug | `worker/promote.py:132` |
| Extractor emits time-only claims constantly (139 refusals / 30 sources) | ingest run 31059045677 |
| Some source URLs point at homepages, a different venue's site, or API docs | R-083 |
| `SEPT 04-27` normalizes to **2027-09-04** — a fabricated year | R-081 |
| A theatre run is not an event; showtimes sit on a ticketing domain | Bastrop / Ludus, founder screenshots |

**The single architectural cause:** ingestion fetches ONE url and extracts from
that blob. It never finds a site's events section, never opens an individual
event, never follows a ticketing link.

## 2. Constraints

1. **Hard budget: $100 total model spend.** Report at $10, $25, $40, $50,
   $75, $90. Spend is computed from actual token usage returned by each API
   call × published per-token prices — real usage, estimated dollars; there is
   no console API to read true billed spend, and this document will not
   pretend otherwise.
2. **No commits outside the testing ground.** Branch `claude/crawler-lab`,
   directory `lab/`. Nothing merged. No change to `worker/`, `web/`, `ai/`,
   `tools/` gates, or any pipeline workflow.
3. **This sandbox has no outbound network** (proxy refuses all external hosts).
   Every real-site test therefore runs from GitHub Actions.
4. **The live site is available for proof** — founder-granted, site is behind
   the stealth gate.
5. **Cheapest capable tier** (CLAUDE.md cost discipline): a stage may not use a
   stronger model than the bar requires, and quality gates never relax to save
   money.

## 3. The proving set — 62 sites

Two representatives of each of the 23 ratified supply segments
(`docs/strategy/ONE_LIVE_SUPPLY_SEGMENTS_v1.md`) plus the 16 already agreed
with the founder. Sites marked ° are in the committed catalog; sites marked ▲
are not and are added here because the catalog has no representative — which
is itself a finding.

**The 16 agreed (the original ten + six named by the founder)**

| # | Site | Why in the set |
|---|---|---|
| 1 | ACL Live at The Moody Theater ° | JS-rendered; catalog hostname disagrees with production |
| 2 | Moody Amphitheater at Waterloo Park ° | JS-rendered listing |
| 3 | Bastrop Opera House ° | run vs performances; showtimes on Ludus |
| 4 | Palmer Events Center ° | civic venue, mixed event types |
| 5 | Visit Austin Festivals Calendar ° | aggregator, not a venue |
| 6 | The Wimberley Players ° | small hand-built theatre site |
| 7 | Giddings Area Chamber ° | chamber events list |
| 8 | City of San Marcos Calendar ° | government calendar software |
| 9 | Science Mill ° | off-site events at other venues |
| 10 | Austin Food & Wine Festival ° | multi-day festival schedule |
| 11 | The Saxon Pub ° | 11 dateless rows live; early/late shows |
| 12 | Antone's Nightclub ° | 6 dateless rows live; site root |
| 13 | Becker Vineyards ° | winery, ticketed tastings + concerts |
| 14 | William Chris Vineyards ° | winery, likely WordPress Events Calendar |
| 15 | Jester King Brewery ° | destination brewery, mixed event types |
| 16 | Treaty Oak Distilling ° | distillery-as-venue |

**Two per segment (46)**

| Segment | Rep A | Rep B |
|---|---|---|
| 1 Live music venues & clubs | Mohawk Austin ° | The White Horse ° |
| 2 Bars & lounges with programming | Elephant Room ° | Cheer Up Charlies ° |
| 3 Breweries/wineries/distilleries | Real Ale Brewing ° | Still Austin Whiskey ° |
| 4 Restaurants & cafés with events | Redbud Cafe ° | Altdorf Biergarten ° |
| 5 Theaters & performing arts centers | ZACH Theatre ° | The Long Center ° |
| 6 Comedy clubs & rooms | Cap City Comedy ° | The Velveeta Room ° |
| 7 Nightlife: dance clubs & DJ rooms | Kingdom Nightclub ° | The Concourse Project ° |
| 8 Galleries & independent art spaces | The Contemporary Austin ° | UMLAUF Sculpture Garden ° |
| 9 Museums & cultural institutions | Blanton Museum ° | Bullock Texas State History Museum ° |
| 10 Independent cinemas | Austin Film Society ° | Alamo Drafthouse Austin ° |
| 11 Nontraditional & multi-use spaces | BookPeople ° | Waterloo Greenway ° |
| 12 Festivals | Fusebox Festival ° | Texas Book Festival ° |
| 13 Independent promoters & presenters | KUTX Presents ° | Golden Hornet ° |
| 14 Community orgs & nonprofits | HAAM ° | Austin History Center Assoc ° |
| 15 Recurring-scene organizers | Austin Poetry Slam ▲ | Kick Butt Coffee open mic ▲ |
| 16 Social-dance & movement communities | Austin Swing Syndicate ▲ | Esquina Tango ▲ |
| 17 Markets, fairs & pop-ups | SFC Farmers' Market ° | Maker Faire Austin ° |
| 18 Bands & musical acts | Black Pumas ▲ | Spoon ▲ |
| 19 Solo musicians & singer-songwriters | Gary Clark Jr. ▲ | Shakey Graves ▲ |
| 20 DJs & electronic artists | (2 via Resident Advisor artist pages) ▲ | ▲ |
| 21 Comedians & spoken-word | (2 via official tour pages) ▲ | ▲ |
| 22 Theater & dance companies | Ballet Austin ° | Tapestry Dance Company ° |
| 23 Visual artists, makers & craft creators | (2 via official sites) ▲ | ▲ |

**Finding before we start:** segments 15, 16, 18–21 and 23 have **no catalog
representative**. Nine of the twenty-three ratified segments are unrepresented
in the source catalog. That is a supply gap independent of extraction, and it
belongs in the record whatever this engine achieves.

## 3a. THE TARGET SCHEMA — what "100%" actually means

**This section, not the prose elsewhere, defines completeness.** Recall cannot
be scored against an intention; it is scored against this list. Derived from
three real consumers, not from imagination:

* **the card** — `web/lib/licensed.ts:48` `LicensedEvent`, the single shape
  BOTH lanes render into (26 fields);
* **search/filters** — `web/app/(public)/tonight/FeedApp.tsx` filters on
  `area` (29 refs), `free`, `price`, `when`, `category`, `subsegment`;
* **analysis** — segment/tier rollups, cost-per-verified-event, the 50:1 KPI,
  freshness and coverage reporting.

### REQUIRED — group 1. A row missing any of these is incomplete.

| Field | Consumer | Structured source (tier 0) | Today |
|---|---|---|---|
| `title` | card, search | `name` | ✅ |
| `start_time` | card, `when` filter | `startDate` | ✅ |
| `end_time` | card | `endDate` | ⚠️ dropped by segment.py |
| `venue_name` | card, search | `location.name` | ✅ |
| `venue_city` | card | `location.address.addressLocality` | ✅ |
| `venue_address` | card, geocode→`area` | `location.address.streetAddress` | ❌ |
| `venue_area` | **`area` filter** | derived from address/lat-lng | ❌ |
| `category` | **`category` filter** | `@type` / site section | ❌ guessed downstream |
| `subsegment` | **`subsegment` filter** | `@type` / genre / site section | ❌ guessed downstream |
| `price_min`, `price_max`, `currency` | **`price` filter**, card | `offers.price`, `offers.priceCurrency`, `offers.lowPrice/highPrice` | ❌ |
| `is_free` | **`free` filter**, card | `offers.price == 0` / "free" in text | ❌ |
| `ticket_url` | card CTA | `offers.url` | ⚠️ via ticket_link |
| `description` | card detail, search text | `description` | ❌ not extracted, and NOT in the card contract |
| `image_url` | card | `image` | ❌ |
| `source_url` (the event's OWN page) | trust display | detail page URL | ⚠️ currently the source's base URL |

### REQUIRED — group 2 (founder-ratified 2026-08-06: *"Tier b is required"*)

Formerly "required where the source states it". **Now required at the same
standard as group 1**, scored at the same threshold, and a source that publishes
one of these and loses it is a failure of the run.

| Field | Structured source (tier 0) | Consumer |
|---|---|---|
| `performer` / `artist_names` | `performer` | card, search, Spark Line binding |
| `door_time` | `doorTime` | card |
| `age_restriction` | `typicalAgeRange` / page text | card, filter |
| `on_sale_status` | `offers.availability` | card CTA |
| `event_status` — cancelled / postponed / rescheduled | `eventStatus` | **trust** — a cancelled show must never read as live |
| `organizer` | `organizer.name` | analysis, claim routing |
| `venue_lat` / `venue_lng` | `location.geo` | map, `area` derivation |
| `venue_url`, `venue_phone` | `location.url` / `telephone` | card detail |
| `series_name` (the run a performance belongs to) | `superEvent.name` | grouping |
| `specials` — the free-text offer ("$5 tacos", "2-for-1 til 7") | page text | card, the owner-facing promise |

The one thing this directive does not change, because it is the trust
invariant: a field is never *invented*. "Required" means we must capture it
wherever the source publishes it — not that we manufacture a value when the
source is silent. A silent source yields an honest null; a stated value that we
drop is a defect.

### ANALYSIS — required for reporting, not rendered on the card.

`supply_segment` (1–23) · `size_tier` · `extraction_tier` (0–5, which method
won) · `recurrence_rule` + `is_expanded_occurrence` · `first_seen_at`,
`last_verified_at` · `capacity` where stated.

### The completeness metric

For each site: **field-level recall = fields correctly extracted ÷ fields the
source actually publishes**, judged per field against the hand-built fixture,
NOT against this list — a site that states no price is not penalised for a
missing price, and a site that states one and loses it IS.

Acceptance (replaces the looser §7 wording for fields):

| | Threshold |
|---|---|
| Required group 1 — field recall where the source states the field | **≥ 98%** |
| Required group 2 — field recall where the source states the field | **≥ 98%** (raised from 90% by founder directive 2026-08-06) |
| Analysis fields populated | 100% (they are computed, not extracted) |
| Any field asserted that the source does NOT state | **0 — fails the run** |
| Events filterable on `area`, `price`, `free` after ingestion | ≥ 95% |
| Cancelled/postponed events correctly marked, never shown as live | **100%** |

### Why this section exists

`worker/ai_models.py` today defines eleven fields and can fill about seven of
the card's twenty-six. **A discovered event cannot be filtered by area, price
or free — three of the six filters the feed offers — because nothing extracts
them.** Fixing dates alone would still leave every crawled event priceless,
image-less and half-unfilterable, sitting next to Ticketmaster rows that have
all of it. Extending the schema is a precondition of this project, not a
follow-up to it.

## 4. Ground truth — the thing that makes "proof" mean anything

For each site, before any extraction runs, a human-readable fixture is written
by hand from the rendered page: every event the site publishes, with title,
date, start time, location, price and notes. Stored as
`lab/truth/<site_id>.json`, with the date the page was read and the URL read.

Extraction is then scored against that fixture: **precision** (of what we
extracted, how much is right), **recall** (of what the site published, how much
we got), and **field-level accuracy** per field. Every miss and every wrong
value is printed, never summarized away.

**Page snapshots are cached** (`lab/snapshots/<site_id>/`) so scoring is
deterministic and re-runnable without re-hitting anyone's server. Live fetches
happen once per site per change, not once per test run.

## 5. Architecture — simplest thing first, escalate only on measured failure

An ordered ladder. Each site is tried at the lowest tier that works; a site
only reaches a tier because the tier below it failed against ground truth.

| Tier | Method | Model cost |
|---|---|---|
| **0** | **schema.org JSON-LD / microdata** on the listing or detail page | **$0** |
| **1** | Machine feeds the site already publishes — `.ics`, RSS/Atom, a public JSON endpoint | **$0** |
| **2** | HTML link enumeration → fetch each event's detail page → deterministic date/price parse | **$0** |
| **3** | Model extraction on a **single event detail page** (not a blob) | Haiku 4.5 |
| **4** | Browser render, then re-enter at tier 0 | render time, then as above |
| **5** | Follow the ticketing platform link (Ludus, Eventbrite, Tixr, See Tickets…) | as above |

The order is the whole point. Tier 0 is exact, free, and cannot hallucinate;
tiers 3+ exist only for sites that publish nothing structured. **Step one of
execution is a $0 census** measuring how many of the 62 sites are served by
tiers 0–2, because that number decides the entire cost profile.

## 6. Decisions — three options each, with a recommendation

### D1. Where the engine lives while being proved

| | Option | Consequence |
|---|---|---|
| A | Standalone in `lab/`, importing nothing from `worker/` | clean, disposable, risks proving something that can't be adopted |
| B | Standalone in `lab/`, **reusing** `worker/fetch`, `datetime_normalize` | proves against the real components; adoption path visible |
| C | Modify `worker/` behind a feature flag | fastest to production, violates the testing-ground constraint |

**Recommendation: B.**
*What* — lab-only orchestration; reuse the existing fetch, render and datetime
components unchanged.
*Why* — a proof built on different components proves nothing about the
pipeline; a proof that edits the pipeline breaks the founder's constraint.
*Why it matters* — the failure mode this project keeps hitting is code that
passes its own tests and fails on real sites. Reusing the real fetch path means
the lab meets the same reality production does.
*Why that matters* — adoption becomes a small, reviewable diff instead of a
rewrite, so the gap between "proved" and "shipped" is days not weeks.
*Expected outcome* — every lab result is a claim about production behaviour,
and defects found in `worker/fetch` during the lab are real defects.

### D2. Structured data vs model extraction

| | Option | Consequence |
|---|---|---|
| A | Model-first (today's design) | uniform, expensive, hallucination-exposed |
| B | **Structured-first, model only as fallback** | exact where available, cheap, uneven coverage |
| C | Model-only but on detail pages | better than today, still pays per event forever |

**Recommendation: B.**
*What* — try JSON-LD/microdata, then site feeds, then deterministic HTML, and
only then a model.
*Why* — a `schema.org/Event` block already contains startDate, endDate,
location, offers and description as typed fields. Parsing it is free, exact,
and structurally incapable of inventing a date.
*Why it matters* — it removes the fabrication risk (R-081) for every site that
publishes it, and collapses cost to near zero for that share.
*Why that matters* — cost per verified event is the metric the charter governs
the pipeline by; a free tier that covers a large share changes what we can
afford to crawl, and therefore how many events reach the site.
*Expected outcome* — the census in §5 gives the exact share; my prior is that
most ticketed venues publish it and small hand-built sites do not.

### D3. When to render with a browser

| | Option | Consequence |
|---|---|---|
| A | Never | cheapest; ACL Live and similar stay broken |
| B | Always | correct everywhere; slowest and heaviest |
| C | **Conditional on a positive test for missing content** | fast common path, correct hard path |

**Recommendation: C, with a corrected trigger.**
*What* — render when the fetched HTML yields no candidate event links and no
structured data, rather than only when the page looks like bare nav chrome.
*Why* — today's trigger (`boilerplate_only`) misses JS shells that carry normal
nav and footer text, which is exactly the ACL Live failure.
*Why it matters* — it converts a whole class of silently-empty sites into
working ones without paying browser cost on the sites that don't need it.
*Why that matters* — rendering everything would multiply run time per source,
and throughput is already the constraint at 30 sources per run.
*Expected outcome* — measured: how many of the 62 need rendering, and what it
costs in seconds per site.

### D4. What a row in `event` represents

| | Option | Consequence |
|---|---|---|
| A | One row per production ("Newsies, Sep 4–27") | wrong for a tonight feed |
| B | **One row per performance** | correct for the product; more rows |
| C | Production row + child performance rows | most faithful; schema change |

**Recommendation: B for this proof, C flagged as the likely end state.**
*What* — expand a run into its individual performances; each row is one thing a
person can attend.
*Why* — `/tonight` answers "what can I do tonight," which is a performance-level
question. A run cannot answer it.
*Why it matters* — Bastrop's twelve showtimes are twelve answers, not one.
*Why that matters* — this is the difference between a feed that looks populated
and a feed that is useful; the founder's objective is the latter.
*Expected outcome* — event counts rise materially for theatre, comedy and
performing-arts sources. C requires a schema decision and is out of scope here.

### D5. Recurring events ("live music every Thursday, 6–9pm")

| | Option | Consequence |
|---|---|---|
| A | Ignore | loses most taproom programming |
| B | **Expand to a bounded horizon (90 days) with the rule recorded** | usable now, auditable, may over-assert |
| C | Store the rule, expand at read time | most correct, schema + API change |

**Recommendation: B, with the source sentence stored verbatim as provenance.**
*What* — expand to a bounded horizon and keep the originating sentence on every
generated row.
*Why* — the alternative is discarding real programming, or a schema change
this proof cannot justify yet.
*Why it matters* — producers and neighbourhood bars publish this way; it is
the difference between covering the segment and not.
*Why that matters* — segment 3 is canon with a three-sided revenue model, so
under-covering it undercuts the product thesis, not just the count.
*Expected outcome* — measurable recall gain on taprooms; a stated over-assertion
risk (a cancelled Thursday) that the update pass in §9 must catch.
**Trust note:** an expanded occurrence is an inference, not a source statement.
It must carry that distinction into the candidate's provenance, and whether it
may reach the public feed at `confirmed` is a founder decision, not mine.

### D6. Following ticketing platforms

| | Option | Consequence |
|---|---|---|
| A | Never leave the venue domain | Bastrop-class sites unsolvable |
| B | **Follow when the venue defers, generically** | solves the class; off-domain fetches |
| C | Per-platform adapters (Ludus, Tixr, Eventbrite…) | most accurate; N adapters to maintain |

**Recommendation: B first, measure, then add adapters only where B fails.**
*What* — when a detail page states a range and links out for showtimes, follow
one hop and extract there.
*Why* — the data is on the other side of that link; nothing on the venue page
can substitute.
*Why it matters* — it is the only route to real showtimes for theatres and
small venues that outsource ticketing, which is most of them.
*Why that matters* — those are exactly the independent operators the product
exists to serve; failing them fails the thesis, not just the coverage.
*Expected outcome* — measured per site; adapters justified only by a recorded
failure of the generic path.

### D7. Model tier for tier-3 extraction

| | Option | Cost profile |
|---|---|---|
| A | **Haiku 4.5** | cheapest; adequate for reading one explicit date off one page |
| B | Sonnet 5 | ~10× Haiku; unnecessary for a structured read |
| C | Opus 5 | reserved for reasoning, not extraction |

**Recommendation: A, with a measured escalation rule.**
*What* — Haiku for detail-page extraction; escalate a specific site to Sonnet
only after Haiku misses ground truth on it, and record the reason.
*Why* — a detail page states the date in plain text; this is the easiest
extraction task in the system.
*Why it matters* — it is the difference between roughly $8 and roughly $80 for
the same proof.
*Why that matters* — the founder capped this at $100 after prior spend produced
nothing usable; coming in far under is part of the deliverable.
*Expected outcome* — per-site accuracy table showing where Haiku suffices and
where it doesn't, rather than an assumption in either direction.

### D8. Ground truth

| | Option | Consequence |
|---|---|---|
| A | Trust the site (extract twice, compare) | circular; proves consistency not correctness |
| B | **Hand-built fixtures per site** | slow to author; the only real proof |
| C | Sample-audit 10% by hand | cheaper; hides tail failures |

**Recommendation: B.**
*What* — write the fixture by hand from the rendered page before extraction runs.
*Why* — every prior claim in this project failed because nothing independent
said what the right answer was.
*Why it matters* — precision and recall are meaningless without a denominator
that a human established.
*Why that matters* — the founder's stated objection is that progress has been
unmeasurable. This is the measurement.
*Expected outcome* — a fixture set that outlives the lab and becomes the
regression suite for the real pipeline.

### D9. Detecting updates

| | Option | Consequence |
|---|---|---|
| A | Full re-extract every run | simple, costs full price every cycle |
| B | **ETag / Last-Modified, then content hash, then re-extract on change** | cheap steady state |
| C | Model-diff the page | expensive and unnecessary |

**Recommendation: B.**
*What* — conditional fetch first; hash the normalized content; only changed
pages re-extract.
*Why* — most calendar pages are unchanged between runs.
*Why it matters* — it makes a large corpus affordable at a short cadence, which
is what freshness requires.
*Why that matters* — a stale event is a trust failure, not a coverage failure;
cheap re-checks are how a listing stays true.
*Expected outcome* — measured: what fraction of the 62 are unchanged run to
run, and the resulting steady-state cost per cycle.

### D10. Per-site adapters

| | Option | Consequence |
|---|---|---|
| A | **None — one generic pipeline** | generalizes; may under-serve odd sites |
| B | Per-platform adapters (Squarespace, Tribe, Shopify…) | strong coverage; bounded maintenance |
| C | Per-site adapters | best accuracy; unmaintainable at scale |

**Recommendation: A, and treat any need for B as a measured finding.**
*What* — one path for all sites; count how many fail it.
*Why* — the founder's requirement is generalization to sites we haven't seen.
*Why it matters* — a per-site engine cannot serve a corpus of hundreds.
*Why that matters* — the product's reach is the corpus size; an engine that
needs bespoke work per venue caps the business at whatever we hand-build.
*Expected outcome* — a number: how many of 62 the generic path handles, and a
named list of what the exceptions have in common.

## 7. Acceptance criteria (numeric, set before running)

The proof succeeds only if all of these hold on the 62-site set:

| Metric | Threshold |
|---|---|
| Sites yielding ≥1 correctly dated event | **≥ 90%** (56/62) |
| Event recall vs hand-built ground truth | **≥ 95%** median per site |
| Date correctness on extracted events | **100%** — a wrong date is a trust failure, not an accuracy point |
| Start-time correctness where the source states one | ≥ 95% |
| Venue/location correctness | ≥ 95% |
| Price captured where the source states one | ≥ 90% |
| Fabricated fields (any value not in the source) | **0** |
| Total model spend | **< $100**, target < $25 |
| Update pass detects a changed/cancelled/added event | 100% on the seeded test |

A single fabricated date fails the whole run regardless of the other numbers.

## 8. Failure taxonomy (every failure is classified, never "it didn't work")

`NO_NETWORK` · `BLOCKED_403` · `ROBOTS_DISALLOW` · `NEEDS_RENDER` ·
`NO_EVENT_LINKS` · `DETAIL_PAGE_MISSING_DATE` · `RANGE_ONLY` ·
`TICKETING_OFFSITE` · `RECURRING_RULE` · `EXTRACTION_WRONG` ·
`GROUND_TRUTH_AMBIGUOUS`. Counts per class drive the next iteration; a class
with one member is not worth engineering for.

## 9. Proving reading → extraction → ingestion → updates

1. **Reading** — census of tiers 0–4 across 62 sites, with byte counts, final
   URLs after redirect, and render need. Cost: $0.
2. **Extraction** — scored against hand-built fixtures, per-field.
3. **Ingestion** — the extracted events go through the **real** candidate →
   gate → promote path into the live database, and are then read back from the
   public feed. Proof is the event visible on the stealth site, not a log line.
4. **Updates** — seed three changes on cached snapshots (an event moved, one
   cancelled, one added), re-run, and show the database reflects all three.
   This is the test the current pipeline has never had.

## 10. Politeness, legality, safety

Respect `robots.txt`; identify honestly in the User-Agent with a contact;
minimum interval between requests to one host (existing default 2s); conditional
requests so we don't re-download unchanged pages; hard per-site page cap; no
login-walled scraping (the catalog already marks `login_scraping` disallowed
per source); cache snapshots so repeat testing costs the site nothing.

## 11. Budget model and checkpoints

Every API call's returned `usage` is logged to `lab/spend.jsonl` with model,
input tokens, output tokens and computed cost. A running total prints on every
run. Checkpoints reported to the founder at $10, $25, $40, $50, $75, $90.
Hard stop at $100 — the runner refuses to make another call.

Estimate to beat: tier-3 extraction at ~3k input / ~300 output tokens per
event, Haiku pricing, ~1,900 events ⇒ **~$8–10**, assuming the tier-0/1/2
census covers none of them. Every site the census covers reduces this.

## 12. Rollback and disposal

Nothing to roll back: the lab writes to `lab/` only. The ingestion proof (§9.3)
writes real rows to the production database; those rows are tagged and a
listed, tested delete path removes exactly them. If the proof fails the §7
thresholds, the recommendation is "do not adopt", and the record says why.

## 13. Deliverables

1. `lab/` engine + fixtures + snapshots.
2. A results table: 62 sites × tier used × precision/recall/field accuracy.
3. The census: how many sites each tier serves.
4. Spend ledger with the final figure.
5. Proof of the four stages in §9, including live-site screenshots or feed reads.
6. A record documenting what to adopt into `worker/`, and what to discard.
7. A paste-ready prompt for the session that does the adoption.

## 13a. Red-team result and the conditions it imposes

The non-Claude panel (adversarial-review, run 31074395263, head a280d785)
returned **APPROVE on all four seats**: openai/attacker-smuggle,
openai/absence-only, gemini/dataflow-taint, gemini/spec-vs-contract.

**Read that verdict narrowly.** The panel reviews DIFFS for defects that could
reach a user, and this diff is documentation. Both openai seats said so in as
many words — *"no executable crawler or posting loop"*, *"no extraction or
publish path is added in this diff"*. An APPROVE here means "this text cannot
hurt anyone," NOT "this architecture is sound." The plan has not been attacked
on its merits by an independent model; `lab/EXTERNAL_AI_BRIEF.md` exists for
that.

Two ARMING conditions were raised, both independently by more than one seat.
They are BINDING on the build session:

**AC-1 — before the live-database ingestion proof (§9.3) may run.** The
tag-and-delete path must be enforced in code, not merely intended, and proof
rows must be structurally incapable of masquerading as ordinary public events.
Panel wording: *"the future implementation needs an actual enforced tag/delete
path and must ensure proof rows cannot masquerade as ordinary public events."*

**AC-2 — before recurring-event expansion (D5) may be implemented.** The
confidence and provenance treatment for an inferred occurrence must be settled
first. Panel wording: *"recurring-event expansion is an inference, not a
directly stated source fact … Clear confidence/provenance treatment before
recurring expansion is implemented/adopted."* Whether an inferred occurrence
may publish at `confirmed` remains founder-crucial.

## 14. Open risks I am not hiding

- **Ground truth is hand-built by the same agent that writes the extractor.**
  Mitigation: fixtures are authored from the rendered page before the
  extractor is written, and every disagreement is printed for the founder to
  spot-check. This is a real weakness, not a solved one.
- **62 hand-built fixtures is a lot of authoring.** If it proves too slow, the
  honest move is to reduce the set and say so, not to weaken the fixtures.
- **Nine of 23 segments have no catalog representative** (§3). The engine can
  be proved on them; the supply gap remains.
- **Recurring expansion asserts occurrences the source did not individually
  state** (D5). Whether that may publish at `confirmed` is founder-crucial.
- **The live-site ingestion proof writes to production.** Tagged and reversible,
  but it is production.
