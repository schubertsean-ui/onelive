"""Publish desk union rows. Ticket A: title exists. Date/place holes do not hold."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from worker.locale_pack.desk_union import BASIS_LOCAL, DeskUnion, UnionRow
from worker.locale_pack.pack import Door
from worker.locale_pack.existence import hold_reason as existence_hold

DESK_KEY = "_desk"
LIVE = "LIVE"


class DeskPublishError(ValueError):
    """The write cannot be planned."""


@dataclass(frozen=True)
class DeskRegistration:
    door_id: str
    via: str
    source_name: str


def write_for(union: DeskUnion, *, mode: str = LIVE, doors: Optional[Sequence[Door]] = None) -> List[Any]:
    """Plan catalog writes. Existence = title (or listing URL). Date/place cannot hold."""
    if mode != LIVE:
        raise DeskPublishError(f"mode must be LIVE, got {mode!r}")
    writes = []
    for row in union.rows:
        title = (row.title or "").strip()
        listing_url = None
        for m in row.members:
            u = getattr(m.row, "listing_url", None) or getattr(m.row, "url", None)
            if u:
                listing_url = u
                break
        hr = existence_hold(
            door_readable=True,
            title=title,
            listing_url=listing_url,
            is_fixture=False,
        )
        if hr:
            continue
        # publish with holes allowed
        start_time = None
        clocks = []
        for m in row.members:
            t = getattr(m.row, "start_time", None) or getattr(m.row, "when_time", None)
            if t and t not in clocks:
                clocks.append(t)
        if len(clocks) == 1:
            start_time = clocks[0]
        # never invent T17:00 from date-only
        writes.append({
            "title": title,
            "start_date": getattr(row, "night", None) or getattr(row, "when", None),
            "start_time": start_time,
            "venue_name": getattr(row, "place_text", None),
            "hold_reason": None,
            "via": list(getattr(row, "vias", []) or []),
        })
    return writes
