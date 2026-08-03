-- 0018_spark_line.sql — the Spark Line store (UI Canon §4; Design Brief 65,151-163).
--
-- A Spark Line is a 3/5/7-word vivid descriptor of an act's WORK. It is a
-- SEPARATE trust category from verified event facts: it NEVER touches the
-- event candidate -> gate -> promote pipeline, and it is joined into the feed
-- at read time by artist NAME (the only key present on BOTH feed halves — the
-- licensed feed's free-text `performer` and the promoted feed's resolved
-- `artist.name`). AI-drafted lines are tier C and land here as `candidate`;
-- only an `approved` row is ever anon-readable (fail-closed).
--
-- Idempotent (create-if-not-exists / drop-then-create policy / guarded DO
-- blocks). Applied by a migration run / the Descriptor Foundry import step,
-- exactly like 0010/0014/0017 — never a manual apply. RLS + column GRANT mirror
-- migration 0010's posture; `provenance` is the one column deliberately kept
-- OUT of the anon grant (it holds the audit trail: source refs, prompt hash,
-- model ids, the raw candidate set), the same way `licensed_event.raw` is.

create table if not exists spark_line (
  spark_line_id  uuid primary key default gen_random_uuid(),
  -- Join key: lower(trim(artist name)). Matches licensed_event.performer and
  -- the resolved artist.name so one line serves both feeds.
  artist_key     text not null,
  artist_name    text not null,           -- display form, as sourced
  text           text not null,
  word_count     int  not null,
  tier           text not null,           -- A (artist) | B (critic) | C (AI)
  attribution    text,                    -- tier B: the named critic/source
  status         text not null default 'candidate',  -- candidate|approved|rejected
  provenance     jsonb not null default '{}'::jsonb,  -- audit trail; NOT anon-granted
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

-- Guarded CHECK constraints (idempotent add). A malformed tier/status/word
-- count is a data defect that must fail at the DB boundary, never render.
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'spark_line_tier_ck') then
    alter table spark_line add constraint spark_line_tier_ck check (tier in ('A','B','C'));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'spark_line_status_ck') then
    alter table spark_line add constraint spark_line_status_ck
      check (status in ('candidate','approved','rejected'));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'spark_line_wordcount_ck') then
    alter table spark_line add constraint spark_line_wordcount_ck
      check (word_count in (3,5,7));
  end if;
end $$;

create index if not exists spark_line_artist_key_idx on spark_line (artist_key);

-- At most ONE approved Spark Line per artist (discovery neutrality: no artist
-- carries two live descriptors). Candidates/rejected rows are unconstrained.
create unique index if not exists spark_line_one_approved_per_artist
  on spark_line (artist_key) where status = 'approved';

-- RLS: fail-closed. Enable so the table is not open by default, then grant a
-- read of ONLY approved rows. The service-role backend (the Foundry writer /
-- ops approval) bypasses RLS as elsewhere.
alter table spark_line enable row level security;
drop policy if exists public_read on spark_line;
create policy public_read on spark_line
  for select to anon, authenticated
  using (status = 'approved');

-- REVOKE any pre-existing table-level SELECT first (idempotent): a column-level
-- grant does NOT remove a broader existing grant, so without this revoke
-- `provenance` could stay publicly selectable.
revoke select on spark_line from anon, authenticated, public;

-- COLUMN-LEVEL select grant — every column EXCEPT `provenance` (the audit
-- payload). NOTE (per 0017's lesson): a column added by a LATER migration is
-- NOT covered by this grant and needs its own grant, or PostgREST rejects the
-- whole request.
grant select (
  spark_line_id, artist_key, artist_name, text, word_count, tier,
  attribution, status, created_at, updated_at
) on spark_line to anon, authenticated;
