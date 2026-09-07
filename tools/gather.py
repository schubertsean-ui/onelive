"""Dry-run one gather job for a typed place, and print what it would do.

    python tools/gather.py --place "Round Rock, TX" --max-pages 6

This is the founder-facing side of `worker/locale/gather.py`: it types a place
the way a visitor would, runs ONE bounded tick over the COMMITTED page fixtures,
and prints the go-live numbers (§4 step 5) plus every door it did not open and
why.

THERE IS NO `--write` FLAG, AND NO LIVE FETCH. Not "off by default" — absent.
This tool exists to answer "what would this place's first tick do?" on a laptop
or in CI, and a rehearsal that can reach production by adding one word is not a
rehearsal. Writing is `tools/desk_ingest.py`'s job, on an authorized head, after
a founder reads a table like this one. A test asserts the flag's absence, so it
cannot come back by accident.

Fixtures, not the network: every page comes from `tests/fixtures/desk_pages/`.
A door with no committed pages is REPORTED by name as a gap in the REHEARSAL —
never as a desk with nothing on.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.locale.desk_walk import PageFetch  # noqa: E402
from worker.locale.gather import (  # noqa: E402
    TRIGGERS,
    GatherError,
    Lead,
    Registry,
    Tick,
    door_table,
    gather,
    summary_table,
)
from worker.locale.pack import Door  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_ROOT = os.path.join(REPO, "tests", "fixtures", "desk_pages")
CATALOG = os.path.join(REPO, "sources", "master_sources_catalog_120.json")


def fixture_pages() -> Tuple[Dict[str, Tuple[str, str]], Dict[str, str]]:
    """Every committed page, indexed by the URL its manifest files it under.

    Returns `(url -> (directory, filename), door_id -> start_url)`. One index
    across every door, because a gather walks several desks and hands them all
    ONE fetcher.
    """
    by_url: Dict[str, Tuple[str, str]] = {}
    starts: Dict[str, str] = {}
    if not os.path.isdir(FIXTURE_ROOT):
        return by_url, starts
    for door_id in sorted(os.listdir(FIXTURE_ROOT)):
        directory = os.path.join(FIXTURE_ROOT, door_id)
        manifest_path = os.path.join(directory, "manifest.json")
        if not os.path.isfile(manifest_path):
            continue
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
        for url, name in (manifest.get("pages") or {}).items():
            by_url[url] = (directory, name)
        if manifest.get("start_url"):
            starts[door_id] = manifest["start_url"]
    return by_url, starts


def fixture_fetcher(by_url: Dict[str, Tuple[str, str]]):
    """A fetcher over the committed pages. A URL nobody committed answers with
    an explicit rehearsal gap rather than a 200 and an empty list.
    """
    def fetch(url: str) -> PageFetch:
        hit = by_url.get(url)
        if hit is None:
            return PageFetch(
                url=url,
                error="no committed fixture for this page — a gap in the "
                      "REHEARSAL, not a statement about the desk")
        directory, name = hit
        with open(os.path.join(directory, name), encoding="utf-8") as fh:
            return PageFetch(url=url, status=200, body=fh.read(), final_url=url)
    return fetch


def load_catalog() -> List[dict]:
    with open(CATALOG, encoding="utf-8") as fh:
        return json.load(fh)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--place", required=True,
                    help="the place as a person would type it, e.g. \"Round Rock, TX\"")
    ap.add_argument("--trigger", default="typed_place", choices=list(TRIGGERS),
                    help="what started this job. `page_load` is not offered: a "
                         "page load must never start a gather (Locale Launch §6a)")
    ap.add_argument("--max-pages", type=int, default=12,
                    help="page bound for the whole tick, across every door")
    ap.add_argument("--max-seconds", type=float, default=60.0,
                    help="wall-clock bound for the whole tick")
    ap.add_argument("--max-dollars", type=float, default=0.50,
                    help="spend bound for the whole tick")
    ap.add_argument("--timezone", default=None,
                    help="IANA clock for a place with no pack (a geocode's "
                         "answer). Without it a pack-less place is HELD, never "
                         "given a guessed night")
    ap.add_argument("--lead", action="append", default=[], metavar="URL",
                    help="a search LEAD to propose as a door. A lead is a URL, "
                         "never a listing; repeat the flag for several")
    ap.add_argument("--json", action="store_true",
                    help="print the numbers as JSON instead of tables")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    by_url, starts = fixture_pages()
    fetch = fixture_fetcher(by_url)

    def start_url_for(door: Door) -> Optional[str]:
        return starts.get(door.door_id)

    tick = Tick(max_pages=args.max_pages, max_seconds=args.max_seconds,
                max_dollars=args.max_dollars)
    leads = tuple(Lead(query=f"lead for {args.place}", url=u) for u in args.lead)

    try:
        report = gather(
            args.place, fetch=fetch, tick=tick, trigger=args.trigger,
            registry=Registry(), catalog=load_catalog(), leads=leads,
            timezone_id=args.timezone, start_url_for=start_url_for)
    except GatherError as exc:
        print(f"gather refused: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({
            "place_id": report.place_id,
            "pack": report.pack_id,
            "grammar": report.grammar_source,
            "queries": list(report.queries),
            "timezone": report.timezone_id,
            "rows_n": report.rows_n,
            "dated_n": report.dated_n,
            "placed_n": report.placed_n,
            "mash_n": report.mash_n,
            "403_n": report.walls_n,
            "held_n": report.held_n,
            "publishable_n": report.publishable_n,
            "state": report.state,
            "stopped_because": report.stopped_because,
            "held_reason": report.held_reason,
            "skipped": [{"door_id": s.door_id, "class": s.source_class,
                         "why": s.why} for s in report.skipped],
        }, indent=2, sort_keys=True))
        return 0

    print(f"# Gather (DRY RUN) — {report.display}\n")
    print(summary_table(report))
    print(f"\n{report.honest_line()}\n")
    print("## Doors\n")
    print(door_table(report))
    if report.queries:
        print("\n## Query grammar (bounded, not a crawl)\n")
        for q in report.queries[:20]:
            print(f"  - {q}")
        if len(report.queries) > 20:
            print(f"  ... and {len(report.queries) - 20} more")
    if report.notes:
        print("\n## Notes\n")
        for note in report.notes:
            print(f"  - {note}")
    print("\nNothing was written. This tool has no write path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
