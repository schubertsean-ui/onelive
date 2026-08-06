# 2026-08-06 — Merge freeze waived for PR #193; backlog drained on merge

## Founder directive (verbatim)

> Do Option 1 + the speed rule

Answering a written choice of four options. Option 1 was stated as:

> **1. Merge #193 now** — waive the merge freeze for this one PR.
> It's built, tested, and approved. Events start flowing within the hour.
> *Cost:* it moves the codebase under #189, so #189 needs about 15 minutes of
> rework. No risk to the site.

and the speed lever as:

> the hourly publisher does 200 at a time. If thousands are parked, I can run
> it manually with a higher ceiling and drain it in one go instead of over
> several hours.

## What was authorised

1. **The standing merge freeze is waived for PR #193 specifically.** The
   freeze ("freeze all other merges while an exam-bound PR is open") remains
   in force for every other PR; #189 is still exam-bound and still open.
2. **A manual autopromote pass with a raised ceiling**, to drain the parked
   backlog in one go rather than at 200/hour.

## Why the founder was asked rather than told

Waiving the freeze is the founder's call, not the agent's, for a concrete
reason on the record: master moving under an exam-bound PR is not
hypothetical — PR #188 merged mid-review earlier in this session and the
evaluator refused the evidence with *"the golden-exam log does not prove
execution against the current base"*, costing a full re-verification cycle.
The freeze exists because of that. Trading it away is a scope decision.

## What this does NOT change

- The trust invariant is untouched. #193 does not lower a gate; it applies the
  founder's 2026-08-05 first-party ruling to the gate, which had never
  received it (decision record
  `2026-08-05_first-party-promotes-on-one-source.md`). Third-party
  republishers still require corroboration, and an unrecognised class still
  holds — fail-closed in both directions.
- Publication is still gate-custodied. Nothing publishes that the gate has not
  passed; the gate simply now agrees with the publish policy about what your
  own ruling means.
- The freeze itself still stands for #189, #192, #194, #195, #187, #196.

## The cost, accepted knowingly

#189 will need its base re-merged and a fresh verification run once master
moves. That is roughly fifteen minutes of agent work and no product risk. It
was presented as the price of Option 1 and the founder chose it with that
stated.
