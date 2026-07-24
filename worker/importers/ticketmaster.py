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

import json
import os
import time
import urllib.parse
import urllib.request
from typing import Iterator, Optional

ROOT_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

# CAPCOG center (Austin) + a radius covering the council-of-governments area
# (Travis, Williamson, Hays, Bastrop, Caldwell, Burnet, Blanco, Lee, Fayette,
# Llano). ~60 mi from downtown reaches the ring cities.
CAPCOG_LATLONG = "30.2672,-97.7431"
CAPCOG_RADIUS_MILES = 60


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
