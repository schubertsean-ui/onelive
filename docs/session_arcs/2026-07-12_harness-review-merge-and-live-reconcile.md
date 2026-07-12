# Session Arc — 2026-07-12 — Harness Cross-Model Review, PR #8 Merge, and Live-State Reconcile

- **Session focus:** Run the world-class process on PR #8 (the agentic-harness
  buildout that existed only as an unreviewed parallel branch): cross-model
  review it, fix every finding, get it green, and merge to master. Then
  determine — honestly, against verified ground truth — what "OneLive live"
  actually requires and how far it can be advanced from this sandbox.
- **Status at close:** PR #8 REVIEWED, all findings fixed with regression tests,
  and MERGED to master (HEAD `a0b3724`). The `validate` gate's founding
  anti-pattern (SKIP/ADVISORY reading as PASS) is fixed in the gate itself.
  "OneLive live" is NOT achievable from this sandbox this session — it depends
  on unmerged PR #7 work and on 3 auth/Next-15 commits that only exist on the
  user's old sandbox and were never pushed. Documented, not faked.

## Ground-truth snapshot (reconciliation result, verified)
| Dimension | Verified state |
|---|---|
| Repo (branch HEAD) | `a0b3724` on `master` (PR #8 squash-merge) |
| PRs | merged: #1 #2 #3 #5 #6 #8; open: #4, #7 (verified via `gh`) |
| Migrations applied (live) | 9 — 0001-0007 + 0009 + `source_geo_coverage` (via Supabase connector) |
| DB data (row counts) | `source` = 230; `event`/`event_candidate`/`candidate_evidence` = 0 |
| Services | GitHub / Supabase / Vercel / Clerk connected (unchanged) |
| Test suite | 127 passed / 27 skipped (was 120/27) |

## Decisions (what + why + tradeoffs)
- **Cross-model review used GPT-5.5 subagents with two personas** (security +
  domain-truth-and-trust) — Why: PR #8's code was written by Claude; a genuine
  review must come from a different model. Tradeoff: two focused personas, not
  all six, since the diff was tooling + docstring/import-reorder only.
- **`validate` SKIP/ADVISORY now => INCOMPLETE + exit 2, gated behind
  `--allow-skips`** — Why: the project's founding rule (§1) is "couldn't verify
  must not look like passed", and that anti-pattern was living in the enforcement
  gate itself (it printed `RESULT: PASS` + exit 0 on skips). Tradeoff: routine
  runs now need `--allow-skips` while visual_regression can't run headless; the
  flag makes the acknowledgement explicit and logged rather than silent.
- **`visual_regression` capture switched from `shell=True` to shlex+argv
  (shell=False) + stderr redaction** — Why: a formatted `{url}`/`{out}` command
  under a shell is a command-injection hole, and a capture URL can carry a signed
  token. Tradeoff: none material; `{url}`/`{out}` still substitute as whole argv
  elements, and embedded-placeholder tokens (`--out={out}`) still work.
- **Injection + redaction tests are NOT `@pytest.mark.visual`** — Why: the whole
  visual test module is opt-in (needs a booted app), but these are pure-logic
  security invariants that must run in the DEFAULT gate. Hiding a security
  regression behind `-m visual` would itself be the "looks covered but isn't"
  smell. Put them in `tests/test_visual_regression_security.py`.
- **GAP 1 (azp/CSRF) reported as BLOCKED, not closed** — Why: it targets
  `api/clerk_auth.py`, which does not exist on master or ANY remote branch. It
  lives only in the user's unpushed old-sandbox commits. Fabricating a fix
  against an absent file would be the exact §1 violation the harness prevents.
- **"OneLive live" reported as not-achievable-from-here, with the real critical
  path written down** (`LIVE_READINESS.md`) — Why: honesty over theatre. The two
  things that make it live (real ingestion run to create events; the auth gate +
  Next 15 upgrade) depend on unmerged #7 and unpushed local commits.

## Findings (verified, not assumed)
- **No P0 blockers in PR #8.** App-code diff (worker/ai/api) independently
  confirmed to be docstring + import-reordering ONLY — zero behavioral change to
  auth/gating/promotion.
- **P1 (both reviewers):** `validate` silent-pass — fixed.
- **P1:** `visual_regression` shell-injection — fixed.
- **P2s:** `agent_review` arbitrary/out-of-repo/secret file disclosure; hook
  staging filename handling; `commit_sweep` empty-range exit 0; `test_audit`
  mock-detection docstring overclaimed patch()-created mocks — all fixed.
- **Live DB (verified via connector):** the RLS migrations 0006/0007 that older
  notes called "pending" are ALREADY APPLIED; a 9th migration
  (`source_geo_coverage`) is live. `source` = 230, but events are still 0.
- **The arc's Clerk stealth-gate commits (f970e3a, 1a9728d, 35c5605) are absent
  from the remote entirely** — remote `feat/orchestrator-harness` = `3258a57`,
  not the arc's `1a9728d`. Confirms the KNOWN CONSTRAINT: never pushed.
- **`worker/run_once.py` on master is a STUB smoke test** (hardcoded text, stub
  provider), not a real orchestrator. The real one is on unmerged PR #7.

## Documents / artifacts
| Artifact | Location | Note |
|---|---|---|
| Review findings | `/workspace/review_security_findings.md`, `review_trust_findings.md` | cross-model, GPT-5.5 |
| Fix commit | `bd1bcdf` on `feat/agentic-harness-buildout` (squashed into `a0b3724`) | 8 files + 1 new test file |
| Gate fix | `tools/validate` | SKIP/ADVISORY -> INCOMPLETE/exit 2; `--allow-skips` |
| Injection fix | `tools/visual_regression.py` | shlex+argv, shell=False, `_redact()` |
| P2 fixes | `tools/agent_review`, `tools/install_hooks.sh`, `tools/commit_sweep.py`, `tools/test_audit.py` | containment/denylist, NUL-safe, empty-range=2, patch()-mocks |
| New security tests | `tests/test_visual_regression_security.py` | run in default gate |
| Live readiness assessment | `LIVE_READINESS.md` (repo root) | what "live" needs + why it's blocked here |

## Open threads / next steps (ordered — the real critical path to live)
1. **Push the 3 local Clerk/Next-15 commits** (f970e3a, 1a9728d, 35c5605) from
   the OLD sandbox to a branch. Only the user can do this.
2. **Land PR #7** (orchestrator + /tonight feed) into master, after its own
   cross-model review.
3. **Close GAP 1** on `api/clerk_auth.py` (azp validation vs known origins +
   tests) once that file is actually on master.
4. **Run the real orchestrator** over the 230 sources to populate
   `event_candidate` -> gate -> promote to `event` (the thing that makes the
   feed non-empty).
5. **Deploy web + API to Vercel**; verify `/tonight` renders real, gated events.

## Drift corrected this session
- STATE.md GROUND_TRUTH block said PR #6 `open`; live is `merged` (material
  contradiction). Resolved the block to verified `gh` truth (added #6=merged,
  #7=open, #8=merged; branch=master, head=a0b3724), then re-ran
  `session_reconcile.py --heal` which refreshed it clean. DB facts (9 migrations,
  source=230, events=0) verified via the Supabase connector and recorded in the
  prose Reality-check (the script reports DB UNVERIFIED because no
  `ONELIVE_DB_DSN` is set in the sandbox — the connector is the verification path).
