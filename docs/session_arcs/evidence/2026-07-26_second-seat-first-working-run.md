# PROVENANCE — read this before the excerpts below.
#
# WHAT: the first CI run ON THIS BRANCH in which the second review seat
# (Gemini) actually completed a review — both its lenses returning
# parseable verdicts — rather than hard-failing on an uncallable model.
# The branch qualifier is part of the claim, not a footnote to it: the
# 04:06:50Z floor below is repo-wide and mechanical, but the "earliest
# run after that floor" step is proven from a BRANCH-FILTERED enumeration.
# A repo-wide ordinal would need the unfiltered run list, which is not
# committed here and is therefore not claimed.
#
# WHY THIS FILE EXISTS: a claim ABOUT a run is not evidence OF it. #73 r5
# blocked on exactly that (class: retyped-evidence / false-confidence-gate),
# so the artifact is committed to sit IN the diff a reviewer reads.
#
# CORRECTED AT r6 — TWICE, and both corrections are the reviewer's win.
# The r5 version of this file named job 89754542551 as the first working
# run, unqualified. The r6 OpenAI absence-only lens blocked it as an unproven ORDINAL
# claim (class: missing-ordinal-evidence). Going to prove it DISPROVED it:
#   (1) job 89754542551 was NOT first. Job 89754035048 completed a Gemini
#       review ~7 minutes earlier. The reviewer did not merely catch an
#       unsupported claim; it caught a FALSE one.
#   (2) the r5 file also said "both Gemini lenses ran and returned
#       APPROVE verdicts" as though that were the milestone. On the actual
#       first run one lens returned REQUEST-CHANGES. What the milestone is,
#       precisely, is that both lenses RETURNED PARSEABLE VERDICTS — the
#       seat executes. Their content is a separate question, and conflating
#       "the seat works" with "the seat approved" was the same overclaim in
#       smaller print.
# The ordinal is now PROVEN below rather than asserted.
#
# ============================================================================
# ORDINAL PROOF — why no earlier run could have done this
# ============================================================================
# The proof is mechanical, not an enumeration of logs, because the reviewer
# script is BASE-OWNED: a run's Gemini seat can only complete if the copy of
# tools/adversarial_review.py on `master` AT CHECKOUT TIME names a model the
# project's key can call.
#
# CORRECTED at r12 (self-caught, class unverified-claim-as-fact): this
# paragraph previously attributed the base-ownership to the workflow running
# on `pull_request_target`. That is FALSE for this workflow —
# adversarial-review.yml triggers on plain `pull_request`. Verify:
#     sed -n '/^on:/,/^concurrency:/p' .github/workflows/adversarial-review.yml
# The base-ownership is real but comes from a DIFFERENT mechanism: an
# explicit step fetches the reviewer from the trusted base ref,
#     git show "$TRUSTED_BASE:tools/adversarial_review.py" > /tmp/trusted/...
# and the job runs THAT copy under `python -I`. (`pull_request_target` IS
# used by extraction-eval.yml and brain-held-out-eval.yml, which is where I
# imported the wrong detail from.) The CONCLUSION is unchanged — the model
# constant still comes from master at checkout time — but a proof that names
# the wrong mechanism is not a proof, and stating the right one is the whole
# point of this file.
#
# master's history for that file bounds the window:
#
#   * before 0d16d90 (committed 2026-07-25T20:33:19-05:00 = 07-26T01:33:19Z)
#     — no second seat existed at all; the reviewer was v1, single-lens.
#   * 0d16d90 .. f907a518 — the default was `gemini-2.5-pro`, which this
#     tier no longer serves. Every run in this window hard-failed with
#     HTTP 404 before any verdict was produced (quoted in full in
#     docs/memory/decisions/2026-07-26_red-check-merge-pr72.md).
#   * f907a518 (committed 2026-07-25T23:06:50-05:00 = 07-26T04:06:50Z)
#     — PR #72 merged: a callable model plus the base-owned preflight.
#
# So 04:06:50Z is a hard floor: no run in the repository whose base checkout
# preceded it could have had a completing Gemini seat. Reproduce the floor:
#     git log origin/master --format='%H %cI %s' -- tools/adversarial_review.py
#
# Every adversarial-review run on this branch at or after 04:00Z, from the
# Actions run list (workflow adversarial-review.yml, branch
# claude/onelife-meta-carousel-wu7sh7):
#
#   run 583  id 30187213586  04:05:06Z  head 58314bb0  CANCELLED (evaluator
#                                                       step never ran)
#   run 584  id 30187255366  04:06:38Z  head 58314bb0  <-- FIRST. Job
#            created 04:06:54Z; its checkout ran 04:06:59-04:07:01Z, i.e.
#            9 seconds AFTER the merge landed, so it is the earliest run to
#            pick up a callable base. Preflight OK 04:11:36Z; both Gemini
#            lenses emitted verdicts 04:15:03Z.
#   run 585  id 30187444778  04:13:43Z  head d3a0d1f3  (job 89754542551 —
#            the run r5 wrongly called first; it is the SECOND.)
#   runs 587, 588, 607, 612, 616, 617, 619 — all later still.
#
# Scope stated exactly: "first" is proven for THIS branch. The 04:06:50Z
# floor is repo-wide, so any counterexample would have to be a run on
# another branch started inside the 4-second window between the merge and
# run 584's job creation. None is claimed and none appears in the
# branch-filtered list; a reader who wants the repo-wide form should re-run
# the enumeration without the branch filter.
#
# ============================================================================
# EXCERPT A — THE FIRST WORKING RUN ON THIS BRANCH (the claim's subject)
# ============================================================================
# SOURCE:  GitHub Actions job 89754035048
#          run  https://github.com/schubertsean-ui/onelive/actions/runs/30187255366
#          job  https://github.com/schubertsean-ui/onelive/actions/runs/30187255366/job/89754035048
# HEAD:    58314bb06ec60819785312e82849d6f1fdce2943   (PR #73)
# FETCHED: via the GitHub API job-logs endpoint, pasted verbatim with
#          GitHub's own line timestamps intact. Nothing retyped.
#
# HOW TO VERIFY INDEPENDENTLY (30 seconds, no trust in this file required):
#   1. Open the job URL above.
#   2. Expand the step "Independent evaluator (APPROVE required)".
#   3. Search the log for "SEAT gemini".
#   Expect the two verdict lines reproduced below.

2026-07-26T04:11:36.1701089Z second seat: model taken from the BASE copy = gemini-flash-latest
2026-07-26T04:11:36.9564767Z second seat: PINNED MODEL 'gemini-flash-latest' is advertised AND answered a live generateContent probe — preflight OK
2026-07-26T04:15:03.5589786Z ### SEAT gemini / LENS dataflow-taint: REQUEST-CHANGES
2026-07-26T04:15:03.5590433Z ### BLOCKERS
2026-07-26T04:15:03.5614607Z VERDICT: REQUEST-CHANGES
2026-07-26T04:15:03.5615432Z ### SEAT gemini / LENS spec-vs-contract: APPROVE
2026-07-26T04:15:03.5615936Z ### LENS EVALUATION & PROVOCATIONS
2026-07-26T04:15:03.5642604Z VERDICT: APPROVE
2026-07-26T04:15:03.5642841Z VERDICT: REQUEST-CHANGES

# WHAT EXCERPT A PROVES: both Gemini lenses executed and returned parseable
# verdicts, so the two-family panel runs end to end. It does NOT prove the
# verdicts were correct — a verdict's correctness is never established by
# the fact that it was emitted. Note that one lens BLOCKED here: a working
# seat is one that can say no.
#
# ============================================================================
# EXCERPT B — the run r5 mistakenly called first (kept, relabelled)
# ============================================================================
# SOURCE:  GitHub Actions job 89754542551
#          run  https://github.com/schubertsean-ui/onelive/actions/runs/30187444778
#          job  https://github.com/schubertsean-ui/onelive/actions/runs/30187444778/job/89754542551
# HEAD:    d3a0d1f3c169d4c41dbb0e7235fb7849f08a848e   (PR #73)
# This is the SECOND working run, ~7 minutes after Excerpt A. It is kept
# because it is the round where both Gemini lenses approved, and because
# deleting the excerpt r5 got wrong would erase the correction's subject.

2026-07-26T04:19:50.5527961Z ### SEAT gemini / LENS dataflow-taint: APPROVE
2026-07-26T04:19:50.5528616Z The raw diff and test logs have been evaluated against all repository standards, review disciplines, and session contract requirements.
2026-07-26T04:19:50.5529385Z ### Dataflow Taint Trace
2026-07-26T04:19:50.5530154Z The diff consists entirely of documentation updates (`STATE.md`, `docs/ONE_LIVE_CHANGE_LOG.md`, and `docs/metrics/KAIZEN_LEDGER.md`). No external data paths or executable code sinks are touched.
2026-07-26T04:19:50.5534657Z VERDICT: APPROVE
2026-07-26T04:19:50.5535075Z ### SEAT gemini / LENS spec-vs-contract: APPROVE
2026-07-26T04:19:50.5541010Z No blocking issues or non-blocking issues identified.
2026-07-26T04:19:50.5541462Z VERDICT: APPROVE
2026-07-26T04:19:50.5541736Z VERDICT: REQUEST-CHANGES

# In BOTH excerpts the trailing REQUEST-CHANGES is the PANEL verdict, not a
# Gemini verdict: ANY-lens-red = red, and an OpenAI lens blocked both
# rounds. Both facts belong here — a seat that works and a round that was
# still correctly refused.
