# Session Arc — 2026-07-11 — Agentic-Harness Buildout

- **Session focus:** Audit OneLive against two external agentic frameworks (Jamon
  Holmgren's 18-item setup; the 20-step Loop Engineering roadmap) and build out
  every missing/partial piece to a world-class bar.
- **Status at close:** All identified harness gaps implemented, tested, committed
  on `feat/agentic-harness-buildout`. Full validate gate green (7 PASS, 1
  SKIP-loud for visual regression which needs a booted app). One known world-class
  gap deliberately left for a follow-up: model-cost routing (Loop step 17).

## Ground-truth snapshot (reconciliation result)
| Dimension | Verified state |
|---|---|
| Repo (branch HEAD) | `f9d9910` on `feat/agentic-harness-buildout` |
| PRs | this branch's PR opened this session (see STATE.md) |
| Migrations applied (live) | unchanged this session (no schema work) |
| DB data (row counts) | unchanged (no pipeline run this session) |
| Services | GitHub / Supabase / Vercel / Clerk connected (unchanged) |

## Decisions (what + why + tradeoffs)
- **Custom linter is pure-stdlib, not ruff** — Why: it must always run in any
  sandbox regardless of network/pip. Tradeoff: reimplements a few checks ruff would
  give; mitigated by keeping it focused on OneLive-specific rules (swallowed errors,
  print-for-errors, missing docstrings, TODO/FIXME) that encode §1 of OPERATING_RULES.
- **`tools/validate` treats SKIP as not-green** — Why: "couldn't verify" must never
  read as "passed" (the project's founding anti-pattern). Tradeoff: an all-green run
  with a skip still prints a caveat and asks the operator to resolve it.
- **Night-shift harness codified as a doc/skill, not a runner script** — Why: the
  core dev loop is deliberately human-checkpointed (OPERATING_RULES §4); the skill
  defines the orchestration + layered exits so a scheduled runner can be added later
  without re-deriving the safety model. Tradeoff: not yet a literal cron.
- **Model-cost routing (Loop step 17) explicitly deferred** — Why: it's the one
  world-class gap the buildout didn't close; flagged in night_shift.md §4 and
  AGENT_FEEDBACK so it isn't silently lost.

## Findings (verified, not assumed)
- Existing harness scored A-tier on the trust-defining half of loop engineering
  (deterministic verifier `trust_gate.py`, measurable done, self-healing state,
  human-checkpoint-before-irreversible) and C-tier only on scale/automation.
- `commit_sweep.py` flagged TODO-marker growth 4→32 across the window; verified it
  is entirely the harness tooling's own detection strings + doc examples, not real
  deferred debt in product code. Advisory, no fix needed.
- Full suite grew 78→120 passing tests (10→27 skipped, the adds being perf/visual
  opt-in + db-integration) with no reds at any commit.

## Documents / artifacts
| Artifact | Location | Note |
|---|---|---|
| Custom linter + hooks | `tools/lint.py`, `.pre-commit-config.yaml`, `tools/install_hooks.sh` | item 5; --fix mutates; hook blocks commits |
| Cross-commit sweep | `tools/commit_sweep.py` | item 10; advisory |
| False-confidence audit | `tools/test_audit.py` | item 14 |
| Perf benchmarks + profiler | `tests/test_perf_benchmarks.py`, `tools/profile_target.py` | items 16/17; `-m perf` |
| Visual regression harness | `tools/visual_regression.py`, `tests/visual_baselines/README.md` | item 15; SKIP-loud headless |
| Feedback log | `docs/AGENT_FEEDBACK.md` | item 8 |
| Test inventory / conventions / queue | `docs/TESTS.md`, `docs/CODING_CONVENTIONS.md`, `TODOS.md` | items 4/11/13 |
| Review personas | `docs/review_personas/*.md` (6) | item 6; doc ownership |
| Tools authoring doc + CLIs | `tools/README.md`, `tools/agent_review`, `tools/validate` | items 9/18 |
| Night-shift skill | `docs/skills/night_shift.md` | item 12 |
| Git-tag-per-arc convention | `docs/session_arcs/README.md` | item 7 |
| Controlling-doc wiring | `CLAUDE.md`, `SESSION_START.md`, `OPERATING_RULES.md` | none orphaned |

## Open threads / next steps (ordered)
1. **Model-cost routing (Loop step 17)** — add `docs/MODEL_ROUTING.md` + a router
   helper that picks cheapest-capable model per loop stage. The clearest remaining
   world-class gap.
2. **Explicit open/closed loop framing (Loop step 15)** — cheap; largely covered by
   night_shift.md §3, revisit once a real runner exists.
3. **Commit baselines for visual regression** once the web app is bootable in CI, so
   `tools/validate`'s visual check moves from SKIP to PASS.

## Drift corrected this session
- None. STATE.md prose updated to describe the new harness; GROUND_TRUTH block
  untouched (no git/PR/DB facts changed materially beyond this branch's own commits).
