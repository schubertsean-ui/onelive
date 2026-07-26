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
| Adversarial Review v2 + construction_gate base-freshness rebuild | `tools/adversarial_review.py`, `tools/reviewer_scorecard.py`, `tools/construction_gate.py`, `.github/workflows/adversarial-review.yml` | `0d16d90` (PR #71, 12 rounds) |

M1 trend across the session: **15 → 9 → 3 → 1 → 12** rounds. The last
figure is not a regression in review quality: eleven of those twelve
rounds landed on the reviewer's own upgrade and on a gate proving a
property that turned out to be unprovable offline. The Construction
Loop's Stage 3 gate governed the last two.

## PR #71 — MERGED (no action needed)

`0d16d90` (12 rounds). Adversarial Review v2 shipped: the lens panel
(ANY lens red = red, explicit empty seat, self-printed po seed), the
structured escape hatch, the CLASS sibling mandate, the M9 scorecard,
and the Gemini second-family seat.

**The one thing the next session must check first:** the BASE-owned
reviewer copy is v2 only from this merge onward, so PR #71 itself was
judged by v1. The NEXT pull request is the first the two-family panel
actually runs on — confirm from its job log that both seats fire (the
log prints which mode it runs and the po seed).

The arc also spent five rounds rebuilding `construction_gate`'s
base-freshness proof, ending with: read the remote tip, compare commit
ids, no offline path. CI grants read-only remote access to the validate
step alone via per-process `GIT_CONFIG`.

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
