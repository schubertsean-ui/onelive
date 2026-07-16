# OneLive — STATE

Last updated: 2026-07-13 by Claude Code (Session Contract #1) — GENESIS package installed; PR state re-verified via GitHub API (PRs #9 + #10 MERGED — see the 2026-07-13 reality check); DB facts NOT re-verified this session (no DSN/connector in this sandbox).

Previous update: 2026-07-12 by Computer (PM) — reconciled against live ground truth (repo, PRs, Supabase migrations, DB row counts). **This session: PR #8 (agentic-harness buildout) reviewed cross-model, its findings fixed, and MERGED to master (HEAD a0b3724).** The `validate` gate no longer treats SKIP/ADVISORY as PASS (the founding anti-pattern is now impossible in the gate itself). **Corrected stale status: RLS migrations 0006/0007 ARE applied to the live DB, and 9 migrations total are live (incl. `source_geo_coverage`); `source` = 230 rows, but `event`/`event_candidate`/`candidate_evidence` are still 0.** Established the session-arc system — see `docs/session_arcs/`.

> **Session arcs:** chronological per-session records of decisions, findings, and artifacts live in `docs/session_arcs/`. This file (`STATE.md`) is the always-current rollup; arcs explain how the state got here. Latest arc: `docs/session_arcs/2026-07-12_harness-review-merge-and-live-reconcile.md`.

> **Operating rules:** how we work on OneLive (quality bar, Loops/Kaizen, trust rules, the Harness) is codified in `docs/OPERATING_RULES.md`. Read it with `CLAUDE.md`.

> **Start here every session:** run `docs/SESSION_START.md`. It runs `python tools/session_reconcile.py --heal` to verify the block below against live ground truth (git/PRs/DB) BEFORE you trust anything in this file. The block below is machine-maintained by that script — do not hand-edit it; fix the prose sections and let the script refresh the block.

<!-- GROUND_TRUTH:BEGIN -->
```json
{
  "git": {
    "branch": "master",
    "head": "a0b3724"
  },
  "prs": {
    "1": "merged",
    "2": "merged",
    "3": "merged",
    "4": "open",
    "5": "merged",
    "6": "merged",
    "7": "open",
    "8": "merged"
  },
  "reconciled_at": "2026-07-12T05:51:07.747368+00:00"
}
```
<!-- GROUND_TRUTH:END -->

> **Ground-truth block staleness (2026-07-13):** the JSON block above is machine-maintained and could NOT be refreshed this session — the reconciler needs `gh` (absent in this sandbox) and a DB DSN (not provided). It shows pre-PR#9 state. The 2026-07-13 reality check below records what WAS independently verified (via the GitHub API). Refresh the block with `session_reconcile.py --heal` from an env with `gh` + `ONELIVE_DB_DSN`.

## Where we are (updated 2026-07-15, session close — see arc 2026-07-14_first-real-run-ratchet-and-sensor-canon)

DONE this arc: PRs #14–#22 merged through the armed gate (M1 trend 5→1). All four Actions secrets landed (founder). FIRST REAL RUN: DB connected (266 sources), caps enforced, dead-man pinged, replay persisted; extraction failed LOUD on a retired model id (~$0, nothing false entered). R-006 RATIFIED at 1% + one-way ratchet (KAIZEN §M7, field-assertion unit). Sensor architecture + po/Kaizen are canon.

NEXT (top of queue, contract-first, evaluator mandatory): **Step 6 golden-set gate** — ≥40-example golden set (~320 facts, incl. injection cases), live-exam runner over the REAL provider path (design the documented exam channel past the R-013 gate carefully), blocking CI job; flag flips with a PASSING result → extraction unlocks → first real candidates → Step 7. Then: R-008 cron arming (po battery + friction attack first).

FOUNDER DECISIONS CLOSED 2026-07-15: PRs #4/#7 closed ("Close both" — R-009 resolved); 4-state confidence model CONFIRMED as final canon ("confirmed"). The same-day fifth-state question is RESOLVED: founder ratified the Certainty Display Stack ("Display stack accepted", 2026-07-15) — NO fifth state; state (frozen at 4) × freshness × provenance compose as attributes; event_status its own field (docs/strategy/ONE_LIVE_CERTAINTY_DISPLAY_v1.md, canon; Axes 2/3 + event_status build at Step 7). **No founder decision blocks the CRITICAL PATH (Steps 6–10).** The non-blocking founder-decision backlog remains OPEN in TODOS.md (monitoring-stack timing P1; trust-framework naming, payments, native-mobile timing P2; revenue reconciliation, sync licensing P3) — agents must not silently pick any of these.

## Session contracts — this PR renumbers its own to avoid collision (2026-07-15 merge reconciliation)
This research session originally numbered its contracts #5–#9; they are #14–#18 here so they don't collide with the `onelive-agent-management` (#5–#12) and `review-and-execute` (#13) sessions landing separately. Its deferrals moved R-013/R-014→R-016/R-017 for the same reason.

## Session Contract #18 (2026-07-15, research session `pr-aggregator-research` — founder: "Financial" + partial egress unblock [FIRST LIVE EDGAR RUN])

GOAL: Execute the beachhead-sector decision (FINANCIALS) and the first live EDGAR run now that www.sec.gov is reachable (data.sec.gov + efts.sec.gov remain proxy-blocked — remaining ask recorded).
SCOPE: (1) verify egress (www.sec.gov 200; data/efts still CONNECT-403); (2) LIVE RUN 1 (sprint step 4, financials): list real 8-Ks via browse-edgar Atom for JPM/BAC — both filed Q2 earnings 8-Ks TODAY — fetch real filing indexes, discover exhibits, fetch both EX-99.1 press releases with full provenance into eval/source_material/ (internal-only per the never-verbatim rule); (3) LIVE-RUN CATCH fixed same-commit: real filenames (letters/digits directly before "ex(hibit)99") missed the fallback regex — implemented the AUTHORITATIVE path our design promised (index-headers TYPE/FILENAME table, parse_exhibit_documents + find_ex99_exhibits_authoritative (renamed r22: returns ALL EX-99.x, not "the press release")), verified on both real filings, committed real fixtures + regression tests; fallback broadened, confidence semantics unchanged; (4) sector decision recorded + charter-mandated po battery run (seed 20260715, word "anchor", full canon, complete working notes) with 8-item harvest feeding the sector build; (5) bookends + R-017 progress note.
NON-GOALS: no extraction-model calls yet (R-017 still OPEN until ≥20 labeled real examples), no paid sources (R-016 unchanged), no scheduled polling (single budgeted run only, charter Sentinel rule untouched).
DONE-CRITERIA: live pipeline proven on real same-day filings · real source material stored with provenance · sector battery + records committed · tests green through the gate.
EVALUATOR r22 ADDENDUM (2026-07-15, same PR): review-diff policy for fetched third-party corpus accepted (excluded from diff, MANIFEST kept in-diff, hash-integrity tests in CI); five substantive fixes landed — LifecycleEvent gained `recorded_at` (knowledge horizon, distinct from observed_at) and the store's as-of reads now key on it (late-discovery regression test proves no time-travel); `record_source_retrieval()` public writer added (custody record type was a stub); fiscal periods now NEVER resolve to calendar dates (due_date=None, phrase kept — false-overdue blast radius closed) with the locking test corrected; `find_ex99_exhibits_authoritative` renamed for what it returns; repo-wide stale-reference sweep after the merge reconciliation (changelog headings #5–#9 → #14–#18, TODOS, README/sprint/module status banners trued up to greenlit + live-run reality).

## Session Contract #17 (2026-07-15, research session `pr-aggregator-research` — founder: "Go" [VENTURE GREENLIT — build phase 1, sector-agnostic core])

GOAL: Execute the promise-ledger build phase within this sandbox's hard limits (no sec.gov egress, no vendor-domain egress, no spend, no new services). "Go" resolves the venture go/no-go; it does NOT pick the beachhead sector (still founder's, memo stands) and does NOT waive R-016/R-017 — it FIRES R-016's trigger.
SCOPE: (1) record the greenlight (TODOS item checked, changelog); (2) R-016 fired-trigger handling: the primary-source pricing/ToS pass is egress-blocked from here — action what IS possible: committed draft redistribution-question letters to the four finalist providers (RTPR, FMP, StockNewsAPI, Benzinga) + R-016 row updated with the fired-but-blocked state and the founder unblock ask; (3) BUILD: point-in-time ledger store v0 (stdlib sqlite3, append-only event log per LEDGER_STORAGE_DESIGN.md — claim_recorded/lifecycle_event/source_retrieved records, as-of-known-when reads, corrections-as-events) + tests; (4) BUILD: due-date parser v0 (deterministic, no LLM — "by Q3 2027" / "in the third quarter of fiscal 2027" / month-year forms → date + kept original text per schema invariant) + tests; (5) VENTURE_SPRINT.md — numbered build plan to MVP with every gate marked (R-016/R-017/sector/friction), attacked by the evaluator through the PR gate; (6) bookends.
NON-GOALS: no extraction-model calls (R-017 blocks until real EDGAR examples), no provider contracts or spend (R-016 blocks until the re-verification pass runs), no sector choice, no deploy, no new external services.
DONE-CRITERIA: store + parser green with tests through the armed gate · letters + sprint plan committed · R-016 row updated same-commit · bookends updated.

## Session Contract #16 (2026-07-14, research session `pr-aggregator-research` — founder: "Keep moving forward" [promise-ledger venture pre-build groundwork])

GOAL: Advance the venture with FREE, REVERSIBLE groundwork only — the items the market analysis (§13/§14) says precede any build decision — without touching founder-crucial territory (no spend, no new services, no provider contracts — R-016 untouched; no beachhead-sector decision — that memo is prepared FOR the founder, not taken).
SCOPE: under `ventures/promise_ledger/` (standalone product workspace inside this repo; extracted to its own repo at founder go): (1) Claim Schema v0 — the H13 "promise markup" (spec + stdlib dataclass models + JSON Schema + tests); (2) extraction-precision golden-set EVAL HARNESS (fail-closed scoring; seeded with clearly-labeled SYNTHETIC examples only — real EDGAR seeds blocked by sandbox egress, recorded as R-017); (3) point-in-time ledger storage design doc (event-sourced, LEI-keyed, 4-state fulfillment confidence); (4) EDGAR ingestion client written to the documented API contract (compliant User-Agent, ≤10 req/s, bulk-first) with synthetic-fixture tests — connectivity limitation stated, never simulated away; (5) beachhead-sector decision memo for the founder (criteria + candidates, NO decision).
NON-GOALS: no live ingestion (egress-blocked), no extraction model calls (no spend), no sector choice, no go/no-go inference — "keep moving forward" is read as authorization for reversible groundwork, not as the venture greenlight (that TODOS item stays open).
DONE-CRITERIA: artifacts committed on the designated branch through the armed gate · tests green locally where deps allow and in CI · R-017 recorded · bookends updated.

## Session Contract #15 (2026-07-14, research session `pr-aggregator-research`, same conversation as #14 — founder: deep market analysis + full de Bono pass + whitespace revisit for the PR-aggregator venture)

GOAL: McKinsey-grade market analysis of the investment-research/disclosure-intelligence market for the PR-aggregator venture (standalone product; multibagger is context and prospective customer #1, NOT a required integration), then a full de Bono divergent pass (po battery per docs/skills/po_provocation.md — all operators, standalone + random-combos, movement techniques), then a convergent revisit mapping meaningful whitespace and improvement levers (content, quality, speed, cost, insight, combinatorial options).
SCOPE: (1) 3-agent research fan-out — market sizing/industry economics, buyer segments/willingness-to-pay, trends/discontinuities — provenance-labeled per the round-1–3 evaluator standard (no figure presented stronger than its evidence); (2) market analysis doc `docs/research/PR_AGGREGATOR_MARKET_ANALYSIS.md` (segmentation, sizing, value chain, five forces, positioning map, competitor tiers, buyer analysis, trends); (3) po battery run (`tools/po_battery.py`, seeded, full canon) + harvest table + M6 ledger row — provocations are stimuli, never facts, per charter; (4) whitespace/opportunity assessment incl. combinatorial plays; (5) bookends.
NON-GOALS: no build, no spend, no provider contracts (R-016 still gates); no OneLive pipeline changes; no venture go/no-go decision (founder-only).
DONE-CRITERIA: analysis doc committed on the branch with provenance labels · po battery run recorded with harvest · whitespace assessment delivered · bookends updated.
STATUS 2026-07-14: DELIVERED — `docs/research/PR_AGGREGATOR_MARKET_ANALYSIS.md` committed with 8 source appendices (`market_analysis_sources/A–H`; verbatim agent output except appendix C, which carries one additive editor REFUTED-verdict preserving the original citation in place — see its header), po battery run (seed 20260714, full canon, 16-idea harvest, M6 ledger row), whitespace + combinatorial assessment, and the founder's mid-session historical-data directive folded in as §12. Same provenance caveat as Contract #14: single-pass figures, not adversarially verified; R-016 still gates spend.

## Session Contract #14 (2026-07-14, research session `pr-aggregator-research` — founder-directed research task in a PARALLEL session; renumbered #5→#14 in the 2026-07-15 merge reconciliation. Contracts #5–#13 belong to the other two sessions and land with their PRs.)

GOAL: Research-only. Answer the founder's question: are there press-release (PR) aggregators with free/very-low-cost APIs, and is a "PR Aggregator + longitudinal analysis" product (ingest PRs per entity, diff vs prior PRs — what's new/changed/unanswered/undelivered — for investors/consultants/policy makers) viable, with real moats identified.
SCOPE: (1) deep multi-source web research (deep-research harness: fan-out search → fetch → adversarial claim verification → cited synthesis); (2) written report at `docs/research/PR_AGGREGATOR_RESEARCH.md` covering sources+pricing+licensing, legal posture, competitive landscape, moat assessment, recommended cheapest-viable ingestion stack; (3) session bookends (STATE/TODOS/changelog). Related context: founder's `multibagger` repo (investor audience) was attached to this session; the shared Perplexity space link is login-gated and could NOT be read.
NON-GOALS: no code, no ingestion build, no spend, no new services, no OneLive pipeline changes. This is a NEW-VENTURE research doc, not an OneLive feature; build would need its own contract + founder go.
DONE-CRITERIA: report committed on the designated branch · draft PR opened · bookends updated.
STATUS 2026-07-14: PARTIALLY DELIVERED, CONTRACT OPEN — report on branch (draft PR #18) with 22 claims verified 3-0 and 3 refuted+recorded, but the pricing/licensing verification half of the declared scope could NOT be executed from this sandbox (egress policy 403s vendor domains) and is answered provisionally from search-index/secondary reads. The contract is NOT closed as complete. Paths to closure (founder ask, added to TODOS): (a) founder accepts the narrowed scope with R-016 as the completion gate at venture greenlight, or (b) an unproxied environment (or relaxed egress policy for the listed vendor domains) is provided and the verification pass is run to finish the scope as written. FOLLOW-ON 2026-07-14: founder directed a phase-2 market analysis in the same conversation — see Session Contract #15.

## Session Contract #4 (2026-07-14, same conversation — founder: "Record it" [scale-out sensor architecture + first-party trust rule])

GOAL: Record the founder-ratified scale-out sensor architecture as canon, with the po battery run against it per the new charter rule.
SCOPE: docs/strategy/ONE_LIVE_SCALEOUT_SENSOR_ARCHITECTURE_v1.md (RATIFIED: watcher records not idle agents; pull/push/investigate modes; provenance-weighted gate — validated first-party assertion about own logistics enters at `confirmed`, via verified external channels OR authorized in-product accounts; scoped authority / no command authority / disputed-still-wins; scout swarm gated+capped; build triggers table — current critical path unchanged) + po harvest appendix (M6 ledger row) + TODOS/changelog wiring.
NON-GOALS: no code builds now (triggers: Step 7+); ingest mailbox = future founder decision; no trust-invariant changes (4-state model, AI-never-publishes, shown-never-hidden all unchanged).
DONE-CRITERIA: doc merged through the gate · decision anchors verbatim · harvest in ledger · TODOS carry the build triggers.

## Session Contract #3 (2026-07-14, same conversation — founder ratified "All three" [po + measures + levels-later] and directed a maximally robust po)

GOAL: Institutionalize divergent thinking (de Bono po) and Kaizen measurement without touching any trust gate's convergent behavior.
SCOPE: (1) research-grounded po protocol (`docs/skills/po_provocation.md`) with the founder-directed operator battery — escape/reversal-invert-opposite/exaggeration/distortion/wishful/absurd/random-entry + random×operator combos — and de Bono's movement techniques; (2) mechanical prompt generator `tools/po_battery.py` (+8 tests, seedable); (3) `docs/KAIZEN.md` + append-only `docs/metrics/KAIZEN_LEDGER.md` (measures M1–M6; zero ESCAPED defects absolute; internal catches mined by class), seeded with real PR #11–#14 data incl. the empty-env repeat-class watch; (4) charter section + SESSION_START close step 8 + standing TODOS items; (5) levels deferred behind R-012 (objective trigger: first real cron week).
NON-GOALS: no po output into memory/factual records; no gate threshold changes; no maturity levels yet.
DONE-CRITERIA: suite green incl. new tests · deferral_scan/lint/trust_gate green · PR opened through the armed gate · ledger's first rows written.

## Session Contract #2 (2026-07-13, same conversation — founder said "proceed with the sprint plan")

GOAL: Execute the unblocked scaffolding of SPRINT Step 5 (scheduled ingestion) without triggering any founder-crucial precondition.
SCOPE: (1) record PR #11 merge (evaluator gate now armed on master) in STATE/changelog; (2) per-run budget ceiling on the real ingestion run (`worker/run_once.py --max-sources` + `ONELIVE_MAX_SOURCES_PER_RUN`, §14.3 "caps before the recurring loop") with tests; (3) `.github/workflows/ingest.yml` shipped **manual-only** (`workflow_dispatch`; cron deliberately ABSENT until the founder arms P2/P3 — charter: no scheduled loop without dead-man + budget caps), failing loud on missing env; (4) consolidated founder unblock-list delivered in chat.
NON-GOALS this block: no cron trigger, no migrations, no spend, no extraction threshold ratification (proposed number stays PROPOSAL), no design implementation (design/inbox is empty).
DONE-CRITERIA: tests green · validate green (visual-regression skip acknowledged) · PR opened and it receives a real armed-gate evaluator verdict · founder unblock-list delivered.

## Session Contract #1 (2026-07-13 — this session)

GOAL: Stand up the autonomous build loop and take the first two steps toward the live site.
Scope (per `docs/ops/CLAUDE_CODE_KICKOFF_PROMPT.md`): (1) VERIFY repo+DB state and reconcile drift — report, don't fix silently; (2) EVALUATOR ONLINE — `tools/adversarial_review.py`; (3) FRICTION GATE ONLINE — `docs/FRICTION_LOG.md` + pre-work attack wiring; (4) SENTINEL MINIMUM — Sentry behind `SENTRY_DSN` on web+api+worker, healthchecks dead-man wrapper on the scheduled entrypoint; (5) PLAN ONLY — `docs/SPRINT_LIVE_SITE.md` for critical-path Steps 5→10.
DONE-CRITERIA: reconcile run (drift reported below) · verification report delivered · adversarial_review.py exercised on a real diff (skip-loud path — no key) · friction log exists with entry #1 (the sprint plan, attacked) · Sentry/no-op wired · sprint plan written. NOTHING deploys, migrates, or spends in this session. Constraint honored: zero deploys, zero migrations, zero spend.

## Reality check (verified 2026-07-13 — this session, via GitHub API + local git/pytest)

- **PR #9 (two-layer fail-closed Clerk stealth gate + PR#7 orchestrator reconcile) is MERGED** (2026-07-12T07:03Z) — master HEAD at session start = `3247ad7` = that merge. **This supersedes the 2026-07-12 claim below that GAP 1 (azp/CSRF) is blocked on unpushed commits: `api/clerk_auth.py` IS on master, azp validated, fail-closed.** PR #9's live test plan (real allowlist/azp rejection observed against a deployed instance) remains unexecuted — carried into `docs/SPRINT_LIVE_SITE.md` Step 8.
- **PR #10 (per-clause-cited world-class bar) is MERGED** — `docs/WORLD_CLASS.md` is in-repo canon.
- **Open PRs: #4 (draft, source-trust scoring + unapplied migration 0008) and #7 (orchestrator-harness).** PR #9 already ported #7's content onto master — recommend closing #7 as superseded (founder ack; see SPRINT precondition P4).
- **Test suite: 218 passed, 27 skipped, 1 environment-artifact failure fixed** — `test_fails_loud_on_unwritable_dir` fails only when run as root (root ignores chmod, so the unwritable-dir precondition can't exist); now skips honestly under euid 0. Matches the MASTER doc's claimed 219/27 (the 219th is this test on a non-root box). This resolves defect D1's ambiguity for the python side: canonical count = **219 passed / 27 skipped non-root; 218/28 as root** (+25 vitest, verified green this session).
- **DB facts UNVERIFIED this session** (no `ONELIVE_DB_DSN`, no Supabase connector in this sandbox). The 2026-07-12 row counts (source=230, event=0) are the latest verified numbers and were NOT re-checked. Per SESSION_START, do not treat as re-confirmed.
- **web build note:** `next build` fails at prerendering `/ops` without `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (pre-existing on master, verified by building clean `3247ad7`); builds green with a key present. Not introduced this session.
- **Genesis canon presence (charter Step 2):** WORLD_CLASS bar equivalent = `docs/WORLD_CLASS.md` (present). `OneLive_MASTER_the_whole_enchilada.md` has NO in-repo equivalent (not fabricated; the charter's Document Index points at `docs/source/` paths that only exist for the doc itself once the founder supplies the two source files).
- **New external dependencies (CLAUDE.md review rule #3):** `sentry-sdk` (api+worker requirements; no-op unless `SENTRY_DSN` set) and `@sentry/nextjs` (web; no-op unless DSN set). Both wired via `worker/sentinel.py` / `web/instrumentation*.ts`. No new services activated, no spend.
- **New harness pieces:** `tools/adversarial_review.py` (non-Claude evaluator gate; SKIPPED-loud without `OPENAI_API_KEY`, `--require` for CI), `docs/FRICTION_LOG.md` (entry #1 = sprint plan attacked, PROVISIONAL pending non-Claude re-attack), `docs/SPRINT_LIVE_SITE.md` (Steps 5→10 plan), healthchecks dead-man wrapper on `worker/run_once.py`.
- **The one missing item: `OPENAI_API_KEY`** — evaluator + friction attacks degrade gracefully but are NOT live. Minting is founder-crucial.

## Reality check (verified 2026-07-12 — this session)
- **Master HEAD = a0b3724** — PR #8 (agentic-harness buildout) MERGED this session after cross-model review (GPT-5.5, security + domain-truth-and-trust personas). All review findings fixed: `validate` silent-pass P1 (SKIP/ADVISORY → INCOMPLETE/exit 2, `--allow-skips` to acknowledge), `visual_regression` shell-injection P1, and four P2s (agent_review containment/secret-denylist, NUL-safe hook staging, commit_sweep empty-range=exit 2, test_audit patch()-mock detection). CI trust-gate green. Suite: 127 passed / 27 skipped.
- **DB: 9 migrations applied and live** (confirmed via `list_migrations` on `vqipjlvzfiwnandjumvx`): 0001-0007 + 0009 (`source_name_unique`) + `source_geo_coverage`. The RLS + narrowed-public-read migrations (0006/0007) are ALREADY LIVE.
- **Row counts (verified via `execute_sql`):** `source` = **230**; `event` = **0**; `event_candidate` = **0**; `candidate_evidence` = **0**. The pipeline has NOT run on real data — there are zero events.
- **Open PRs:** #4 (source-trust scoring, `feature/source-trust-scoring`) and **#7 (orchestrator-as-Harness + /tonight feed, `feat/orchestrator-harness`)** — both still OPEN/unmerged. The real ingestion orchestrator lives on #7; master only has the STUB `worker/run_once.py`.
- **GAP 1 (azp/CSRF) is BLOCKED, not closed.** It targets `api/clerk_auth.py`, which does NOT exist on master or on ANY remote branch. It lives only in the user's Clerk stealth-gate + Next-15 commits (f970e3a, 1a9728d, 35c5605) that were authored on the OLD sandbox and were **never pushed** (remote `feat/orchestrator-harness` = 3258a57, not the arc's 1a9728d). Pushing them is the user's step; this sandbox cannot reproduce or push them. See `LIVE_READINESS.md`.
- **"OneLive live" is not achievable end-to-end from this sandbox** — it requires (a) a real ingestion run to create events and (b) the unpushed auth gate; both depend on unmerged #7 work and on 3 local commits that only exist on the user's old sandbox. Fabricating events or a clerk_auth fix against absent files would be a §1 violation.
- Security advisors: only INFO-level `rls_enabled_no_policy` on the service-role-only tables — intentional/benign.

## Historical reality check (verified 2026-07-10)
- **Migrations 0001-0007 are ALL applied** to live project `vqipjlvzfiwnandjumvx` (confirmed via `list_migrations`).
- **PRs #1, #2, #3 are MERGED**; **PR #4 (source-trust scoring, migration 0008) is an open DRAFT**.
- **Source catalog IMPORTED (2026-07-10):** the `source` table now holds **43 rows** (all enabled, 15 source_types, avg credibility_weight 0.673), verified via `execute_sql count(*)`. Migration `0009_source_name_unique` (unique constraint on `source.name`) applied to make the import idempotent.
- **Real AI provider IMPLEMENTED (2026-07-10):** `ai/claude_provider.py` (`ClaudeProvider`) replaces the stub behind the `AIProvider` protocol. Fail-loud on misconfig (`ExtractionConfigError`), retry+audit-degrade on transient faults, `_provenance` stamping, hallucination-rate eval (`ai/eval_harness.py`). Requires `ANTHROPIC_API_KEY`. New dep `anthropic` noted here (CLAUDE.md review rule #3). 64 unit/integration tests green.
- **Remaining pipeline gap:** no orchestrator yet loops the 43 sources through `fetch → extract → gate → promote → /tonight` on real data. That is now the next bottleneck (was: catalog+provider, both now done).
- Security advisors: only INFO-level `rls_enabled_no_policy` on the 11 service-role-only tables — intentional/benign.

> NOTE: The historical sections below were written before the reconciliation above and describe some migrations/PRs as "NOT yet applied / not merged." That language is now superseded by the Reality check — kept verbatim for audit history.

## Phase 1 — feed pipeline hardening (this session)
Branch/PR opened against `master` (not merged). Changes:
- **4-state confidence enforced end-to-end.** New `worker/confidence.py` is the single
  source of truth (`CONFIDENCE_STATES`, `derive_confidence`, `renders_in_public_feed`,
  `FEED_PRIORITY`). `worker/promote.py` now derives confidence from evidence at
  promotion (anchor→`confirmed`, corroborated→`likely`, else `unverified`) instead of
  hardcoding `unverified`, and adds `set_event_confidence` / `mark_event_disputed`
  (disputed is set explicitly by ops, never inferred; the row is never deleted).
- **Disputed always renders.** `api/public.py` `/tonight` now ranks `disputed` explicitly
  (sorts last, never filtered); `/events` applies no confidence filter. A structural
  test guards that neither endpoint filters on confidence in its WHERE clause.
- **Anti-hallucination prompt.** New editable `ai/prompts.py::EXTRACTION_SYSTEM_PROMPT`
  instructs the model to extract only what is literally in the source and return
  null/empty otherwise. Wired through `ai/provider.py` (protocol), `ai/bedrock_provider.py`,
  and `worker/ai_extract.py`.
- **Entity resolution hardened.** `worker/resolve_entities.py` now does exact →
  pg_trgm trigram fuzzy (threshold 0.45) → placeholder, in that order, degrading
  gracefully to exact+placeholder if pg_trgm is absent.
- **New migration `supabase/migrations/0005_pg_trgm.sql`**: `create extension pg_trgm`
  + trigram GIN indexes on `venue.name` and `artist.name`. NOT YET APPLIED to the live
  Supabase project — apply via the migration tool before fuzzy resolution is relied on.
- **Tests added** in `tests/` (pytest): gate thresholds, 4-state transitions incl.
  disputed, and disputed-never-dropped guards. Pure-logic tests need no DB; an optional
  `@pytest.mark.dbintegration` suite runs against `ONELIVE_TEST_DB_DSN`. See README.
- New dependency note: tests use `pytest`; DB fuzzy matching depends on the `pg_trgm`
  Postgres extension (migration 0005).

## Phase 1 PR #1 review fixes (follow-up commit)
Addressed the 3 blocking issues both reviewers (Claude + GPT-5.5) flagged on PR #1:
- **Trigram GIN indexes now actually used.** `worker/resolve_entities.py` fuzzy step
  switched from `where similarity(name,x) >= t` (forces seq scan) to the pg_trgm `%`
  operator (`where name % <input>`), with the cutoff set via
  `SET LOCAL pg_trgm.similarity_threshold`. A `@dbintegration` EXPLAIN test asserts
  `idx_venue_name_trgm` is used. Migration `0005_pg_trgm.sql` comments updated.
- **No more orphan placeholder venues/artists.** `resolve_venue_id`/`resolve_artist_ids`
  no longer open their own connection or COMMIT — they take the caller's cursor.
  `worker/promote.py` runs them inside the same transaction as the dedupe check, so a
  dedupe ValueError rolls back any freshly-created placeholder entities (venue has no
  unique name constraint, so leaked placeholders used to duplicate on every retry).
  `worker/dedupe.py::find_possible_duplicates` gained an optional `cur=` param.
- **Fuzzy match is city-scoped.** The fuzzy fallback now applies the same city filter
  as the exact step, preventing cross-city merges (e.g. two venues named "Empire").
  Fuzzy merges are audited to `audit_log` (`action='fuzzy_match_merge'`, matched id +
  similarity + input name) plus a log line.
- **Tests added** `tests/test_resolve_entities.py`: 7 pure-logic tests (exact, fuzzy
  within city, cross-city rejection, placeholder, blank-name, artist path, threshold)
  via an in-memory FakeCursor, + 5 `@dbintegration` tests (skipped without
  ONELIVE_TEST_DB_DSN). Suite: 30 passed, 6 skipped.

## What's done
- Repo created at github.com/schubertsean-ui/onelive.
- Supabase project created (ref: vqipjlvzfiwnandjumvx, org: schubertsean-ui's Org, region: us-east-1). Status: **ACTIVE_HEALTHY** (Postgres 17.6.1.141).
- CLAUDE.md and STATE.md established.
- **Reference implementation code has been fully extracted and written into the repo.** The original reference build (DDL, worker pipeline, AI layer, API, web ops UI, mobile scaffold, source catalog) was recovered from uploaded `.pages`/`.pdf` files and transcribed into plain files under this repo:
  - `supabase/migrations/0001_core.sql` – `0004_ads.sql`: full DB schema (source, venue, artist, event, event_candidate, candidate_evidence, source_reliability, raw_fetch, raw_event, advertiser, ad_campaign, ad_creative, ad_placement_rule, audit_log)
  - `worker/`: full ingestion + candidate gating pipeline (source_rank, ai_models, gating, multiconfirm, candidate_store, ai_extract, resolve_entities, dedupe, promote, source_reliability, definition_of_done, fetch/, run_once)
  - `ai/`: provider abstraction, Bedrock provider, eval harness
  - `tools/import_sources.py`: source catalog importer
  - `api/`: FastAPI app (public.py, ops_candidates.py, deps.py, main.py) + `contracts/ops_inbox.contract.json`
  - `web/`: Next.js 14 Ops UI (inbox list, candidate detail, evidence form, promote action)
  - `mobile/`: Expo/React Native scaffold (`/tonight` screen)
  - `sources/master_sources_catalog_120.json`: 43 populated entries (ranks 1-41, 119-120); **ranks 42-118 are an explicit TODO gap**, documented in `sources/README.md`
  - `docs/Final_ONE_Live_Authoritative_Technical_Spec.md`: original reference handoff memo
  - PDF-extraction ligature typos (e.g. "conﬁdence" → "confidence", "ﬂoat" → "float", "oﬀer" → "offer") were fixed throughout during transcription.

## Architecture deviations from the reference build (intentional, documented)
- **DB engine:** Supabase-managed Postgres 17 replaces the reference build's local Docker Postgres 16. Schema lives in `supabase/migrations/*.sql` (applied via the Supabase migration tool) instead of `db/migrations/*.sql` + `db/apply_schema.sh` (raw psql script). **The legacy `docker-compose.yml`, `db/apply_schema.sh`, and `db/migrations/` local-Postgres path from the reference build was deliberately dropped** — Supabase is the only DB path going forward. If local-Postgres dev (no Supabase network dependency) is ever needed, re-add this path explicitly; it is not currently planned.
- **Confidence model:** `event.confidence` uses the 4-state model (`unverified|likely|confirmed|disputed`), not the reference build's 3-state model — per the earlier master-spec decision. Encoded with a comment in `supabase/migrations/0001_core.sql`.

## What's done (continued)
- All 60+ extracted files committed and pushed to `origin/master` (commit `5ecaa05`).
- All 4 SQL migrations applied to the live Supabase project (`vqipjlvzfiwnandjumvx`): `0001_core`, `0002_event_candidates`, `0003_raw_fetch`, `0004_ads`. Verified via `list_tables`: 14 tables live (source, venue, artist, event, audit_log, event_candidate, candidate_evidence, source_reliability, advertiser, ad_campaign, ad_creative, ad_placement_rule, raw_fetch, raw_event).
- GitHub Actions workflows added: `.github/workflows/pr-review.yml`, `source-backfill.yml`, `dependency-hygiene.yml`, plus `.claude/agents/gate-verifier.md` — copied verbatim from `OneLive_Build_Runbook.md` §1.6-1.7.

## Security — RLS + pg_trgm schema (migration 0006 written & PR'd, NOT yet applied)
Two Supabase security advisories are addressed by **`supabase/migrations/0006_rls_policies.sql`** (branch `security/0006-rls-and-pg_trgm-schema`, PR opened against `master`, **not merged and NOT yet applied to the live database** — the founder will apply it separately after review).

- **RLS enabled on all 14 public tables** with the founder-approved policy model:
  - Public read-only (`event`, `venue`, `artist` — `source_reliability` was removed from this bucket in the second review round, see below): RLS on + a `SELECT` policy (`public_read`) granting read to `anon` + `authenticated`. No write policies — writes only via the service-role backend connection, which bypasses RLS.
  - Service-role-only (the other 11: `source`, `source_reliability`, `event_candidate`, `candidate_evidence`, `audit_log`, `raw_fetch`, `raw_event`, `advertiser`, `ad_campaign`, `ad_creative`, `ad_placement_rule`): RLS on with NO policies → default-deny for anon/authenticated; the service-role backend is unaffected.
  - **Verified safe before writing:** the FastAPI backend (`api/`, `worker/`, `tools/`) connects via a direct `psycopg2` connection as the `postgres` superuser/service role (`ONELIVE_DB_DSN`), NOT the Supabase client SDK with an anon key — confirmed by grepping the whole backend (no `supabase`/`create_client` usage anywhere). service_role/superuser bypasses RLS, so this migration does not affect any current backend code path.
- **pg_trgm moved out of `public`** into a dedicated `extensions` schema (fixes the "Extension in Public" advisory). Drops the two trigram GIN indexes, drops & recreates the extension `SCHEMA extensions`, then recreates `idx_venue_name_trgm`/`idx_artist_name_trgm` with the schema-qualified `extensions.gin_trgm_ops` opclass. Both tables are empty in prod; migration is idempotent. **NOTE (updated in the second review round):** the `%`/`similarity()` calls in `worker/resolve_entities.py` are now **schema-qualified in code** (`OPERATOR(extensions.%)` / `extensions.similarity`), so resolution no longer depends on search_path; the `ALTER DATABASE postgres SET search_path TO public, extensions` is kept as defense-in-depth only.
- **Tests** in `tests/test_migration_0006_rls.py`: structural (no DB) asserting RLS on all 14 tables, only-SELECT/anon+authenticated policies on the 3 public-read tables, no policies on the 11 service-role tables, no write policies anywhere (including for-less `FOR ALL` evasion), and the pg_trgm move + schema-qualified index recreation; plus `@dbintegration` tests (skip without `ONELIVE_TEST_DB_DSN`) asserting pg_trgm lives in `extensions`, fuzzy resolution works after the move even without `extensions` on the default search_path, and that a schema-resolution failure fails loudly rather than silently degrading. Full suite: 40 passed, 9 skipped.

### Second review-round fixes (follow-up commits on the same PR #2 branch — NOT merged)
Both reviewers (Claude + GPT-5.5) re-reviewed `0006_rls_policies.sql`. Three findings, all addressed on the PR branch (still open, still not applied to the live DB):

1. **[Major] pg_trgm resolution no longer relies on search_path.** The `ALTER DATABASE postgres SET search_path TO public, extensions` was flagged as an unreliable fix — on Supabase, role-level search_path settings take precedence over the database-level default, so for the actual connection role that ALTER can be a no-op. Meanwhile `worker/resolve_entities.py::_fuzzy_match` swallowed *any* `psycopg2.Error` inside its SAVEPOINT, so an unresolved `%`/`similarity()` would silently degrade to placeholder-only matching → duplicate venue/artist rows, no error. **Fix:** the trigram operator and function are now **schema-qualified in code** — `OPERATOR(extensions.%)` and `extensions.similarity(name, …)` — so resolution does not depend on search_path at all. The `ALTER DATABASE` stays as **defense-in-depth only** (comment updated to say so). `_fuzzy_match` now **fails loudly** (logs an error + re-raises) on SQLSTATE `42883` (operator/function does not exist = schema-resolution failure), while still soft-falling-back to placeholder for other (genuinely transient) errors. New `@dbintegration` test `test_db_fuzzy_resolution_works_without_extensions_on_search_path` connects with `search_path = public` (no extensions) and asserts fuzzy match still resolves — proving the code fix, not the migration, is what works. New pure-logic tests cover the re-raise vs. soft-fallback branches.
2. **[Minor decision] `source_reliability` moved out of public-read.** Reviewers flagged that `event.private_access` / `event.is_private_rsvp` and `source_reliability`'s internal trust scores would be exposed to the anon key by `USING (true)`. Verified `source_reliability` is accessed **only** via the backend service-role connection (`worker/source_reliability.py`) — no API endpoint, no client SDK query it — so it was moved to the **service-role-only (no-policy) bucket**, removing the exposure with zero functional loss (now 3 public-read tables, 11 service-role-only). For `event` (which IS served publicly via `/tonight`), the `USING (true)` breadth is kept as an **accepted tradeoff** with an explicit code comment in the migration, flagged here for founder review → **DECISION TO REVISIT before the anon key is ever shipped client-side:** narrow the `event` policy (e.g. `using (is_private_rsvp = false and private_access = '{}'::jsonb)`) or move private events behind an authenticated-only policy. Safe today only because nothing uses the anon key yet.
3. **[Minor test quality] Negative-RLS test parsing hardened.** `tests/test_migration_0006_rls.py::_policies()` only matched policies with an explicit `for` clause, so a `for`-less `CREATE POLICY` (which defaults to `FOR ALL` = read **and** write) could slip past `test_no_write_policies_anywhere` / `test_service_role_tables_have_no_policies`. Parser now attributes a missing `for` as `all` and flags it as write-capable. Added `test_trigram_indexes_are_schema_qualified` asserting both GIN indexes use `extensions.gin_trgm_ops` (not a bare opclass).

Full suite after these fixes: **40 passed, 9 skipped** (the 9 skips are `@dbintegration`, need `ONELIVE_TEST_DB_DSN`).

## Security — narrowed event public-read RLS (migration 0007 written & PR'd, NOT yet applied)
Follows through on the accepted-tradeoff/DECISION-TO-REVISIT flagged in migration 0006's second review round (see item 2 above): **`supabase/migrations/0007_narrow_event_public_read.sql`** (branch `security/0007-narrow-event-public-read`, PR opened against `master`, **not merged and NOT yet applied to the live database** — the founder will apply it separately after review, same process as 0005/0006).

- **What changed:** 0006 gave `event` a `public_read` SELECT policy of `using (true)`, which exposed EVERY event row (including rows flagged private via `event.is_private_rsvp` / `event.private_access`) to the anon/authenticated Supabase key. 0007 drops and recreates that policy as:
  `using (is_private_rsvp = false and private_access = '{}'::jsonb)` — anon/authenticated can now only SELECT non-private events. Still SELECT-only, still granted to anon + authenticated. venue/artist policies are intentionally left as `using (true)` (no privacy columns).
- **Why now:** Phase 2 (PWA consumer screen + Clerk auth) is about to start and will ship the anon key client-side. 0006/STATE.md flagged narrowing "before the anon key is ever shipped client-side" — that time is now.
- **Verified zero effect on the backend:** the FastAPI backend (`api/`, `worker/`, `tools/`) reads via a direct psycopg2 service-role connection (`ONELIVE_DB_DSN`) which BYPASSES RLS. `/tonight` + `/events` continue to read ALL events (including private and disputed) exactly as before — RLS only constrains hypothetical future direct-Supabase-client (anon-key) reads, of which there are none yet. The confidence-never-filters guarantee is untouched.
- **Semantics note / flagged for founder:** `private_access` is a freeform jsonb carried straight from AI extraction (`ai_models.py` → `candidate_store.py` → `promote.py` → `event`) and surfaced verbatim in the API responses. **No code anywhere branches on its contents** — it is a passthrough blob today, so "empty jsonb = not private" is the only interpretation the current code supports, and 0007 uses it. IF a future use case gives `private_access` richer meaning (e.g. `{"ticket_holders": ...}` = "restricted to specific ticket holders" rather than fully private), this policy's `private_access = '{}'` test would over-hide such events from the anon key and should be revisited then. Implemented the straightforward interpretation per the current code; flagged here so the nuance isn't silently lost.
- **Tests** in `tests/test_migration_0007_narrow_event_read.py`: structural (no DB) asserting the event USING clause references BOTH `is_private_rsvp` and `private_access` (not `using (true)`), stays SELECT-only for anon+authenticated, introduces no write policy, and that venue/artist remain `using (true)`; a backend-guarantee test (no DB) asserting `/tonight`+`/events` still read via service-role psycopg2 (not the Supabase client SDK) and never filter on confidence; plus a `@dbintegration` test (skips without `ONELIVE_TEST_DB_DSN`) that creates public + private events and asserts an `anon`/`authenticated` role sees only the public one while the service-role connection still sees all. Full suite: **48 passed, 10 skipped**.

## Agentic harness buildout (2026-07-11, branch `feat/agentic-harness-buildout`)
Audited the build against two external agentic frameworks (Jamon Holmgren's 18-item
setup and the 20-step Loop Engineering roadmap) and built out every missing/partial
piece. All committed on the branch, full `tools/validate` gate green (7 PASS, 1
SKIP-loud for visual regression which needs a booted app). Test suite 78→120 passing.
- **Enforcement:** `tools/lint.py` (pure-stdlib conventions linter, `--fix`) +
  `.pre-commit-config.yaml` + `tools/install_hooks.sh` (hook runs lint --fix +
  trust_gate, blocks bad commits).
- **Single gate:** `tools/validate` runs trust_gate, lint, full pytest,
  eval_harness import, perf benchmarks, test_audit, commit_sweep, visual_regression
  (SKIP-loud headless), with a PASS/FAIL/SKIP summary; a skip is never counted green.
- **Quality instrumentation:** `tools/commit_sweep.py` (cross-commit gotchas),
  `tools/test_audit.py` (false-confidence test scan), `tests/test_perf_benchmarks.py`
  + `tools/profile_target.py` (perf budgets + profiling), `tools/visual_regression.py`
  + `tests/visual_baselines/`.
- **Autonomy + review:** `docs/skills/night_shift.md` (orchestration loop, layered
  exits, open/closed choice, hard stops), `docs/review_personas/` (6 cross-agent
  review lenses w/ doc ownership), `tools/agent_review` CLI, `tools/README.md`.
- **Docs + queue:** `docs/TESTS.md`, `docs/CODING_CONVENTIONS.md`, `TODOS.md`,
  `docs/AGENT_FEEDBACK.md`; git-tag-per-arc convention; all wired into CLAUDE.md /
  SESSION_START.md / OPERATING_RULES.md (nothing orphaned).
- **Known remaining world-class gap:** model-cost routing (Loop step 17) — no router
  yet; documented as prose in night_shift.md §4 and tracked in TODOS.md + AGENT_FEEDBACK.
- New dev-time deps (all optional, none required to run the app): `pytest` (already
  noted), and — only for the visual-regression capture path — a Playwright/headless
  browser + PIL, both gracefully absent-tolerant (fail-loud with install instructions).

## What's next
- **Next phase: public consumer PWA screen + Clerk auth wiring.** Clerk IS now connected
  to the project. Next step: wire the consumer feed UI and auth/claim flow. Nothing in
  Phase 1 blocks it. NOTE: Phase 2 will ship the anon Supabase key client-side, so
  `event`'s public-read RLS policy has now been narrowed (migration 0007, see Security
  section below) so the anon key can no longer read private events.
- Apply `supabase/migrations/0005_pg_trgm.sql` to the live Supabase project before relying
  on fuzzy entity resolution (exact + placeholder still work without it). NOTE: `0006`
  moves pg_trgm to the `extensions` schema and drops/recreates it, so apply `0005` then
  `0006` in order (or, if neither is applied yet, `0006` alone stands up pg_trgm in
  `extensions` with both indexes — but the migration chain expects 0005 first).
- **Apply `supabase/migrations/0006_rls_policies.sql`** (RLS policy model + pg_trgm schema
  move) after code review. Written and PR'd, NOT yet applied — see the Security section above.
- **Apply `supabase/migrations/0007_narrow_event_public_read.sql`** (narrowed event
  public-read policy) after code review — apply after 0006. Written and PR'd, NOT yet
  applied — see the Security section above. Required before the anon key ships client-side
  in Phase 2.
- Populate source catalog ranks 42-118 (target: 120+ sources total) — flagged as an ongoing gap, not blocking Phase 1.
- Connect Vercel + Clerk (see Accounts/services status below) before Phase 1 needs public preview/auth.

## Open founder decisions (pull from Spec §17 — do not let these silently lapse)
- [ ] Confirm 4-state confidence model finalized — CLAUDE.md already assumes this is decided.
- [ ] Trust framework naming: drop "ESIM" 3-pillar branding, or relabel as OneLive's own framing.
- [ ] Monitoring stack: Vercel Analytics + Supabase logs to start, Sentry before public launch.
- [ ] Payments: Stripe Connect only, or keep Trolley for international creator payouts.
- [ ] Year 1 revenue figure reconciliation ($1.2M vs $1.44M) — external materials only.
- [ ] Native mobile timing: PWA-first still holds, or does the existing Expo scaffold change that.
- [ ] Sync licensing as a future matching expansion — flag as Phase 3+ or rule out now.

## Known schema/architecture decisions already locked in
- **G-BRAIN (ratified 2026-07-13): build-agent memory = 1A file brain (`docs/memory/`, live) + 1B pgvector recall in the existing Supabase (build queued in TODOS); platform semantic memory at Sprint Step 7; option 1D (graph infrastructure) deferred behind the STANDING trigger G-BRAIN-1D — fire conditions and protocol in `docs/strategy/ONE_LIVE_BRAIN_OPTIONS_v1.md` §RATIFIED ("one investment serving both brains").**
- 4-state confidence model (not 3-state).
- Creator-Venue Matching (not Heartbeat Analytics) is the v1 differentiator.
- Tastemaker Content ships in Phase 2, before Matching (Phase 3) — it's the growth-loop mechanism.
- Tastemaker posts are a fully separate trust category from event data — never mixed.
- Supabase-managed Postgres is the only DB path (legacy local-Docker path dropped — see Architecture deviations above).

## Accounts/services status
- GitHub: connected, repo live.
- Supabase: connected, project live and ACTIVE_HEALTHY (ref vqipjlvzfiwnandjumvx).
- Vercel: connected.
- Clerk: connected.
- Sentry: not needed until Phase 4.
