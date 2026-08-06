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
  both the licensed lane and the crawler lane render into. **30 fields.**
* **search** — the feed filters on `area`, `free`, `price`, `when`,
  `category`, `subsegment`.
* **analysis** — segment rollups, cost per verified event, freshness.

**The current extraction schema fills 7 of the card's 30 fields.** It cannot
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

## 4b. CRITICAL — HOW SOURCES ARE FOUND, AND WHY THAT IS THE DEEPER FAILURE

**Read this before the extraction work. Extraction can only be as good as the
list of sites it is pointed at, and the mechanism that produces that list is
the least-built part of the system.**

### What exists today

Exactly one automated discovery mechanism: `tools/scan_new_sources.py`. Its
method, quoted from its own docstring:

> "run a category × term query pack through Google's Programmable Search JSON
> API … collect result domains, and DIFF them against the committed source
> catalog. Output: NEW domains only … CANDIDATES for human curation"

The entire query pack is **20 hardcoded phrases**, prefixed with one city:

```
live music venues · bars with live music · music venue calendar · comedy club
theater performances calendar · art gallery openings · museum events calendar
dance hall · brewery live music events · winery events · coffee shop open mic
bookstore author events · farmers market events · community center events
calendar · church concert series · university events calendar · poetry reading
open mic · trivia night bars · festival calendar · record store in-store
performance
```

Plus an Eventbrite organiser harvest (`tools/search_discover_eventbrite.py`).
That is the whole of "discovery".

### Why this is critical, defect by defect

**D-1. It has never run.** The workflow that would schedule it
(`source-scan.yml`) sits on an unmerged pull request. The Google CSE
credential returns `403 PERMISSION_DENIED` at project level. So the only
automated discovery lane is both unmerged and credential-blocked. **Every
source in production got there by hand or by an Eventbrite harvest.**

**D-2. Twenty generic queries is not a search strategy.** 20 queries × 10
results = at most 210 domains, most of which are platforms and aggregators
that get filtered out. That is the entire funnel, for a 23-segment taxonomy
across a metro area plus the surrounding Hill Country.

**D-3. The query pack does not ask for most of the taxonomy.** There is no
query for social-dance communities, DJs and electronic artists, comedians,
visual artists, recurring-scene organisers, bands, or solo musicians. **Nine of
the twenty-three ratified segments have no representative in the catalog — and
the reason is simply that nothing ever searched for them.** The gap is not bad
luck; it is the query pack.

**D-4. One geography.** Queries are prefixed `--city "Austin"`. The catalog
already contains Fredericksburg, Round Top, Blanco, Luling, Giddings, Marble
Falls, Bertram, Schulenburg. Nothing searches for those towns, so the corpus
can only grow where it already looked.

**D-5. One method, and the cheapest one.** Search-index only. Nothing:
- expands the link graph from venues already known (a venue's "friends",
  "presented by", "also playing at" links);
- mines the aggregators we already crawl (Do512, the Chronicle, Visit Austin)
  for the venue names inside their listings — those pages are a venue
  directory we already fetch and throw away;
- mines chambers of commerce, arts councils, tourism boards, city cultural
  offices — the places small operators are actually indexed;
- reverse-looks-up from performers to the venues they play;
- enumerates other customers of a ticketing platform we already know
  (Ludus, Tixr, Prekindle, See Tickets), which is how you find the next fifty
  theatres at once;
- reads sitemaps.

**D-6. Domain-level diffing hides platform-hosted venues.** Candidates are
deduped by domain against the catalog. A new venue whose events live on a
platform domain already in the catalog is invisible to it.

**D-7. Human curation is the throughput ceiling.** Output is "CANDIDATES for
human curation". The founder's stated intent was *"constantly identifying new
sources"*; a mechanism gated on manual review cannot do that.

**D-8. No qualification, so a candidate is never checked.** Nothing verifies
that a discovered domain actually publishes dated events before it becomes a
source. This is why production crawls a different venue's website for The
Parish, a homepage for Stubb's, and Eventbrite's API *documentation* page.

**D-9. No feedback loop.** Nothing measures which queries produced sources that
went on to yield real events, so the pack cannot improve. It is a fixed list
written once.

### The evidence that this is the binding constraint

When this brief needed two representatives for each of seven unrepresented
segments, the system offered **nothing** — no discovery output, no candidate
queue, no ranked list. The stopgap was an agent typing site names from memory
into `lab/verify_urls.py` and checking whether they existed. On the first pass
**5 of 14 slots verified**; the rest were 404s, bot-blocks, a domain that does
not resolve at all, and pages with no dated content.

**`lab/verify_urls.py` is a VERIFIER, not a discovery mechanism. Do not mistake
it for one.** It checks hypotheses a human or model already had. It cannot find
a venue nobody thought of, which is precisely what discovery must do.

### What you are being asked to fix here

Sourcing is a first-class component of this build, not a prerequisite someone
else handles:

1. A discovery mechanism that **generates** candidates rather than checking
   guesses — multi-method (link graph, aggregator mining, directory mining,
   ticketing-platform enumeration, sitemaps, search), not search-only.
2. Query and method coverage for **all 23 segments and every town in the
   market**, not one city and 20 phrases.
3. An automatic **qualification** step: a candidate is not a source until
   something has confirmed the URL resolves to a page that lists dated events
   (this also fixes the wrong-site and homepage rows already in production).
4. A **feedback loop**: measure which discovery methods and which queries
   produce sources that actually yield published events, and let that steer the
   next sweep.
5. Coverage reporting **by segment and by town**, so a gap like "nine segments
   have nothing" is visible the day it appears instead of being discovered
   months later by inspection.

Treat a design that leaves discovery as "run 20 queries and have a human read
the output" as failing this brief.

## 4c. WORKING RULE — SOURCE OVER MEMORY (founder directive)

**Never assert a fact you have not just read from the source.** Not from
recall, not from an earlier turn's summary, not from what a docstring claims
the code does. Read the code, the run log, or the page — then speak.

This is not a style preference. It is the measured lesson of the session that
produced this brief.

### The evidence

Every factual error in that session came from memory. Every claim taken from
source survived scrutiny.

| Asserted from memory | What the source actually said |
|---|---|
| "a third of sources publish bare times" explains 2,214 dateless events | It explains a fraction. The dominant causes were catalog rows pointing at non-event pages, and JS shells read as content. |
| The card needs roughly the fields we extract | `web/lib/licensed.ts:48` defines **30**; `worker/ai_models.py` fills **7** |
| "2 affected sources" | **95** — the sample had been sorted by name and only its first page read |
| A set of plausible venue URLs | 5 of 14 verified; one domain did not resolve at all — a fabricated fact inside a document |
| "The plan is being red-teamed" | The job had died in `validate`; no reviewer seat ever ran |
| Three estimates of recoverable events | Three different wrong models of the problem |

Read from source, and correct every time: `datetime_normalize`'s actual parse
behaviour, `promote.py:132`, `segment.py:252`, `gating.py` containing **zero**
occurrences of `start_time`, the card contract, the 20-phrase query pack.

### What it costs, honestly

- **Tokens:** reading the exact lines costs 1-5k. A wrong claim costs a full
  correction round plus rework. Reading first is roughly an order of magnitude
  cheaper.
- **Time:** seconds slower per answer; hours faster per project.
- **The real penalty:** external facts. A dev sandbox with no outbound network
  turns "check this page" into a CI round trip of 2-10 minutes. That friction
  is exactly why URLs got typed from memory instead of checked — **and it was
  still the wrong trade.** Build the verification path early and use it.

### How to apply it

1. **Cite or mark.** Every factual claim carries `file:line`, a run id, or a
   URL you just fetched. A claim you cannot cite is written `UNVERIFIED`, with
   the reason.
2. **Re-read, don't recall.** Never quote a number from earlier in your own
   output. Recompute it.
3. **Separate fact from judgment.** The rule forbids unsourced *assertions*,
   not reasoning. Recommendations and designs are welcome — label them as
   judgment so they cannot be mistaken for measurements.
4. **Proof of absence is a read too.** "There is no date check in the gate" is
   a claim; `grep -c start_time worker/gating.py` returning `0` is the
   evidence.
5. **Verify your own output.** Hand-assembling this document silently dropped
   two appendices. The assembler now fails loudly when a section is missing.
   Apply the same to every artifact you produce.
6. **A docstring is not the code.** It is a claim about the code, possibly
   wrong, possibly stale. Read the body.

### Why this matters more here than on most projects

The product's promise is that a date on the site was stated by its source. An
engineer who works from memory will eventually write a date nobody published.
The discipline that makes this brief trustworthy is the same discipline the
extractor must embody: **capture what the source says, refuse what it does
not, and never fill a gap from your own head.**

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

CRITICAL, AND SEPARATE FROM EXTRACTION: how sources are found. The only
automated discovery mechanism is 20 hardcoded search phrases prefixed with one
city, sent to a Google CSE credential that currently returns 403, in a workflow
that has never merged. It has no query for social dance, DJs, comedians, visual
artists, open-mic organisers, bands or solo musicians — which is exactly why
nine of the twenty-three supply segments have no source at all. It searches one
city while the catalog spans a dozen towns. It never checks that a discovered
domain actually lists events, which is why production crawls a different
venue's website, two homepages and an API documentation page. See section 4b —
sourcing is part of this build, not someone else's prerequisite.

FIX THESE FIRST — they are hours of work each and they block everything else:
1. worker/ai_models.py fills only 7 of the 30 fields the card contract
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
- NEVER WORK FROM MEMORY — read the source (section 4c, founder directive with
  measured backing). Every factual claim carries a file:line, a run id, or a
  URL you just fetched; anything you cannot cite is marked UNVERIFIED. Never
  quote a number from your own earlier output — recompute it. A docstring is a
  claim about the code, not the code.
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
