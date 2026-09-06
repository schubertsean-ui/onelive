#!/usr/bin/env python3
"""Follow a desk's permalinks to their own pages and print what THEY state.

    python tools/event_page_table.py                    # fixtures, 20 permalinks
    python tools/event_page_table.py --real             # live (needs egress)
    python tools/event_page_table.py --door do512-today --limit 10

Founder, Ticket C, verbatim: "a Chronicle (or Do512) /event/… page becomes a
Happening with when + place_text when THAT page states them. No invented dates.
No mash." (Quoted here rather than in `worker/locale/`, where a committed gate
keeps brand literals out so a locale stays data.)

Ticket C's artifact — the founder's four columns:

    url | dated? | place? | blocked reason

Ticket B (`worker/locale/desk_read.py`) split each list page into rows and gave
each row its own address. This tool follows those addresses, SAME HOST ONLY, one
knock each, and asks `worker.locale.event_page.read_event_page` what the page
itself states. A date the page did not state is a hole; a place it did not state
is a hole; a wall is a hole with its reason printed and the door queued for the
human claim path. Nothing is guessed and nothing is filled from a neighbouring
page — that is the whole point of the table.

TWO MODES, never confused:

  (default) FIXTURE  the committed pages under tests/fixtures/event_pages/<door>/
                     stand for the SHAPE of a desk's event pages. They prove the
                     reader fills what is stated and holes what is not. They are
                     NOT a measurement of any live desk, and the footer says so
                     on every run.
  --real             fetch the live pages, politely, one at a time. A wall
                     (401/402/403/407/429 or a sign-in redirect) is recorded
                     through the ingest loop's own authority — we knock once, we
                     never log in, we never retry.

This tool REPORTS. It writes nothing: no candidate, no promotion, no DB write of
any kind. Running it does not change the catalog or the live site.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.desk_coverage import (  # noqa: E402
    USER_AGENT, fixture_fetcher, live_fetcher,
)
from worker.locale.desk_read import Happening  # noqa: E402
from worker.locale.desk_walk import PageFetch, walk  # noqa: E402
from worker.locale.event_page import FollowRun, follow  # noqa: E402
from worker.locale.pack import load_pack  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_ROOT = os.path.join(REPO_ROOT, "tests", "fixtures", "event_pages")
DEFAULT_DOORS = ("austin-chronicle-eventsearch", "do512-today")
DEFAULT_LIMIT = 20


def event_fixture_fetcher(door_id: str, *, fixture_root: Optional[str] = None):
    """A fetcher over the committed EVENT pages for one door.

    A url the manifest lists under `walls` answers with that status, so the
    blocked path is exercised by the same committed data as the readable one.
    Any url the manifest does not list at all answers 404 — a fixture set that
    stops short says so, rather than pretending the desk published nothing.
    """
    directory = os.path.join(fixture_root or FIXTURE_ROOT, door_id)
    with open(os.path.join(directory, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    pages: Dict[str, str] = manifest.get("pages") or {}
    walls: Dict[str, int] = manifest.get("walls") or {}

    def fetch(url: str) -> PageFetch:
        if url in walls:
            status = walls[url]
            return PageFetch(url=url, status=status, final_url=url,
                             error=f"HTTP {status}")
        name = pages.get(url)
        if not name:
            return PageFetch(url=url, status=404, final_url=url, error="HTTP 404")
        with open(os.path.join(directory, name), encoding="utf-8") as page_fh:
            return PageFetch(url=url, status=200, body=page_fh.read(), final_url=url)

    return fetch, manifest


def rows_for(door_id: str, *, real: bool, timeout_s: int, min_interval_s: float,
             max_pages: int) -> Tuple[List[Happening], List[str]]:
    """The Ticket B rows for one door — the permalinks this tool follows."""
    pack = load_pack("us-tx-capcog")
    door = next((d for d in pack.doors if d.door_id == door_id), None)
    if door is None:
        raise SystemExit(f"ERROR: no door {door_id!r} in the us-tx-capcog pack")
    notes: List[str] = []
    if real:
        fetch = live_fetcher(timeout_s=timeout_s, min_interval_s=min_interval_s)
        start = None
    else:
        fetch, start, _manifest = fixture_fetcher(door_id)
    result = walk(door, fetch, start_url=start, max_pages=max_pages)
    if result.stopped_because and result.stopped_because != "no_next_link":
        notes.append(f"{door_id}: list walk stopped on {result.stopped_because}")
    return list(result.rows), notes


def collect(doors: Sequence[str], *, limit: int, real: bool = False,
            timeout_s: int = 20, min_interval_s: float = 1.0,
            max_pages: int = 5, read_ics: bool = True
            ) -> Tuple[List[Tuple[str, FollowRun]], List[str]]:
    """Walk each door's list, then follow its permalinks — the whole artifact.

    One function so the tool and its test guarantee the same thing: the table
    the founder reads is the table the test checks.
    """
    runs: List[Tuple[str, FollowRun]] = []
    notes: List[str] = []
    remaining = max(0, limit)
    for door_id in doors:
        if remaining <= 0:
            break
        rows, door_notes = rows_for(door_id, real=real, timeout_s=timeout_s,
                                    min_interval_s=min_interval_s,
                                    max_pages=max_pages)
        notes.extend(door_notes)
        if real:
            fetch = live_fetcher(timeout_s=timeout_s, min_interval_s=min_interval_s)
        else:
            try:
                fetch, _manifest = event_fixture_fetcher(door_id)
            except FileNotFoundError:
                notes.append(f"{door_id}: no committed event-page fixtures "
                             f"(tests/fixtures/event_pages/{door_id}/) — skipped")
                continue
        run = follow(rows, fetch, limit=remaining, read_ics=read_ics)
        remaining -= len(run.visits)
        runs.append((door_id, run))
    return runs, notes


def render(runs: Sequence[Tuple[str, FollowRun]], *, mode: str, limit: int) -> str:
    """The founder's table across every door, capped at `limit` rows total."""
    lines = [f"### Ticket C — same-host event page -> date + place ({mode})",
             "",
             "| # | url | dated? | place? | blocked reason |",
             "|---:|---|:---|:---|---|"]
    n = 0
    totals = {"dated": 0, "placed": 0, "blocked": 0, "walled": 0,
              "off_host": 0, "filled_when": 0, "filled_place": 0, "conflict": 0,
              "not_knocked": 0, "nulled_when": 0, "rows_dated": 0}
    for door_id, run in runs:
        for v in run.visits:
            if n >= limit:
                break
            n += 1
            st = v.statement
            if v.blocked:
                dated = place = "—"
            else:
                if v.when_conflict:
                    # Founder ruling 2026-09-06: the desk's two pages disagree,
                    # so the row has NO night. Printing the page's date here
                    # would show a night no row carries.
                    dated = (f"no — CONTESTED, night removed "
                             f"(list {v.listed_when} vs page {v.page_when})")
                elif st and st.when:
                    dated = f"yes — {st.when} ({st.when_source})"
                elif st and st.clock_only:
                    dated = "no — clock only, no night stated"
                elif st and st.ambiguous_dates:
                    dated = f"no — {len(st.ambiguous_dates)} dates stated, none taken"
                else:
                    dated = "no"
                place = (f"yes — {st.place_text} ({st.place_source})"
                         if st and st.place_text else "no")
            lines.append(f"| {n} | {_cell(v.listing_url)} | {_cell(dated)} | "
                         f"{_cell(place)} | {_cell(v.blocked_reason or '')} |")
        totals["dated"] += run.dated_n
        totals["placed"] += run.placed_n
        totals["blocked"] += run.blocked_n
        totals["walled"] += run.walled_n
        totals["off_host"] += run.off_host_n
        totals["not_knocked"] += run.not_knocked_n
        totals["nulled_when"] += run.nulled_when_n
        totals["rows_dated"] += run.rows_dated_n
        totals["filled_when"] += run.filled_when_n
        totals["filled_place"] += run.filled_place_n
        totals["conflict"] += run.conflict_n

    followed = sum(len(r.visits) for _, r in runs)
    lines += [
        "",
        f"permalinks tried **{followed}** · pages that STATED a night "
        f"**{totals['dated']}** · rows CARRYING a night afterwards "
        f"**{totals['rows_dated']}** · "
        f"placed by their own page **{totals['placed']}** · blocked **{totals['blocked']}** "
        f"(walls MET **{totals['walled']}**, not knocked after a run of walls "
        f"**{totals['not_knocked']}**, off-host **{totals['off_host']}**)",
        f"holes FILLED by this ticket: when **{totals['filled_when']}**, "
        f"place **{totals['filled_place']}** · list/page disagreements recorded "
        f"**{totals['conflict']}**, of which nights REMOVED as contested "
        f"**{totals['nulled_when']}** (neither side's claim adopted)",
    ]
    if mode == "FIXTURE":
        lines += [
            "",
            "_FIXTURE run: every url, date and venue above comes from the committed "
            "shape fixtures in `tests/fixtures/event_pages/`, not from a live desk. "
            "Egress to both desks is denied from this sandbox (CONNECT 403 at the "
            "proxy). These counts describe the reader's behaviour, never a desk's "
            "coverage._",
        ]
    return "\n".join(lines)


def _cell(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\n", " ")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--door", action="append", dest="doors",
                    help="door id (repeatable); default: both CapCoG desks")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                    help=f"permalinks to print (default {DEFAULT_LIMIT})")
    ap.add_argument("--real", action="store_true",
                    help="fetch the live pages instead of the committed fixtures")
    ap.add_argument("--max-pages", type=int, default=5,
                    help="cap on LIST pages walked per door (default 5)")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--min-interval", type=float, default=1.0,
                    help="seconds between live fetches (default 1.0)")
    ap.add_argument("--no-ics", action="store_true",
                    help="do not read an iCalendar file a page advertises")
    args = ap.parse_args(argv)

    doors = tuple(args.doors or DEFAULT_DOORS)
    mode = "LIVE" if args.real else "FIXTURE"
    runs, notes = collect(doors, limit=args.limit, real=args.real,
                          timeout_s=args.timeout, min_interval_s=args.min_interval,
                          max_pages=args.max_pages, read_ics=not args.no_ics)

    print(render(runs, mode=mode, limit=args.limit))
    if notes:
        print("")
        for note in notes:
            print(f"- {note}")
    print("")
    print("This tool wrote nothing: no candidate, no promotion, no DB write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
