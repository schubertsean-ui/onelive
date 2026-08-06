# Why the site is empty: the crawler never clicks through

**2026-08-06.** Written at founder direction ("save all to disk") at the point
the session was stopped. Everything below is measured or read off committed
code, with the citation attached. The plan at the end is **NOT APPROVED** and
nothing in it was built.

---

## The founder's diagnosis, which is the correct one

> "your main problem is you are doing a poor job investigating each web page
> and then clicking through to find the details"

Our ingestion fetches **one URL**, splits the returned text into blocks, and
asks the model to pull events out of the blob. It never navigates: it does not
find the events section of a site it landed on, does not open an individual
event, and does not follow a venue's ticketing link. Every symptom below is a
consequence of that single gap.

The founder demonstrated it in three clicks — acllive.com → Events → the event
— arriving at a page that reads, in plain text:

```
MASEGO — Fix Your Face Tour, with Lekan
THURSDAY AUGUST 6, 2026
8:00 PM
```

The date is also on the listing card (`AUG 6, 2026`) and in the URL itself
(`/event/2026-08-06-masego-at-8-pm`). Nothing is hidden. We publish 81 events
from this venue with no date and mostly no title.

---

## What was measured

### The published state (db-report run 31068431505, prove-feed run 31069431885)

| | rows | with a FUTURE start_time |
|---|---|---|
| licensed lane (Ticketmaster / ics / jsonld) | 1,644 | 1,359 |
| **our discovered-events pipeline** | **2,215** | **1** |

Split of the pipeline rows by date usability, measured directly:

```
total            2215
NO start_time    2214
past start_time     0
future              1
```

Not "mostly stale" — **essentially every event we discover ourselves carries no
date at all**, so the feed (which filters by date range, and PostgREST drops
NULLs from a range filter) cannot show any of them.

### The gate fix that preceded this (PR #193, merged 7609222)

Autopromote run 31067808019 at raised ceilings: stamp 418 examined
(239 ready / 111 hold / 68 escalated), promote **292 examined / 292 promoted /
0 human_review / 0 errors**. The gate/policy disagreement is genuinely gone.
Publication is not the bottleneck. What we publish is unusable.

---

## The trace, step by step

Each step was checked, not assumed.

1. **The normalizer is correct.** `worker/datetime_normalize.py` accepts every
   full-date form tested (ISO, `August 15, 2026 8:00 PM`, `Aug 15 2026 8pm`,
   `8/15/2026 8:00 PM`, `Friday August 15, 2026`) and refuses only genuinely
   dateless text. Not the bug.
2. **`promote` is correct.** `worker/promote.py` copies `start_time` from the
   candidate verbatim. The candidates arrive dateless.
3. **The extractor emits times with no dates, constantly.** Ingest run
   31059045677 (30 sources, 20 minutes): **139 refusals**, every one
   `no-full-date-evidence`, e.g. `UMLAUF Sculpture Garden + Museum:
   start_time {'raw': '11:00 AM'}`.
4. **But that only explains listings that genuinely lack a date** — and the
   ACL Live and Bastrop pages plainly have one. So it is not the whole story,
   and treating it as the whole story was the session's own recurring error
   (see "What I got wrong", below).

---

## The four distinct causes found

### 1. We fetch pages that contain no events at all

`source_url` values taken off our own published rows — these are the sources
with the most invisible listings:

| Source | URL we crawl | What it is |
|---|---|---|
| The Parish (53 rows) | `brushystreet.com/event-calendar` | a different venue's website |
| Vulcan Gas Company (158) | `vulcanatx.com/` | site root, not a calendar |
| Stubb's Austin (34) | `stubbsaustin.com/` | site root |
| Luling Watermelon Thump **Schedule** (72) | `watermelonthump.com/properties` | not the schedule page |
| Eventbrite API (7) | `eventbrite.com/platform/api` | developer documentation |
| ACL Live Moody (81) | `acl-live.com/events` | domain does not match our catalog |

The committed catalog (`sources/master_sources_catalog_120.json`) says ACL Live
is `https://www.acllive.com/`. The live database crawls
`https://www.acl-live.com/events` — a different hostname. The catalog and the
production `source` table disagree, and the database is what runs.

For these rows, "no date extracted" is the CORRECT output: there was no event
on the page. It also explains the untitled rows — there was never an event to
name.

### 2. JavaScript-rendered sites are read as empty shells

`acllive.com` builds its listings in the browser. `worker/fetch/render_fetch.py`
re-fetches through a real browser **only** when the sensor flags a page as
`boilerplate_only`. A JS shell carrying ordinary nav and footer text does not
trip that flag, so we extract the shell as though it were content.

### 3. Date ranges are dropped, and — worse — silently mis-parsed

Tested against the literal strings on `bastropoperahouse.org`:

```
'Friday, September 4, 2026, – Sunday, September 27, 2026,'  REFUSED: unparseable
'Fri, Sep 4, 2026,  – Sun, Sep 27, 2026,'                   REFUSED: unparseable
'Fri, Sep 4, 2026'                                          -> 2026-09-04   OK
'September 4-27'                                            -> 2027-09-04   WRONG
'SEPT 04-27'                                                -> 2027-09-04   WRONG
```

Either endpoint alone parses. Joined by a dash the whole claim is discarded —
so theatre runs, gallery shows, antique fairs and multi-day festivals are lost
wholesale.

And a range with no year is read with the range END as the YEAR. `SEPT 04-27`
— the exact string printed on the Newsies poster — becomes September 2027.
Both probes of the two-probe guard agree on it, so the mechanism that exists
specifically to prevent invented dates passes it as genuine evidence. That is
a fabricated date publishable under a `confirmed` label. Recorded as **R-081**.

### 4. A run is not an event

Bastrop's page states `Fri, Sep 4, 2026 – Sun, Sep 27, 2026` and says outright:
*"For specific show days and times please click the button below."* The twelve
actual performances (7:30 PM Fri/Sat, 2:30 PM Sun) live on
`bohtickets.ludus.com`, a different domain behind "Buy Tickets".

Even perfect range handling yields "a run", which is not what a person
browsing tonight needs. Showtimes require following the ticketing link, and
require deciding whether a row in `event` is a PRODUCTION or a PERFORMANCE.
For a "what's on tonight" feed it has to be a performance.

---

## What this does to PR #189

#189 infers a date from a listing fragment: carry the page's date context down
into time-only blocks, call back to the source, apply a year rule last. Eight
review rounds; five variants of one defect class (a partial identity signal
treated as proof of identity); the range case found today is the sixth.

Most of that machinery exists to guess at something the detail page states
outright. `THURSDAY AUGUST 6, 2026 / 8:00 PM` needs no context carry, no
identity rule, no year inference, no range interpretation.

**#189 is a workaround for not clicking through.** It is not wrong, and it
still helps sources that genuinely list only a time — but it is no longer
obviously the highest-leverage work, and the estimate that it recovers ~2,200
events is NOT supportable: an unknown share of those 2,214 rows are
extractions of pages that never contained an event, and no date recovery can
help them.

---

## What I got wrong this session, in order

Each was corrected by the founder, not caught internally.

1. Reported "the bottleneck is the gate, not the supply." True, and fixed —
   but incomplete, and I presented it as the answer.
2. Explained the dateless events as "a third of sources publish bare times."
   That accounts for a third, not 2,214 of 2,215. **A mechanism that explains
   a fraction was allowed to stand as the explanation for all of it** — the
   same defect class this session has now recorded six times.
3. Said the founder "sat the exam personally." The founder dispatched it; the
   harness, the golden set, the scoring, the classifier and the code under
   test were all written by this agent. That is a custody control, not
   independent oversight.
4. Called the golden-exam refusal "correct" without checking what happens
   afterwards. It is manual and maintainer-dispatched; nothing re-runs it when
   a harness change merges. Recorded as **R-082**.
5. Sampled 60 rows ordered by source name and reported "2 affected sources."
   It had only seen the alphabetically-first two calendars. Fixed; the true
   figure is 95 sources.
6. Estimated the recoverable event count three times from three different
   wrong models of the problem.

The through-line: **a signal that narrows the possibilities treated as one
that determines the answer.** It is the same shape as the defects the review
panel kept finding in #189, applied to my own reasoning about the system.

---

## The plan — NOT APPROVED, NOT BUILT

Recorded so the next session starts from it rather than re-deriving it.
Founder stopped the session before approving any of this.

**What** — Rebuild ingestion as navigation rather than single-page extraction:
1. From the source URL, find the events/calendar page if we are not on one.
2. Render pages that need JavaScript, instead of only when a page looks like
   nav chrome.
3. Enumerate the individual event links from the listing.
4. Fetch each event's own page and extract from it, where date, time, title,
   price and ticket link are stated explicitly.
5. Follow the ticketing link when a venue defers showtimes to it.

**How** — Link enumeration is ordinary HTML parsing, no model call. Extraction
moves from "segment a blob" to "read one event page," which REMOVES
segmentation heuristics rather than adding to them. Rendering already exists
in `worker/fetch/render_fetch.py`; what changes is when it triggers. A
per-source detail-page cap keeps one large calendar from eating a run.

**Why this and not #189** — #189 infers dates from fragments; this reads them
where they are written. Where they conflict the detail page wins, and most of
#189's rules stop having a job.

**Why that matters** — Every defect class this session has been a partial
signal treated as a whole answer. Working from a listing snippet GUARANTEES
partial signals. The detail page ends the class instead of patching its next
instance.

**Expected outcomes** — Events carry real dates and titles and therefore
appear on the feed; untitled rows stop being generated; runs resolve into
individual performances. Cost is slower cycles per source and a throughput
number to re-derive with the founder.

**Cost note, measured not guessed:** `worker/ai_extract.py` already makes ONE
extraction call per event block. Reading detail pages does not multiply AI
calls — same count, better input. The added cost is HTTP fetches and browser
rendering: time and bandwidth, not materially more model spend. Throughput
(`MAX_SOURCES: 30`, 3 runs/hour) is the constraint to design against, and
re-deriving it is a founder decision.

**Two open questions the founder had not answered when work stopped:**
- How deep to go per source (the throughput cap).
- Whether to repair the bad catalog URLs first. Recommendation: yes — a
  crawler that navigates from the wrong site still ends up in the wrong place,
  as The Parish pointing at `brushystreet.com` shows.

**Smallest first step offered, not accepted:** one source end to end (ACL Live),
so real dated events appear on the site before committing to the rebuild.

---

## Instruments built today (read-only, no secrets)

- `tools/sample_dateless.py` on branch `claude/dateless-diagnostic` — splits
  `event` into NO-date / past / future, prints real examples with venue and
  source URL, prints every affected source with counts, and prints every row
  that DID get a stored date (so an asserted date can be eyeballed against its
  source). Runs through `prove_feed.yml`, which holds no secrets and has no
  master-only guard, so it can run from a branch.
- NOT built: the fetch probe that would turn causes 1 and 2 above from
  hypothesis into counts — run the real fetcher against the top 20 dateless
  sources and report status, final URL after redirects, byte count, and
  whether the visible event text appears in what we received. **This is the
  measurement that decides the fix order and it has not been run.**
