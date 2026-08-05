# Decision: one session with multiple agents; the parallel work streams merge (2026-08-06, founder-directed)

**Founder, verbatim:**

> "Let's move to 1 session with multiple agents.
> Merge them together."

## Context that produced it

Two Claude Code sessions were running the same mission in parallel against the
same repository:

- `session_01J53YyFWFhNNdfxJd6hRKEY` (this one) — PR #191.
- `session_01HZnpc5yC6GhDi19fLvWpHs` — PRs #187, #189, #190, #192, #193, #194,
  #195.

The cost of that was surfaced to the founder in the preceding report and is
now the reason for this ruling:

- **#191 and #193 rewrite the same region of `worker/gating.py`** from the same
  founder directive, disagreeing on exactly one class (`local_media`), with two
  separate decision records written for one ruling.
- **#189 and #191 merge CLEANLY into a doctrine inversion** — git interleaves
  their two date-recovery blocks into a sequence, and #191's block deletes the
  entries #189's block is guarded on, so an *inferred* year silently beats the
  source site's own machine-declared date. A conflict search by filename misses
  this entirely.
- **#189 and #195 are two independent implementations of pagination**, written
  without reference to each other.
- Both sessions dispatched ingest smoke runs into the single `ingest`
  concurrency group, cancelling each other's runs — two of this session's
  arming re-binds died that way, each costing a paid run and a CI round.

## The ruling, as implemented

**ONE session drives the mission. Parallelism comes from subagents inside it,
never from a second session.** Concurrency that a single session can see and
order is an asset; concurrency between sessions that cannot see each other
produces duplicate decision records, competing implementations of one feature,
and silent doctrine inversions.

**"Merge them together"** is executed as a single integration branch off master
that carries every parallel branch's work, with the conflicts resolved against
the founder rulings already on record — not by picking a session's version:

- **Gating** resolves to the **UNION** of both class sets. Both lists came from
  founder rulings; taking both implements both. Neither PR alone is complete —
  #193 omits the venue-type calendars (~58 live sources), #191 omits
  `local_media` and `community` (~84).
- **Date recovery** resolves to the founder's stated order from #189's record —
  the source site's own declared date first, inference LAST — regardless of what
  a textual merge produces.
- **Pagination** keeps one implementation and drops the other.

## What the consolidation ALSO carries, and why it is the point

The integration is not only a merge. The investigation recorded in
`docs/ops/PATH_TO_THOUSANDS.md` found that **none of the eight PRs fixes the
reason discovered events are invisible** (R-084): the trust gate is fed the same
instant in two string forms and escalates every dated candidate, while the feed
query drops every dateless one. Consolidating without that fix would merge eight
branches and change nothing a user can see. The root-cause fixes land in the
same integration.

## Custody

Unchanged. This is a repo-operations and merge-order ruling; it moves no gate,
threshold, or publication path. The union gating set is the application of two
existing founder rulings, not a new relaxation — and the integration still
merges only on evaluator APPROVE with every required check green, per the
standing protocol.
