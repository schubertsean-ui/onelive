#!/usr/bin/env python3
"""Source DISCOVERY that generates candidates instead of checking guesses.

The existing mechanism (`tools/scan_new_sources.py`) is 21 hardcoded search
phrases prefixed with one city, against a credential that returns 403. It has
never run. Nine of the twenty-three ratified supply segments have no source
because nothing ever searched for them.

This is the replacement's first method, and the cheapest one: **mine the
aggregators we already fetch.** Do512, the Austin Chronicle, Visit Austin,
CultureMap, KUT and the chamber calendars are, functionally, venue directories.
We download them on every ingest cycle, extract a few events, and throw the
rest away — including every outbound link to a venue we have never heard of.

Method:
  1. Fetch seed pages that are already in the committed catalog.
  2. Extract every outbound link, normalise to a registrable domain.
  3. Drop platforms, socials, the seed's own domain, and anything the catalog
     already knows.
  4. Rank what remains by how many DIFFERENT seeds surfaced it — a domain three
     independent local guides link to is a stronger candidate than one linked
     once.
  5. Probe the top candidates for event-like content, so the output is
     qualified rather than raw.

No credential. No model call. No search quota. Read-only.

This finds venues nobody typed, which is the part guessing cannot do.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

UA = "OneLiveBot/0.1 (+contact: ops@1live.co) source-discovery"
CATALOG = "sources/master_sources_catalog_120.json"

# Seeds: pages already in our catalog that function as directories of OTHER
# venues. These are fetched by the production pipeline already.
SEEDS = [
    "https://do512.com/",
    "https://www.austinchronicle.com/events/",
    "https://www.austintexas.org/events/",
    "https://austin.culturemap.com/events/",
    "https://www.austintexas.gov/events",
    "https://www.kut.org/tags/kut-events",
    "https://giddingstx.com/events-list/",
    "https://www.sanmarcostx.gov/Calendar/home",
    "https://www.austintexas.org/events/festivals/",
    "https://events.kvue.com/",
]

# Never a first-party event source. Kept deliberately small and obvious; the
# ranking and the probe do the rest of the work.
PLATFORMS = {
    "facebook.com", "instagram.com", "x.com", "twitter.com", "tiktok.com",
    "youtube.com", "yelp.com", "tripadvisor.com", "reddit.com",
    "wikipedia.org", "eventbrite.com", "ticketmaster.com", "seatgeek.com",
    "stubhub.com", "bandsintown.com", "songkick.com", "meetup.com",
    "google.com", "linktr.ee", "spotify.com", "apple.com", "opentable.com",
    "gofundme.com", "mailchimp.com", "paypal.com", "wordpress.org", "wix.com",
    "squarespace.com", "godaddy.com", "cloudflare.com", "adobe.com",
    "linkedin.com", "pinterest.com", "vimeo.com", "soundcloud.com",
    "amazon.com", "patreon.com", "venmo.com", "zoom.us", "flickr.com",
    "creativecommons.org", "schema.org", "w3.org", "gstatic.com",
    "googleapis.com", "doubleclick.net", "ticketweb.com", "tixr.com",
    "axs.com", "dice.fm", "ra.co", "prekindle.com", "seetickets.us",
    "universe.com", "etix.com", "showclix.com", "ludus.com", "eventvesta.com",
}

_HREF = re.compile(r'href=["\'](https?://[^"\']+)["\']', re.I)
_MONTHS = r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
_DATE = re.compile(
    rf"(\b(?:{_MONTHS})[a-z]*\.?\s+\d{{1,2}}\b)|(\b\d{{4}}-\d{{2}}-\d{{2}}\b)", re.I)
_EVENT_LINK = re.compile(
    r'href=["\'][^"\']*(event|show|calendar|tickets|performance|lineup)[^"\']*["\']', re.I)
_JSONLD_EVENT = re.compile(r'"@type"\s*:\s*"[^"]*Event"', re.I)


def get(url: str, cap: int = 800_000) -> tuple[str, str] | None:
    """Fetch a page. Returns (final_url, html) or None with the reason printed —
    a failure is reported, never swallowed."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:  # noqa: S310
            return r.geturl(), r.read(cap).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        print(f"    fetch failed {url} — HTTP {exc.code}", file=sys.stderr)
    except Exception as exc:
        print(f"    fetch failed {url} — {type(exc).__name__}: {exc}", file=sys.stderr)
    return None


def registrable(url: str) -> str | None:
    """Reduce a url to its registrable domain. Deliberately simple: a wrong
    reduction only costs a duplicate candidate, never a false fact."""
    try:
        host = urllib.parse.urlparse(url).netloc.lower().split(":")[0]
    except ValueError:
        return None
    if not host:
        return None
    host = host[4:] if host.startswith("www.") else host
    parts = host.split(".")
    if len(parts) > 2 and parts[-2] in {"co", "com", "org", "net"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])          # e.g. example.co.uk
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def catalog_domains() -> set[str]:
    rows = json.load(open(CATALOG))
    rows = rows if isinstance(rows, list) else rows.get("sources", rows)
    out = set()
    for r in rows:
        d = registrable(r.get("base_url") or "")
        if d:
            out.add(d)
    return out


def event_like(html: str) -> dict:
    return {
        "date_mentions": len(_DATE.findall(html)),
        "event_link_patterns": len(set(_EVENT_LINK.findall(html))),
        "jsonld_event_objects": len(_JSONLD_EVENT.findall(html)),
    }


def main() -> int:
    known = catalog_domains()
    print(f"catalog covers {len(known)} registrable domains")

    surfaced: dict[str, set[str]] = defaultdict(set)
    seeds_ok = 0
    for seed in SEEDS:
        print(f"\nseed: {seed}")
        got = get(seed)
        if not got:
            continue
        seeds_ok += 1
        final, html = got
        seed_domain = registrable(final)
        found = 0
        for href in _HREF.findall(html):
            d = registrable(href)
            if not d or d == seed_domain or d in PLATFORMS or d in known:
                continue
            surfaced[d].add(seed_domain or seed)
            found += 1
        print(f"    {len(set(_HREF.findall(html)))} links, "
              f"{found} pointing at domains the catalog does not have")
        time.sleep(2)   # politeness: one host at a time, 2s apart

    if seeds_ok == 0:
        print("\nNO SEED FETCHED — network or blocks. Not an empty result, a "
              "failed run.", file=sys.stderr)
        return 3

    ranked = sorted(surfaced.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    print(f"\n{'='*72}\n{len(ranked)} NEW DOMAINS the catalog has never seen\n{'='*72}")
    for d, seeds in ranked[:60]:
        print(f"  {len(seeds)}x  {d}   (via {', '.join(sorted(seeds))})")

    # Qualify the strongest candidates so the output is usable, not raw.
    print(f"\n{'='*72}\nQUALIFYING the top candidates (does the site list dated events?)\n{'='*72}")
    qualified, checked = [], 0
    for d, seeds in ranked:
        if checked >= 25:
            break
        checked += 1
        got = get(f"https://{d}/", cap=400_000)
        time.sleep(2)
        if not got:
            continue
        final, html = got
        sig = event_like(html)
        ok = sig["jsonld_event_objects"] > 0 or (
            sig["date_mentions"] >= 3 and sig["event_link_patterns"] >= 1)
        row = {"domain": d, "final_url": final, "surfaced_by": sorted(seeds),
               "verdict": "LISTS_DATED_EVENTS" if ok else "NO_EVENTS_IN_SERVED_HTML",
               **sig}
        if ok:
            qualified.append(row)
        print(f"  {row['verdict']:26} {d}  dates={sig['date_mentions']} "
              f"links={sig['event_link_patterns']} jsonld={sig['jsonld_event_objects']}")

    print(f"\n{'='*72}\nRESULT\n{'='*72}")
    print(f"  seeds fetched:            {seeds_ok}/{len(SEEDS)}")
    print(f"  new domains surfaced:     {len(ranked)}")
    print(f"  probed:                   {checked}")
    print(f"  qualified as event sites: {len(qualified)}")
    print("\n  NOTE: probes read raw HTML only. NO_EVENTS_IN_SERVED_HTML means "
          "'nothing in the served markup' — a render candidate, not a dead site.")
    print("\n--- MACHINE READABLE ---")
    print(json.dumps({"qualified": qualified,
                      "all_new_domains": {d: sorted(s) for d, s in ranked}},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
