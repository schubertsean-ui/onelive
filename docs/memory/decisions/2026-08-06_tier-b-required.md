# 2026-08-06 — Tier B fields are REQUIRED, not best-effort

## Founder directive (verbatim)

> Tier b is required
> Add it
> Do your job.

## What was wrong

`lab/PLAN.md` §3a split the target schema into three tiers and marked Tier B
"REQUIRED WHERE THE SOURCE STATES IT" with a 90% threshold, against Tier A's
98%. That framing let a whole class of fields — performer, door time, age
restriction, on-sale status, **event status (cancelled/postponed)**, organizer,
venue geo/url/phone, series name, and specials — be treated as nice-to-have.

The founder rejected the split. They are required.

## The ruling

1. Tier B is **merged into REQUIRED** as "required group 2", at the **same
   standard and the same ≥98% threshold** as group 1.
2. A source that publishes one of these fields and loses it in extraction is a
   **failure of the run**, not a deduction.
3. `event_status` gains its own absolute acceptance criterion: cancelled and
   postponed events must be marked correctly **100%** of the time and must
   never render as live.
4. The tier labels A/B/C are retired in favour of "required group 1",
   "required group 2", "analysis", so nothing reads as optional again.

## Why the founder was right

The fields dismissed as Tier B are the ones that make a listing usable rather
than merely present: what time the doors open, whether a 19-year-old can get
in, whether tickets are still on sale, whether the show is still happening, and
what the venue is actually offering that night. A product that lists an event
without them is a calendar, not a guide.

`event_status` is the sharpest case. It is discarded today at
`worker/segment.py:252` along with the rest of the JSON-LD payload, which means
a cancelled show stays on the site reading as live. That is a worse trust
failure than never listing the event at all — and it was sitting in a tier
marked optional.

## The one thing this does NOT change

A field is never invented. "Required" means we must capture what the source
publishes; it does not mean manufacturing a value when the source is silent. A
silent source yields an honest null. A stated value we drop is a defect. This
is the standing trust invariant and the directive does not touch it.

## Where this binds

- `lab/PLAN.md` §3a (target schema) and §7 (acceptance criteria).
- `lab/EXTERNAL_AI_BRIEF.md` §4a and the paste-ready prompt.
- Any adoption into `worker/ai_models.py`, the candidate table, and the
  promote INSERT must carry the full required list, both groups.
