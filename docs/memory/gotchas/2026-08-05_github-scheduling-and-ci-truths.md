# Gotcha: four GitHub Actions truths that cost us cycles tonight

**Date:** 2026-08-05 · **Session:** the completion session (Contract #43).

1. **Input validation runs against the DEFAULT branch's workflow copy.** A
   `workflow_dispatch` choice option added on a PR branch is NOT dispatchable
   until the file with the option is on the ref you dispatch — and a step
   gated on `inputs.provider == 'x'` is unreachable if `x` is missing from
   the choice list in the same file (found on PR #178: the eventbrite-events
   step was undispatched-able).
2. **`rerun_failed_jobs` replays the FROZEN merge ref.** A PR check that
   failed against a stale base re-fails on rerun even after the base is
   fixed — except checks that fetch live state themselves (staleness_check
   fetches origin/master, so IT heals on rerun; the arming binding diffs the
   checkout, so it does NOT). To re-run against a new base, update the
   branch (new merge commit) or push.
3. **A `concurrency:` group holds ONE pending run.** Queueing four dispatches
   back-to-back silently cancels the middle ones (`cancelled`, not failed) —
   dispatch serially, confirming each starts, or accept re-dispatching.
4. **A docs-only squash merge that carries no STATE.md touch re-opens
   staleness drift repo-wide** (drift is measured from master's last
   STATE-touching commit). Every PR carries its STATE rollup line, or the
   merge is followed immediately by the records-only direct commit
   (bfbe761/5d96264/d9b0e50 precedent). Kaizen class:
   `docs-only-merge-owes-state-line`.

**Retrieval tokens:** `input-validation-default-branch`, `frozen-merge-ref`,
`concurrency-queue-cancel`, `docs-only-merge-owes-state-line`.
