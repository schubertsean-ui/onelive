-- 0014 — venue contact: website + phone on licensed_event.
--
-- Purpose: give a user a one-tap way to CONFIRM with the venue directly — the
-- venue is always the last word (trust posture). Two nullable, additive columns;
-- no backfill here (see tools/backfill_venue_contact.py, which fills them from
-- the raw payload we already store). Idempotent, applied by the import workflow
-- like the earlier feed migrations.
--
-- Coverage note: populated for FREE from the providers' own venue data
-- (Ticketmaster venue url + box-office phone; SeatGeek venue url). Gaps are
-- filled later by a Google Places enrichment pass (a separate, key-gated,
-- cost-bounded step) — these same two columns receive that data, so no schema
-- change is needed when it lands.

alter table if exists licensed_event
  add column if not exists venue_url   text,
  add column if not exists venue_phone text;

-- No new grants needed: the existing table-level SELECT grant to the anon role
-- (migration 0010) covers columns added later. Kept as a comment so the
-- reviewer doesn't have to re-derive that.
