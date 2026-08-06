# Complete evaluation: what in this codebase blocks the thing that was asked for

**2026-08-06.** Written at founder direction: *"I also want a complete
evaluation - a-z with nothing omitted - of our current code to identify where
the blocks are that are preventing you from building what I have plainly asked
you to build."*

Every claim below cites a file and line, a measured run, or a committed
schema. Where I am inferring rather than measuring, it says so.

**The thing asked for, quoted so it cannot drift:**
> "The end product should be a perfect extraction or ingestion of every event,
> date, time, specifics, notes, descriptions, specials, etc that are on a site
> that will be and are translated to 1 live."

---

## Executive summary — the five that actually matter

| # | Blocker | Severity |
|---|---|---|
| **1** | The extraction schema has **no field for price, description, or category**. What was asked for cannot be stored. | **Hard blocker** |
| **2** | We parse schema.org JSON-LD, keep 4 of ~12 fields, flatten it to a string, and pay a model to re-read it. | **Hard blocker + waste** |
| **3** | Ingestion fetches ONE url and never opens an event's own page. | **Root cause** |
| **4** | Nothing anywhere asserts that a published event is *visible*. 2,214 invisible events passed every gate. | **Systemic** |
| **5** | The change harness costs more per change than most changes cost. | **Velocity** |

Blockers 1 and 2 are small code changes. Blocker 3 is the architecture. Blocker
4 is a missing test. Blocker 5 is why everything has taken so long.

---

# A. Data model

## A1. The extraction schema cannot hold price, description, or category

`worker/ai_models.py:8-19` — the complete set of fields the extractor may
return:

```python
class AIEventExtraction(BaseModel):
    title, start_time, end_time, venue_name, city,
    artist_names, ticket_link, rsvp_link,
    is_private_rsvp, private_access, notes
```

There is **no** `price`, `price_min`, `price_max`, `is_free`, `description`,
`category`, `image_url`, `performer`, `door_time`, or `age_restriction`.

Consequence: a site can state "$25 advance / $30 door, doors 7pm, 21+, here is
the description" and the pipeline is structurally incapable of carrying any of
it. This is not an extraction-quality problem. It is a missing column.

**Severity: hard blocker on the stated goal.** No amount of crawler work fixes it.
**Cost to fix: hours.** Add the fields to the model, the candidate table, and
the promote INSERT.

## A2. `event_candidate` has no price or description columns

`supabase/migrations/0002_event_candidates.sql` — candidate columns are
title, start/end time, venue, city, artists, ticket_link, rsvp_link, raw_text,
extracted (jsonb). Price and description exist nowhere except inside the
free-form `extracted` blob, which nothing downstream reads for those fields.

## A3. The public `event` table HAS price columns the pipeline never fills

`0010_licensed_feed_and_domains.sql:33-37` adds `price_min`, `price_max`,
`ticket_url` to `event`. The licensed importer fills them. `worker/promote.py`
fills `ticket_url` only — via `card_fields`, derived from `ticket_link`.
**Every pipeline-published event has NULL price**, not because the site didn't
say, but because nothing carries it.

## A4. One row = one event. There is no production/performance distinction

A theatre run ("Newsies, Sep 4–27", twelve performances) has no representation.
Either it becomes one row with a wrong or absent date, or nothing.
Consequence: theatres, comedy rooms, dance companies and gallery runs — five of
the twenty-three ratified segments — cannot be represented correctly.

## A5. No recurrence model

"Live music every Thursday 6–9pm" is one sentence meaning ~52 events. Nothing
in the schema or the extractor understands it. This is how most taprooms,
neighbourhood bars and open-mic scenes publish — segments 2, 3, 4 and 15.

---

# B. Extraction architecture

## B1. Single-page fetch. No navigation. (The root cause)

`worker/orchestrator.py:_run_one_source` — fetch `source["url"]`, sensor-check
it, segment the text, extract. There is no step that finds a site's events
page, and no step that opens an individual event.

The founder demonstrated the gap in three clicks: `acllive.com` → Events → an
event page reading `THURSDAY AUGUST 6, 2026 / 8:00 PM`. We publish 81 dateless,
mostly untitled rows from that venue.

## B2. We find structured data and then throw it away

`worker/segment.py:212-281`. The code locates schema.org `Event` JSON-LD —
the exact typed object with `startDate` as an ISO timestamp — and then:

```python
for key in ("name", "startDate", "start_date"):   # keeps 2 fields
    ...
text = " | ".join(parts)                          # flattens to a string
```

It keeps **name, startDate, location, url**. It discards `endDate`, `offers`
(price), `description`, `performer`, `image`, `eventStatus`,
`eventAttendanceMode`, `doorTime`, `organizer`, `duration`.

Then the pipe-joined string is handed to a model to extract from prose the
values we already had as typed fields.

Three separate defects in one function:
1. **Cost** — we pay a model per event for data that was free and exact.
2. **Accuracy** — an ISO timestamp becomes a substring the model must find again.
3. **Coverage** — price and description are dropped here even when published,
   which is a second, independent cause of A1's symptom.

**This is the single highest-value fix in the codebase.** Reading the typed
fields directly is strictly cheaper, strictly more accurate, and cannot
hallucinate.

## B3. Heuristic blob-splitting is the fallback for everything else

`worker/segment.py` (394 lines) splits page text into "event blocks" by
repeated-structure detection and anchor heuristics. Everything downstream —
including the entire `date_callback` machinery in PR #189 — exists to repair
the ambiguity this creates. Eight review rounds on #189 found six variants of
one defect class, all of them "a partial signal treated as the whole answer."
Those ambiguities do not exist on a detail page.

## B4. The browser-render trigger is too narrow

`worker/fetch/render_fetch.py:238` `should_render()` returns true **only** when
the sensor flags `boilerplate_only`. A JavaScript shell that ships normal nav
and footer text does not trip it, so we extract the shell as though it were
content. This is the ACL Live failure exactly.

## B5. Pagination goes wide, never deep

`worker/fetch/paginate.py` follows *next-page* links — more of the listing.
Nothing follows an *event* link. Breadth without depth: we can read pages 1–5
of a calendar that tells us nothing useful on any of them.

## B6. No off-domain follow, so ticketing platforms are invisible

Bastrop Opera House states a range and says *"For specific show days and times
please click the button below"* — pointing at `bohtickets.ludus.com`. Small and
mid-size venues overwhelmingly outsource ticketing. The real showtimes are
always one hop away and we never take it.

## B7. Date ranges are dropped, and year-less ranges are silently mis-parsed

Measured against the literal strings on the Bastrop page:

```
'Friday, September 4, 2026, – Sunday, September 27, 2026,'  REFUSED unparseable
'Fri, Sep 4, 2026'                                          -> 2026-09-04  OK
'September 4-27'                                            -> 2027-09-04  WRONG
'SEPT 04-27'                                                -> 2027-09-04  WRONG
```

The parser reads the range end as a **year**. Both probes of the two-probe
guard agree, so the mechanism whose sole job is to refuse invented dates passes
it. Recorded as **R-081**. This is a live fabrication risk.

## B8. Cost scales with blocks, and blocks are garbage on a bad page

`worker/ai_extract.py:40-47` — one model call per event block, capped at 50 per
page. On a JS shell or a homepage, those blocks are navigation, so we pay per
call to extract nothing. The cap protects the budget; it does not protect the
output.

---

# C. Trust and gates

## C1. The gate has no date requirement

`worker/gating.py` (142 lines) contains no reference to `start_time`. A
candidate with no date passes the trust gate.

## C2. The promoter publishes dateless events on purpose

`worker/promote.py:132`:

```python
dups = find_possible_duplicates(venue_id, start_time, cur=cur) if start_time else []
```

A dated event is duplicate-checked and can be **refused**. A dateless event
skips the check entirely and always publishes. The publication path is
therefore *biased toward* publishing exactly the events that cannot be
displayed.

## C3. The feed cannot show what the pipeline publishes, and nothing notices

`web/lib/promoted.ts:94-95` filters `start_time` with `gte.`/`lte.`; PostgREST
excludes NULLs from a range filter. So a dateless event is published, gated,
labelled `confirmed`, and invisible.

**2,214 events passed every gate in this repo and are invisible to every user.**
Twenty validate checks, 1,953 tests, a golden exam, a trust gate, a
non-Claude adversarial panel — and not one of them asks *"can a person see
this?"* That is the systemic failure, and it is a missing test, not a missing
opinion.

---

# D. Catalog and data

## D1. Production source rows disagree with the committed catalog

From `source_url` on our own published rows:

| Source | URL we crawl | What it is |
|---|---|---|
| The Parish (53 rows) | `brushystreet.com/event-calendar` | a different venue's site |
| Vulcan Gas Company (158) | `vulcanatx.com/` | site root |
| Stubb's Austin (34) | `stubbsaustin.com/` | site root |
| Luling Watermelon Thump *Schedule* (72) | `watermelonthump.com/properties` | not the schedule |
| Eventbrite API (7) | `eventbrite.com/platform/api` | developer docs |
| ACL Live Moody (81) | `acl-live.com/events` | catalog says `acllive.com` |

For these, a dateless untitled extraction is the *correct* output — there was
no event on the page. Recorded as **R-083**.

## D2. 86 sources exist in the live DB that the catalog does not describe

Catalog holds 180; ingest reports 266 enabled. Nobody has audited the gap.

## D3. Nine of twenty-three ratified segments have no catalog representative

Recurring-scene organizers, social-dance communities, bands, solo musicians,
DJs, comedians, visual artists. A supply gap independent of extraction.

---

# E. Process — why this has taken so long

This section is the honest answer to the founder's question, and it is about
work I created.

## E1. Every runtime change requires a live re-arming ritual

`tools/arming_runtime.py` defines 29 runtime files. Touching **any** of them
invalidates `docs/evidence/ARMING_SMOKE_RUN.json`, turning trust-gate and
adversarial-review red until a **fresh ingest run is dispatched against the
branch head and re-bound** in a docs-only commit.

That means: push → dispatch → wait for a real crawl → read the run id → edit
the evidence file → commit → push → re-run checks. And `ingest.yml` shares one
concurrency slot with the production cron, so the dispatch can be cancelled by
a scheduled run and has to be retried.

**Minutes to change three lines of `gating.py`: tens. Sometimes an hour.**
PR #189's evidence file lists **twenty-one superseded runs** — twenty-one
re-arming cycles for one pull request.

## E2. The golden exam is red by design and never re-runs itself

Any PR touching `worker/ai_extract.py` fails `golden-exam` on purpose. The
merge is allowed via a classifier exception. But the *real* exam
(`extraction-exam-dispatch.yml`) is manual and maintainer-dispatched, so after
a harness change merges, hallucination rate is re-measured **only if a human
remembers**. Recorded as **R-082**.

## E3. Review rounds

PR #189: **eight rounds**. Rounds 3, 4, 6, 7 and 8 found the same defect class.
The panel is genuinely good — it caught real bugs — but each round costs a
full re-arm (E1) plus a full check suite.

## E4. `construction_gate` fires on documents about defects

It matches trigger words anywhere in the diff **content**, so a document whose
purpose is to describe defect classes trips every class it names. On this
session's records commit it demanded citations for **45 classes**, and on the
lab plan **45** again. Advisory, but it is noise that trains you to ignore a
gate. Recorded as **R-080**.

## E5. `staleness_check` makes every branch red until STATE.md is touched

Master moved when #193 merged; the reconciliation sits unmerged on #196. Every
branch cut from master is therefore red until it edits `STATE.md` —
including a branch containing nothing but a planning document. This blocked the
adversarial panel from running at all on PR #197 (the job died in `validate`
before reaching the review seats).

## E6. The merge freeze serialises everything

"Freeze all other merges while an exam-bound PR is open" is a sound rule that,
combined with E1–E3, produced a queue of **seven open PRs**, several of them
finished work.

## E7. The check suite itself

`tools/validate` runs 20 checks including 1,953 tests. Locally ~6 minutes; in
CI, four separate workflows per push.

## E8. 245 documents, 30,842 lines of governance prose

Real value in the decision records. But the ratio of governance to pipeline
code (**30,842 doc lines vs 7,278 lines of `worker/` + `ai/`**) is 4:1, and
every substantive change must be reflected in several of them.

## E9. The dev sandbox has no outbound network

Every real-world test is a CI round trip of 2–10 minutes. There is no way to
`curl` a venue page and look at it. This alone explains why "does our fetcher
actually see this page?" went unasked for so long — it is never one command
away.

---

# F. What is genuinely good and should not be rewritten

Stated so a rebuild doesn't throw it out.

- **`worker/datetime_normalize.py`** — the two-probe refusal is a sound design
  and correctly accepts every full-date form tested. Its only defect is range
  handling (B7).
- **The gate → candidate → promote separation** and the structural rule that
  the orchestrator cannot import the promote path.
- **`worker/fetch/render_fetch.py`** — a working headless renderer already
  exists. Only its trigger is wrong (B4).
- **`worker/sensors.py`** — content-quality sensing is real and useful.
- **The replay log** — every stage records inputs/outputs digests. This made
  today's diagnosis possible.
- **The adversarial panel** — it finds real defects. Its cost is E1/E3, not its
  judgement.
- **1,953 tests** — the suite is genuine. It simply never asked the one
  question in C3.

---

# G. Ranked recommendation

| Rank | Fix | Effort | Unblocks |
|---|---|---|---|
| 1 | Add price/description/category/image/performer to the extraction model + candidate + promote | hours | The stated goal — "costs, specials, descriptions" |
| 2 | Read JSON-LD **as typed fields** instead of flattening to a string | hours | Free exact dates + all of #1's fields, on every site that publishes it |
| 3 | Add a visibility assertion: a published event MUST be readable from the public feed | hours | Would have caught all 2,214 |
| 4 | Detail-page navigation (find events page → enumerate → open each) | days | The root cause |
| 5 | Fix `should_render` trigger | hours | The JS-shell class |
| 6 | Fix range parsing + the fabricated year (R-081) | hours | A live trust defect |
| 7 | Audit the source table against the catalog (R-083) | day | Sites we never actually reach |
| 8 | Follow ticketing platforms one hop | days | Theatres and small venues |
| 9 | Production/performance model + recurrence | days | Five segments |
| 10 | Reduce the change tax: batch the re-arm, fix `construction_gate`, unblock `staleness_check` | days | Everything above, ~2–5× |

Items 1–3 are hours of work each, and together they address more of the stated
goal than any crawler change. That they went unbuilt for weeks while #189 went
eight rounds on date heuristics is the clearest indictment in this document.
