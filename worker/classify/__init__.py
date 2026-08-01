"""Category/genre classification for OneLive events.

The Router pattern from the graph-engineering playbook (Anthropic workflow
patterns, Table I: "Routing — classifier input — entity/degree route queries"):
a dedicated classifier that assigns a cultural DOMAIN (+ best-effort genre) to an
event from the STRONGEST available real signal, each carrying provenance — never
a guess from the title alone. See docs/memory/decisions/2026-07-25_graph-
engineering-adoption.md for why this replaced the title-only fallback.
"""
from worker.classify.category_resolver import (
    CategoryResult,
    resolve_category,
)

__all__ = ["CategoryResult", "resolve_category"]
