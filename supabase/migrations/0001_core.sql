-- OneLive schema, migration 1 of 4: core entities
-- Source: extracted from Entertainment-App-Code-v1-4 reference build (db/migrations/001_core.sql)
create extension if not exists pgcrypto;

-- Sources
create table if not exists source (
  source_id uuid primary key default gen_random_uuid(),
  name text not null,
  source_type text not null,
  base_url text,
  enabled boolean not null default true,
  credibility_weight numeric not null default 0.50,
  config jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create unique index if not exists idx_source_name on source(lower(name));

-- Venue / Artist (minimal for v1)
create table if not exists venue (
  venue_id uuid primary key default gen_random_uuid(),
  name text not null,
  city text,
  state text,
  country text,
  created_at timestamptz not null default now()
);
create index if not exists idx_venue_city_name on venue(lower(city), lower(name));

create table if not exists artist (
  artist_id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);
create unique index if not exists idx_artist_name on artist(lower(name));

-- Canonical Events
-- NOTE: confidence uses the 4-state model (unverified|likely|confirmed|disputed) per
-- ONE_LIVE_Reconciled_Master_Spec.md decision, extending the reference build's 3-state column.
create table if not exists event (
  event_id uuid primary key default gen_random_uuid(),
  venue_id uuid references venue(venue_id),
  artist_ids uuid[] not null default '{}'::uuid[],
  start_time timestamptz,
  end_time timestamptz,
  status text not null default 'scheduled',          -- scheduled|cancelled|moved
  confidence text not null default 'unverified',     -- unverified|likely|confirmed|disputed
  override_lock boolean not null default false,
  is_private_rsvp boolean not null default false,
  private_access jsonb not null default '{}'::jsonb,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_event_start_time on event(start_time);
create index if not exists idx_event_venue_start on event(venue_id, start_time);

-- Audit Log
create table if not exists audit_log (
  audit_id uuid primary key default gen_random_uuid(),
  actor_type text not null,        -- system|admin|venue|artist
  actor_id uuid,
  action text not null,            -- create_candidate|add_evidence|promote|override|edit_event
  entity_type text not null,       -- source|candidate|event|venue|artist
  entity_id uuid,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
