# Decision: the CAPCOG region is a view scope, and the direct-link refusal is repealed (2026-09-01)

**Governing law.** `ONE-LIVE-COVERAGE-LAW.md` (ratified 2026-09-01, in force,
and explicitly superior to CLAUDE.md / STATE.md / any session contract on
scope):

> Austin Tonight is a VIEW. CAPCOG is the TEST LOCALE and a view filter, not
> the map. … Views (picky): /tonight may filter CAPCOG and time. Views must not
> delete catalog rows. Views should say "Showing N of M."

**Founder, verbatim (2026-09-01, Session 2 directive):**

> "Default Tonight view may filter to CAPCOG."
> "Show 'Showing N of M known listings' for the selected time window. M =
> catalog rows in that window. N = rows the current view is showing. If the
> user clears the region filter, M is not CAPCOG-only."
> Must not: "Treat CAPCOG as a catalog delete."

## What changed

1. **Where the boundary is applied.** `web/app/(public)/tonight/page.tsx` used
   to run `filterToCapcog` and forward only the survivors. It now forwards the
   whole window; `FeedApp` applies the scope as the DEFAULT view filter
   (`applyRegionScope`), prints how many rows the scope is holding back, and
   lets the reader clear it (URL: `?region=all`).

2. **The direct-link refusal is REPEALED.** `resolveDetailView` used to return
   a distinct `outside-market` branch (PR #107) and the page rendered "This
   event is outside the Central Texas area 1Live covers, so it isn't one of our
   listings." That sentence asserts a CATALOG fact, and the Coverage Law says
   the opposite: the row is in the catalog, it is simply outside the region the
   default view scopes to. The branch is now a LABEL on the event
   (`{ kind: "event", event, outsideRegion }`) and the page says so plainly.

## What did NOT change (and must not, without a founder ruling)

- The classification itself. `lib/region.ts` still resolves inside / known-outside /
  unrecognised exactly as before, with the same drop-direction rule (a
  known-outside reading anywhere in the row wins) and the same keep-and-count
  discipline (unrecognised is KEPT and counted, never guessed either way).
- The DEFAULT a reader lands on: CAPCOG. The founder's must-do #1 permits the
  default scope, and it is still the default.
- Every trust invariant. The region is a PLACE filter and never a trust one —
  a disputed in-market row renders exactly as before, and a rendered-markup
  test pins that the scope did not become a second, quieter trust filter.

## Why the earlier reasoning does not survive

PR #107's argument was that the feed's filter never links to a San Antonio
event, so a direct link must be refused or the invariant is half-enforced. That
was correct under the old law, where CAPCOG was the market. Under the Coverage
Law the market is not the catalog, so refusing a catalog row on a link the
product itself can now produce would be the defect — and the invariant it was
protecting ("San Antonio does not reach a reader unasked") is intact: the
default view still scopes it out, proven on rendered markup in
`web/app/(public)/tonight/region-view.test.tsx`.

## Retrieval tokens

`region-is-view-scope-not-catalog-delete`, `coverage-law-views-say-n-of-m`.
A view that cannot say what it is holding back is indistinguishable from a
small catalog — the count line, not the filter, is what makes a picky view
honest.
