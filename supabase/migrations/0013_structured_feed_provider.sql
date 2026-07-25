-- OneLive schema, migration 13: register the deterministic STRUCTURED-FEED
-- providers as known licensed providers (widen licensed_event_provider_chk).
--
-- WHY A MIGRATION (not just importer code): migration 0010 states, verbatim,
-- "Adding a source is a schema event ... the boundary rejects a typo'd/invalid
-- provider." The licensed_event_provider_chk CHECK constraint is that boundary;
-- after 0011 it accepts only ('ticketmaster', 'seatgeek', 'eventbrite'), so an
-- upsert from the new structured-feed importer would be REJECTED by the DB until
-- this set is widened.
--
-- TWO provider tokens, not one, because provenance must record HOW an event was
-- parsed from a first-party machine-readable calendar:
--   * 'ics'    — parsed from an iCalendar VEVENT feed (RFC 5545, text/calendar);
--   * 'jsonld' — parsed from schema.org/Event JSON-LD embedded in a page's HTML.
-- Both are FIRST-PARTY, DETERMINISTIC (no-AI) sources: a venue/university/
-- library/civic/museum publishing its own calendar is an authoritative anchor,
-- so its rows are 'confirmed' by construction (like the licensed ticketing feeds)
-- and flow through the same separate licensed_event store WITHOUT the AI-
-- extraction / human-promote path. Recording the parse method keeps each row's
-- provenance honest and auditable (which reader produced it, so a shape drift is
-- traceable to ICS vs JSON-LD).
--
-- Minimal + additive: this ONLY re-defines the provider CHECK to add the two
-- tokens. No column, RLS, or grant posture changes — those from 0010 hold.
-- Idempotent via a guarded DO-block that DROPs the existing constraint (if any)
-- and re-adds it with the widened set, so re-running converges regardless of
-- whether the 0010, 0011, or this definition is currently installed (mirrors
-- 0011's constraint-add style; DROP-then-add is required because ALTER cannot
-- edit a CHECK in place).
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
    check (source_provider in ('ticketmaster', 'seatgeek', 'eventbrite', 'ics', 'jsonld'));
end $$;
