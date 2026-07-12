# OneLive — Stealth Launch Plan (world-class bar, autonomous build)

**Owner:** Sean Schubert. **Directive (2026-07-11):** drive to a world-class
live stealth site autonomously and fast; return only with final go-live
decisions the founder must make. Quality bar = docs/OPERATING_RULES.md §1
(world-class across EVERY aspect; test-as-you-go).

This is the durable checklist. It survives context compaction. Each gate ends in
a verified state (full pytest + trust_gate green) and a commit on the branch.

## Gates (in dependency order)

1. **Eval loop (Layer 4)** — adversarial corpus + runner + over-suppression
   tracking, on the hardened scorer. Exit: corpus loads, gate/sensor cases pass
   with ai=None, over_suppression surfaced, sabotage test proves it can fail.

2. **Source schema: geo/coverage dimension** — migration adding `county`,
   `sub_region`, `coverage_categories` to `source`; the reason 43 sources was
   "coverage theater" is there was no way to measure geographic/category
   blindness. Exit: migration + model + tests green.

3. **Real source catalog (250–400+)** — 5-county Austin metro (Travis,
   Williamson, Hays, Bastrop, Caldwell) × categories (music venues, theaters/
   arts, galleries/museums, food/culinary, universities, city/county calendars,
   local media, community/cultural orgs). VERIFIED real URLs via browser
   research — NEVER model-invented sources (that would poison the catalog and
   violate the Class-D trust discipline). Scored + imported idempotently.
   Exit: source table holds the catalog, geotagged, category-balanced.

4. **Coverage report** — `tools/coverage_report.py`: county × category matrix so
   "are we blind anywhere?" is a query. Exit: report runs, shows the grid.

5. **Pipeline on real data** — run orchestrator `--real` end-to-end; confirm
   candidates promote through the 3-way gate; measure hallucination_rate on real
   extractions. Exit: ≥1 confirmed event lands from real sources; metrics
   recorded. THE biggest unknown — de-risks the whole launch.

6. **Public feed UI** — `/tonight` + event feed, world-class UX: loading/empty/
   error states, accessibility, copy, and trust display (confidence states:
   confirmed/likely/unverified/disputed all render honestly). Exit: renders real
   promoted events from the API.

7. **Deploy + stealth gate** — wire public API to Supabase in prod; deploy web
   app; invite/password wall for stealth. Exit: a real URL reachable behind the
   gate.

8. **World-class QA on live data** — security, performance, failure semantics,
   observability; final trust review across all aspects. Exit: no unnamed
   weakness; every aspect graded honestly.

9. **Founder finalize** — return with the live URL + the decisions only the
   founder can make (domain, invite list, stealth copy, launch timing, any
   category/geo scope calls). Do NOT bounce answerable questions back.

## Discipline
- Sunset Law before adding guards; sabotage-validate every guard.
- Findings are claims until verified against ground truth.
- Checkpoint arc + STATE.md before compaction; update this file as gates close.
