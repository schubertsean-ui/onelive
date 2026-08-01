-- OneLive schema, migration 10: cultural-domain fields + a SEPARATE licensed
-- event store (Session Contract #20, live-site-capcog).
--
-- TWO independent changes, both additive:
--
-- 1. Cultural-domain fields on `event` and geo on `venue` (nullable, additive)
--    for the 22-domain monitor. These serve PIPELINE-promoted (long-tail)
--    events; nothing here adds a writer to `event` — worker/promote.py (the
--    single human-custodied writer guarded by tools/trust_gate.py's
--    promote-import-allowlist) sets them. The guarded promote path is UNTOUCHED.
--
-- 2. A NEW, self-contained `licensed_event` table for the Ticketmaster/SeatGeek
--    licensed feeds. WHY A SEPARATE TABLE (not columns on `event`): the charter
--    physically separates trust categories (cf. tastemaker posts, which "must
--    NEVER touch the event candidate/gating/promotion pipeline"). Licensed feeds
--    are a distinct, higher-trust, DETERMINISTIC (no-AI) category. Keeping them
--    in their own store means:
--      * the guarded `event`/promote path and its allowlist are untouched — no
--        new writer to the AI-custodied table, so "AI never publishes" and the
--        promote-import-allowlist both hold BY CONSTRUCTION;
--      * licensed rows carry their own provenance (source_provider+external_id,
--        UNIQUE ⇒ idempotent import) and the raw source payload for audit;
--      * the consumer read path UNIONs `event` ∪ `licensed_event`, each row
--        provenance-tagged. Licensed rows are 'confirmed' by construction (an
--        authoritative ticketing source stated them), never by AI judgement.
-- This migration is idempotent.

-- 1a. Cultural-domain fields on `event` (for pipeline-promoted rows).
alter table event
  add column if not exists title       text,
  add column if not exists category    text,     -- cultural domain id, e.g. 'live-music'
  add column if not exists subsegment   text,     -- e.g. 'Jazz'
  add column if not exists price_min    numeric,
  add column if not exists price_max    numeric,
  add column if not exists currency     text,
  add column if not exists is_free      boolean,
  add column if not exists ticket_url   text,
  add column if not exists image_url    text;

create index if not exists idx_event_category on event(category);
create index if not exists idx_event_category_start on event(category, start_time);

-- 1b. Real geo/address on `venue` for the "nearby / in area" lenses.
alter table venue
  add column if not exists lat         double precision,
  add column if not exists lng         double precision,
  add column if not exists address     text,
  add column if not exists area        text,      -- neighborhood/area label, e.g. 'Downtown'
  add column if not exists postal_code text;

-- 2. The separate licensed-event store. Self-contained (venue denormalized in)
-- so it never depends on or writes the guarded `event`/`venue` tables.
create table if not exists licensed_event (
  licensed_event_id uuid primary key default gen_random_uuid(),
  source_provider   text not null,                     -- 'ticketmaster' | 'seatgeek'
  external_id       text not null,                     -- the provider's stable event id
  title             text not null,
  category          text,                              -- cultural domain id
  subsegment        text,
  performer         text,
  start_time        timestamptz,
  end_time          timestamptz,
  status            text not null default 'scheduled', -- scheduled|cancelled|moved
  on_sale_status    text,                              -- onsale|offsale|cancelled|...
  price_min         numeric,
  price_max         numeric,
  currency          text,
  is_free           boolean,
  ticket_url        text,
  image_url         text,
  venue_name        text,
  venue_city        text,
  venue_area        text,
  venue_address     text,
  venue_lat         double precision,
  venue_lng         double precision,
  confidence        text not null default 'confirmed', -- licensed ⇒ confirmed by construction
  raw               jsonb not null default '{}'::jsonb, -- provenance: the source payload
  imported_at       timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  constraint uq_licensed_provider_external unique (source_provider, external_id)
);
create index if not exists idx_licensed_start on licensed_event(start_time);
create index if not exists idx_licensed_category on licensed_event(category);
create index if not exists idx_licensed_category_start on licensed_event(category, start_time);
create index if not exists idx_licensed_city on licensed_event(lower(venue_city));

-- RLS: mirror migration 0006's posture. Licensed rows are all PUBLIC listings
-- (no private-RSVP concept), so anon/authenticated may read them; the
-- service-role backend bypasses RLS as elsewhere. Enable RLS so the table is
-- not open by default, then grant the explicit public read.
alter table licensed_event enable row level security;
drop policy if exists public_read on licensed_event;
create policy public_read on licensed_event
  for select to anon, authenticated
  using (true);

-- REVOKE any pre-existing table-level SELECT first. An earlier application of
-- this migration granted table-level `select` (all columns incl. `raw`); a
-- column-level grant does NOT remove a broader existing grant, so without this
-- revoke `raw` could stay publicly selectable. Revoke is idempotent (no-op when
-- nothing is granted), and the column grant below then becomes the ONLY select
-- privilege for anon/authenticated.
revoke select on licensed_event from anon, authenticated, public;

-- COLUMN-LEVEL select grant — everything EXCEPT `raw`. `raw` holds the internal
-- provider payload (provenance/audit), which must not be publicly selectable
-- through the anon/authenticated Supabase (PostgREST) key; excluding it from the
-- grant fails that column closed while the public listing fields stay readable.
grant select (
  licensed_event_id, source_provider, external_id, title, category, subsegment,
  performer, start_time, end_time, status, on_sale_status, price_min, price_max,
  currency, is_free, ticket_url, image_url, venue_name, venue_city, venue_area,
  venue_address, venue_lat, venue_lng, confidence, imported_at, updated_at
) on licensed_event to anon, authenticated;

-- CHECK constraints so the DB rejects invalid trust/status values at the
-- boundary — a public trust field must not accept 'banana'/'hidden'. Added via a
-- guarded DO-block (the table already exists) so this stays idempotent.
do $$
begin
  if not exists (select 1 from pg_constraint where conrelid = 'licensed_event'::regclass and conname ='licensed_event_confidence_chk') then
    alter table licensed_event add constraint licensed_event_confidence_chk
      check (confidence in ('confirmed', 'likely', 'unverified', 'disputed'));
  end if;
  if not exists (select 1 from pg_constraint where conrelid = 'licensed_event'::regclass and conname ='licensed_event_status_chk') then
    alter table licensed_event add constraint licensed_event_status_chk
      check (status in ('scheduled', 'cancelled', 'moved'));
  end if;
  -- Known licensed providers. Adding a source is a schema event (update this set
  -- in a follow-up migration) — the boundary rejects a typo'd/invalid provider.
  if not exists (select 1 from pg_constraint where conrelid = 'licensed_event'::regclass and conname ='licensed_event_provider_chk') then
    alter table licensed_event add constraint licensed_event_provider_chk
      check (source_provider in ('ticketmaster', 'seatgeek'));
  end if;
  if not exists (select 1 from pg_constraint where conrelid = 'licensed_event'::regclass and conname ='licensed_event_price_chk') then
    alter table licensed_event add constraint licensed_event_price_chk
      check (price_min is null or price_max is null or price_min <= price_max);
  end if;
  if not exists (select 1 from pg_constraint where conrelid = 'licensed_event'::regclass and conname ='licensed_event_geo_chk') then
    alter table licensed_event add constraint licensed_event_geo_chk
      check ((venue_lat is null or venue_lat between -90 and 90)
             and (venue_lng is null or venue_lng between -180 and 180));
  end if;
end $$;
