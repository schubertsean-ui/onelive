"""Sourcing model — the three-layer, reuse-first architecture for ingestion.

Layer 1 (global): PATHWAY adapters keyed by machine protocol, one adapter per
kind, reusable in every market (tools/source_pathways.py taxonomy; adapters in
worker/importers/ + the AI loop).
Layer 2 (local): MARKETS as data files (sources/markets/<id>.json) — boundary,
timezone, locale, catalog. Adding a market adds a file, never a fork.
Layer 3 (special): declared per-market SPECIALS (festival corroboration modes,
boundary extensions) pointing at the code that implements them.

Canon: docs/strategy/SOURCING_MODEL_v1.md.
"""
from worker.sourcing.markets import (  # noqa: F401
    Market,
    MarketConfigError,
    SpecialSituation,
    available_markets,
    get_market,
)
