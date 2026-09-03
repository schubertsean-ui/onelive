# A clean 404 of the defining URL marks the listing gone — founder overrule

**Founder-ratified 2026-09-02.** Verbatim, from the Session Contract #55 ticket:

> Confirmed gone (clean 404 of defining URL, or clean parse that the event is
> absent from that calendar): mark cancelled/moved with evidence; row remains.

## What this overrules

`docs/memory/decisions/2026-09-02_confirmed-check-may-update-listing.md`
resolved the 404 case the other way, under the heading "The 404 reading,
flagged rather than quietly resolved", and said in as many words that it was
"an interpretation the founder should be able to overrule in one line." That
line arrived. This record is the overrule; the earlier record stands as
history, and the code comment in `worker/crawl_state.py` now carries this
reading rather than that one.

The reasoning that lost is worth keeping, because it names the real cost:

> a venue reorganizing its URLs, a CMS migration, and a genuinely cancelled
> show all 404 identically

That is true, and the ruling accepts it knowingly. A 404 is weaker evidence
about a LISTING than a page that still loads and no longer names it.

## What the ruling actually licenses, and what it does not

`may_mark_gone` (worker/crawl_state.py) is True for `verified_absent`, and it
is bounded on every side:

- **`status` only.** `may_update_listing` is still `verified_present`-only. A
  page that is gone cannot state a new start time or a new title, so a 404 can
  never retime or retitle a row.
- **The row stays.** `may_delete_listing` returns False for every input, pinned
  by a test. `cancelled` drops the row from the live feed
  (`web/lib/promoted.ts`, `web/lib/licensed.ts` select
  `status in (scheduled, moved)`) but it remains in the catalog, keeps its
  evidence, is still reachable by direct link, and the detail page says "This
  event has been cancelled." rather than 404-ing.
- **Nothing is one-way.** `cancelled` is a visible state a later check or a
  person can move back.
- **It is the DEFINING door's own 404.** The orchestrator computes the verdict
  from `defining_door`, so a remembered best URL that 404s and then falls back
  to a healthy homepage does not report the page present — and equally, the
  homepage's health does not hide the 404.
- **Re-finding the door still happens.** The fallback and re-discovery the
  earlier record pointed to are unchanged, so a moved calendar re-discovers
  itself and the next clean read can restore the listing.
- **Both doors down is not confirmed absence.** If the fallback ALSO misses,
  the source raises and is isolated as an error — a whole site being down is
  not evidence that an event was cancelled, and nothing is marked.

## The second confirmed-gone shape

"A clean parse that the event is absent from that calendar" is the shape that
carries real same-page evidence, and it is adjudicated in
`worker/listing_update.py`. It carries one guard the founder's text does not
name, added because absence is the only evidence shape here that a page can
manufacture merely by being SHORT: the page's own parsed listings must
BRACKET the missing event in time — something at or before its date and
something at or after it — before its silence counts as a statement. A
calendar showing the next ten shows has said nothing about a show three months
out. An unbracketed absence keeps.

## Status: wired

Unlike the record this overrules, the path is built: `worker/listing_update.py`
adjudicates and writes, `worker/orchestrator.py` calls it for the
event-proximity queue only, and every mutation carries its evidence in the same
transaction as the change.

CORRECTED 2026-09-03 (openai/attacker-smuggle nit, PR #214 r9 — the seat
APPROVED and flagged this as a doc contradiction rather than a defect): this
paragraph said every mutation carries a `candidate_evidence` row AND an
`audit_log` row. That is true of an UPDATE and false of the cancellation this
very record authorises. A 404 has no page and no candidate, so there is nothing
for a candidate_evidence row to cite; the founder ratified `audit_log` plus the
defining URL and the reason as the evidence for a cancellation
(`docs/memory/decisions/2026-09-03_cancellation-evidence-is-the-audit-row.md`),
and inventing a candidate_evidence row with no candidate is exactly what that
ruling forbids. The audit row is written for EVERY mutation; the
candidate_evidence row only where a matched candidate exists to attest.
