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
write failed — see section 6), 2 refused before writing anything (bad door, bad
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
from worker.locale.desk_follow import (  # noqa: E402
    DEFAULT_BUDGET,
    FollowResult,
    follow,
    followable,
)
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
from worker.locale.identity_patterns import load_patterns  # noqa: E402
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

def split_table(walks: Sequence[DeskWalk]) -> str:
    """The founder's Ticket B table: did the list become MANY happenings?

    ONE-LIVE-ENTITY-SPLIT-LAW.md §9.6 binds this ticket to these counters, and
    §2 to what they must read. Every number is derived from the walk's own rows
    and pages here, never carried in from the reader's internal counters — the
    one exception is `mash_blocked`, which is printed BESIDE `mash_n` precisely
    so a zero there reads as a refusal rather than as an absence.

      rows_n       happenings this desk yielded
      identities   distinct addresses the pages declared
      unsplit_n    pages read that declared no identity we hold (ZERO rows,
                   never one blob) — a coverage defect on THAT door
      mash_n       rows whose `listing_url` is a LIST url (must be 0)
      403_n        pages walled — by the desk, or by a proxy between us and it;
                   their rows are UNKNOWN, never zero, and the door stays queued
      unread_n     pages we could not read for ANY reason (403_n is a subset)
      split by     which rung(s) of the ladder read this desk's pages
    """
    lines = ["| desk | rows_n | identities | unsplit_n | mash_n | mash_blocked | "
             "403_n | unread_n | pages read | split by |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for one in walks:
        identities = len({r.listing_url for r in one.rows if r.listing_url})
        tiers = ", ".join(f"`{t}`" for t in one.identity_tiers) or "—"
        lines.append(
            f"| `{one.door_id}` | {one.count} | {identities} | {one.unsplit_n} | "
            f"{one.mash_n} | {one.mash_blocked} | {one.walled_n} | "
            f"{one.unread_n} | {one.pages_read} | {tiers} |")
    total_mash = sum(w.mash_n for w in walks)
    total_unsplit = sum(w.unsplit_n for w in walks)
    total_walled = sum(w.walled_n for w in walks)
    read_any = [w for w in walks if w.pages_read]
    lines.append("")
    lines.append(
        f"`mash_n` totals **{total_mash}** across these desks — a row whose "
        f"address is the list's own URL keys a whole desk to one identity, which "
        f"is the defect this ticket exists to remove (§2 Forbidden). "
        f"`unsplit_n` totals **{total_unsplit}**: pages we could not split are "
        f"ZERO rows and a named coverage defect on that door, answered by a "
        f"pattern or a claim — never by a mashed row and never printed as an "
        f"empty desk. `403_n` totals **{total_walled}**: a walled page has an "
        f"UNKNOWN list, not an empty calendar, and the door stays queued for a "
        f"claim.")
    if not read_any:
        lines.append("")
        lines.append(
            "**No page was read on this run**, so every count above is 0 for the "
            "same reason: nothing to count. That is NOT evidence the split "
            "works and NOT evidence these desks are empty — the split is proven "
            "by `tests/test_identity_split.py` and by the FIXTURE run of this "
            "same command, and these desks stay queued.")
    return "\n".join(lines)


def follow_walks(walks: Sequence[DeskWalk], fetchers: Mapping[str, object], *,
                 budget: int, as_of, patterns=None) -> Dict[str, FollowResult]:
    """The FIELD TICK: open each happening's own page and fill the holes it
    states (ONE-LIVE-ENTITY-SPLIT-LAW.md §4, "fetch best door -> fields (when,
    place, actors) same-page only").

    The walk's rows are REPLACED by the filled ones, so everything downstream —
    the union, the write plan, the counts — sees what the event pages said. The
    budget is per desk, and the rows it does not reach are counted rather than
    quietly presented as dateless.
    """
    out: Dict[str, FollowResult] = {}
    for one in walks:
        fetch = fetchers.get(one.door_id)
        if fetch is None or not one.rows:
            continue
        result = follow(one.rows, fetch, door_id=one.door_id, budget=budget,
                        as_of=as_of, patterns=patterns)
        one.rows = result.rows
        out[one.door_id] = result
    return out


def null_reasons(one: DeskWalk, result: Optional[FollowResult], *, patterns
                 ) -> Dict[str, int]:
    """WHY each row still has no clock, derived from the rows themselves.

    `still_null_n` is the number a table would misread first: it holds rows
    whose own page was read and stated no date, rows whose page we were refused,
    and rows nobody asked because the budget ran out — three different facts, and
    only the first is about the desk. Counting them apart is what stops a bounded
    run from reading as a finding (RED_CLASSES: pagination-integrity-gap).
    """
    queued = {url for url, _ in (result.queued if result else ())}
    counts = {"page stated no date": 0, "page could not be read": 0,
              "not asked (budget)": 0, "no followable address": 0}
    for row in one.rows:
        if row.when:
            continue
        if row.detail_url:
            counts["page stated no date"] += 1
        elif (row.listing_url or "").strip() in queued:
            counts["page could not be read"] += 1
        elif followable(row, patterns=patterns)[0]:
            counts["not asked (budget)"] += 1
        else:
            counts["no followable address"] += 1
    return counts


def follow_table(walks: Sequence[DeskWalk], follows: Mapping[str, FollowResult],
                 *, budget: int, patterns) -> str:
    """The founder's Ticket C table, exactly these five columns.

      rows_n        happenings this desk yielded (unchanged by the follow — a
                    field tick never creates or destroys a happening)
      dated_n       rows carrying a clock a page STATED, after the follow
      still_null_n  rows with none. Decomposed below, because it is not one fact
      403_n         pages walled, list walk AND event pages, ours or theirs
      mash_n        rows whose address is a list URL — must be 0 (§2 Forbidden)
    """
    lines = ["| desk | rows_n | dated_n | still_null_n | 403_n | mash_n |",
             "|---|---:|---:|---:|---:|---:|"]
    for one in walks:
        result = follows.get(one.door_id)
        dated = sum(1 for r in one.rows if r.when)
        walled = one.walled_n + (result.walled if result else 0)
        lines.append(
            f"| `{one.door_id}` | {one.count} | {dated} | {one.count - dated} | "
            f"{walled} | {one.mash_n} |")
    total_mash = sum(w.mash_n for w in walks)
    lines.append("")
    lines.append(
        f"`mash_n` totals **{total_mash}**: a row whose address is the list's "
        f"own URL keys a whole desk to one identity (§2 Forbidden), and the "
        f"field tick opens a row's address — so a mashed row would have sent "
        f"every fetch at the list page and written one page's date onto every "
        f"happening on the desk. Following permalinks is only safe while this "
        f"is 0.")
    lines.append("")
    lines.append("**Why the rest are still NULL** — three different facts, and "
                 "only the first is about the desk:")
    lines.append("")
    lines.append("| desk | pages opened | page stated no date | page could not be read | "
                 "not asked (budget) | no followable address |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for one in walks:
        result = follows.get(one.door_id)
        why = null_reasons(one, result, patterns=patterns)
        lines.append(
            f"| `{one.door_id}` | {result.fetched if result else 0} | "
            f"{why['page stated no date']} | {why['page could not be read']} | "
            f"{why['not asked (budget)']} | {why['no followable address']} |")
    unasked = sum(null_reasons(one, follows.get(one.door_id), patterns=patterns)
                  ["not asked (budget)"] for one in walks)
    lines.append("")
    lines.append(
        f"The budget for this tick is **{budget} event pages per desk** (the "
        f"founder's cap for this ticket). **{unasked}** happening(s) with a "
        f"followable address were NOT opened by it: their clocks are UNASKED, "
        f"not absent, so `dated_n` is a FLOOR and `still_null_n` is a CEILING "
        f"on what these desks actually leave dateless. Raising the cap is the "
        f"next ticket's decision, not this table's finding.")
    return "\n".join(lines)


def what_the_pages_said(follows: Mapping[str, FollowResult]) -> str:
    """What the OPENED pages actually stated, counted by reason.

    Without this, a live run reports `still_null_n = 1568` and there is nothing
    to do about it. With it, the same run says whether those pages published no
    date at all, stated one only in their plumbing, or printed a clock the day
    never came with — three different repairs, and the next ticket is whichever
    one is largest (ONE-LIVE-ENTITY-SPLIT-LAW.md §9.3).
    """
    counts: Dict[str, int] = {}
    pages = 0
    for result in follows.values():
        for read in result.reads:
            pages += 1
            for code in read.codes:
                counts[code] = counts.get(code, 0) + 1
    if not pages:
        return "_No event page was opened on this run, so there is nothing to count._"
    out = ["| the page said | pages | of opened |", "|---|---:|---:|"]
    for code, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        out.append(f"| `{code}` | {count} | {100 * count // pages}% |")
    out.append("")
    out.append(f"{pages} event page(s) opened. A page can carry more than one "
               f"reason (a date refusal and a place refusal are separate), so "
               f"these do not sum to the page count.")
    # R-115's EXPOSURE, printed rather than argued. A precise time taken from
    # markup on a page whose card printed no clock at all is correct on every
    # desk that simply says nothing about time — and it is also the only way a
    # word clock in a language this repo cannot read reaches a reader. Nothing
    # is refused here; the number is the size of the residual on real desks,
    # which is what the record needs and what four rounds of arguing it did not
    # produce.
    lonely = sum(1 for result in follows.values()
                 for read in result.reads if read.clock_uncorroborated)
    out.append("")
    out.append(f"**{lonely} of {pages}** opened page(s) took a PRECISE time from "
               f"markup while their own card printed no clock at all. Those rows "
               f"are right whenever the card says nothing about time, and they "
               f"are the whole surface on which an unreadable word clock "
               f"(R-115) could disagree — so this count, not the record's "
               f"prose, is the residual's size on this desk.")
    # The codes say WHICH repair; the sentences say what the pages actually
    # printed. A code counted at 100% and never quoted is still not something a
    # person can act on — the next ticket needs the desk's own words.
    seen: List[str] = []
    for result in follows.values():
        for read in result.reads:
            for code, sentence in zip(read.codes, read.refusals):
                line = f"- `{code}` — {read.url}: {sentence}"
                if line not in seen and len(seen) < 6:
                    seen.append(line)
    if seen:
        out.append("")
        out.append("What that looked like, in the pages' own words:")
        out.append("")
        out.extend(seen)
    return "\n".join(out)


def sample_rows(walks: Sequence[DeskWalk], n: int = 3) -> str:
    """A few rows as a person would read them: the address, the clock, the place.

    Rows the field tick actually opened come first — those are the ones this
    ticket is evidence about — and each says which page stated what, so a filled
    hole can never be mistaken for something the list card printed.
    """
    picked = [r for one in walks for r in one.rows if r.detail_url and r.when]
    picked += [r for one in walks for r in one.rows if r.detail_url and not r.when]
    picked += [r for one in walks for r in one.rows if not r.detail_url]
    out = ["| # | listing_url | start_time | place | filled from the event page |",
           "|---:|---|---|---|---|"]
    for i, row in enumerate(picked[:n], 1):
        out.append(
            f"| {i} | {_cell(row.listing_url)} | {_cell(row.when)} | "
            f"{_cell(row.place_text)} | "
            f"{_cell(', '.join(row.filled_from_detail) or '—')} |")
    if not picked:
        out.append("| — | _no rows_ | — | — | — |")
    return "\n".join(out)


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
               ) -> Tuple[List[DeskWalk], Dict[str, DeskRegistration], object, str,
                          Dict[str, object]]:
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
    # The SAME fetcher walks the list and, later, opens each happening's own
    # page: one politeness delay, one user agent, one wall classifier. A second
    # fetcher for the field tick would be a second answer to "was that a wall?".
    fetchers: Dict[str, object] = {}
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
        fetchers[door.door_id] = fetch
        walks.append(walk(door, fetch, max_pages=max_pages, start_url=start_url,
                          kind_map=kind_map))
    return walks, registrations, tz, pack.timezone, fetchers


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

            # DISPUTE FIRST, RECORD SECOND (evaluator PR #229 r9). The order
            # was the other way round, and it quietly broke the recovery this
            # tool ADVERTISES. `existing_keys` reads the NEWEST statement for a
            # key, so a drift candidate written after a FAILED dispute becomes
            # the thing tomorrow's run compares against: no drift is seen, the
            # row is skipped, and the published event stays `confirmed` while
            # its own desk contradicts it — with the run's own "re-run this
            # tool, it will re-detect these" telling an operator otherwise.
            # Disputing first means a failure leaves the store EXACTLY as it
            # was, so the next run sees the same drift and tries again. That is
            # what makes the printed instruction true.
            if against:
                try:
                    verdict = dispute(event_id)
                except Exception as exc:  # noqa: BLE001 — a row we could not flag fails the run
                    verdict = (f"COULD NOT DISPUTE published row {event_id} "
                               f"({type(exc).__name__}: {exc}) — it may still "
                               f"read as confirmed")
                    out["dispute_failures"].append((event_id, verdict))
                    out["failed"].append((
                        w, f"{verdict}. NOTHING was recorded for this row, "
                           f"deliberately: the next run must see the same drift "
                           f"and retry rather than mistake this correction for "
                           f"the desk's settled word"))
                    continue
            else:
                verdict = (f"published row {event_id} is left alone: this is "
                           f"corroboration, not a contradiction — nothing the "
                           f"desks say about it has changed")
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


#: How many planned rows the report prints in full. A live walk plans over a
#: thousand, and a thousand-row markdown table is not a deliverable anybody
#: reads — it also buries the counters this ticket is judged on. The cap is on
#: the PRINTING only: every row is still planned, still counted, and the total
#: is stated beside the sample so the table can never read as the whole plan.
PLAN_ROWS_SHOWN = 25


def plan_table(writes: Sequence[CandidateWrite], *, limit: int = PLAN_ROWS_SHOWN) -> str:
    out = ["| # | key | desks | title | place | starts | clock |",
           "|---:|---|---|---|---|---|---|"]
    for i, w in enumerate(writes[:limit], 1):
        out.append("| {} | `{}` | {} | {} | {} | {} | {} |".format(
            i, _cell(w.ingest_key), _cell(" + ".join(w.vias)), _cell(w.title),
            _cell(w.extracted.get("venue_name")), _cell(w.start_time),
            "stated" if w.start_time else _cell(w.clock_hole)))
    if len(writes) > limit:
        out.append("")
        out.append(f"_Showing the first {limit} of {len(writes)} planned rows. "
                   f"The rest are planned, counted in every number on this page, "
                   f"and simply not printed._")
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
    ap.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES,
                    help="page ceiling for the LIST walk (unchanged by this ticket)")
    ap.add_argument("--follow-budget", type=int, default=DEFAULT_BUDGET,
                    help="event pages the field tick may open PER DESK "
                         f"(default {DEFAULT_BUDGET}); rows past it are counted "
                         f"as unasked, never as dateless")
    ap.add_argument("--no-follow", action="store_true",
                    help="do not open any event page; rows keep whatever the "
                         "list card stated")
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

    if args.follow_budget < 0:
        print("ERROR: --follow-budget must be zero or more.", file=sys.stderr)
        return 2

    try:
        walks, registrations, tz, tz_id, fetchers = walk_doors(
            args.locale, door_ids, real=args.real, max_pages=args.max_pages,
            timeout=args.timeout, min_interval=args.min_interval)
    except (LocalePackError, DeskWalkError, DeskPublishError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    # The field tick, before the union: the union keys on the night, so a date
    # an event page states has to be on the row BEFORE two desks are compared —
    # otherwise one desk's dated row and another's hole never meet.
    patterns = load_patterns()
    follows: Dict[str, FollowResult] = {}
    if not args.no_follow:
        follows = follow_walks(
            walks, fetchers, budget=args.follow_budget,
            as_of=datetime.now(tz).date(), patterns=patterns)

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
    print("## 2. The split — did the list become many happenings?")
    print()
    print(split_table(walks))
    print()
    print("## 3. Following the permalink — date and place from the event page")
    print()
    if args.no_follow:
        print("`--no-follow`: no event page was opened. Every clock below is "
              "whatever the LIST card stated, which for most rows is a hole.")
    else:
        print(follow_table(walks, follows, budget=args.follow_budget,
                           patterns=patterns))
        print()
        print("**What the opened pages said** — so a NULL is a repair, not a "
              "number:")
        print()
        print(what_the_pages_said(follows))
        print()
        print("Three sample rows, as a person would read them:")
        print()
        print(sample_rows(walks))
        for each in walks:
            result = follows.get(each.door_id)
            if result is None:
                continue
            for note in result.notes:
                print(f"- `{each.door_id}`: {note}")
            if not result.eligible:
                print(f"- `{each.door_id}`: no row on this desk carries an "
                      f"address a committed identity pattern calls one "
                      f"happening on this host, so the field tick opened "
                      f"nothing. That is a pattern-table fact, not a finding "
                      f"about the desk.")
            for url, why in result.queued[:5]:
                print(f"- `{each.door_id}` queued: {url} — {why}")
    print()
    print("## 4. The write plan")
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
        print("## 5. Nothing was written")
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

    print("## 6. What happened to each row")
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
    print("## 7. Before / after — what the site serves")
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
        print("## 8. FAILED — published rows are live and mislabelled")
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
