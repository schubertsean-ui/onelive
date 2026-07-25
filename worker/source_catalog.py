"""Source catalog lookup — map a candidate's originating source to the curated
`cultural_domain` a human recorded for it in sources/master_sources_catalog_120.json.

Why this exists (founder, 2026-07-25, taken literally): the category of an event
is NOT a guess from its title — you can READ what the source IS. A source we
curated as `live-music` (a concert hall's calendar) produces live-music events; a
source curated `visual-arts` (a museum) produces visual-arts events. The catalog
already carries that human-vetted `cultural_domain` per source; this module is the
join that finally FEEDS it to the promote-time classifier (worker.classify.
resolve_category's `venue_domain_hint`, its signal #3 — above the title-keyword
last resort). Before this, promote passed no signal at all, so every promoted
long-tail event fell to the title read regardless of how well we knew the source.

NON-FABRICATING, by construction:
  * only a `cultural_domain` that is a REAL OneLive domain id (in domain_map.DOMAINS)
    is ever returned — a typo'd or unknown value yields None, not a bad category;
  * a source with no `cultural_domain`, or a source not in the catalog at all
    (e.g. a test stub), yields None — the classifier then falls through to its
    own signals honestly;
  * the match is an EXACT (case-insensitive, stripped) name match — no fuzzy
    guessing that could attach one source's domain to another.
The hint is optional enrichment: if the catalog file cannot be read, this logs a
warning and returns None for every lookup (promote degrades to the title read,
never crashes and never invents a domain).

Pure/deterministic and file-only (no network, no DB), so it is unit-testable.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Dict, Optional

from worker.importers.domain_map import DOMAINS

logger = logging.getLogger(__name__)

_CATALOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "sources",
    "master_sources_catalog_120.json",
)

_VALID_DOMAINS = frozenset(DOMAINS)

# Lazily built {normalized source name -> valid cultural_domain id}. None until
# first load; a dict (possibly empty) after, so a failed load is not retried on
# every promote (and stays fail-safe, returning None for all lookups).
_NAME_TO_DOMAIN: Optional[Dict[str, str]] = None


def _norm(name: Optional[str]) -> str:
    return (name or "").strip().lower()


def _build_map(path: Optional[str] = None) -> Dict[str, str]:
    """Read the catalog and index name -> cultural_domain for the rows that
    carry a VALID domain id. Invalid/missing domains and nameless rows are
    skipped (never indexed), so a lookup can only ever return a real domain.

    The path is resolved from the module global at CALL time (not bound as a
    default) so tests can repoint _CATALOG_PATH and the fail-safe path is real."""
    if path is None:
        path = _CATALOG_PATH
    with open(path, "r", encoding="utf-8") as f:
        rows = json.load(f)
    if not isinstance(rows, list):
        rows = rows.get("sources", []) if isinstance(rows, dict) else []
    mapping: Dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = _norm(row.get("name"))
        domain = row.get("cultural_domain")
        if name and domain in _VALID_DOMAINS:
            # First writer wins; a duplicate name (shouldn't happen — ids/ranks
            # are unique) keeps the earlier row rather than silently overwriting.
            mapping.setdefault(name, domain)
    return mapping


def _get_map() -> Dict[str, str]:
    global _NAME_TO_DOMAIN
    if _NAME_TO_DOMAIN is None:
        try:
            _NAME_TO_DOMAIN = _build_map()
        except (OSError, ValueError) as exc:
            # Fail SAFE, not silent: log loudly, then treat the catalog as
            # empty so every lookup returns None (title-keyword fallback) —
            # a missing enrichment file must never crash promote or fabricate.
            logger.warning(
                "source_catalog: could not load %s (%s: %s) — cultural_domain "
                "hints disabled this process; category falls back to the title "
                "read. This is a fail-safe degrade, not a silent drop.",
                _CATALOG_PATH, type(exc).__name__, exc,
            )
            _NAME_TO_DOMAIN = {}
    return _NAME_TO_DOMAIN


def cultural_domain_for_source(source_name: Optional[str]) -> Optional[str]:
    """Return the curated OneLive cultural-domain id for the named source, or
    None when the source is unknown, has no curated domain, or the domain is
    not a real id. Never raises; never returns a non-domain string."""
    if not source_name:
        return None
    return _get_map().get(_norm(source_name))
