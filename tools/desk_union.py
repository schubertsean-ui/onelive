#!/usr/bin/env python3
"""Walk TWO desks and print ONE happening table — the union, deduped, in our model.

    python tools/desk_union.py                                  # fixtures, both desks
    python tools/desk_union.py --real                           # live walk
    python tools/desk_union.py --door austin-chronicle-eventsearch --door do512-today

Five tables, all five the founder's ticket:

  1. DESKS        each desk, its pages, and whether it was readable at all. A
                  desk that answered 403 prints UNREADABLE — never 0 rows.
  2. HAPPENINGS   the union: unique key | via (which desk, or both) | kind or
                  `other` | dated or not | title | place.
  3. BOARD        <desk> only | <other desk> only | both | unique total.
  4. HELD APART   every row the de-dup rule could not key, and why. These rows
                  are IN table 2 under a desk-local key; this is the reason
                  list, never a discard pile.
  5. NEAR MISSES  different desks, same night, same place, different name — the
                  honest ceiling on how much more the union could collapse.

Then: NEXT DOORS, the short list of doors this locale knows and this run did not
open. Named from the committed pack only. This tool fetches none of them.

TWO MODES, never confused:

  (default) FIXTURE  the committed shape pages in tests/fixtures/desk_pages/.
                     They prove the union rule, the key and the counting. They
                     are NOT a measurement of any live desk, and every table
                     says so in its footer.
  --real             fetch the live desks, politely, one page at a time. A wall
                     (401/402/403/407/429 or a sign-in redirect) ends that
                     desk's walk through the ingest loop's own authority — we
                     knock once, we never log in — and the board then refuses to
                     state "<other desk> only", because that is a claim about a
                     list nobody read.

This tool REPORTS. It writes nothing: no candidate, no promotion, no user-visible
row, no DB write of any kind. Nothing it prints reaches a person browsing the
site — running it does not change the catalog.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.desk_coverage import fixture_fetcher, live_fetcher  # noqa: E402
from worker.locale.desk_union import (  # noqa: E402
    DeskUnionError, board_table, certainty_note, desk_table, held_apart_table,
    near_miss_table, summary_line, union, union_table,
)
from worker.locale.desk_walk import (  # noqa: E402
    DEFAULT_MAX_PAGES, DeskWalkError, walk,
)
from worker.locale.kind_map import KindMapError, map_for_door  # noqa: E402
from worker.locale.pack import (  # noqa: E402
    LocalePackError, available_locales, load_pack,
)

#: The two desks already dumped on master. Named here as a DEFAULT, not a law:
#: `--door` takes any door the pack states, and a third desk is a third flag.
DEFAULT_DOORS = ("austin-chronicle-eventsearch", "do512-today")

#: How many unopened doors the NEXT list prints before summarising the rest.
#: The founder asked for a short list.
NEXT_DOORS_SHOWN = 8


def next_doors(pack, walked) -> str:
    """The short list of doors this locale knows and this run did not open.

    Read off the committed pack, in its own trust order (most trusted first).
    Nothing here is fetched, and no door is graded by anything except what the
    pack already states about it.
    """
    walked = set(walked)
    readable = [d for d in pack.doors if d.readable and d.door_id not in walked]
    order = {"local_desk": 0, "civic": 1, "official_list": 2, "marketplace": 3}
    readable.sort(key=lambda d: (order.get(d.door_type, 9), d.door_id))
    shown = readable[:NEXT_DOORS_SHOWN]

    lines = ["| door | type | via | evidence the pack states | category map |",
             "|---|---|---|---|---|"]
    for door in shown:
        try:
            mapped = map_for_door(door.door_id)
        except KindMapError:
            mapped = None
        lines.append(
            f"| `{door.door_id}` | {door.door_type} | {door.via or '—'} | "
            f"{door.evidence} | {'`' + mapped.map_id + '`' if mapped else '**none yet**'} |")
    out = ["\n".join(lines)]
    rest = len(readable) - len(shown)
    if rest > 0:
        out.append(f"\n…and {rest} more readable door(s) in this pack, unopened.")

    shut = [d for d in pack.doors if not d.readable]
    if shut:
        out.append(
            "\nNot on this list, and not a gap to close: "
            + ", ".join(f"`{d.door_id}`" for d in shut)
            + " — the pack states each as a wall, a copy farm, or a door with no "
              "read path we may use. We do not log in and we do not launder a "
              "copy farm into a listing.")
    out.append("\n**Nothing above was fetched.** These are names off the "
               "committed pack, and opening one is its own ticket.")
    return "".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--locale", default="us-tx-capcog",
                    help=f"locale pack holding the doors (have: {list(available_locales())})")
    ap.add_argument("--door", action="append", dest="doors", default=None,
                    help=f"door_id to walk; repeatable (default: {list(DEFAULT_DOORS)})")
    ap.add_argument("--real", action="store_true",
                    help="walk the LIVE desks (writes nothing)")
    ap.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--min-interval", type=float, default=2.0,
                    help="politeness delay between live page fetches, seconds")
    args = ap.parse_args(argv)

    try:
        pack = load_pack(args.locale)
    except LocalePackError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    doors_by_id = {d.door_id: d for d in pack.doors}

    wanted = tuple(args.doors) if args.doors else DEFAULT_DOORS
    missing = [d for d in wanted if d not in doors_by_id]
    if missing:
        print(f"ERROR: no door(s) {missing} in locale {args.locale!r}. "
              f"Have: {sorted(doors_by_id)}", file=sys.stderr)
        return 2

    # The locale's clock is pack data. No fallback: a union with a guessed
    # timezone would put rows on the wrong nights and merge the wrong ones.
    if not pack.timezone:
        print(f"ERROR: locale pack {args.locale!r} states no `locale.timezone`, "
              f"so 'same night' cannot be computed. State it in the pack; this "
              f"tool will not assume one.", file=sys.stderr)
        return 2
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(pack.timezone)
    except Exception as exc:  # noqa: BLE001 — an unusable clock stops the run
        print(f"ERROR: timezone {pack.timezone!r} is unusable here "
              f"({type(exc).__name__}: {exc}). Install tzdata rather than "
              f"letting the union guess a night.", file=sys.stderr)
        return 2

    walks = []
    for door_id in wanted:
        door = doors_by_id[door_id]
        start_url = None
        if args.real:
            fetch = live_fetcher(timeout_s=args.timeout, min_interval_s=args.min_interval)
        else:
            try:
                fetch, start_url, _manifest = fixture_fetcher(door_id)
            except OSError as exc:
                print(f"ERROR: no committed fixtures for door {door_id!r} ({exc}). "
                      f"Run with --real, or add "
                      f"tests/fixtures/desk_pages/{door_id}/manifest.json",
                      file=sys.stderr)
                return 2
        try:
            kind_map = map_for_door(door_id)
        except KindMapError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        try:
            walks.append(walk(door, fetch, max_pages=args.max_pages,
                              start_url=start_url, kind_map=kind_map))
        except DeskWalkError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    mode = "LIVE" if args.real else "FIXTURE"
    try:
        one = union(walks, timezone=tz, timezone_id=pack.timezone, mode=mode)
    except DeskUnionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"# One happening table — {' + '.join(w.via or w.door_id for w in walks)} "
          f"— {mode} walk")
    print()
    print(f"Locale: `{pack.locale_id}` ({pack.label}) · nights are calendar dates "
          f"in `{pack.timezone}`, projected from the instant each desk stated.")
    print(f"De-dup rule: same night + same place-text + same title-or-performer "
          f"-> one row, many vias. No identity service. No invented dates.")
    print()
    print("## 1. Desks")
    print()
    print(desk_table(one))
    print()
    if not one.all_readable:
        print("**One or more desks did not open.** A desk we could not read has an "
              "UNKNOWN list, not an empty one, so the board below refuses every "
              "count that would state what that desk did or did not have.")
        print()
    print("## 2. Happenings — the union, deduped")
    print()
    print(union_table(one))
    print()
    # Derived, like the board's cells: this sentence used to state the total
    # flat while the board beside it stated a bound.
    print(summary_line(one))
    if one.performer_merges:
        print()
        print(f"**Merged on the performer, not the whole title ({len(one.performer_merges)})** "
              f"— listed so every judgment-bearing merge is visible: "
              + "; ".join(f"`{k}`: " + " / ".join(t) for k, t in one.performer_merges))
    if one.within_desk_merges:
        print()
        print(f"**Collapsed within ONE desk ({len(one.within_desk_merges)})** — the "
              f"rule applies to every pair, so this table's per-desk count differs "
              f"from `tools/desk_coverage.py` by that many: "
              + "; ".join(f"`{k}`: " + " / ".join(t) for k, t in one.within_desk_merges))
    print()
    print("## 3. Board")
    print()
    print(board_table(one))
    print()
    print("## 4. Held apart — rows that can only ever be themselves")
    print()
    print(held_apart_table(one))
    print()
    print("## 5. Near misses — same night, same place, different name")
    print()
    print(near_miss_table(one))
    print()
    print("## Next doors we still miss")
    print()
    print(next_doors(pack, wanted))
    print()
    print("## Limits of this table")
    print()
    print("- A night comes only from a date a desk STATED in markup. Prose "
          "(\"this Saturday\", \"Ongoing\") is carried verbatim and yields no "
          "night, so those rows never merge. No date is parsed out of prose.")
    print("- A 12:30am listing is keyed to its own calendar date, not to the "
          "evening before. Rolling late sets back a night is a rule the founder "
          "has not set, and it would move rows between nights silently.")
    print("- The performer strip removes a trailing \"at <this row's own venue>\" "
          "and a support-act tail (\"w/\", \"feat.\"). It runs only after night "
          "AND place already match, and every merge it makes is listed above.")
    if not args.real:
        print("- **FIXTURE run.** Every count above is a count of committed shape "
              "fixtures — invented titles, venues and dates that exist to prove "
              "the walk, the key and the board. It is not a measurement of the "
              "Austin Chronicle, of Do512, or of any live desk.")
    # Derived from the board's own facts, never written beside them: a
    # hand-written certainty sentence drifts from the table it summarises.
    print("- " + certainty_note(one))
    print()
    print("This tool wrote nothing: no candidate, no promotion, no user-visible row. "
          "Reading two desks does not change the catalog — wiring these rows into "
          "the pipeline is a separate, named step.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
