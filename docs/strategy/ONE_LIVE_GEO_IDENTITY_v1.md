# ONE LIVE — Geography & Identity Backbone (PROPOSAL v1)

**Status: PROPOSAL, founder-gated.** Builds nothing on its own. Written
2026-07-29 at founder direction ("this gets at the larger geo issue which I
think we need to address now"). Ratify section by section; PROPOSAL ≠ license to
build.

Plain-language note (per the charter's founder-communication rules): this doc
assumes a smart non-engineer. Jargon is explained the first time it appears.

---

## 1. Why this exists — the problem in one paragraph

The live market boundary today is a **hand-maintained list of place names**
(`worker/region/capcog.py`: "austin"→Travis, "san antonio"→Bexar, …). It works,
but it is fragile in a way we have now paid for repeatedly:

- The boundary PR (#107) took **four independent review rounds**, each finding a
  new way a place *name* could be mislabeled (a contradictory county field, a
  bare county name, a fallback field, a same-name collision, a trailing period).
- **Fredericksburg was silently excluded** — a Hill Country wine town the
  founder explicitly wants — because it sat in a "known outside" list.
- Adding a county means **hand-editing town lists**.

Every one of these is the *same root cause*: we are matching **strings that
humans typed**, not deciding **where a place actually is**. As OneLive grows
beyond Central Texas — the founder's stated ambition ("festivals in Southern
California… Northern Italy… the Dolomites… a prefecture in Japan… the Ring of
Kerry") — the string approach does not scale. We need a real geographic and
identity foundation.

This is **two linked problems**, and the same design idea solves both.

---

## 2. The two problems

### 2a. Geography — "where is this, at any zoom level?"
A user should be able to ask for events in a **country** (Ireland), a **region**
(Northern Italy), a **sub-region** (the Dolomites, the Ring of Kerry — informal,
fuzzy areas), a **state/province**, a **county/prefecture**, a **city**, or a
**neighborhood** — and get the right answer whether they're trip-planning ahead
or opportunistically discovering while already somewhere unfamiliar.

### 2b. Identity — "is this the same real thing?"
The same **artist**, **venue**, or **group** appears across many sources, spelled
differently, in different languages. To manage and mine data as we grow, each
real-world entity needs **one stable record** that everything else points at —
so dedup, provenance, trust, and the matching engine all have a clean spine.

---

## 3. The core design decision (the "why this, not that")

**Keep our own stable internal ID for every entity, but anchor it to the open
world authorities that already maintain the planet's identities — rather than
inventing a proprietary global ID scheme from scratch.**

Concretely, every canonical entity we store gets:
- **Our own surrogate ID** (a stable internal key — a ULID/UUID). This is what
  our data points at, so we are never hostage to an external ID's churn, and we
  can represent things no authority lists (a tiny Hill Country winery).
- **A crosswalk of external IDs** to open authorities:
  - **Geography:** **ISO 3166** (countries + states/provinces), **Wikidata**
    QIDs and **GeoNames** IDs (stable IDs for places — *including informal
    regions*: "the Dolomites," "the Ring of Kerry," "Southern California" all
    exist as real Wikidata entities), and **OpenStreetMap** relations for the
    actual boundary **polygons**.
  - **People / groups:** **MusicBrainz** IDs (artists), **Wikidata** QIDs (a
    universal join key), plus the source IDs we already touch (Ticketmaster,
    SeatGeek) and official social handles.

**Why anchor to open authorities instead of building our own global IDs:**
Reinventing identifiers for the world's places, people, and organizations is
enormous, perpetually incomplete, and *isolates* us from a huge amount of free
signal — multilingual names, hierarchy (this city is in this county is in this
state is in this country), and dedup. The authorities already maintain all of
it. We layer our stable key on top and cross-reference — which is exactly the
venue cross-referencing already in the Night Out spec (Ticketmaster × Google
Places × TABC).

**Why keep our own key anyway:** so a broken or churned external ID never breaks
our data, and so we can carry entities the authorities don't have.

---

## 4. Geography, mechanically — geometry beats names

Once a place has a **polygon** (from OSM/Census boundary data) and an event has
**coordinates** (`venue_lat`/`venue_lng`, which our importers already populate),
"is this event in region X?" is a **point-in-polygon** test:

- No spelling. No contradictory-field games. No same-name collisions. A point is
  inside Travis County's boundary or it isn't.
- "Include Gillespie" becomes **adding one county polygon to the in-market set**,
  not hand-editing town lists.
- The *exact same machinery* answers "in the Dolomites," "within 20 minutes'
  walk," and "in this neighborhood" — one engine, every zoom level. This is also
  the foundation the Night Out "what's nearby" feature needs.

**Informal regions** (Southern California, Northern Italy, the Dolomites) are the
genuinely hard part — they're fuzzy, overlapping, and not administrative. Many
exist as Wikidata/OSM relations with usable polygons; the rest we curate. Where a
boundary is genuinely contested, we show it **honestly** (disputed boundaries
shown, not hidden — consistent with our trust rules), and we keep the
**keep-and-count-unknowns** discipline: a place we can't yet classify is shown
and counted as a coverage-gap worklist item, never silently dropped.

---

## 5. Draw-to-search — the geometry engine's headline consumer feature

Founder idea, 2026-07-29: alongside **speaking** or **typing** what they want
(activities, locales, geographies, timeframes, and combinations), a user can just
**draw a loop on the map with their finger** — and we return the events inside
it. Crucially, the loop can be **any size**: a single block, "everything within a
ten-minute walk," a whole neighborhood, a metro, a region, or a country. One
gesture, every zoom level.

**Why this is nearly free once geometry exists:** a finger-drawn loop *is* a
polygon. Answering "what events are in it?" is the **exact same point-in-polygon
query** as the market-boundary check (§4) — just with a user-supplied shape
instead of a county boundary. Building the geometry engine (Phase 1) is what
makes this feature a small UI addition rather than a from-scratch system. It is
the single most compelling reason to prioritize the geometry foundation.

**"Truing up" the freehand shape** (the founder's phrase — interpret the rough
loop into a meaningful area, in the background):
- **Literal first, always honest.** We query the *actual shape drawn*, so "these
  three blocks" means those blocks — never silently widened. Keep-and-count
  holds: unknowns inside the loop are shown and counted, and if the loop covers a
  coverage gap we say so rather than making it look empty.
- **Name it by the right layer, chosen by the loop's SIZE.** A tiny loop is named
  by neighborhood/district; a large one by county / region / country. So the user
  sees "Searching your area · **East Austin**" or "· **Hill Country**" — a
  nameable, **shareable** area (this feeds the Group-Plans / share-card path).
- **Offer a snap, never force one.** "Looks like you meant *downtown* — use that
  boundary instead?" The user stays in control; we never override the literal
  selection with an assumption.
- **Walk/drive-time variant.** A small loop can offer "within a 10-minute walk of
  here" — an **isochrone** (travel-time area), which is the same containment
  query against a travel-time polygon. This is the Night Out "what's nearby"
  feature in map form.

**One input model, three ways in.** Speak, type, or draw all resolve to the same
underlying query: **{ geo-area × timeframe × filters }**. The geo-area is a
polygon (drawn, or resolved from a spoken/typed place name via §3's authority
crosswalk); the rest is unchanged. This keeps the voice-navigation requirement,
typed search, and draw-to-search as three faces of one engine, not three
codebases.

**Trust & privacy rails (unchanged invariants):**
- **No pay-to-rank, ever** — a drawn-area result must never be gameable by who
  paid; results are ranked by honest relevance/time/proximity only.
- **Location is opt-in and disclosed** — if we center the map on the user's
  position, that's an explicit permission with a visible indicator and a
  plain-language disclosure, same discipline as the voice-nav Web Speech note.
  The drawn gesture itself is client-side.
- **Disputed/again shown, never hidden** — a low-confidence event inside the loop
  still appears with its quiet caveat.

**Where it lands:** the geometry engine (Phase 1) is the prerequisite; the
draw-to-search UI is a consumer feature that rides on it (proposed for the same
wave as, or just after, Phase 1 — a design-brief item, since it touches the map
UX and the trust-display rules). Informal/vernacular naming of arbitrary drawn
areas leans on the §3 authority crosswalk (Wikidata/OSM named regions), so it
strengthens the case for Phase 2 as international coverage grows.

---

## 6. Phased plan (what to build, and when)

**Phase 1 — County geometry (proposed: build NOW, as the next increment).**
A pure point-in-polygon module: venue lat/lng → county → in-market or not, using
real county boundaries (US Census TIGER — free, public). This ends the
string-bypass bug class for any event that has coordinates. The existing
name-based boundary (#107, now including Gillespie) **stays as the fallback** for
rows *without* coordinates — geometry-first, name-match-fallback, one boundary.
Follows the proven TABC pattern: pure logic fixture-tested here; boundary data
fetched where egress reaches the data source (CI, not the sandbox).

**Phase 2 — Identity + geography backbone (proposed: DESIGN now, BUILD at the
next-locale boundary).** The canonical-entity table + external-ID crosswalk +
the place hierarchy (country→region→…→neighborhood) loaded from the open
authorities. This is a schema/data-model investment touching the DB, the
pipeline, and the matching engine — substantial, ongoing work. The **objective
trigger to start building: before the first non-Texas locale opens.** Doing it
earlier is over-engineering (no multi-region data yet); doing it later is a
painful retrofit.

**Bridge:** Phase 1's place records should carry **empty slots for the external
IDs** (Wikidata/GeoNames/ISO) from day one, so Phase 1 is the *first brick* of
Phase 2, not throwaway.

---

## 7. Tradeoffs & risks (stated honestly)

- **Coordinate coverage isn't 100%.** Long-tail/promoted events often lack
  lat/lng — which is *why* the name-based boundary stays as the fallback. We
  carry two mechanisms (defense-in-depth), not one. **Recommended first step:
  measure the actual lat/lng coverage %** before committing to geometry as
  primary, so we decide on data, not a guess.
- **Data licensing is founder-crucial.** Wikidata (CC0) and MusicBrainz (CC0)
  are clean. GeoNames is CC-BY (attribution). **OpenStreetMap is ODbL —
  share-alike with redistribution obligations** that need a legal-posture read
  before we bake OSM-derived polygons into a product we may monetize. Census
  TIGER is US-public-domain (clean) but US-only. No commitment to any source
  without founder sign-off — same discipline as the aggregator-ToS check
  (R-016).
- **Informal regions are fuzzy** — we choose/curate definitions and show them
  honestly; some will be genuinely debatable.
- **Identity systems attract gold-plating** — this needs a tight contract and
  incremental delivery or it sprawls.
- **A polygon test costs more than a string lookup** — negligible per page,
  real at large scale; a spatial index (or Postgres/PostGIS) handles it when we
  get there.

---

## 8. Connections to existing canon

- **Graph-brain (G-BRAIN option 1D).** Entity + geography + relationship queries
  ("what artists played in this region last summer?") are precisely the
  pre-registered **T3 trigger** ("relationship queries outgrow SQL") for
  re-evaluating the deferred graph-DB option. This proposal and that decision
  should be weighed together — one infrastructure investment could serve both.
- **`tools/metro_outline.py`** (TODO, Step 9) already targets public boundary
  GeoJSON for the map silhouette — same input data as Phase 1; build them
  together.
- **Night Out spec** — the "what's nearby, before/after" feature is distance +
  containment geometry; Phase 1 is its foundation.
- **Descriptor Foundry / matching engine** — both get cleaner when every
  candidate resolves to one canonical entity with provenance.

---

## 9. The decisions this proposal asks the founder to make

1. **Approve Phase 1 (county geometry) as the next build increment?** (Recommended.)
2. **Market scope for launch** — confirmed: CAPCOG's ten counties **+ Gillespie,
   Comal, Kendall, Kerr** (fourteen, done 2026-07-29). Any further Hill Country
   counties, or is geometry now the place to settle the exact boundary?
3. **Draw-to-search (§5)** — approve as a headline consumer feature riding on the
   geometry engine? If yes, it becomes a design-brief item (map UX + trust
   display) for the Phase-1 wave or just after.
4. **Phase 2 timing** — agree the objective trigger "before the first non-Texas
   locale opens"? Or sooner?
5. **Licensing posture** — willing to use ODbL (OpenStreetMap) data, or prefer
   to stay on public-domain/CC0/CC-BY sources only? (Affects how much informal-
   region coverage — and how well draw-to-search can *name* arbitrary areas — we
   get cheaply.)
6. **Graph-DB** — evaluate the graph-brain (1D) option alongside Phase 2, given
   the trigger this work would fire?

---

## 10. What this proposal deliberately does NOT propose

- It does **not** propose a proprietary global ID scheme built from scratch.
- It does **not** propose building the full multi-scale system (neighborhoods,
  streets, police/fire/school districts, isochrones) now — those are real future
  work behind Phase 2's trigger.
- It does **not** relax any trust invariant or gate. Geometry is *more* strict
  than name-matching, and the keep-and-count-unknowns discipline is preserved.
