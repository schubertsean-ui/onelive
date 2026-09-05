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
  * A HOLE IS PUBLISHED AS THE HOLE IT IS. `event` has one clock column, so
    every unstated time becomes the same NULL and the feed renders every NULL
    as "Date TBA". Three different truths would arrive as one display, so
    `desk_publish` separates them first: no date stated publishes (TBA is
    true); desks disagreeing about the time publishes DISPUTED, labelled by the
    publisher inside the insert's own transaction rather than by a second write
    from here;
    a desk that stated the NIGHT and no time is HELD, because saying "date
    unknown" about a date we were given is manufacturing an absence (R-111).
  * Re-running is safe, and it asks TWO questions rather than one. Every
    candidate carries the founder's de-dup key at `extracted._desk.key`, so a
    happening already in the store is not written twice. But a key answers only
    "is this the same happening?" — a desk that corrects 8pm to 9:30pm on the
    same night keys identically — so each candidate also carries the desk's
    STATEMENT (`extracted._desk.statement`). A row is skipped only when the
    desk still says the same thing about it; when the desk has changed its
    word, the new statement is recorded as a candidate, the published row is
    marked DISPUTED so it stops reading `confirmed` while its own desk
    contradicts it (shown as disputed, never hidden), and the divergence is
    REPORTED under `changed`. Correcting the FIELD is still the reviewed update
    seam's job (R-110); nothing goes stale silently, and nothing goes stale
    while still looking settled.

Exit codes: 0 ran clean, 1 ran but left a published row mislabelled (a dispute
write failed — see section 5), 2 refused before writing anything (bad door, bad
locale, a fixture union, no DSN).
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
    DESK_KEY,
    CandidateWrite,
    DeskPublishError,
    DeskRegistration,
    contradicts,
    describe_drift,
    drift,
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

def existing_keys(cur) -> Dict[str, Tuple[str, str, Optional[str], Optional[dict]]]:
    """Every desk key already in the store -> (id, status, event id, statement).

    ONE scan, not one query per row: the whole point of the key is that a
    re-run is cheap, and 33 sequential scans of a growing table is not cheap.

    The STATEMENT comes back with the key because the key alone cannot answer
    the question a re-run actually has to ask (see `ingest`). The most RECENT
    row for a key wins: a drift row is written as a new candidate carrying the
    desk's newer statement, so ordering by `created_at` is what makes the next
    run compare against the desk's latest word rather than its first.
    """
    cur.execute(
        """
        select distinct on (extracted->'_desk'->>'key')
               extracted->'_desk'->>'key', candidate_id::text, status,
               promoted_event_id::text, extracted->'_desk'->'statement'
        from event_candidate
        where extracted ? '_desk'
        order by extracted->'_desk'->>'key', created_at desc
        """)
    return {r[0]: (r[1], r[2], r[3], r[4]) for r in cur.fetchall() if r[0]}


#: The buckets every planned row lands in, exactly one each. Named so the
#: cardinality invariant is over a stated set rather than "whatever keys the
#: dict happens to have" — `ingest` also returns a non-row key for rows whose
#: public state it failed to correct.
ROW_BUCKETS = ("promoted", "held", "changed", "skipped", "failed")


def dispute_superseded(event_id: Optional[str]) -> str:
    """The published row now reads DISPUTED, and says why it does not.

    Evaluator, PR #229 r2 (openai/absence-only): recording a desk's correction
    while the published row keeps reading `confirmed` still shows a reader an
    older detail "as if it were still confirmed". That is the gap r1 left, and
    the 4-state model already holds its answer — `disputed` is the state for
    "our evidence about this row no longer agrees with itself", and CLAUDE.md's
    invariant is that a disputed event is SHOWN as disputed, never deleted and
    never softened. So the row stays on the feed, carrying every fact the desk
    stated, with our confidence in those facts told honestly.

    This is a confidence transition, NOT a correction: no field the desk stated
    is rewritten here. Rewriting one is `worker/listing_update.py`'s job and
    still is (R-110) — this closes the "reads as confirmed" half, which is the
    half a reader can see.

    A CLAIM-LOCKED row is left alone, and that is the founder's own precedence
    rule rather than caution: an artist or venue claim overrides (CLAUDE.md
    agent org / resolve_entities), so a third-party desk disagreeing with the
    principal's own listing is not evidence against the principal. It is
    reported instead.
    """
    if not event_id:
        return "no published row to dispute (the earlier candidate never promoted)"
    from worker.candidate_store import db  # noqa: PLC0415
    from worker.promote import mark_event_disputed  # noqa: PLC0415

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select override_lock, confidence from event where event_id=%s",
                (event_id,))
            row = cur.fetchone()
    if row is None:
        return f"published row {event_id} is gone; nothing to dispute"
    locked, confidence = row
    if locked:
        return (f"published row {event_id} is claim-locked — a venue or artist "
                f"owns it, and a claim overrides a desk, so its confidence is "
                f"left alone")
    if confidence == "disputed":
        return f"published row {event_id} already reads disputed"
    mark_event_disputed(event_id, actor_type="system")
    return (f"published row {event_id} now reads DISPUTED — shown as disputed, "
            f"never hidden")


def ingest(writes: Sequence[CandidateWrite], *, seen: Mapping[str, tuple],
           create, add_evidence, promote, dispute=dispute_superseded) -> Dict[str, list]:
    """Write every planned row that is not already in the store.

    The three DB seams are INJECTED so this function — the one that decides
    what happens to each row — is testable without a database. Nothing is
    swallowed: every row lands in exactly one bucket, and the buckets are
    printed.
    """
    out: Dict[str, list] = {b: [] for b in ROW_BUCKETS}
    # NOT a row bucket: rows already counted above whose PUBLIC state we failed
    # to correct. Kept apart so the cardinality invariant over ROW_BUCKETS still
    # holds, and read by main() to fail the run (evaluator PR #229 r4).
    out["dispute_failures"] = []
    for w in writes:
        supersedes = None
        if w.ingest_key in seen:
            cid, status, event_id, stored = seen[w.ingest_key]
            fresh = w.extracted[DESK_KEY]["statement"]
            moved = drift(stored, fresh)
            if not moved:
                out["skipped"].append((w, f"already in the store as {status} ({cid})"))
                continue
            # THE DESK HAS CHANGED ITS MIND, so this is not a re-run of a row
            # we already have — it is a new statement about it, and skipping on
            # the key alone would leave a listing published under this desk's
            # name that the desk itself no longer supports (evaluator, PR #229
            # r1: "users can be shown false event details").
            #
            # It is RECORDED, never applied. Rewriting a published row is a
            # MUTATION, and this repository has one reviewed seam for that
            # (`worker/listing_update.py`, founder-ruled 2026-09-02: same-page
            # evidence, four enumerated columns, never a delete). A walker that
            # grew its own update path beside it would be a second, unreviewed
            # answer to the same question. So the desk's new word becomes a
            # candidate — evidence, auditable, in the ops queue — the published
            # row is left alone, and the divergence is REPORTED rather than
            # silently absorbed. The residual is R-110, with its trigger.
            # A CHANGE IS NOT AUTOMATICALLY A DISAGREEMENT (evaluator PR #229
            # r6). A second desk picking up a row the first already gave us
            # changes `vias` and contradicts nothing — disputing the published
            # row for that would show a reader MORE agreement as a dispute,
            # which is a false trust display in the opposite direction to the
            # one r2 fixed. So the desk's new word is always RECORDED, and only
            # a contradicting field puts the published row's label in question.
            against = contradicts(stored, fresh)
            supersedes = {"candidate_id": cid, "event_id": event_id,
                          "was": stored, "changed": moved,
                          "contradicts": against}
            w.extracted[DESK_KEY]["supersedes"] = supersedes
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
        if supersedes is not None:
            # Recorded, not re-published. Promoting would put a SECOND listing
            # for this happening on the feed beside the one already there —
            # strictly worse for a reader than one stale field.
            #
            # But the published row does not go on reading `confirmed` while
            # its own desk disagrees with it: it is marked DISPUTED, which is
            # the state the 4-state model has for exactly this evidence shape
            # and which the feed renders without hiding the row. Correcting the
            # FIELD is still worker/listing_update.py's (R-110); telling the
            # truth about our confidence in it is ours, now.
            if not supersedes["contradicts"]:
                verdict = (f"published row {supersedes['event_id']} is left "
                           f"alone: this is corroboration, not a contradiction "
                           f"— nothing the desks say about it has changed")
            else:
                try:
                    verdict = dispute(supersedes["event_id"])
                except Exception as exc:  # noqa: BLE001 — a row we could not flag fails the run
                    verdict = (f"COULD NOT DISPUTE published row "
                               f"{supersedes['event_id']} ({type(exc).__name__}: "
                               f"{exc}) — it may still read as confirmed")
                    out["dispute_failures"].append((supersedes["event_id"], verdict))
            out["changed"].append((
                w, f"the desk has changed its statement since we published "
                   f"event {supersedes['event_id']} — "
                   f"{describe_drift(supersedes['was'], w.extracted[DESK_KEY]['statement'], supersedes['changed'])}"
                   f" — recorded as candidate {cid}, not re-published; "
                   f"{verdict}"))
            continue
        if w.hold_reason:
            # Written, deliberately not published: `event` has one clock column
            # and a NULL in it renders as "Date TBA", which would tell a reader
            # we do not know a date the desk gave us (evaluator PR #229 r3).
            # The row is in the catalog as a candidate and in the ops queue.
            out["held"].append((w, f"{w.hold_reason} — candidate {cid}"))
            continue
        try:
            event_id = promote(cid)
            if w.clock_disputed:
                # The desks agree it is ON and disagree about WHEN. It publishes
                # — existence is not in doubt — and `promote_candidate` writes
                # its confidence as `disputed` in the SAME transaction as the
                # insert, from the gate's own field-hole finding.
                #
                # This tool deliberately does NOT mark it afterwards. A
                # promote-then-flag pair leaves a window where a contested row
                # is public and labelled confirmed, and a failure in between
                # makes that window permanent (evaluator PR #229 r5). "Publish
                # as disputed or do not publish" is an invariant only the
                # publisher can hold, so it is held there and asserted here.
                out["promoted"].append((w, f"{event_id} (disputed at publish: {w.clock_hole})"))
                continue
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
        "held": "written as a candidate, not published — the gate, the duplicate guard, or a hole we cannot display honestly said so (reason below)",
        "changed": "the desk has CHANGED its statement about a happening we already published — recorded as a new candidate and the published row marked disputed, so it is still shown but no longer reads as settled (reason below)",
        "skipped": "this happening was already in the store, and the desk still says the same thing about it — a re-run, not a loss",
        "failed": "not written — the reason is printed, never swallowed",
    }
    for bucket in ("promoted", "held", "changed", "skipped", "failed"):
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
    tba = digest['clock_holes'] - digest['held'] - digest['clock_disputed']
    print(f"{bounded(digest['rows'], one)} happening(s) planned, of which "
          f"{digest['publishable']} publish and {digest['held']} "
          f"{'is' if digest['held'] == 1 else 'are'} HELD "
          f"(a desk stated the night and no time — publishing would render as "
          f"'Date TBA' and hide a date we were given; R-111). "
          f"{digest['timed']} carry a clock a desk stated; "
          f"{digest['clock_disputed']} publish DISPUTED because their desks "
          f"state different times; {tba} publish with a true 'Date TBA' "
          f"because no desk stated a date at all. "
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
    for bucket in ("changed", "held", "failed"):
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

    # FAIL CLOSED ON A ROW LEFT MISLABELLED (evaluator PR #229 r4). Marking a
    # row disputed is not decoration: it is what stops a listing from reading
    # `confirmed` while the evidence contradicts it. If that write failed, a
    # public row is live and wrong RIGHT NOW, and a run that printed its tables
    # and exited 0 would report success over exactly the harm this tool exists
    # to prevent. The rows cannot be un-published (no delete, and withdrawing a
    # real happening is worse), so the honest signal is the run itself: exit
    # non-zero, name the events, and say what a person has to do.
    if result["dispute_failures"]:
        print()
        print("## 5. FAILED — published rows are live and mislabelled")
        print()
        for event_id, why in result["dispute_failures"]:
            print(f"- `{event_id}` — {why}")
        print()
        print(f"{len(result['dispute_failures'])} published row(s) could not be "
              f"marked disputed, so each may read `confirmed` while its own "
              f"evidence contradicts it. Re-run this tool once the database is "
              f"reachable (it is idempotent, and it will re-detect these), or "
              f"set their confidence to `disputed` in the ops console.")
        print("This run is a FAILURE despite the counts above.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
