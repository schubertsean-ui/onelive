-- 0019_spark_line_identity.sql — bind a Spark Line to a stable ACT IDENTITY.
--
-- A Spark Line is displayed by IDENTITY, never by display name. A performer name
-- is NOT an identity: two different acts can share the same normalized name, so a
-- name-keyed read could attach one act's descriptor (including the tier-C
-- "drafted from the artist's own materials" attribution) to a same-name act's
-- card (adversarial-review #148, attacker-smuggle lens). `artist_ref` is the
-- stable identity (e.g. a MusicBrainz id / Wikidata QID) the line is bound to; the
-- feed read (web/lib/spark.ts) matches licensed_event.artist_ref ->
-- spark_line.artist_ref ONLY, so a same-name act can never receive another act's
-- line.
--
-- Nullable: existing candidate/human rows carry no resolved identity yet, and the
-- feed simply never attaches a ref-less row (fail closed by construction). It is
-- populated by the ratified identity-resolution enrichment (MusicBrainz/Wikidata;
-- gated, founder-crucial) on both licensed_event and approved spark_line rows.
--
-- Idempotent (add-column-if-not-exists / create-index-if-not-exists), self-applied
-- by the migration run exactly like 0018 — never a manual apply.

alter table spark_line add column if not exists artist_ref text;

create index if not exists spark_line_artist_ref_idx
  on spark_line (artist_ref) where artist_ref is not null;

-- Column-level SELECT grant for the new column (per 0017/0018's lesson: a column
-- added by a LATER migration is NOT covered by the earlier grant, and PostgREST
-- rejects a select that names an ungranted column). The identity ref is a public
-- display join key, never audit payload — safe to grant, unlike `provenance`.
grant select (artist_ref) on spark_line to anon, authenticated;
