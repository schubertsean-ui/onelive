# ONE LIVE — Geo & Identity: How the World Solves This (RESEARCH v1)

**Status: RESEARCH BRIEF, companion to `ONE_LIVE_GEO_IDENTITY_v1.md` (PROPOSAL).**
Founder-directed 2026-07-29: "ensure the research is informing how we build all
of this identity capability… research the world-leading approaches to complex
problems similar to this." Four parallel research streams (hyperscale identity,
massive scientific catalogs, geospatial engineering, data licensing), cited to
primary/authoritative sources, synthesized here into build guidance.

Plain-language note: written for a smart non-engineer. Sources are linked so any
claim can be checked; figures that could not be primary-verified are flagged.

---

## 0. The headline finding

**The best in the world — Google, Meta, Spotify, the people who track 2 billion
stars and every object in orbit — all solve "stable identity at massive scale
without corruption" using the SAME shape OneLive already uses for events:
extract → candidate → gate → promote, with everything auditable.** We are not
inventing a new discipline; we are applying our existing trust architecture to a
second kind of thing (entities: places, artists, venues, groups). That is a
strong signal we're on the right path — and it tells us exactly which proven
mechanisms to copy.

Five mechanisms recur in *every* domain we studied. Adopt these five and the
identity layer is built on bedrock:

1. **Opaque internal IDs + an external-ID crosswalk** (never dedupe on a name).
2. **Merge/split via redirects, never delete; never reuse a retired ID.**
3. **Append-only / versioned records** (overwrite-in-place *is* silent corruption).
4. **Never mint an identity from one observation — gate it with a duplicate check.**
5. **Probabilistic matching, then a governed promotion decision** (our gate).

---

## 1. Identity at hyperscale (Google, Meta, Spotify, MusicBrainz, MDM)

How platforms with hundreds of millions of users keep entity + preference data
correct:

- **Opaque surrogate IDs.** Google's Knowledge Graph gives every entity a
  meaningless "MID"; Meta's TAO gives every object a 64-bit ID; MusicBrainz an
  MBID. Source IDs (Ticketmaster's, Spotify's) become *attributes in a crosswalk
  table*, never our primary key. → build an `entity ↔ (source, source_id,
  provenance, confidence)` crosswalk.
- **Merge/split via redirects.** MusicBrainz keeps a merged entity's old ID alive
  in a redirect table pointing at the survivor, so every saved link keeps
  resolving. ORCID/ISNI (people) and RefSeq (genes) do the same "deprecate to a
  tombstone that redirects, never delete." → OneLive needs a `superseded_by`
  redirect from day one, or a bad merge silently breaks users' saved shows.
- **Append-only, versioned truth.** Uber's Schemaless stores immutable cells
  (updates append a new version); Google Spanner uses MVCC; master-data-
  management practice is explicit: *overwriting a field without keeping history
  is the definition of silent corruption.* → the canonical entity store is
  append-only; every merge/edit writes a new version with provenance.
- **Probabilistic matching, gated.** Entity resolution is inherently fuzzy —
  Splink (UK gov) and Zingg use statistical/ML matching with **blocking** (never
  compare every pair — fatal at scale) and route the *uncertain middle* to human
  review. Spotify uses audio+metadata classifiers to detect when one artist ID
  wrongly conflates two real people. → the matcher proposes candidates with a
  confidence; our admin-review gate disposes. This is our 4-state
  `unverified/likely/confirmed/disputed` model, exactly.
- **Preferences keyed to the canonical ID, timestamped.** Feature-store practice
  (Uber Michelangelo → Feast) keeps preferences point-in-time-correct and
  single-definition. Because preferences reference the *canonical* entity (and we
  keep redirects), a merge carries a user's preferences forward automatically.

*Sources: Google Enterprise KG / MID docs; Meta TAO (engineering.fb.com); Splink
(moj-analytical-services); Zingg; Spotify Research "Which Witch"; MusicBrainz
MBID + gid_redirect; Uber Schemaless; Google Spanner external consistency; MDM
golden-record/survivorship; Feast. Caveat: some (TAO 2013, Spotify article) were
read via search index, not full-page fetch — treat internals as original-design,
not current.*

---

## 2. Identity at the scale of billions (space, astronomy, physics, genomics, GS1)

The scientific/industrial catalogs handle millions-to-billions of entities and
have decades of hard-won anti-corruption discipline:

- **Never mint from one observation.** US Space Force will NOT catalog a new
  orbital object from a single sighting: **3–4 observations must correlate into a
  consistent orbit AND pass an explicit duplicate-check + maneuver-check before
  an ID is issued.** This is the single most important lesson — *the duplicate
  check is a hard gate before minting.* It maps precisely onto our
  candidate→gate→promote: the gate is where double-counting is prevented.
- **Two IDs, different jobs.** Satellites carry a meaningless sequential number
  (SATCAT) *and* a structured provenance ID (COSPAR = launch year + piece). Gaia
  embeds sky position in the star's 64-bit ID. → keep an opaque key for identity,
  optionally a structured/provenance key alongside; never join on the opaque
  key's structure. (Also: SATCAT is being widened from 5 to 9 digits as the
  catalog grew — **provision ID width generously up front.**)
- **Persistence = deprecate/redirect, never delete or reuse.** DOIs "cannot be
  deleted"; ORCID/ISNI deprecate to redirecting tombstones; RefSeq replaces with
  a forward pointer; Ensembl retires IDs and never reissues them; UniParc keeps
  every version ever seen and flags a cross-reference inactive the moment its
  source changes — a built-in staleness alarm. → retired IDs must never be
  recycled; that's silent corruption.
- **"New entity vs. edit" as a mechanical rule.** GS1's GTIN rules are a decision
  tree that says exactly which changes force a new product ID vs. an edit, so two
  operators reach the same answer. → OneLive needs an explicit, test-covered rule:
  does a venue rename / a rescheduled show / a lineup change create a *new* event
  or *edit* an existing one? Version it like `test_gates.py` covers our
  confidence-state transitions.
- **Rebuild-ability beats in-place mutation.** Gaia re-derives its entire
  2-billion-source catalog each release (IDs stable across releases, clustering
  improves). CERN addresses every collision by a hierarchical key and ships
  provenance + config with derived data. → design so the canonical catalog can be
  recomputed from raw + provenance and diffed against live — a safety net and a
  regression harness.

*Sources: Space-Track/SATCAT + COSPAR; USRA/NASA ODPO correlation paper; Gaia DR3
datamodel + source-list paper (arXiv 2012.06420); SIMBAD/VizieR/IVOA; CERN
EventIndex (arXiv 2211.08293); Ensembl/RefSeq/UniParc; DOI/Handle; ORCID/ISNI;
GS1 GTIN rules. Caveats flagged in-stream (Gaia bit layout, UCT thresholds read
from search snippets — confirm before mirroring exact encodings).*

---

## 3. Geospatial engineering — the concrete architecture

The geometry side has a clear, staged answer that needs **no new database** for
Phase 1:

**Phase 1 (now, US, county/city level):**
- **PostGIS on our existing Supabase Postgres.** Load US **Census TIGER/Line**
  county/place/tract polygons, GiST-indexed. A first-class Supabase extension —
  no new service to secure or monitor (this wins over adopting H3/S2 tooling now
  purely on operational simplicity).
- **Assign region at INGESTION, not query.** When an event is promoted, run
  `ST_Contains(region.geom, event.point)` ONCE and write `county_id`/`place_id`
  FK columns. `/tonight` then filters by a plain indexed FK — no geometry math on
  the hot path. This slots cleanly into our pipeline as another gate-side
  enrichment stage, independently auditable, and geometry (not AI) decides
  membership.
- **Model membership many-to-many / multi-scale from day one.** A point is in a
  county *and* a neighborhood *and* an overlapping "downtown" at once. A single
  `region_id` is a guaranteed future refactor.
- **"Near me" now:** `ST_DWithin` on the GiST index as a first walkable proxy.

**Phase 2 (international, multi-scale, draw-to-search, isochrones):**
- **Swap the boundary corpus to Overture Divisions** (country→microhood, one
  global source) when we leave the US; keep the same ingestion pattern.
- **Add H3** (Uber's hex index) as a denormalized column for two jobs Postgres
  does poorly: map-tile/heatmap aggregation at any zoom, and coarse pre-filtering
  of "everything in region X" before the exact `ST_Contains`. (H3 over S2 because
  our product is city-scale density; pick S2 only if we later need sphere-correct
  geofences.)
- **Draw-to-search** (§5 of the proposal): client lasso (Mapbox GL Draw /
  MapLibre) → GeoJSON polygon → H3-cover prefilter → `ST_Contains` refine; snap
  to a named admin polygon when the freehand nearly matches one.
- **Isochrones ("10-minute walk"):** self-host **Valhalla/OSRM** on the OSM road
  network — a real street-network travel-time shape, far truer than a radius.
  Precompute for stable anchors (venues, transit stops); on-demand for arbitrary
  origins. A managed isochrone API is the fast path but a spend/new-service
  decision — **founder-crucial**, flagged not adopted.

**Two-phase query everywhere:** cheap approximate cover (cell/bounding-box) →
exact refine. Every scaled system does this.

*Sources: PostGIS docs + Crunchy Data indexing; Uber H3; Google S2; Overture
Divisions; OSM admin data model; TIGER/Line; Natural Earth; Valhalla/OSRM
isochrones; Mapbox GL Draw; BigQuery GIS. Latency figures in-stream are secondary
— validate on our own data before quoting.*

---

## 4. Licensing — the verified answer (and the ODbL cost question)

**Cost across every recommended source: $0.** None charge a fee. The only
"costs" are compliance obligations (attribution, and for one license,
share-alike).

**ODbL (OpenStreetMap) in plain terms:** free, with three duties — attribute,
share-alike, keep-open. The decisive legal fact: **using the data to produce a
map or a search result is a "Produced Work" → attribution ONLY. Share-alike bites
only if you publicly distribute a *modified database*.** OSM's own guidance is
explicit that *"conveying does not include interaction with a user through a
computer network"* — so a web app serving query results is not "distributing the
database." For OneLive's use (internal point-in-region + an attributed map),
**the only obligation is on-screen attribution.**

| Source | License | Cost | Share-alike? | Coverage |
|---|---|---|---|---|
| **US Census TIGER/Line** | Public domain | $0 | No | US only |
| **Wikidata** | CC0 | $0 | No | Global (place identity/hierarchy, informal regions) |
| **Natural Earth** | Public domain | $0 | No | Global (coarse) |
| **Overture Divisions/Places** | CDLA-Permissive-2.0 | $0 | **No** | Global admin boundaries |
| **GeoNames / Who's On First** | CC-BY | $0 | No | Global gazetteer |
| **OpenStreetMap** | ODbL | $0 | Only if you distribute a modified DB | Global |
| **GADM** | ⚠️ non-commercial only | — | — | **AVOID (hard wall for a for-profit)** |

**Recommendation:** for the US launch use **TIGER (public domain) + Wikidata
(CC0)** — zero share-alike to reason about. For international, **Overture
Divisions (CDLA-Permissive) + Wikidata**. Use **OSM/ODbL only for the visible
map + internal geofencing** (attribution-only), kept unmodified and separate (a
"Collective Database"). **The one thing to never do: publicly redistribute a
database that merges OSM boundaries with our proprietary event data** — that is
the single move that turns ODbL's cheap attribution into a real copyleft
obligation. **AVOID GADM entirely** (non-commercial license — worse than ODbL).

**Still needs a real lawyer before international launch** (R-016 discipline):
the ODbL §4.6 "derivative database served publicly" edge as it maps to our exact
architecture; the "Substantial extract" threshold; Overture per-layer license
confirmation; and any use of the OpenStreetMap name/logo in our own branding
(trademark, separate from the data license).

*Sources: ODbL 1.0 text (opendatacommons.org); OSMF Attribution / Geocoding /
Collective-Database / Substantial guidelines + Legal FAQ; Census TIGER tech doc;
Wikidata:Licensing; Natural Earth terms; GeoNames; geoBoundaries; Overture
attribution docs; GADM license. Caveat: the license/OSMF pages were read via
search synthesis (egress blocked direct fetch) — confirm exact clauses on the
primary URLs before relying on them, and get legal sign-off before international.*

---

## 5. What this changes about the build (net)

1. **The identity layer is our existing pipeline, re-pointed at entities.**
   extract (parse a source's artist/venue) → candidate (a proposed entity match,
   scored) → gate (duplicate-check + admin review) → promote (write the canonical
   record). Nothing new to invent; the discipline is proven across every domain.
2. **Four non-negotiable primitives, added up front:** opaque IDs + crosswalk;
   redirect-on-merge (never delete/reuse); append-only versioning; a mechanical
   "new-vs-edit" ruleset (test-covered).
3. **Geometry needs no new infrastructure now** — PostGIS on Supabase, region
   assigned at ingestion. H3 and Valhalla are later accelerators, not launch
   dependencies.
4. **Licensing is a solved, $0 problem for the US launch** (TIGER + Wikidata);
   ODbL is usable-but-managed for the map, with a clear "never redistribute a
   merged DB" rule and a lawyer gate before international.

These update how `ONE_LIVE_GEO_IDENTITY_v1.md` Phases 1 and 2 get built; they do
not relax any trust invariant or gate. Founder-crucial items surfaced:
self-hosting/managed isochrone spend, and the pre-international legal review.
