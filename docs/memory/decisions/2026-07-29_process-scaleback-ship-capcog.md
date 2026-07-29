Founder-ratified 2026-07-29 ("Go — do both, then CAPCOG"): PAUSE the process-facing gates, KEEP the user-facing trust gates, and refocus all effort on shipping live event data — CAPCOG (Austin region) first, then Lexington KY. This breaks the review/re-review cycle that produced 412 harness commits to 83 product commits over two weeks (measured 2026-07-29).

## The decision (plain)

The founder measured the cycle and called it: effort was flowing ~5:1 into
the machinery that checks the work versus the product itself. PRs ran 12–21
adversarial rounds. A two-file docs PR (#91) failed CI on `construction_gate`
alone — pure `[S3:...]` recitation ceremony, zero user protection.

Ratified fix, both levers (founder chose "do both"):

1. **Tame the adversarial reviewer** — scope it to USER/PUBLIC-FACING harm
   only, and collapse the multi-round ceremony. It blocks only: fabricated/
   unverified data on a user surface, AI publishing directly (must go through
   the gate), a disputed event hidden/deleted, auth/RLS fail-open, non-
   parameterized SQL, unvalidated input, broken trust display, a test that
   cannot fail. Internal process (red-class tokens, Kaizen rows, construction
   contracts, session-doc formatting, premortems) is EXPLICITLY out of scope.
   (`tools/adversarial_review.py` SYSTEM_PROMPT + V2_DISCIPLINE.)

2. **Pause the ceremony gates** — `construction_gate` and `kaizen_trends`
   downgraded from blocking to ADVISORY in `tools/validate` (they still RUN
   and print findings; they no longer block a merge).

## What stays BLOCKING (the user-facing invariants — unchanged)

`trust_gate` (AI-never-publishes, RLS fail-closed, no-pay-to-rank), the full
`pytest` suite, `lint`, `deferral_scan`. Disputed-shown and no-fabricated-data
are enforced by trust_gate + tests. **No trust invariant is relaxed.** This is
a scope+ceremony change, not a safety change.

## The bootstrap catch (honest)

This change weakens gate custody, which the CURRENT base-owned reviewer is
built to hard-block — so the `adversarial-review` check on the PR carrying
this change will (correctly) go RED, flagging a founder-crucial gate change.
That red is the system working: gate tuning is the founder's call by charter,
so the FOUNDER merges this PR. The tamed reviewer + advisory gates take effect
for every PR AFTER it lands on master.

## Reversal

One commit: restore `run_check` for the two gates in `tools/validate` and
revert the `adversarial_review.py` prompt. If live quality dips once we have a
site in hand, we turn a gate back on — empirically, per the founder's "we see
what we get" directive.

## Next (the actual product)

CAPCOG live behind the Clerk stealth gate: licensed importers (Ticketmaster +
SeatGeek, deterministic/confirmed-tier, no AI) for the ticketed spine + the
crawl/AI pipeline for the long tail → real events → production Vercel deploy →
allowlist testers → founder go/no-go. Then replicate for Lexington KY (new
source catalog + geo config, same pipeline).
