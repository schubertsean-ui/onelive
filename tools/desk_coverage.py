#!/usr/bin/env python3
"""Walk ONE public desk to the end of its list and print what we hold against it.

    python tools/desk_coverage.py --door austin-chronicle-eventsearch            # fixtures
    python tools/desk_coverage.py --door austin-chronicle-eventsearch --real     # live
    python tools/desk_coverage.py --door austin-chronicle-eventsearch --real --store

Three tables, all three the founder's:

  1. PAGES        every page opened, its status, its rows, and `blocked_reason`
                  when it did not open. A stopped walk always says why.
  2. CATEGORIES   the desk's own category -> our kind, from the committed mapping
                  (`sources/kind_maps/`), plus every category the desk stated
                  that the mapping does NOT cover.
  3. COVERAGE     on_desk | in_store | gap | reason.

THREE MODES, because they answer different questions and must never be confused:

  (default) FIXTURE  the committed pages in tests/fixtures/desk_pages/<door>/
                     stand for the desk's SHAPE. They prove the walker follows
                     pagination, maps kinds and counts honestly. They are NOT a
                     measurement of any live desk, and the footer says so.
  --real             fetch the live desk, politely, one page at a time, and read
                     what comes back. A wall (401/402/403/407/429 or a sign-in
                     redirect) ends the walk through the ingest loop's own
                     authority — we knock once, we never log in.
  --store            additionally ask the database how many of those happenings
                     we already hold (needs ONELIVE_DB_DSN). Without it,
                     `in_store` prints `unverified` — never 0, because "we could
                     not check" must never render as "we have none" (and 0 would
                     make the gap look worse than it is).

This tool REPORTS. It writes nothing: no candidate, no promotion, no user-visible
row, no DB write of any kind. Nothing it prints reaches a person browsing the
site — running it does not change the catalog, and the PR body says so.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.locale.desk_read import Happening  # noqa: E402
from worker.locale.desk_walk import (  # noqa: E402
    _WALL_CODE_RE, DEFAULT_MAX_PAGES, DeskWalk, DeskWalkError, PageFetch, walk,
    walk_table,
)
from worker.locale.kind_map import (  # noqa: E402
    KindMap, KindMapError, load_kind_map, map_for_door, normalize_label,
)
from worker.locale.pack import (  # noqa: E402
    LocalePackError, available_locales, hunt,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_ROOT = os.path.join(REPO_ROOT, "tests", "fixtures", "desk_pages")

USER_AGENT = "OneLiveBot/0.1 (+contact: ops@onelive.example)"

#: What `in_store` prints when we could not ask. Not a number, on purpose:
#: an unchecked store must never render as an empty one (docs/OPERATING_RULES —
#: "couldn't verify" never looks like "passed").
UNVERIFIED = "unverified"


# --------------------------------------------------------------------------
# Fetchers
# --------------------------------------------------------------------------

def fixture_fetcher(door_id: str, *, fixture_root: Optional[str] = None):
    """A fetcher over the committed pages for one door, plus its start URL.

    Any URL the manifest does not list answers 404 — a fixture set that stops
    short says so as a blocked page rather than pretending the desk ended.
    """
    directory = os.path.join(fixture_root or FIXTURE_ROOT, door_id)
    manifest_path = os.path.join(directory, "manifest.json")
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    pages = manifest.get("pages") or {}

    def fetch(url: str) -> PageFetch:
        name = pages.get(url)
        if not name:
            return PageFetch(url=url, status=404)
        with open(os.path.join(directory, name), encoding="utf-8") as page_fh:
            return PageFetch(url=url, status=200, body=page_fh.read(), final_url=url)

    return fetch, manifest.get("start_url"), manifest


def live_fetcher(*, timeout_s: int, min_interval_s: float):
    """A polite live fetcher. Every transport failure becomes a PageFetch the
    walker can classify — never an exception that loses the pages already read.
    """
    try:
        import requests
    except ImportError:  # pragma: no cover - environment-dependent
        def unavailable(url: str) -> PageFetch:
            return PageFetch(url=url, error="requests is not installed")
        return unavailable

    def fetch(url: str) -> PageFetch:
        time.sleep(max(0.0, min_interval_s))
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT},
                                timeout=timeout_s)
        except Exception as exc:  # noqa: BLE001 — a failed page is a row, not a crash
            detail = f"{type(exc).__name__}: {exc}"
            # Classify the FULL text before truncating it for display. A proxy
            # CONNECT denial ("Tunnel connection failed: 403 Forbidden") is a
            # wall, and whether those three digits survive a 200-char cut
            # depends on the length of the URL — which must not decide whether
            # a walled desk is counted as walled.
            return PageFetch(url=url, error=detail[:200],
                             walled=bool(_WALL_CODE_RE.search(detail)))
        return PageFetch(url=url, status=resp.status_code, body=resp.text,
                         final_url=str(resp.url))

    return fetch


# --------------------------------------------------------------------------
# in_store — how many of these happenings we already hold
# --------------------------------------------------------------------------

def _norm_title(value: Optional[str]) -> str:
    return " ".join((value or "").lower().split())


def _day(value: Optional[str]) -> Optional[str]:
    """The calendar day of an ISO timestamp, as the string the row stated it in.

    No timezone conversion: R-090 is open precisely because a listing carries no
    timezone, and converting here would invent one. Same-day comparison is
    therefore done on the date part both sides printed.
    """
    if not value:
        return None
    return str(value)[:10] or None


def store_matches(rows: Sequence[Happening], fetch_rows) -> Dict[str, int]:
    """How many desk rows we already hold, by the honest rule below.

    `fetch_rows(titles) -> [(title, start_time_iso_or_None), ...]` is injected so
    the matching rule is testable without a database.

    THE RULE, stated because a coverage number is worthless without one:
      * a desk row with a DATE matches only a stored row with the same
        normalised title AND the same calendar day (title alone re-times
        recurring listings — the defect R-094/MATCH_COLLISION already records);
      * a desk row with NO date matches on normalised title alone, and that
        match is reported separately (`title_only`) because it is the weaker of
        the two and must not silently shrink the gap.
    """
    titles = sorted({_norm_title(r.title) for r in rows if r.title})
    stored: Dict[str, set] = {}
    for title, start in (fetch_rows(titles) or ()):
        stored.setdefault(_norm_title(title), set()).add(_day(start))
    exact = title_only = 0
    for row in rows:
        key = _norm_title(row.title)
        if key not in stored:
            continue
        day = _day(row.when)
        if day is None:
            title_only += 1
        elif day in stored[key]:
            exact += 1
    return {"matched": exact + title_only, "dated_match": exact,
            "title_only": title_only}


def db_fetch_rows(titles: Sequence[str]) -> List[Tuple[str, Optional[str]]]:
    """Ask the candidate store which of these titles it already holds.

    Parameterised, read-only, and bounded by the titles we are asking about —
    never a table scan, never a string-interpolated query.
    """
    if not titles:
        return []
    import psycopg2  # imported here so the fixture path needs no driver

    from worker.db_config import resolve_dsn
    out: List[Tuple[str, Optional[str]]] = []
    with psycopg2.connect(resolve_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select title, start_time from event_candidate "
                "where lower(btrim(title)) = any(%s)",
                (list(titles),))
            for title, start in cur.fetchall():
                out.append((title, start.isoformat() if start else None))
    return out


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------

def _cell(value) -> str:
    return str(value if value is not None else "—").replace("|", "\\|")


def category_table(one: DeskWalk, kind_map: Optional[KindMap]) -> str:
    """Their category -> our kind, with how many rows each decided."""
    counts: Dict[Tuple[str, str], int] = {}
    for row in one.rows:
        if row.kind_source != "desk_category":
            continue
        counts[(row.category_text or "—", row.kind)] = (
            counts.get((row.category_text or "—", row.kind), 0) + 1)
    lines = ["| desk category (their label) | our kind | rows | evidence |",
             "|---|---|---|---|"]
    for (label, kind), count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0][0])):
        evidence = "—"
        if kind_map is not None:
            # Ids BEFORE labels, the same order `KindMap.resolve` decides in.
            # The other way round misreports the grade whenever a desk's section
            # id also reads as one of our label words ("live-music"): the row was
            # decided by a cited id, and the table would print `language_rule`.
            row = (kind_map.id_rows.get(label)
                   or kind_map.label_rows.get(normalize_label(label)))
            evidence = row.evidence if row else "—"
        lines.append(f"| {_cell(label)} | `{kind}` | {count} | {evidence} |")
    unmapped_rows = sum(1 for r in one.rows if r.kind_source != "desk_category")
    lines.append(f"| _(no mapped category stated)_ | `{'other'}` | {unmapped_rows} "
                 f"| door scope / default |")
    return "\n".join(lines)


def coverage_table(one: DeskWalk, store: Optional[Dict[str, int]],
                   *, live: bool, reason_when_unknown: str) -> str:
    """The founder's table: on_desk | in_store | gap | reason."""
    by_kind: Dict[str, List[Happening]] = {}
    for row in one.rows:
        by_kind.setdefault(row.kind, []).append(row)

    lines = ["| scope | on_desk | in_store | gap | reason |", "|---|---|---|---|---|"]
    for kind in sorted(by_kind, key=lambda k: (-len(by_kind[k]), k)):
        # Per-kind store counts are NOT derivable: a stored candidate carries no
        # kind, so splitting `in_store` by kind would be a guess. The honest
        # store number is the total, and the footnote says why.
        lines.append(f"| kind `{kind}` | {len(by_kind[kind])} | — | — | see TOTAL |")
    on_desk = one.count
    if store is None:
        lines.append(f"| **TOTAL (this desk)** | **{on_desk}** | **{UNVERIFIED}** "
                     f"| **{UNVERIFIED}** | {_cell(reason_when_unknown)} |")
    else:
        held = store["matched"]
        lines.append(
            f"| **TOTAL (this desk)** | **{on_desk}** | **{held}** "
            f"| **{on_desk - held}** | {store['dated_match']} matched on title+day, "
            f"{store['title_only']} on title alone (the desk stated no date) |")
    if not one.exhausted:
        lines.append(
            f"| _walk incomplete_ | — | — | — | stopped because "
            f"`{one.stopped_because}` — on_desk is a FLOOR, not the desk's list |")
    if not live:
        lines.append("| _fixture run_ | — | — | — | counts above are from committed "
                     "shape fixtures, not from the live desk |")
    lines.append("")
    lines.append("`in_store` is only ever filled for the TOTAL row: a stored candidate "
                 "carries a title and a time, not one of our kinds, so a per-kind store "
                 "count would be inferred rather than counted.")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--locale", default="us-tx-capcog",
                    help=f"locale pack holding the door (have: {list(available_locales())})")
    ap.add_argument("--door", required=True, help="door_id to walk")
    ap.add_argument("--real", action="store_true",
                    help="walk the LIVE desk (writes nothing)")
    ap.add_argument("--store", action="store_true",
                    help="fill in_store from the candidate store (needs ONELIVE_DB_DSN)")
    ap.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--min-interval", type=float, default=2.0,
                    help="politeness delay between live page fetches, seconds")
    ap.add_argument("--kind-map", default=None,
                    help="mapping id to apply (default: the one claiming this door)")
    args = ap.parse_args(argv)

    try:
        doors = {d.door_id: d for d in hunt(args.locale)}
    except LocalePackError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    door = doors.get(args.door)
    if door is None:
        print(f"ERROR: no door {args.door!r} in locale {args.locale!r}. "
              f"Have: {sorted(doors)}", file=sys.stderr)
        return 2

    try:
        kind_map = (load_kind_map(args.kind_map) if args.kind_map
                    else map_for_door(door.door_id))
    except KindMapError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    start_url: Optional[str] = None
    manifest = {}
    if args.real:
        fetch = live_fetcher(timeout_s=args.timeout, min_interval_s=args.min_interval)
    else:
        try:
            fetch, start_url, manifest = fixture_fetcher(door.door_id)
        except OSError as exc:
            print(f"ERROR: no committed fixtures for door {door.door_id!r} ({exc}). "
                  f"Run with --real, or add "
                  f"tests/fixtures/desk_pages/{door.door_id}/manifest.json",
                  file=sys.stderr)
            return 2

    try:
        one = walk(door, fetch, max_pages=args.max_pages, start_url=start_url,
                   kind_map=kind_map)
    except DeskWalkError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    store = None
    store_reason = ("ONELIVE_DB_DSN is not set in this environment, so the store "
                    "was never asked — `unverified`, never 0")
    if args.store:
        if not os.getenv("ONELIVE_DB_DSN"):
            print("ERROR: --store needs ONELIVE_DB_DSN", file=sys.stderr)
            return 2
        try:
            store = store_matches(one.rows, db_fetch_rows)
        except Exception as exc:  # noqa: BLE001 — a store we could not read is unverified, not empty
            store_reason = f"store read failed ({type(exc).__name__}: {exc})"[:200]

    mode = "LIVE" if args.real else "FIXTURE"
    print(f"# Desk coverage — `{door.door_id}` ({door.door_type}, via {door.via}) "
          f"— {mode} walk")
    print()
    print(f"Start: {one.start_url}")
    print(f"Mapping: {kind_map.map_id if kind_map else 'none — kinds come from the door scope'}"
          f"{f' ({len(kind_map.rows)} committed rows)' if kind_map else ''}")
    print(f"Stopped because: `{one.stopped_because}`"
          + ("" if one.exhausted else "  ← the desk's list may continue past this"))
    print()
    print("## 1. Pages")
    print()
    print(walk_table([one]))
    print()
    print(f"{len(one.pages)} page(s) opened, {one.pages_read} read, "
          f"{one.pages_blocked} blocked. {one.rows_seen} row(s) printed, "
          f"{one.count} unique happening(s) "
          f"({one.duplicates_across_pages} repeat(s) across pages, "
          f"{one.merged_readings} card(s) read twice on one page and merged, "
          f"{one.skipped_untitled} block(s) with no title). "
          f"{one.dated} carry a date the page stated; {one.count - one.dated} have "
          f"an honest hole on the clock.")
    if one.notes:
        print()
        for note in one.notes:
            print(f"- {note}")
    print()
    print("## 2. Categories — their label, our kind")
    print()
    print(category_table(one, kind_map))
    if one.unmapped_categories:
        print()
        print(f"**Unmapped ({len(one.unmapped_categories)})**, stated by the desk and "
              f"not in the committed table — these rows kept the door's kind, and the "
              f"table is completed from these words, never from memory: "
              + ", ".join(f"`{c}`" for c in one.unmapped_categories))
    print()
    print("## 3. Coverage")
    print()
    print(coverage_table(one, store, live=args.real,
                         reason_when_unknown=store_reason))
    print()
    if not args.real:
        note = manifest.get("note")
        print("**Fixture run.** " + (note or "Counts come from committed shape "
                                             "fixtures, not from the live desk."))
    print()
    print("This tool wrote nothing: no candidate, no promotion, no user-visible row. "
          "Reading a desk does not change the catalog — wiring these rows into the "
          "pipeline is a separate, named step.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
