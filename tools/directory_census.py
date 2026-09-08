#!/usr/bin/env python3
"""Walk founder-named Place/Actor directories and write venue/artist rows.

    python3 tools/directory_census.py                  # fixtures, dry plan
    python3 tools/directory_census.py --real --dry-run # live pages, no write
    python3 tools/directory_census.py --real --write   # live pages -> venue/artist

Entity Split Law §3.3: directories write the universe, not Tonight.
No dates. No event insert. identity_patterns.json is not touched.

--write requires --real and ONELIVE_DB_DSN. Fixtures never reach production.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional, Sequence

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.locale_pack.directory_read import (  # noqa: E402
    DirectoryEntity, DirectoryRead, DirectoryReadError, DirectorySpec,
    load_directories, read, spec_for,
)

FIXTURE_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "fixtures", "directory_pages",
)


class CensusError(ValueError):
    """The census cannot run as asked."""


def fixture_html(directory_id: str) -> str:
    path = os.path.join(FIXTURE_ROOT, f"{directory_id}.html")
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError as exc:
        raise CensusError(
            f"no fixture at {path}. A fixture run without a committed page is a guess."
        ) from exc


def fetch_live(url: str) -> str:
    """One polite GET. A wall is OUR failure, never an empty directory."""
    import requests
    try:
        response = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "1Live-directory-census/1 (+https://1live.co)"},
        )
    except requests.RequestException as exc:
        raise CensusError(f"fetch_error for {url}: {exc}") from exc
    if response.status_code in (401, 402, 403, 407, 429):
        raise CensusError(
            f"WALL {response.status_code} at {url} — list UNKNOWN, not empty. "
            "Do not bypass. Queue claim."
        )
    if response.status_code >= 400:
        raise CensusError(
            f"HTTP {response.status_code} at {url} is WE failed, not 'no venues'"
        )
    return response.text


def plan_table(reads: Sequence[DirectoryRead]) -> str:
    lines = [
        "| directory_id | kind | rows | nameless | other_links |",
        "|---|---|---:|---:|---:|",
    ]
    for one in reads:
        kind = one.entities[0].kind if one.entities else "—"
        lines.append(
            f"| `{one.directory_id}` | {kind} | {one.count} | "
            f"{one.skipped_nameless} | {one.skipped_other_links} |"
        )
    lines.append("")
    lines.append(
        "These rows are Places/Actors. They do not publish on /tonight."
    )
    return "\n".join(lines)


def write_entities(entities: Sequence[DirectoryEntity]) -> dict:
    dsn = os.environ.get("ONELIVE_DB_DSN", "").strip()
    if not dsn:
        raise CensusError("--write needs ONELIVE_DB_DSN")
    import psycopg2
    from worker.resolve_entities import resolve_artist_ids, resolve_venue_id

    created_venues = 0
    created_artists = 0
    reused = 0
    conn = psycopg2.connect(dsn)
    try:
        with conn:
            with conn.cursor() as cur:
                for entity in entities:
                    if entity.kind == "place":
                        cur.execute(
                            "select venue_id from venue where lower(name)=lower(%s) "
                            "and (city is null or lower(city)=lower(%s)) limit 1",
                            (entity.name, entity.city or ""),
                        )
                        existed = cur.fetchone() is not None
                        resolve_venue_id(cur, entity.name, entity.city or "Austin")
                        if existed:
                            reused += 1
                        else:
                            created_venues += 1
                    elif entity.kind == "actor":
                        cur.execute(
                            "select artist_id from artist where lower(name)=lower(%s) limit 1",
                            (entity.name,),
                        )
                        existed = cur.fetchone() is not None
                        resolve_artist_ids(cur, [entity.name])
                        if existed:
                            reused += 1
                        else:
                            created_artists += 1
    finally:
        conn.close()
    return {
        "created_venues": created_venues,
        "created_artists": created_artists,
        "reused": reused,
        "total": len(entities),
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--real", action="store_true",
                    help="Fetch live directory pages. Default is fixtures.")
    ap.add_argument("--write", action="store_true",
                    help="Write venue/artist rows. Requires --real and DSN.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the plan and write nothing (default).")
    ap.add_argument("--directory", action="append", default=[],
                    help="directory_id to walk. Default: every row in the table.")
    args = ap.parse_args(argv)

    if args.write and not args.real:
        print("REFUSED: --write without --real would put fixture names in production.",
              file=sys.stderr)
        return 2
    if args.write and args.dry_run:
        print("REFUSED: --write and --dry-run together.", file=sys.stderr)
        return 2

    try:
        table = load_directories()
        wanted = args.directory or [s.directory_id for s in table]
        reads: List[DirectoryRead] = []
        for directory_id in wanted:
            spec = spec_for(directory_id, table)
            html = fetch_live(spec.url) if args.real else fixture_html(spec.directory_id)
            reads.append(read(spec, html, base_url=spec.url))
    except (DirectoryReadError, CensusError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("# Directory census")
    print()
    print("LIVE" if args.real else "FIXTURE")
    print()
    print(plan_table(reads))
    print()
    for one in reads:
        print(f"## {one.directory_id}")
        for entity in one.entities:
            city = f" · {entity.city}" if entity.city else ""
            print(f"- {entity.name}{city} — {entity.url}")
        for note in one.notes:
            print(f"- note: {note}")
        print()

    entities = [e for one in reads for e in one.entities]
    if args.write:
        try:
            stats = write_entities(entities)
        except CensusError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2
        print(
            f"Wrote venues={stats['created_venues']} "
            f"artists={stats['created_artists']} reused={stats['reused']} "
            f"of {stats['total']}."
        )
        print("Tonight count is unchanged by this tool.")
    else:
        print(f"Dry run. Would write {len(entities)} Place/Actor rows. Nothing stored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
