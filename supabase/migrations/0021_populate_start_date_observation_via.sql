-- Ticket A: date-only listings publish. Observation and via start the union clock.
alter table event add column if not exists start_date date;
create index if not exists event_start_date_idx on event (start_date);

update event
   set start_date = (start_time at time zone 'America/Chicago')::date
 where start_date is null
   and start_time is not null;

create table if not exists observation (
  observation_id uuid primary key default gen_random_uuid(),
  door_id text not null,
  source_url text not null,
  fetched_at timestamptz not null default now(),
  http_status int,
  extracted jsonb,
  run_id text
);

create table if not exists happening_via (
  happening_id uuid not null,
  door_id text not null,
  observed_at timestamptz not null default now(),
  listing_url text,
  primary key (happening_id, door_id)
);
