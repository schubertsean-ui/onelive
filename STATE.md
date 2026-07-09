# OneLive — STATE

Last updated: 2026-07-09 by Computer (PM) — includes PR #2 second review-round fixes (see Security section)

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

## What's next
- **Next phase: public consumer PWA screen + Clerk auth wiring.** Deferred this pass on
  purpose — Clerk is not yet connected to the project (pending founder action). Once Clerk
  is connected, wire the consumer feed UI and auth/claim flow. Nothing in Phase 1 blocks it.
- Apply `supabase/migrations/0005_pg_trgm.sql` to the live Supabase project before relying
  on fuzzy entity resolution (exact + placeholder still work without it). NOTE: `0006`
  moves pg_trgm to the `extensions` schema and drops/recreates it, so apply `0005` then
  `0006` in order (or, if neither is applied yet, `0006` alone stands up pg_trgm in
  `extensions` with both indexes — but the migration chain expects 0005 first).
- **Apply `supabase/migrations/0006_rls_policies.sql`** (RLS policy model + pg_trgm schema
  move) after code review. Written and PR'd, NOT yet applied — see the Security section above.
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
