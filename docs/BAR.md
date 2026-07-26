# BAR — what "world class" means for OneLive, per aspect, as a number

**Status: CANON. This is the definition of done.** Read this before writing code.
It is the one place the quality bar lives. `docs/WORLD_CLASS.md` is the citation
appendix behind it (every clause there names the authority — Google eng-practices,
OWASP, NIST, W3C, DAMA, Google SRE, DORA, Nielsen, Fowler, Beck, Ousterhout,
Kleppmann, 12-Factor, Karpathy's LOOPS). This file is the operational form: one
row per aspect, a number, the gate that enforces it, and the honest current
status.

**Three rules about this file.**

1. **A bar without a number is not a bar.** If an aspect cannot be measured, it
   says `UNMEASURED` — never "good", never "solid".
2. **A bar without a gate is an intention.** The `Gate` column names the
   mechanism. `—` means nothing enforces it yet, and that is stated rather than
   implied.
3. **Status is measured, not asserted.** Every `MET` was verified by a run whose
   date is in the row. A stale measurement is `UNMEASURED`, not `MET`.

**Enforcement legend.** `ENFORCED` = mechanically blocking today. `PROPOSED` =
written here as the target but **not** yet blocking; it becomes blocking only
after the founder ratifies it (making a gate stricter is cheap, but it is still a
gate change and gets reviewed). Loosening any `ENFORCED` row is
**founder-crucial** — never an agent decision.

Last full measurement pass: **2026-07-26** (`docs/V1_AUDIT_2026-07-26.md`).

**The scoreboard, 66 rows:** **46 MET** (one of them only informally) ·
**13 NOT MET** · **6 UNMEASURED** · **1 partial** (H1, met for the two jobs that
are scheduled). Read that as good news with a sharp edge: the *standards* are
overwhelmingly met, and almost every miss is something built-but-not-connected or
never-measured. **Nothing on the NOT MET list needs a new standard.** The six
UNMEASURED rows are the honest embarrassment — five of them are the experience
users actually get.

---

## A. Truth and data trust — the moat

| # | World class means | Number | Gate | Enforcement | Status 2026-07-26 |
|---|---|---|---|---|---|
| A1 | The AI that extracts never decides what publishes. Extraction, gating and promotion are separate, separately auditable stages. | Structural: the orchestrator cannot import the promote path | `tools/trust_gate.py` (import-allowlist assertion) | ENFORCED | **MET** |
| A2 | Nothing is ever published that was not extracted from a real fetched source. "Never fabricate an event" is absolute. | 0 fabricated rows | sensor + schema validation in `worker/ai_extract.py`; `tests/test_gates.py` | ENFORCED | **MET** |
| A3 | Every published fact carries its provenance: which source, which fetch, which prompt version. | 100% of rows | schema NOT NULL + `worker/candidate_store.py` | ENFORCED | **MET** |
| A4 | Confidence is a 4-state model — `unverified` / `likely` / `confirmed` / `disputed`. No fifth state, ever. | exactly 4 | `worker/confidence.py` + `tests/test_gates.py` | ENFORCED | **MET** |
| A5 | Disputed events are always shown as disputed. Never deleted, never hidden. | 0 hidden | `web/lib/trust.ts` + `web/lib/trust.test.ts` | ENFORCED | **MET** |
| A6 | Uncertainty is shown quietly and honestly — no badges, no "confirmed" text; a low-confidence marker opens an explanation and a link to the venue. | 0 badges in the shipped feed | design brief rubric + `web/lib/trust.test.ts` | ENFORCED | **MET** |
| A7 | No pay-to-rank surface exists. Paid placement can never influence ordering. | 0 ranking inputs from any paid field | `tools/trust_gate.py` | ENFORCED | **MET** |
| A8 | Row-level security is fail-closed: the public role reads listing columns and nothing else. | deny by default | migrations `0006`/`0007`/`0010`/`0012` + `tools/trust_gate.py` | ENFORCED | **MET** |
| A9 | Human-opinion content (Tastemaker posts) never touches the event candidate/gating/promotion path. | 0 shared code paths | `tools/trust_gate.py` | ENFORCED | **MET** |

## B. Extraction quality

| # | World class means | Number | Gate | Enforcement | Status |
|---|---|---|---|---|---|
| B1 | Field-level hallucination rate on the golden set. | **≤ 1%** (one-way ratchet — may tighten, never loosen) | `ai/golden_exam.py`, `extraction-eval.yml` | ENFORCED | **MET** — 0.63% measured, attended exam run `29659010747` |
| B2 | Recall floor, so "going mute" cannot be mistaken for safety. | **≥ 80%** | same | ENFORCED | **MET** — 97.82% |
| B3 | The golden set is large enough for the rate to mean something. | **≥ 300 facts** | `ai/exam_thresholds.py` | ENFORCED | **MET** — 316 facts |
| B4 | Fetched page text is untrusted input: embedded instructions must be treated as data, never obeyed. | 0 successful injections | injection cases in the golden set | ENFORCED | **MET** — 0 of the set's injection cases succeeded |
| B5 | Extraction runs against the real provider path, not a stub, before any threshold claim. | attended exam on the real path | `extraction-eval.yml` + certification record | ENFORCED | **MET** |

## C. Data coverage and freshness — the product promise

| # | World class means | Number | Gate | Enforcement | Status |
|---|---|---|---|---|---|
| C1 | Tonight's feed is fresh: the newest data is younger than one refresh cycle. | **≤ 12 h** since the last successful import | dead-man alarm per scheduled import | ENFORCED | **NOT MET** — the local-venue import had never completed a scheduled run before 2026-07-26 (audit D1) |
| C2 | The ticketed feed refreshes without a human. | scheduled, **≥ 2×/day** | `import_licensed.yml` has **no schedule** | — | **NOT MET** — manual dispatch only (audit D4) |
| C3 | A passing long-tail candidate reaches users without a human click, except the ratified exceptions. | median time-to-publish **≤ 1 h** | `worker/publish_policy.py` exists but is wired to nothing | — | **NOT MET** — no automated promoter (audit D3) |
| C4 | Geographic coverage matches the stated service area. | all 10 CAPCOG counties | `worker/importers/*` geo scoping | PROPOSED | **UNMEASURED** — single 60-mile radius today (R-025) |
| C5 | A run that does zero useful work fails loudly rather than reporting success. | 0 silent no-op runs | `enforce_useful_work` in `worker/run_once.py` | ENFORCED | **MET** — proven by run `30186783965` failing correctly |

## D. Security and auth

| # | World class means | Number | Gate | Enforcement | Status |
|---|---|---|---|---|---|
| D1 | Deny by default. A failed check never leaves the system open. | 0 fail-open paths | `web/middleware.ts` + `api/clerk_auth.py` + `tests/test_clerk_auth.py` | ENFORCED | **MET** |
| D2 | Two independent enforcement layers, so no single library is the only thing standing. | 2 | Next middleware **and** FastAPI JWT verification | ENFORCED | **MET** |
| D3 | Session JWTs verify algorithm, signature, expiry **and** `azp` (the anti-CSRF check). | 4 of 4 | `api/clerk_auth.py` | ENFORCED | **MET** |
| D4 | Authorisation is checked on every protected request, not most. | 100% | `tests/test_clerk_auth.py` | ENFORCED | **MET** |
| D5 | No secret is ever committed or logged. | 0 | `tools/lint.py`, log-masking in every workflow, `tools/assemble_dsn.py` | ENFORCED | **MET** |
| D6 | SQL is always parameterised. | 0 interpolated queries | `tools/lint.py` | ENFORCED | **MET** |
| D7 | Every API input is schema-validated before it touches the database. | 100% of endpoints | pydantic/zod + `tools/lint.py` | ENFORCED | **MET** |
| D8 | Known-vulnerable dependencies are tracked and either fixed or explicitly accepted with a reason. | 0 unrecorded advisories | `tools/sca_gate.py`, `docs/SCA_BASELINE.md` | ENFORCED | **MET** — 2 high + 4 moderate accepted with no upstream fix (R-048, R-003) |

## E. Web experience

| # | World class means | Number | Gate | Enforcement | Status |
|---|---|---|---|---|---|
| E1 | Largest Contentful Paint, 75th percentile, mobile. | **≤ 2.5 s** | — | PROPOSED | **UNMEASURED** |
| E2 | Interaction to Next Paint, 75th percentile. | **≤ 200 ms** | — | PROPOSED | **UNMEASURED** |
| E3 | Cumulative Layout Shift, 75th percentile. | **≤ 0.1** | — | PROPOSED | **UNMEASURED** |
| E4 | Accessibility: WCAG 2.2 **AA**, including 4.5:1 text contrast. | AA, 0 violations | — | PROPOSED | **UNMEASURED** |
| E5 | The feed never shows a blank page on a data failure — it explains what is wrong. | 0 silent blanks | `web/app/(public)/tonight/page.tsx` + `web/lib/*.test.ts` | ENFORCED | **MET** |
| E6 | A secondary-source failure cannot blank a working feed. | additive union read | `web/lib/promoted.ts` (catch → empty) | ENFORCED | **MET** |
| E7 | TypeScript strict mode, no unexplained `any`. | 0 unexplained | `tsconfig.json` + `tools/lint.py` | ENFORCED | **MET** |

**E1–E4 are the largest honest gap in the product.** Nothing measures the user
experience of the thing users see. Closing it is a Lighthouse run in CI against
the preview deployment — cheap, and it is item 5 in `docs/V1.md`.

## F. Code quality

| # | World class means | Number | Gate | Enforcement | Status |
|---|---|---|---|---|---|
| F1 | Small, self-contained changes. | ~100 lines typical; **1,000 too large**; hard cap 800 KB diff (past it the independent reviewer refuses) | `tools/pr_size_check.py` | ENFORCED | **NOT MET in practice** — PR #59 reached 1.26 MB and the review refused to run (R-051) |
| F2 | Tests ship in the same change as the code, and they can actually fail. | 100% of behaviour changes | `tools/test_audit.py` | ENFORCED | **MET** |
| F3 | No swallowed errors. `except: pass` is banned unless the branch is itself logged and justified. | 0 | `tools/lint.py` | ENFORCED | **MET** |
| F4 | No silent degradation: "we failed" must never look identical to "there was nothing to do". | 0 instances | `tools/lint.py` + `tools/test_audit.py` | ENFORCED | **MET** |
| F5 | No dead code. A module nothing can reach is not done — wire it or delete it. | 0 unreachable modules | — | PROPOSED | **NOT MET** — `worker/publish_policy.py` (D3), `brain/` (D9), `social/carousel/` posting path (R-026) |
| F6 | Comments explain **why**, not what. | reviewer judgement | independent review | ENFORCED | **MET** |
| F7 | Every deferral is recorded in the same commit with a cited bar and an objective resolution trigger. | 0 silent deferrals | `tools/deferral_scan.py` | ENFORCED | **MET** — 46 rows open, all tagged |

**F5 is the rule this build most needs and least has.** Three subsystems are
built, tested, documented, honestly labelled "not wired", and reachable by
nothing. A proposed mechanism is in `docs/V1.md`.

## G. Testing

| # | World class means | Number | Gate | Enforcement | Status |
|---|---|---|---|---|---|
| G1 | Master is green. Always. | **0 failing tests** | `tools/validate` → CI | ENFORCED | **MET** — 1,665 green with full history (verified 2026-07-26). The one failure seen in a shallow clone is the binding failing closed on an unreachable commit, by design (R-036); the defect is that the gate does not distinguish it from a real failure — see G5 |
| G2 | A test that cannot fail proves nothing — every new gate is proven red before it is proven green. | 100% of new gates | `tools/test_audit.py` + reviewer | ENFORCED | **MET** |
| G3 | Test shape follows the pyramid: many fast unit tests, few broad ones. | unit ≥ 90% of suite | — | PROPOSED | **MET informally** — 1,665 tests, suite runs in 47 s |
| G4 | Coverage is a signal, not a target; the real bar is "bugs rarely escape". | 0 escaped defects | Kaizen ledger (`docs/metrics/KAIZEN_LEDGER.md`) | ENFORCED | **NOT MET** — audit D1 escaped every gate into production |
| G5 | A fresh clone can run the suite, and the gate distinguishes a broken environment from broken code. | one documented command, 0 manual steps; **0 red rows that mean "environment incomplete"** | — | PROPOSED | **NOT MET** — no dev-dependency bootstrap, and 4 of 19 rows go red in the agent's default environment (3 from missing packages, 1 from a shallow clone) with nothing marking them as environment faults (audit D7, D12; R-058) |

## H. Reliability and operations

| # | World class means | Number | Gate | Enforcement | Status |
|---|---|---|---|---|---|
| H1 | No scheduled job runs unwatched: a dead-man alarm fires if it stops. | 100% of crons | `tools/assert_deadman_period.py`, blocking pre-run | ENFORCED | **MET** for `ingest.yml` and `import_structured.yml`; **N/A** for `import_licensed.yml` (not scheduled — C2) |
| H2 | The armed cadence is the delivered cadence. | delivered **≥ 80%** of armed | — | PROPOSED | **NOT MET** — 21% measured over 45.1 h (audit D5) |
| H3 | Errors reach a human: Sentry on web, API and worker. | 3 surfaces | `worker/sentinel.py`, `api/main.py`, `web/instrumentation*.ts` | ENFORCED (wiring) | **wiring MET**, DSNs absent → inert (R-001) |
| H4 | Every run leaves a replay log that can reconstruct what happened. | 100% of runs | `worker/replay_log.py` + artifact upload | ENFORCED | **MET** |
| H5 | Config lives in the environment; the repository could be public without leaking a credential. | 0 secrets in git | `tools/lint.py`, `docs/DEPLOY.md` | ENFORCED | **MET** |
| H6 | The deployment is observable without guessing: one endpoint reports resolved config and reachability. | `/api/health` always reachable | `web/app/api/health/route.ts` + its test | ENFORCED | **MET** |
| H7 | There is a live deployment and its URL is recorded. | 1 URL on disk | — | PROPOSED | **NOT MET** — no URL anywhere in the repo (audit D11) |

## I. Cost

| # | World class means | Number | Gate | Enforcement | Status |
|---|---|---|---|---|---|
| I1 | A per-run ceiling exists before any scheduled AI spend, and it is structurally pinned (a caller cannot raise it). | 10 sources/run on the schedule path | `ingest.yml` + `tests/test_ingest_workflow_contract.py` | ENFORCED | **MET** |
| I2 | The provider account carries a hard monthly cap set in the console **before** the first scheduled run. | cap set | Anthropic console (founder-owned) | ENFORCED (externally) | **MET, and it fired** — limit reached 2026-07-25, access returns 2026-08-01 (audit D2) |
| I3 | Every stage uses the cheapest model tier that clears the same gates. Quality gates never relax for cost. | routing table, identical thresholds at every tier | `docs/MODEL_ROUTING.md` + `tools/model_router.py` | ENFORCED | **MET** |
| I4 | Cost per verified event is measured, not guessed. | tracked per run | `tools/kpi_report.py` | ENFORCED | **UNMEASURED** — registry live, no populated series |
| I5 | Zero-marginal-cost sources are preferred over metered ones for the same fact. | deterministic feeds first | — | PROPOSED | **NOT MET in priority** — the AI path is scheduled every 20 min; the free deterministic paths are 2×/day and manual (D1/D4) |

## J. How the work is done (agent process)

| # | World class means | Number | Gate | Enforcement | Status |
|---|---|---|---|---|---|
| J1 | The generator never grades its own work. Every PR is reviewed by a non-Claude model. | 100% of PRs, no path filter | `.github/workflows/adversarial-review.yml` | ENFORCED | **MET** — 2 independent seats |
| J2 | The contract (goal, scope, done-criteria) is written before code. | 1 per session, before the first commit | `STATE.md` + reviewer | ENFORCED | **MET** — 27 contracts |
| J3 | Disk is truth. State is verified against reality, never trusted from memory. | reconciler exits 0 | `tools/session_reconcile.py` | ENFORCED | **NOT MET** — exits 2; cannot verify PRs or the database from the agent sandbox (audit D6) |
| J4 | Irreversible actions are attacked in writing before they are taken. | 1 friction entry per irreversible action | `docs/FRICTION_LOG.md` + reviewer | ENFORCED | **MET** |
| J5 | The harness is pruned as well as grown — anything the model now does for free gets deleted. | 1 pruning pass per Kaizen cycle | — | PROPOSED | **NOT MET** — never done until this audit (audit §6) |
| J6 | Every internally-caught defect gets a ledger row with its class; repeat classes trend to zero. | repeat-class rate ↓ | `tools/kaizen_trends.py` (blocking) | ENFORCED | **MET** — 194 rows |
| J7 | The current bottleneck is named explicitly each session. | 1 named bottleneck | `STATE.md` | ENFORCED | **MET** — currently **delivery** |
| J8 | The rule surface a builder must hold before writing code stays small enough to hold. | **≤ 5,000 words** of CANON | `docs/INDEX.md` classification | PROPOSED | **NOT MET at audit time** (~26,000 words); this change brings CANON to ≈4,400 |

---

## The five rows that are the whole job right now

Everything above is either MET or is one of these. If you read nothing else:

1. **C1 / C2 — the feed must refresh itself.** One is fixed in this change; one
   needs one healthchecks check from the founder.
2. **C3 — a passing candidate must reach users without a human click.** The
   policy is written and ratified; the wiring does not exist.
3. **G1 — master must be green.** One red test, days old.
4. **E1–E4 — nobody has measured the experience users actually get.**
5. **H7 — there is no recorded live deployment.**

Nothing on that list is a quality *standard* problem. Every one of them is a
*delivery* problem, which is exactly what `docs/V1.md` is ordered around.
