-- 0020_event_provenance.sql
--
-- Cards reflect the updated content (founder directive 2026-08-05, decision
-- record docs/memory/decisions/2026-08-05_cards-reflect-updated-content.md):
-- carry a promoted event's SOURCE PROVENANCE onto the public row, so the
-- consumer surface's "How we know" disclosure can name and link the real
-- listing the event was published from (design-canon trust display: quiet
-- marker -> dismissible sheet + source link) instead of the generic "a local
-- venue or organizer listing". The engine has always known this fact — the
-- trust gate's verdict is built on it — but the promote boundary dropped it,
-- so the one thing a discovered event's card could not show was the strongest
-- honest trust signal we hold (red class: featurability-dimension-missed).
--
-- Idempotent per tools/apply_migration.py's contract: add column if not
-- exists; backfills touch only rows where the column is still null; the
-- column grant is naturally re-runnable. Applied by autopromote.yml before
-- its pass (the 0010/0013 import-workflow precedent).

alter table event
  add column if not exists source_name text,  -- e.g. 'Mohawk Austin'
  add column if not exists source_url  text;  -- that source's own base URL

-- Backfill rows promoted before this migration from the candidate's OWN row —
-- the same no-fabrication shape as 0010's card fields (promote-derived public
-- columns come from the candidate's data, never invented). promoted_event_id
-- is written by worker/promote.py in the same transaction as the event
-- insert, so this join reproduces exactly what promote would have written.
update event e
   set source_name = c.source_name
  from event_candidate c
 where c.promoted_event_id = e.event_id
   and e.source_name is null
   and c.source_name is not null;

-- The source's own URL, from the unique-keyed source registry (0009 makes
-- name unique, so this join is at most one row per event).
update event e
   set source_url = s.base_url
  from source s
 where lower(s.name) = lower(e.source_name)
   and e.source_url is null
   and e.source_name is not null
   and s.base_url is not null;

-- Public read: provenance is part of the honest listing surface. 0012 already
-- revoked the broad anon grant and granted listing columns explicitly; new
-- columns are closed until granted, so this is purely additive and the
-- privacy/internal columns stay fenced exactly as before.
grant select (source_name, source_url) on event to anon, authenticated;
