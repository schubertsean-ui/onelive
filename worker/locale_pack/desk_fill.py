"""FL-010 — a first printed field on a public row is a fill, not corroboration.

Read docs/ONE-LIVE-FIX-LOOP.md and docs/fix-library/FL-010.md before changing this.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

FILLABLE = ("place", "clocks", "night", "title", "listing_url")


def fills(stored: Optional[Mapping[str, Any]],
          fresh: Mapping[str, Any]) -> List[str]:
    """Fields the desk now prints that the published statement left empty."""
    if not stored:
        return []
    out: List[str] = []
    for field in FILLABLE:
        if not stored.get(field) and fresh.get(field):
            out.append(field)
    return out


def fill_patch(fresh: Mapping[str, Any], fields: List[str]) -> Dict[str, Any]:
    """The values to write onto the published row. Never invent."""
    patch: Dict[str, Any] = {}
    if "place" in fields and fresh.get("place"):
        patch["venue_name"] = fresh["place"]
    if "clocks" in fields:
        clocks = fresh.get("clocks") or []
        if clocks:
            patch["start_time"] = clocks[0]
    if "title" in fields and fresh.get("title"):
        patch["title"] = fresh["title"]
    return patch
