# CLAUDE.md — ONE LIVE Autonomous Build Charter (place at repo root)
This file is read by Claude Code at the start of every session. It is the standing contract.

## Prime directives
1. **Trust invariants are physics, not policy.** AI never publishes; orchestrator cannot import the promote path; no pay-to-rank surface, ever; disputed shown-never-hidden; RLS stays fail-closed. Any change touching these = STOP and escalate to founder.
2. **Loops discipline (docs/LOOPS + Part 5 of MASTER):** every session begins with `python tools/session_reconcile.py` and ends by updating STATE.md + TODOS.md + docs/ONE_LIVE_CHANGE_LOG.md. Disk is truth; never trust chat memory over files.
3. **Contract-first:** no code before the session contract (goal, scope, done-criteria) is written to STATE.md. If the contract is ambiguous → ask the founder ONE consolidated question set, then proceed.
4. **Validation:** `python tools/validate.py` must pass before any PR is opened. `--allow-skips` is temporary debt; log every skip.

## Agent org (who does what)
- **Generator = this Claude Code session.** Writes code, tests-in-same-PR, small self-contained changes.
- **Independent Evaluator = GPT-5.5 via `OPENAI_API_KEY`** (script: `tools/adversarial_review.py`; create it in session 1 if absent — it posts the raw diff + test logs and demands APPROVE/REQUEST-CHANGES). MANDATORY for: auth, pipeline, SQL/RLS, data-trust, prompt/model changes. Optional second lens: Gemini via `GEMINI_API_KEY`.
- **Friction Agent = non-Claude model, pre-work.** Before any irreversible action (deploy, migration, spend, prompt_version bump), write the plan to `docs/FRICTION_LOG.md` and run it past the evaluator model with the prompt: "Attack this plan: what breaks, who is harmed, cheaper path, founder-crucial or not?" Blockers must be answered in writing.
- **Sentinel:** Sentry (`SENTRY_DSN`) on web+API+worker; healthchecks.io dead-man ping on any scheduled job. No scheduled loop ships without both.
- **Librarian:** session bookends, weekly digest appended to docs/FOUNDER_DIGEST.md.

## Founder-crucial escalations (the ONLY interrupts)
Money/new services · legal posture · trust-invariant changes · go-live/allowlist pushes · credential minting. Everything else: decide, log the decision record, proceed.

## Working with the designer AI (Stitch loop)
1. Founder runs the 3 direction passes in Google Stitch using `docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.md` (v2.4) and drops exports (HTML/Tailwind or Figma-exported assets) into `design/inbox/`.
2. Generator translates the chosen direction into `apps/web` (Next.js 15 + Tailwind), honoring: verbatim copy strings, trust display rules (NO badges/"confirmed" text; low-confidence = quiet icon → dismissible sheet + venue link), Spark Line/Emotion Glyph card anatomy, WCAG 2.2 AA, CWV budgets (LCP≤2.5s).
3. Every design-derived PR gets an evaluator pass against the brief's 8-criterion rubric; deltas from the brief are logged, never silent.
4. Descriptor Foundry (brief appendix) is the mandatory pipeline for ALL AI-generated descriptors: 6 candidates → pairwise knockout vs checklist → Fusion-of-N synthesis (style new, facts never) → independent judge → provenance + golden-set regression.

## Environment (never in git; see docs/KEYS.md and the API manifest)
ONELIVE_DB_DSN · SUPABASE anon (web) · ANTHROPIC_API_KEY (extraction only, spend cap set in console FIRST) · OPENAI_API_KEY (evaluator/friction) · GEMINI_API_KEY (optional) · CLERK keys · VERCEL_TOKEN · SENTRY_DSN · ORCHESTRATOR_PING_URL. Agents never mint keys.

## Document index (read on demand, not every session)
Source canon (this session's inputs): `docs/source/OneLive_WORLD_CLASS_bar.md` (§0–§9 engineering bar) · `docs/source/OneLive_MASTER_the_whole_enchilada.md` (Parts 0–8 master state).
Session 2026-07-12 outputs: `docs/strategy/OneLive_WORLD_CLASS_v1.1_DEEP_REVIEW.md` (PROPOSAL: §10 legal/TRAIGA·TDPSA, §11 AI governance/NIST AI RMF, §12 IR/DR, §13 privacy, §14 FinOps, §15 growth; defects D1–D5; DORA/ASVS numbers) · `docs/strategy/OneLive_AUTONOMOUS_BUILD_CHARTER_and_API_MANIFEST.md` (6-agent org, escalation protocol, 12-service key manifest) · `docs/strategy/ONE_LIVE_EMOTION_VIBE_LAYER_SPEC_v1.md` (PROPOSAL: two-axis taxonomy, Feel mode, Emotion Graph, EU-AI-Act guardrails) · `docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md` (RATIFIED design canon: trust display rules, Spark Line waterfall incl. subtle-✳ tier C, Emotion Glyph engine, Descriptor Foundry, behavioral architecture, 3-direction Stitch mandate) · `docs/design/OneLive_Tonight_Prototype_v2.jsx` (reference implementation of the PRD wireframe) · `docs/ops/CLAUDE_CODE_KICKOFF_PROMPT.md` (Session Contract #1) · `docs/ops/ONE_LIVE_CHANGE_LOG_UPDATE_2026-07-12.md` (append to docs/ONE_LIVE_CHANGE_LOG.md).
Status legend: brief v2.4 = founder-ratified through its edits; deep review §10–§15, Emotion & Vibe spec, and taxonomy remain PROPOSALS pending gap-by-gap ratification (G1–G6, G-VT, G-EG, G-F). When in doubt, PROPOSAL ≠ license to build.

## Current mission (until founder changes it)
Ship the live site behind the stealth gate: Steps 5→10 of the critical path — schedule ingestion (GitHub Actions cron + dead-man ping + budget caps BEFORE first scheduled run), extraction with eval-harness thresholds, gate→candidate flow, admin review, implement the ratified design direction on /tonight (feed+filters+detail), Clerk allowlist gate, Vercel deploy, founder go/no-go.


---

<!-- ===== REPO-LOCAL ADDITIONS PRESERVED (pre-genesis CLAUDE.md, still in force) ===== -->

# OneLive — Agent Instructions

## Architecture (do not deviate without a STATE.md note)
Pipeline: Sources -> Raw Fetch -> AI Extract -> Candidate Store -> Evidence -> Gate -> Promote -> Canonical Event -> `/tonight` API.
Every stage is independently auditable. The AI extraction step never publishes directly — everything passes through the gate.

Confidence states (4-state, confirmed decision — do not revert to a 3-state model):
`unverified` | `likely` | `confirmed` | `disputed`
Rule: disputed events are always shown as disputed, never deleted.

Stack:
- PostgreSQL 15 (via Supabase), project ref: vqipjlvzfiwnandjumvx
- Python/FastAPI + Celery workers (pipeline, matching engine)
- Claude API — used only for weak-signal extraction from raw fetched text, never to auto-publish
- Next.js 14 PWA (consumer feed + ops console)
- Clerk (auth)
- S3 (photo storage for Tastemaker posts)
- Stripe Connect (deferred until Phase 3 matching payments — not needed for v1 intro-only matching)

## Coding standards
(Full reviewer-facing checklist: `docs/CODING_CONVENTIONS.md`. Mechanically enforced
by `python tools/lint.py` — pre-commit hook installed via `tools/install_hooks.sh`
runs `lint.py --fix` + `trust_gate.py` and blocks the commit on any violation.)
- TypeScript strict mode everywhere in the Next.js app. No `any` without a comment explaining why.
- Every API endpoint validates input (zod or pydantic schema) before touching the DB.
- Parameterized queries only — never string-interpolate SQL.
- Auth checks required on every protected route (venue/creator claim actions, tastemaker posting, admin moderation).
- Tastemaker posts (opinionated human content) must NEVER touch the event candidate/gating/promotion pipeline. They are a fully separate trust category from verified event data. See STATE.md if this boundary is ever unclear.

## Review criteria for any PR you generate or review
1. Does it touch the promotion pipeline or auth? If yes, flag for a deeper review pass, not the fast default pass.
2. Are confidence-state and moderation-state transitions covered by a test in `tests/test_gates.py` (or the tastemaker-post equivalent)?
3. Does it introduce a new external dependency? If yes, note it in STATE.md.
4. Run a cross-agent review (a *different* model than wrote the code) via
   `tools/agent_review --persona <p> --target <ref>`, choosing the persona(s) in
   `docs/review_personas/` that own the risk (security, performance,
   maintainability, code-quality, ai-smells, domain-truth-and-trust). Each persona
   also owns and maintains a set of system docs — see its file.

## Where to look first
Quick map of the harness (all discoverable, none orphaned):
- `docs/SESSION_START.md` — session bookends (reconcile → work → close).
- `TODOS.md` — the work queue. `docs/skills/night_shift.md` — autonomous-run orchestration.
- `tools/validate` — the single end-of-shift "run everything" gate (trust_gate,
  lint, full pytest, eval_harness, perf, test_audit, commit_sweep, visual_regression).
- `docs/TESTS.md` — test inventory + how-to-write-tests. `docs/CODING_CONVENTIONS.md` — conventions.
- `docs/review_personas/` — cross-agent review lenses. `docs/AGENT_FEEDBACK.md` — session-end friction log.
- `tools/README.md` — index of every helper script (lint, trust_gate, test_audit,
  commit_sweep, profile_target, visual_regression, session_reconcile, agent_review).

**Run `docs/SESSION_START.md` before starting any session.** It reconciles STATE.md
against live ground truth (git/PRs/DB via `tools/session_reconcile.py`) so you can
trust it, then routes you to STATE.md (what's done/next), the latest session arc
(how we got here), and `docs/OPERATING_RULES.md` (how we work). Do not trust
STATE.md until the reconcile step is clean. Update STATE.md and re-run the
reconciler at the end of every meaningful session.
