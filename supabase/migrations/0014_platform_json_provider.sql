-- OneLive schema, migration 14: register 'platform_json' as a known licensed
-- provider (widen licensed_event_provider_chk).
--
-- WHY (evaluator nit, PR #68 r3): the structured importer gained a reader for
-- PLATFORM EVENT APIs — WordPress "The Events Calendar" (Tribe REST) and
-- Localist. Those return ordinary JSON event collections, NOT schema.org JSON-LD.
-- Until this migration those rows were stored under the 'jsonld' token purely to
-- satisfy the CHECK, which CONFLATED two materially different acquisition
-- formats and would make downstream provenance / quality debugging harder: a
-- shape drift in the Tribe reader would be indistinguishable from one in the
-- JSON-LD reader.
--
-- Migration 0010's rule holds — "adding a source is a schema event ... the
-- boundary rejects a typo'd/invalid provider" — so the parse method gets its own
-- token rather than borrowing one:
--   * 'ics'           — iCalendar VEVENT feed (RFC 5545, text/calendar)
--   * 'jsonld'        — schema.org/Event JSON-LD (embedded in HTML, or a bare
--                       application/ld+json document)
--   * 'platform_json' — a platform's own events API (Tribe REST / Localist)
--
-- Same trust posture as the other two: FIRST-PARTY and DETERMINISTIC (no AI), so
-- rows are 'confirmed' by construction and flow through the separate
-- licensed_event store, never the AI-extraction / human-promote path.
--
-- Idempotent + additive: drops and re-creates the CHECK with the widened set.

alter table licensed_event
  drop constraint if exists licensed_event_provider_chk;

alter table licensed_event
  add constraint licensed_event_provider_chk
  check (source_provider in (
    'ticketmaster', 'seatgeek', 'eventbrite', 'ics', 'jsonld', 'platform_json'
  ));
