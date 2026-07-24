#!/usr/bin/env python3
"""Read-only PROOF: print a diverse sample of REAL licensed events straight from
the live Supabase, across many cultural domains, with counts. Uses the PUBLIC
publishable key (same value web/lib/licensed.ts ships to every browser) — no
secret. Runs on GitHub Actions (open egress); the dev sandbox cannot reach
Supabase. For founder verification that the feed is real end to end.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

_URL = "https://vqipjlvzfiwnandjumvx.supabase.co"
# PUBLIC publishable (anon) key — identical to web/lib/licensed.ts; RLS is the
# security boundary, not this key. Never a service_role/secret.
_KEY = "sb_publishable_cWk_eNqbMWGIIFQf5B5hIg_CFqjAyac"
_HDR = {"apikey": _KEY, "Authorization": f"Bearer {_KEY}"}


def _get(params: str, count: bool = False):
    req = urllib.request.Request(f"{_URL}/rest/v1/licensed_event?{params}", headers={**_HDR, **({"Prefer": "count=exact", "Range": "0-0"} if count else {})})
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 (fixed host)
        body = json.load(r)
        if count:
            cr = r.headers.get("content-range", "")
            return int(cr.split("/")[1]) if "/" in cr else len(body)
        return body


def _money(e: dict) -> str:
    if e.get("is_free") or e.get("price_min") == 0:
        return "Free"
    lo, hi = e.get("price_min"), e.get("price_max")
    if lo is not None and hi is not None and hi != lo:
        return f"${round(lo)}-${round(hi)}"
    if lo is not None:
        return f"${round(lo)}+"
    return "see tickets"


DOMAINS = [
    "live-music", "comedy", "theater", "performing-arts", "sports",
    "food-drink", "family", "film", "festivals", "dance",
]

total = _get("select=licensed_event_id&status=in.(scheduled,moved)", count=True)
print(f"LIVE licensed_event rows (scheduled/moved): {total}\n")

grand = 0
for cat in DOMAINS:
    n = _get(f"select=licensed_event_id&category=eq.{cat}&status=in.(scheduled,moved)", count=True)
    grand += n
    if n == 0:
        continue
    rows = _get(
        "select=title,subsegment,start_time,venue_name,venue_city,price_min,price_max,is_free,ticket_url"
        f"&category=eq.{cat}&status=in.(scheduled,moved)&order=start_time.asc&limit=6"
    )
    print(f"══ {cat.upper()} — {n} events ══")
    for e in rows:
        when = (e.get("start_time") or "TBA")[:16].replace("T", " ")
        sub = f" [{e['subsegment']}]" if e.get("subsegment") else ""
        print(f"  {when}  {e.get('title','?')}{sub}")
        print(f"            @ {e.get('venue_name','?')}, {e.get('venue_city','?')}  ·  {_money(e)}  ·  {'ticket' if e.get('ticket_url') else 'no-link'}")
    print()

print(f"Covered domains total: {grand} of {total} (rest in Other/unmapped or unlisted domains).")
