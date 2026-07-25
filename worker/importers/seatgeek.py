"""SeatGeek Platform API client — deterministic licensed-feed fetch.

Stdlib-only (urllib), no AI: fetches CAPCOG-area events from
https://api.seatgeek.com/2/events and yields the raw event dicts for
worker.importers.normalize.normalize_seatgeek. Pagination uses SeatGeek's
1-indexed `page` + `per_page` and stops once meta.total is exhausted; the rate
cap is respected with a polite sleep between requests.

The API credential is read from the environment (SEATGEEK_CLIENT_ID) or passed
in — NEVER hard-coded or committed. Auth is the client_id (and optional
client_secret) query parameter, per platform.seatgeek.com. This module mirrors
worker.importers.ticketmaster field-for-field so the two licensed feeds behave
identically (same CAPCOG center, same window-sweep to break any deep-paging cap,
same de-dupe-by-id, same fail-loud-on-missing-key discipline).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import time
import urllib.parse
import urllib.request
from typing import Iterator, Optional

ROOT_URL = "https://api.seatgeek.com/2/events"

# CAPCOG center (Austin) + an APPROXIMATE radius over the council-of-governments
# area (Travis, Williamson, Hays, Bastrop, Caldwell, Burnet, Blanco, Lee,
# Fayette, Llano). 75 mi from downtown reaches the outer ring (La Grange, Llano,
# Lampasas); a single circle still misses some outer county area and includes
# some non-CAPCOG area — tracked as R-025 (county/city-scoped queries are the
# precise fix). SeatGeek takes lat/lon/range rather than Ticketmaster's
# latlong/radius, but the geographic scope is IDENTICAL to the TM importer.
CAPCOG_LAT = 30.2672
CAPCOG_LON = -97.7431
CAPCOG_RANGE_MILES = 75


def _get(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_events(
    client_id: Optional[str] = None,
    *,
    client_secret: Optional[str] = None,
    extra_params: Optional[dict] = None,
    lat: float = CAPCOG_LAT,
    lon: float = CAPCOG_LON,
    range_miles: int = CAPCOG_RANGE_MILES,
    per_page: int = 100,
    max_pages: int = 5,
    start: Optional[str] = None,
    end: Optional[str] = None,
    sleep: float = 0.25,
) -> Iterator[dict]:
    """Yield raw SeatGeek event dicts for the CAPCOG area, page by page.

    client_id falls back to the SEATGEEK_CLIENT_ID env var when not passed;
    client_secret falls back to SEATGEEK_CLIENT_SECRET (optional — SeatGeek
    accepts client_id alone for read access). `start`/`end` are naive-UTC ISO
    strings (SeatGeek's datetime_utc filter format), applied as
    datetime_utc.gte / datetime_utc.lte."""
    client_id = client_id or os.environ.get("SEATGEEK_CLIENT_ID", "")
    if not client_id:
        raise RuntimeError(
            "SEATGEEK_CLIENT_ID is not set — cannot fetch. Set the env var to "
            "your SeatGeek client id, or pass client_id explicitly."
        )
    client_secret = client_secret or os.environ.get("SEATGEEK_CLIENT_SECRET") or None
    # SeatGeek pages are 1-indexed (page=0 is treated as page=1); start at 1.
    page = 1
    while page <= max_pages:
        params = {
            "client_id": client_id,
            "lat": str(lat),
            "lon": str(lon),
            "range": f"{range_miles}mi",
            "per_page": str(per_page),
            "page": str(page),
            "sort": "datetime_utc.asc",
        }
        if client_secret:
            params["client_secret"] = client_secret
        if start:
            params["datetime_utc.gte"] = start
        if end:
            params["datetime_utc.lte"] = end
        if extra_params:
            params.update(extra_params)
        url = ROOT_URL + "?" + urllib.parse.urlencode(params)
        data = _get(url)
        events = data.get("events") or []
        if not events:
            break
        for ev in events:
            yield ev
        # Stop once the reported total has been paged through. meta.total /
        # meta.per_page are the API's own counts; we never guess a page ceiling.
        meta = data.get("meta") or {}
        total = meta.get("total") or 0
        per = meta.get("per_page") or per_page
        if per and page * per >= total:
            break
        page += 1
        time.sleep(sleep)


def _iso_naive(t: _dt.datetime) -> str:
    """SeatGeek's datetime_utc filter is naive UTC (no offset/Z designator)."""
    return t.strftime("%Y-%m-%dT%H:%M:%S")


def fetch_events_capcog(
    client_id: Optional[str] = None,
    *,
    windows: int = 6,
    window_days: int = 30,
    per_window_pages: int = 10,
    lat: float = CAPCOG_LAT,
    lon: float = CAPCOG_LON,
    range_miles: int = CAPCOG_RANGE_MILES,
    per_page: int = 100,
    sleep: float = 0.2,
    _now: Optional[_dt.datetime] = None,
) -> Iterator[dict]:
    """Comprehensive CAPCOG fetch — sweeps rolling time windows, de-dupes by id.

    A single unbounded query can truncate a busy metro's calendar at the API's
    practical deep-paging depth, and high-volume music crowds out low-volume
    categories (comedy, family, film). We instead sweep the next `windows`
    rolling ~monthly time windows (datetime_utc.gte/lte), deep-page each, and
    de-duplicate by event id — pulling the FULL forward calendar across every
    category. Mirrors worker.importers.ticketmaster.fetch_events_capcog exactly,
    including the injectable `_now` for deterministic tests.
    """
    client_id = client_id or os.environ.get("SEATGEEK_CLIENT_ID", "")
    if not client_id:
        raise RuntimeError("SEATGEEK_CLIENT_ID is not set — cannot fetch.")
    pages = max(1, per_window_pages)
    now = _now or _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)
    seen: set = set()
    for i in range(max(1, windows)):
        start = now + _dt.timedelta(days=i * window_days)
        end = now + _dt.timedelta(days=(i + 1) * window_days)
        for ev in fetch_events(
            client_id,
            lat=lat,
            lon=lon,
            range_miles=range_miles,
            per_page=per_page,
            max_pages=pages,
            start=_iso_naive(start),
            end=_iso_naive(end),
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

    from worker.importers.normalize import normalize_seatgeek

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger("seatgeek_smoke")

    cid = os.environ.get("SEATGEEK_CLIENT_ID", "")
    raws = list(fetch_events(cid, per_page=100, max_pages=4))
    norm = [n for n in (normalize_seatgeek(e) for e in raws) if n]
    if not norm:
        log.error("smoke fetched %d, normalized 0 — bad key / query / drift. Failing loud.", len(raws))
        return 3
    by_domain = Counter(n["category"] for n in norm)
    log.info("REAL SeatGeek events fetched (CAPCOG area): %d", len(raws))
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
