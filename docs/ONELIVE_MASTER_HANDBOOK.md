# OneLive — Master Handbook (Build · Launch · Operations)

> **Single source of orientation.** This file consolidates everything needed to
> understand, build, launch, and operate OneLive. It is a rollup and index; the
> deeper canonical docs it points to remain authoritative for their domain.
> Last consolidated: 2026-07-11.

---

## 0. What OneLive is

A **truth-first live-entertainment discovery platform** for the Austin metro
(music, art, food, and culture). AI *proposes* event candidates; **publication
requires multi-confirm evidence or a trusted claim** — the AI never publishes
directly. No pay-to-play ranking. No bypassing logins, paywalls, or bot
protection. Trust is the foundation, integrated into every layer — not a badge.

**The product promise:** if OneLive shows you an event, it is real, and the
platform is honest about how sure it is (confirmed / likely / unverified /
disputed) — and it never silently hides a disputed event.

---

## 1. Non-negotiable operating rules (the bar)

Full text: [`docs/OPERATING_RULES.md`](OPERATING_RULES.md). Summary:

- **§0 Prime directive:** trust is the foundation; when a rule and a deadline
  conflict, the rule wins — cut scope, never trust.
- **§1 Quality bar — world-class across EVERY aspect, tested as built.**
  "World-class" is a defensible claim (correct-at-core, adversarially tested,
  best-in-class with a named comparison, no unnamed weakness, honest maturity
  grading), and it applies to *every* aspect: architecture, data model, APIs,
  UX/UI, trust layer, security, performance, reliability/failure semantics,
  observability, tests, DX, and docs. No aspect gets a pass because another is
  strong. Tests ship in the same increment as the code and prove both directions.
- **§2 Loops (Kaizen):** inner loop (Understand→Implement→Self-review→Fix→
  Verify→loop until clean); weekly Kaizen; guard maturation (point-fix→meta-rule
  →mechanized scanner); **sabotage-validate every guard**; **Sunset Law** (retire
  an equivalent guard before adding one).
- **§3 Trust rules:** AI never publishes; 3-way gate with an escalate-to-human
  branch; everything auditable and replayable.
- **§4 Harness:** in-session discipline — reconcile at open, checkpoint before
  compaction, finalize at close.
- **No "ok" code, no "no immediate problems," nothing lingers/ignored/deferred.**
  No silent degradation, no swallowed errors, no dead code, no red tests.
  Findings are claims until verified against ground truth.

---

## 2. Architecture

Canonical: [`CLAUDE.md`](../CLAUDE.md) and
[`docs/Final_ONE_Live_Authoritative_Technical_Spec.md`](Final_ONE_Live_Authoritative_Technical_Spec.md).

**Pipeline (every stage independently auditable):**
```
Sources → Raw Fetch → Sensors (input-quality gate) → AI Extract → Candidate Store
        → Evidence → 3-way Gate (PASS / HOLD / ESCALATE) → Promote → Canonical Event → /tonight API → Public feed
```

**Two loops (do not conflate) —**
- **Product/extraction loop = a supervised *workflow*.** It SHOULD stop and
  **ESCALATE to a human** on ambiguity (conflicting times, private/RSVP,
  dedupe-ambiguity). It never auto-publishes. "Never ask a human" is REJECTED
  here.
- **Dev-time build loop = an autonomous *agent*.** It runs continuously
  (Understand→Implement→Self-review→Fix→Verify), stopping only at a genuine
  founder-decision fork, compaction risk, or arc completion.

**Confidence (4-state, do not revert to 3):** `unverified | likely | confirmed
| disputed`. Disputed always renders as disputed, never deleted.

**Stack:**
- PostgreSQL 15 via Supabase (project ref `vqipjlvzfiwnandjumvx`).
- Python / FastAPI + workers (pipeline, matching).
- Claude API — weak-signal extraction only, never auto-publish.
- Next.js 14 PWA (consumer feed + ops console).
- Clerk (auth), S3 (tastemaker photo storage), Stripe Connect (deferred to Phase 3).

**Trust invariants enforced mechanically** by `tools/trust_gate.py` (AST-based,
dependency-free, runs in CI on every PR + push):
1. No dynamic/interpolated SQL in api/worker/tools.
2. Ads/tastemaker code never imports gating/promote (separate trust category).
3. The AI/extraction layer never imports promote (AI can't publish).

**4-layer reference architecture** (see `docs/agent_loop_research.md` when
present, and the orchestrator arc):
- L1 Grounded loop — bounded pipeline; reasoning-trace is a plan-to-verify, not evidence.
- L2 Harness — input/output/tool guardrails + human-in-loop resumable state + deterministic replay.
- L3 Verification/gate — groundedness vs source, 3-way pass/fail/escalate.
- L4 Sensing/eval/Kaizen — tracing, drift proxies, rotating adversarial eval, guard maturation + Sunset Law.

---

## 3. Current build state (verified)

Authoritative & self-reconciling: [`STATE.md`](../STATE.md) (its GROUND_TRUTH
block is machine-maintained by `tools/session_reconcile.py` — run
[`docs/SESSION_START.md`](SESSION_START.md) at the start of every session).

**Done and verified:**
- Core schema + migrations applied to the live Supabase project.
- 4-state confidence enforced end-to-end; disputed always renders.
- Anti-hallucination extraction prompt; entity resolution (exact → pg_trgm fuzzy → placeholder).
- Real AI provider (`ai/claude_provider.py`) behind the `AIProvider` protocol; fail-loud on misconfig, degrade+audit on transient.
- Deterministic trust-gate CI (`tools/trust_gate.py`) — replaced the AI PR-reviewer.
- **Orchestrator-as-Harness**: `worker/orchestrator.py` (the loop, per-source error isolation), `worker/trust_gate3.py` (3-way PASS/HOLD/ESCALATE), `worker/sensors.py` (Class-D input-quality gate: truncation, mojibake, boilerplate-only, prompt-injection), `worker/replay_log.py` (append-only JSONL deterministic replay, fail-loud).
- **World-class extraction scorer** (`ai/eval_harness.py`): field-kind-aware comparison (TIME/DATE/VENUE/LIST_TEXT), partial credit for lists, bootstrap 95% CIs, `unparsed_values` diagnostics. Retired the obsolete exact-match scorer (Sunset Law).

**Known gaps being closed toward launch** (see §5): thin source catalog (43,
ungeotagged) → real geotagged 250–400+ catalog; eval/Kaizen learning loop
(Layer 4); pipeline never yet run `--real` (0 events / 0 candidates); no
public-facing UI yet (only ops console); no deploy/stealth gate.

---

## 4. Repository map

```
CLAUDE.md            Agent instructions + architecture invariants
README.md            Build-ready MVP overview + local dev quick start
STATE.md             Always-current state rollup (self-reconciling GROUND_TRUTH block)
CHANGELOG.md         Human-readable change history
docs/
  ONELIVE_MASTER_HANDBOOK.md         (this file)
  OPERATING_RULES.md                 how we work (quality bar, loops, trust, harness)
  Final_ONE_Live_Authoritative_Technical_Spec.md   full technical spec
  launch_plan.md                     9-gate stealth launch plan
  SESSION_START.md                   run first every session (reconciles STATE)
  orchestrator_spec.md               orchestrator-as-Harness build spec
  scorer_hardening_spec.md           world-class scorer spec
  eval_loop_spec.md                  adversarial eval loop spec
  session_arcs/                      per-session decision/finding records
ai/        AIProvider protocol, claude/bedrock providers, prompts, eval_harness, (eval_loop + eval_corpus)
api/       FastAPI: public.py (/tonight, /events), ops_candidates.py, deps, main
worker/    pipeline: orchestrator, sensors, trust_gate3, gating, promote, ai_extract,
           confidence, resolve_entities, replay_log, fetch/, candidate_store, run_once
tools/     trust_gate.py (CI gate), import_sources.py, session_reconcile.py, (coverage_report.py)
web/       Next.js 14 app (ops console now; public feed to be built)
mobile/    Expo / React Native
supabase/  migrations/ (0001–0010), config
sources/   master source catalog JSON (to be expanded + geotagged)
tests/     pytest suite (gates, confidence, orchestrator, sensors, replay, scorer, eval loop)
contracts/ shared type/contract definitions
```

---

## 5. Launch plan (9 gates)

Full detail: [`docs/launch_plan.md`](launch_plan.md). Dependency-ordered; each
gate ends green (pytest + trust_gate) and committed.

1. **Eval loop (Layer 4)** — adversarial corpus + runner + over-suppression tracking on the hardened scorer.
2. **Source geo/coverage schema** — migration `0010` adds `county`, `sub_region`, `coverage_categories` so blindness is measurable.
3. **Real source catalog (250–400+)** — 5-county Austin metro (Travis, Williamson, Hays, Bastrop, Caldwell) × categories (music venues, theaters/arts, galleries/museums, food/culinary, universities, city/county calendars, local media, community/cultural orgs). VERIFIED real URLs via browser research — never model-invented (would poison the catalog and violate the Class-D discipline). Scored + imported idempotently.
4. **Coverage report** — `tools/coverage_report.py`: county × category matrix.
5. **Pipeline on real data** — run orchestrator `--real`; confirm candidates promote; measure hallucination_rate. THE biggest unknown.
6. **Public feed UI** — `/tonight` + feed, world-class UX (loading/empty/error, a11y, copy, honest confidence display).
7. **Deploy + stealth gate** — wire public API to prod Supabase; deploy web; invite/password wall.
8. **World-class QA on live data** — security, performance, failure semantics, observability, final trust review.
9. **Founder finalize** — return with live URL + decisions only the founder can make.

**Estimate:** ~3–5 focused build-weeks to a genuine stealth-public launch
(prove pipeline on real data → build public UI → deploy behind stealth gate →
QA), driven by the autonomous build loop.

---

## 6. Operations & runbook

### 6.1 Start-of-session (every time)
```
# Reconciles STATE.md against live git/PRs/DB before you trust anything.
bash docs/SESSION_START.md          # or: python tools/session_reconcile.py --heal
```

### 6.2 Verification bar (run after every increment — must be green)
```
cd onelive
python -m pytest -q                 # full suite (currently 161 passed, 10 skipped)
python tools/trust_gate.py ; echo $? # trust invariants; exit 0 required
python -m ai.eval_loop ; echo $?     # adversarial eval; exit 0 = no regression
python worker/run_once.py ; echo $?  # loop smoke (DB-less sandbox isolates per-source, exits 0)
```

### 6.3 Local dev bring-up
```
# 1. Schema — run supabase/migrations/*.sql in order against Postgres 14+
# 2. Import sources
python tools/import_sources.py --json sources/master_sources_catalog_120.json
# 3. API
pip install -r api/requirements.txt && uvicorn api.main:app --reload --port 8000
# 4. Worker smoke
pip install -r worker/requirements.txt && python worker/run_once.py
# 5. Ops UI
cd web && npm i && npm run dev
```

### 6.4 Environment / secrets
- `ONELIVE_DB_DSN` — Postgres DSN (psycopg2). Sandbox has NO live Postgres (documented norm).
- `ANTHROPIC_API_KEY` — required for the real Claude provider (`--real` runs).
- `ONELIVE_REPLAY_LOG_DIR` — deterministic replay log dir (default `var/replay`).

### 6.5 Failure semantics (project-wide)
- **Fail LOUD** on config/structural errors (misconfig, missing extension, SQLSTATE 42883).
- **Soft-degrade + AUDIT** on transient faults (network, a single source down).
- **Never let "we failed" look like "nothing there."** This is the founding anti-pattern.
- Per-source error isolation lives in ONE place (`worker/orchestrator.py`); one bad source never sinks a run.

### 6.6 Trust & moderation invariants
- AI extraction never writes to the canonical event table — only the gate/promote path does, and promote re-checks the gate (defense in depth).
- Tastemaker / ads content is a separate trust category and must never touch the candidate/gating/promotion pipeline (mechanically enforced by `trust_gate.py`).
- `disputed` is set explicitly by ops, never inferred; the row is never deleted; it always renders.
- Every promotion decision is replayable from the append-only replay log.

### 6.7 Git & CI conventions
- Feature branches; PRs into `master`; squash-merge.
- CI = `.github/workflows/trust-gate.yml` (trust_gate + full pytest) on every PR + push. Green required.
- Commit each verified increment; never build on red.
- Store arcs/decisions in BOTH the repo (`docs/session_arcs/`) and memory.

---

## 7. Session arcs (how we got here)

Chronological decision/finding records in
[`docs/session_arcs/`](session_arcs/). Latest first:
- `2026-07-11_orchestrator-as-harness.md` — the loop built as Sensors→Harness→Loop; 3-way gate; replay log.
- `2026-07-10_source-import-and-ai-provider.md` — source catalog import + real Claude provider.
- `2026-07-10_build-assessment.md` — reconciliation + session-arc system established.

STATE.md is the always-current rollup; arcs explain how the state got there.

---

## 8. Glossary

- **Anchor / anchor-class source** — a primary source strong enough that its
  agreement can confirm an event (vs. a corroborating-only source).
- **Class-D failure** (Wu 2026) — polluted input laundered into fluent,
  confident, wrong output. Caught BEFORE extraction by `worker/sensors.py`.
- **ESCALATE** — the 3-way gate's human-judgement branch for conflicting/
  ambiguous evidence; never auto-promotes.
- **Sunset Law** — before adding a guard, retire/fold an equivalent one;
  defenses are themselves incident surfaces.
- **Sabotage-validation** — prove a guard fires on the exact violation it
  targets before trusting it (an unvalidated guard may be silently vacuous).
- **Karpathy ratchet** — the autonomy discipline; applies to the BUILD loop
  only, fenced OUT of the product gate.
- **Harness** — the in-session operating discipline (reconcile / checkpoint /
  finalize) plus the runtime guardrail layer (L2).
