#!/usr/bin/env python3
"""Shared licensed-search client — Brave Search API.

Founder-ratified provider switch (2026-08-05, verbatim "Switch to Brave - do
all the work"; decision record docs/memory/decisions/2026-08-05_search-lane-
brave-switch.md): Google's Custom Search JSON API refuses this account at the
account level (proven mechanically — see 2026-08-05_founder-delegated-google-
fix.md), so the search lane's discovery tools (scan_new_sources.py,
search_discover_eventbrite.py) query Brave's licensed Web Search API instead.

Documented endpoint, keyed access, no scraping:
  GET https://api.search.brave.com/res/v1/web/search?q=..&count=..&offset=..
  header X-Subscription-Token: BRAVE_SEARCH_API_KEY

Free plan: 2,000 queries/month at 1 request/second — budget in
docs/ops/SEARCH_QUOTA_BUDGET.md. The 1 rps limit is enforced here with a
module-level throttle so no caller can accidentally burst past it.

Fail-loud contract: a missing key raises MissingKey (callers exit 2 with a
paste-ready message); HTTP errors raise SearchError carrying the API's own
error body so quota/auth problems diagnose themselves in run logs.
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request

API = "https://api.search.brave.com/res/v1/web/search"
_MIN_INTERVAL_S = 1.05  # free-plan rate limit is 1 req/s; stay just under
_last_call = 0.0


class MissingKey(RuntimeError):
    """BRAVE_SEARCH_API_KEY is absent from the environment."""


class SearchError(RuntimeError):
    """The API answered with an error; .status and .body carry its own words."""

    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status = status
        self.body = body


def api_key() -> str:
    """The subscription token, or MissingKey with the paste-ready pointer."""
    key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
    if not key:
        raise MissingKey(
            "BRAVE_SEARCH_API_KEY missing — create one (Free plan, 2,000 "
            "queries/month) at https://api-dashboard.search.brave.com/ and "
            "add it as a repo Actions secret.")
    return key


def search(query: str, *, count: int = 20, offset: int = 0,
           timeout: int = 20) -> dict:
    """One Brave Web Search call (documented endpoint, keyed, throttled)."""
    global _last_call
    wait = _MIN_INTERVAL_S - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    qs = urllib.parse.urlencode({"q": query, "count": count, "offset": offset})
    req = urllib.request.Request(f"{API}?{qs}", headers={
        "X-Subscription-Token": api_key(),
        "Accept": "application/json",
        "User-Agent": "1LiveSourceDiscovery/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        raise SearchError(exc.code,
                          exc.read().decode("utf-8", "replace")) from exc
    finally:
        _last_call = time.monotonic()
    return payload


def web_results(payload: dict) -> list[dict]:
    """Normalize a response to [{url, title, description}] (missing -> '')."""
    out = []
    for item in (payload.get("web") or {}).get("results", []):
        out.append({"url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "description": item.get("description", "")})
    return out
