# Extraction Engine v2 — Plan of Record

**Status: PLAN ONLY. Nothing in this document has been built.**
Written 2026-08-06 for adversarial red-team review before any code is written.
Everything lives under `lab/` on branch `claude/crawler-lab`. No product file,
no gate, no workflow the pipeline depends on, is touched by this plan.

---

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

### Tier A — REQUIRED. A row missing any of these is incomplete.

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

### Tier B — REQUIRED WHERE THE SOURCE STATES IT. Absence must be provable.

`performer` / `artist_names` (`performer`) · `door_time` (`doorTime`) ·
`age_restriction` (`typicalAgeRange` / page text) · `on_sale_status`
(`offers.availability`) · `event_status` — cancelled/postponed/rescheduled
(`eventStatus`) · `organizer` (`organizer.name`) · `venue_lat`/`venue_lng`
(`location.geo`) · `venue_url`, `venue_phone` · `series_name` for a run ·
`specials` — the free-text offer a venue states ("$5 tacos", "2-for-1 til 7").

### Tier C — ANALYSIS. Not on the card; required for reporting.

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
| Tier A field recall, where the source states the field | **≥ 98%** |
| Tier B field recall, where the source states the field | ≥ 90% |
| Any field asserted that the source does NOT state | **0 — fails the run** |
| Events filterable on `area`, `price`, `free` after ingestion | ≥ 95% |

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
