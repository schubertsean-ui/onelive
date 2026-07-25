-- OneLive schema, migration 11: register 'eventbrite' as a known licensed
-- provider (widen licensed_event_provider_chk).
--
-- WHY A MIGRATION (not just importer code): migration 0010 states, verbatim,
-- "Adding a source is a schema event ... the boundary rejects a typo'd/invalid
-- provider." The licensed_event_provider_chk CHECK constraint is that boundary:
-- it currently accepts only ('ticketmaster', 'seatgeek'), so an eventbrite
-- upsert would be REJECTED by the DB until this set is widened. Eventbrite is
-- the highest-volume NON-music-ticketed source (community, food & drink,
-- classes, festivals, business), broadening OneLive beyond music — registering
-- it here is the deliberate, auditable schema event that admits its rows.
--
-- Minimal + additive: this ONLY re-defines the provider CHECK to add
-- 'eventbrite'. No column, RLS, or grant posture changes — those from 0010 hold.
-- Idempotent via a guarded DO-block that DROPs the existing constraint (if any)
-- and re-adds it with the widened set, so re-running converges regardless of
-- whether the old or new definition is currently installed (mirrors 0010's
-- constraint-add style; DROP-then-add is required because ALTER cannot edit a
-- CHECK in place).
do $$
begin
  if exists (
    select 1 from pg_constraint
    where conrelid = 'licensed_event'::regclass
      and conname = 'licensed_event_provider_chk'
  ) then
    alter table licensed_event drop constraint licensed_event_provider_chk;
  end if;
  alter table licensed_event add constraint licensed_event_provider_chk
    check (source_provider in ('ticketmaster', 'seatgeek', 'eventbrite'));
end $$;
