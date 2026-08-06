#!/usr/bin/env python3
"""THE DENOMINATOR — how many events are actually happening, per night?

Every number this project reports is a numerator: events published, candidates
promoted, tests passed. None of them answer the only question that matters —
what fraction of what is REALLY happening tonight can a person see on 1live.co?

That fraction needs a denominator, and a denominator needs a census of reality,
not of our own database. This script builds one by counting distinct dated
events across the aggregators that already inventory this market: the alt-weekly
calendar, the city guides, the ticketing platforms, the public radio and TV
calendars, the community boards.

It is deliberately NOT the crawler. It does not extract for publication, it does
not write candidates, it touches no gate. It counts. A count we did not produce
ourselves is the only thing that can tell us how far short we fall, which is why
this is a lab instrument and not a pipeline stage.

Costs nothing: no model call, no credential, no search quota. Plain HTTP,
stdlib only, polite delay between requests.

Method, per source, cheapest signal first — the same tier order the census uses:
  tier 0   schema.org JSON-LD Event objects (exact dates, free)
  tier 0b  microdata itemtype=...Event
  tier 2   date-bearing event links (a count, not a claim about each event)
  BLOCKED  403/JS-shell/unreachable — reported as blocked, NEVER as zero

That last rule is the one that matters. A source we could not read contributes
UNKNOWN to the denominator, not 0. Silently counting an unreadable aggregator as
"no events" would deflate the denominator and flatter our coverage — the exact
self-serving error a denominator exists to prevent.

Distinctness: the same show is listed by several aggregators, so a raw sum
overcounts badly. Events are keyed on (normalised title, date, normalised
venue); the union of keys is the distinct count, and the per-source counts are
kept alongside so the overlap is visible rather than assumed.

Run from CI (open egress). The dev sandbox cannot fetch.

  python3 lab/denominator.py [--date YYYY-MM-DD] [--json out.json]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

UA = "OneLiveBot/0.1 (+contact: ops@1live.co) denominator-census"
TIMEOUT = 25
DELAY = 2.0

# The aggregators that inventory this market. Founder-named 2026-08-06 plus the
# two WebSearch surfaced the same day (showlists.net, austincomedyshows.com),
# neither of which is in the committed catalog.
#
# `kind` records what we EXPECT so an unexpected result is visible: a source
# marked "ticketing" that serves a JS shell is a known-cost item, not a surprise.
SOURCES: list[tuple[str, str, str]] = [
    # (label, url, kind)
    ("Austin Chronicle calendar", "https://calendar.austinchronicle.com/austin/EventSearch?v=g", "alt-weekly"),
    ("Do512", "https://do512.com/events", "city-guide"),
    ("Showlist Austin", "https://austin.showlists.net/", "music-aggregator"),
    ("Visit Austin events", "https://www.austintexas.org/events/", "tourism-board"),
    ("Austin Comedy Shows", "https://austincomedyshows.com/calendar", "comedy-aggregator"),
    ("Eventbrite Austin", "https://www.eventbrite.com/d/tx--austin/all-events/", "ticketing"),
    ("Ticketmaster Austin", "https://www.ticketmaster.com/discover/concerts/austin", "ticketing"),
    ("Meetup Austin", "https://www.meetup.com/find/?location=us--tx--austin", "community"),
    ("Yelp Austin events", "https://www.yelp.com/events/austin", "community"),
    ("CultureMap Austin", "https://austin.culturemap.com/events/", "periodical"),
    ("KUTX (public radio)", "https://kutx.org/events/", "radio"),
    ("KUT (public radio)", "https://www.kut.org/events", "radio"),
    ("Austin Monitor", "https://www.austinmonitor.com/events/", "periodical"),
    ("Austin American-Statesman things to do", "https://www.statesman.com/things-to-do/", "newspaper"),
    ("KVUE (TV)", "https://www.kvue.com/events", "tv"),
    ("Austin Public Library", "https://library.austintexas.gov/events", "library"),
]

_JSONLD_RE = re.compile(
    r'<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)
_MICRODATA_RE = re.compile(r'itemtype\s*=\s*["\'][^"\']*schema\.org/[A-Za-z]*Event', re.I)
_EVENT_HREF_RE = re.compile(r'href\s*=\s*["\']([^"\']*/(?:event|events|show|shows|concert|calendar)/[^"\']*)["\']', re.I)
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_JS_SHELL_RE = re.compile(r'<div[^>]+id\s*=\s*["\'](?:root|app|__next)["\']', re.I)


def _fetch(url: str) -> tuple[str | None, str | None, str]:
    """Return (html, error, final_url). Never raises — a source that fails is a
    reported BLOCKED row, never a silent zero."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310 — fixed host list
            raw = r.read(4_000_000)
            enc = r.headers.get_content_charset() or "utf-8"
            return raw.decode(enc, errors="replace"), None, r.geturl()
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}", url
    except Exception as e:  # noqa: BLE001 — every failure mode is data here
        return None, f"{type(e).__name__}: {e}", url


def _iter_jsonld(data):
    stack = [data]
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, dict):
            yield node
            g = node.get("@graph")
            if isinstance(g, list):
                stack.extend(g)


def _is_event(obj: dict) -> bool:
    t = obj.get("@type")
    types = t if isinstance(t, list) else [t]
    return any(isinstance(x, str) and x.lower().endswith("event") for x in types)


def _venue_of(obj: dict) -> str:
    loc = obj.get("location")
    if isinstance(loc, dict):
        n = loc.get("name")
        if isinstance(n, str):
            return n
    elif isinstance(loc, str):
        return loc
    return ""


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _date_of(obj: dict) -> str:
    v = obj.get("startDate")
    if isinstance(v, str):
        m = _ISO_DATE_RE.search(v)
        if m:
            return m.group(0)
    return ""


def harvest(label: str, url: str, kind: str, target: str) -> dict:
    html, err, final = _fetch(url)
    row: dict = {"source": label, "kind": kind, "url": url, "final_url": final}
    if html is None:
        row.update(status="BLOCKED", reason=err, events=None, on_target=None)
        return row

    events: list[dict] = []
    for m in _JSONLD_RE.finditer(html):
        try:
            data = json.loads(m.group(1).strip())
        except (ValueError, TypeError):
            continue
        for obj in _iter_jsonld(data):
            if not _is_event(obj):
                continue
            title = obj.get("name") if isinstance(obj.get("name"), str) else ""
            if not title:
                continue
            events.append({
                "title": title.strip(),
                "date": _date_of(obj),
                "venue": _venue_of(obj).strip(),
                "start": obj.get("startDate") if isinstance(obj.get("startDate"), str) else "",
                "end": obj.get("endDate") if isinstance(obj.get("endDate"), str) else "",
                "status": obj.get("eventStatus") if isinstance(obj.get("eventStatus"), str) else "",
                "url": obj.get("url") if isinstance(obj.get("url"), str) else "",
            })

    if events:
        row["tier"] = "0 JSON-LD"
    elif _MICRODATA_RE.search(html):
        row["tier"] = "0b microdata"
    elif _EVENT_HREF_RE.search(html):
        row["tier"] = "2 links"
    elif _JS_SHELL_RE.search(html):
        row["tier"] = "4 needs render"
    else:
        row["tier"] = "none"

    # A JS shell that yielded nothing is BLOCKED, not empty — see module docstring.
    if not events and row["tier"] in ("4 needs render", "none"):
        row.update(status="BLOCKED", reason=f"no readable events ({row['tier']})",
                   events=None, on_target=None,
                   link_count=len(set(_EVENT_HREF_RE.findall(html))))
        return row

    link_count = len(set(_EVENT_HREF_RE.findall(html)))
    row.update(
        status="READ",
        events=len(events),
        on_target=sum(1 for e in events if e["date"] == target) if events else 0,
        link_count=link_count,
        dated=sum(1 for e in events if e["date"]),
        with_end=sum(1 for e in events if e["end"]),
        with_status=sum(1 for e in events if e["status"]),
        sample=[e for e in events[:3]],
    )
    row["_events"] = events
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=_dt.date.today().isoformat(),
                    help="target night, YYYY-MM-DD (default: today, UTC)")
    ap.add_argument("--json", default="", help="write the full result here")
    args = ap.parse_args()
    target = args.date

    rows = []
    for i, (label, url, kind) in enumerate(SOURCES):
        if i:
            time.sleep(DELAY)
        print(f"  fetching {label} ...", flush=True)
        rows.append(harvest(label, url, kind, target))

    # Distinct union across sources. Same show, several aggregators.
    keys: dict[tuple, list[str]] = defaultdict(list)
    for r in rows:
        for e in r.pop("_events", []) or []:
            if not e["date"]:
                continue
            keys[(_norm(e["title"]), e["date"], _norm(e["venue"]))].append(r["source"])

    on_target_keys = {k: v for k, v in keys.items() if k[1] == target}

    read = [r for r in rows if r["status"] == "READ"]
    blocked = [r for r in rows if r["status"] == "BLOCKED"]

    print()
    print("=" * 72)
    print(f"DENOMINATOR CENSUS — target night {target}")
    print("=" * 72)
    print(f"{'source':38s} {'status':8s} {'events':>7s} {'on-night':>9s}  tier")
    for r in rows:
        ev = "-" if r["events"] is None else str(r["events"])
        on = "-" if r["on_target"] is None else str(r["on_target"])
        print(f"  {r['source']:36s} {r['status']:8s} {ev:>7s} {on:>9s}  {r.get('tier','-')}")
        if r["status"] == "BLOCKED":
            print(f"      reason: {r['reason']}")

    print()
    print(f"sources READ:    {len(read)}/{len(rows)}")
    print(f"sources BLOCKED: {len(blocked)}/{len(rows)}  <- contribute UNKNOWN, never 0")
    print(f"raw events seen (all dates):        {sum(r['events'] or 0 for r in read)}")
    print(f"DISTINCT events (all dates):        {len(keys)}")
    print(f"DISTINCT events on {target}: {len(on_target_keys)}")
    print()
    print("The distinct on-night count is the DENOMINATOR floor — a floor, not a")
    print("total, because every BLOCKED source above is uncounted reality.")

    overlap = sorted(((len(set(v)), k) for k, v in on_target_keys.items()), reverse=True)[:5]
    if overlap:
        print()
        print("most-corroborated events on the night (listed by N sources):")
        for n, k in overlap:
            print(f"  {n}x  {k[0][:60]!r} @ {k[2][:30]!r}")

    payload = {
        "target_date": target,
        "sources_total": len(rows),
        "sources_read": len(read),
        "sources_blocked": len(blocked),
        "distinct_all_dates": len(keys),
        "distinct_on_target": len(on_target_keys),
        "denominator_is_a_floor": True,
        "rows": rows,
    }
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
