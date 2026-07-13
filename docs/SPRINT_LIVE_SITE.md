# SPRINT — Live site behind the stealth gate (critical-path Steps 5→10)

Greppable summary: the step-by-step plan for the current mission (CLAUDE.md
"Current mission"): scheduled ingestion → extraction thresholds → gate flow →
admin review → ratified design on /tonight → allowlist gate → Vercel deploy →
founder go/no-go. Each step has a done-criterion and a named gating agent.
Written by Session Contract #1 (2026-07-13). **PLAN ONLY — nothing in this
file has been executed. Zero deploys, zero migrations, zero spend so far.**

Status legend: each step is NOT STARTED unless annotated. Update this file in
the same commit that advances a step.

---

## Standing preconditions (before Step 5 can start)

| # | Precondition | Owner | Status |
|---|---|---|---|
| P1 | `OPENAI_API_KEY` minted (Independent Evaluator + friction attacks) | founder (credential minting is founder-crucial) | **MISSING — the one item Session 1 could not finish** |
| P2 | `ANTHROPIC_API_KEY` minted **with monthly spend cap set in console FIRST** (§14.3) | founder | missing (needed at Step 6, not 5) |
| P3 | `SENTRY_DSN` ×3 surfaces + `ORCHESTRATOR_PING_URL` (healthchecks.io) | founder mints; wiring ALREADY DONE (worker/sentinel.py, api/main.py, web/instrumentation*.ts — all no-op until DSNs exist) | wiring done 2026-07-13 |
| P4 | Decide open PR #7 (orchestrator-harness): PR #9 already ported its content to master — recommend CLOSE as superseded | founder ack (1 line) | open |
| P5 | Migration 0008 (source-trust config, PR #4 draft) — finish or defer explicitly | Generator + Evaluator | open draft |

## Step 5 — Scheduled ingestion loop (GitHub Actions cron)

**What:** `.github/workflows/ingest.yml` running `python worker/run_once.py --real`
on an hourly cron; secrets `ONELIVE_DB_DSN`, `ANTHROPIC_API_KEY` in Actions;
`ORCHESTRATOR_PING_URL` dead-man ping wraps the run (already wired);
**budget caps in place BEFORE the first scheduled run** (Anthropic console cap
+ per-run source/token ceiling flag on run_once).
**Done when:** one green scheduled run on real sources writes `raw_fetch` rows +
candidates, the healthchecks check shows the ping, and a kill test (disable the
workflow) fires the dead-man alarm.
**Gated by:** Friction pre-work attack in `docs/FRICTION_LOG.md` (this is the
first irreversible/spend-adjacent action) → Independent Evaluator (`--require`)
on the PR → founder approves the spend cap (money = founder-crucial).

## Step 6 — Extraction with ratified eval-harness thresholds

**What:** ratify `hallucination_rate ≤ 1%` on the golden set (deep-review §11.2
proposal) or founder's number; wire `ai/eval_harness.py` into `tools/validate`
as a blocking check on any prompt/model change; record `prompt_version` in
provenance (already stamped).
**Done when:** eval harness runs on a golden set in CI and a deliberately
degraded prompt fails the gate (prove the gate can fail).
**Gated by:** Independent Evaluator (prompt/model changes are trust-critical,
`--require`); founder ratifies the threshold number (Q-threshold, one line).

## Step 7 — Gate → candidate flow on real data + admin review

**What:** first real candidates flow fetch → sensors → extract → gate3
(PASS/HOLD/ESCALATE) → candidate store; ops inbox (`api/ops_candidates.py`,
`web/app/ops`) exercised against real rows; promotion stays a human ops action.
**Done when:** ≥1 real event promoted to `event` via the ops UI by a human,
`/tonight` (service-role path) returns it, `event` row count > 0 verified.
**Gated by:** trust_gate + full validate; Independent Evaluator on any pipeline
diff; NO auto-promotion anywhere (trust invariant — physics, not policy).

## Step 8 — Clerk allowlist gate verified live

**What:** the two-layer fail-closed gate is already on master (PR #9). Set real
`ONELIVE_ALLOWLIST`, `CLERK_SECRET_KEY`/`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`,
`ONELIVE_CLERK_AZP_ALLOWED` in the deploy env and execute PR #9's unchecked
test plan (non-allowlisted → /access; wrong azp → 403).
**Done when:** a non-allowlisted real account is redirected and the API rejects
a wrong-azp token, both observed live and logged in STATE.md.
**Gated by:** Independent Evaluator already reviewed the code (PR #9); this
step is configuration + live verification. Allowlist content = founder-crucial.

## Step 9 — Ratified design direction on /tonight + Vercel deploy

**What:** founder drops the chosen Stitch direction into `design/inbox/`;
Generator implements feed + filters + event detail per
`docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md` (verbatim copy strings,
quiet-icon trust treatment, NO badges — note: the reference prototype's
"✓ Confirmed by multiple sources" line predates the ratified no-badges rule
and must NOT ship), WCAG 2.2 AA, LCP ≤ 2.5s; deploy to Vercel behind the gate.
**Done when:** deployed preview URL serves the gated /tonight with real
promoted events; evaluator scores the build against the brief's 8-criterion
rubric; CWV budget measured on the preview.
**Gated by:** design-PR evaluator pass vs the rubric (deltas logged, never
silent); deploy itself gets a Friction pre-work attack; `VERCEL_TOKEN` minting
= founder-crucial.

## Step 10 — Founder go/no-go

**What:** founder walks the live gated site, reviews the friction log, spend
meters, and Sentinel signals, then explicitly approves widening the allowlist.
**Done when:** written go/no-go decision recorded in STATE.md +
docs/ONE_LIVE_CHANGE_LOG.md. Go-live/allowlist pushes are founder-crucial by
charter — no agent may take this step.

---

## Sequencing note

5 → 6 → 7 are strictly ordered (no real candidates without a scheduled loop;
no trusted extraction without thresholds). 8 and 9 can proceed in parallel
with 6–7 once Step 5's workflow file exists, because they touch the web
surface, not the pipeline. 10 is last, always.
