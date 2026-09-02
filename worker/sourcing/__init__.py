"""Sourcing model — the three-layer, reuse-first architecture for ingestion.

Layer 1 (global): PATHWAY adapters keyed by machine protocol, one adapter per
kind, reusable in every market (tools/source_pathways.py taxonomy; adapters in
worker/importers/ + the AI loop).
Layer 2 (local): MARKETS as data files (sources/markets/<id>.json) — boundary,
timezone, locale, catalog. Adding a market adds a file, never a fork.
Layer 3 (special): declared per-market SPECIALS (festival corroboration modes,
boundary extensions) pointing at the code that implements them.

Canon: docs/strategy/SOURCING_MODEL_v1.md.

DELIBERATELY EMPTY of imports (2026-09-02). This package init used to re-export
the Layer 2 market registry (`from worker.sourcing.markets import ...`), which
NOTHING imported through this module — every caller already names the submodule
(`from worker.sourcing.markets import get_market`). Since the armed ingestion
cron now imports worker.sourcing.page_discovery, Python executes THIS file on
the way in, so the re-export dragged worker/sourcing/markets.py — and its
deliberate `importlib.import_module` for pluggable boundary modules — into the
cron's import closure, where tools/arming_runtime.py must refuse a dynamic
import it cannot statically prove complete (fail closed, by design). Removing
an unused convenience import keeps the closure provable WITHOUT relaxing that
refusal. Import the submodules directly; do not re-add eager re-exports here.
"""
