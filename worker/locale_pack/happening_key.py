"""Happening identity key.

FL-010 / FL-013: clock and Place are fields, not the key.
Same listing URL is one happening.
Same title + same local date is one happening when no listing URL exists.
Filling Place or rewriting timezone must not mint a second card.
"""
from __future__ import annotations

from typing import Optional

from worker.locale_pack.desk_union import UnionRow


def _listing_url(row: UnionRow) -> Optional[str]:
    for member in row.members:
        url = getattr(member.row, "listing_url", None)
        if url:
            return str(url).strip() or None
    return None


def _local_date(row: UnionRow) -> str:
    """YYYY-MM-DD only. Never the minute. Never a timezone offset."""
    night = (getattr(row, "night", None) or "").strip()
    if len(night) >= 10 and night[4] == "-":
        return night[:10]
    for member in row.members:
        when = (getattr(member.row, "when", None) or "").strip()
        if len(when) >= 10 and when[4] == "-":
            return when[:10]
    return ""


def identity_key(row: UnionRow) -> str:
    """The handle a re-run finds this row by.

    1. listing URL if the desk printed one.
    2. else title + local date.
    Place and clock-minute stay out of the key.
    """
    url = _listing_url(row)
    if url:
        return f"url:{url}"
    local_date = _local_date(row)
    member = row.members[0]
    title_key = (getattr(member, "title_key", None) or "").strip()
    if title_key and local_date:
        return f"title:{title_key}~{local_date}"
    if title_key:
        return f"title:{title_key}"
    place = (getattr(member, "place", None) or "").strip()
    return f"title:{place}~{title_key}"
