# Decision — Sourcing model: three layers (pathways / markets / specials)

One-line: founder-directed — the sourcing model is structured for maximum reuse
with planned special situations: Layer 1 pathway adapters keyed by PROTOCOL
(global reuse, `tools/source_pathways.py` taxonomy), Layer 2 MARKETS as
fail-closed data files (`sources/markets/*.json` + `worker/sourcing/markets.py`;
Austin = market #1), Layer 3 SPECIALS declared per market (SXSW corroboration,
Hill Country boundary) pointing at their implementing code — scale = add files,
never fork pipeline code.

**Date:** 2026-08-03. **Authority:** founder-directed, verbatim: *"Your
sourcing model should be reusable and structured as a world class engineer
would to be able to reuse as much as possible while also planning for unique
special situations for local regional global items."* Context: same session as
the ingestion-truth audit (one vendor carrying ~94% of the feed) and the
founder's "this will need to scale nationally and then globally."

## What was built

- `docs/strategy/SOURCING_MODEL_v1.md` — the canon (three layers, rules,
  alternatives rejected, honest status).
- `worker/sourcing/markets.py` — fail-closed market registry: unknown id /
  malformed file / bad timezone / missing catalog / unresolvable-or-empty
  boundary all refuse loudly; boundary is a module+symbol REFERENCE resolved
  by import (mechanical identity with `worker/region/capcog.py`, never a
  mirrored list).
- `sources/markets/austin.json` — market #1 with three declared specials.
- `tools/import_sources.py --market` — catalog seeding routes through the
  registry (the market file is the authority, not a hand-typed path).

## The transferable rules

1. New source ≠ new importer; only a new PROTOCOL earns a new adapter, and its
   classifier entry lands in the same PR.
2. New city/country = new market FILE (+ boundary resolver kind only if the
   geography needs one). Pipeline code untouched.
3. A special implemented but undeclared is a silent fork (defect); declared
   but unbuilt is visible `planned` debt.
4. Boundary/market resolution is fail-closed — never default to "everywhere."
