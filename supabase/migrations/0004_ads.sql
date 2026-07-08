-- OneLive schema, migration 4 of 4: policy-safe contextual advertising that cannot influence ranking
-- Source: extracted from Entertainment-App-Code-v1-4 reference build (db/migrations/004_ads.sql)

create table if not exists advertiser (
  advertiser_id uuid primary key default gen_random_uuid(),
  name text not null,
  category text,              -- restaurant|bar|hotel|transport|tourism|brand
  website text,
  status text not null default 'active',
  created_at timestamptz not null default now()
);

create table if not exists ad_campaign (
  campaign_id uuid primary key default gen_random_uuid(),
  advertiser_id uuid not null references advertiser(advertiser_id) on delete cascade,
  name text not null,
  city text,
  start_date date,
  end_date date,
  budget_usd numeric,
  status text not null default 'draft', -- draft|active|paused|ended
  created_at timestamptz not null default now()
);

create table if not exists ad_creative (
  creative_id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references ad_campaign(campaign_id) on delete cascade,
  headline text,
  body text,
  image_url text,
  click_url text,
  created_at timestamptz not null default now()
);

create table if not exists ad_placement_rule (
  rule_id uuid primary key default gen_random_uuid(),
  name text not null,
  placement text not null,           -- feed_separator|tonight_footer|venue_sidebar|city_hub
  city text,
  enabled boolean not null default true,
  created_at timestamptz not null default now()
);
