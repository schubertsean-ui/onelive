#!/usr/bin/env python3
"""Resolve harvested Eventbrite EVENT ids to their ORGANIZERS via the official API.

Second leg of founder-approved discovery path #1: venue/festival pages link
individual Eventbrite events ("/e/...-<id>"); the organizer behind each event
comes from Eventbrite's DOCUMENTED API (GET /v3/events/{id}/?expand=organizer)
using the founder-minted token — the product Eventbrite built for exactly this,
no page scraping, no circumvention. Output is organizer candidates for HUMAN
review before anything is committed (same custody as every discovery lane).

Input: the JSON file tools/harvest_eventbrite_links.py wrote (reads its
"event_ids" list), or explicit --event-ids. Requires EVENTBRITE_TOKEN in the
environment. Bounded (--max-events), polite (1s delay).

Fail-loud contract: a missing token or zero input ids exits 2 (usage); ALL
lookups failing exits 3 (auth/network problem — never an empty green). Partial
failures are reported per-id and the successes still emit.

Usage:
  python tools/resolve_eventbrite_event_orgs.py --harvest harvest.json
  python tools/resolve_eventbrite_event_orgs.py --event-ids 123,456
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request

API = "https://www.eventbriteapi.com/v3/events/{eid}/?expand=organizer"


def fetch_event(eid: str, token: str, timeout: int = 20) -> dict:
    """One documented-API event lookup, organizer expanded."""
    req = urllib.request.Request(
        API.format(eid=eid),
        headers={"Authorization": f"Bearer {token}",
                 "User-Agent": "1LiveSourceDiscovery/1.0 (+https://1live.co)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def organizer_of(event: dict) -> dict | None:
    """The organizer candidate an API event payload carries, or None."""
    org = event.get("organizer") or {}
    oid = str(org.get("id") or "").strip()
    if not oid:
        return None
    return {"org_id": oid,
            "name": (org.get("name") or "").strip() or "(unnamed organizer)",
            "via_event": str(event.get("id") or "")}


def main(argv=None) -> int:
    """Resolve event ids -> organizer candidates through the official API."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--harvest", help="harvest JSON file (event_ids read from it)")
    ap.add_argument("--event-ids", default="",
                    help="comma-separated Eventbrite event ids")
    ap.add_argument("--max-events", type=int, default=50,
                    help="cap on API lookups this run")
    args = ap.parse_args(argv)

    token = os.environ.get("EVENTBRITE_TOKEN", "").strip()
    if not token:
        print("EVENTBRITE_TOKEN missing — the official API is the only access "
              "method this tool uses", file=sys.stderr)
        return 2

    ids: list[str] = []
    if args.harvest:
        with open(args.harvest, encoding="utf-8") as fh:
            harvest = json.load(fh)
        ids.extend(str(e["event_id"]) for e in harvest.get("event_ids", []))
    ids.extend(i.strip() for i in args.event_ids.split(",") if i.strip())
    # De-dupe, preserve order (most-corroborated first from the harvest).
    seen: set[str] = set()
    ids = [i for i in ids if not (i in seen or seen.add(i))]
    if not ids:
        print("no event ids supplied (empty harvest and no --event-ids)",
              file=sys.stderr)
        return 2
    ids = ids[: args.max_events]

    organizers: dict[str, dict] = {}
    failures = 0
    for eid in ids:
        try:
            ev = fetch_event(eid, token)
        except Exception as exc:  # noqa: BLE001 — per-id report; all-fail exits 3 below
            failures += 1
            print(f"event {eid}: lookup failed ({exc})", file=sys.stderr)
            continue
        cand = organizer_of(ev)
        if cand:
            entry = organizers.setdefault(
                cand["org_id"], {"org_id": cand["org_id"], "name": cand["name"],
                                 "via_events": []})
            entry["via_events"].append(cand["via_event"])
        time.sleep(1)

    if failures == len(ids):
        print(f"ALL {failures} lookups failed — token/auth/network problem; "
              "failing loud (never an empty green).", file=sys.stderr)
        return 3

    out = {"events_requested": len(ids), "events_failed": failures,
           "organizers": sorted(organizers.values(),
                                key=lambda o: -len(o["via_events"]))}
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    print()
    print(f"resolve: {len(out['organizers'])} organizer(s) from "
          f"{len(ids) - failures} of {len(ids)} event id(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
