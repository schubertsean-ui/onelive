"""Pure, deterministic normalization of licensed-feed event payloads into the
`licensed_event` canonical shape. NO network, NO DB, NO AI — just field mapping,
so it is fully unit-testable against captured fixtures.

Each `normalize_*` returns a dict whose keys are exactly the writable
`licensed_event` columns (see supabase/migrations/0010), or None when the
payload lacks the irreducible minimum (a stable id and a title) — we never
invent data to fill a gap.
"""
from __future__ import annotations

from typing import Any, Optional

from worker.importers.domain_map import seatgeek_domain, ticketmaster_domain


def _f(x: Any) -> Optional[float]:
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


def _first(seq: Any) -> Any:
    return seq[0] if isinstance(seq, list) and seq else None


def _utc_iso(s: Any) -> Optional[str]:
    """Make a UTC timestamp string unambiguous for a timestamptz column: append
    'Z' when the value carries no timezone designator. SeatGeek's datetime_utc
    is UTC but formatted naive (no offset), so without this it would be
    interpreted in the DB/session timezone."""
    if not isinstance(s, str) or not s:
        return s if s else None
    if s.endswith("Z") or "+" in s[10:] or s[10:].count("-") > 0:
        return s
    return s + "Z"


def _best_image(images: Any) -> Optional[str]:
    """Pick the widest 16:9 image; fall back to the widest of any ratio."""
    if not isinstance(images, list) or not images:
        return None
    wide = [i for i in images if isinstance(i, dict) and i.get("ratio") == "16_9"]
    pool = wide or [i for i in images if isinstance(i, dict) and i.get("url")]
    if not pool:
        return None
    best = max(pool, key=lambda i: i.get("width") or 0)
    return best.get("url")


# ---- Ticketmaster ------------------------------------------------------------

_TM_STATUS = {
    "onsale": ("onsale", "scheduled"),
    "offsale": ("offsale", "scheduled"),
    "canceled": ("cancelled", "cancelled"),
    "cancelled": ("cancelled", "cancelled"),
    "postponed": ("postponed", "moved"),
    "rescheduled": ("rescheduled", "moved"),
}


def normalize_ticketmaster(ev: dict) -> Optional[dict]:
    ext = ev.get("id")
    title = ev.get("name")
    if not ext or not title:
        return None

    # Prefer the classification Ticketmaster marks primary; else the first.
    classifications = ev.get("classifications") or []
    cls = next(
        (c for c in classifications if isinstance(c, dict) and c.get("primary")),
        _first(classifications),
    ) or {}
    seg = (cls.get("segment") or {}).get("name")
    gen = (cls.get("genre") or {}).get("name")
    sub = (cls.get("subGenre") or {}).get("name")
    category, subsegment = ticketmaster_domain(seg, gen, sub)

    dates = ev.get("dates") or {}
    start = (dates.get("start") or {})
    start_time = start.get("dateTime")  # ISO 8601 UTC when present
    status_code = ((dates.get("status") or {}).get("code") or "").lower()
    on_sale_status, status = _TM_STATUS.get(status_code, (status_code or None, "scheduled"))

    prices = ev.get("priceRanges") or []
    mins = [v for v in (_f(p.get("min")) for p in prices) if v is not None]
    maxs = [v for v in (_f(p.get("max")) for p in prices) if v is not None]
    price_min = min(mins) if mins else None
    price_max = max(maxs) if maxs else None
    currency = (_first(prices) or {}).get("currency") if prices else None
    is_free = (price_min == 0) if price_min is not None else None

    emb = ev.get("_embedded") or {}
    venue = _first(emb.get("venues")) or {}
    loc = venue.get("location") or {}
    attractions = emb.get("attractions") or []
    performer = ", ".join(a.get("name") for a in attractions if a.get("name")) or None

    return {
        "source_provider": "ticketmaster",
        "external_id": str(ext),
        "title": title,
        "category": category,
        "subsegment": subsegment,
        "performer": performer,
        "start_time": start_time,
        "end_time": None,
        "status": status,
        "on_sale_status": on_sale_status,
        "price_min": price_min,
        "price_max": price_max,
        "currency": currency,
        "is_free": is_free,
        "ticket_url": ev.get("url"),
        "image_url": _best_image(ev.get("images")),
        "venue_name": venue.get("name"),
        "venue_city": (venue.get("city") or {}).get("name"),
        "venue_area": None,  # neighborhood derived later from geo; not asserted here
        "venue_address": (venue.get("address") or {}).get("line1"),
        "venue_lat": _f(loc.get("latitude")),
        "venue_lng": _f(loc.get("longitude")),
        "confidence": "confirmed",
        "raw": ev,
    }


# ---- SeatGeek ----------------------------------------------------------------

def normalize_seatgeek(ev: dict) -> Optional[dict]:
    ext = ev.get("id")
    title = ev.get("title") or ev.get("short_title")
    if ext is None or not title:
        return None

    performers = ev.get("performers") or []
    primary = next((p for p in performers if p.get("primary")), _first(performers)) or {}
    genres = [g.get("name") for g in (primary.get("genres") or []) if g.get("name")]
    category, subsegment = seatgeek_domain(ev.get("type"), genres)
    performer = ", ".join(p.get("name") for p in performers if p.get("name")) or None

    stats = ev.get("stats") or {}
    price_min = _f(stats.get("lowest_price"))
    price_max = _f(stats.get("highest_price"))

    venue = ev.get("venue") or {}
    loc = venue.get("location") or {}

    return {
        "source_provider": "seatgeek",
        "external_id": str(ext),
        "title": title,
        "category": category,
        "subsegment": subsegment,
        "performer": performer,
        "start_time": _utc_iso(ev.get("datetime_utc")),  # SeatGeek gives naive-UTC ISO → make Z-explicit
        "end_time": None,
        "status": "scheduled",
        "on_sale_status": None,
        "price_min": price_min,
        "price_max": price_max,
        "currency": "USD" if (price_min is not None or price_max is not None) else None,
        "is_free": (price_min == 0) if price_min is not None else None,
        "ticket_url": ev.get("url"),
        "image_url": (primary.get("image") if isinstance(primary.get("image"), str) else None),
        "venue_name": venue.get("name"),
        "venue_city": venue.get("city"),
        "venue_area": None,
        "venue_address": venue.get("address"),
        "venue_lat": _f(loc.get("lat")),
        "venue_lng": _f(loc.get("lon")),
        "confidence": "confirmed",
        "raw": ev,
    }
