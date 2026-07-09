-- OneLive schema, migration 7: narrow the `event` public-read RLS policy.
--
-- Migration 0006 enabled RLS on all 14 public tables and gave `event` a
-- `public_read` SELECT policy of `using (true)` — an ACCEPTED TRADEOFF at the
-- time (documented in 0006 + STATE.md) because it exposes EVERY event row to
-- the anon/authenticated Supabase key, including rows flagged private via
-- `event.is_private_rsvp` (boolean, default false) and `event.private_access`
-- (jsonb, default '{}') — see 0001_core.sql lines 48-49. That was safe only
-- because nothing talks to Supabase with the anon key yet; STATE.md flagged it
-- to be narrowed "before the anon key is ever shipped client-side". Phase 2
-- (PWA consumer screen + Clerk auth) is about to start, so we narrow it now.
--
-- THE FIX: replace `using (true)` so anon/authenticated can only SELECT events
-- that are not private (is_private_rsvp = false AND private_access = '{}').
--
-- SAFETY NOTE (verified before writing — unchanged from 0006's audit): the
-- FastAPI backend (api/, worker/, tools/) connects via a DIRECT psycopg2
-- connection as the `postgres` superuser/service role (ONELIVE_DB_DSN), NOT the
-- Supabase client SDK with the anon key. service_role/superuser BYPASSES RLS
-- entirely, so this narrowing has ZERO effect on the existing /tonight and
-- /events endpoints — they continue to read ALL events (including private and
-- disputed ones) exactly as before. This policy only constrains hypothetical
-- future direct-Supabase-client reads using the anon/authenticated key.
--
-- venue/artist public_read policies are intentionally left as `using (true)` —
-- those tables have no privacy columns. This migration is idempotent.

drop policy if exists public_read on event;
create policy public_read on event
  for select to anon, authenticated
  using (is_private_rsvp = false and private_access = '{}'::jsonb);
