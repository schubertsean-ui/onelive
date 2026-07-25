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

from worker.importers.domain_map import (
    UNMAPPED,
    eventbrite_domain,
    seatgeek_domain,
    ticketmaster_domain,
    ticketmaster_fallback_domain,
)


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

    # When the provider left it Undefined, recover a domain from REAL provider
    # data: the performer's own classification, then keyword inference from the
    # literal event name (deterministic, never fabricated). This is what shrinks
    # the "Other" bucket without guessing.
    if category == UNMAPPED:
        attractions = ((ev.get("_embedded") or {}).get("attractions")) or []
        attr_cls = []
        for a in attractions:
            for c in (a.get("classifications") or []):
                if isinstance(c, dict):
                    attr_cls.append((
                        (c.get("segment") or {}).get("name"),
                        (c.get("genre") or {}).get("name"),
                        (c.get("subGenre") or {}).get("name"),
                    ))
        category, subsegment = ticketmaster_fallback_domain(title, attr_cls)

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


# ---- Eventbrite --------------------------------------------------------------

# Eventbrite event status → (event status, on_sale_status). Only the ticketing
# states that map to our closed vocabulary (scheduled|cancelled|moved) are
# translated; anything else stays 'scheduled' (the runner polls status=live).
_EB_STATUS = {
    "live": ("scheduled", "onsale"),
    "started": ("scheduled", "onsale"),
    "ended": ("scheduled", "offsale"),
    "completed": ("scheduled", "offsale"),
    "canceled": ("cancelled", "cancelled"),
    "cancelled": ("cancelled", "cancelled"),
    "postponed": ("moved", "postponed"),
}


def normalize_eventbrite(ev: dict) -> Optional[dict]:
    """Map an Eventbrite v3 event (expand=venue,ticket_availability,category,
    subcategory) into the licensed_event column shape. None when the irreducible
    minimum (a stable id and a title) is missing — never invents data.

    Public event SEARCH was removed by Eventbrite in 2020; the fetch client polls
    KNOWN organizers/venues, but the per-event shape mapped here is identical.
    """
    ext = ev.get("id")
    # Eventbrite wraps text fields as {"text": ..., "html": ...}.
    name = ev.get("name") or {}
    title = name.get("text") if isinstance(name, dict) else name
    if ext is None or not title:
        return None

    category = (ev.get("category") or {}).get("name")
    subcategory = (ev.get("subcategory") or {}).get("name")
    domain, subsegment = eventbrite_domain(category, subcategory)

    start = ev.get("start") or {}
    end = ev.get("end") or {}
    # Eventbrite's start.utc/end.utc are ISO-8601 with a trailing 'Z' already;
    # _utc_iso is a no-op safety net if a naive value ever appears.
    start_time = _utc_iso(start.get("utc")) if isinstance(start, dict) else None
    end_time = _utc_iso(end.get("utc")) if isinstance(end, dict) else None

    status_code = (ev.get("status") or "").lower()
    status, on_sale_status = _EB_STATUS.get(status_code, ("scheduled", None))

    # ticket_availability carries the price envelope. is_free is authoritative
    # from the provider; only infer it from a $0 minimum when the flag is absent.
    ta = ev.get("ticket_availability") or {}
    tmin = ta.get("minimum_ticket_price") or {}
    tmax = ta.get("maximum_ticket_price") or {}
    price_min = _f(tmin.get("major_value"))
    price_max = _f(tmax.get("major_value"))
    currency = tmin.get("currency") or tmax.get("currency")
    is_free = ev.get("is_free")
    if is_free is None and price_min is not None:
        is_free = price_min == 0

    venue = ev.get("venue") or {}
    addr = venue.get("address") or {}

    return {
        "source_provider": "eventbrite",
        "external_id": str(ext),
        "title": title,
        "category": domain,
        "subsegment": subsegment,
        "performer": None,  # Eventbrite events have no performer taxonomy
        "start_time": start_time,
        "end_time": end_time,
        "status": status,
        "on_sale_status": on_sale_status,
        "price_min": price_min,
        "price_max": price_max,
        "currency": currency,
        "is_free": is_free,
        "ticket_url": ev.get("url"),
        "image_url": (ev.get("logo") or {}).get("url"),
        "venue_name": venue.get("name"),
        "venue_city": addr.get("city"),
        "venue_area": None,  # neighborhood derived later from geo; not asserted here
        "venue_address": addr.get("localized_address_display"),
        "venue_lat": _f(addr.get("latitude")),
        "venue_lng": _f(addr.get("longitude")),
        "confidence": "confirmed",
        "raw": ev,
    }
