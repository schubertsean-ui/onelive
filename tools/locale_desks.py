#!/usr/bin/env python3
"""Print the door table for one locale: what we would open, and what came back.

    python tools/locale_desks.py --locale us-tx-capcog             # fixture run
    python tools/locale_desks.py --locale us-tx-capcog --real      # live read

Columns are the founder's, verbatim: door | public? | sample happening count |
via | blocked_reason.

TWO MODES, because one of them cannot run everywhere.

  (default) FIXTURE. Each readable door is handed the committed fixture whose
            SHAPE matches its declared intake and door type
            (tests/fixtures/locale_desks/). The count proves the reader works on
            that shape. It is NOT a claim about how many happenings the live
            desk lists, and the table says so in its own footer.
  --real    LIVE. Fetches each readable door once, politely, and reads what came
            back. It writes NOTHING — no DB rows, no candidates, no promotion.
            A 401/402/403/407/429 or a redirect to a sign-in page demotes the
            door to class D through the SAME authority the ingest loop uses
            (worker.sourcing.source_class.demote_on_response); we knock once and
            never work around a wall.

This tool reports. It does not ingest: no candidate is written and nothing
reaches a user through it.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.locale.desk_read import DeskReadError, read  # noqa: E402
from worker.locale.pack import (  # noqa: E402
    LocalePackError, available_locales, hunt, load_pack,
)
from worker.sourcing.source_class import (  # noqa: E402
    ClassVerdict, demote_on_response,
)

FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "fixtures", "locale_desks",
)

#: Which committed fixture stands for which door SHAPE. This is a shape
#: assignment for an offline run, never a claim that the live page looks like
#: this. Checked in the fixture run's footer so a reader cannot mistake it.
SHAPE_FIXTURES = (
    (lambda d: d.intake == "json_ld", "civic_jsonld.html"),
    (lambda d: d.door_type == "marketplace", "marketplace_microdata.html"),
    (lambda d: d.door_type == "official_list", "official_list.html"),
    (lambda d: True, "desk_listing.html"),
)

USER_AGENT = "OneLiveBot/0.1 (+contact: ops@onelive.example)"


def fixture_for(door) -> str:
    for predicate, name in SHAPE_FIXTURES:
        if predicate(door):
            return name
    raise AssertionError("SHAPE_FIXTURES must end in a catch-all")


def _fixture_row(door):
    name = fixture_for(door)
    path = os.path.join(FIXTURE_DIR, name)
    try:
        with open(path, encoding="utf-8") as fh:
            html = fh.read()
    except OSError as exc:
        return None, f"fixture unreadable: {exc}"
    try:
        return read(door, html), None
    except DeskReadError as exc:
        return None, str(exc)


def _real_row(door, *, timeout_s: int, min_interval_s: float):
    try:
        import requests
    except ImportError:
        return None, "requests is not installed in this environment"
    time.sleep(max(0.0, min_interval_s))
    try:
        resp = requests.get(door.url, headers={"User-Agent": USER_AGENT},
                            timeout=timeout_s)
    except Exception as exc:  # noqa: BLE001 — every transport failure is a row, not a crash
        return None, f"fetch failed: {type(exc).__name__}: {exc}"[:200]
    declared = ClassVerdict("B", "declared public in the locale pack", fetchable=True)
    verdict = demote_on_response(
        declared, status=resp.status_code, final_url=str(resp.url))
    if verdict.klass == "D":
        return None, f"class D on first contact — {verdict.reason}"
    if resp.status_code >= 400:
        return None, f"HTTP {resp.status_code} — triage, not 'no events here'"
    try:
        return read(door, resp.text, base_url=str(resp.url)), None
    except DeskReadError as exc:
        return None, str(exc)


def _cell(value) -> str:
    return (value or "").replace("|", "\\|")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--locale", required=True,
                    help=f"locale id of a pack in sources/locale_packs "
                         f"(have: {list(available_locales())})")
    ap.add_argument("--real", action="store_true",
                    help="fetch each readable door live (writes nothing)")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--min-interval", type=float, default=2.0,
                    help="politeness delay between live fetches, seconds")
    ap.add_argument("--door-type", action="append", default=None,
                    help="restrict to a door type (repeatable)")
    args = ap.parse_args(argv)

    try:
        pack = load_pack(args.locale)
        doors = hunt(args.locale, door_types=args.door_type)
    except LocalePackError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    mode = "LIVE" if args.real else "FIXTURE"
    print(f"# Doors — {pack.label} (`{pack.locale_id}`) — {mode} run")
    print()
    print(f"{len(doors)} door(s) in the pack; "
          f"{sum(1 for d in doors if d.readable)} readable. "
          f"{len(pack.queries())} consumer queries in the grammar.")
    print()
    print("| door | public? | sample happening count | via | blocked_reason |")
    print("|---|---|---|---|---|")

    totals = {"rows": 0, "dated": 0, "read": 0, "blocked": 0}
    for door in doors:
        via = _cell(door.via) or "—"
        public = "yes" if door.public else "no"
        if not door.readable:
            reason = door.blocked_reason or (
                f"door_type {door.door_type} is not a listable door"
                if door.door_type in ("wall", "junk")
                else f"intake {door.intake}: no read path")
            totals["blocked"] += 1
            print(f"| `{door.door_id}` ({door.door_type}) | {public} | — | {via} "
                  f"| {_cell(reason)} |")
            continue
        result, error = (_real_row(door, timeout_s=args.timeout,
                                   min_interval_s=args.min_interval)
                         if args.real else _fixture_row(door))
        if result is None:
            totals["blocked"] += 1
            print(f"| `{door.door_id}` ({door.door_type}) | {public} | — | {via} "
                  f"| {_cell(error)} |")
            continue
        totals["read"] += 1
        totals["rows"] += result.count
        totals["dated"] += result.dated
        undated = result.count - result.dated
        detail = f"{result.count}" + (f" ({undated} with no date on the page)" if undated else "")
        source = "" if args.real else f" via `{fixture_for(door)}`"
        print(f"| `{door.door_id}` ({door.door_type}) | {public} | {detail}{source} "
              f"| {via} | — |")

    print()
    print(f"**Totals:** {totals['read']} door(s) read, {totals['rows']} happening "
          f"row(s), {totals['dated']} with a date the page stated, "
          f"{totals['rows'] - totals['dated']} with an honest hole on the clock, "
          f"{totals['blocked']} door(s) not read.")
    if not args.real:
        print()
        print("Counts above come from committed FIXTURES that stand for each door's "
              "SHAPE (`tests/fixtures/locale_desks/`). They prove the reader handles "
              "that shape. They are not a measurement of any live desk.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
