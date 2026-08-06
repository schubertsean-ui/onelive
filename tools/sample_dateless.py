#!/usr/bin/env python3
"""Read-only DIAGNOSTIC: split the canonical `event` table by whether a row
carries a date the consumer feed can use, and print real examples of the rows
that do not.

Why this exists (2026-08-06): the production scope report showed 2,215
pipeline-published events with exactly ONE future start_time, but "upcoming"
conflates two very different populations — a row with NO start_time at all
(the extractor correctly refused to invent a date it could not see) and a row
whose event genuinely already happened. Only the first population is
recoverable by date recovery, so the split decides how much PR #189 is worth.
`tools/db_scope_report.py` cannot answer it without a schema-level query, and
that report is master-only by design.

This script needs no secret. It reads the same rows a browser reads, through
the PUBLIC publishable key already committed in `tools/sample_feed.py` and
shipped in `web/lib/licensed.ts` — RLS is the security boundary, not the key.
It writes nothing.

Deliberately NOT a gate and NOT imported by any pipeline module: it is an
observation instrument, and observation must never become a trust input.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

_URL = "https://vqipjlvzfiwnandjumvx.supabase.co"
# PUBLIC publishable (anon) key — identical to tools/sample_feed.py and
# web/lib/licensed.ts. Never a service_role/secret.
_KEY = "sb_publishable_cWk_eNqbMWGIIFQf5B5hIg_CFqjAyac"
_HDR = {"apikey": _KEY, "Authorization": f"Bearer {_KEY}"}

# Anon-granted listing columns only (migration 0012). `venue:venue_id(...)` is
# the PostgREST embed over the event->venue FK, exactly as web/lib/promoted.ts
# reads it — so what this prints is what a visitor could see.
_SELECT = "event_id,title,start_time,status,confidence,source_name,source_url,venue:venue_id(name,city)"


def _request(params: str, *, count: bool = False):
    """One GET against /rest/v1/event. With count=True, ask PostgREST for an
    exact row count and read it off the content-range header instead of
    downloading the rows."""
    url = f"{_URL}/rest/v1/event?{params}"
    headers = dict(_HDR)
    if count:
        headers["Prefer"] = "count=exact"
        headers["Range"] = "0-0"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (fixed host)
        body = json.load(resp)
        if count:
            content_range = resp.headers.get("content-range", "")
            if "/" not in content_range:
                raise RuntimeError(
                    f"PostgREST returned no exact count for {params!r} "
                    f"(content-range={content_range!r}) — refusing to report a "
                    "row count inferred from a partial page."
                )
            return int(content_range.split("/")[1])
        return body


def _count(params: str) -> int:
    return _request(params, count=True)


def _venue(row: dict) -> str:
    v = row.get("venue") or {}
    name, city = v.get("name"), v.get("city")
    if name and city:
        return f"{name} ({city})"
    return name or city or "—"


def main() -> int:
    now = datetime.now(timezone.utc).isoformat()

    total = _count("select=event_id")
    dateless = _count("select=event_id&start_time=is.null")
    past = _count(f"select=event_id&start_time=lt.{urllib.parse.quote(now)}")
    future = _count(f"select=event_id&start_time=gte.{urllib.parse.quote(now)}")

    print(f"canonical `event` rows, measured {now}\n")
    print(f"  total            {total}")
    print(f"  NO start_time    {dateless}   <- recoverable by date recovery (PR #189)")
    print(f"  past start_time  {past}   <- genuinely over, or a wrong year")
    print(f"  future           {future}   <- visible on the feed today")
    accounted = dateless + past + future
    if accounted != total:
        print(f"\n  NOTE: {dateless}+{past}+{future}={accounted} != {total} — "
              "the three buckets should partition the table; investigate "
              "before quoting these numbers.")

    print("\n" + "=" * 78)
    print("REAL EXAMPLES of published-but-dateless events (what a visitor never sees)")
    print("=" * 78)
    # Read the WHOLE dateless population, not a page of it. An earlier version
    # took the first 60 rows ordered by source_name and reported "2 affected
    # sources" — it had only ever seen the alphabetically-first two calendars.
    # A page of a sorted table is not a sample of the table.
    rows: list = []
    page = 0
    while True:
        batch = _request(
            f"select={_SELECT}&start_time=is.null&order=event_id.asc"
            f"&limit=1000&offset={page * 1000}"
        )
        rows.extend(batch)
        if len(batch) < 1000 or page > 20:
            break
        page += 1
    print(f"\n(read {len(rows)} of the {dateless} dateless rows)")

    seen_sources: set = set()
    shown = 0
    # One row per SOURCE, so the examples show the breadth of affected venues
    # rather than many listings from a single calendar.
    for row in rows:
        src = row.get("source_name") or "(unknown source)"
        if src in seen_sources:
            continue
        seen_sources.add(src)
        shown += 1
        print(f"\n{shown}. {row.get('title') or '(untitled)'}")
        print(f"   venue:      {_venue(row)}")
        print(f"   source:     {src}")
        print(f"   source_url: {row.get('source_url') or '—'}")
        print(f"   state:      status={row.get('status')} confidence={row.get('confidence')} start_time=NULL")
        print(f"   event_id:   {row.get('event_id')}")
        if shown >= 20:
            break
    if not shown:
        print("\n  none — no published event is missing a start_time.")

    # Every row that DID get a stored date. With 2,214 of 2,215 dateless,
    # this set is small enough to print in full — and a stored date is a fact
    # we asserted publicly, so each one deserves to be eyeballed against its
    # source rather than trusted because it parsed.
    print("\n" + "=" * 78)
    print("EVERY row with a STORED start_time (we asserted these dates publicly)")
    print("=" * 78)
    dated = _request(f"select={_SELECT}&start_time=not.is.null&order=start_time.asc&limit=200")
    for row in dated:
        print(f"\n   {row.get('start_time')}  {row.get('title') or '(untitled)'}")
        print(f"   venue:  {_venue(row)}")
        print(f"   source: {row.get('source_name')}  {row.get('source_url') or ''}")
    if not dated:
        print("\n  none.")

    print("\n" + "=" * 78)
    print("EVERY SOURCE with published-but-dateless events (whole population)")
    print("=" * 78)
    by_source: dict = {}
    for row in rows:
        by_source[row.get("source_name") or "(unknown source)"] = (
            by_source.get(row.get("source_name") or "(unknown source)", 0) + 1
        )
    for src, n in sorted(by_source.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>4}  {src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
