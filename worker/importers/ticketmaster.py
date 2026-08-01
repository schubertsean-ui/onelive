"""Ticketmaster Discovery API client — deterministic licensed-feed fetch.

Stdlib-only (urllib), no AI: fetches CAPCOG-area events from
/discovery/v2/events and yields the raw event dicts for
worker.importers.normalize.normalize_ticketmaster. Pagination respects the
API's deep-paging limit (size*page < 1000) and the rate cap (<=5 req/s).

The API key is read from the environment (TICKETMASTER_API_KEY) or passed in —
NEVER hard-coded or committed. Auth is the Consumer Key as the `apikey` query
parameter (per developer.ticketmaster.com).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import time
import urllib.parse
import urllib.request
from typing import Iterator, Optional

ROOT_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

# CAPCOG center (Austin) + an APPROXIMATE radius over the council-of-governments
# area (Travis, Williamson, Hays, Bastrop, Caldwell, Burnet, Blanco, Lee,
# Fayette, Llano). 75 mi from downtown reaches the outer ring (La Grange, Llano,
# Lampasas); a single circle still misses some outer county area and includes
# some non-CAPCOG area — tracked as R-025 (county/city-scoped queries are the
# precise fix).
CAPCOG_LATLONG = "30.2672,-97.7431"
CAPCOG_RADIUS_MILES = 75

# Western Hill Country center (Kerrville). The market counties added
# 2026-07-29 (Gillespie/Fredericksburg, Kerr/Kerrville, Kendall/Boerne) sit WEST
# of the 75-mi Austin circle, so their venues were PERMITTED by the read-path
# boundary (worker/region/capcog.py) yet never FETCHED. A second acquisition
# center covers them; a 45-mi radius from Kerrville reaches Fredericksburg
# (~24 mi), Boerne (~34 mi) and Kerrville itself. Any out-of-market overflow the
# wider net pulls in is trimmed by the read-path boundary, so widening
# acquisition is trust-safe.
HILL_COUNTRY_WEST_LATLONG = "30.0474,-99.1403"
HILL_COUNTRY_WEST_RADIUS_MILES = 45

# The market's acquisition centers: the CAPCOG core (Austin) + the western Hill
# Country. fetch_events_capcog sweeps EVERY center and de-dupes across them, so a
# show near the seam is fetched once. (R-025's precise fix is still county/city-
# scoped queries; two circles is the pragmatic cover until then.)
MARKET_CENTERS = [
    (CAPCOG_LATLONG, CAPCOG_RADIUS_MILES),
    (HILL_COUNTRY_WEST_LATLONG, HILL_COUNTRY_WEST_RADIUS_MILES),
]


def _get(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_events(
    api_key: Optional[str] = None,
    *,
    extra_params: Optional[dict] = None,
    latlong: str = CAPCOG_LATLONG,
    radius: int = CAPCOG_RADIUS_MILES,
    size: int = 100,
    max_pages: int = 5,
    start: Optional[str] = None,
    end: Optional[str] = None,
    sleep: float = 0.25,
) -> Iterator[dict]:
    """Yield raw Ticketmaster event dicts for the CAPCOG area, page by page.

    api_key falls back to the TICKETMASTER_API_KEY env var when not passed."""
    api_key = api_key or os.environ.get("TICKETMASTER_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "TICKETMASTER_API_KEY is not set — cannot fetch. Set the env var to "
            "your Ticketmaster Consumer Key, or pass api_key explicitly."
        )
    page = 0
    while page < max_pages and size * page < 1000:
        params = {
            "apikey": api_key,
            "latlong": latlong,
            "radius": str(radius),
            "unit": "miles",
            "size": str(size),
            "page": str(page),
            "sort": "date,asc",
        }
        if start:
            params["startDateTime"] = start
        if end:
            params["endDateTime"] = end
        if extra_params:
            params.update(extra_params)
        url = ROOT_URL + "?" + urllib.parse.urlencode(params)
        data = _get(url)
        events = (data.get("_embedded") or {}).get("events") or []
        if not events:
            break
        for ev in events:
            yield ev
        total_pages = (data.get("page") or {}).get("totalPages", 0)
        page += 1
        if page >= total_pages:
            break
        time.sleep(sleep)


def _iso_z(t: _dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_events_capcog(
    api_key: Optional[str] = None,
    *,
    windows: int = 6,
    window_days: int = 30,
    per_window_pages: int = 10,
    centers: "list[tuple[str, int]]" = MARKET_CENTERS,
    size: int = 100,
    sleep: float = 0.2,
    _now: Optional[_dt.datetime] = None,
) -> Iterator[dict]:
    """Comprehensive market fetch — breaks the Discovery API's deep-paging cap.

    A single query truncates at ~1000 results (size*page < 1000), so a busy
    metro's calendar is silently cut off and low-volume categories (comedy,
    family, film) get crowded out by high-volume music. We instead sweep the
    next `windows` rolling ~monthly time windows, deep-page each up to the cap,
    and de-duplicate by event id — pulling the FULL forward calendar across every
    category. `per_window_pages` is clamped to the API's 10-page ceiling.

    We also sweep every acquisition CENTER (default MARKET_CENTERS: the Austin
    core PLUS the western Hill Country), so the added western counties actually
    get fetched. The single `seen` set spans centers AND windows, so a show in
    the overlap between two circles is yielded exactly once.
    """
    api_key = api_key or os.environ.get("TICKETMASTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("TICKETMASTER_API_KEY is not set — cannot fetch.")
    pages = max(1, min(per_window_pages, 10))
    now = _now or _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)
    seen: set[str] = set()
    for latlong, radius in centers:
        for i in range(max(1, windows)):
            start = now + _dt.timedelta(days=i * window_days)
            end = now + _dt.timedelta(days=(i + 1) * window_days)
            for ev in fetch_events(
                api_key,
                latlong=latlong,
                radius=radius,
                size=size,
                max_pages=pages,
                start=_iso_z(start),
                end=_iso_z(end),
                sleep=sleep,
            ):
                eid = ev.get("id")
                if eid is not None:
                    if eid in seen:
                        continue
                    seen.add(eid)
                yield ev


def _summary(argv=None):
    """Live smoke summary (no DB): fetch CAPCOG events, classify into the 22
    domains, log counts + a sample. Proves the real-data path end to end."""
    import logging
    from collections import Counter

    from worker.importers.normalize import normalize_ticketmaster

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger("ticketmaster_smoke")

    key = os.environ.get("TICKETMASTER_API_KEY", "")
    raws = list(fetch_events(key, size=100, max_pages=4))
    norm = [n for n in (normalize_ticketmaster(e) for e in raws) if n]
    if not norm:
        log.error("smoke fetched %d, normalized 0 — bad key / query / drift. Failing loud.", len(raws))
        return 3
    by_domain = Counter(n["category"] for n in norm)
    log.info("REAL Ticketmaster events fetched (CAPCOG area): %d", len(raws))
    log.info("Normalized OK: %d", len(norm))
    log.info("By cultural domain:")
    for dom, c in by_domain.most_common():
        log.info("  %-18s %d", dom, c)
    log.info("Sample (first 12):")
    for n in norm[:12]:
        price = "Free" if n["is_free"] else (
            f"${n['price_min']:.0f}-${n['price_max']:.0f}" if n["price_min"] is not None else "—")
        when = (n["start_time"] or "")[:16].replace("T", " ")
        log.info("  · %-42s | %-14s | %-22s | %s | %s",
                 n["title"][:42], n["category"], (n["venue_name"] or "")[:22], when, price)
    return 0


if __name__ == "__main__":
    raise SystemExit(_summary())
