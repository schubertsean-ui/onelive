-- 0009_source_name_unique.sql
-- Adds a UNIQUE constraint on source.name.
--
-- Why: tools/import_sources.py uses `INSERT ... ON CONFLICT DO NOTHING` to be
-- idempotent (safe to re-run without creating duplicate source rows). That
-- requires a unique arbiter on the conflict column. The core schema (0001) only
-- created a primary key on source_id (a random UUID), so there was no arbiter on
-- `name` -- the importer's ON CONFLICT could not dedupe by name and re-running it
-- would insert duplicate sources. This migration makes `name` the natural key the
-- importer expects.
--
-- Safe to apply: the `source` table is currently empty, and source names in the
-- master catalog are already distinct, so no dedupe backfill is needed.

alter table public.source
  add constraint source_name_key unique (name);
