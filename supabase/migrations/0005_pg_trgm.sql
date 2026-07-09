-- OneLive schema, migration 5: enable pg_trgm for fuzzy entity resolution
-- Added in Phase 1 (feed pipeline hardening). worker/resolve_entities.py uses
-- trigram similarity() as its second resolution step (exact -> fuzzy -> placeholder).
create extension if not exists pg_trgm;

-- Trigram GIN indexes back the fuzzy name lookups so resolution stays fast as
-- the venue/artist tables grow. resolve_entities.py queries them with the pg_trgm
-- `%` operator (WHERE name % <input>), which gin_trgm_ops CAN serve; the match
-- cutoff is set per session with `SET pg_trgm.similarity_threshold`. (The earlier
-- `WHERE similarity(name, x) >= t` form could NOT use a GIN index and forced a
-- sequential scan on every lookup.)
create index if not exists idx_venue_name_trgm on venue using gin (name gin_trgm_ops);
create index if not exists idx_artist_name_trgm on artist using gin (name gin_trgm_ops);
