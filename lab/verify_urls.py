#!/usr/bin/env python3
"""Verify candidate source URLs from CI, where there IS outbound network.

The dev sandbox cannot reach the internet, so any URL written into the handoff
from memory would be an unverified assertion. This script closes that gap the
only honest way: propose candidates as HYPOTHESES, fetch each one, and report
what is actually there. A candidate that fails is reported as failed and
replaced — it never silently enters the document.

Read-only. No secrets. One request per host, honest User-Agent, redirects
followed and the FINAL url reported (the acl-live.com / acllive.com class of
defect is exactly a redirect nobody looked at).

Verdict per URL:
  LISTS_DATED_EVENTS  reachable AND shows evidence of dated event listings
  REACHABLE_NO_EVENTS reachable but nothing event-like — not a valid source
  UNREACHABLE         DNS/TLS/HTTP failure, with the reason

KNOWN LIMITATION, stated rather than hidden: this reads RAW HTML and does not
run JavaScript. A site that builds its listing in the browser will report
REACHABLE_NO_EVENTS even when it has events. That is the same defect the
production fetcher has, so a REACHABLE_NO_EVENTS verdict means "no events in
the served HTML" — a render candidate, not a dead site.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request

UA = "OneLiveBot/0.1 (+contact: ops@1live.co) source-verification"

# Candidates for the nine ratified supply segments with NO catalog
# representative. These are HYPOTHESES to be checked, not claims.
# Paths tried per candidate host. Round 1 probed site ROOTS and produced false
# negatives: an artist's root page carries no dates while /tour does. A root is
# not a listing page, and checking one is not checking the site.
PATHS = ("", "/tour", "/tour-dates", "/shows", "/events", "/calendar",
         "/schedule", "/live", "/upcoming")

CANDIDATES = {
    "15 recurring-scene organizers": [
        ("Kick Butt Coffee", "https://kickbuttcoffee.com"),
        ("The Hideout Theatre", "https://hideouttheatre.com"),
        ("Spider House Ballroom", "https://spiderhouseballroom.com"),
        ("Austin Poetry Slam", "https://austinpoetryslam.org"),
    ],
    "16 social-dance & movement": [
        ("Go Dance Austin", "https://godancestudio.com"),
        ("Esquina Tango", "https://www.esquinatango.org"),
        ("Austin Swing Syndicate", "https://www.austinswingsyndicate.org"),
        ("Dance Austin Studio", "https://danceaustinstudio.com"),
    ],
    "18 bands & musical acts": [
        ("Black Pumas", "https://www.blackpumas.com"),
        ("Spoon", "https://spoontheband.com"),
        ("Explosions in the Sky", "https://www.explosionsinthesky.com"),
        ("Grupo Fantasma", "https://grupofantasma.com"),
    ],
    "19 solo musicians & singer-songwriters": [
        ("Gary Clark Jr.", "https://www.garyclarkjr.com"),
        ("Shakey Graves", "https://www.shakeygraves.com"),
        ("Jackie Venson", "https://jackievenson.com"),
        ("Bob Schneider", "https://bobschneider.com"),
    ],
    "20 DJs & electronic artists": [
        ("The Concourse Project", "https://concourseproject.com"),
        ("Kingdom Nightclub", "https://kingdomnightclub.com"),
        ("Elysium", "https://www.elysiumonline.net"),
        ("Empire Control Room", "https://empireatx.com"),
    ],
    "21 comedians & spoken-word": [
        ("Cap City Comedy", "https://www.capcitycomedy.com"),
        ("The Velveeta Room", "https://www.thevelveetaroom.com"),
        ("Fallout Comedy", "https://falloutcomedy.com"),
        ("Creek and the Cave", "https://creekandcave.com"),
    ],
    "23 visual artists, makers & craft creators": [
        ("Big Medium (Austin Studio Tour)", "https://bigmedium.org"),
        ("Canopy Austin", "https://www.canopyaustin.com"),
        ("Blue Genie Art Bazaar", "https://bluegenieartbazaar.com"),
        ("Dougherty Arts Center", "https://www.austintexas.gov/department/dougherty-arts-center"),
    ],
}

_MONTHS = (r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec")
_DATE_RE = re.compile(
    rf"(\b(?:{_MONTHS})[a-z]*\.?\s+\d{{1,2}}\b)|(\b\d{{4}}-\d{{2}}-\d{{2}}\b)"
    rf"|(\b\d{{1,2}}/\d{{1,2}}/\d{{2,4}}\b)",
    re.I,
)
_EVENT_LINK_RE = re.compile(
    r'href=["\'][^"\']*(event|show|calendar|tickets|performance|lineup)[^"\']*["\']',
    re.I,
)
_JSONLD_EVENT_RE = re.compile(r'"@type"\s*:\s*"[^"]*Event"', re.I)


def probe(name: str, url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:  # noqa: S310
            raw = r.read(600_000)
            final = r.geturl()
            status = r.status
    except urllib.error.HTTPError as exc:
        return {"name": name, "url": url, "verdict": "UNREACHABLE",
                "reason": f"HTTP {exc.code}"}
    except Exception as exc:  # DNS, TLS, timeout — report, never swallow
        return {"name": name, "url": url, "verdict": "UNREACHABLE",
                "reason": f"{type(exc).__name__}: {exc}"}

    html = raw.decode("utf-8", "replace")
    dates = len(_DATE_RE.findall(html))
    links = len(set(_EVENT_LINK_RE.findall(html)))
    jsonld = len(_JSONLD_EVENT_RE.findall(html))
    # "Event-like" is deliberately generous at this stage: this decides whether
    # a site is worth putting in the proving set, not whether extraction works.
    listy = jsonld > 0 or (dates >= 3 and links >= 1)
    return {
        "name": name,
        "url": url,
        "final_url": final,
        "status": status,
        "bytes": len(raw),
        "date_mentions": dates,
        "event_link_patterns": links,
        "jsonld_event_objects": jsonld,
        "verdict": "LISTS_DATED_EVENTS" if listy else "REACHABLE_NO_EVENTS",
    }


def best_of_paths(name: str, host: str) -> dict:
    """Probe the host root AND the paths a listing normally lives at, and keep
    the strongest result. Reporting only the root is how round 1 produced false
    negatives on artist sites."""
    tried = []
    for path in PATHS:
        r = probe(name, host.rstrip("/") + path)
        r["path_tried"] = path or "/"
        tried.append(r)
        if r["verdict"] == "LISTS_DATED_EVENTS":
            r["also_tried"] = len(tried)
            return r
    reachable = [t for t in tried if t["verdict"] != "UNREACHABLE"]
    best = max(reachable, key=lambda t: t.get("date_mentions", 0)) if reachable else tried[0]
    best["also_tried"] = len(tried)
    return best


def main() -> int:
    results = {}
    for segment, cands in CANDIDATES.items():
        print(f"\n=== {segment} ===")
        rows = []
        for name, url in cands:
            row = best_of_paths(name, url)
            rows.append(row)
            if row["verdict"] == "UNREACHABLE":
                print(f"  {row['verdict']:20} {name}  {row['url']}  ({row['reason']})")
            else:
                redirect = ""
                if row.get("final_url") and row["final_url"].rstrip("/") != row["url"].rstrip("/"):
                    redirect = f"  -> REDIRECTED TO {row['final_url']}"
                print(f"  {row['verdict']:20} {name}  {row['url']}{redirect}")
                print(f"      status={row['status']} bytes={row['bytes']} "
                      f"dates={row['date_mentions']} event_links={row['event_link_patterns']} "
                      f"jsonld_events={row['jsonld_event_objects']}")
        results[segment] = rows

    print("\n\n=== VERIFIED PICKS (first two LISTS_DATED_EVENTS per segment) ===")
    for segment, rows in results.items():
        good = [r for r in rows if r["verdict"] == "LISTS_DATED_EVENTS"]
        if len(good) < 2:
            print(f"  {segment}: ONLY {len(good)} VERIFIED — needs another candidate")
        for r in good[:2]:
            print(f"  {segment}: {r['name']} -> {r.get('final_url') or r['url']}")

    print("\n--- MACHINE READABLE ---")
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
