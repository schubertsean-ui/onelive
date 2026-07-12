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

---

**Adding a new item:** append under the right section (or add a new one) with
a priority, owner, and one line of context — link the STATE.md section or
session arc it came from if there is one. **Completing an item:** check the
box in the same commit that resolves it; leave the line in place (don't
delete completed items — they're a record of what got done).
