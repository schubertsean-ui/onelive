# A confirmed check may update a published listing — never delete it

> **SUPERSEDED IN PART, 2026-09-02.** The section "The 404 reading, flagged
> rather than quietly resolved" below invited a one-line founder overrule and
> got one: a clean 404 of the defining URL is now a CONFIRMED-GONE shape and
> marks the listing (status only, row kept). See
> `2026-09-02_404-of-defining-url-marks-the-listing-gone.md`. Everything else
> in this record still stands, including "Status: encoded, not wired" being
> superseded by fact — the path is built (Session Contract #55).

**Founder-ratified 2026-09-02.** Verbatim:

> Confirmed check MAY update a published listing (time, cancel, postpone,
> title) only with same-page evidence. Unconfirmed = no mutation. Do not
> delete the row from the catalog; mark cancelled/moved and keep evidence.
> Ambiguous parse = keep.

Preceded, same day, by the fail-closed rule this ratifies the other half of:

> If a scheduled check cannot confirm OR cannot disconfirm, make no change to
> the listing (no delete, no cancel, no date edit). Only mutate on confirmed
> same-page evidence. Fetch failure / cap / 429 / parse miss = last good row
> stands.

## What this settles

The event-proximity queue re-reads the page that DEFINES a published event as
the event approaches. That immediately raises the question the two directives
above answer together: when the page comes back different, what may change?

- **Updatable fields:** `start_time`, `end_time`, `status`, `title`
  (`UPDATABLE_LISTING_FIELDS` in `worker/crawl_state.py`). Cancel and postpone
  are `status` values on the existing row — migration 0001's
  `scheduled|cancelled|moved` — which is exactly why there is no delete.
- **Only on `verified_present`.** That is the only verdict with a page behind
  it, and therefore the only one carrying same-page evidence.
- **Never a delete.** No verdict, evidence, or confidence level licenses
  removing a published row (`may_delete_listing` returns False for every
  input, pinned by a test). This agrees with Coverage Law — a legally seen row
  is never dropped — and with the 4-state model, where disputed is shown and
  never hidden.
- **Ambiguous parse = keep.** A page we fetched but could not read cleanly is
  `unverified`, and unverified changes nothing.

## The 404 reading, flagged rather than quietly resolved

The two directives need reading together on one case, and the resolution is an
interpretation the founder should be able to overrule in one line.

A clear 404 on the defining page yields `verified_absent` — the PAGE is
confirmed gone. But "only with same-page evidence" cannot be satisfied by a
404, because there is no page left to carry evidence: a venue reorganizing its
URLs, a CMS migration, and a genuinely cancelled show all 404 identically.

**So a 404 licenses no listing change at all.** What it licenses is re-finding
the door, which the loop already does — the best-URL fallback re-fetches the
registered start URL and re-discovers from there. The case that CAN license a
cancel is a clean parse in which a published event is absent from a page that
still loads; that is same-page evidence, and adjudicating it belongs to the
update path.

## Status: encoded, not wired

`worker/crawl_state.py` carries the vocabulary, the field list, and both
gate functions so the eventual update path has ONE definition to obey rather
than inventing a second. Nothing updates a published event today: the
orchestrator imports no promote path, writes only candidates, and issues no
UPDATE against `event` — pinned structurally by tests in
`tests/test_fair_crawl.py` and `tests/test_crawl_state.py`.

Building the update path is its own ticket. It writes to the published `event`
table, so it is a trust-surface change that needs its own adversarial review,
and it changes the armed cron's runtime, which the founder capped for the
incremental-crawl session ("No second wave after that").
