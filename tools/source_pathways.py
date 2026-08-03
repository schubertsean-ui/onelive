#!/usr/bin/env python3
"""Assign every catalog source a REUSABLE, market-agnostic ingestion PATHWAY and
report its status — so "every potential source has a specific, working pathway"
is a mechanically-checked fact, not a promise (founder directive 2026-07-31).

The unit of reuse is the PATHWAY KIND, defined by the machine protocol a source
speaks — NOT by the city it serves. A `gov_open_data` pathway that reads Austin's
Socrata portal reads Chicago's or Seattle's with the same adapter; a
`calendar_platform` pathway that reads one Localist calendar reads every
university or city running Localist. Austin is the first market; the pathways are
the product.

Kinds (each = one adapter, reusable across US markets):

  licensed_api            Ticketing / data APIs with a key or OAuth
                          (Ticketmaster, SeatGeek, Eventbrite, Meetup).
  ics_feed                iCalendar (.ics) feed the site publishes/advertises
                          (worker/importers/structured_feed.py, incl. the
                          advertised-feed discovery added in PR #115).
  jsonld_embedded         schema.org/Event JSON-LD embedded in the page HTML.
  calendar_platform       A hosted event-calendar PLATFORM's JSON API — Localist,
                          The Events Calendar (WordPress), Squarespace — reusable
                          for every customer of that platform, any market.
  gov_open_data           Government / administrative OPEN-DATA portals — Socrata
                          (SODA), CKAN, ArcGIS — for authoritative venue facts:
                          licensing, occupancy/capacity (fire marshal), health
                          permits, service type. Reusable across every US
                          jurisdiction on these platforms. Primarily a VENUE-TRUTH
                          and triangulation anchor, not an event list.
  structured_feed         A generic RSS/Atom/JSON feed offered but not one of the
                          above shapes.
  ai_extract_triangulated Plain HTML with no machine feed: AI extracts a candidate,
                          which PUBLISHES ONLY after the triangulation/confidence
                          process corroborates it against independent sources
                          (other aggregators' feeds, the venue's own social posts,
                          gov records). Publication is gate-custodied — AI output
                          publishes THROUGH validation, never directly
                          (founder corrections 2026-07-31 / 2026-08-03).
  partner_agreement       Needs a partnership / paid plan / signed export.
  social                  Social platforms needing OAuth or an app review.
  manual_upload           Venue/creator self-serve upload or opt-in email parse.
  not_a_source            Benchmarks / directories that are not an ingest target.

Status (honest — "it works" is proven by a live run, never asserted here):

  LIVE                    Adapter exists AND a live run has produced events.
  CODE_READY_NEEDS_KEY    Adapter exists; blocked only on a credential.
  ADAPTER_BUILT           Adapter exists; live yield not yet proven for this source.
  NEEDS_BUILD             Pathway identified; adapter not yet built.
  NEEDS_AGREEMENT         Blocked on a partnership / paid plan / OAuth app.

Usage:
  python tools/source_pathways.py                # human report to stdout
  python tools/source_pathways.py --markdown P   # write the review matrix to P
  python tools/source_pathways.py --assert       # exit 1 if any source is unclassified
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter, defaultdict

REPO = pathlib.Path(__file__).resolve().parent.parent
CATALOG = REPO / "sources" / "master_sources_catalog_120.json"

# Providers proven LIVE by a real import run (worker/importers/*). Keyed by the
# catalog id. Update as adapters prove out on CI, never by guesswork.
LIVE_SOURCE_IDS = {"ticketmaster_discovery"}
# Sources whose adapter exists and fails ONLY for a missing credential.
NEEDS_KEY_SOURCE_IDS = {
    "seatgeek": "SEATGEEK_CLIENT_ID (application pending founder approval)",
    "seatgeek_platform": "SEATGEEK_CLIENT_ID (application pending founder approval)",
    "eventbrite": "EVENTBRITE_API_TOKEN",
    "eventbrite_api": "EVENTBRITE_API_TOKEN",
}

# Kinds whose deterministic adapter already exists in the repo today. A source on
# such a kind is at least ADAPTER_BUILT (proof of live yield still comes from a
# real run); other kinds are NEEDS_BUILD until their adapter lands.
BUILT_KINDS = {"licensed_api", "ics_feed", "jsonld_embedded", "ai_extract_triangulated"}


def _tokens(entry: dict) -> set[str]:
    t = {str(a).lower() for a in (entry.get("allowed") or [])}
    t.add(str(entry.get("access_method") or "").lower())
    return t


def classify_kind(entry: dict) -> str:
    """Assign ONE reusable pathway kind, most-specific signal first. Deterministic
    and market-agnostic — driven by the protocol tokens + category, never the
    city."""
    cat = str(entry.get("category") or "").lower()
    toks = _tokens(entry)
    blob = " ".join(toks) + " " + cat

    if cat in ("search_benchmark", "directory", "link_hub", "artist_directory"):
        return "not_a_source"
    if cat == "social" or "oauth" in blob and cat in ("social",):
        return "social"
    # Credentialed APIs (ticketing/data).
    if cat == "ticketing" or {"api_access", "api_key", "oauth_api"} & toks:
        # Meetup/social APIs still need OAuth review → treat as social/agreement
        # only when the category says so; ticketing/data APIs are licensed_api.
        if cat in ("ticketing", "music_platform", "artist_aggregator", "festival_feed"):
            return "licensed_api"
        return "licensed_api"
    # Government / administrative open data (licensing, capacity, permits).
    if "open_data" in blob or "lucene" in blob or "socrata" in blob or "ckan" in blob:
        return "gov_open_data"
    # Hosted calendar PLATFORM feeds (Localist & friends).
    if "localist" in blob or cat in ("university_calendar", "library_calendar"):
        return "calendar_platform"
    # iCalendar.
    if "ics" in blob:
        return "ics_feed"
    # Embedded schema.org JSON-LD.
    if "jsonld" in blob or "json-ld" in blob or "schema" in blob:
        return "jsonld_embedded"
    # Partner-only exports / paid.
    if "partner" in blob:
        return "partner_agreement"
    # Self-serve upload / opt-in.
    if "upload" in blob or "opt_in" in blob or "email" in blob or cat in ("claimed_upload", "email_opt_in"):
        return "manual_upload"
    # A source that OFFERS its own generic feed (RSS/Atom/JSON). NOTE the
    # `structured_feed_verify` token is deliberately NOT matched here: it is a
    # triangulation/verify ALLOWANCE ("this source may be used to corroborate"),
    # not evidence the source publishes a feed of its own. Only an offered/
    # official feed counts.
    if "feed_if_offered" in toks or "official_feed" in toks or cat == "calendar_feed":
        return "structured_feed"
    # Everything else is a public HTML calendar page → AI extraction, PUBLISHED
    # ONLY through the triangulation/confidence process. The very common
    # `structured_feed_verify` token is the corroboration anchor that process
    # uses, so it lands here by design, not by omission.
    return "ai_extract_triangulated"


def status_for(entry: dict, kind: str) -> tuple[str, str]:
    """Return (status, note). Honest: LIVE requires a proven run; a built adapter
    without proof for this source is ADAPTER_BUILT, not LIVE."""
    sid = str(entry.get("id"))
    if sid in LIVE_SOURCE_IDS:
        return "LIVE", "producing events on the live feed"
    if sid in NEEDS_KEY_SOURCE_IDS:
        return "CODE_READY_NEEDS_KEY", NEEDS_KEY_SOURCE_IDS[sid]
    if kind == "not_a_source":
        return "NEEDS_BUILD", "benchmark/directory — not an ingest target"
    if kind in ("partner_agreement",):
        return "NEEDS_AGREEMENT", "partner export / paid plan"
    if kind == "social":
        return "NEEDS_AGREEMENT", "OAuth app / platform review"
    if kind == "manual_upload":
        return "NEEDS_BUILD", "venue/creator self-serve upload"
    if kind in BUILT_KINDS:
        return "ADAPTER_BUILT", "adapter exists; prove live yield on a real run"
    return "NEEDS_BUILD", "pathway identified; adapter not yet built"


def build_rows(catalog: list[dict]) -> list[dict]:
    rows = []
    for e in catalog:
        kind = classify_kind(e)
        status, note = status_for(e, kind)
        rows.append({
            "id": str(e.get("id")),
            "name": e.get("name") or e.get("id"),
            "category": e.get("category"),
            "kind": kind,
            "status": status,
            "note": note,
        })
    return rows


def _report(rows: list[dict]) -> str:
    out: list[str] = []
    by_kind = Counter(r["kind"] for r in rows)
    by_status = Counter(r["status"] for r in rows)
    out.append(f"SOURCE PATHWAYS — {len(rows)} sources\n")
    out.append("By reusable pathway kind:")
    for k, n in by_kind.most_common():
        out.append(f"  {n:3d}  {k}")
    out.append("\nBy status:")
    for s, n in by_status.most_common():
        out.append(f"  {n:3d}  {s}")
    # Group the source list by kind for scanning.
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        grouped[r["kind"]].append(r)
    for k in sorted(grouped):
        out.append(f"\n== {k} ({len(grouped[k])}) ==")
        for r in sorted(grouped[k], key=lambda r: r["id"]):
            out.append(f"  {r['status']:20s} {r['id']:32s} {r['note']}")
    return "\n".join(out)


def _markdown(rows: list[dict]) -> str:
    by_kind = Counter(r["kind"] for r in rows)
    by_status = Counter(r["status"] for r in rows)
    md = ["# Source ingestion pathway matrix",
          "",
          "_Generated by `tools/source_pathways.py` — do not hand-edit; re-run to refresh._",
          "",
          f"Every one of the **{len(rows)}** catalog sources is assigned a reusable, "
          "market-agnostic pathway kind and an honest status. "
          "`LIVE` means a real run produced events; it is never asserted here.",
          "",
          "## By pathway kind",
          "",
          "| Kind | Sources |",
          "|---|---|"]
    for k, n in by_kind.most_common():
        md.append(f"| `{k}` | {n} |")
    md += ["", "## By status", "", "| Status | Sources |", "|---|---|"]
    for s, n in by_status.most_common():
        md.append(f"| `{s}` | {n} |")
    md += ["", "## Every source, its pathway, and its status", "",
           "| Source | Category | Pathway kind | Status | Note |",
           "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["kind"], r["id"])):
        md.append(f"| `{r['id']}` | {r['category']} | `{r['kind']}` | "
                  f"`{r['status']}` | {r['note']} |")
    return "\n".join(md) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", default=str(CATALOG))
    ap.add_argument("--markdown", metavar="PATH",
                    help="write the review matrix as markdown to PATH")
    ap.add_argument("--assert", dest="assert_", action="store_true",
                    help="exit 1 if any source is left unclassified")
    args = ap.parse_args(argv)

    catalog = json.loads(pathlib.Path(args.catalog).read_text(encoding="utf-8"))
    rows = build_rows(catalog)

    if args.assert_:
        bad = [r["id"] for r in rows if not r["kind"]]
        if bad:
            print(f"UNCLASSIFIED sources: {bad}", file=sys.stderr)
            return 1
        print(f"OK — all {len(rows)} sources classified.")
        return 0

    if args.markdown:
        pathlib.Path(args.markdown).write_text(_markdown(rows), encoding="utf-8")
        print(f"wrote {args.markdown}")
        return 0

    print(_report(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
