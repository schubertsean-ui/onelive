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
was learned). Read the two "yes" rows against the thirteen "no" rows: the
default is no mutation, and confirmation is the exception that has to be
earned.

```
event                                                | check result | mutated? | why
-----------------------------------------------------+--------------+----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------
Nightjar — page moved it to 3am                      | present      | yes      | confirmed same-page change, gate PASS on that listing: start_time
Nightjar — page renamed it                           | present      | yes      | confirmed same-page change, gate PASS on that listing: title
Nightjar — page unchanged                            | present      | no       | the page still says exactly what we published — no change
Nightjar — page dropped its end time                 | present      | no       | the page still says exactly what we published — no change
Nightjar — moved, but the gate declined that listing | present      | no       | the page states a change, but the trust gate did not PASS that listing's own evidence — last good row stands
Nightjar — two listings match it                     | present      | no       | 2 listings on the page match this row on title or time — ambiguous; last good row stands
Nightjar — absent, page brackets its date            | present      | yes      | absent from a clean parse of the page that defines it, and the page's own listings bracket its date — confirmed gone; marked cancelled, row kept with its evidence
Nightjar — absent, calendar stops before its date    | present      | no       | not on the page, but the page's own listings do not reach this date — a short calendar has not said this event is gone; last good row stands
Nightjar — page loaded but listed nothing            | present      | no       | page verified but it produced no listings this read — nothing to compare; last good row stands
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
| absent, page brackets its date | The page still loads, still lists shows both before and after this date, and no longer names this one. That is same-page evidence of absence. Writes `status='cancelled'`; the row is KEPT. |
| defining page 404 | The founder's 2026-09-02 overrule (`docs/memory/decisions/2026-09-02_404-of-defining-url-marks-the-listing-gone.md`). Writes `status='cancelled'` and nothing else — a page that is gone cannot state a new time or title. The row is KEPT. |

## Reading the thirteen refusals

Three of them are the ones worth arguing about, because each is a case where
something DID change and the loop still refused:

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

## What no row can do

No verdict, no evidence and no confidence level deletes a published row.
`worker.crawl_state.may_delete_listing` returns False for every input
including ones nobody has written yet, `worker/listing_update.py` contains no
`DELETE` and no `INSERT INTO event`, and both facts are pinned structurally
rather than by prose.

## The live re-bind run, and what it does not show

Founder-authorized dry smoke, run
[33696784882](https://github.com/schubertsean-ui/onelive/actions/runs/33696784882)
on head `6231147` — success, 75.4s, 2 sources, 29 candidates, $0.2457.
Recorded in full in `docs/evidence/ARMING_SMOKE_RUN.json`.

Its first line is the switch resolving:

```
listing-update writer DISABLED for this run (dry): no published row can be
updated or marked, whatever any page says.
```

and its counters agree — `'listings_updated': 0, 'listings_marked_gone': 0`.

**Those are two different facts and only one of them is evidence.** The
DISABLED line proves the kill switch worked: the dispatched word `dry` reached
the shell case and set the mutation budget to 0. The zero counters prove
nothing on their own, because the same tick reported `0 event-proximity
page(s)` due — a tick with no defining page to re-read would have printed zeros
whether the writer was armed or not.

What the run *does* certify about this PR's code, beyond "the runtime loads
it": the R-091(a) tightening does not break the ordinary path. Both sources
report `verified? present`, and under the new rule that column can only read
`present` when the trust gate PASSED the page. Both did
(`decision=ready_to_promote`), so the stricter verdict is exercised against
live pages rather than only against fixtures.

What it does **not** show: the listing-update path acting on real data. No
published row was read for adjudication and none could have been written. That
coverage is the table above, `tests/test_listing_update.py`, and section 8 of
`tests/test_fair_crawl.py` — and the first armed tick that finds an
event-proximity page due will be the first live exercise of it.
