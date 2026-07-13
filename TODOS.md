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
- [ ] (P0) Mint `OPENAI_API_KEY` (usage-capped) — owner: founder (credential minting is founder-crucial) — the Independent Evaluator (`tools/adversarial_review.py`) and Friction attacks are wired but SKIPPED-loud without it; required before any trust-critical PR merges and before Step 5.
- [ ] (P0) Re-attack FRICTION_LOG entry #1 with the non-Claude evaluator once the key exists — owner: evaluator — entry is PROVISIONAL (attacked by the generator model, flagged).
- [ ] (P1) Decide open PR #7: PR #9 already ported its content to master — close as superseded, or state what still needs extraction — owner: founder (1 line).
- [ ] (P1) Mint `SENTRY_DSN` (web/api/worker) + `ORCHESTRATOR_PING_URL` (healthchecks.io) — owner: founder — wiring is done and no-op until these exist; charter forbids scheduling the recurring loop without both.
- [ ] (P1) Execute PR #9's live gate test plan (non-allowlisted → /access; wrong azp → 403) once deploy env exists — owner: Generator — SPRINT Step 8.
- [ ] (P2) Supply `docs/source/OneLive_WORLD_CLASS_bar.md` + `docs/source/OneLive_MASTER_the_whole_enchilada.md` (the two genesis source-canon files) or amend the charter's Document Index to point at `docs/WORLD_CLASS.md` — owner: founder — MASTER doc currently has no in-repo equivalent.
- [ ] (P2) Refresh STATE.md GROUND_TRUTH block via `session_reconcile.py --heal` from an env with `gh` + DB DSN — owner: next session with credentials — block is stale at pre-PR#9 state and could not be machine-refreshed from this sandbox.

## Founder decisions needed (cannot be resolved by an agent — do not silently pick one)
- [ ] (P1) Confirm 4-state confidence model finalized — owner: founder — `CLAUDE.md` already assumes this is decided; STATE.md flags it as still open.
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
- [ ] (P1) Wire the consumer feed UI + auth/claim flow (Clerk) — owner: web app — next phase per STATE.md, nothing in Phase 1 blocks it.
- [ ] (P2) Populate source catalog ranks 42-118 (target 120+ sources total) — owner: pipeline — ongoing gap, not blocking Phase 1.

## Harness / agent-tooling follow-ups (this session's own findings)
- [ ] (P2) `tools/test_audit.py` runs clean on `tests/` today — re-run it after any large test-file addition, since it's advisory (exit 0) by default and won't block a commit on its own; consider `--strict` in `tools/validate`'s policy once the team is comfortable with zero tolerance.
- [ ] (P3) `tools/visual_regression.py`'s capture path has never run end-to-end against a live `web/` app (no headless browser installed in the agent sandbox) — owner: whoever has a real dev environment — see `tests/visual_baselines/README.md` for exact setup + first-baseline commands.
- [ ] (P3) `tools/commit_sweep.py` surfaces real advisory findings against current history (documented TODO gaps in `sources/README.md`, some large merge commits) — triage these opportunistically, not urgently; it's advisory by design.
- [ ] (P2) **Model-cost routing (Loop Engineering step 17)** — add `docs/MODEL_ROUTING.md` (policy: loop stage → cheapest-capable model tier + reasoning) and a `tools/` helper resolving a stage label to a model id; wire into any future scheduled runner and the CI actions (currently hardcoded `claude-sonnet-4-6`). The one world-class gap the 2026-07-11 harness buildout did not close — see `docs/AGENT_FEEDBACK.md` 2026-07-11 entry + that day's arc, open thread #1.
- [ ] (P3) **Explicit open-vs-closed loop framing (Loop Engineering step 15)** — largely covered by `docs/skills/night_shift.md` §3; revisit to make it a per-item field once a real scheduled runner exists.

---

**Adding a new item:** append under the right section (or add a new one) with
a priority, owner, and one line of context — link the STATE.md section or
session arc it came from if there is one. **Completing an item:** check the
box in the same commit that resolves it; leave the line in place (don't
delete completed items — they're a record of what got done).
