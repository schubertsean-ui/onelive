# Decision: map tiles = self-hosted PMTiles · nearby-POI dataset = OpenStreetMap (2026-08-04)

**Founder, verbatim:** "PMTiles" (the map-tiles choice) and "Do" (approving the
recommended OpenStreetMap extract for the nearby-POI dataset), given in the same
message against the delivered decision descriptions of 2026-08-04.

## What is decided

1. **Map tiles: self-hosted PMTiles.** A one-time Austin-area map extract (tens of
   MB, PMTiles format) stored with our own assets and rendered client-side by
   MapLibre GL JS (open source). No Mapbox, no per-view fees, no new tile vendor.
   Source pattern: the GeoLibre evaluation's harvest (H-items, decision record
   `2026-08-03_geolibre-draw-to-search-prototype-bench.md` context) — MapLibre +
   PMTiles as the pattern donor, never GeoLibre as a product dependency.
2. **Nearby-POI dataset: OpenStreetMap extract.** Bars/restaurants/clubs for the
   Night Out nearby lens (counts + distance, never ratings — canon §7), from an
   OSM extract under ODbL (attribution + share-alike on the data), stored and
   reshaped in our pipeline like any other auditable dataset. Google Places was
   the alternative: fresher but paid-per-request and its terms restrict long-term
   storage/caching and tie display to Google Maps — incompatible with our
   disk-is-truth/auditability posture and it would have dragged the tile decision
   to Google too.

## What this unlocks (charter 3.1 reading, stated so it can be vetoed)

UI canon §12 gated the nearby-lens map surface on exactly these
spend-or-service decisions. With both decided, the **Night Out nearby lens**
(canon §7: street map, 5-minute-walk ring, sparse POIs, transport guidance;
anti-loathing rules canon) moves from founder-gated to **ratified-unbuilt =
queued agent work** — scheduled after frictionless-nav wave 2, its own
five-field plan recorded at build start, evaluator as always, and the CWV
budget guard applies (map code lazy-loads inside the lens; the feed's LCP
budget is untouchable). Honest bounds: **draw-to-search stays PROPOSAL**
(bench first, separate go/no-go); tile-extract refresh becomes a recurring
chore we own (documented with the build); if hosting the extract ever needs a
NEW storage/CDN service beyond what we already run, that returns as a
founder-crucial ask rather than riding this decision.
