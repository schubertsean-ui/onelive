"""Eventbrite API v3 client — deterministic licensed-feed fetch.

Stdlib-only (urllib), no AI. Eventbrite REMOVED public event search in 2020, so
there is no keyword/geo query to run; instead we POLL a configured list of KNOWN
organizer (and/or venue) ids and yield their live events for
worker.importers.normalize.normalize_eventbrite. This is the deliberate design:
OneLive curates which organizers/venues it trusts, and re-polls them on schedule.

Auth is an OAuth private token sent as a Bearer header (per
www.eventbrite.com/platform/api). The token is read from the environment
(EVENTBRITE_TOKEN) or passed in — NEVER hard-coded or committed. It is a NEW
service credential (founder-crucial) and is not present in the dev sandbox; runs
happen on GitHub Actions where egress reaches Eventbrite.

Pagination follows Eventbrite's continuation model:
pagination.has_more_items + pagination.continuation (?continuation=...).
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from typing import Iterator, Optional

BASE_URL = "https://www.eventbriteapi.com/v3"

# Everything normalize_eventbrite needs off a single event GET.
DEFAULT_EXPAND = "venue,ticket_availability,category,subcategory"


def _get(url: str, token: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _require_token(token: Optional[str]) -> str:
    token = token or os.environ.get("EVENTBRITE_TOKEN", "")
    if not token:
        raise RuntimeError(
            "EVENTBRITE_TOKEN is not set — cannot fetch. Set the env var to your "
            "Eventbrite private OAuth token, or pass token explicitly. (This is a "
            "founder-crucial new service credential; agents never mint keys.)"
        )
    return token


def _fetch_paged(
    path: str,
    token: str,
    *,
    status: str = "live",
    expand: str = DEFAULT_EXPAND,
    order_by: str = "start_asc",
    max_pages: int = 20,
    sleep: float = 0.2,
) -> Iterator[dict]:
    """Yield raw event dicts from a paged `.../events/` endpoint, following
    Eventbrite's continuation tokens up to max_pages."""
    continuation: Optional[str] = None
    pages = 0
    while pages < max_pages:
        params = {"status": status, "expand": expand, "order_by": order_by}
        if continuation:
            params["continuation"] = continuation
        url = f"{BASE_URL}/{path}?" + urllib.parse.urlencode(params)
        data = _get(url, token)
        events = data.get("events") or []
        for ev in events:
            yield ev
        pagination = data.get("pagination") or {}
        continuation = pagination.get("continuation")
        pages += 1
        if not pagination.get("has_more_items") or not continuation:
            break
        time.sleep(sleep)


def fetch_organizer_events(
    token: Optional[str],
    org_id: str,
    *,
    status: str = "live",
    expand: str = DEFAULT_EXPAND,
    order_by: str = "start_asc",
    max_pages: int = 20,
    sleep: float = 0.2,
) -> Iterator[dict]:
    """Yield the live events of ONE known Eventbrite organization, page by page.

    token falls back to the EVENTBRITE_TOKEN env var when not passed."""
    token = _require_token(token)
    yield from _fetch_paged(
        f"organizations/{org_id}/events",
        token,
        status=status,
        expand=expand,
        order_by=order_by,
        max_pages=max_pages,
        sleep=sleep,
    )


def fetch_venue_events(
    token: Optional[str],
    venue_id: str,
    *,
    status: str = "live",
    expand: str = DEFAULT_EXPAND,
    order_by: str = "start_asc",
    max_pages: int = 20,
    sleep: float = 0.2,
) -> Iterator[dict]:
    """Yield the live events of ONE known Eventbrite venue, page by page."""
    token = _require_token(token)
    yield from _fetch_paged(
        f"venues/{venue_id}/events",
        token,
        status=status,
        expand=expand,
        order_by=order_by,
        max_pages=max_pages,
        sleep=sleep,
    )


def fetch_known(
    token: Optional[str],
    ids: list[str],
    *,
    kind: str = "organization",
    status: str = "live",
    expand: str = DEFAULT_EXPAND,
    max_pages: int = 20,
    sleep: float = 0.2,
) -> Iterator[dict]:
    """Poll a CONFIGURED list of known organizer/venue ids and yield their raw
    events, de-duplicated by event id (the same show can be surfaced under more
    than one polled id). `kind` selects the endpoint: 'organization' | 'venue'.

    This is the top-level entry the runner uses. There is no search — the trusted
    id list IS the query, so a coverage gap is a curation decision we can see, not
    a silent API guess.
    """
    token = _require_token(token)
    if kind not in ("organization", "venue"):
        raise ValueError(f"kind must be 'organization' or 'venue', got {kind!r}")
    fetch_one = fetch_organizer_events if kind == "organization" else fetch_venue_events
    seen: set[str] = set()
    for _id in ids:
        for ev in fetch_one(
            token, str(_id), status=status, expand=expand,
            max_pages=max_pages, sleep=sleep,
        ):
            eid = ev.get("id")
            if eid is not None:
                if eid in seen:
                    continue
                seen.add(eid)
            yield ev
