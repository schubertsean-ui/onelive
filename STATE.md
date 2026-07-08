# OneLive — STATE

Last updated: 2026-07-08 by Computer (PM)

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

## What's in progress
- Phase 0 harness setup: GitHub Actions workflows (`pr-review.yml`, `source-backfill.yml`, `dependency-hygiene.yml`) and `.claude/agents/gate-verifier.md` not yet added to the repo (drafted in `OneLive_Build_Runbook.md`, ready to copy in).
- Nothing has been committed/pushed to git yet — working tree has all files above as untracked.
- Migrations have not yet been applied to the live Supabase project (project just became healthy this session).

## What's next
- Commit and push all extracted files to `origin/master`.
- Apply the 4 SQL migrations to Supabase (`apply_migration`, project ref `vqipjlvzfiwnandjumvx`).
- Add the 3 GitHub Actions workflows + gate-verifier agent config.
- Dispatch the first coding subagent (Phase 1: feed pipeline extension) against the real, now-populated repo.
- Populate source catalog ranks 42-118 (target: 120+ sources total) — flagged as an ongoing gap, not blocking Phase 1.

## Open founder decisions (pull from Spec §17 — do not let these silently lapse)
- [ ] Confirm 4-state confidence model finalized — CLAUDE.md already assumes this is decided.
- [ ] Trust framework naming: drop "ESIM" 3-pillar branding, or relabel as OneLive's own framing.
- [ ] Monitoring stack: Vercel Analytics + Supabase logs to start, Sentry before public launch.
- [ ] Payments: Stripe Connect only, or keep Trolley for international creator payouts.
- [ ] Year 1 revenue figure reconciliation ($1.2M vs $1.44M) — external materials only.
- [ ] Native mobile timing: PWA-first still holds, or does the existing Expo scaffold change that.
- [ ] Sync licensing as a future matching expansion — flag as Phase 3+ or rule out now.

## Known schema/architecture decisions already locked in
- 4-state confidence model (not 3-state).
- Creator-Venue Matching (not Heartbeat Analytics) is the v1 differentiator.
- Tastemaker Content ships in Phase 2, before Matching (Phase 3) — it's the growth-loop mechanism.
- Tastemaker posts are a fully separate trust category from event data — never mixed.
- Supabase-managed Postgres is the only DB path (legacy local-Docker path dropped — see Architecture deviations above).

## Accounts/services status
- GitHub: connected, repo live.
- Supabase: connected, project live and ACTIVE_HEALTHY (ref vqipjlvzfiwnandjumvx).
- Vercel: NOT YET connected — needed before Phase 1 can deploy a public preview.
- Clerk: NOT YET connected — needed before Phase 1 auth/claim flow work.
- Sentry: not needed until Phase 4.
