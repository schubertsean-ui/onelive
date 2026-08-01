-- OneLive schema, migration 12: the anon/authenticated SELECT GRANT that
-- completes the documented `event ∪ licensed_event` consumer read path.
--
-- WHY THIS EXISTS. Migration 0010 states the design plainly: "the consumer read
-- path UNIONs `event` ∪ `licensed_event`". `licensed_event` got its explicit
-- column-level GRANT in 0010; `event`/`venue`/`artist` never did — 0006/0007 set
-- the RLS *policies* but relied on an implicit table grant for the anon role. A
-- PostgREST read with the publishable (anon) key needs BOTH a row policy AND a
-- column/table privilege; without the privilege the promoted-event read returns
-- a permission error, not rows. This migration grants exactly the public listing
-- columns, so the web `web/lib/promoted.ts` reader can render promoted long-tail
-- events beside the licensed feed. Idempotent; additive; the guarded FastAPI
-- backend is unaffected (it connects as service_role/superuser, which bypasses
-- both GRANTs and RLS — see 0007's verified note).
--
-- TRUST POSTURE (unchanged, defense-in-depth):
--   * RLS is the ROW fence and stays exactly as 0007 set it: anon may read only
--     NON-private events (is_private_rsvp = false AND private_access = '{}').
--     `disputed` is NOT a row filter — disputed events are read and shown, as
--     the charter requires (shown-never-hidden).
--   * This GRANT is the COLUMN fence: it deliberately EXCLUDES the privacy
--     columns (`is_private_rsvp`, `private_access`) and the internal
--     `override_lock`/`notes`, so even if the RLS policy were ever loosened by
--     mistake, those columns are still not publicly selectable. Same
--     revoke-then-column-grant shape 0010 used for `licensed_event.raw`.

-- EVENT — revoke any pre-existing broad grant first (idempotent no-op when none
-- exists), then grant ONLY the public listing columns. A column grant does not
-- remove a broader table grant, so the revoke is what actually fences the
-- privacy/internal columns closed.
revoke select on event from anon, authenticated, public;
grant select (
  event_id, venue_id, artist_ids, start_time, end_time, status, confidence,
  title, category, subsegment, price_min, price_max, currency, is_free,
  ticket_url, image_url
) on event to anon, authenticated;

-- VENUE — the denormalized location fields the card needs. No privacy columns on
-- venue (0006 left its policy `using (true)`), so a straightforward column grant.
revoke select on venue from anon, authenticated, public;
grant select (
  venue_id, name, city, area, address, lat, lng
) on venue to anon, authenticated;

-- ARTIST — just the display name, resolved from event.artist_ids for `performer`.
revoke select on artist from anon, authenticated, public;
grant select (
  artist_id, name
) on artist to anon, authenticated;
