-- OneLive schema, migration 8: source-trust scoring config + 4-state lock-in.
--
-- Stands up the data-driven config substrate for the three source-trust
-- mechanisms so the product owner can flex/iterate the numbers without a code
-- change. Mirrors sources/trust_config.json (the Python fallback/seed source);
-- at runtime these tables are authoritative. Idempotent.
--
-- 1) source_type_weight        : per-source-type default credibility weight.
-- 2) source.credibility_weight : already exists (0001_core.sql) = the PER-SOURCE
--                                override that decay/growth drifts over time.
-- 3) confidence_weight_threshold: aggregated-weight -> 4-state confidence.
-- 4) priority_formula_version + priority_formula_coefficient: VERSIONED priority
--    ranking coefficients (audit/rollback).
-- 5) priority_band             : score band cutoffs (P0..P3).
-- 6) reputation_update_version + reputation_update_param: versioned decay/growth
--    constants (multipliers, floor, cap).
--
-- Also HARDENS the 4-state confidence model at the schema level: 0001_core.sql
-- declared event.confidence as free text with only a comment, so a reverted
-- 3-state writer or a typo could persist an invalid state. This adds a CHECK
-- constraint pinning it to exactly (unverified|likely|confirmed|disputed) with
-- `disputed` a first-class, non-deletable state (disputed rows are never
-- deleted — enforced in app logic; the constraint just guarantees the state is
-- always one of the canonical four).

-- 1) Per-source-type default credibility weights (0.0-1.0). -----------------
create table if not exists source_type_weight (
  source_type text primary key,
  default_weight numeric not null check (default_weight >= 0 and default_weight <= 1),
  updated_at timestamptz not null default now()
);

insert into source_type_weight (source_type, default_weight) values
  ('venue_calendar',     1.0),
  ('venue_claim',        1.0),
  ('artist_claim',       1.0),
  ('ticketing',          0.9),
  ('community_calendar', 0.7),
  ('artist_website',     0.6),
  ('linktree',           0.6),
  ('soundcloud',         0.6),
  ('bandcamp',           0.6),
  ('instagram',          0.4),
  ('facebook',           0.4),
  ('anonymous',          0.2)
on conflict (source_type) do nothing;

-- 3) Aggregated-weight -> 4-state confidence thresholds. --------------------
-- Highest matching min_weight wins: >=1.8 likely, >=1.0 unverified, else disputed.
create table if not exists confidence_weight_threshold (
  state text primary key check (state in ('unverified','likely','confirmed','disputed')),
  min_weight numeric not null
);

insert into confidence_weight_threshold (state, min_weight) values
  ('likely',     1.8),
  ('unverified', 1.0),
  ('disputed',   0.0)
on conflict (state) do nothing;

-- 4) Versioned priority-ranking formula coefficients. -----------------------
create table if not exists priority_formula_version (
  version text primary key,
  is_current boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists priority_formula_coefficient (
  version text not null references priority_formula_version(version) on delete cascade,
  subscore text not null,
  coefficient numeric not null check (coefficient >= 0 and coefficient <= 1),
  primary key (version, subscore)
);

insert into priority_formula_version (version, is_current) values ('v1', true)
on conflict (version) do nothing;

insert into priority_formula_coefficient (version, subscore, coefficient) values
  ('v1', 'credibility_weight',        0.40),
  ('v1', 'access_reliability',        0.20),
  ('v1', 'coverage_uniqueness',       0.15),
  ('v1', 'update_frequency_score',    0.15),
  ('v1', 'verification_anchor_score', 0.10)
on conflict (version, subscore) do nothing;

-- 5) Priority bands on the 0-100 score. -------------------------------------
create table if not exists priority_band (
  band text primary key,
  label text not null,
  min_score numeric not null check (min_score >= 0 and min_score <= 100)
);

insert into priority_band (band, label, min_score) values
  ('P0', 'Anchor truth',   85),
  ('P1', 'High trust',     70),
  ('P2', 'Corroboration',  50),
  ('P3', 'Weak signal',    0)
on conflict (band) do nothing;

-- 6) Versioned reputation decay/growth constants. ---------------------------
create table if not exists reputation_update_version (
  version text primary key,
  is_current boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists reputation_update_param (
  version text not null references reputation_update_version(version) on delete cascade,
  param text not null,
  value numeric not null,
  primary key (version, param)
);

insert into reputation_update_version (version, is_current) values ('v1', true)
on conflict (version) do nothing;

insert into reputation_update_param (version, param, value) values
  ('v1', 'false_positive_multiplier', 0.85),
  ('v1', 'true_positive_multiplier',  1.02),
  ('v1', 'floor',                     0.1),
  ('v1', 'cap',                       1.0)
on conflict (version, param) do nothing;

-- Schema-level 4-state lock-in for event.confidence. ------------------------
-- Drop first so re-running is idempotent even if the state set is retuned.
alter table event drop constraint if exists event_confidence_4state_chk;
alter table event add constraint event_confidence_4state_chk
  check (confidence in ('unverified','likely','confirmed','disputed'));
