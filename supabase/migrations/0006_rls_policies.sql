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

-- Public read-only tables (event, venue, artist, source_reliability):
-- RLS on + a SELECT policy granting read to anon + authenticated. No
-- INSERT/UPDATE/DELETE policies — writes happen only via the service-role
-- backend connection, which bypasses RLS.
alter table event             enable row level security;
alter table venue             enable row level security;
alter table artist            enable row level security;
alter table source_reliability enable row level security;

drop policy if exists public_read on event;
create policy public_read on event
  for select to anon, authenticated using (true);

drop policy if exists public_read on venue;
create policy public_read on venue
  for select to anon, authenticated using (true);

drop policy if exists public_read on artist;
create policy public_read on artist
  for select to anon, authenticated using (true);

drop policy if exists public_read on source_reliability;
create policy public_read on source_reliability
  for select to anon, authenticated using (true);

-- Service-role-only tables: RLS on with NO policies at all. With RLS enabled
-- and no matching policy, anon/authenticated get zero access (default-deny);
-- the service-role backend connection is unaffected (service_role bypasses RLS).
alter table source              enable row level security;
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

-- Ensure the `extensions` schema is on the search_path for future backend
-- connections so worker/resolve_entities.py's unqualified `%` operator and
-- similarity() calls still resolve. On Supabase the live database is `postgres`.
-- (This affects sessions opened AFTER it runs, not the current migration
-- session — hence the schema-qualified opclass in the CREATE INDEX below.)
alter database postgres set search_path to public, extensions;

-- Recreate the trigram GIN indexes. The operator class is schema-qualified
-- (extensions.gin_trgm_ops) so index creation does not depend on the current
-- session's search_path ordering. Both tables are empty in production, so this
-- is fast and carries no data-migration risk.
create index if not exists idx_venue_name_trgm  on venue  using gin (name extensions.gin_trgm_ops);
create index if not exists idx_artist_name_trgm on artist using gin (name extensions.gin_trgm_ops);
