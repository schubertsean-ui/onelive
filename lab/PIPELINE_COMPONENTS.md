# The pipeline, broken into its component parts

**2026-08-06.** Founder direction: *"I want this to be broken down into the
component parts of the process from searching to publishing to analyzing."*

Every "today" claim below was read out of the code or measured from a run, not
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
