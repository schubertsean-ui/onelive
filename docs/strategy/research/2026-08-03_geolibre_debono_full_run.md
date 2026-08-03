# GeoLibre × 1Live — the FULL de Bono run (all operators, all hats)

**Statement S:** "1Live adopts GeoLibre as its geospatial/map layer."
**Mode:** sequential (docs/hats/README.md tier 1) — one agent wears the hats in
de Bono's sequence: Blue frame → White facts → Green (full po battery) →
Yellow and Black as independent-as-possible passes → devil's advocate on any
consensus → Blue conflict-preserving merge. **Custody note (fail-closed):**
the generator-side Black pass below carries NO adversarial authority; the real
Black hat is the non-Claude adversarial review running on the PR that lands
this document. Red = the founder, never an agent (already exercised: the
2026-08-03 ratification of the prototype bench).
**Battery generation:** `python tools/po_battery.py "1Live adopts GeoLibre as
its geospatial/map layer" --seed 42` (random word: **lantern**). Rules
honored: every provocation written BEFORE any judging; ≥2 movement techniques
per provocation; provocations are stimuli, never facts — nothing below enters
memory/candidate data/user copy except through normal gates.
**Origin of this document:** founder correction 2026-08-03 (verbatim: *"I
expect when I say debono for the entire Po model to be run with all the
reverse and random and invert etc - and all the hats!"*) — the first
delivery condensed the battery; this is the full write-out. Decision record:
`docs/memory/decisions/2026-08-03_debono-means-full-model.md`.

---

## BLUE — frame (pre-registered, before any lens ran)

Decision in play: what role, if any, does GeoLibre take in 1Live?
Sub-decisions: (a) product dependency yes/no; (b) ops/analysis instrument
yes/no; (c) draw-to-search UX bench yes/no (RATIFIED by Red 2026-08-03);
(d) what the harvest should feed (tile decision, nearby lens, density work,
sourcing). Success = a merged view that preserves every unresolved conflict
explicitly, plus a harvest list traceable provocation-by-provocation.
Non-goals: no gate, threshold, or invariant moves on the strength of
anything below.

## WHITE — facts only (verified 2026-08-03, sources named)

- GeoLibre: opengeos org (maintainer lineage: leafmap/geemap, lead Qiusheng
  Wu), MIT license. Stack: Tauri v2, React, TypeScript, MapLibre GL JS,
  DuckDB-WASM Spatial, deck.gl. 1,000+ WASM geoprocessing tools
  (whitebox-derived, `opengeos/geolibre-rust`). Runs browser / desktop /
  Android / Jupyter (`geolibre` anywidget). Local-first: data does not leave
  the machine. [github.com/opengeos/GeoLibre, README + releases]
- Releases: v2.0.0 (2026-07-11) → v2.4.0 (2026-07-29): five minors in 18
  days. Roadmap: no semver guarantees, no deprecation policy, no LTS.
  v2.4 added a versioned `postMessage` embed API (whole-app-in-iframe, not a
  component) and an AI-assistant model picker (multi-provider, keys optional).
  [releases page; docs/roadmap.md]
- 1Live geo surfaces (UI canon): mini-map chip (§7), address+distance
  ("0.4 mi"), nearby lens = street map + 5-minute walk ring + POI counts +
  transport guidance (RATIFIED layout, build founder-gated), draw-to-search
  loop (PROPOSAL, founder-gated; spec citation unresolved — R-073).
- 1Live geo data held: venue lat/lng in `licensed_event` (Ticketmaster
  CAPCOG import). Boundary model: CAPCOG county/city name match
  (`worker/region/capcog.py`), layered-boundary upgrade queued (TODOS P3).
- Founder-gated money decisions (canon §12): "any map tiles (Mapbox)",
  nearby-POI dataset (Google Places / OSM).
- Free POI sources exist: Overture Places (CDLA-Permissive-2.0, GeoParquet —
  DuckDB-native), OSM (ODbL, share-alike), TABC + Austin datasets on Socrata
  (existing generic importer `worker/importers/socrata.py`).
- CWV budget: LCP ≤ 2.5 s. Calm/cognitive-load law is canon (§1).

## GREEN — the full po battery

### Step 0 — assumptions S takes for granted

- A1. 1Live needs a geospatial/map layer at all.
- A2. "The layer" is one thing — a single tool serves every geo surface.
- A3. Adopting means embedding third-party software in the product.
- A4. Maps are rendered client-side at view time.
- A5. Map data (tiles, POIs) comes from an external provider.
- A6. GeoLibre qualifies because it is free and open source.
- A7. The map layer serves end users (consumers).
- A8. Venue location is simple, uncontested data.

### P1 — ESCAPE (negate every assumption)

- **P1.1 Po: 1Live needs no map.**
  Movement — *difference:* the provoked world ships geo value as TEXT; our
  canon already makes "0.4 mi" the primary geo utility and the map
  secondary. *Positive:* distance is arithmetic on lat/lng we already hold —
  shippable with zero map libraries. → **H2, H11**
- **P1.2 Po: every geo surface uses a different tool.**
  Movement — *extract principle:* per-surface fit beats platform adoption;
  the chip, the lens, and draw-to-search have different weight budgets.
  *Special circumstances:* exactly right when surfaces ship years apart, as
  ours will (chip now-ish, lens and loop founder-gated). → **H7**
- **P1.3 Po: the product contains zero map software.**
  Movement — *moment to moment:* a card loads; the "map" is a pre-rendered
  image the pipeline made last night; nothing map-shaped executes on the
  phone. *Positive:* protects LCP absolutely. → **H2**
- **P1.4 Po: maps are rendered years before anyone looks.**
  Movement — *extract principle:* render-at-ingest, not render-at-view —
  the pipeline's batch nature already works this way for everything else.
  *Difference:* map freshness becomes a pipeline concern (re-render on venue
  change), which our provenance discipline already handles. → **H2, H3**
- **P1.5 Po: 1Live provides its own map data to the world.**
  Movement — *positive:* our promoted events ARE geodata someone else would
  want; publishing them internally as standard geo formats makes every tool
  a consumer. *Extract principle:* be a producer of geodata, a consumer of
  basemaps. → **H4**
- **P1.6 Po: GeoLibre costs $10,000 a month.**
  Movement — *difference:* if it cost that, we'd scope precisely what we
  needed and build only that — do that anyway. *Special circumstances:*
  "free" software still bills in attention and churn-tracking; treat
  adoption cost as real even at $0 license. → feeds Black.
- **P1.7 Po: the map serves only machines, never people.**
  Movement — *positive:* taken straight, that's the ops console and the
  density analysis — the first legitimate geo consumers ARE internal.
  *Moment to moment:* an agent opens a coverage map, spots a POI-dense,
  event-sparse pocket, adds sources for it; no user ever saw a map. → **H12, H10**
- **P1.8 Po: venue locations are disputed data.**
  Movement — *extract principle:* geo facts deserve the same provenance
  discipline as any fact — record WHERE each lat/lng came from; two sources
  disagreeing on a venue's location is a real drift case (we already caught
  a cross-source DATE drift once). *Special circumstances:* pop-ups, food
  trucks, festival grounds — locations genuinely contested. → **H8**

### P2 — REVERSAL / INVERT / OPPOSITE (both directions)

- **P2.1 Po: GeoLibre adopts 1Live (we are its events layer).**
  Movement — *difference:* the flow inverts — our data flows OUT into geo
  tools rather than a map widget flowing IN. *Positive:* a GeoJSON/PMTiles
  export of promoted events makes GeoLibre, QGIS, and the future native lens
  all consumers of one artifact; the pipeline stays tool-agnostic. → **H4**
- **P2.2 Po: the events are the base map; geography is the overlay.**
  Movement — *extract principle:* in a tonight-product the event is the
  figure and the city is the ground — design the lens so events render
  first and the basemap is the quietest layer (calm law alignment).
  *Moment to moment:* lens opens: dots and walk-ring appear instantly from
  our own data; basemap tiles fade in beneath. → **H5, H6**

### P3 — EXAGGERATION (every quantity, absurdly up AND down)

- **P3.1 Po (up): all 1,000 geoprocessing tools run on every page view.**
  Movement — *positive (taken straight):* this is literally what embedding
  the workbench risks; the provocation is the dependency verdict in one
  line. *Difference:* the provoked world's page weighs hundreds of MB; ours
  must stay near zero — the gap IS the decision. → dependency NO.
- **P3.2 Po (down): the entire map is one pixel.**
  Movement — *positive:* the canon's chip is nearly that — Austin outline +
  river + locale dot; one static SVG. *Extract principle:* minimum viable
  cartography; every additional map feature must fight the calm law. → **H2**
- **P3.3 Po (up): a million residents each draw 100 loops tonight.**
  Movement — *moment to moment:* at that load, per-draw server queries die;
  only client-side point-in-polygon over a small nightly event set survives —
  which is exactly the cheap implementation. *Difference:* loops are also a
  DEMAND signal at scale — a heatmap of where people LOOK. → **H10**
- **P3.4 Po (down): one loop is drawn per year.**
  Movement — *special circumstances:* if usage were that low the surface
  shouldn't exist — which is why the bench (feel it before building it)
  precedes the build; the bench is the cheap test of whether the gesture is
  loved. *Positive:* validates Red's gating of the feature. → bench rationale.

### P4 — DISTORTION (scramble time-order / relationship structure)

- **P4.1 Po: the map renders before the event is verified.**
  Movement — *special circumstances:* legitimate exactly once — the OPS
  console mapping CANDIDATES pre-gate (dedup by proximity, coverage holes).
  *Extract principle:* geo tooling belongs upstream (ops) before downstream
  (consumers). → **H3, H12**
- **P4.2 Po: the loop is drawn before any events exist; events are created to fill it.**
  Movement — *positive (taken straight):* a drawn loop over an event-empty
  area is a SOURCING instruction — "people look here; we have nothing here" —
  feeding the source-discovery engine. *Difference:* draw-to-search becomes
  a two-sided instrument: search for users, coverage-gap probe for ops. → **H10**
- **P4.3 Po: the venue moves to the user after the map is read.**
  Movement — *extract principle:* bring the geography to the person —
  precomputed distance, walk-time, and transport guidance attached to each
  event AT PROMOTE TIME, so the "map" arrives as data inside the feed.
  *Moment to moment:* card shows "0.4 mi · 8-min walk" with no map fetch. → **H3, H11**

### P5 — WISHFUL ("wouldn't it be nice if…")

- **P5.1 Po: tiles are free forever, never phone home, never go stale.**
  Movement — *positive (taken straight):* two-thirds TRUE today — MapLibre +
  self-hosted PMTiles (one-time Austin extract, tens of MB, our storage) is
  free and phones nobody; staleness remains ours to schedule (quarterly
  re-extract). *Difference:* converts the canon's "any map tiles (Mapbox)"
  money decision into a ~$0, no-new-vendor decision awaiting Red. → **H1**
- **P5.2 Po: every phone already contains the map of Austin.**
  Movement — *extract principle:* PWA-cache the basemap once; offline-capable
  nearby lens (service-worker + PMTiles range requests). *Special
  circumstances:* festival crowds on saturated cell networks — exactly our
  peak moment. → **H6**

### P6 — ABSURD (category error, past exaggeration)

- **P6.1 Po: the venues render the map themselves.**
  Movement — *extract principle:* venue-owned locality — the venue block's
  character line already renders "place" in WORDS; geography stays
  narrative-first, map-second (calm law). *Positive:* no map dependency for
  the thing users actually read. → supports **H2**.
- **P6.2 Po: the events attend the map.**
  Movement — *difference:* the provoked world's map is an audience — events
  present themselves TO a location+time context. Inverted into ours: a
  "near me now" ordering is just distance-sort over precomputed geo data,
  no map surface required. *Moment to moment:* user opens feed at 9pm;
  closest-soonest bubbles up; zero tiles fetched. → **H9**

### P7 — RANDOM ENTRY (word: "lantern")

Associations: portable, hand-carried; lights a small radius; fuel-limited;
works off-grid; released at festivals; kin to lighthouse; draws moths; dims
at dawn.

- **P7.1 Po: the map is a lantern.**
  Movement — *extract principle:* illuminate a small radius around one
  point, never the whole city — the nearby lens's 5-minute walk ring IS a
  lantern; a pan-the-city explorer is out of character. *Difference:*
  micro-map per venue vs. city GIS — argues the dependency verdict again
  from a design direction. → **H5**
- **P7.2 Po: events are moths drawn to the user's light.**
  Movement — *positive:* attraction inverts search — the feed already does
  time-attraction; add distance-attraction ("near me now") from precomputed
  data. *Special circumstances:* late-night mode, walking home. → **H9**
- **P7.3 Po: the map dims at dawn.**
  Movement — *positive (taken straight):* the Night Out spec already says
  the nearby experience is EPHEMERAL — "dies at sunrise, no profile." The
  map should share that lifecycle: nightly build, nightly expiry; no
  standing map infra. *Extract principle:* cache lifetimes follow product
  ephemerality, not infra convention. → **H6**
- **P7.4 Po: users release lanterns that drift (festival sky-lanterns).**
  Movement — *difference:* a drawn loop someone SHARES is a drifting
  lantern — the canon already makes loops shareable; the share is the
  growth loop for the surface. *Positive:* bench should test the share
  gesture too, not just the draw. → bench scope note.

### P8 — RANDOM + each operator (lantern associations, mapped back)

- **P8.1 (+ESCAPE) Po: a lantern that needs no fuel.**
  Movement — *extract principle:* no-fuel = no vendor, no meter, no keys —
  the bench and the tile path both run fuel-free (local, self-hosted).
  *Positive:* the GeoLibre bench needs no account by design. → **H1, H12**
- **P8.2 (+REVERSAL) Po: the near things find the lantern.**
  Movement — *difference:* POIs precomputed per venue at promote time
  (counts + distances stored server-side) instead of client geo-queries at
  view time. *Moment to moment:* lens opens; counts are already in the
  payload. → **H3**
- **P8.3 (+EXAGGERATION) Po: 10,000 lanterns; Po: one lantern for the whole city.**
  Movement — *extract principle (up):* per-venue pre-rendered chips,
  batch-generated — 10,000 tiny lanterns are cheap when made offline.
  *Difference (down):* one city-wide map for everything is the GIS-workbench
  smell; refuse it. → **H2, H7**
- **P8.4 (+DISTORTION) Po: light arrives before dark.**
  Movement — *extract principle:* compute nearby data BEFORE the night —
  at promote time, in the pipeline — never at page view. *Positive:*
  aligns with the pipeline's batch physics. → **H3**
- **P8.5 (+WISHFUL) Po: the lantern never runs out.**
  Movement — *positive (taken straight):* a one-time tile extract + static
  chips genuinely never meter; the only renewable is a scheduled re-extract.
  *Special circumstances:* if 1Live scales to many metros, per-metro
  extracts stay linear and cheap. → **H1**
- **P8.6 (+ABSURD) Po: the lantern carries the walker.**
  Movement — *difference:* the map moves the person — transport guidance
  (walk / pedicab / ride by distance band) is already canon; derive it from
  the same precomputed distance, no map needed. *Moment to moment:* card
  says "12 min walk or 4 min pedicab"; user never opens a map. → **H11**

### GREEN harvest (every idea traceable)

| # | Idea | From |
|---|---|---|
| H1 | MapLibre GL JS + self-hosted PMTiles (one-time Austin extract) as the tile answer — turns the founder-gated "any map tiles" money decision into a ~$0/no-new-vendor option awaiting Red | P5.1, P8.1, P8.5 |
| H2 | Mini-map chip as PIPELINE-pre-rendered static SVG/PNG per venue — zero runtime map code on cards, LCP protected | P1.1, P1.3, P1.4, P3.2, P6.1, P8.3 |
| H3 | Precompute POI counts, distances, walk-times at PROMOTE time (server-side); lens and cards consume stored data | P1.4, P4.1, P4.3, P8.2, P8.4 |
| H4 | Publish promoted events internally as GeoJSON/PMTiles — one artifact, every tool (GeoLibre/QGIS/native lens) a consumer | P1.5, P2.1 |
| H5 | Nearby lens scoped as single-venue micro-map (walk ring), never a city explorer | P2.2, P7.1 |
| H6 | Map lifecycle follows product ephemerality — nightly build/expiry, PWA-cached basemap, offline-capable at festival peaks | P2.2, P5.2, P7.3 |
| H7 | "The layer" is three different needs (chip / lens / loop) — per-surface tools, no platform adoption | P1.2, P8.3 |
| H8 | Geo provenance: record the SOURCE of each venue lat/lng; location disagreement is a drift case like any fact | P1.8 |
| H9 | "Near me now" ordering = distance-sort over precomputed data — geo value with no map surface at all | P6.2, P7.2 |
| H10 | Draw-to-search doubles as a COVERAGE-GAP PROBE — loops over event-empty areas are sourcing instructions for the discovery engine | P3.3, P4.2 |
| H11 | Transport guidance derived from precomputed distance bands — no map required | P1.1, P4.3, P8.6 |
| H12 | GeoLibre desktop/Jupyter as the ops density/coverage instrument — zero coupling, no account, data local | P1.7, P4.1, P8.1 |

## YELLOW — deliberate best case (independent pass, taken straight)

Best true version: the bench is also TRAINING — every hour in it builds
fluency with the exact primitives (MapLibre, PMTiles, DuckDB/GeoParquet) the
native Phase-3 build will use, so prototype time is not thrown away, it is
the first hour of the build. The density work seeds the nearby-POI dataset
the canon needs: Overture/TABC ingested through the existing Socrata/importer
machinery turns a founder-gated PURCHASE decision into a founder-gated
INGEST decision — same gate, near-zero cost. opengeos' decade of maintained
tools (leafmap, geemap) is real evidence GeoLibre outlives its churn phase.
Upside ceiling: the whole spatial phase — chip, lens, loop, density-steered
sourcing — ships on free primitives, validated by a bench that cost nothing,
with Red's gates intact at every step. (Kaizen M8: this validated-upside
lens is the harvest's counterweight, not decoration.)

## BLACK — generator-side attack (NO adversarial authority; the real Black
seat is the non-Claude adversarial review on the PR landing this document)

1. **Anchoring risk:** bench feel ≠ native feel; GeoLibre's draw gesture and
   styling could quietly become the spec. Mitigation already written into
   the decision record (findings are directional, never visual canon) — but
   the risk is behavioral, not textual; the design formality must restate it
   at every bench run. *(Residual.)*
2. **Attention spend:** a GIS playground adjacent to a founder-gated feature
   invites premature work. Mitigation: the TODOS item binds the bench to the
   gate decision; the CAPCOG mission outranks it. *(Managed.)*
3. **License trap:** OSM ODbL share-alike could contaminate product-bound
   derived data (nearby counts). Mitigation: prefer Overture
   (CDLA-Permissive-2.0) for anything product-bound; a written source-license
   check belongs in the POI-dataset decision packet when Red opens that
   gate. *(Residual — carried into the merge.)*
4. **Boundary leak:** the density workflow's numbers could be hand-copied
   into product surfaces. The boundary (product numbers recompute in the
   pipeline from ingested data) is stated but NOT mechanical today; it
   becomes enforceable only when a product surface first consumes POI data —
   at which point a gate must exist. *(Residual — carried into the merge.)*
5. **Embedded AI assistant:** bench users must leave provider keys unset;
   key/spend discipline applies even to $0 tools. *(Managed — bench needs no
   keys by design.)*
6. **Data custody:** exporting event points into a browser tool is local-only
   by GeoLibre's architecture and the data is our own; low risk, stated for
   completeness. *(Managed.)*

## DEVIL'S ADVOCATE — against the emerging consensus

Consensus forming: "bench is free and harmless; dependency-no is final."
Attack both: (a) *Nothing is free* — the bench bills in attention and in
subtle design anchoring (Black #1/#2); the merge must carry those as live
conditions, not footnotes. (b) *Dependency-no may be over-final* — GeoLibre
is 3 weeks into its 2.x line; if it ships a stable, semver'd, component-level
embed (not whole-app iframe), the CWV and canon-control objections weaken.
The verdict deserves an objective RE-OPEN trigger, not a forever-no:
**re-evaluate if GeoLibre ships a versioned npm component with a stated
semver/deprecation policy AND a bundle path under ~200 KB gz for a
draw+query-only build.** Until then, dependency-no stands.

## BLUE — merge (conflict preserved, never averaged)

- **Ratified and standing (Red, 2026-08-03):** the draw-to-search UX bench,
  as a design-formality step. Bench scope grows one item from this run:
  test the SHARE gesture, not just the draw (P7.4).
- **Dependency verdict:** NO — with the devil's-advocate re-open trigger
  recorded above (component embed + semver + ~200 KB path).
- **Standing conflict #1 (preserved, unresolved):** Yellow's "the bench
  seeds the POI dataset" vs Black's "the density workflow must not become a
  product path." Not averaged; ROUTED: seeding happens only via the
  importer/pipeline (an ingest job through normal gates), never via numbers
  carried out of a bench session. The conflict stays live until a product
  surface first consumes POI data, at which point Black #4's mechanical
  guard must exist before launch.
- **Standing conflict #2 (preserved):** Yellow's "bench time is training"
  vs Black's "attention spend / anchoring." Both true; the binding is the
  TODOS gate-coupling (bench fires with the gate decision, not before the
  CAPCOG mission's needs) and the directional-only rule restated at each run.
- **Harvest routing (all through normal gates, nothing self-executing):**
  H1 → the tile decision packet for Red, when Red opens it. H2/H3/H9/H11 →
  pipeline work items, no tile decision needed, buildable when prioritized.
  H4 → cheap pipeline artifact, any session. H5/H6 → design constraints
  logged for the lens build. H7 → standing architecture note. H8 → a real
  candidate for the truth-states work (geo provenance) — routed to the
  R-064 implementation session as an input, not a scope change. H10 → noted
  for the source-discovery engine design. H12 → available now, ops-side.
- **Red (founder) keeps:** the draw-to-search gate itself, the tile
  decision, the POI-dataset decision, any spend.
