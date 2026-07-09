-- OneLive schema, migration 6: Row Level Security + move pg_trgm out of public.
-- Addresses two Supabase security advisories on project vqipjlvzfiwnandjumvx:
--   1. "RLS disabled in public" — all 14 public tables had RLS off.
--   2. "Extension in Public" — pg_trgm (migration 0005) was installed in `public`.
--
-- SAFETY NOTE (verified before writing this migration): the FastAPI backend
-- (api/, worker/, tools/) connects to Postgres via a DIRECT psycopg2 connection
-- as the `postgres` superuser/service role (ONELIVE_DB_DSN) — it does NOT use the
-- Supabase client SDK with the anon/publishable key. In Postgres/Supabase the
-- service_role / superuser BYPASSES RLS entirely, so enabling RLS below does not
-- affect any backend code path. Only anon/authenticated clients (browser/mobile
-- talking to Supabase directly, which nothing does yet) are constrained.
-- This migration is idempotent and safe to re-run.

-- =========================================================================
-- Part 1 — Enable Row Level Security on all 14 public tables.
-- =========================================================================

-- Public read-only tables (event, venue, artist):
-- RLS on + a SELECT policy granting read to anon + authenticated. No
-- INSERT/UPDATE/DELETE policies — writes happen only via the service-role
-- backend connection, which bypasses RLS.
alter table event             enable row level security;
alter table venue             enable row level security;
alter table artist            enable row level security;

drop policy if exists public_read on event;
-- ACCEPTED TRADEOFF (flagged for founder review in STATE.md — revisit before the
-- anon key is ever shipped client-side): this `using (true)` exposes ALL columns
-- of `event` to anon/authenticated, including `event.private_access` (jsonb) and
-- `event.is_private_rsvp` (see 0001_core.sql). That is safe TODAY only because
-- nothing talks to Supabase with the anon key yet — every read goes through the
-- backend's service-role connection (verified backend audit). Before the anon key
-- is used client-side this should be narrowed, e.g.
--   using (is_private_rsvp = false and private_access = '{}'::jsonb)
-- or private events moved behind an authenticated-only policy. Not changing it
-- silently now: /tonight + /events currently rely on unfiltered event reads via
-- the backend, and narrowing here without wiring the client is premature.
create policy public_read on event
  for select to anon, authenticated using (true);

drop policy if exists public_read on venue;
create policy public_read on venue
  for select to anon, authenticated using (true);

drop policy if exists public_read on artist;
create policy public_read on artist
  for select to anon, authenticated using (true);

-- source_reliability is INTERNAL trust-scoring data (per-source reliability
-- scores). It was public-read in the first review round, which would have exposed
-- internal scoring to the anon key. Verified (second review round) that it is only
-- ever read/written via the backend service-role connection
-- (worker/source_reliability.py) — no API endpoint and no client SDK query it. So
-- it moves to the service-role-only bucket below (RLS on, NO policy → default-deny
-- for anon/authenticated), removing the exposure entirely with zero functional loss.

-- Service-role-only tables: RLS on with NO policies at all. With RLS enabled
-- and no matching policy, anon/authenticated get zero access (default-deny);
-- the service-role backend connection is unaffected (service_role bypasses RLS).
alter table source              enable row level security;
alter table source_reliability  enable row level security;
alter table event_candidate     enable row level security;
alter table candidate_evidence  enable row level security;
alter table audit_log           enable row level security;
alter table raw_fetch           enable row level security;
alter table raw_event           enable row level security;
alter table advertiser          enable row level security;
alter table ad_campaign         enable row level security;
alter table ad_creative         enable row level security;
alter table ad_placement_rule   enable row level security;

-- =========================================================================
-- Part 2 — Move pg_trgm out of the public schema into a dedicated `extensions`
-- schema (Supabase "Extension in Public" advisory).
-- =========================================================================

create schema if not exists extensions;

-- The trigram GIN indexes depend on pg_trgm's gin_trgm_ops operator class, so
-- they must be dropped before the extension can be dropped (no CASCADE needed —
-- dropping them explicitly keeps the blast radius visible and controlled).
drop index if exists idx_venue_name_trgm;
drop index if exists idx_artist_name_trgm;

drop extension if exists pg_trgm;
create extension if not exists pg_trgm schema extensions;

-- Defense-in-depth ONLY: set a database-level default search_path that includes
-- `extensions`. This is NOT relied upon — on Supabase, role-level search_path
-- settings take precedence over this database-level default, so for the actual
-- connection role this ALTER may be a no-op. The real fix lives in the code:
-- worker/resolve_entities.py schema-qualifies the pg_trgm `%` operator and
-- similarity() to `extensions` (OPERATOR(extensions.%) / extensions.similarity),
-- so fuzzy matching resolves regardless of search_path. We keep this statement
-- so unqualified ad-hoc queries in a psql session still work by default.
-- On Supabase the live database is `postgres`. (Affects sessions opened AFTER it
-- runs, not this migration session — hence the schema-qualified opclass below.)
alter database postgres set search_path to public, extensions;

-- Recreate the trigram GIN indexes. The operator class is schema-qualified
-- (extensions.gin_trgm_ops) so index creation does not depend on the current
-- session's search_path ordering. Both tables are empty in production, so this
-- is fast and carries no data-migration risk.
create index if not exists idx_venue_name_trgm  on venue  using gin (name extensions.gin_trgm_ops);
create index if not exists idx_artist_name_trgm on artist using gin (name extensions.gin_trgm_ops);
