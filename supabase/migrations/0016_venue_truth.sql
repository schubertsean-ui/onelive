-- 0016 — venue_truth: authoritative venue facts from government open data.
--
-- The gov_open_data pathway (worker/importers/socrata.py, migration companion):
-- local & state agencies publish authoritative VENUE facts — liquor licensing
-- (TABC), fire-marshal occupancy/capacity, health permits / service type — as
-- machine-readable JSON via Socrata. This table stores the normalized records.
--
-- SEPARATE from `licensed_event` and the AI candidate/promote path by design:
-- these are VENUE facts, not events, and they never publish an event. They serve
-- two purposes — (1) user-facing venue enrichment (capacity, service type) and
-- (2) a TRIANGULATION anchor (does a venue exist, licensed, at this capacity?).
-- Keyed by (source_provider, external_id) so an idempotent re-import updates in
-- place, exactly like licensed_event.
--
-- Trust posture: this is PUBLIC government data, so the table is anon-readable
-- (a table-level SELECT grant to anon), mirroring licensed_event (0010). It holds
-- no user data and no secrets. RLS is not enabled for the same reason
-- licensed_event does not enable it — the whole table is public-by-construction
-- reference data; the boundary that matters (the provider CHECK) is below.
--
-- Idempotent: create-if-not-exists + a guarded provider CHECK, so re-running
-- converges. 'socrata' is the only provider today; the CHECK is the boundary that
-- rejects a typo'd/invalid provider, mirroring licensed_event_provider_chk.

create table if not exists venue_truth (
  source_provider text not null,
  external_id     text not null,
  name            text,
  address         text,
  city            text,
  state           text,
  postal_code     text,
  latitude        double precision,
  longitude       double precision,
  capacity        double precision,
  license_type    text,
  license_status  text,
  service_type    text,
  source_name     text,
  raw             jsonb,
  first_seen_at   timestamptz not null default now(),
  last_seen_at    timestamptz not null default now(),
  primary key (source_provider, external_id)
);

do $$
begin
  if exists (
    select 1 from pg_constraint
    where conrelid = 'venue_truth'::regclass
      and conname = 'venue_truth_provider_chk'
  ) then
    alter table venue_truth drop constraint venue_truth_provider_chk;
  end if;
  alter table venue_truth add constraint venue_truth_provider_chk
    check (source_provider in ('socrata'));
end $$;

-- Lookup by name/city for the venue-resolution/triangulation join.
create index if not exists idx_venue_truth_city_name
  on venue_truth (lower(city), lower(name));

-- Public reference data: readable by the anon role like licensed_event (0010).
-- No RLS (public-by-construction); no user data present.
grant select on venue_truth to anon;
