-- OneLive schema, migration 5: enable pg_trgm for fuzzy entity resolution
-- Added in Phase 1 (feed pipeline hardening). worker/resolve_entities.py uses
-- trigram similarity() as its second resolution step (exact -> fuzzy -> placeholder).
create extension if not exists pg_trgm;

-- Trigram GIN indexes back the similarity() lookups on entity names so fuzzy
-- resolution stays fast as venue/artist tables grow.
create index if not exists idx_venue_name_trgm on venue using gin (name gin_trgm_ops);
create index if not exists idx_artist_name_trgm on artist using gin (name gin_trgm_ops);
