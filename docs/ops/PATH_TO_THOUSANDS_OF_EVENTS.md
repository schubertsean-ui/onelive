# The path to thousands of events on the live site

Written 2026-08-06 at founder direction: *"Create a detailed list of what
remains to have thousands of events listed on the live site."*

Everything below is measured from live production logs or committed code, with
the citation attached. Where a number is an estimate it says so.

---

## What is already working (so it is not on the list)

Established from real runs today, not from reading the code:

- **Extraction is ON.** `EXTRACTION_THRESHOLD_RATIFIED = True`
  (`tools/routing_data.py:61`).
- **The ingest cron runs 3× an hour**, 30 sources per run — `9,29,49 * * * *`,
  `MAX_SOURCES: 30` (`.github/workflows/ingest.yml:56,100`). With 266 enabled
  sources that is a full cycle roughly every 3 hours.
- **Auto-publish is ON and working.** `autopromote.yml` runs hourly at `:15`
  with `AUTO_PUBLISH_RATIFIED: "1"`, and run 31052244130 shows real
  publications: `action=promoted event_id=61faa0f7-… detail=PASS →
  auto-published as confirmed`. Nothing is waiting on a human to click
  promote.
- **The engine reads real sources.** Run 31050080437 read the Austin Chronicle
  calendar and correctly refused its bare-time claims rather than guessing.

So the pipeline is not broken and the publish valve is not shut. The volume
problem is narrower than that, and item 1 is most of it.

---

## 1. The gate contradicts the publish policy — highest leverage by far

**Status: MERGED 2026-08-06 (PR #193, squash `7609222`) and MEASURED. Done.**

This is the single biggest cause of low volume, and it is visible verbatim in
the live autopromote log (run 31052244130):

> `action=human_review detail=policy would publish (single trustworthy source
> → auto-published as likely (founder ruling 2026-08-04)) but the fresh gate
> verdict is 'hold' (Insufficient corroboration (have 1; need 2)) — the
> promoter publishes only gate-PASS candidates; left for human review`

In that one sampled pass: **3 promoted, 4 held on exactly this**. The publish
policy already implements the founder's ruling. The GATE does not, because the
source's class is not in `ANCHOR_CLASSES`. The two disagree and the gate wins,
so events the policy considers publishable are parked.

PR #193 makes first-party and published-media classes promote on one source —
`local_media` (Chronicle, do512, KUT, CultureMap), plus the institutional
classes found in the live DB that no code defined (`theater_arts`,
`gallery_museum`, `food_culinary`, `university`).

**Expected effect (written BEFORE the merge):** the `human_review` rows above
become `promoted` rows. Based on the sampled 3:4 ratio this is plausibly a
near-doubling of publish rate, but the sample is one pass — treat it as
directional until measured (see item 8).

**MEASURED effect (run 31067808019, on the merged code, ceilings raised to
`limit=3000 stamp_limit=20000` at founder direction — "Do Option 1 + the speed
rule"):**

```
StampReport:       examined 418  stamped_ready 239  stamped_hold 111  escalated 68  errors 0
AutopromoteReport: examined 292  promoted 292  human_review 0  errors 0
```

All 292 published as `confirmed`. **Zero held, zero errors** — the
`policy would publish … but the fresh gate verdict is 'hold'` line does not
appear once in the log. The prediction was directionally right and understated:
the hold rate went to zero, not to half.

Note what the ceiling proved: `limit=3000` was never the binding constraint —
the ready queue held 292. The backlog was not thousands deep; the gate was
simply refusing it.

---

## 1b. THE NEW HEADLINE: published discovered events carry no usable date

**Status: FOUND 2026-08-06 by the first real end-to-end measurement. Not
fixed. This is now the binding constraint, ahead of everything below.**

Merging item 1 let the publish pass run at full rate, and running the
read-only production scope report immediately afterwards
(`db-report.yml` run 31068431505, `tools/db_scope_report.py`) produced the
first honest picture of the live site:

| | total rows | with a FUTURE start_time |
|---|---|---|
| licensed lane (Ticketmaster/ics/jsonld — events anyone can license) | 1,644 | **1,359** |
| **pipeline lane (our discovered events)** | **2,215** | **1** |
| published total | 3,859 | 1,360 |

Read the second row again. We have **2,215 discovered events published**, every
one of them gated and stamped `confirmed`, and **exactly one** of them has a
start time in the future. The same report's 50:1 KPI block shows it from the
other side: `non_api_events` is **0** for today, 0 for the weekend, and 0 for
the next seven days, against 19 / 74 / 116 licensed events in those windows.

So the site is not empty — it is showing the *licensed* feed. Almost nothing
we discover ourselves is reaching a visitor, and item 1 did not change that,
because item 1 was about whether events get published, not about whether a
published event is findable.

**The mechanism, traced end to end in committed code:**

1. A third of sampled sources publish bare time strings — "8pm", "6:00 PM" —
   with the calendar date living in a page header above the listing.
2. `worker/datetime_normalize.py` **correctly refuses to guess** a date it
   cannot see in the string (its module docstring states the rule: guessing
   "would assert an unverified fact, the exact thing the pipeline exists to
   prevent"). `start_time` is stored as NULL and the raw claim is preserved
   under `_provenance.unstored_datetime_claims`.
3. The trust gate has **no date requirement at all** — `worker/gating.py`
   contains no reference to `start_time`. A dateless candidate passes.
4. `worker/promote.py` publishes it anyway: line 132 reads
   `dups = find_possible_duplicates(...) if start_time else []` — the promote
   path explicitly tolerates a missing start time.
5. The consumer feed then cannot show it. `web/lib/promoted.ts`
   (`buildPromotedQuery`) filters `start_time` with `gte.`/`lte.` for the
   requested window, and PostgREST excludes NULLs from a range filter. A
   dateless event is published, correct, gated — and invisible.

Nothing in that chain is a bug in isolation. Step 2 is the trust invariant
working exactly as designed, and it must not be "fixed" by defaulting a date.
The defect is that steps 3-5 treat a dateless candidate as publishable when the
only surface that displays it requires a date.

**This is what PR #189 is for.** Date recovery reads the date out of the page
header and attaches it to the time-only blocks beneath it — recovering a date
the source really did state, rather than inventing one. #189 has therefore gone
from "a nice correctness PR in review" to **the highest-leverage unmerged work
in the repo**, and its round-8 finding (a range header like "August 5-9" being
read as a single day) is squarely on the same code path.

**Two things must be planned, not assumed** (founder ruling 2026-08-06,
plan-first):

- **How many of the 2,215 are dateless vs genuinely past?** The scope report
  measures "upcoming", which conflates NULL with past. The split decides
  whether #189 recovers ~2,000 events or ~200. Getting it needs a small
  read-only addition to `tools/db_scope_report.py` (a NULL/past/future
  histogram of `event.start_time`), and `db-report.yml` is master-only by
  design, so the addition has to land on master to be runnable.
- **Should the gate hold a dateless candidate instead of publishing it?**
  Arguable both ways — holding keeps the published set honest, publishing keeps
  the row visible to ops and to a future backfill. Changing what the gate
  requires is a gate change and therefore founder-crucial either way.

---

## 2. Only page 1 of each calendar is read

**Status: fixed in PR #189 (which carries the pagination), waiting on review.**

The Austin Chronicle calendar publishes **2,362 events across 60 pages**; a
single-page fetch reads roughly forty. Multi-page ingestion follows the
source's own next-page links, bounded to 5 pages per source per run, with
front-following depth (calendars are date-ordered, so page 1 holds the
soonest events and deeper ones rise as their dates approach).

**Expected effect:** up to 5× the events per paginated source per run. Not
5× overall — most sources are single-page venue calendars.

---

## 3. The Chronicle is category-segmented and we read one slice

**Status: NOT STARTED. This is new, from the founder's 2026-08-06 screenshot.**

The screenshot shows the calendar URL carrying filters —
`Showing All Events · on Date Wed, Aug 5 → Wed, Aug 5 · Showing Categories
Music` — and a category tree beside it:

> Arts · Community · Family · Film · Food & Drink · Music · Out of Town ·
> Queer · Sports

plus sibling sections: **Music, Summer Events, Movie Times, Contests**.

Our source row points at one view of that calendar. Even with pagination
fixed, a category-filtered or date-filtered view will not surface the rest.
The founder was explicit that this is not a template to copy — *"I'm not
saying to replicate - but it should help you ensure we are crawling all"* —
the point is coverage, not imitating their taxonomy.

**Work required:**
- Determine what the Chronicle's *unfiltered* calendar URL is, and whether one
  exists that spans categories, or whether each category must be enumerated.
- If enumeration is needed, decide whether one source row per category (9-13
  rows) or one row with a category list is the right shape. One row per
  category is simpler and needs no new code; it multiplies the source count.
- Apply the same audit to do512, KUT and CultureMap, which are likely
  segmented too.
- **Requires a plan first** (founder ruling 2026-08-06): this changes what we
  crawl, not just how.

---

## 4. 86 sources exist in the live DB that the repo catalog does not describe

**Status: partially addressed; the audit is NOT done.**

The committed catalog holds 180 sources; the ingest run reports *"processing 5
of 266 enabled sources"*. Roughly 86 sources were seeded straight into the
database, and four of their classes (`theater_arts`, `gallery_museum`,
`food_culinary`, `university`) were unknown to the gate — which is why they
were held forever, silently.

PR #193 names those four and adds a loud warning for any future unknown class,
so this cannot recur invisibly. What has NOT been done is the audit itself:
nobody has listed the 86, checked their URLs resolve, or confirmed their
classes are right. Some fraction are probably dead or misclassified.

**Work required:** dump the live `source` table, diff against the catalog,
verify each unlisted row, and either commit it to the catalog or disable it.

---

## 5. Source breadth — 266 sources is not a thousands-of-events corpus

**Status: machinery built, never run at scale.**

The discovery machinery — `source-scan.yml` plus the Brave search lane — is
NOT in the tree yet; it lands with PR #187, which is still open. The launch
sweep (max_queries 1000) has therefore never been dispatched, and cannot be
until #187 merges. (Verified rather than assumed: `source-scan.yml` exists
only on `claude/search-lane-brave`. `tools/db_scope_report.py` and
`prove_feed.yml`, cited in item 8, DO exist on master.)

**Work required:** dispatch it, review what it finds, import the survivors
through `tools/import_sources.py` — which will now refuse any row whose class
the gate does not know, so the vocabulary cannot drift again.

**Note:** more sources multiplies the ingest cycle time. At 30 sources/run ×
3 runs/hour, 500 sources would take ~5.5 hours per cycle. Item 7 covers that.

---

## 6. Eventbrite and the other structured feeds are not on a schedule

**Status: import path exists (`import_structured.yml`), lane not scheduled.**

Structured feeds are the cheapest events we can get — no AI extraction, no
date recovery, no gate ambiguity. They should be the volume floor, not an
afterthought. WS4 in the standing queue.

---

## 7. Throughput ceiling: 30 sources per run

**Status: a deliberate cap, not yet re-examined against the new volume.**

`MAX_SOURCES: 30` was set when the corpus was small. With pagination landing
(item 2) each source now costs more time and more extraction budget, and with
item 5 the corpus grows. The cap, the cron cadence, and
`EXTRACT_MAX_EVENTS_PER_PAGE` (default 50) need re-deriving together against
the spend ceiling.

**This is a money decision** and therefore founder-crucial: raising throughput
raises the extraction bill. It should be presented with a projected
cost-per-verified-event, not just a new number.

---

## 8. Nobody is measuring any of this — the gap behind the frustration

**Status: NOT STARTED, and it is why this has felt endless.**

Every test written this session is an internal unit test. There is no
end-to-end measurement that answers the founder's actual question: *how many
events are live on 1live.co right now, and is that number going up?*

`tools/db_scope_report.py` and `prove_feed.yml` exist. Neither is scheduled,
and neither has been used to produce a trend.

**Work required — this should arguably come FIRST:**
- A scheduled job that records, per run: candidates created, gate PASS vs
  HOLD, events promoted, and the live `/tonight` count.
- One number posted where the founder can see it without asking.
- Then every item above becomes measurable instead of argued.

---

## Honest sequencing

| # | Item | Blocked on | Effort |
|---|---|---|---|
| 1 | Gate/policy contradiction | — | **MERGED + measured 2026-08-06** |
| 1b | **Dateless published events** | plan → #189 | **now the binding constraint** |
| 2 | Pagination | PR #189 review | done, in review |
| 8 | Measurement | nothing | small |
| 4 | Audit the 86 DB-only sources | nothing | medium |
| 3 | Category segmentation | plan + founder approval | medium |
| 6 | Structured feeds on a schedule | nothing | medium |
| 5 | Source-discovery sweep | nothing | medium |
| 7 | Throughput/cost re-derivation | founder (money) | small + decision |

Item 1 is done and measured. Item 1b is the new front of the queue and it runs
through #189. Item 8 is small and makes everything else legible. Items 3-7 are
the real remaining build.

## What "thousands" plausibly requires

Rough arithmetic, stated as an estimate: 266 sources × ~40 events on page 1 is
already ~10,000 candidate events per full cycle — and the live count is now
measured rather than estimated: **9,223 candidates** in
`event_candidate` (scope report, 2026-08-06). **The corpus is large enough
already** — the remaining work is about letting what we already extract reach
the site, not about finding more. Items 3-5 matter for breadth and freshness,
not for clearing the first thousand.

## The one sentence that matters, revised

The original version of this document ended: *"the bottleneck is the gate, not
the supply."* That was right, and item 1 removed it — 292 published in one pass
with zero holds. Measuring immediately afterwards revealed the sentence was
only half the truth, so it is superseded rather than deleted:

> **The bottleneck was the gate. Now it is the date.** 2,215 discovered events
> are published and exactly one of them has a future start time — so the events
> exist, they are gated, they are `confirmed`, and the feed still cannot show
> them. Supply was never the problem, and now publication is not either.

Keeping both sentences on the page is deliberate. The first one was measured,
acted on, and proved correct; it was also incomplete, and a document that
quietly swapped it out would hide that a prediction ran out before the problem
did.
