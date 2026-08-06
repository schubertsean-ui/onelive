#!/usr/bin/env python3
"""$0 CENSUS — which extraction tier can serve each proving-set site?

This produces the number the Fix 01 go/no-go decision turns on
(`lab/FIX_01_JSONLD.md` §6): what share of the proving set publishes
schema.org Event data we could read for free and exactly, instead of paying a
model to re-read a flattened string.

Costs nothing: no model call, no credential, plain HTTP, 2s between requests.

Per site it reports, in tier order:
  tier 0  schema.org JSON-LD Event objects in the served HTML
  tier 0b microdata itemtype=...Event
  tier 1  a machine feed the site already publishes (.ics / rss / atom)
  tier 2  event links that could be enumerated and opened individually
  tier 4  nothing in the served markup -> needs a browser

Run from CI. The dev sandbox has no outbound network.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "OneLiveBot/0.1 (+contact: ops@1live.co) structured-census"

# The 16 sites agreed with the founder. URLs taken from the committed catalog
# (sources/master_sources_catalog_120.json) or, where production diverges from
# the catalog, the url production actually crawls — noted per row.
SITES = [
    ("ACL Live at The Moody Theater", "https://www.acllive.com/events"),
    ("ACL Live at 3TEN", "https://www.acllive.com/events/venue/acl-live-at-3ten"),
    ("Moody Amphitheater", "https://www.moodyamphitheater.com/events-tickets"),
    ("Bastrop Opera House", "https://www.bastropoperahouse.org/upcoming-shows"),
    ("Palmer Events Center", "https://www.palmereventscenter.com/events"),
    ("Visit Austin Festivals", "https://www.austintexas.org/events/festivals/"),
    ("The Wimberley Players", "https://www.wimberleyplayers.org/"),
    ("Giddings Area Chamber", "https://giddingstx.com/events-list/"),
    ("City of San Marcos", "https://www.sanmarcostx.gov/Calendar/home"),
    ("Science Mill", "https://www.sciencemill.org/outreach-events"),
    ("Austin Food & Wine Festival", "https://www.austinfoodandwinefestival.com/"),
    ("The Saxon Pub", "https://saxonpub.com/"),
    ("Antone's Nightclub", "https://antonesnightclub.com/"),
    ("Becker Vineyards", "https://beckervineyards.com/events"),
    ("William Chris Vineyards", "https://williamchriswines.com/events/"),
    ("Jester King Brewery", "https://jesterkingbrewery.com/events-calendar"),
    ("Treaty Oak Distilling", "https://www.treatyoakdistilling.com/events"),
]

_JSONLD_BLOCK = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S)
_MICRODATA_EVENT = re.compile(r'itemtype=["\'][^"\']*schema\.org/\w*Event', re.I)
_FEED = re.compile(
    r'href=["\']([^"\']*\.(?:ics|rss|xml)(?:\?[^"\']*)?)["\']', re.I)
_FEED_TYPE = re.compile(
    r'<link[^>]+type=["\']application/(?:rss\+xml|atom\+xml)["\'][^>]*href=["\']([^"\']+)["\']',
    re.I)
_EVENT_HREF = re.compile(
    r'href=["\']([^"\']*/(?:event|events|shows?|calendar|performance|tickets)/[^"\']*)["\']',
    re.I)

# Fields we care about, so the census also answers "and would it give us the
# fields the card needs?" rather than only "does JSON-LD exist?"
WANTED = ("startDate", "endDate", "offers", "description", "image",
          "performer", "eventStatus", "location", "doorTime")


def fetch(url: str) -> tuple[str, str, int] | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:  # noqa: S310
            return r.geturl(), r.read(900_000).decode("utf-8", "replace"), r.status
    except urllib.error.HTTPError as exc:
        print(f"    HTTP {exc.code}", file=sys.stderr)
    except Exception as exc:
        print(f"    {type(exc).__name__}: {exc}", file=sys.stderr)
    return None


def jsonld_events(html: str) -> list:
    """Parse ld+json blocks and return the Event objects, properly — not by
    regex-matching the word Event, which would count a mention in prose."""
    events = []
    for raw in _JSONLD_BLOCK.findall(html):
        try:
            data = json.loads(raw.strip())
        except Exception:
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                t = node.get("@type")
                types = t if isinstance(t, list) else [t]
                if any(isinstance(x, str) and x.lower().endswith(("event", "festival"))
                       for x in types):
                    events.append(node)
                stack.extend(v for v in node.values()
                             if isinstance(v, (dict, list)))
    return events


def main() -> int:
    rows = []
    for name, url in SITES:
        print(f"\n{name}\n  {url}")
        got = fetch(url)
        time.sleep(2)
        if not got:
            rows.append({"site": name, "url": url, "tier": "UNREACHABLE"})
            print("  -> UNREACHABLE")
            continue
        final, html, status = got
        evs = jsonld_events(html)
        micro = len(_MICRODATA_EVENT.findall(html))
        feeds = set(_FEED.findall(html)) | set(_FEED_TYPE.findall(html))
        links = set(_EVENT_HREF.findall(html))

        field_hits = {f: sum(1 for e in evs if e.get(f) is not None) for f in WANTED}

        if evs:
            tier = "0 JSON-LD"
        elif micro:
            tier = "0b microdata"
        elif feeds:
            tier = "1 feed"
        elif links:
            tier = "2 links"
        else:
            tier = "4 needs render"

        rows.append({"site": name, "url": url, "final_url": final,
                     "status": status, "bytes": len(html), "tier": tier,
                     "jsonld_events": len(evs), "microdata_events": micro,
                     "feeds": sorted(feeds)[:3], "event_links": len(links),
                     "jsonld_fields": field_hits})
        print(f"  -> TIER {tier}   jsonld_events={len(evs)} microdata={micro} "
              f"feeds={len(feeds)} event_links={len(links)}")
        if evs:
            present = [f for f, n in field_hits.items() if n]
            print(f"     fields present in JSON-LD: {', '.join(present) or 'none'}")

    print("\n" + "=" * 74)
    print("CENSUS RESULT — the Fix 01 go/no-go input")
    print("=" * 74)
    total = len(rows)
    by_tier = {}
    for r in rows:
        by_tier.setdefault(r["tier"], []).append(r["site"])
    for tier in sorted(by_tier):
        n = len(by_tier[tier])
        print(f"  {n:2}/{total}  ({n/total*100:4.0f}%)  tier {tier}")
        for s in by_tier[tier]:
            print(f"            - {s}")

    structured = sum(len(v) for k, v in by_tier.items() if k.startswith("0"))
    free = sum(len(v) for k, v in by_tier.items() if k[0] in "012")
    print(f"\n  STRUCTURED (tier 0/0b, free AND exact): {structured}/{total} "
          f"= {structured/total*100:.0f}%")
    print(f"  ANY FREE TIER (0/0b/1/2, no model call): {free}/{total} "
          f"= {free/total*100:.0f}%")
    print(f"\n  GO threshold in lab/FIX_01_JSONLD.md is >=30% structured.")
    print(f"  VERDICT INPUT: {'GO range' if structured/total >= 0.30 else 'DELAY/NO-GO range'}")

    # Which of the fields the card needs would arrive for free
    print("\n  Fields the card needs, seen in JSON-LD across the set:")
    agg = {}
    for r in rows:
        for f, n in (r.get("jsonld_fields") or {}).items():
            agg[f] = agg.get(f, 0) + (1 if n else 0)
    for f in WANTED:
        print(f"    {agg.get(f, 0):2}/{total} sites publish {f}")

    print("\n--- MACHINE READABLE ---")
    print(json.dumps(rows, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
