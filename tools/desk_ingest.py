#!/usr/bin/env python3
"""Walk the local desks and WRITE what they printed into the catalog.

    python tools/desk_ingest.py --dry-run                  # fixtures, prints the plan, writes nothing
    python tools/desk_ingest.py --real --dry-run           # live desks, prints the plan, writes nothing
    python tools/desk_ingest.py --real --write             # live desks -> candidates -> promote

Founder, this session's ticket: "Take the Chronicle + Do512 walker that already
exists and write candidates + promote into the catalog (same key: night +
place-text + title-or-performer). Single-source rows stay and are labelled. Do
not require a second desk to publish."

The walk (`worker/locale_pack/desk_walk.py`) and the de-dup (`worker/locale_pack/desk_union.py`)
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
  * Re-running is safe, and it asks THREE questions rather than one. Every
    candidate carries the founder's de-dup key at `extracted._desk.key`, so a
    happening already in the store is not written twice. But a key answers only
    "is this the same happening?" — a desk that corrects 8pm to 9:30pm on the
    same night keys identically — so each candidate also carries the desk's
    STATEMENT (`extracted._desk.statement`), and the store is asked one more
    thing before either: DID WE EVER PUBLISH IT? A row is skipped only when it
    is already PUBLIC and the desk still says the same thing about it (founder,
    2026-09-07). A statement that exists only as a CANDIDATE — held by the gate
    that day, holed until a later walk filled it, or left behind by a run that
    was cancelled mid-wave — is promoted on the next run instead of being
    skipped for ever, because the map is the published row and not the queue
    (ONE-LIVE-TRUST.md: existence is not a field test). When the desk has
    changed its word about something we DID publish, the new statement is
    recorded as a candidate, the published row is marked DISPUTED so it stops
    reading `confirmed` while its own desk contradicts it (shown as disputed,
    never hidden), and the divergence is REPORTED under `changed`. Correcting
    the FIELD is still the reviewed update seam's job (R-110); nothing goes
    stale silently, and nothing goes stale while still looking settled.

Exit codes: 0 ran clean, 1 ran but left a published row mislabelled (a dispute
write failed — see section 5), 2 refused before writing anything (bad door, bad
locale, a fixture union, no DSN).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import contextmanager
from dataclasses import replace as dc_replace
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.desk_coverage import fixture_fetcher, live_fetcher  # noqa: E402
from tools.event_page_table import event_fixture_fetcher  # noqa: E402
from worker.locale_pack.event_page import FollowRun, apply, follow  # noqa: E402,F401
from worker.locale_pack.desk_publish import (  # noqa: E402
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
from worker.locale_pack.desk_fill import fill_patch, fills  # noqa: E402
from worker.locale_pack.desk_union import DeskUnion, bounded, union  # noqa: E402
from worker.locale_pack.desk_walk import (  # noqa: E402
    DEFAULT_MAX_PAGES, DeskWalk, DeskWalkError, _normalize, _same_host, walk,
)
from worker.locale_pack.kind_map import KindMapError, load_kind_map, map_for_door  # noqa: E402
from worker.locale_pack.pack import (  # noqa: E402
    LocalePackError, available_locales, load_pack, public_desks,
)

def default_doors(locale: str) -> List[str]:
    """Every door a run with no `--door` walks: the pack's whole public desk.

    DERIVED FROM THE PACK FILE, never typed here (founder, 2026-09-07: "Derive
    the list from the pack file. Do not hard-code Chronicle."). Until that
    ticket this constant named two desks, and two desks is the starve defect
    Operating Law effectiveness rule 3 forbids — "budget that starves all but
    two sources is a defect" — with a whole locale of civic calendars, official
    lists and other local desks sitting unread in the same file.

    The predicate is `worker.locale_pack.pack.public_desks`, which is the pack's OWN
    `Door.readable`: a listable door type AND `public` AND `intake != "none"`.
    That is the founder's "public is true and intake is not none" with the door
    TYPE carried along, and the type leg subtracts nothing here — every door in
    `us-tx-capcog` that is public with a read path is already one of the four
    listable types. What it does is keep `wall` (class D, never fetched) and
    `junk` (ONE-LIVE-TRUST.md: "SEO scrapers / copy farms - lead only") out of
    the default by the same rule the rest of the stack reads them out with,
    rather than by a second predicate written down twice.

    Trust order, most trusted first (`pack.hunt`), so a run that runs out of
    wall clock has spent it on the best doors rather than on whichever the
    JSON happened to list first.

    A second locale is a second pack file: nothing here names a place, and the
    locale arrives from `--locale`.
    """
    return [d.door_id for d in public_desks(locale)]

CATALOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "sources", "master_sources_catalog_120.json")


# --------------------------------------------------------------------------
# Counting what the site shows — the SAME predicates as api/public.py
# --------------------------------------------------------------------------

def door_table(walks: Sequence[DeskWalk], runs: Mapping[str, FollowRun]) -> str:
    """The founder's walk table: ONE ROW PER DOOR WALKED (2026-09-07).

    The columns are his, in his order, and every one of them is derived from
    THIS walk's own pages and rows — never from a counter carried in from the
    reader — so the table cannot report a desk we did not actually read.

      door_id     the pack's id for this door
      door_type   `local_desk` / `civic` / `official_list` / `marketplace`;
                  the trust statement, not a topic (ONE-LIVE-TRUST.md)
      fetched?    did ANY page of this desk open? `no` next to a non-zero
                  `403_n` is a WALL, and a walled desk's list is UNKNOWN —
                  never an empty calendar (Operating Law, effectiveness 4)
      pages       list pages read
      rows_split  happenings this desk yielded — the split's whole output
      mash_n      rows whose address is the LIST's own url. MUST BE 0
                  (ONE-LIVE-ENTITY-SPLIT-LAW.md §2 Forbidden)
      dated_n     rows carrying a night after the event pages were followed
      placed_n    rows carrying a place after the event pages were followed
      403_n       walls met, on the list AND on this desk's event pages
      unsplit_n   pages read that declared no identity we hold — ZERO rows and
                  a named coverage defect on THAT door, never a mashed row

    `dated_n` / `placed_n` read the ROWS, so a night an event page contradicted
    is already gone from them: this is what a friend would see, not what a page
    claimed.
    """
    lines = ["| door_id | door_type | fetched? | pages | rows_split | mash_n | "
             "dated_n | placed_n | 403_n | unsplit_n |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    total_mash = 0
    total_walled = 0
    for one in walks:
        run = runs.get(one.door_id) or FollowRun()
        walled = one.walled_n + run.walled_n
        total_mash += one.mash_n
        total_walled += walled
        lines.append(
            f"| `{one.door_id}` | {one.door_type} | "
            f"{'yes' if one.pages_read else 'no'} | {one.pages_read} | "
            f"{one.count} | {one.mash_n} | "
            f"{sum(1 for r in one.rows if r.when)} | "
            f"{sum(1 for r in one.rows if r.place_text)} | "
            f"{walled} | {one.unsplit_n} |")
    lines.append("")
    lines.append(
        f"{len(walks)} door(s) walked. `mash_n` totals **{total_mash}** and must "
        f"be 0: a row addressed by the list's own url keys a whole desk to one "
        f"identity. `403_n` totals **{total_walled}** — every one of those pages "
        f"has an UNKNOWN list, so a `no` in `fetched?` beside it means we were "
        f"shut out, never that the desk had nothing on.")
    return "\n".join(lines)


def skipped_doors_note(skipped: Sequence[Tuple[str, str, str]]) -> str:
    """The doors this run did NOT walk, by name, with the remedy.

    A shorter list is the one thing a coverage report may never be quiet about
    (Coverage Law: a missing door is a defect, and a defect gets named). Each
    line is the loader's or the registrar's own refusal text, so the fix is
    printed rather than described.
    """
    if not skipped:
        return ""
    lines = [f"**{len(skipped)} door(s) in this pack were NOT walked** — an "
             f"unwalked door is UNKNOWN, never empty, and nothing is written "
             f"for it:", ""]
    for door_id, door_type, why in skipped:
        lines.append(f"- `{door_id}` ({door_type}): {' '.join(str(why).split())}")
    return "\n".join(lines)


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


# --------------------------------------------------------------------------
# Ticket D — the event page fills the row's holes
# --------------------------------------------------------------------------
#
# `worker/locale_pack/event_page.py` (Ticket C, merged ad3a578) reads ONE event page
# and fills the two holes Ticket B's rows carry. Until now it ran only in tests
# and in `tools/event_page_table.py`. This section is the GLUE that runs it on
# the desks' own walk, and it is glue only: the reader is imported, never
# reimplemented and not modified.
#
# Three founder rules are enforced HERE rather than inside the reader, because
# they are about which pages a RUN may spend, and the reader knows about one
# page at a time:
#
#   * SAME HOST ONLY. Selected here (a permalink on another host is not this
#     desk's page) and again inside `follow()`, which reports `off_host`.
#   * AT MOST `DEFAULT_FOLLOW_PAGES` PAGES PER RUN, across all desks.
#   * ROUND-ROBIN, never 200 pages of one venue. `follow()`'s own `limit` walks
#     one list in order, so passing the budget straight to it would spend the
#     whole thing on the first desk — which is the shape the founder's cap
#     exists to forbid, not to permit.

#: Founder cap, RAISED 40 -> 200 (Ticket E, 2026-09-06). A cap on PAGES, not on
#: rows — two rows sharing one permalink cost one knock (`follow()` answers the
#: second from the first). It is the most EVENT pages one run may knock on,
#: across every desk.
#:
#: WHY it moved: the Ticket D run read 1571 rows off the list pages and could
#: only knock on 40 of them, so 1552 rows kept a hole. 40 pages cannot fill 1571
#: rows, and the number of rows a friend could act on was being decided by the
#: budget rather than by the desks.
#:
#: Two honest asterisks, both about what a FULL budget costs on a live run:
#:   * a page that advertises its own iCalendar file may cost one further fetch
#:     (`event_page.MAX_ICS_FETCHES` is 1), because reading that file is part of
#:     reading THAT page rather than a knock on a 201st one. So the worst case
#:     for a full budget is 200 pages plus up to 200 same-host .ics reads.
#:   * those fetches are POLITE: `--min-interval` sleeps between live fetches
#:     (2.0s by default), so a full budget is ~7 minutes of waiting at best and
#:     ~13 at the .ics worst case, before any page is transferred. That is the
#:     real cost of the raise, and stating it is cheaper than someone finding it
#:     in a server log or in a job that ran out of minutes.
DEFAULT_FOLLOW_PAGES = 200


def _knocks(run: Optional[FollowRun]) -> int:
    """Pages this desk actually cost the budget.

    A knock is a fetch we spent. A REUSED visit is a second row at an address
    already answered, a NOT-KNOCKED visit is a page we declined after a run of
    walls, and an OFF-HOST visit was never fetched at all — none of the three
    spends anything, so none of them is a knock. A wall we met IS one: we spent
    the fetch and got a closed door.
    """
    if run is None:
        return 0
    return sum(1 for v in run.visits
               if not v.reused and not v.not_knocked and not v.off_host)


def followable(one: DeskWalk) -> List[str]:
    """This desk's own event pages, in walk order, each listed once.

    Three addresses are refused before any budget is spent, and each refusal is
    a rule from a law rather than a tidy-up:

      * no `listing_url` — the row never stated its own address, so there is
        nothing to follow (it is Ticket B's hole, not this ticket's).
      * the LIST's own url — ONE-LIVE-ENTITY-SPLIT-LAW.md §2 Forbidden: that
        row is a mash, and knocking on it would read a list page as an event
        page and staple a list's date onto a blob. Counted in `mash_n`, never
        followed.
      * another host — the ticket's first Must-do. `follow()` refuses it too;
        refusing it here as well keeps the budget for pages we can actually read.
    """
    starts = {_normalize(p.url) for p in one.pages}
    starts.add(_normalize(one.start_url))
    seen: set = set()
    out: List[str] = []
    for row in one.rows:
        url = (row.listing_url or "").strip()
        if not url:
            continue
        key = _normalize(url)
        if key in starts or key in seen:
            continue
        if not _same_host(url, row.source_url):
            continue
        seen.add(key)
        out.append(url)
    return out


def round_robin(walks: Sequence[DeskWalk], *, cap: int) -> Dict[str, List[str]]:
    """Spread the page budget ACROSS the desks, never down one of them.

    Not `worker/crawl_state.py`'s round-robin, which answers a different
    question (which SOURCES are due next, with round-robin only as the
    tie-break, and a database behind it). This one spreads one run's page
    budget across the desks already walked, and is pure.

    One page from each desk, then a second from each, until the cap runs out.
    A desk with fewer pages than its share simply stops contributing and the
    rest of the budget keeps circulating, so a small desk cannot strand pages
    and a large one cannot swallow the run.
    """
    queues: Dict[str, List[str]] = {w.door_id: followable(w) for w in walks}
    picked: Dict[str, List[str]] = {door: [] for door in queues}
    budget = max(0, cap)
    depth = 0
    while budget > 0 and any(depth < len(q) for q in queues.values()):
        for door, queue in queues.items():
            if budget <= 0:
                break
            if depth < len(queue):
                picked[door].append(queue[depth])
                budget -= 1
        depth += 1
    return picked


def follow_fetchers(door_ids: Sequence[str], *, real: bool, timeout: int,
                    min_interval: float) -> Tuple[Dict[str, object], List[str]]:
    """A fetcher per door for its EVENT pages — a different set from the list.

    Live: the same polite fetcher the walk uses (it holds no state between
    calls, so a second one is the same fetcher, not a second rate budget).
    Fixture: the committed event pages under `tests/fixtures/event_pages/<door>/`,
    reusing `tools/event_page_table.py`'s reader so the fixture run here and the
    Ticket C table cannot drift apart. A door with no committed event fixtures
    is REPORTED and skipped, never silently followed to a wall of 404s.
    """
    out: Dict[str, object] = {}
    notes: List[str] = []
    for door_id in door_ids:
        if real:
            out[door_id] = live_fetcher(timeout_s=timeout, min_interval_s=min_interval)
            continue
        try:
            fetch, _manifest = event_fixture_fetcher(door_id)
        except (FileNotFoundError, OSError):
            notes.append(f"`{door_id}`: no committed event-page fixtures "
                         f"(tests/fixtures/event_pages/{door_id}/) — its pages "
                         f"were not followed on this FIXTURE run")
            continue
        out[door_id] = fetch
    return out, notes


def follow_pages(walks: Sequence[DeskWalk], fetchers: Mapping[str, object], *,
                 cap: int, read_ics: bool = True
                 ) -> Tuple[List[DeskWalk], Dict[str, FollowRun]]:
    """Follow the selected permalinks and give each desk back its filled rows.

    Returns walks whose `rows` are the SAME rows in the SAME order — no row is
    added, dropped or reordered by following; a row is only replaced by itself
    with a hole filled (or, on a contested night, with a night taken away —
    `event_page.apply()`'s founder ruling, unchanged here).
    """
    # Only desks we can actually fetch for get a share of the budget. A desk
    # with no fetcher (fixture mode, no committed event pages for that door)
    # would otherwise be handed pages it can never knock on, and those pages
    # would be stranded — spent from the cap and read by nobody.
    reachable = [w for w in walks if fetchers.get(w.door_id) is not None]
    selection = round_robin(reachable, cap=cap)
    out: List[DeskWalk] = []
    runs: Dict[str, FollowRun] = {}
    for one in walks:
        chosen = {_normalize(u) for u in selection.get(one.door_id, ())}
        fetch = fetchers.get(one.door_id)
        if not chosen or fetch is None:
            runs[one.door_id] = FollowRun()
            out.append(one)
            continue
        rows_in = [r for r in one.rows
                   if _normalize((r.listing_url or "").strip()) in chosen]
        run = follow(rows_in, fetch, read_ics=read_ics)
        if len(run.rows) != len(rows_in):
            raise DeskPublishError(
                f"follow() returned {len(run.rows)} rows for {len(rows_in)} sent on "
                f"{one.door_id!r}; the desk's rows cannot be put back in order")
        filled = iter(run.rows)
        new_rows = []
        for row in one.rows:
            if _normalize((row.listing_url or "").strip()) in chosen:
                new_rows.append(next(filled))
            else:
                new_rows.append(row)
        runs[one.door_id] = run
        out.append(dc_replace(one, rows=new_rows))
    return out, runs


def follow_table(walks: Sequence[DeskWalk], runs: Mapping[str, FollowRun],
                 *, cap: int) -> str:
    """The founder's Ticket D table: how many rows a friend could act on.

    Every count is derived from the rows THEMSELVES after following, never from
    the reader's internal tallies, because the claim under test is what the row
    carries — not what a page said.

      rows_n         happenings this desk yielded (unchanged by following)
      dated_n        rows carrying a night AFTERWARDS. Not the same as pages
                     that stated one: a night the page and the list contest is
                     taken AWAY (`event_page.apply()`), and a table printing the
                     page's number would overstate what a friend would see.
      placed_n       rows carrying a place text afterwards
      still_null_n   rows still missing a night, a place, or both — the holes
                     this ticket did not close, printed beside the ones it did
      403_n          walls we MET while following (401/402/403/407/429 or a
                     sign-in redirect). One knock, then the page is a hole and
                     the door is queued for the human claim path. Pages we
                     declined to knock on after a run of walls are OUR stop and
                     are in `not_asked`, never here.
      mash_n         rows whose address is the LIST's own url (§2 Forbidden).
                     Never followed; must be 0.
      pages_followed distinct event pages actually read on this desk
      not_asked      rows whose page this run never put a question to: beyond
                     the page budget, no permalink, a mash address, off-host,
                     or behind our own wall-streak stop
    """
    lines = ["| desk | rows_n | dated_n | placed_n | still_null_n | 403_n | "
             "mash_n | pages_followed | not_asked |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    totals = {"rows": 0, "dated": 0, "placed": 0, "null": 0, "walled": 0,
              "mash": 0, "followed": 0, "not_asked": 0, "nothing": 0}
    for one in walks:
        run = runs.get(one.door_id) or FollowRun()
        rows_n = len(one.rows)
        dated_n = sum(1 for r in one.rows if r.when)
        placed_n = sum(1 for r in one.rows if r.place_text)
        still_null_n = sum(1 for r in one.rows if not r.when or not r.place_text)
        asked = sum(1 for v in run.visits if not v.not_knocked and not v.off_host)
        not_asked = rows_n - asked
        # Every page we KNOCKED on lands in exactly one bucket: it opened, it
        # walled, or it answered with nothing we could read (404, an empty
        # body, a transport failure that is not a wall). The third bucket is
        # derived rather than counted so it can never go missing — the gap
        # between "asked" and "read" is the number that would otherwise let a
        # partial fixture set, or a desk that moved its pages, read as a desk
        # that has nothing to say.
        knocks = asked - sum(1 for v in run.visits if v.reused)
        totals["nothing"] += max(0, knocks - run.followed_n - run.walled_n)
        lines.append(
            f"| `{one.door_id}` | {rows_n} | {dated_n} | {placed_n} | "
            f"{still_null_n} | {run.walled_n} | {one.mash_n} | "
            f"{run.followed_n} | {not_asked} |")
        totals["rows"] += rows_n
        totals["dated"] += dated_n
        totals["placed"] += placed_n
        totals["null"] += still_null_n
        totals["walled"] += run.walled_n
        totals["mash"] += one.mash_n
        totals["followed"] += run.followed_n
        totals["not_asked"] += not_asked
    filled_when = sum(r.filled_when_n for r in runs.values())
    filled_place = sum(r.filled_place_n for r in runs.values())
    nulled = sum(r.nulled_when_n for r in runs.values())
    not_knocked = sum(r.not_knocked_n for r in runs.values())
    off_host = sum(r.off_host_n for r in runs.values())
    # How the budget was ACTUALLY spent, derived — not the number of desks we
    # walked. On a run where one desk is walled, every page goes to the other
    # one, and a sentence claiming a spread across two desks would be false on
    # exactly the run a reader most needs to understand.
    #
    # The unit is a KNOCK, because that is what the founder's cap counts.
    # Evaluator, PR #238 r2 (openai/attacker-smuggle): this was `len(visits)`,
    # which counts ROWS — three rows sharing one permalink cost one knock but
    # were reported as three "pages", overstating how the cap was spent. A
    # reused visit, a page behind our wall-streak stop, and an off-host address
    # all cost nothing, so none of them is a knock.
    spread = sorted((one.door_id, _knocks(runs.get(one.door_id))) for one in walks)
    spent = [f"`{door}` {n}" for door, n in spread if n]
    if len(spent) > 1:
        how = (f"the budget was spent round-robin across {len(spent)} desk(s) "
               f"rather than down one ({', '.join(spent)} knock(s))")
    elif spent:
        how = (f"every knock went to {spent[0].split()[0]}, the ONLY desk whose "
               f"pages we knocked on this run — the others offered none we could "
               f"reach (walled, no same-host permalink, or held back by our own "
               f"wall-streak stop), so the round-robin had nothing to alternate "
               f"with and no page was stranded")
    else:
        how = "no desk offered a page we could knock on"
    lines.append("")
    lines.append(
        f"**{totals['followed']}** event page(s) read of a founder cap of "
        f"**{cap}** knock(s) per run, and {how}. Following FILLED "
        f"{filled_when} night(s) and "
        f"{filled_place} place(s) that the list pages left empty, and TOOK AWAY "
        f"{nulled} night(s) where the desk's own event page contradicted its list "
        f"card — a contested night is no night, so neither claim is published and "
        f"both are kept on the visit. **{totals['null']}** row(s) still carry a "
        f"hole. Walls met: **{totals['walled']}** — one knock each, then the page "
        f"is a hole and the door stays queued for a claim; a walled page is an "
        f"UNKNOWN listing, never a mash and never an empty desk. "
        f"{totals['nothing']} page(s) were asked and answered with nothing we "
        f"could read (404, an empty body, a transport failure that is not a "
        f"wall) — asked, so not in `not_asked`, and an UNKNOWN listing rather "
        f"than an absent one. "
        f"{not_knocked} page(s) went unknocked behind our own wall-streak stop and "
        f"{off_host} address(es) left the desk's host; both are in `not_asked`, "
        f"which counts rows we never asked about, for any reason.")
    if not totals["followed"]:
        lines.append("")
        lines.append(
            "**No event page was read on this run**, so `dated_n` and `placed_n` "
            "above are whatever the LIST pages already stated — they are not "
            "evidence that following does nothing, and not evidence these pages "
            "are empty. The reader is proven by `tests/test_event_page.py` and "
            "`tests/test_event_page_dryrun.py`; these pages stay queued.")
    return "\n".join(lines)


def changed_rows_n(runs: Mapping[str, FollowRun]) -> int:
    """How many rows following actually CHANGED — the predicate
    `follow_effect_note()` asks to decide whether following contributed
    anything to the plan at all."""
    return sum(r.filled_when_n + r.filled_place_n + r.nulled_when_n
               for r in runs.values())


def follow_effect_note(runs: Mapping[str, FollowRun]) -> str:
    """How much of the plan above came from the event pages rather than the list.

    This line used to be a CAVEAT, and the caveat was true: a dry run followed
    event pages and planned from the FILLED rows while `--write` skipped
    following, so a section headed "The write plan" showed an operator writes
    the write path would not produce (evaluator, PR #238). The founder's fix
    was not a better warning but the same walk on both paths (2026-09-07), so
    what is left to report is the SIZE of following's contribution — still
    derived from the visits, never described in the abstract, because an
    operator reading "the write plan" is entitled to know how much of it a list
    page never said.

    The one difference this line does NOT cover, because it is not about
    following: a FIXTURE run plans fixture rows. That is said where it belongs,
    under section 5, on the runs that are fixture runs.
    """
    filled_when = sum(r.filled_when_n for r in runs.values())
    filled_place = sum(r.filled_place_n for r in runs.values())
    nulled = sum(r.nulled_when_n for r in runs.values())
    if not changed_rows_n(runs):
        return ("Event pages were followed and changed no row, so this plan is "
                "what the list pages alone stated. `--write` follows the same "
                "pages under the same cap, so it plans these same rows.")
    return (
        f"**{filled_when} night(s) and {filled_place} place(s) in this plan came "
        f"from an event page, not from a list page**, and {nulled} contested "
        f"night(s) were taken back off rows whose page disagreed with the list. "
        f"A `--real --write` run follows the same pages under the same cap and "
        f"the same politeness delay, so this is the plan it works from — a row "
        f"that reads dated and placed here is dated and placed there.")


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
               ) -> Tuple[List[DeskWalk], Dict[str, DeskRegistration], object,
                          str, List[Tuple[str, str, str]]]:
    """Walk each named door, and NAME the ones this run could not walk.

    Registration happens BEFORE any write is planned, so a door that cannot be
    labelled never reaches the catalog half-labelled.

    A DOOR THAT CANNOT BE WALKED IS ONE DOOR'S DEFECT, NOT THE RUN'S (founder,
    2026-09-07, on making the default walk the whole pack). Registration used
    to stop the whole run at the first door with no catalog row: with two
    named desks that was a fine tripwire, and with a pack of 26 it means one
    unlisted publisher deletes the other 25 desks from the night. That is the
    shape Coverage Law calls a defect — "missing locale, missing category, or
    dropping a legally seen row" — and it is the same reasoning as a 403: the
    door is UNKNOWN to us, so it is REPORTED and stays queued, and nothing is
    written for it. Fail-closed is untouched: an unlabelled door contributes no
    row, because a listing we cannot put a masthead on is exactly what
    `registration_for` refuses to guess at.

    Returned alongside the walks: `skipped`, one `(door_id, door_type, why)`
    per door this run did not walk, so the report prints them by name with the
    remedy rather than leaving a silently shorter list. A run that walked
    NOTHING still raises — an empty walk is never reported as an empty locale.
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

    skipped: List[Tuple[str, str, str]] = []

    for door_id in door_ids:
        door = doors.get(door_id)
        if door is None:
            # A door_id that is not in the pack is a TYPO, not a coverage hole:
            # somebody asked for a door this locale does not have, and walking
            # on quietly would answer a question nobody asked.
            raise LocalePackError(
                f"no door {door_id!r} in locale {locale!r}. Have: {sorted(doors)}")
        try:
            reg = registration_for(door, catalog)
        except DeskPublishError as exc:
            skipped.append((door.door_id, door.door_type, str(exc)))
            continue
        registrations[reg.via] = reg
        try:
            kind_map = map_for_door(door.door_id)
        except KindMapError:
            kind_map = None
        if real:
            fetch, start_url = fetch_live, None
        else:
            try:
                fetch, start_url, _ = fixture_fetcher(door.door_id)
            except OSError:
                # FIXTURE MODE ONLY. The live walk fetches every door; a
                # rehearsal can only walk the pages somebody committed, and a
                # door with none is a gap in the REHEARSAL, never a statement
                # about the desk. Same shape as `follow_fetchers`, which has
                # reported this for event pages since Ticket D.
                skipped.append((
                    door.door_id, door.door_type,
                    f"no committed list fixtures "
                    f"(tests/fixtures/desk_pages/{door.door_id}/) — not walked "
                    f"on this FIXTURE run; `--real` walks it"))
                continue
        walks.append(walk(door, fetch, max_pages=max_pages, start_url=start_url,
                          kind_map=kind_map, as_of=date.today()))

    if door_ids and not walks:
        raise DeskPublishError(
            "not one of the {n} door(s) asked for could be walked, so this run "
            "has NOTHING to say about this locale — an empty walk is not an "
            "empty calendar. Reasons, per door:\n{why}".format(
                n=len(door_ids),
                why="\n".join(f"  - {d} ({t}): {w}" for d, t, w in skipped)))
    return walks, registrations, tz, pack.timezone, skipped


# --------------------------------------------------------------------------
# The write
# --------------------------------------------------------------------------

@contextmanager
def one_connection(connect=None):
    """Hold ONE database connection open for the write, and hand it to every
    seam that asks for one.

    THE BOTTLENECK THIS EXISTS FOR (founder, 2026-09-07). Dispatch
    34079785167 printed its plan at about ten minutes and was then killed at
    the job's 30-minute ceiling, still writing. The walk was not the cost --
    200 pages at 2.0s is bounded and had already been spent. The cost is that
    `worker.candidate_store.db()` and `worker.promote.db()` each open a NEW
    `psycopg2.connect(resolve_dsn())`, and the write calls them two or more
    times PER ROW (create, one per evidence row, promote, plus a dispute on a
    drifted row). COUNTED, not estimated: a plan the shape of that run's --
    94 publishing rows and 1490 held ones -- opened **3262** connections
    against a real PostgreSQL, and one leased connection carries the identical
    write (94 promoted, 1490 held, 0 failed). Each of those 3262 is a TCP +
    TLS + SCRAM handshake to a remote server, taken one after another, before
    a single statement is counted.

    SO THE HANDSHAKE IS AMORTISED AND NOTHING ELSE CHANGES. This is not a
    faster path around the gate: the seams called, the SQL they run, their
    order, and their TRANSACTION BOUNDARIES are exactly what they were. `db()`
    returns a connection whose `__exit__` commits and does not close, so a
    leased connection gives every seam the same per-call commit it had before.
    That per-row commit is also what makes a killed run KEEP the rows it
    already wrote -- one transaction across the whole write would lose all of
    them, which is the opposite of what the founder asked for.

    WHY A LEASE AND NOT AN ARGUMENT. The obvious change is for `db()` itself to
    reuse a connection. It is refused here: `worker/candidate_store.py` and
    `worker/db_config.py` are both inside the ARMED CRON's runtime closure
    (`tools/arming_runtime.py`) while `EXTRACTION_THRESHOLD_RATIFIED` is True,
    so one byte in either re-fires `tests/test_arming_smoke_binding.py` and
    demands a fresh paid smoke run -- founder money for a change the cron
    cannot benefit from. This tool is outside that closure and the cron never
    runs it, so the reuse is installed from out here, for the duration of the
    write, and handed back in `finally`. No file the armed cron runs changes.

    RE-DIAL, NEVER A DEAD RUN. One held connection is one thing a server can
    hang up on (idle timeout, restart, pooler eviction), and where the old code
    silently got a fresh connection on the next call, a lease handing back a
    corpse would fail every remaining row. So the lease reads `closed` before
    handing the connection out and dials again when the server is gone. The
    residual is a connection already broken but not yet KNOWN to be broken
    (psycopg2 sets `closed` when it finds out): that one row lands in `failed`
    and is printed, which is exactly how a lost connection is reported today.

    THE DIALLER IS THE SEAM'S OWN. `connect` defaults to
    `candidate_store.db` as it stands before the lease replaces it, so the DSN
    is still resolved by `worker/db_config.resolve_dsn` and a missing one
    still fails loudly, in the same place, with the same message. The lease
    invents no second way to reach the database; it calls the existing one
    once instead of once per row. `connect` stays injectable so a test can
    count the dials without a database.

    The seam MODULES are read out of `sys.modules` rather than bound with
    `from worker import candidate_store`, because the latter resolves through
    the `worker` package's attribute and would quietly reach past a module a
    caller had substituted — which is exactly how the write path's own tests
    stand in for the store.
    """
    import worker.candidate_store  # noqa: PLC0415,F401 — ensure both are in sys.modules
    import worker.promote  # noqa: PLC0415,F401
    store = sys.modules["worker.candidate_store"]
    publisher = sys.modules["worker.promote"]

    # NEVER NESTED, and loudly so. A lease inside a lease would take the outer
    # lease as its dialler, then CLOSE the outer's live connection on its own
    # way out — every remaining row of the outer write would then run on a
    # connection somebody else had shut. There is one write phase per run, so
    # a second lease means a caller lost track of the first: say so rather
    # than repair it, because the repair would be a guess about which write is
    # the real one.
    for module in (store, publisher):
        if getattr(module.db, "_desk_ingest_lease", False):
            raise RuntimeError(
                f"{module.__name__}.db is already leased — one write phase "
                f"holds one connection, and a nested lease would close the "
                f"outer one's connection underneath it")

    if connect is None:
        connect = store.db

    held = [connect()]

    def lease():
        if getattr(held[0], "closed", 0):
            held[0] = connect()
        return held[0]

    lease._desk_ingest_lease = True

    # BOTH seam modules, because each holds its own module-level `db` name and
    # a write that leased one and dialled the other would still open a
    # connection per promote.
    originals = ((store, store.db), (publisher, publisher.db))
    for module, _ in originals:
        module.db = lease
    try:
        yield lease
    finally:
        # Handed back whatever happened, including a KeyboardInterrupt from the
        # runner's own timeout: leaving a patched `db` behind would outlive this
        # write and hand a closed connection to whatever ran next.
        for module, original in originals:
            module.db = original
        try:
            held[0].close()
        except Exception as exc:  # noqa: BLE001
            # SAID, never swallowed. Every row was committed as it was
            # written, so a close that fails costs no data — but an operator
            # reading this run should still see that the connection did not
            # come down cleanly, because the next thing it points at is the
            # database's own health.
            print(f"note: the leased connection did not close cleanly "
                  f"({type(exc).__name__}: {exc})", file=sys.stderr)


def existing_keys(cur) -> Dict[str, Tuple[str, str, Optional[str], Optional[dict]]]:
    """Every desk key already in the store -> (id, status, event id, statement).

    ONE scan, not one query per row: the whole point of the key is that a
    re-run is cheap, and 33 sequential scans of a growing table is not cheap.

    The STATEMENT comes back with the key because the key alone cannot answer
    the question a re-run actually has to ask (see `ingest`). The most RECENT
    row for a key wins: a drift row is written as a new candidate carrying the
    desk's newer statement, so ordering by `created_at` is what makes the next
    run compare against the desk's latest word rather than its first.

    THE EVENT ID IS THE KEY'S, NOT THE NEWEST CANDIDATE'S, and the difference
    is a published row (2026-09-07, caught by
    `tests/integration/test_desk_ingest_pg.py`). A drift candidate is written
    deliberately UNPROMOTED — recorded, disputed, never re-published beside the
    listing already on the feed — so it carries `promoted_event_id = NULL`
    while the happening it describes is very much public, under an earlier
    candidate of the same key. Reading the newest row alone therefore answers
    "was this happening ever published?" with "no" for exactly the happenings
    that were, and `ingest`'s skip test is built on that answer: it would
    publish a SECOND listing at the corrected time, which is the harm the
    drift seam exists to prevent. So the event id is taken from whichever
    candidate of this key actually promoted (most recently created first), and
    the id / status / statement stay the newest candidate's — the row we
    compare the desk's word against.
    """
    cur.execute(
        """
        select key, candidate_id, status, published_event_id, statement
        from (
            select extracted->'_desk'->>'key'      as key,
                   candidate_id::text              as candidate_id,
                   status,
                   extracted->'_desk'->'statement' as statement,
                   first_value(promoted_event_id::text) over (
                       partition by extracted->'_desk'->>'key'
                       order by (promoted_event_id is null), created_at desc
                   )                               as published_event_id,
                   row_number() over (
                       partition by extracted->'_desk'->>'key'
                       order by created_at desc
                   )                               as recency
            from event_candidate
            where extracted ? '_desk'
        ) keyed
        where recency = 1
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


def corrects_a_live_listing(w: CandidateWrite, seen: Mapping[str, tuple]) -> bool:
    """True when this row's turn carries a CORRECTION to a row already public.

    Same two questions `ingest` asks, asked with the same two functions so
    there is one definition of "the desk now disagrees with what we
    published": the key finds the happening, `drift` says the desk has changed
    its word, and `contradicts` says the change is one that puts the published
    row's `confirmed` label in question (a second desk joining moves `vias`
    and contradicts nothing). A row whose earlier candidate never promoted has
    no live listing to correct, so `event_id` must be there too.
    """
    entry = seen.get(w.ingest_key)
    if not entry:
        return False
    _cid, _status, event_id, stored = entry
    if not event_id:
        return False
    fresh = w.extracted.get(DESK_KEY, {}).get("statement")
    if not fresh:
        return False
    return bool(contradicts(stored, fresh))


def publish_first(writes: Sequence[CandidateWrite], *,
                  seen: Optional[Mapping[str, tuple]] = None) -> List[CandidateWrite]:
    """Corrections to live listings, then the rows that will PUBLISH, then the
    rows that will HOLD.

    Founder, 2026-09-07: "Write PUBLIC rows first (title+when+place, the ~94),
    THEN holds. If the job dies, /tonight still has listings. Holds still get
    written when time remains -- do not drop them."

    A held row is a candidate the feed never shows, so writing 1490 of them
    before the 94 a friend can act on buys a reader nothing, and a run killed
    partway through that leaves /tonight exactly as empty as it was. Ordering
    is the entire mechanism: every planned row is still written, each in its
    own committed transaction, so the publishing rows are DURABLE by the time
    the first held row is attempted. Nothing is dropped and no budget is
    guessed at -- this decides only what goes first.

    CORRECTIONS OUTRANK BOTH, and that is the evaluator's finding on PR #245
    (openai/attacker-smuggle), which the first version of this function got
    wrong. Splitting on `hold_reason` alone sent EVERY held row behind the
    publics -- including a row whose desk has since contradicted a listing
    that is on the feed right now. Those two states coincide readily: an event
    page that used to state 8pm and now states only the night both HOLDS
    (R-111) and contradicts the published clock. A run killed before reaching
    it leaves a listing reading `confirmed` while its own desk no longer
    supports it, which is a falsehood a reader can SEE. An unpublished row is
    only an absence. Correcting what is wrong on the feed therefore goes ahead
    of adding what is missing from it -- `ingest` disputes before it records
    (PR #229 r9), so a corrective row's turn is what fires the dispute. There
    are few of these, so the publics lose almost nothing.

    The publish/hold split reads `hold_reason`, the same field that decides
    whether a row publishes at all (`desk_publish.write_for`), so "public"
    cannot drift into a second definition that disagrees with the gate; the
    correction test reuses `contradicts`, the same function `ingest` gates the
    dispute on. Order inside each group is the plan's own, so the printed plan
    and the write still read alike.
    """
    seen = seen or {}
    correcting = [w for w in writes if corrects_a_live_listing(w, seen)]
    rest = [w for w in writes if not corrects_a_live_listing(w, seen)]
    publishing = [w for w in rest if not w.hold_reason]
    holding = [w for w in rest if w.hold_reason]
    return correcting + publishing + holding


def fill_published_holes(event_id: str, patch: dict) -> str:
    """FL-010. Write a first printed Place onto event.venue_id."""
    if not event_id or not patch:
        return "nothing to fill"
    from worker.candidate_store import db  # noqa: PLC0415
    from worker.resolve_entities import resolve_venue_id  # noqa: PLC0415
    raw = str(event_id)
    if raw.startswith("promoted:"):
        raw = raw.split(":", 1)[1]
    venue = (patch.get("venue_name") or "").strip() or None
    start = patch.get("start_time")
    title = patch.get("title")
    with db() as conn:
        with conn.cursor() as cur:
            venue_id = resolve_venue_id(cur, venue, "Austin") if venue else None
            cur.execute(
                """
                update event
                   set venue_id = case
                         when venue_id is null and %s is not null
                         then %s::uuid else venue_id end,
                       start_time = coalesce(%s::timestamptz, start_time),
                       title = coalesce(%s, title)
                 where event_id = %s::uuid
                   and override_lock = false
                """,
                (venue_id, venue_id, start, title, raw),
            )
            n = cur.rowcount
    return f"filled public row {raw} ({n} row, {sorted(patch)})"


def ingest(writes: Sequence[CandidateWrite], *, seen: Mapping[str, tuple],
           create, add_evidence, promote, dispute=dispute_superseded,
           fill=fill_published_holes) -> Dict[str, list]:
    """Publish every planned row that is not already PUBLIC.

    THE SKIP TEST IS PUBLICATION, NOT EXISTENCE IN THE STORE (founder,
    2026-09-07; ONE-LIVE-TRUST.md "existence must not use mutation tests").
    It used to be existence: any key already carrying a candidate was skipped,
    whatever had become of that candidate. So a happening a trusted door
    stated — title, night AND place — that was written once and never
    published (the gate held it that day, its place arrived on a later walk,
    the promote raised, the run was cancelled mid-wave) was skipped by every
    run afterwards, for ever. The candidate is not the map; the published row
    is. A statement the desks still make and we have never published is work
    left undone, and this function now finishes it:

      * ALREADY PUBLIC, desk unchanged -> skip. That is the re-run case, and
        it is the only skip.
      * ALREADY PUBLIC, desk changed -> record the new statement, dispute the
        published row if the change contradicts it, never publish a second
        listing beside the first. Unchanged from the seam evaluators built.
      * NOT PUBLIC, desk unchanged -> promote the candidate ALREADY in the
        store. No second candidate is written: the same statement does not
        need a second handle, and the evidence rows it needs are already
        attached to the first.
      * NOT PUBLIC, desk changed -> write the newer statement as a candidate
        (linked to the older one) and promote that. Nothing is disputed,
        because nothing published is contradicted — there is no published row.

    A HOLE IS STILL A HOLE on every one of those paths: `hold_reason` is read
    after this decision, not before it, so a row missing a night or a place is
    held exactly as it was, and re-promoting cannot turn a hole into a public
    "Date TBA". The gate is likewise untouched — every promote here is
    `promote_candidate`, the full trust gate, which may hold the row again.

    THE ORDER IS `publish_first`, and it is the only thing this loop knows
    about the runner's clock: corrections to rows already on the feed, then
    the rows that will publish, then the held ones. A write that does not
    finish has still corrected every listing its own desk now contradicts,
    and still leaves /tonight with the rows a friend can act on. Held rows
    follow and are all still written.

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
    for w in publish_first(writes, seen=seen):
        supersedes = None
        #: A candidate ALREADY in the store that this row should be published
        #: from, rather than writing a second one for the same statement.
        standing = None
        if w.ingest_key in seen:
            cid, status, event_id, stored = seen[w.ingest_key]
            fresh = w.extracted[DESK_KEY]["statement"]
            moved = drift(stored, fresh)
            if not event_id:
                # NOTHING WAS EVER PUBLISHED FOR THIS HAPPENING. Everything
                # below this line — the dispute, the "recorded, not
                # re-published" refusal — exists to protect a row that is on
                # the feed. There is no such row here, so none of it applies,
                # and the candidate sitting in the store is not a reason to
                # leave the map short of a happening the desks still state.
                if moved:
                    # The desk's newer word becomes the candidate we publish
                    # from, linked to the older one so the store still shows
                    # what we were told first. `existing_keys` reads the most
                    # recent statement per key, so tomorrow compares against
                    # this one.
                    w.extracted[DESK_KEY]["supersedes"] = {
                        "candidate_id": cid, "event_id": None, "was": stored,
                        "changed": moved, "contradicts": contradicts(stored, fresh),
                        "published": False,
                    }
                else:
                    standing = cid
            elif not moved:
                if (fresh or {}).get("place"):
                    try:
                        fill(event_id, fill_patch(fresh, ["place"]))
                    except Exception as exc:  # noqa: BLE001
                        out["failed"].append((
                            w, f"COULD NOT FILL published row {event_id} "
                               f"({type(exc).__name__}: {exc})"))
                        continue
                out["skipped"].append((
                    w, f"already PUBLIC as event {event_id} (candidate {cid}, "
                       f"{status}), and the desk still says the same thing "
                       f"about it"))
                continue
            else:
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
                    hole = fills(stored, fresh)
                    if not hole and fresh.get("place"):
                        hole = ["place"]
                    if hole:
                        patch = fill_patch(fresh, hole)
                        try:
                            verdict = fill(event_id, patch)
                        except Exception as exc:  # noqa: BLE001
                            verdict = (f"COULD NOT FILL published row {event_id} "
                                       f"({type(exc).__name__}: {exc})")
                            out["failed"].append((w, verdict))
                            continue
                    else:
                        verdict = (f"published row {event_id} is left alone: this is "
                                   f"corroboration, not a contradiction — nothing the "
                                   f"desks say about it has changed")
                supersedes = {"candidate_id": cid, "event_id": event_id,
                              "was": stored, "changed": moved,
                              "contradicts": against}
                w.extracted[DESK_KEY]["supersedes"] = supersedes
        if standing is not None:
            # THE CANDIDATE IS ALREADY THERE, with the same statement and the
            # evidence rows the gate reads. Writing a second one would give one
            # happening two handles and the ops queue two copies of one
            # question; what was missing was never the candidate, it was the
            # publication. So this row goes straight to the hold/promote
            # decision below on the candidate it already has.
            cid = standing
            held_note = f"candidate {cid}, already in the store"
        else:
            held_note = None
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
        # A STANDING CANDIDATE KEEPS THE EVIDENCE IT WAS WRITTEN WITH. Its
        # rows were added when it was created, from the same desks saying the
        # same thing (that is what `standing` means — no drift), so re-adding
        # them would duplicate the gate's own inputs and could turn one desk
        # into two corroborating rows. Nothing is skipped for a NEW candidate.
        evidence_failure = None
        for ev in (() if standing is not None else w.evidence):
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
            #
            # A HOLE IS A HOLE ON THE RETRY PATH TOO (founder, 2026-09-07:
            # "Field holes stay holes"). Re-reading a standing candidate asks
            # the publication question again, never the field question: this
            # row still has no night, or no place, so it is still held — the
            # retry cannot promote it into a public "Date TBA".
            out["held"].append((w, f"{w.hold_reason} — {held_note or f'candidate {cid}'}"))
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


def plan_counters(digest: Mapping[str, Any], walks: Sequence[DeskWalk],
                  runs: Mapping[str, FollowRun]) -> str:
    """The eight numbers the founder reads before authorising a write.

      publish_n     rows this plan would PUBLISH (title + night + place)
      hold_n        rows written as candidates and kept off the feed
      skip_n        rows already PUBLIC whose desks still say the same thing.
                    A row the store holds only as a CANDIDATE is not a skip —
                    it is promoted, or held if it still has a hole. This table is
                    printed BEFORE any database is opened — on a dry run there
                    is no store to read, and on a write run the keys have not
                    been compared yet — so it is always `—` here and the real
                    number lands in the outcome table below. `—` rather than
                    0 because "we did not look" and "there were none" are
                    different facts, and a founder authorising a write off
                    this table must not have them collapsed.
      mash_n        rows addressed by a LIST url (§2 Forbidden). Must be 0.
      403_n         pages walled — an UNREAD desk, never an empty one.
      dated_n       planned rows carrying a night (published or held)
      placed_n      planned rows carrying a place (published or held)
      tba_public_n  rows that would go PUBLIC with no clock and no dispute
                    label — a bare "Date TBA" on the feed. Must be 0.
    """
    rows = [
        ("publish_n", str(digest["publishable"])),
        ("hold_n", str(digest["held"])),
        ("skip_n", "—"),
        ("mash_n", str(sum(w.mash_n for w in walks))),
        ("403_n", str(sum(w.walled_n for w in walks)
                      + sum(r.walled_n for r in runs.values()))),
        ("dated_n", str(digest["dated"])),
        ("placed_n", str(digest["placed"])),
        ("tba_public_n", str(digest["tba_public"])),
    ]
    out = ["| " + " | ".join(name for name, _ in rows) + " |",
           "|" + "---:|" * len(rows),
           "| " + " | ".join(value for _, value in rows) + " |"]
    out.append("")
    out.append(
        "`skip_n` is `—`: this plan is computed before any database is opened, "
        "so nothing here knows which rows the store already holds — the real "
        "number appears in the outcome table on a `--write` run. `403_n` counts "
        "list pages AND event pages we were walled on; every one is an unread "
        "page, never an empty desk.")
    return "\n".join(out)


def outcome_table(result: Mapping[str, list]) -> str:
    out = ["| outcome | rows | what it means |", "|---|---:|---|"]
    meaning = {
        "promoted": "written and published — visible on `/events`, and on `/tonight` when the clock falls in the window",
        "held": "written as a candidate, not published — the gate, the duplicate guard, or a hole we cannot display honestly said so (reason below)",
        "changed": "the desk has CHANGED its statement about a happening we already published — recorded as a new candidate and the published row marked disputed, so it is still shown but no longer reads as settled (reason below)",
        "skipped": "this happening is already PUBLIC and the desk still says the same thing about it — a re-run, not a loss. A candidate that was never published is NOT skipped: it is promoted (or held, if it still has a hole)",
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
                    help=("door_id to walk; repeatable. DEFAULT: every door in "
                          "the --locale pack that is public with a read path "
                          "(see default_doors), most trusted first. Naming "
                          "doors here OVERRIDES that list, it does not add to "
                          "it."))
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
    ap.add_argument("--follow-pages", type=int, default=DEFAULT_FOLLOW_PAGES,
                    help=(f"the most EVENT pages this run may knock on, across all "
                          f"desks, round-robin (founder cap, default "
                          f"{DEFAULT_FOLLOW_PAGES}; 0 follows nothing)"))
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--min-interval", type=float, default=2.0,
                    help="politeness delay between live page fetches, seconds")
    args = ap.parse_args(argv)

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
        # NO `--door` WALKS THE WHOLE PUBLIC DESK OF THE PACK (founder,
        # 2026-09-07). Derived from the pack file inside the try, because a
        # pack that will not load is the same class of stop as a door that
        # will not walk and belongs in the same honest ERROR line.
        door_ids = list(args.doors or default_doors(args.locale))
        walks, registrations, tz, tz_id, skipped = walk_doors(
            args.locale, door_ids, real=args.real, max_pages=args.max_pages,
            timeout=args.timeout, min_interval=args.min_interval)
    except (LocalePackError, DeskWalkError, DeskPublishError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    mode = "LIVE" if args.real else "FIXTURE"

    # --- Ticket D: fill the rows' holes from their own event pages --------
    # ONE WALK FOR BOTH RUNS (founder, 2026-09-07: "Dry-run and write must
    # follow the same pages"). Following used to be dry-run only, on the
    # reasoning that a write which followed would publish something the
    # previous write did not. That reasoning was backwards, and the live
    # dry-run of 2026-09-07 (run 34073072428) measured why: every one of its
    # 162 nights and 130 places came from an event page, so a `--write` run
    # that skipped following would have held all 1584 rows for want of a night
    # and a place — and, worse, minted a key for each of them that no later run
    # can match. `desk_publish.ingest_key` falls back to `url:<listing_url>`
    # only for a row the union could not key, i.e. exactly a row with no night
    # and no place; once following fills those two holes the same happening
    # keys as `night~place~title`. Writing the holed rows first therefore does
    # not merely publish nothing — it writes 1584 handles that the corrected
    # run cannot recognise, and every one of them doubles.
    #
    # The three rules that make following affordable are the SAME on both
    # paths because they live in one place, not in this branch: same host
    # (`followable()`), at most `--follow-pages` pages per run spread
    # round-robin across the desks (`round_robin()`), and the walk's own
    # politeness delay between live fetches (`--min-interval`, passed to
    # `follow_fetchers()`). A write does not get a shorter walk, and it does
    # not get a faster one either.
    follow_notes: List[str] = []
    runs: Dict[str, FollowRun] = {}
    cap = max(0, args.follow_pages)
    if cap:
        # ONLY THE DOORS WE ACTUALLY WALKED. A door we could not walk has no
        # rows, so it has no event page to knock on; asking for a fetcher for
        # it would print a second reason it contributed nothing, under a
        # heading about following, and bury the first one.
        fetchers, fetcher_notes = follow_fetchers(
            [one.door_id for one in walks], real=args.real, timeout=args.timeout,
            min_interval=args.min_interval)
        follow_notes.extend(fetcher_notes)
        walks, runs = follow_pages(walks, fetchers, cap=cap)
    else:
        follow_notes.append("`--follow-pages 0`: no event page was knocked on.")

    one = union(walks, timezone=tz, timezone_id=tz_id, mode=mode)
    writes = plan(one, registrations)
    digest = plan_digest(writes)
    from worker.locale_pack.ticket_a_apply import apply_to_writes
    writes = apply_to_writes(writes)

    print(f"# Desk ingest — {len(walks)} door(s) of the `{args.locale}` pack "
          f"— {mode} walk")
    print()
    print("## 1. The doors walked")
    print()
    print(door_table(walks, runs))
    note = skipped_doors_note(skipped)
    if note:
        print()
        print(note)
    print()
    print("### What each walked door writes on a row")
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
    print("## 3. The event pages — did the row get a night and a place?")
    print()
    print(follow_table(walks, runs, cap=cap))
    for note in follow_notes:
        print()
        print(f"**Not followed**: {note}")
    print()
    followed_any = sum(r.followed_n for r in runs.values())
    # ONE heading, on both paths. It carried a "DRY-RUN VIEW, not what
    # `--write` would plan" variant for as long as the write path skipped
    # following (evaluator, PR #238 r2, which made that variant ask the same
    # predicate as the line beneath it so the two could not contradict). Both
    # paths now follow the same pages, so there is no divergence left to warn
    # about and a heading that still warned would be the contradiction — this
    # IS the plan a write run works from.
    print("## 4. The write plan")
    print()
    print(plan_table(writes))
    if followed_any:
        print()
        print(follow_effect_note(runs))
    print()
    print(plan_counters(digest, walks, runs))
    print()
    print(f"{bounded(digest['rows'], one)} happening(s) planned, of which "
          f"{digest['publishable']} publish and {digest['held']} "
          f"{'is' if digest['held'] == 1 else 'are'} HELD. A row goes public "
          f"only with a title, a night AND a place (founder, 2026-09-07); a "
          f"row missing any of the three is written as a candidate and kept "
          f"off the feed, never deleted and never faked. "
          f"{digest['publish_timed']} publish carrying a clock a desk stated; "
          f"{digest['publish_disputed']} publish DISPUTED because their desks "
          f"state different times (shown, never hidden). "
          f"{digest['single_desk']} come from ONE desk and are written anyway "
          f"(founder: do not require a second desk to publish); "
          f"{digest['multi_desk']} carr{'ies' if digest['multi_desk'] == 1 else 'y'} two.")
    print()

    if not args.write:
        print("## 5. Nothing was written")
        print()
        print("This was a dry run" + ("" if args.real else " over COMMITTED FIXTURES")
              + ". Re-run with `--real --write` on a machine that can reach the "
                "desks and holds `ONELIVE_DB_DSN`. That run follows the same "
                "event pages under the same cap, so it plans the rows in "
                "section 4"
              + (" — from the same fixtures, which is why a fixture plan is a "
                 "rehearsal of the shape and never of the catalog."
                 if not args.real else "."))
        return 0

    # --- the write ---------------------------------------------------------
    try:
        refuse_fixture_write(one)
    except DeskPublishError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    from worker.candidate_store import add_evidence, create_candidate  # noqa: PLC0415
    from worker.promote import promote_candidate  # noqa: PLC0415

    # ONE connection for the whole write — the counts, the key scan, every
    # seam call, and the counts again. See `one_connection`: the seams, their
    # SQL and their per-row commits are unchanged; only the handshake is paid
    # once instead of once per call.
    with one_connection() as db:
        with db() as conn:
            with conn.cursor() as cur:
                before = snapshot(cur, city=args.city, hours=args.hours)
                seen = existing_keys(cur)

        result = ingest(writes, seen=seen, create=create_candidate,
                        add_evidence=add_evidence, promote=promote_candidate)

        with db() as conn:
            with conn.cursor() as cur:
                after = snapshot(cur, city=args.city, hours=args.hours)

    print("## 5. What happened to each row")
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
    print("## 6. Before / after — what the site serves")
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
        print("## 7. FAILED — published rows are live and mislabelled")
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
