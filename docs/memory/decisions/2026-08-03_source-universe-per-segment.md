# Decision — Source universe is per-segment × per-market, with a growth ladder

One-line: founder-directed — every segment (the ~23 identified cultural domains)
must have its OWN source universe: dozens → hundreds → thousands → tens of
thousands → eventually millions of potential sources as markets multiply; local
sources must outnumber Ticketmaster 50:1–100:1 per locale. A hand-curated flat
catalog can never reach this; source DISCOVERY is an engine, per segment.

**Date:** 2026-08-03. **Authority:** founder-directed, verbatim: *"Every
segment - the 23 currently identified - should have dozens and hundreds and
thousands and tens of thousands and eventually millions of potential sources"*
and *"Local venues, events, artists, groups, etc. should outnumber Ticketmaster
50:1 or 100:1 or more depending upon the locale."* Context: the 2026-08-03
ingestion audit found Ticketmaster carrying ~94% of the feed (~15:1 the WRONG
way) from a 180-source hand-curated catalog.

## What this ratifies

1. **The coverage north-star KPI: long-tail dominance ratio** — distinct
   local (non-licensed-API) venues and events vs Ticketmaster's, per market,
   per week. Target ≥50:1. A market is not "complete" until it holds. Reported
   in the committed coverage snapshot (see the sourcing scale plan).
2. **The universe model: segment × market matrix.** Each segment has its own
   taxonomy of source TYPES and its own seed registries (e.g. literary:
   bookstores, presses, library systems, reading series, MFA programs;
   visual-arts: galleries, museums, art schools, studio tours; heritage:
   historical societies, preservation orgs; ideas: universities, civic forums).
   Discovery enumerates each cell, never just "venues."
3. **Discovery is an engine, not curation.** Place/registry spines → website
   resolution → calendar-surface probing → pathway classification → scored
   auto-enrollment with provenance; humans review edge cases only. The
   per-segment registries are part of each market file's world (sourcing model
   Layer 2) and the segment taxonomies are global reuse (Layer 1-adjacent
   data, defined once).
4. **Scale posture:** catalog and `source` table must be designed for
   millions of rows (indexes, per-market/per-segment partitioning of sweeps,
   rotation fairness so a giant catalog never starves a segment).

## What it does NOT change

Trust invariants and gates are unchanged: more sources widen ACQUISITION;
every candidate still passes the same corroboration gate → promote path.
Discovery-enrolled sources start at conservative reliability and EARN weight
(source_reliability), exactly like hand-curated ones.
