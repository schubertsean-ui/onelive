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

**Status: fixed in PR #193, green, waiting on the merge freeze.**

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

**Expected effect:** the `human_review` rows above become `promoted` rows.
Based on the sampled 3:4 ratio this is plausibly a near-doubling of publish
rate, but the sample is one pass — treat it as directional until measured
(see item 8).

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

`source-scan.yml` plus the Brave search lane (PR #187) can discover new
sources. The launch sweep (max_queries 1000) has never been dispatched.

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
| 1 | Gate/policy contradiction | merge freeze only — **it is green** | done |
| 2 | Pagination | PR #189 review | done, in review |
| 8 | Measurement | nothing | small |
| 4 | Audit the 86 DB-only sources | nothing | medium |
| 3 | Category segmentation | plan + founder approval | medium |
| 6 | Structured feeds on a schedule | nothing | medium |
| 5 | Source-discovery sweep | nothing | medium |
| 7 | Throughput/cost re-derivation | founder (money) | small + decision |

Items 1 and 2 are finished work sitting behind a review queue. Item 8 is small
and makes everything else legible. Items 3-7 are the real remaining build.

## What "thousands" plausibly requires

Rough arithmetic, stated as an estimate: 266 sources × ~40 events on page 1 is
already ~10,000 candidate events per full cycle. **The corpus is very likely
large enough already** — items 1 and 2 are about letting what we already
extract reach the site, not about finding more. Items 3-5 matter for breadth
and freshness, not for clearing the first thousand.

That is the most important sentence in this document: the bottleneck is the
gate, not the supply.
