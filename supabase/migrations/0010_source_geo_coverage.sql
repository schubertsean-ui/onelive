-- OneLive migration 0010: source geographic + coverage dimension
--
-- Why: the initial catalog (43 sources) had NO geographic or category structure,
-- so coverage blindness (which counties / which cultural categories have no
-- source) was unmeasurable. A trust-first feed's ceiling is its source coverage;
-- coverage must be a QUERYABLE property, not an assumption. This migration adds
-- that dimension so tools/coverage_report.py can produce a county x category grid.
--
-- Design:
--  * county          : the Austin-metro county a source primarily covers. NULL
--                       is allowed for genuinely metro-wide / statewide / national
--                       sources (e.g. a national ticketing platform) — NULL means
--                       "not county-specific", which is distinct from "unknown".
--  * sub_region      : finer locality (e.g. 'round_rock', 'san_marcos', 'downtown_austin').
--  * coverage_categories : the cultural categories a source reports on (music,
--                       theater, visual_art, film, food, literary, community,
--                       festival, comedy, dance, museum, university). A source may
--                       cover several. Empty array = uncategorized (flagged by the
--                       coverage report as debt, never silently ignored).
--
-- County is CHECK-constrained to the 5-county Austin MSA so a typo fails loud at
-- write time rather than silently creating a phantom county in coverage reports.

alter table source
  add column if not exists county text,
  add column if not exists sub_region text,
  add column if not exists coverage_categories text[] not null default '{}'::text[];

-- Fail-loud county domain (5-county Austin MSA). NULL permitted (= not
-- county-specific). Guard against duplicate-run since Postgres has no
-- "add constraint if not exists".
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'source_county_check'
  ) then
    alter table source
      add constraint source_county_check
      check (county is null or county in
        ('travis','williamson','hays','bastrop','caldwell'));
  end if;
end $$;

-- Coverage queries filter/group by county and by category; index both.
create index if not exists idx_source_county on source(county);
create index if not exists idx_source_coverage_categories
  on source using gin (coverage_categories);

comment on column source.county is
  '5-county Austin MSA the source primarily covers; NULL = not county-specific (metro/state/national).';
comment on column source.sub_region is
  'Finer locality within the county (e.g. round_rock, san_marcos, downtown_austin).';
comment on column source.coverage_categories is
  'Cultural categories this source reports on (music, theater, visual_art, food, ...); empty = uncategorized (coverage debt).';
