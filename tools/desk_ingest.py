#!/usr/bin/env python3
"""Walk the local desks and WRITE what they printed into the catalog.

    python tools/desk_ingest.py --dry-run                  # fixtures, prints the plan, writes nothing
    python tools/desk_ingest.py --real --dry-run           # live desks, prints the plan, writes nothing
    python tools/desk_ingest.py --real --write             # live desks -> candidates -> promote

Founder, this session's ticket: "Take the Chronicle + Do512 walker that already
exists and write candidates + promote into the catalog (same key: night +
place-text + title-or-performer). Single-source rows stay and are labelled. Do
not require a second desk to publish."

The walk (`worker/locale/desk_walk.py`) and the de-dup (`worker/locale/desk_union.py`)
already existed and are UNCHANGED here. This tool adds the last hop and nothing
else: for every row of the union it calls the seams the rest of the stack
already publishes through —

    candidate_store.create_candidate   (one candidate per happening)
    candidate_store.add_evidence       (one row per desk that printed it)
    promote.promote_candidate          (the FULL trust gate, then `event`)

— so nothing here re-implements, weakens or bypasses a gate. A single desk
publishes because both desks are `local_media` in the committed catalog and
`worker/gating.py` has promoted that class on one source since the founder's
2026-08-05 ruling; a desk whose catalog class is NOT an anchor simply holds at
`needs_review` and is reported, which is the fail-closed direction.

Two guards worth knowing before you run it:

  * `--write` requires `--real`. A FIXTURE union is refused at the write seam
    itself (`desk_publish.refuse_fixture_write`), because "Fixture Quartet at
    the Shape Hall" in the live catalog is worse than an empty catalog.
  * Re-running is safe. Every candidate carries the founder's de-dup key at
    `extracted._desk.key`; a key already in the store is SKIPPED, so a nightly
    run adds what is new instead of a second copy of what is not.

Exit codes: 0 ran, 2 refused (bad door, bad locale, fixture write, no DSN).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.desk_coverage import fixture_fetcher, live_fetcher  # noqa: E402
from worker.locale.desk_publish import (  # noqa: E402
    CandidateWrite,
    DeskPublishError,
    DeskRegistration,
    plan,
    plan_digest,
    refuse_fixture_write,
    registration_for,
)
from worker.locale.desk_union import DeskUnion, bounded, union  # noqa: E402
from worker.locale.desk_walk import DEFAULT_MAX_PAGES, DeskWalk, DeskWalkError, walk  # noqa: E402
from worker.locale.kind_map import KindMapError, load_kind_map, map_for_door  # noqa: E402
from worker.locale.pack import LocalePackError, available_locales, load_pack  # noqa: E402

#: The two desks the founder named. Both are already walked, mapped and
#: fixtured on master; this tool adds no third desk (Must-not, this session).
DEFAULT_DOORS = ("austin-chronicle-eventsearch", "do512-today")

CATALOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "sources", "master_sources_catalog_120.json")


# --------------------------------------------------------------------------
# Counting what the site shows — the SAME predicates as api/public.py
# --------------------------------------------------------------------------

def count_events(cur) -> int:
    """`GET /events`'s population: every scheduled event, no confidence filter
    (api/public.py returns disputed rows too — shown as disputed, never
    dropped). The endpoint's `limit` caps the PAGE, not the catalog, so the
    count is what the page is drawn from.
    """
    cur.execute("select count(*) from event where status='scheduled'")
    return int(cur.fetchone()[0])


def count_tonight(cur, *, city: str, hours: int) -> int:
    """`GET /tonight`'s population for one window.

    The predicate is copied from `api/public.py::tonight` and must stay
    identical to it — a "before/after" that counts something the page does not
    show would be a number about this tool, not about the site. The city clause
    keeps its `v.city is null` arm for the same reason: that is the arm these
    desk rows arrive on when a desk named a venue and no city.
    """
    now = datetime.now(timezone.utc)
    cur.execute(
        """
        select count(*)
        from event e
        left join venue v on v.venue_id = e.venue_id
        where e.status='scheduled'
          and e.start_time >= %s
          and e.start_time <= %s
          and (v.city is null or v.city = %s)
        """,
        (now, now + timedelta(hours=hours), city))
    return int(cur.fetchone()[0])


def snapshot(cur, *, city: str, hours: int) -> Dict[str, int]:
    return {
        "events": count_events(cur),
        f"tonight_{hours}h": count_tonight(cur, city=city, hours=hours),
        "tonight_12h": count_tonight(cur, city=city, hours=12),
    }


def counts_table(before: Mapping[str, int], after: Mapping[str, int],
                 *, city: str, hours: int) -> str:
    rows = [
        (f"`GET /events` (all scheduled)", "events"),
        (f"`GET /tonight?city={city}` (default 12h window)", "tonight_12h"),
        (f"`GET /tonight?city={city}&hours={hours}` (this week)", f"tonight_{hours}h"),
    ]
    out = ["| surface | before | after | delta |", "|---|---:|---:|---:|"]
    for label, key in rows:
        b, a = before.get(key, 0), after.get(key, 0)
        out.append(f"| {label} | {b} | {a} | {a - b:+d} |")
    return "\n".join(out)


# --------------------------------------------------------------------------
# The walk
# --------------------------------------------------------------------------

def walk_doors(locale: str, door_ids: Sequence[str], *, real: bool,
               max_pages: int, timeout: int, min_interval: float
               ) -> Tuple[List[DeskWalk], Dict[str, DeskRegistration], object, str]:
    """Walk each named door and resolve every one of them to a catalog row.

    Registration happens BEFORE any write is planned, so a door that cannot be
    labelled stops the run at the door rather than half-way through a catalog.
    """
    pack = load_pack(locale)
    doors = {d.door_id: d for d in pack.doors}
    with open(CATALOG, encoding="utf-8") as fh:
        catalog = json.load(fh)

    # The locale's clock is pack data. No fallback: a guessed timezone puts
    # rows on the wrong nights, and the night is half the founder's de-dup key.
    if not pack.timezone:
        raise LocalePackError(
            f"locale pack {locale!r} states no `locale.timezone`, so 'same "
            f"night' cannot be computed. State it in the pack; this tool will "
            f"not assume one.")
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(pack.timezone)
    except Exception as exc:  # noqa: BLE001 — an unusable clock stops the run
        raise LocalePackError(
            f"timezone {pack.timezone!r} is unusable here "
            f"({type(exc).__name__}: {exc}). Install tzdata rather than "
            f"letting the union guess a night.") from exc

    walks: List[DeskWalk] = []
    registrations: Dict[str, DeskRegistration] = {}
    fetch_live = live_fetcher(timeout_s=timeout, min_interval_s=min_interval) if real else None

    for door_id in door_ids:
        door = doors.get(door_id)
        if door is None:
            raise LocalePackError(
                f"no door {door_id!r} in locale {locale!r}. Have: {sorted(doors)}")
        reg = registration_for(door, catalog)
        registrations[reg.via] = reg
        try:
            kind_map = map_for_door(door.door_id)
        except KindMapError:
            kind_map = None
        if real:
            fetch, start_url = fetch_live, None
        else:
            fetch, start_url, _ = fixture_fetcher(door.door_id)
        walks.append(walk(door, fetch, max_pages=max_pages, start_url=start_url,
                          kind_map=kind_map))
    return walks, registrations, tz, pack.timezone


# --------------------------------------------------------------------------
# The write
# --------------------------------------------------------------------------

def existing_keys(cur) -> Dict[str, Tuple[str, str, Optional[str]]]:
    """Every desk key already in the candidate store -> (id, status, event id).

    ONE scan, not one query per row: the whole point of the key is that a
    re-run is cheap, and 33 sequential scans of a growing table is not cheap.
    """
    cur.execute(
        """
        select extracted->'_desk'->>'key', candidate_id::text, status,
               promoted_event_id::text
        from event_candidate
        where extracted ? '_desk'
        """)
    return {row[0]: (row[1], row[2], row[3]) for row in cur.fetchall() if row[0]}


def ingest(writes: Sequence[CandidateWrite], *, seen: Mapping[str, tuple],
           create, add_evidence, promote) -> Dict[str, list]:
    """Write every planned row that is not already in the store.

    The three DB seams are INJECTED so this function — the one that decides
    what happens to each row — is testable without a database. Nothing is
    swallowed: every row lands in exactly one bucket, and the buckets are
    printed.
    """
    out: Dict[str, list] = {"promoted": [], "held": [], "skipped": [], "failed": []}
    for w in writes:
        if w.ingest_key in seen:
            cid, status, event_id = seen[w.ingest_key]
            out["skipped"].append((w, f"already in the store as {status} ({cid})"))
            continue
        try:
            cid = create(
                source_id=None,
                source_name=w.source_name,
                source_url=w.source_url,
                source_class=w.source_class,
                raw_text=w.raw_text,
                extracted=w.extracted,
                sxsw_mode=False,
            )
        except Exception as exc:  # noqa: BLE001 — a row we could not write is reported, never silent
            out["failed"].append((w, f"create_candidate: {type(exc).__name__}: {exc}"))
            continue
        # EVIDENCE FIRST, AND ALL OF IT. A failed evidence write is not a
        # cosmetic loss: the gate reads its source classes from these rows, so
        # a candidate that lost one would be judged on a partial record — and
        # promoting anyway would publish a listing on evidence we know is
        # incomplete. It also broke this loop's own cardinality: the row landed
        # in `failed` AND then in `promoted`/`held`, so the printed buckets
        # over-counted the plan.
        evidence_failure = None
        for ev in w.evidence:
            try:
                add_evidence(cid, ev.source_class, ev.source_name, ev.source_url, ev.quote)
            except Exception as exc:  # noqa: BLE001
                evidence_failure = f"add_evidence: {type(exc).__name__}: {exc}"
                break
        if evidence_failure:
            out["failed"].append((
                w, f"{evidence_failure} — candidate {cid} was written but NOT "
                   f"promoted: its evidence is incomplete, and the gate reads "
                   f"the evidence"))
            continue
        try:
            event_id = promote(cid)
            out["promoted"].append((w, event_id))
        except ValueError as exc:
            # The gate said HOLD/ESCALATE, or promote's own duplicate guard
            # refused a re-publish. Both are correct outcomes, not errors: the
            # candidate stays in the store where ops can see it.
            out["held"].append((w, str(exc)[:300]))
        except Exception as exc:  # noqa: BLE001
            out["failed"].append((w, f"promote: {type(exc).__name__}: {exc}"))
    return out


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def _cell(value) -> str:
    text = "" if value is None else str(value)
    return " ".join(text.split()).replace("|", "\\|") or "—"


def plan_table(writes: Sequence[CandidateWrite]) -> str:
    out = ["| # | key | desks | title | place | starts | clock |",
           "|---:|---|---|---|---|---|---|"]
    for i, w in enumerate(writes, 1):
        out.append("| {} | `{}` | {} | {} | {} | {} | {} |".format(
            i, _cell(w.ingest_key), _cell(" + ".join(w.vias)), _cell(w.title),
            _cell(w.extracted.get("venue_name")), _cell(w.start_time),
            "stated" if w.start_time else _cell(w.clock_hole)))
    return "\n".join(out)


def outcome_table(result: Mapping[str, list]) -> str:
    out = ["| outcome | rows | what it means |", "|---|---:|---|"]
    meaning = {
        "promoted": "written and published — visible on `/events`, and on `/tonight` when the clock falls in the window",
        "held": "written as a candidate, not published — the gate or the duplicate guard said so (reason below)",
        "skipped": "this happening was already in the store under the same key — a re-run, not a loss",
        "failed": "not written — the reason is printed, never swallowed",
    }
    for bucket in ("promoted", "held", "skipped", "failed"):
        out.append(f"| {bucket} | {len(result[bucket])} | {meaning[bucket]} |")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--locale", default="us-tx-capcog",
                    help=f"locale pack holding the doors (have: {list(available_locales())})")
    ap.add_argument("--door", action="append", dest="doors", default=None,
                    help=f"door_id to walk; repeatable (default: {' '.join(DEFAULT_DOORS)})")
    ap.add_argument("--real", action="store_true",
                    help="walk the LIVE desks (required before anything may be written)")
    ap.add_argument("--write", action="store_true",
                    help="write candidates and promote (needs --real and ONELIVE_DB_DSN)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and write nothing (the default when --write is absent)")
    ap.add_argument("--city", default="Austin", help="city the /tonight counts are taken for")
    ap.add_argument("--hours", type=int, default=168,
                    help="the wide /tonight window to count (default 168 = this week)")
    ap.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--min-interval", type=float, default=2.0,
                    help="politeness delay between live page fetches, seconds")
    args = ap.parse_args(argv)

    door_ids = args.doors or list(DEFAULT_DOORS)

    if args.write and not args.real:
        print("ERROR: --write requires --real. A fixture walk may never be "
              "written to a database (founder Must-not: do not ship fixture "
              "titles to production).", file=sys.stderr)
        return 2
    if args.write and not os.getenv("ONELIVE_DB_DSN"):
        print("ERROR: --write needs ONELIVE_DB_DSN. Refusing to guess a "
              "database.", file=sys.stderr)
        return 2

    try:
        walks, registrations, tz, tz_id = walk_doors(
            args.locale, door_ids, real=args.real, max_pages=args.max_pages,
            timeout=args.timeout, min_interval=args.min_interval)
    except (LocalePackError, DeskWalkError, DeskPublishError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    mode = "LIVE" if args.real else "FIXTURE"
    one = union(walks, timezone=tz, timezone_id=tz_id, mode=mode)
    writes = plan(one, registrations)
    digest = plan_digest(writes)

    print(f"# Desk ingest — {' + '.join(sorted({r.source_name for r in registrations.values()}))} "
          f"— {mode} walk")
    print()
    print("## 1. Desks")
    print()
    print("| desk | label written on the row | class the gate reads | pages read | pages blocked | rows | walk ended |")
    print("|---|---|---|---:|---:|---:|---|")
    for state in one.desks:
        reg = registrations.get(state.via)
        print(f"| `{state.door_id}` | {reg.source_name if reg else '—'} | "
              f"`{reg.source_class if reg else '—'}` | {state.pages_read} | "
              f"{state.pages_blocked} | {state.rows} | `{state.stopped_because}` |")
    unreadable = [d for d in one.desks if not d.readable]
    if unreadable:
        print()
        print("**UNREADABLE**: " + "; ".join(
            f"`{d.door_id}` opened no page ({', '.join(d.blocked_reasons) or d.stopped_because})"
            for d in unreadable)
            + " — an unread desk has an UNKNOWN list, never an empty one. Nothing "
              "is written for it and nothing is deleted because of it.")
    print()
    print("## 2. The write plan")
    print()
    print(plan_table(writes))
    print()
    print(f"{bounded(digest['rows'], one)} happening(s) planned: "
          f"{digest['timed']} carry a clock a desk stated, {digest['clock_holes']} "
          f"publish with an honest hole on the clock. "
          f"{digest['single_desk']} come from ONE desk and are written anyway "
          f"(founder: do not require a second desk to publish); "
          f"{digest['multi_desk']} carr{'ies' if digest['multi_desk'] == 1 else 'y'} two.")
    print()

    if not args.write:
        print("## 3. Nothing was written")
        print()
        print("This was a dry run" + ("" if args.real else " over COMMITTED FIXTURES")
              + ". Re-run with `--real --write` on a machine that can reach the "
                "desks and holds `ONELIVE_DB_DSN`.")
        return 0

    # --- the write ---------------------------------------------------------
    try:
        refuse_fixture_write(one)
    except DeskPublishError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    from worker.candidate_store import add_evidence, create_candidate, db  # noqa: PLC0415
    from worker.promote import promote_candidate  # noqa: PLC0415

    with db() as conn:
        with conn.cursor() as cur:
            before = snapshot(cur, city=args.city, hours=args.hours)
            seen = existing_keys(cur)

    result = ingest(writes, seen=seen, create=create_candidate,
                    add_evidence=add_evidence, promote=promote_candidate)

    with db() as conn:
        with conn.cursor() as cur:
            after = snapshot(cur, city=args.city, hours=args.hours)

    print("## 3. What happened to each row")
    print()
    print(outcome_table(result))
    for bucket in ("held", "failed"):
        if result[bucket]:
            print()
            print(f"### {bucket}")
            print()
            for w, why in result[bucket]:
                print(f"- `{w.ingest_key}` — {w.title}: {why}")
    print()
    print("## 4. Before / after — what the site serves")
    print()
    print(counts_table(before, after, city=args.city, hours=args.hours))
    print()
    print("Counted with `api/public.py`'s own predicates against the same "
          "database the API reads. `/tonight` shows only rows whose stated "
          "clock falls inside its window, which is why the week column moves "
          "further than the 12-hour one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
