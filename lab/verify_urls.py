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
CANDIDATES = {
    "15 recurring-scene organizers": [
        ("Austin Poetry Slam", "https://www.austinpoetryslam.com/"),
        ("Kick Butt Coffee", "https://kickbuttcoffee.com/"),
        ("The Hideout Theatre open mic", "https://hideouttheatre.com/"),
    ],
    "16 social-dance & movement": [
        ("Austin Swing Syndicate", "https://www.austinswingsyndicate.org/"),
        ("Esquina Tango", "https://www.esquinatangoaustin.com/"),
        ("Go Dance Austin", "https://www.godancestudio.com/"),
    ],
    "18 bands & musical acts": [
        ("Black Pumas", "https://www.blackpumas.com/"),
        ("Spoon", "https://www.spoontheband.com/"),
        ("Explosions in the Sky", "https://www.explosionsinthesky.com/"),
    ],
    "19 solo musicians & singer-songwriters": [
        ("Gary Clark Jr.", "https://www.garyclarkjr.com/"),
        ("Shakey Graves", "https://www.shakeygraves.com/"),
        ("Jackie Venson", "https://www.jackievenson.com/"),
    ],
    "20 DJs & electronic artists": [
        ("Kastle", "https://www.kastlemusic.com/"),
        ("Resident Advisor Austin events", "https://ra.co/events/us/austin"),
        ("The Concourse Project calendar", "https://concourseproject.com/calendar/"),
    ],
    "21 comedians & spoken-word": [
        ("Cap City Comedy lineup", "https://www.capcitycomedy.com/"),
        ("Matt Bearden", "https://www.mattbearden.com/"),
        ("Fallout Theater", "https://www.fallouttheater.com/"),
    ],
    "23 visual artists, makers & craft creators": [
        ("Austin Studio Tour", "https://austinstudiotour.org/"),
        ("Canopy Austin", "https://canopyaustin.com/"),
        ("Blue Genie Art Bazaar", "https://www.bluegenieartbazaar.com/"),
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


def main() -> int:
    results = {}
    for segment, cands in CANDIDATES.items():
        print(f"\n=== {segment} ===")
        rows = []
        for name, url in cands:
            row = probe(name, url)
            rows.append(row)
            if row["verdict"] == "UNREACHABLE":
                print(f"  {row['verdict']:20} {name}  ({row['reason']})")
            else:
                redirect = ""
                if row.get("final_url") and row["final_url"].rstrip("/") != url.rstrip("/"):
                    redirect = f"  -> REDIRECTED TO {row['final_url']}"
                print(f"  {row['verdict']:20} {name}  {url}{redirect}")
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
