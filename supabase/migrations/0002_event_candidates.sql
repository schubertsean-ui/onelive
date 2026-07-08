-- OneLive schema, migration 2 of 4: candidate events and evidence (AI proposals; not user-facing)
-- Source: extracted from Entertainment-App-Code-v1-4 reference build (db/migrations/002_event_candidates.sql)

create table if not exists event_candidate (
  candidate_id uuid primary key default gen_random_uuid(),
  source_id uuid references source(source_id),
  source_name text,
  source_url text,
  source_class text,                     -- ticketing|venue_calendar|social|local_media|...
  raw_text text,
  extracted jsonb not null default '{}'::jsonb,
  title text,
  start_time timestamptz,
  end_time timestamptz,
  venue_name text,
  city text,
  artist_names text[] not null default '{}'::text[],
  ticket_link text,
  rsvp_link text,
  is_private_rsvp boolean not null default false,
  private_access jsonb not null default '{}'::jsonb,
  status text not null default 'needs_review',
  gate_reason text,
  required_next text,
  promoted_event_id uuid references event(event_id),
  sxsw_mode boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_candidate_status on event_candidate(status);
create index if not exists idx_candidate_start on event_candidate(start_time);

create table if not exists candidate_evidence (
  evidence_id uuid primary key default gen_random_uuid(),
  candidate_id uuid not null references event_candidate(candidate_id) on delete cascade,
  source_class text not null,          -- venue_calendar|ticketing|festival_feed|social|local_media|claimed_upload|email_opt_in
  source_name text,
  source_url text,
  quote text,
  captured_at timestamptz not null default now()
);
create index if not exists idx_evidence_candidate on candidate_evidence(candidate_id);

-- Per-source evolving reliability score
create table if not exists source_reliability (
  source_id uuid primary key references source(source_id) on delete cascade,
  reliability_score numeric not null default 0.50,
  last_updated timestamptz not null default now()
);
