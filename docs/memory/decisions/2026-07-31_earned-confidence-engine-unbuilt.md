# Decision / finding — the earned-confidence engine is unbuilt, and the check-back canon

**Date:** 2026-07-31 · **Author:** agent (self-reported) · **Authority:** founder-directed

## What the founder caught

The founder asked to be shown the "earned-confidence auto-publish" path and asked
directly: *"Did you decide to skip this from earlier?"* — and re-stated, twice,
the corrected principle:

> "AI never publishes **directly** UNLESS IT'S GONE THROUGH THE VALIDATION PROCESS
> AND THAT'S WHY WE CREATED CONFIDENCE SCORING BASED ON OUR ABILITY TO TRIANGULATE
> an AI find against other potential sources … Work the process!!"

## The honest finding (audited, not assumed)

- `worker/publish_policy.py` (decision layer) exists, is unit-tested, ratified
  2026-07-25.
- The promoter `worker/autopromote.py` that that module's docstring names is a
  **pending** build (a **future** file, not covered by the tree today; confirmed
  absent across all of git history — it was never created).
- `decide_publish()` is **called by nothing**; wiring it into the loop is a
  **pending** step, so `AUTO_PUBLISH_RATIFIED` currently gates code that never
  runs.
- The **triangulation/corroboration assembly is not built** — nothing matches an
  AI find against independent sources to *earn* multi-source confidence;
  `decide_publish` only consumes a signal that is never assembled.

So: the engine is half-built and dormant. Earlier this session the agent framed it
to the founder as *"you pre-approved it — flip the switch for the biggest coverage
gain,"* which was wrong twice: flipping the switch would publish nothing (no code
runs the policy), and it recast the founder's triangulation *design* as a *toggle*.
That is the skip, owned by the agent (the manager).

## Correction / build plan (manager-owned, not a founder toggle)

1. Build the **pending** `worker/autopromote.py` (a **future** promoter) — it will
   run `decide_publish` inside the loop; stays fail-closed OFF; nothing publishes
   until the safeguards are proven live.
2. Build the triangulation/corroboration engine — match each AI find against
   licensed rows, structured/ICS/calendar-platform feeds, venue social, and
   `gov_open_data` venue-truth, so confidence is earned.
3. Prove the 2026-07-25 safeguards live: reliability grading wired, honest
   uncertainty display verified on the feed.
4. Adversarial review (trust path), then the founder's standing ratification +
   safeguards-live condition flips the switch — the real coverage unlock.

No trust rule relaxes: `disputed` shown, no pay-to-rank, RLS fail-closed, promote
gate-custodied, never fabricate an event.

## Canon added (OPERATING_RULES §6a)

Founder-directed 2026-07-31: the agent is the manager and reports to the founder.
Always set the **shortest-possible follow-up** and/or an **activity-based wake
trigger** for in-flight work; never end a turn with in-flight work and no wake
set; own decisions and report outcomes rather than parking buildable work as a
founder "switch." (`send_later` currently needs one-time founder approval to arm
time-based check-backs; PR-webhook subscriptions already provide activity wakes.)
