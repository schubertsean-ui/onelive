# Confirmed listing update — the fail-closed decision table

**Session Contract #55, 2026-09-02.** Generated from fixtures, not typed:
every row below is a real `worker.listing_update.adjudicate_page` decision,
rendered by `worker.listing_update.render_decision_table`. Regenerating it is
`tests/test_fair_crawl.py::test_the_founders_listing_table_from_fixtures`
(four of these rows, driven end to end through `run_loop`) plus
`tests/test_listing_update.py` (all of them, at the adjudicator).

Fixtures rather than a smoke run, per Operating Law rule 4 ("Sandbox 403 is
not a product failure. Use fixtures + CI") and the founder's own "Table from
fixtures or smoke". The armed-cron smoke run that re-binds this head's runtime
is a separate artifact (`docs/evidence/ARMING_SMOKE_RUN.json`) and proves the
runtime EXECUTES; this table proves what it DECIDES.

`check result` is the fail-closed verdict from
`worker.crawl_state.classify_recheck` — `present`, `absent`, or `no` (nothing
was learned). Read the four "yes" rows against the seventeen "no" rows: the default is no
mutation, and confirmation is the exception that has to be earned.

```
event                                                | check result | mutated? | why
-----------------------------------------------------+--------------+----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Nightjar — page moved it to 3am                      | present      | yes      | confirmed same-page change, gate PASS on that listing: start_time
Nightjar — page renamed it                           | present      | yes      | confirmed same-page change, gate PASS on that listing: title
Nightjar — page unchanged                            | present      | no       | the page still says exactly what we published — no change
Nightjar — page dropped its end time                 | present      | no       | the page still says exactly what we published — no change
Nightjar — moved, but the gate declined that listing | present      | no       | the page states a change, but the trust gate did not PASS that listing's own evidence — last good row stands
Nightjar — two listings match it                     | present      | no       | 2 listings on the page match this row on title or time — ambiguous; last good row stands
Nightjar — absent, page brackets its date            | present      | yes      | absent from a clean parse of the page that defines it, its title is absent from the page's own raw text, and the page's GATE-PASSED listings bracket its date — confirmed gone; marked cancelled, row kept with its evidence
Nightjar — extraction missed it, page still names it | present      | no       | the page still names this listing but the extraction did not return it — an extraction miss is not a cancellation; last good row stands
Open Mic — only next week's occurrence listed        | present      | no       | the page still lists this title, but at a date too far off to be the same occurrence — ambiguous; last good row stands
Nightjar — doors moved one hour                      | present      | yes      | confirmed same-page change, gate PASS on that listing: start_time
Nightjar — absent, calendar stops before its date    | present      | no       | not on the page, but the page's own gate-passed listings do not reach this date — a short calendar, or one the gate did not confirm, has not said this event is gone; last good row stands
Nightjar — page loaded but listed nothing            | present      | no       | page verified but it produced no listings this read — nothing to compare; last good row stands
Nightjar — absent, but the bracket failed the gate   | present      | no       | not on the page, but the page's own gate-passed listings do not reach this date — a short calendar, or one the gate did not confirm, has not said this event is gone; last good row stands
Nightjar — defining page 404                         | absent       | yes      | the defining page returned a clean 404 — confirmed gone; marked cancelled, row kept with its evidence
Nightjar — fetch timed out                           | no           | no       | unconfirmed — fetch failed (no status) — last good row stands
Nightjar — rate limited (429/503)                    | no           | no       | unconfirmed — rate-limited (429/503) — last good row stands
Nightjar — closed door (401/403)                     | no           | no       | unconfirmed — closed door (401/403) — last good row stands
Nightjar — tick budget deferred it                   | no           | no       | unconfirmed — budget or politeness deferred the check — last good row stands
Nightjar — page parsed, gate HELD                    | no           | no       | unconfirmed — page fetched and parsed, but the trust gate did not confirm it (held) — last good row stands
Nightjar — page parsed, gate ESCALATED               | no           | no       | unconfirmed — page fetched and parsed, but the trust gate did not confirm it (escalated) — last good row stands
Nightjar — sensor rejected the page                  | no           | no       | unconfirmed — page fetched but never reached the gate (sensor_rejected) — last good row stands
```

## Reading the four mutations

| row | why it is allowed to change a published listing |
|---|---|
| page moved it to 3am | Same page, still lists the show under the same title, states a different time. The MATCHED listing's own trust-gate verdict was re-computed and PASSed. Writes `start_time`; the row stays `scheduled` and visible with the new time. |
| page renamed it | Same page, same start time, different title. Matched on time, so a rename does not read as a disappearance. Writes `title`. |
| doors moved one hour | Same title, a shift small enough to be a re-time rather than another occurrence of a recurring series. Writes `start_time`. |
| absent, page brackets its date | Four things at once: the page loads, the raw page text no longer names the listing, its own listings bracket this date, and **those bracketing listings each pass the trust gate**. Writes `status='cancelled'`; the row is KEPT. |
| defining page 404 | The founder's 2026-09-02 overrule (`docs/memory/decisions/2026-09-02_404-of-defining-url-marks-the-listing-gone.md`). Writes `status='cancelled'` and nothing else — a page that is gone cannot state a new time or title. The row is KEPT. |

## Reading the seventeen refusals

Six of them are the ones worth arguing about, because each is a case where
something DID change and the loop still refused. **The last two were caught by
the adversarial panel on this PR, not by me** — both were real defects on the
published-data path, both are fixed here, and both are pinned by tests:

- **"moved, but the gate declined that listing"** — R-091(a). A page's gate
  verdict is the verdict of its FIRST extracted candidate, so on a
  forty-listing calendar it says nothing about the other thirty-nine. The
  page-level PASS is a precondition; the licence is the matched listing's own
  verdict.
- **"absent, calendar stops before its date"** — the false-absence guard. A
  calendar showing the next ten shows legitimately stops mentioning a show
  three months out. Cancelling on that would take a real event off the live
  feed on evidence that was never about it.
- **"page parsed, gate ESCALATED"** — the exact case the adversarial panel
  named on PR #213. Conflicting start times, a schema-invalid extraction, a
  private/RSVP listing or dedupe ambiguity are all reasons to distrust what
  this read says a listing now is.
- **"only next week's occurrence listed"** — normalized-title equality alone
  was treated as identity. `Open Mic` repeats its exact title weekly, so once
  the published night rolls off the calendar a title-only match is a single
  hit, and the row was retimed to the wrong night. A title match beyond
  `MAX_TITLE_ONLY_RETIME` (12h — a *daily* series' next occurrence is exactly
  24h away) is not an identity, and it is not an absence either.
- **"extraction missed it, page still names it"** — the absence branch read
  "the extractor did not return this event" as "the page no longer says it".
  Extraction is the one probabilistic stage in the pipeline; a model that skips
  a listing looks exactly like a removed show. Absence is now corroborated
  against the raw fetched text, deterministically and without a model.
- **"absent, but the bracket failed the gate"** — the asymmetry pointed the
  wrong way. An update already needed the matched listing's own gate PASS,
  while a cancel — the larger, user-visible action — rested on bracket
  timestamps straight from the extractor. A garbled or hostile extraction that
  omits the real event and emits plausible earlier+later listings around its
  date would manufacture the very coverage window the guard demands. The
  bracket must now be gate-passed on both sides.

## What no row can do

No verdict, no evidence and no confidence level deletes a published row.
`worker.crawl_state.may_delete_listing` returns False for every input
including ones nobody has written yet, `worker/listing_update.py` contains no
`DELETE` and no `INSERT INTO event`, and both facts are pinned structurally
rather than by prose.

## The live re-bind run — where the R-091 tightening fired for real

Founder-authorized dry smoke, run
[33698783298](https://github.com/schubertsean-ui/onelive/actions/runs/33698783298)
on head `d29dc5c` — success, 123.3s, 2 sources, 26 candidates, $0.5991.
Recorded in full in `docs/evidence/ARMING_SMOKE_RUN.json`.

**The switch, proven twice:** `LISTING_UPDATE_MODE: dry` resolved in the step
env, and then the run's own line —

```
listing-update writer DISABLED for this run (dry): no published row can be
updated or marked, whatever any page says.
```

The counters agree (`'listings_updated': 0, 'listings_marked_gone': 0`) but
they are consistency, not evidence: the tick reported `0 event-proximity
page(s)` due, so it would have printed zeros with the writer armed. The
DISABLED line is the proof.

**What this run showed that no fixture could.** The R-091(a) tightening fired
live, on both branches, in a single ordinary tick:

```
source             | queue   | url fetched                          | changed? | verified? | candidates
-------------------+---------+--------------------------------------+----------+-----------+-----------
Thinkery           | refresh | https://my.thinkeryaustin.org/events | yes      | present   | 1
Historic Scoot Inn | refresh | https://www.scootinnaustin.com/      | yes      | no        | 25
```

Historic Scoot Inn's page fetched fine, parsed fine, and produced **25**
candidates — and then ESCALATED at the trust gate: *"conflicting start_time
across evidence; dedupe-ambiguity hint present."* Its verdict reads `no`.

**Under the previous rule that same page would have read `verified_present`,**
because it parsed cleanly. That is exactly the case the PR #213 panel named —
"a parsed-but-escalated page cannot accidentally authorize a misleading
published update" — and it turned up unprompted, on a real venue calendar, on
the second source of a two-source tick. Thinkery is the control: a gate PASS,
and `present`.

**What it does not show:** the listing-update path acting on real data. The
writer was disabled and no event-proximity page was due, so no published row
was read for adjudication and none could have been written. That coverage is
the table above, `tests/test_listing_update.py`, and section 8 of
`tests/test_fair_crawl.py` — the first armed tick that finds a defining page
due will be the first live exercise of it.
