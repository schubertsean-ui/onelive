# CLAUDE.md — ONE LIVE Autonomous Build Charter (place at repo root)
This file is read by Claude Code at the start of every session. It is the standing contract.

## Prime directives
1. **Trust invariants are physics, not policy.** AI never publishes; orchestrator cannot import the promote path; no pay-to-rank surface, ever; disputed shown-never-hidden; RLS stays fail-closed. Any change touching these = STOP and escalate to founder. Scope note (founder-ratified 2026-07-18, verbatim directive "You do the merge and notify me" — docs/memory/decisions/2026-07-18_agent-merges-on-green.md): "AI never publishes" governs the PRODUCT data path (extraction → candidate → gate → promote → users) and every outward-facing product surface — it is NOT narrowed by repo operations. Distinctly and explicitly: the agent MAY merge its own PR only when the independent non-Claude evaluator has APPROVED and every required check on the final head is green (red or pending = hard stop, no exceptions), notifying the founder at merge. Product publishing remains gate-custodied and founder-controlled exactly as before. Exception, enumerated, closed, and MECHANICALLY compensated per class (founder-ratified 2026-07-18 "Ratified"; mechanics added at the evaluator's demand on PR #36, the per-class scope split at its r3 — the classified surface is broader than the certification hash, so one blanket "red moves" claim was fail-open): the golden-exam verifier is red BY DESIGN on any PR that modifies the exam harness surface — the CLASSIFIER is the verifier's own harness-refusal output ("changes extraction HARNESS code that the attended exam does not execute"), never agent judgment, and the classifier itself partitions the refused files into the two classes below (tools/classify_extraction_surface.py, reading HARNESS_MANIFEST as data from the single source the exam runner stamps — mechanical identity, never hand-mirrored). That red does not count against "every required check green" ONLY for refusals PROVEN to contain no manifest-bound file — eligibility is read off the classifier's own printed partition (or, for refusals emitted by the pre-partition classifier, checked directly: no listed file appears in HARNESS_MANIFEST), and an unreadable manifest makes a refusal INELIGIBLE (the classifier prints exactly that — fail closed, never fail-open). Both classes are covered, each by a LIVE compensating control (the bootstrap completed 2026-07-18 — gate #36, evidence plumbing #37/#38, verifier hygiene #39, authenticated record #40, re-lock in the same commit as this sentence; no unmerged code ever judged anything): (a) MANIFEST-BOUND files (the exact set compute_harness_sha() covers): trust_gate's extraction-certification re-lock fails the whole tree whenever EXTRACTION_THRESHOLD_RATIFIED is True while the current harness hash differs from the committed attended-exam certification record (ai/golden/CERTIFIED_HARNESS.json, outside the manifest so recording cannot alter what it certifies, and enterable or changeable ONLY through the base-owned online authenticator in extraction-eval.yml). Because that re-lock fires on the PR itself, a manifest-bound refusal is eligible ONLY when the SAME PR sets EXTRACTION_THRESHOLD_RATIFIED to literal False (the classifier verifies this from the subject's routing data and prints it; anything else carries the EXCEPTION-INELIGIBLE marker — there is no double-red merge path, ever): the closure moves, not the red — extraction is OFF, fail-closed, from merge until the standing three-step re-opens it (founder's attended exam on the new harness → authenticated record PR → head-bound flag-flip PR), and trust_gate stays green throughout because a closed extraction needs no certification while the re-lock still hard-stops any certified-but-drifted state (e.g. a direct push). The re-lock computes the harness hash with trust_gate's OWN manifest copy and hasher, never the manifest-bound runner's (r3: circular trust — the compensated PR class must not be able to alter the computation that judges it); single-sided copy drift fails the test suite in the same PR, and a coordinated change of both copies necessarily touches trust-path files, whose compensation is the mandatory review. The re-lock compensates the UNCHANGED, previously-authenticated record only — a refusal accompanied by ANY change to ai/golden/CERTIFIED_HARNESS.json is INELIGIBLE (the refusal precludes the authenticator from running, so the changed record would enter unverified; the classifier prints a canonical EXCEPTION-INELIGIBLE marker and the review's evidence step fails closed on it mechanically — land records separately, after their harness merges and an attended exam certifies them). An unclassifiable refusal (unreadable manifest) is likewise INELIGIBLE, same marker, same mechanical fail. (b) NON-manifest surface files (verifier/trust-path code and exam data outside the manifest) ARE covered now: their compensation is structural and already live — they affect no trust decision except through base-owned copies (pull_request_target: a PR's copy never judges itself) and per-run data bindings re-derived from base at every evidence verification (golden/prompt/model/dependency-lock hashes), and the change itself merges only at the mandatory non-Claude adversarial review's APPROVE on that very PR (adversarial-review.yml, every PR, no path filter). Adding any further named exception is a gate-threshold relaxation: founder-crucial.
2. **Loops discipline (docs/LOOPS + Part 5 of MASTER):** every session begins with `python tools/session_reconcile.py` and ends by updating STATE.md + TODOS.md + docs/ONE_LIVE_CHANGE_LOG.md. Disk is truth; never trust chat memory over files.
3. **Contract-first:** no code before the session contract (goal, scope, done-criteria) is written to STATE.md. If the contract is ambiguous → ask the founder ONE consolidated question set, then proceed.
4. **Validation:** `python tools/validate` must pass before any PR is opened. `--allow-skips` is temporary debt; log every skip.

## Agent org (who does what)
- **Generator = this Claude Code session.** Writes code, tests-in-same-PR, small self-contained changes.
- **Independent Evaluator = GPT-5.5 via `OPENAI_API_KEY`** (script: `tools/adversarial_review.py`; create it in session 1 if absent — it posts the raw diff + test logs and demands APPROVE/REQUEST-CHANGES). MANDATORY for: auth, pipeline, SQL/RLS, data-trust, prompt/model changes, and **gate custody** — any change to the verification tooling or its thresholds (`tools/validate`, `trust_gate.py`, `deferral_scan.py`, `lint.py`, `adversarial_review.py`, `eval_harness`, the CI gate workflows). The Generator never merges an unreviewed change to its own examiners (added 2026-07-14 at founder direction, from the Weco RSI review; `adversarial-review.yml` already enforces this mechanically by running on EVERY PR with no path filter — stated here so the intent never depends on one workflow file). Optional second lens: Gemini via `GEMINI_API_KEY`.
- **Friction Agent = non-Claude model, pre-work.** Before any irreversible action (deploy, migration, spend, prompt_version bump), write the plan to `docs/FRICTION_LOG.md` and run it past the evaluator model with the prompt: "Attack this plan: what breaks, who is harmed, cheaper path, founder-crucial or not?" Structure (2026-07-16 at founder direction, from the swarm-analysis review; registry: `docs/hats/`): Blue frame pre-registered → White facts pass → po battery (unchanged) → independent parallel lenses that never see each other's output, at least one Yellow best-case, cross-family where keys allow → devil's-advocate attack on any consensus → Blue merge that preserves conflict, never averages. Blockers must be answered in writing.
- **Sentinel:** Sentry (`SENTRY_DSN`) on web+API+worker; healthchecks.io dead-man ping on any scheduled job. No scheduled loop ships without both.
- **Librarian:** session bookends, weekly digest appended to docs/FOUNDER_DIGEST.md (pending its first entry — created at first digest).

## Founder-crucial escalations (the ONLY interrupts)
Money/new services · legal posture · trust-invariant changes · **gate-threshold relaxations** (any loosening of validate/trust_gate/evaluator/eval-harness enforcement — added 2026-07-14; making a gate easier to pass is never an agent decision) · go-live/allowlist pushes · credential minting. Everything else: decide, log the decision record, proceed.

## Cost discipline (added 2026-07-13 at founder direction)
Maximally effective AND maximally efficient — highest margin at a world-class bar:
1. **Least costly method first.** Every task/loop stage uses the cheapest-capable model tier, technique (cache, batch, low effort), and tool that meets the bar. Policy + stage→model mapping: `docs/MODEL_ROUTING.md` (resolver: `tools/model_router.py`).
2. **Escalate spend deliberately, never silently.** User-facing breakage, trust/production-critical issues, or repeated failure at a cheaper tier justify a faster/stronger model — log the escalation reason in the decision record.
3. **Quality gates never relax.** validate/trust_gate/evaluator/eval-harness thresholds are identical at every tier — efficiency is achieved by routing, caching, and batching, never by skipping verification.
4. **Measure, don't guess.** Cost-per-verified-event (§14.2) and per-run ceilings govern the pipeline; a cheaper tier earns its place by passing the same gates, and loses it the same way.

## The Record — no silent deferrals (added 2026-07-13 at founder direction)
Everything is checked against the documented world-class bar for that item, so deferrals should not exist. When one does — any "for now", "check later", "ok for now", "revisit", or a noticed-but-unfixed issue, in code, docs, PR text, or chat — it is RECORDED in `docs/RECORD.md` **in the same commit**: what is deferred, the bar it deviates from (cited), and an objective resolution trigger (never "someday"). Silent deferral is a violation. Enforcement: `tools/deferral_scan.py` (blocking, in `tools/validate`) requires every deferral-language code comment to carry a live `[R-###]` tag; prose is covered by this rule + evaluator review. Session close reviews OPEN entries — a fired-but-unactioned trigger is a defect.

## Thinking tools & Kaizen (added 2026-07-14 at founder direction)
1. **Po battery at divergent moments** (`docs/skills/po_provocation.md`, generator `tools/po_battery.py`): before irreversible actions the Friction pre-work OPENS with the full provocation battery (all operators, standalone + random-combos), then attacks; also mandatory for sprint/architecture planning, design-direction selection, Descriptor Foundry ideation. Provocations are stimuli, never facts — nothing po-generated enters memory, candidate data, or user-facing copy except through the normal gates. Convergent gates (validate/trust_gate/evaluator) stay purely convergent.
2. **Kaizen measures** (`docs/KAIZEN.md`, ledger `docs/metrics/KAIZEN_LEDGER.md`): zero ESCAPED defects is absolute; internally-caught defects are treasure — every catch gets a ledger row (gate, class); repeat classes must trend to zero via gate-gap fixes. Ledger row per merged PR + at session close; trends in the weekly founder digest. Maturity levels deferred behind R-012's objective trigger.
3. **Dedicated-hat registry** (`docs/hats/`, added 2026-07-16 at founder direction): the six thinking hats as standing agents — each hat = fixed prompt + owned memory + model binding via the router + custody + its own Kaizen measures (measure, counter-measure, escape definition; all rows in the existing ledger, M8 = Yellow validated upside). Black = the Independent Evaluator/Friction attack (non-Claude, hard invariant); White = the reconcile/eval-harness scripts; Green = the po battery; Blue = the session loop plus the conflict-preserving merge; Yellow = the deliberate best-case lens (new — the harness previously had only attackers); Red = the founder, never an agent. Hats fire at divergent/founder-crucial moments only; no hat's output is ever evidence, and using a hat to relax any gate is founder-crucial.

## Communicating with the founder (added 2026-07-13 at founder direction)
Every report, question, escalation, and PR description addressed to the founder follows these rules — they outrank brevity:
1. **Plain language.** No unexplained jargon; assume a smart non-engineer. A one-line explanation beats an acronym.
2. **Why this, not that.** Every recommended action or tool names the alternatives considered and why this one won, in a sentence or two.
3. **Tradeoffs, honestly.** Say what gets worse or what risk remains with the recommendation — never present a choice as free.
4. **Direct links.** Link the exact page (settings screen, PR, CI run, doc) — never "go find X in the dashboard."
5. **Make it easy.** Numbered steps, phone-friendly, smallest possible founder effort; consolidate asks into ONE list instead of a dribble of interrupts (reinforces prime directive 3).

## Working with the designer AI (Stitch loop)
1. Founder runs the 3 direction passes in Google Stitch using `docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md` and drops exports (HTML/Tailwind or Figma-exported assets) into `design/inbox/`.
2. Generator translates the chosen direction into `apps/web` (Next.js 15 + Tailwind), honoring: verbatim copy strings, trust display rules (NO badges/"confirmed" text; low-confidence = quiet icon → dismissible sheet + venue link), Spark Line/Emotion Glyph card anatomy, WCAG 2.2 AA, CWV budgets (LCP≤2.5s).
3. Every design-derived PR gets an evaluator pass against the brief's 8-criterion rubric; deltas from the brief are logged, never silent.
4. Descriptor Foundry (brief appendix) is the mandatory pipeline for ALL AI-generated descriptors: 6 candidates → pairwise knockout vs checklist → Fusion-of-N synthesis (style new, facts never) → independent judge → provenance + golden-set regression.

## Environment (never in git; see the API manifest in `docs/strategy/OneLive_AUTONOMOUS_BUILD_CHARTER_and_API_MANIFEST.md`; a dedicated docs/KEYS.md is pending)
ONELIVE_DB_DSN · SUPABASE anon (web) · ANTHROPIC_API_KEY (extraction only, spend cap set in console FIRST) · OPENAI_API_KEY (evaluator/friction) · GEMINI_API_KEY (optional) · CLERK keys · VERCEL_TOKEN · SENTRY_DSN · ORCHESTRATOR_PING_URL. Agents never mint keys.

## Document index (read on demand, not every session)
Source canon (2026-07-12 session inputs — historical: supplied to that session, never committed to the repo): OneLive_WORLD_CLASS_bar (§0–§9 engineering bar) · OneLive_MASTER_the_whole_enchilada (Parts 0–8 master state).
Session 2026-07-12 outputs: `docs/strategy/OneLive_WORLD_CLASS_v1.1_DEEP_REVIEW.md` (PROPOSAL: §10 legal/TRAIGA·TDPSA, §11 AI governance/NIST AI RMF, §12 IR/DR, §13 privacy, §14 FinOps, §15 growth; defects D1–D5; DORA/ASVS numbers) · `docs/strategy/OneLive_AUTONOMOUS_BUILD_CHARTER_and_API_MANIFEST.md` (6-agent org, escalation protocol, 12-service key manifest) · `docs/strategy/ONE_LIVE_EMOTION_VIBE_LAYER_SPEC_v1.md` (PROPOSAL: two-axis taxonomy, Feel mode, Emotion Graph, EU-AI-Act guardrails) · `docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md` (RATIFIED design canon: trust display rules, Spark Line waterfall incl. subtle-✳ tier C, Emotion Glyph engine, Descriptor Foundry, behavioral architecture, 3-direction Stitch mandate) · `docs/design/OneLive_Tonight_Prototype_v2.jsx` (reference implementation of the PRD wireframe) · `docs/ops/CLAUDE_CODE_KICKOFF_PROMPT.md` (Session Contract #1) · `docs/ops/CHANGELOG_APPEND_2026-07-12.md` (append to docs/ONE_LIVE_CHANGE_LOG.md).
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
   also owns and maintains a set of system docs — see its file. When multiple
   personas review one change, they run as independent calls that never see each
   other's findings; outputs meet only at the merge (`docs/hats/README.md`,
   Independence — added 2026-07-16).

## Where to look first
Quick map of the harness (all discoverable, none orphaned):
- `docs/SESSION_START.md` — session bookends (reconcile → work → close).
- `docs/memory/` — the agent's long-term memory (Brain 1A, G-BRAIN ratified):
  distilled decisions/gotchas/entity notes; skim after reconcile, write per
  its README conventions before session close.
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
