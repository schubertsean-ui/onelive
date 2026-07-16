# TODOS — the task queue

Greppable summary: checkbox task queue, seeded from STATE.md's "What's next"
and "Open founder decisions" (2026-07-10 snapshot) plus this session's
harness-buildout follow-ups. Format: `- [ ] (P0-P3) Task — owner — context`.
Night-shift/autonomous work picks the highest-priority unchecked item it can
safely do without a founder decision (see `docs/skills/night_shift.md`).
Check items off in the same commit that completes them; don't batch-remove.

## Priority key
- **P0** — blocks a phase or ships something unsafe if skipped.
- **P1** — needed before the next phase's public surface ships.
- **P2** — real gap, not currently blocking.
- **P3** — nice-to-have / ongoing background work.

## Session Contract #1 follow-ups (2026-07-13 — genesis install; see docs/SPRINT_LIVE_SITE.md)
- [x] (P0) Mint `OPENAI_API_KEY` (usage-capped) — owner: founder (credential minting is founder-crucial) — the Independent Evaluator (`tools/adversarial_review.py`) and Friction attacks are wired but SKIPPED-loud without it; required before any trust-critical PR merges and before Step 5. **PROGRESS 2026-07-13: founder added the key as a GitHub Actions repo secret; `.github/workflows/adversarial-review.yml` now runs the evaluator with `--require` on trust-critical PRs. FURTHER PROGRESS (later 2026-07-13): founder reports the key was ALSO added to the Claude Code "onelive" environment — not visible to the already-running session (env injects at container start); VERIFY at next session start (`[ -n "$OPENAI_API_KEY" ]`), then run the in-session evaluator + non-Claude re-attack of FRICTION_LOG entry #1. **DONE for the CI leg 2026-07-13 (gate armed and has since adjudicated PRs #11–#22); the in-session env leg remains R-005.**
- [ ] (P0) Re-attack FRICTION_LOG entry #1 with the non-Claude evaluator once the key exists — owner: evaluator — entry is PROVISIONAL (attacked by the generator model, flagged).
- [x] (P1) Decide open PR #7 — **founder 2026-07-15: "Close both"** — #7 closed as superseded-by-#9; #4 closed as reference-draft for Step 7's provenance-weighted gate (closing notes on both PRs). R-009 RESOLVED.
- [ ] (P1) Mint `SENTRY_DSN` (web/api/worker) — owner: founder — wiring is done and no-op until it exists; needed before Step 9 preview traffic (R-001). **`ORCHESTRATOR_PING_URL` DONE 2026-07-15 (founder; verified live in the first real run's dead-man pings).**
- [ ] (P1) Execute PR #9's live gate test plan (non-allowlisted → /access; wrong azp → 403) once deploy env exists — owner: Generator — SPRINT Step 8.
- [ ] (P2) Supply `docs/source/OneLive_WORLD_CLASS_bar.md` + `docs/source/OneLive_MASTER_the_whole_enchilada.md` (the two genesis source-canon files) or amend the charter's Document Index to point at `docs/WORLD_CLASS.md` — owner: founder — MASTER doc currently has no in-repo equivalent.
- [ ] (P2) Clear the postcss SCA baseline entry (docs/SCA_BASELINE.md) when `next` ships with postcss ≥ 8.5.10 — owner: web — moderate, no fix available upstream as of 2026-07-13; CI re-audits on every web PR.
- [ ] (P2) Refresh STATE.md GROUND_TRUTH block via `session_reconcile.py --heal` from an env with `gh` + DB DSN — owner: next session with credentials — block is stale at pre-PR#9 state and could not be machine-refreshed from this sandbox.

## Brain (G-BRAIN RATIFIED 2026-07-13: "1A+1B, platform at Step 7")
- [x] (P2) Brain 1A — sharpened file brain: `docs/memory/` structure + conventions + seed entries. DONE 2026-07-13 (this ratification session).
- [ ] (P1) **Brain 1B build** — pgvector in the existing Supabase: migration `00xx_pgvector_agent_memory.sql` (extension into `extensions` schema + `agent_memory` table; written+PR'd, applied by founder per the established 0005–0007 process) + `tools/brain_index.py` (embed arcs/decisions/changelog; skip-loud without an embeddings key) + `tools/brain_recall.py` (semantic query at session start; **hybrid retrieval** — vector + Postgres full-text — with a cheap **rerank** pass, per the RAG addendum in `docs/strategy/ONE_LIVE_BRAIN_OPTIONS_v1.md`) + tests. Recall runs as an AGENTIC LOOP, not one-shot RAG (2026-07-14, from the Microsoft Foundry production-harness review): plan → try vector → evaluate → fall back to FTS/grep → combine; and it returns an explicit `no relevant memory` instead of forcing top-k when nothing clears the relevance bar — a confident wrong recall is worse than a miss. Trust-critical (SQL) → evaluator mandatory. Owner: next focused session, contract-first.
- [ ] (P2) Platform brain 2A — semantic event/artist/venue memory. **Gated on Sprint Step 7** (real rows exist); rides the same pgvector migration as 1B.

## Scale-out sensor architecture (RATIFIED 2026-07-14 — docs/strategy/ONE_LIVE_SCALEOUT_SENSOR_ARCHITECTURE_v1.md; RATIFIED ≠ build-now)
- [ ] (P1, gated on Step 7) **Watcher records** — entity schema + verified first-party channels + freshness SLOs + lifecycle states (incl. hibernation), same PR as the first-party-`confirmed` gate rule (trust-critical → evaluator mandatory).
- [ ] (P2, after Step 7) **Push channels** — ingest mailbox (FOUNDER decision: new service + credential) + RSS/ICS + official-social follows; matching-engine dedup eval cases join the golden set.
- [ ] (P2, after Step 7) **Scout swarm** — extend source-backfill into multi-lens discovery (caps + dead-man per scout); scouts propose, gate disposes.
- [ ] (P3) Po-harvest candidates from the battery run (multi-party authority, burst/hibernation lifecycle, per-source extraction templates, "confirm your listing" magic link, change-rate attention allocation) — triage into the pieces above at design time.
- [ ] (P2, STANDING — do not check off; re-evaluate when fired) **G-BRAIN-1D trigger watch** — founder-directed: option 1D (Graphiti + graph DB) is re-evaluated the moment graph infrastructure is needed, "one investment serving both brains." Objective fire conditions T1 (Emotion Graph build begins) / T2 (pgvector temporal-recall failures logged) / T3 (relationship queries outgrow SQL) are defined in `docs/strategy/ONE_LIVE_BRAIN_OPTIONS_v1.md` §RATIFIED. On fire: friction attack → founder decision (money/new services).

## Founder decisions needed (cannot be resolved by an agent — do not silently pick one)
- [x] (P1) Confirm 4-state confidence model finalized — **CONFIRMED by founder 2026-07-15 ("confirmed")**. This closes the 4-state decision ONLY.
- [x] (P2) **Certainty Display Stack proposal (fifth-state question)** — **RATIFIED by founder 2026-07-15 ("Display stack accepted")**: NO fifth state; state (frozen at 4) × freshness × provenance compose; event_status its own field (docs/strategy/ONE_LIVE_CERTAINTY_DISPLAY_v1.md, now canon). Axes 2/3 + event_status build at Step 7.
- [x] (P2) PR-aggregator venture go/no-go — DECIDED 2026-07-15: founder said "Go" (GREENLIT). R-016 trigger fired (letters drafted, live-page pass egress-blocked — see RECORD.md); build phase opened as Session Contract #17 (renumbered from #8 in the merge reconciliation); sector decision still open below.
- [x] (P1) Promise-ledger critical-path unblock — PARTIALLY DONE 2026-07-15: founder updated the policy; www.sec.gov now reachable (verified 200) and the FIRST LIVE RUN succeeded (real JPM/BAC same-day earnings 8-Ks pulled). REMAINING (small): `data.sec.gov` and `efts.sec.gov` still CONNECT-403 — add those two exact hostnames to the same allowlist (they carry the bulk-JSON and full-text-search APIs; the archive path works without them, so this no longer blocks the critical path, it just makes backfill cheaper).
- [x] (P1) Beachhead sector — DECIDED 2026-07-15: founder chose **FINANCIALS**. Charter po battery run same-day (seed 20260715, full canon, working notes committed) → 8-item harvest incl. bank claim taxonomy, capital-return promises as first golden-set class, 2023-regionals stress-window silence backtest, verdict cap ≤ likely at launch. Friction attack = evaluator via the PR gate.
- [ ] (P2) Send the four provider redistribution letters — owner: founder (external comms) — drafts ready in `ventures/promise_ledger/docs/PROVIDER_REDISTRIBUTION_QUESTIONS.md`; answers recorded additively there; gates sprint step 11.
- [ ] (P2) Contract #14 closure path — owner: founder (1 line) — the pricing/licensing verification sub-scope could not run from this sandbox (egress policy 403s vendor domains). Pick one: (a) accept narrowed scope with R-016 as the completion gate at greenlight, or (b) allowlist the vendor domains listed in the report's "Source pages to re-verify" notes (or provide an unproxied run) and the verification pass finishes the scope as written.
- [ ] (P2) Trust framework naming: drop "ESIM" 3-pillar branding, or relabel as OneLive's own framing — owner: founder.
- [ ] (P1) Monitoring stack: Vercel Analytics + Supabase logs to start, Sentry before public launch — owner: founder — confirm timing.
- [ ] (P2) Payments: Stripe Connect only, or keep Trolley for international creator payouts — owner: founder.
- [ ] (P3) Year 1 revenue figure reconciliation ($1.2M vs $1.44M) — owner: founder — external materials only, not a code task.
- [ ] (P2) Native mobile timing: PWA-first still holds, or does the existing Expo scaffold change that — owner: founder.
- [ ] (P3) Sync licensing as a future matching expansion — flag as Phase 3+ or rule out now — owner: founder.

## Infra / migrations (P0-P1 — blocking Phase 2's anon-key client-side ship)
- [ ] (P0) Apply `supabase/migrations/0005_pg_trgm.sql` to the live Supabase project — owner: whoever has DB apply access — required before fuzzy entity resolution works (exact + placeholder resolution still work without it).
- [ ] (P0) Apply `supabase/migrations/0006_rls_policies.sql` (RLS policy model + pg_trgm schema move) — owner: same — apply AFTER 0005, after code review. Written and PR'd, not yet applied.
- [ ] (P0) Apply `supabase/migrations/0007_narrow_event_public_read.sql` (narrowed event public-read policy) — owner: same — apply AFTER 0006. Required before the anon Supabase key ships client-side in Phase 2.
- [ ] (P1) Connect Vercel + Clerk before Phase 1 needs public preview/auth — owner: whoever owns deploy config. (Per STATE.md's Accounts/services status, both show connected already — verify this is still current before treating as done.)

## Product / pipeline (P1-P2)
- [ ] (P0, TOP OF QUEUE) **Step 6 golden-set gate (R-013)** — contract-first, evaluator mandatory: ≥40-example golden set (~320 facts ≥ the 1% sample floor; include indirect-prompt-injection cases per SPRINT Step 6) + live-exam runner over the REAL provider path (design the documented exam channel past the R-013 entry-point gate carefully — the runner is the gate's evidence generator) + blocking CI job; `EXTRACTION_THRESHOLD_RATIFIED` flips ONLY in the commit attaching a PASSING result for the starting model. Unlocks extraction → first real candidates → Step 7.
- [ ] (P1) Wire the consumer feed UI + auth/claim flow (Clerk) — owner: web app — next phase per STATE.md, nothing in Phase 1 blocks it.
- [ ] (P2) Populate source catalog ranks 42-118 (target 120+ sources total) — owner: pipeline — ongoing gap, not blocking Phase 1.

## Harness / agent-tooling follow-ups (this session's own findings)
- [ ] (P2) `tools/test_audit.py` runs clean on `tests/` today — re-run it after any large test-file addition, since it's advisory (exit 0) by default and won't block a commit on its own; consider `--strict` in `tools/validate`'s policy once the team is comfortable with zero tolerance.
- [ ] (P3) `tools/visual_regression.py`'s capture path has never run end-to-end against a live `web/` app (no headless browser installed in the agent sandbox) — owner: whoever has a real dev environment — see `tests/visual_baselines/README.md` for exact setup + first-baseline commands.
- [ ] (P3) `tools/commit_sweep.py` surfaces real advisory findings against current history (documented TODO gaps in `sources/README.md`, some large merge commits) — triage these opportunistically, not urgently; it's advisory by design.
- [x] (P2) **Model-cost routing (Loop Engineering step 17)** — add `docs/MODEL_ROUTING.md` (policy: loop stage → cheapest-capable model tier + reasoning) and a `tools/` helper resolving a stage label to a model id; wire into any future scheduled runner and the CI actions (currently hardcoded `claude-sonnet-4-6`). The one world-class gap the 2026-07-11 harness buildout did not close — see `docs/AGENT_FEEDBACK.md` 2026-07-11 entry + that day's arc, open thread #1. **DONE 2026-07-13 at founder direction: docs/MODEL_ROUTING.md (researched policy w/ real pricing + escalation triggers + caching/batch/effort techniques) + tools/model_router.py (+tests, incl. the fail-closed non-Claude-evaluator invariant) + CLAUDE.md "Cost discipline" section + CI wiring: dependency-hygiene.yml and source-backfill.yml resolve their model via `tools/model_router.py standard` instead of hardcoding.**
- [ ] (P2, STANDING — do not check off) **Extraction ratchet watch (KAIZEN §M7)** — founder-ratified 2026-07-15: threshold BEGINS at 1%, tightens mechanically (4 clean weekly cycles at ≤ half the bar + valid sample size → drop to 2× measured). Check the trailing rate at session close once real extractions flow; a ratchet-eligible state left unactioned is a defect.
- [ ] (P2, STANDING — do not check off) **Kaizen ledger discipline** — every merged PR gets its M1/M2/M5 row in `docs/metrics/KAIZEN_LEDGER.md`; repeat M2 classes get a structural gate-gap response (see the empty-env class watch). Levels: R-012 trigger.
- [ ] (P2, STANDING — do not check off) **Po battery at divergent moments** — Friction pre-work opens with `tools/po_battery.py`; first mandatory run: the R-008 cron-arming friction attack (harvest → M6).
- [ ] (P3) **Kaizen ledger append-only CI check** (evaluator suggestion, PR #15 r1) — mechanical guard: a PR that edits an existing `KAIZEN_LEDGER.md` row (rather than appending) fails unless it adds an explicit correction row. Build when the ledger starts informing decisions (it's a convention until then).
- [ ] (P3) **Model-id liveness smoke check** (evaluator suggestion, PR #14 round 3) — a cheap scheduled check that each id in `tools/model_router.py`'s table is accepted by its API (a 1-token ping or a models-list call), so a vendor rename can't leave `docs/MODEL_ROUTING.md` stale. Today staleness fails loud at first real use, which is acceptable; this upgrades loud-late to loud-early.
- [ ] (P3) **Explicit open-vs-closed loop framing (Loop Engineering step 15)** — largely covered by `docs/skills/night_shift.md` §3; revisit to make it a per-item field once a real scheduled runner exists.

---

**Adding a new item:** append under the right section (or add a new one) with
a priority, owner, and one line of context — link the STATE.md section or
session arc it came from if there is one. **Completing an item:** check the
box in the same commit that resolves it; leave the line in place (don't
delete completed items — they're a record of what got done).
