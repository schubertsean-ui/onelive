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

**The scoreboard, 80 rows:** **51 MET** · **14 NOT MET** · **12 UNMEASURED** ·
**2 NOT BUILT** · **1 partial** (H1, met for the two jobs that are scheduled).

**The split that matters is not the total — it is where the misses cluster.**

**A rule about the PROPOSED rows**, added at the PR #76 review: **every PROPOSED → ENFORCED transition gets its own reviewed PR.** A bar row silently becoming blocking is a gate-threshold change arriving without review, which is the one direction this file must never move on its own.

| Section | MET | Not met / not built / unmeasured |
|---|---|---|
| **P — purpose and felt experience** | 6 of 14 | **8** |
| A–J — the engineering underneath | 45 of 66 | 21, and most are built-but-unwired |

**Nothing on any NOT MET list needs a new standard.** Every engineering miss is
something built and not connected, or never measured. But the P section is the
honest indictment: the machine is in far better shape than the experience it exists
to deliver, and **P1 — the ten-second answer, the single most important number in
this product — has never been measured once.**

---

# §0 — What this is for

Everything below section P exists to keep one promise. Founder directive,
2026-07-26: *"Everything is to be built toward the vision and goals and objectives
and other content surrounding this project and how it is supposed to work and make
people feel. All actions should be in support of all of those things."*
(`docs/memory/decisions/2026-07-26_vision-first-directive.md`.)

The canonical text is `docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md` §1–§6,
ratified. It is quoted here, never paraphrased — paraphrase is how canon drifts.

> **Vision:** "A world where live music is easy to find, fairly represented, and
> culturally valued. At scale: to let culture grow without being stripped of its
> soul."
>
> **Mission:** "To assemble truth about live music, protect discovery from
> distortion, and help real culture travel."
>
> **What ONE LIVE is:** "a system of record for what's really happening tonight —
> artist-first by structure, trust-driven, calm, useful, real. Culture becomes
> infrastructure, not content."
>
> **What ONE LIVE is not:** "not ticketing, not a social feed, not pay-to-play, not
> an algorithm chasing engagement."

**The moment the whole product is built for** (brief §3):

> "It's 9:04 PM on a warm Austin night. You're on a sidewalk on East 6th, phone in
> one hand, a friend saying 'so what are we doing?' … You have about ten seconds of
> everyone's patience."

**The feeling to create** (brief §3) — this is a specification, not decoration:

> "the small thrill of *anticipation* — the night is still unwritten and full of
> real options — fused with *calm certainty*: this thing knows, and it's right. No
> FOMO anxiety, no doomscroll dread, no decision fatigue. The feeling of a friend
> who always knows what's on and has never once been wrong — and never makes it
> about themselves."

**The payoff, and the whole brand in one sentence** (brief §5):

> "The fan locks their phone within ten seconds holding a decision they feel good
> about, and the show is exactly as promised when they walk in. That kept promise,
> repeated nightly, is the entire brand."

**What the product is for** — founder's words, and now ratified canon (brief §3, as
amended 2026-07-26: *"Use the new description for the tagline. Remove the old."*):

> *"This is about finding and engaging in experiences, helping individuals and the
> culture thrive."*

Copy decisions pull toward what a night can **give**, never toward what the app
removes. **There is no tagline on any product surface** — the masthead carries the
city and the date, nothing else. The former defensive line is struck from canon and
from every comp, and is a FORBIDDEN string in `tests/test_design_proposals.py`, so
it cannot return without a red test.

**How to use §0.** It is a blocking question in review, at the same standing as a
failing test: *does this change serve the fan on the sidewalk at 9:04 PM?* A change
that is correct, fast, well-tested and makes that moment worse is not done. A
reviewer may block on §0 alone.

---

## P. Purpose and felt experience — the reason the rest exists

Placed first deliberately. Rows P1–P14 are the product; A–J are how it is kept
honest.

| # | World class means | Number | Gate | Enforcement | Status 2026-07-26 |
|---|---|---|---|---|---|
| P1 | **The ten-second answer.** A stranger with no account answers "what should I do tonight?" and locks their phone with a decision they feel good about. | **≤ 10 s** from first paint to decision | — | PROPOSED | **UNMEASURED** — the single most important number in the product and nothing measures it (R-061) |
| P2 | **It feels instant.** The feed is usable before impatience starts. | **≤ 2.0 s** load (brief §1). *Where canon disagreed, the stricter number won: Core Web Vitals' LCP ≤ 2.5 s is the floor of external acceptability, 2.0 s is the product bar* | — | PROPOSED | **UNMEASURED** (see E1) |
| P3 | **No account, no login, no onboarding, no cognitive tax.** The first rewarding moment arrives in seconds. | 0 required accounts, 0 onboarding steps | `web/middleware.ts` (public feed is open; `/ops` denied) + `web/lib/auth.test.ts` | ENFORCED | **MET** |
| P4 | **Trust is shown, never claimed.** No badges, no shields, no checkmarks, no "verified"/"confirmed" text, no trust-score chrome, no star ratings. | **0** badge elements in any shipped surface | design rubric + `web/lib/trust.test.ts` | ENFORCED | **MET** |
| P5 | **Honesty is a courtesy, never an alarm.** Lower certainty is one small quiet icon; tapping opens a calm, one-tap-dismissible sheet with the venue's own link. | 1 icon, 0 labels, 0 colour alarms, ≤ 1 tap to dismiss | `web/lib/trust.ts` + its test | ENFORCED | **MET** |
| P6 | **Nothing real is ever hidden and money never decides what is seen.** Uncertain shows still appear; sponsored anything, if it exists, is outside discovery. | 0 hidden real events, 0 paid ranking inputs | `tools/trust_gate.py` (see A5, A7) | ENFORCED | **MET** |
| P7 | **The kept promise.** The show is as promised when the fan walks in. | **≥ 99%** of published events accurate on time / venue / existence, sampled | — | PROPOSED | **UNMEASURED** — extraction accuracy is measured (B1: 0.63% hallucination) but *published-event accuracy against the real world* is not (R-062) |
| P8 | **Every real show is findable.** Coverage is the mission, not a metric of convenience. | coverage denominator defined and tracked per city | — | PROPOSED | **UNMEASURED** — CAPCOG denominator is an open question (R-025; PR #74 in flight) |
| P9 | **Artist-first by structure.** An artist is findable without paying, and a creator's own words always beat ours. | creator override wins 100% of the time | Descriptor Foundry + Emotion Glyph creator control (brief appendices) | PROPOSED | **NOT BUILT** — claim flow and creator dashboard do not exist yet |
| P10 | **AI never speaks over the artist.** A machine-drafted descriptor is a placeholder and a reason to claim: composed only from the artist's own materials, faithfulness-gated, marked without shouting. | 0 invented facts; 100% of AI descriptors through the Foundry (6 candidates → pairwise knockout → fusion → independent judge → provenance) | `ai/eval_harness.py` + golden-set regression | PROPOSED | **NOT BUILT** — the Foundry is specified, no descriptor ships today |
| P11 | **Curiosity, honestly opened.** A card shows enough to activate a question and not so much that there's no reason to tap. | every card carries ≤ 1 deliberate hook | design rubric criterion 8 (click-pull) | PROPOSED | **UNMEASURED** |
| P12 | **White-hat only.** Every persuasive mechanism passes the reflection test: shown exactly how the screen influenced them, the user says "yes, that's what I wanted anyway." | **0** dark patterns — no fake scarcity, no guilt, no confirm-shaming, no streak-shaming, no engagement-chasing | design rubric + review | ENFORCED (by review) | **MET** — no such mechanism has shipped |
| P13 | **The daily edition.** Tonight happens once; the feed is dated, fresh, and finite. Anticipation over dread, never guilt for absence. | feed is bounded by tonight, refreshed ≥ 2×/day | C1, C2 | ENFORCED (the freshness half) | **NOT MET** — the freshness mechanism is broken/unscheduled (C1, C2) |
| P14 | **Emotional fidelity, scored not vibed.** Design work is graded against the brief's own 8-criterion rubric (10-second answer · night-sidewalk legibility · trust-by-craft · distinctiveness vs named competitors · emotional fidelity to §3 · accessibility · survivability · click-pull). | **≥ 4/5 on every criterion**, deltas logged never silent | brief PART C rubric, applied on every design PR | ENFORCED (process) | **UNMEASURED against a shipped surface** |

**Read the P column honestly.** Six rows MET, one NOT MET, two NOT BUILT, five
UNMEASURED. Compare that with the engineering sections, which are overwhelmingly
MET. **The machine is in far better shape than the experience it exists to
deliver** — and P1, the ten-second answer, is the single most important number in
this product and has never been measured once.

That asymmetry is the true headline of the 2026-07-26 audit, sharper than the
word-count findings, and it is why `docs/V1.md` now carries experience
done-criteria rather than only mechanical ones.

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
| C1 | Tonight's feed is fresh: the newest data is younger than one refresh cycle. | **≤ 12 h** since the last successful import | dead-man alarm per scheduled import (`watchdog_check`, `event=schedule` only) | ENFORCED | **NOT MET, measured** — the local-venue import has still never completed a SCHEDULED run: 4 successes ever, all manual `workflow_dispatch`, most recent 2026-07-25T19:22Z. The fix is on the PR #76 branch, not on master, so the cron on master still dies in its own guard (R-054). Flips when one scheduled run completes green |
| C2 | The ticketed feed refreshes without a human. | scheduled, **≥ 2×/day** | `import_licensed.yml` `cron: "23 2,14 * * *"` + `tools/watchdog_check.py` | ENFORCED | **MET (scheduled 2026-07-26, founder: "do 2"), pending first-run proof** — 12-hourly at 02:23/14:23 UTC, offset from `import_structured.yml`; watched by `watchdog.yml`. Flips to plain MET when a scheduled run completes green (R-055) |
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
| E1 | Largest Contentful Paint, 75th percentile, mobile. | **≤ 2.0 s** (the brief's number — see P2; Core Web Vitals' 2.5 s is the floor of external acceptability, not the bar) | — | PROPOSED | **UNMEASURED** |
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
| G1 | Master is green. Always. | **0 failing tests** | `tools/validate` → CI | ENFORCED | **MET** — green with full history, verified 2026-07-26: **1,665** on the audited tree, **1,671** with this change's six new tests. The one failure seen in a shallow clone is the binding failing closed on an unreachable commit, by design (R-036); the defect is that the gate does not distinguish it from a real failure — see G5 |
| G2 | A test that cannot fail proves nothing — every new gate is proven red before it is proven green. | 100% of new gates | `tools/test_audit.py` + reviewer | ENFORCED | **MET** |
| G3 | Test shape follows the pyramid: many fast unit tests, few broad ones. | unit ≥ 90% of suite | — | PROPOSED | **MET informally** — 1,665 tests, suite runs in 47 s |
| G4 | Coverage is a signal, not a target; the real bar is "bugs rarely escape". | 0 escaped defects | Kaizen ledger (`docs/metrics/KAIZEN_LEDGER.md`) | ENFORCED | **NOT MET** — audit D1 escaped every gate into production |
| G5 | A fresh clone can run the suite, and the gate distinguishes a broken environment from broken code. | one documented command, 0 manual steps; **0 red rows that mean "environment incomplete"** | `requirements-dev.txt` + `tools/bootstrap_dev.sh` + `tools/env_preflight.py` (informational, wired `|| true`) | ENFORCED | **MET 2026-07-26** — one command (`bash tools/bootstrap_dev.sh`) creates the venv, installs every declared dev dependency and un-shallows the clone; `env_preflight` names MISSING-TOOL / UNPROVABLE-HERE at the top of every run so no red row is ambiguous. Verified against bare system python: it names exactly the three package rows the audit found. **No check was loosened** — the preflight always exits 0 and changes no verdict, asserted by test (R-058) |

## H. Reliability and operations

| # | World class means | Number | Gate | Enforcement | Status |
|---|---|---|---|---|---|
| H1 | No scheduled job runs unwatched: a dead-man alarm fires if it stops. | 100% of crons | `tools/assert_deadman_period.py` (healthchecks path) + `tools/watchdog_check.py` / `watchdog.yml` (GitHub-native path, founder-approved 2026-07-26) | ENFORCED | **MET for all three scheduled jobs.** `ingest.yml` and `import_structured.yml` via healthchecks pings; `import_licensed.yml` via the watchdog's `WATCHED` table, added in the same change that scheduled it. Every scheduled workflow must appear in the watchdog's WATCHED / EXPECTED_SOON / EXCLUDED tables with a reason — enforced by `tests/test_watchdog_check.py`. Weakness stated: the watchdog shares GitHub's failure domain (R-060) |
| H2 | The armed cadence is the delivered cadence. | delivered **≥ 80%** of armed | — | PROPOSED | **NOT MET** — 21% measured over 45.1 h (audit D5) |
| H3 | Errors reach a human: Sentry on web, API and worker. | 3 surfaces | `worker/sentinel.py`, `api/main.py`, `web/instrumentation*.ts` | ENFORCED (wiring) | **wiring MET**, DSNs absent → inert (R-001) |
| H4 | Every run leaves a replay log that can reconstruct what happened. | 100% of runs | `worker/replay_log.py` + artifact upload | ENFORCED | **MET** |
| H5 | Config lives in the environment; the repository could be public without leaking a credential. | 0 secrets in git | `tools/lint.py`, `docs/DEPLOY.md` | ENFORCED | **MET** |
| H6 | The deployment is observable without guessing: one endpoint reports resolved config and reachability. | `/api/health` always reachable | `web/app/api/health/route.ts` + its test | ENFORCED | **MET** |
| H7 | There is a live deployment and its URL is recorded. | 1 URL on disk | `.github/workflows/site_health.yml` (reads `/api/health` from a runner) | ENFORCED | **NOT MET — one reason left of the original three, and it is stability, not reachability.** A preview URL is on disk (`docs/V1.md` §Deployment) and was **measured** on 2026-07-26 (run 30217359539): `http_status: 200`, `ok:true`, `supabase.reachable:true`, **`eventCount: 1532`** — publicly openable by anyone holding the bypass link. The two blockers this cell previously named (host-protected 302; `eventCount` unverified) are closed by that measurement. What remains: the URL is a **branch alias that dies on merge**, so it is not yet a URL that *is* the product. Flips when the post-merge production URL is recorded (R-070) |

## I. Cost

| # | World class means | Number | Gate | Enforcement | Status |
|---|---|---|---|---|---|
| I1 | A per-run ceiling exists before any scheduled AI spend, and it is structurally pinned (a caller cannot raise it). | 10 sources/run on the schedule path | `ingest.yml` + `tests/test_ingest_workflow_contract.py` | ENFORCED | **MET** |
| I2 | The provider account carries a hard monthly cap set in the console **before** the first scheduled run. | cap set | Anthropic console (founder-owned) | ENFORCED (externally) | **MET, and it fired** — the cap was reached 2026-07-25 and extraction stopped, which is the row working. **The reset date is deliberately NOT recorded here** (founder, 2026-07-26: *"Remove the 8/1 date — it was arbitrarily set by you"*): the API's own words are *"your **specified** API usage limits"*, i.e. a founder-owned setting raisable in about a minute, not a date to wait out. No step of the v1 plan waits on it (ask 2) |
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
| J8 | The rule surface a builder must hold before writing code stays small enough to hold, and every part of it is reachable in one sitting. | **≤ 4 documents**, and the word count is reported by `tools/health_check.py` rather than transcribed into prose | `docs/INDEX.md` classification + `tools/health_check.py` (measures it) | PROPOSED | **document count MET** (4: charter, bar, v1, loop). Word count: see the newest snapshot in `docs/health/`. Deliberately not quoted here — two earlier drafts of this row carried figures that were wrong within hours, which is the `false-confidence-gate` class; the number now lives in a command |
| J9 | **A founder-facing answer carries what the founder needs to act**: three options, one named recommendation, plain language, a walkthrough with full URLs and what-they-will-see, and the tradeoffs. | **7 required fields + ≥ 3 options** on every open ask | `tools/founder_ask_lint.py` (blocking, wired into `tools/validate`) | ENFORCED | **MET** — 3 open asks, all fully structured. Proven red first at 28 violations across 4 asks. Rule: `CLAUDE.md` prime directive 6, from four founder directives on 2026-07-26 (three options; working links; step-by-step of what I'll see; as little manual work as possible) |
| J10 | **A decision reaches the repo, not just the session** — every decision record names the commit, file, gate or Record row that implements it. | **100% of `docs/memory/decisions/`** | `tools/decision_codified_lint.py` (blocking) | ENFORCED | **MET** — 27 records, every one names what carries it. Proven red first at 25 violations of 25 records, then all backfilled; 4 honestly read `NOTHING YET` with a reason and a trigger. Founder directive 2026-07-26: *"confirm once a decision is made it has been codified in the code and not left in the session"* |
| J11 | **The founder's manual work is treated as the scarcest resource** — an option needing zero founder action beats a better one needing an action, and every ask states why it cannot be automated. | **0 asks without a `Why this needs you` justification**; open-ask count trending down | `tools/founder_ask_lint.py` | ENFORCED | **MET, and moving** — asks went 6 open → 3 on 2026-07-26 by automating rather than polishing: the healthchecks signup was replaced by `watchdog.yml` (zero setup), and ask 7 was folded into ask 6 because two asks wanted one secret |

---

## The five rows that are the whole job right now

Everything above is either MET or is one of these. If you read nothing else:

1. **C1 / C2 — the feed must refresh itself.** One is fixed in this change; one
   needs one healthchecks check from the founder.
2. **C3 — a passing candidate must reach users without a human click.** The
   policy is written and ratified; the wiring does not exist.
3. **G5 — the gate must stop lying about why it is red.** Master IS green (1,665 on the audited tree). Four of nineteen rows go red in the agent's environment for reasons that are not code. *(This item said "one red test, days old" until the PR #76 review caught it contradicting the corrected G1 row.)*
4. **E1–E4 — nobody has measured the experience users actually get.**
5. **H7 — the recorded deployment is not yet a stable URL.** *(This item said "there
   is no recorded live deployment" until 2026-07-26, when the site was measured at
   HTTP 200 with 1,532 events. What is left is that the URL is a branch alias which
   dies on merge — R-070, whose trigger is the merge itself.)*

Nothing on that list is a quality *standard* problem. Every one of them is a
*delivery* problem, which is exactly what `docs/V1.md` is ordered around.
