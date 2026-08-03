GeoLibre (opengeos, MIT) is the RATIFIED standing UX prototyping bench for the draw-to-search surface — a step of the UI/UX design formality; the feature itself stays PROPOSAL/founder-gated.

# 2026-08-03 — GeoLibre = the draw-to-search UX prototype bench (UI/UX design formality)

**Status:** RATIFIED. **Decider:** founder.
**Trigger (verbatim):** *"This should be ratified - if not I ratify it - make it
part of the UI/UX design formality"* — applied to this line of the session's
GeoLibre evaluation: *"As a prototyping bench for draw-to-search (DuckDB-WASM
spatial + draw tools), if that proposal is ever ratified — cheap way to feel the
UX before building it natively."*

## What is ratified

A **design-process step**, now part of the UI/UX design formality (UI canon §7
and §12): [GeoLibre](https://github.com/opengeos/GeoLibre) — open-source (MIT),
in-browser GIS with draw tools and DuckDB-WASM spatial — is the standing
**prototyping bench** for the draw-to-search surface (finger-drawn loop →
point-in-polygon → the events inside; Geo-Identity spec §5).

Mechanics of a bench run: export real event points (GeoJSON from
`licensed_event` ∪ promoted events) → load into GeoLibre in the browser →
draw loops of block/neighborhood/region size → feel the query-inside-a-loop
UX and iterate → log findings into the design canon as ordinary design input.
Cost: $0, no account, no server — data stays local. The bench may run
**before** the founder's gate decision to inform it, not only after.

## What is NOT ratified (scope fences)

1. **Draw-to-search itself remains PROPOSAL, founder-gated** (UI canon §12).
   The bench is how we design it, not permission to build it.
2. **No product dependency on GeoLibre** — it never enters the render path or
   the repo's dependency set. The same session's critical evaluation stands:
   scope mismatch, CWV budget (LCP ≤ 2.5s vs DuckDB-WASM/deck.gl weight),
   canon control of the venue-block UI, and release churn (v2.0→v2.4 in 18
   days, no semver policy) rule it out as a dependency. Native build target
   remains MapLibre-class tooling under the founder-gated tile decision.
3. **Bench findings are design inputs, never gate evidence.** Using a bench
   result to argue any gate or threshold down is a gate-threshold relaxation:
   founder-crucial.
4. **No spend, no new service, no credentials.**

## Why GeoLibre and not the alternatives

kepler.gl has no draw-then-query flow; QGIS is install-heavy desktop and
nothing like the touch UX; a throwaway native prototype is exactly the cost
this avoids. GeoLibre is the only zero-install tool with the loop-draw +
in-browser spatial-SQL combination that approximates the surface.

**Tradeoff, honestly:** the bench's gestures and styling will not match the
eventual native implementation — findings are directional UX learning
(loop sizes, result framing, naming-by-scale), never visual canon.

## Provenance

From this session's critical evaluation of GeoLibre (with the po battery per
`docs/skills/po_provocation.md`); the bench was the evaluation's "where it
genuinely fits" item. Related: R-073 (renumbered from R-068; the canon's `ONE_LIVE_GEO_IDENTITY_v1.md`
§5 citation resolves to no committed file — land the spec or fix the citation
before the first bench run / gate decision).
