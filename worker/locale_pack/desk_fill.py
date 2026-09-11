"""FL-010 — a first printed field on a public row is a fill, not corroboration.

Read docs/ONE-LIVE-FIX-LOOP.md and docs/fix-library/FL-010.md before changing this.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

FILLABLE = ("place", "clocks", "night", "title", "listing_url")
FAKE_PLACE = frozenset({
    "unknown venue", "venue", "unknown", "tbd", "n/a", "na",
    "place to be confirmed",
})


def venue_label(place: Optional[str]) -> str:
    """The Place name the card should print. Street after the first comma is not the name."""
    raw = (place or "").strip()
    if not raw:
        return ""
    return raw.split(",", 1)[0].strip()


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
        patch["venue_name"] = venue_label(str(fresh["place"])) or str(fresh["place"]).strip()
    if "clocks" in fields:
        clocks = fresh.get("clocks") or []
        if clocks:
            patch["start_time"] = clocks[0]
    if "title" in fields and fresh.get("title"):
        patch["title"] = fresh["title"]
    return patch


def sibling_event_id(fresh: Mapping[str, Any],
                     seen: Mapping[str, tuple]) -> Optional[str]:
    """Public event for this listing when the Place-in-key identity is new."""
    url = (fresh.get("listing_url") or "").strip()
    title = (fresh.get("title") or "").strip().lower()
    night = (fresh.get("night") or "").strip()
    for _key, tup in seen.items():
        if not isinstance(tup, (tuple, list)) or len(tup) < 3:
            continue
        event_id = tup[2]
        stored = tup[3] if len(tup) > 3 else None
        if not event_id or not isinstance(stored, dict):
            continue
        stored_url = (stored.get("listing_url") or "").strip()
        stored_title = (stored.get("title") or "").strip().lower()
        stored_night = (stored.get("night") or "").strip()
        if url and stored_url and url == stored_url:
            if not night or not stored_night or night == stored_night:
                return str(event_id)
        if title and stored_title == title and night and stored_night == night:
            return str(event_id)
    return None
