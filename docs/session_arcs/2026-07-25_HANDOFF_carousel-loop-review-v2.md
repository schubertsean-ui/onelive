# HANDOFF 2026-07-25 → next session — carousel engine, Construction Loop, Adversarial Review v2

One-line summary: three arcs MERGED to master (carousel engine, the
founder-ratified Construction Loop with its blocking Stage 3 gate, the v1
launch decks) and ONE arc IN FLIGHT (PR #71, Adversarial Review v2). Read
this file after `python tools/session_reconcile.py`; it is the fastest
path to current state. Disk is truth — nothing from the prior session's
chat transfers.

## What is MERGED on master (no action needed)

| What | Where | Merge |
|---|---|---|
| Meta carousel engine (trust-custodied, listicle canon, learning loop, GEO bundle) | `social/carousel/` | `5481c15` (PR #65, 15 rounds) |
| Construction Loop canon + `construction_gate` (blocking Stage 3 retrieval) + `RED_CLASSES.md` | `docs/skills/construction_loop.md`, `tools/construction_gate.py`, `docs/memory/RED_CLASSES.md`, CLAUDE.md item 4 | `d4f4bc9` (PR #67, 9 rounds) |
| V1 launch decks (founder-reviewed creative pinned, golden-snapshot drift-proof) | `social/carousel/launch.py`, `tests/golden/carousel_launch_v1.json` | `ec91a81` (PR #69, 3 rounds) |
| Close records for #69 | STATE/Kaizen | `4ebbd88` (PR #70, 1 round) |

M1 trend across the session: **15 → 9 → 3 → 1** rounds. The Construction
Loop's Stage 3 gate governed the last two.

## What is IN FLIGHT — PR #71 (Adversarial Review v2)

Branch `claude/onelife-meta-carousel-wu7sh7`; contract = STATE.md
**Session Contract #26** (A3 form, premortem, `[S3:…]` citations already
written). Draft PR: https://github.com/schubertsean-ui/onelive/pull/71

SHIPPED in the PR, all tested (docs/TESTS.md owns the per-file counts —
this document deliberately carries NO numbers, because a count copied
into prose drifts the moment a test is added; #71 r6/r10/r11 each spent a
nit on exactly that drift):
- `tools/adversarial_review.py` — lens PANEL: per seat a forced method
  lens + a po-seeded lens (OpenAI: attacker-smuggle, absence-only;
  Gemini: dataflow-taint, spec-vs-contract). ANY lens red = red;
  unparseable = hard fail; absent seat key = EXPLICIT printed empty seat.
  Structured escape hatch in the prompt (invariants MUST block any round;
  post-r1 classes carry token + why-not-findable-earlier) + CLASS sibling
  enumeration mandate.
- `tools/reviewer_scorecard.py` — M9: round-1 recall, sibling-misses,
  novelty, derived mechanically from the ledger; ADVISORY in validate.
- Workflow wiring with FEATURE DETECTION (see gotchas below).
- Docs: `docs/skills/adversarial_review_v2.md`,
  `docs/memory/decisions/2026-07-25_adversarial-review-v2.md` (founder
  verbatims: escape hatch, metrics, second seat, forcing functions, po).

STATE at handoff: trust-gate GREEN on the pre-fix head; the review gate
died twice on SELF-INFLICTED CI issues (both fixed, both class-indexed —
see gotchas). The next run is the first true two-family panel run (the
founder minted `GEMINI_API_KEY` on 2026-07-25).

## The next session's job, in order

1. `python tools/session_reconcile.py`, then read STATE.md Contract #26.
2. Check PR #71's checks. If adversarial-review is red, pull the job log,
   adopt findings MINIMALLY (scope frozen — this PR has already absorbed
   two self-inflicted rounds), run
   `bash tools/validate --allow-skips > /tmp/v.log 2>&1` and check the
   exit code EXPLICITLY (never pipe — `pushed-on-red` class), satisfy any
   `construction_gate` `[S3:…]` demands, commit, push.
3. On APPROVE + trust-gate green: `update_pull_request draft:false`, then
   squash-merge SILENTLY (founder no-notify directive, decision record
   `2026-07-25_silent-merge-directive.md`). Vercel is NOT a required check.
4. After merge: close Contract #26 in STATE.md with the SHA + a Kaizen
   merged-PR row (M1 = rounds), and verify the panel actually ran
   two-family on the NEXT PR (the base copy is v2 only after this merge).

## Gotchas this session paid for (all class-indexed in RED_CLASSES.md)

- `stale-base-widens-range` — a stale `origin/master` widens the local
  diff range so `construction_gate` can pass locally what CI fails.
  `tools/validate` now always refreshes the base ref first.
- `workflow-tool-version-skew` — CI runs the BASE-owned reviewer copy, so
  a PR adding new CLI flags must FEATURE-DETECT them (grep the trusted
  copy's `--help`) or the gate dies at exit 2. Fixed in the workflow.
- `pushed-on-red` — piping validate's output eats its exit code. Redirect
  to a file and test `$?` explicitly.
- Conflicted PRs (`mergeable_state: dirty`) receive NO `pull_request` CI
  runs at all. If gates are absent on two consecutive checks, probe
  `pull_request_read get` immediately (`stalled-state-needs-active-diagnosis`).
- Squash-merging a branch and then continuing on it creates a conflict
  with the squashed twin — merge master back in before pushing more.

## Founder-crucial queue (never agent decisions; steps live in TODOS)

1. Meta credentials (`META_ACCESS_TOKEN`, `META_IG_USER_ID`,
   `META_FB_PAGE_ID`) — the R-026 trigger; unlocks the posting client +
   Insights importer. THE blocker for live carousels.
2. `ONELIVE_APPROVAL_KEY` — founder-minted, ≥32 chars varied, Vercel
   **Production only**; signs carousel approvals.
3. Posting posture ratification (recommended: launch at L0, founder
   approves each post; cadence 1–2/day, hard cap 2).
4. DONE 2026-07-25: Vercel Clerk key (Preview green), `GEMINI_API_KEY`
   (second reviewer seat).

## Open records / next builds

- R-029: green-example retrieval (Stage 3's second half) mechanizes at
  the Brain 1B build — its recall tool becomes the green matcher.
- R-026/R-027/R-028: posting boundary, cron Sentinel, asymmetric
  signatures — all bound to the Meta-credential trigger.
- TODOS P3: `social/carousel` documentation-only stabilization pass.
