-- OneLive schema, migration 15: register the 'localist' calendar-platform provider
-- as a known licensed provider (widen licensed_event_provider_chk).
--
-- WHY A MIGRATION (not just importer code): migration 0010 states, verbatim,
-- "Adding a source is a schema event ... the boundary rejects a typo'd/invalid
-- provider." The licensed_event_provider_chk CHECK constraint is that boundary;
-- after 0013 it accepts ('ticketmaster','seatgeek','eventbrite','ics','jsonld'),
-- so an upsert from the new Localist calendar-platform importer would be REJECTED
-- by the DB until this set is widened.
--
-- 'localist' is a FIRST-PARTY, DETERMINISTIC (no-AI) provider exactly like 'ics'
-- and 'jsonld': a university/library/city publishing its own schedule via the
-- Localist platform's public /api/2/events JSON is an authoritative anchor, so its
-- rows are 'confirmed' by construction and flow through the same separate
-- licensed_event store WITHOUT the AI-extraction / human-promote path. Recording
-- the provider keeps each row's provenance honest (which reader produced it, so a
-- shape drift is traceable to the Localist API vs ICS vs JSON-LD).
--
-- Minimal + additive: this ONLY re-defines the provider CHECK to add the one
-- token. No column, RLS, or grant posture changes — those from 0010 hold.
-- Idempotent via a guarded DO-block that DROPs the existing constraint (if any)
-- and re-adds it with the widened set, so re-running converges regardless of
-- which prior definition is currently installed (mirrors 0013's style; DROP-then-
-- add is required because ALTER cannot edit a CHECK in place).
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
    check (source_provider in ('ticketmaster', 'seatgeek', 'eventbrite', 'ics', 'jsonld', 'localist'));
end $$;
