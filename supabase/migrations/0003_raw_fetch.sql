-- OneLive schema, migration 3 of 4: raw fetch capture for replayability/auditability
-- Source: extracted from Entertainment-App-Code-v1-4 reference build (db/migrations/003_raw_fetch.sql)

create table if not exists raw_fetch (
  raw_fetch_id uuid primary key default gen_random_uuid(),
  source_id uuid references source(source_id),
  fetch_url text not null,
  content_hash text not null,
  headers jsonb not null default '{}'::jsonb,
  storage_ref text,
  fetched_at timestamptz not null default now()
);
create index if not exists idx_raw_fetch_source_time on raw_fetch(source_id, fetched_at);

create table if not exists raw_event (
  raw_event_id uuid primary key default gen_random_uuid(),
  raw_fetch_id uuid references raw_fetch(raw_fetch_id) on delete cascade,
  extracted_text text,
  extracted_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
