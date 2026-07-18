# Point-in-time ledger storage — design v0 (groundwork, not build authorization)

**Status:** design only (Session Contract #16, renumbered from #7). Reviewed through the gate; built
only after founder go.

## The one invariant everything serves

**As-of-known-when correctness.** Any query must be answerable "as of date D
using only what was knowable at D." This is what makes the ledger usable as
backtest input (multibagger's yfinance-ban standard), safe as evidence
(verdicts cite what was known when), and impossible to back-fill dishonestly
by a competitor. It is enforced structurally, not by policy:

1. **Append-only event log.** Three record types, no updates, no deletes:
   `claim_recorded` (Claim Schema v0), `lifecycle_event` (state + 4-state
   confidence + evidence), `source_retrieved` (raw-document custody record:
   URL, retrieval time, content hash — verbatim text stored internally only).
2. **Two timestamps on everything — "when it happened" vs "when WE learned
   it" — and reads ALWAYS key on the second.** For claims: `published_at`
   (what the source says) vs `retrieved_at` (when we saw it). For lifecycle
   events (updated per evaluator r22, which caught the original text of this
   section implemented as time-travel): `observed_at` (when the outcome
   occurred/was stated) vs `recorded_at` (when the system learned it) —
   as-of reads key on `recorded_at`, NEVER `observed_at`, so a
   late-discovered outcome is invisible at times before its discovery. The
   schema validator rejects published_at > retrieved_at (time-incoherence)
   and a lifecycle `recorded_at` earlier than its evidence's retrieval; the
   store additionally refuses a lifecycle event knowable before the claim it
   judges (r23).
3. **Corrections are events.** A wrong extraction is corrected by appending a
   superseding event that references the superseded one — same event type,
   same claim, never with an earlier knowledge horizon than the record it
   corrects (r23) — the mistake stays
   visible with its correction attached (disputed-shown-never-hidden applied
   to ourselves; identical to the additive-verdict rule the research PR
   enforced on its own appendices).

## Keys and identity

- **Entity:** LEI primary (FDTA-mandated cross-agency key, effective Oct
  2026), CIK + ticker secondary; entity aliases are events too (renames,
  re-tickers, mergers preserve history instead of breaking it).
- **Claim:** content-derived stable id (hash of entity + normalized claim
  fields + first provenance) so re-ingestion is idempotent.
- **Executive attribution (H2, phase 2):** officers referenced by their own
  records so credibility history survives company changes.

## Materialized views (rebuildable, never authoritative)

The event log is the truth; everything user-facing is a projection that can be
rebuilt from scratch: current-state-per-claim, per-entity timeline, promise
maturity calendar (H9: due dates ticking), overdue/silence alerts (H8:
expected-cadence model vs observed), integrity metrics (H16, gated on
precision). Projections carry the event-log offset they were built to, so a
stale view is detectable, not silent.

## Deliberately NOT decided here (build-time decisions, gated)

Engine choice (Postgres event table vs log store), hosting, retention/cost
envelope, and anything that costs money or creates a service — founder-crucial
or R-016-gated. This design constrains any implementation to the invariant; it
does not pick vendors.
