"""Fair-crawl state — whose turn it is, which door to knock on, has it changed.

The problem this exists to fix (founder, 2026-09-02): the ingest run spent its
page budget IN SOURCE ORDER, so the first two link-heavy calendars consumed all
30 follow-pages and every source behind them got zero. Coverage Law makes a
missing locale or category a defect; a budget that starves all but two sources
is that defect in scheduler form.

INCREMENTAL CRAWL (founder correction, same day, verbatim: "K=30 is a spend/time
safety cap, not the design"). A tick is not "N sources". A tick is: take the
sources that are DUE, most overdue first, and keep going until a real budget
says stop — wall clock, model spend, or host politeness. How many sources that
turns out to be is an OUTCOME, reported after the fact, not an input someone
picked. Two consequences that are easy to get wrong and are pinned by tests:

  * ROUND-ROBIN IS ONLY A TIE-BREAK. Least-recently-attempted decides the order
    between two sources that are equally overdue; it does not decide who is in
    the tick. Overdue-ness does that.
  * THERE IS NO CATEGORY WEIGHTING anywhere in this module. Nothing here reads
    a source's category, type, city, or name to decide its turn — only its own
    crawl history. A scheduler is exactly where a "music first" thumb would
    hide, and there is no field here for it to hide in.

TWO QUEUES, because a source in one costs a different amount than a source in
the other:

  * REFRESH — we know this source's door (`best_url`). One fetch: go straight
    at it. This is the steady state and it is cheap.
  * DISCOVER — we do not. One or two probes: the registered start URL, plus the
    single top-ranked events/calendar/shows page it advertises.

Discovery gets a bounded SHARE of the tick (DISCOVER_FETCH_SHARE) so a large
import cannot consume a tick that the live catalog needed for refreshing, and
refresh cannot starve discovery of ever finding a door.

Four facts per source drive that, and all four are DERIVED from rows the
pipeline already writes — there is no new table, no new column, no new vendor,
and nothing for a catalog re-import to clobber:

  * `raw_fetch` is already the crawl log. A successful fetch stores the body's
    sha256 in `content_hash` plus the server's ETag/Last-Modified in `headers`
    (worker/fetch/http_fetch.py); a failed or 304 attempt stores
    `attempt:<outcome>` there instead. That is last_success, the body
    fingerprint, the conditional-GET validators, and the fail streak.
  * `event_candidate.source_url` is already the door each candidate came
    through. That is best_url.

WHY DERIVED, NOT STORED. The alternatives were (a) a new `crawl_state` table,
(b) new columns on `source`, (c) a `crawl_state` key inside `source.config`.
(a) and (b) need a migration applied to a live DB before the armed cron can
run, for facts the audit trail already holds — two copies of "when did we last
fetch this" drift, and the copy the scheduler trusts would be the one nobody
audits. (c) is worse than it looks: tools/import_sources.py upserts with
`config = excluded.config`, so the next catalog import would silently erase
the crawl state. Deriving costs four correlated subqueries over an index that
already exists (idx_raw_fetch_source_time) at a catalog of a few hundred rows.
Revisit trigger: enabled-source count > 2,000, the same threshold
worker/run_once.py's rotation ordering already prints and carries.

THE CURSOR is likewise not a stored integer index into the enabled-source list.
An index breaks the moment a source is added, disabled, or renamed — it would
point at a different source than it did last tick, which is silent coverage
loss. The cursor is the least-recently-ATTEMPTED ordering
(worker/run_once.py::order_for_rotation), persisted as raw_fetch rows and
correct under insertion and deletion — and it is the TIE-BREAK, not the
schedule: `order_due` sorts by how long each source has been overdue and only
consults the cursor when two are equally overdue.

Pure functions plus two narrow SELECTs. No writes, no network — and NO MODEL
CALL: extraction is the only stage in the pipeline that may reach Anthropic,
so a scheduler that phoned a model to decide whose turn it was would be
spending the extraction budget on itself.
"""
from __future__ import annotations

import logging
import os
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# --- raw_fetch vocabulary ----------------------------------------------------
#
# http_fetch writes attempt rows as "attempt:<outcome>" in content_hash (see
# ATTEMPT_HASH_PREFIX there). We read that vocabulary rather than re-define it;
# the two markers below are the outcomes that exist today.
ATTEMPT_PREFIX = "attempt:"
ATTEMPT_FAILED = "attempt:failed"
ATTEMPT_NOT_MODIFIED = "attempt:not_modified"

# --- Queues ------------------------------------------------------------------
#
# A source is in exactly one of these, decided by ONE fact: do we know its
# door? Nothing about what kind of place it is enters here (see the module
# docstring: no category weighting, and no field to hide one in).
QUEUE_REFRESH = "refresh"
QUEUE_DISCOVER = "discover"
#: EVENT-PROXIMITY refresh. Not a source's turn — a PAGE's turn, because a
#: published event is getting close and its defining page is where a change
#: (moved, cancelled, sold out, new time) would show up. See
#: EVENT_REFRESH_LADDER.
QUEUE_EVENT = "event"

#: EVENT-PROXIMITY LADDER (founder, 2026-09-02: "Published rows with
#: start_time: recheck their defining URL at T-30d, T-14d, T-7d, T-3d, T-1d,
#: day-of, then stop after end"). Hours before an event's start_time, largest
#: first. A daily re-crawl of everything would spend the whole budget on
#: events three months out; this spends it where a change still matters.
#:
#: "day-of" is SIX HOURS before start, and that is a documented STAND-IN for
#: what the founder actually asked for (2026-09-02): "day-of = start of that
#: event's local calendar day (timezone of the listing). Not 'six hours before'
#: unless that is easier to pin in one constant — if so, keep 6h and document
#: it." It is not merely easier; on today's schema the local-calendar-day
#: version is not computable at all, and the escape clause is taken for a
#: stated reason rather than for convenience:
#:
#:   * `event.start_time` is `timestamptz` — an absolute instant. The wall
#:     clock and UTC offset the listing was written in are not preserved, so
#:     the event's own local midnight cannot be recovered from it.
#:   * Nothing in the schema carries a timezone. `venue` has city/state/lat/lng
#:     (migration 0010) and no tz column; deriving one from coordinates needs a
#:     tz database dependency, which is a new vendor and the founder's call.
#:   * Assuming a project timezone would be wrong by design: Coverage Law says
#:     locale is not a border, so an Austin default would mis-time every row
#:     outside CAPCOG — and silently, which is the worse half.
#:
#: Anchoring to the UTC day instead was considered and rejected as ERRATIC, not
#: merely imprecise: for an 8pm CDT show the UTC day starts an hour before
#: doors, but for a 2pm CDT matinee it starts the previous local evening. Six
#: hours before start is consistent, always lands on the event's own local day
#: for anything starting after 06:00 local, and is one constant.
#:
#: Recorded as a deviation with an objective trigger: docs/RECORD.md R-090.
EVENT_REFRESH_LADDER_HOURS = (30 * 24, 14 * 24, 7 * 24, 3 * 24, 24, 6)

#: The largest share of a tick's fetch budget that event-proximity refresh may
#: take. Proximity items go FIRST — they are the only work with a deadline, and
#: a show tonight that was cancelled is a user-visible error now, while a source
#: taking its routine turn is not. This share is what stops that priority from
#: becoming a monopoly: a night with hundreds of near events must not freeze
#: the ordinary rotation, so half the tick stays with it.
EVENT_FETCH_SHARE = 0.5

#: The largest share of a tick's fetch budget discovery may take. A catalog
#: import can add hundreds of door-less rows at once; without a share they
#: would fill every tick and the live catalog would go stale while we probed.
#: Half, because neither job is worth more than the other: refresh keeps what
#: we have true, discovery is how we get more. Enforced in TickBudget.
DISCOVER_FETCH_SHARE = 0.5

# --- Tick budgets ------------------------------------------------------------
#
# What actually stops a tick. Each is a different real limit, and none of them
# is a source count — how many sources a tick reached is an OUTCOME.

#: WALL CLOCK. The armed cron fires every 20 minutes and its concurrency group
#: does not cancel in flight, so a tick that runs long queues behind the next
#: one. Ten minutes leaves half the cadence as headroom.
MAX_TICK_SECONDS = 600

#: MODEL BUDGET, in pages sent to extraction. Extraction is the ONLY stage that
#: may call Anthropic (fetch, sensor, discovery and the gate are all
#: deterministic), so counting extract calls counts the spend. Each page fans
#: out to at most EXTRACT_MAX_EVENTS_PER_PAGE model calls (worker/ai_extract.py,
#: default 50), which makes the per-tick AI ceiling 60 x 50 = 3000 calls — the
#: SAME worst case the old (30 sources + 30 follow-pages) x 50 arithmetic gave,
#: now expressed as the thing it actually bounds instead of as a source count.
MAX_EXTRACT_CALLS_PER_TICK = 60

#: BUG-SAFETY CAP, named for what it caps (founder: "if you need a bug-safety
#: cap call it MAX_FETCHES_PER_TICK, not 30 sources theology"). At the fetch
#: adapter's 2s politeness sleep plus real network time this lands near the
#: wall-clock limit by design: in a healthy tick one of the two binds, and
#: which one is not important. It exists so a loop bug cannot fetch forever.
MAX_FETCHES_PER_TICK = 120

#: HOST POLITENESS. Several catalog rows can share one host (a ticketing
#: platform, a university, a city portal). Past this many fetches to the same
#: host in one tick, further sources on that host are DEFERRED to the next tick
#: — not dropped, and not slept on: sleeping would spend the wall clock we owe
#: to every other source. The global 2s inter-fetch sleep in
#: worker/fetch/http_fetch.py is unchanged and still applies to every request.
MAX_FETCHES_PER_HOST_PER_TICK = 4

# --- Backoff policy ----------------------------------------------------------
#
# Minutes. Deliberately few numbers, none of them env knobs: every knob is a
# way for a scheduled loop to be mis-tuned in production without a code review.

#: A healthy source is not re-crawled more often than this. It is politeness
#: and nothing more: with the tick bounded by time and spend rather than by a
#: source count, this floor is what stops a small catalog from being re-read
#: every twenty minutes forever. Two and a half hours is under the ~3h cadence
#: the live catalog gets anyway, so it does not slow a full sweep down.
BASE_INTERVAL_MINUTES = 150

#: First failure waits an hour, then doubles: 1h, 2h, 4h, 8h ... A source
#: refusing an unauthenticated read (class D, 401/403) fails every time, so
#: this is what makes "we knock once" true over days instead of only within a
#: single tick — no persisted closed-door flag to keep in sync with reality.
FAIL_BACKOFF_MINUTES = 60

#: Ceiling on that doubling. A week: long enough that a permanently walled
#: source costs ~4 fetches a month, short enough that a venue which fixes its
#: site is picked up again without a human touching anything.
MAX_BACKOFF_MINUTES = 10080

#: Statuses that mean "slow down", NOT "you are not invited". 429 also appears
#: in worker.sourcing.source_class.WALL_STATUSES, which demotes to class D;
#: the founder's rule for this scheduler is explicit and narrower — "401/403 ->
#: class D, one knock, fail_streak++. 429/503 -> back off" — so the fair-crawl
#: path checks THIS set FIRST and demote_on_response never sees a 429 here.
#: WALL_STATUSES itself is left untouched: other callers (the claim queue) keep
#: their meaning, and there is exactly one place where the two differ, named.
BACKOFF_STATUSES = frozenset({429, 503})


@dataclass(frozen=True)
class SourceCrawlState:
    """What the audit trail says about one source's crawl.

    `fail_streak` counts attempts since the last time the source ANSWERED at
    all — a 304 answers, so a perpetually-unchanged source has streak 0 and
    keeps its healthy cadence, while a source that refuses or times out climbs
    the backoff. `best_url` is the door that produced the most candidates
    recently, not merely the newest one: an importer that stamps a single
    event's URL onto a candidate must never turn one event page into the
    venue's permanent door.
    """

    source_id: str
    last_attempt_at: Optional[datetime] = None
    #: The last time we actually READ and parsed this source — not merely
    #: knocked on it. Distinct from last_attempt_at by design: see the
    #: last_verified_at subquery in _STATE_SQL for why the two must not merge.
    last_verified_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    fail_streak: int = 0
    best_url: Optional[str] = None

    @property
    def queue(self) -> str:
        """REFRESH when we know this source's door, DISCOVER when we do not.

        The ONLY input is whether a `best_url` exists. Not the source's type,
        category, city, or name — a scheduler is where a category thumb would
        hide, and this property is the whole of the queue decision.
        """
        return QUEUE_REFRESH if self.best_url else QUEUE_DISCOVER

    def interval_minutes(self) -> int:
        """How long this source waits between ticks, from its own history."""
        if self.fail_streak <= 0:
            return BASE_INTERVAL_MINUTES
        backoff = FAIL_BACKOFF_MINUTES * (2 ** (self.fail_streak - 1))
        return min(backoff, MAX_BACKOFF_MINUTES)

    def next_due_at(self) -> Optional[datetime]:
        """When this source may next be crawled. None = now (never attempted).

        A never-attempted source is due immediately and is infinitely overdue,
        so it sorts to the front — new catalog rows are crawled the same day an
        import adds them.
        """
        if self.last_attempt_at is None:
            return None
        return _as_utc(self.last_attempt_at) + timedelta(minutes=self.interval_minutes())

    def is_due(self, now: Optional[datetime] = None) -> bool:
        due = self.next_due_at()
        if due is None:
            return True
        return _as_utc(now or datetime.now(timezone.utc)) >= due

    def overdue_seconds(self, now: Optional[datetime] = None) -> float:
        """How long this source has been waiting past its own due time.

        THIS is the priority. A source that came due an hour ago goes before
        one that came due a minute ago, whatever their absolute last-fetch
        times were, so a source with a long backoff is not permanently
        outranked by a healthy one that is barely due.

        A never-attempted source returns infinity: it has been waiting since it
        entered the catalog and there is no honest finite answer.
        """
        due = self.next_due_at()
        if due is None:
            return float("inf")
        moment = _as_utc(now or datetime.now(timezone.utc))
        return (moment - due).total_seconds()


@dataclass(frozen=True)
class DoorFingerprint:
    """The last successful read of ONE url: body hash + cache validators.

    `content_hash` answers "did the body change?" after the bytes arrive;
    `etag`/`last_modified` let the server answer it BEFORE they do (304). Both
    matter: a server with no validators still costs zero AI calls, because the
    hash comparison still skips extraction.
    """

    url: str
    content_hash: str
    etag: Optional[str] = None
    last_modified: Optional[str] = None

    def unchanged(self, content_hash: Optional[str]) -> bool:
        return bool(content_hash) and content_hash == self.content_hash


def _as_utc(value: datetime) -> datetime:
    """Timestamps from psycopg2 are tz-aware (timestamptz); a naive one can only
    come from a caller or a fixture, and assuming UTC beats raising in a
    scheduler."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def order_due(
    states: Sequence[SourceCrawlState],
    *,
    now: Optional[datetime] = None,
    rotation_rank: Optional[Dict[str, int]] = None,
) -> List[SourceCrawlState]:
    """The due sources, MOST OVERDUE FIRST, round-robin only as the tie-break.

    Founder, verbatim: "round-robin is only a tie-break among due sources".
    The two candidate orderings genuinely differ, which is why this matters: a
    source with an 8-hour backoff that came due an hour ago has an OLDER
    last_attempt_at than a healthy source due five minutes ago, so pure
    round-robin would put the backing-off source first every single time.
    Overdue-ness asks the question that actually matters — who has been waiting
    longest past the moment we said we would come back?

    `rotation_rank` is the caller's least-recently-attempted position per
    source id (worker/run_once.py::order_for_rotation, the one definition of
    the cursor in this tree). It breaks ties; source_id breaks ties after that,
    so the order is total and deterministic.

    Not-due sources are simply absent: DEFERRED to a later tick, never dropped.
    Nothing here reads a source's category, type, city, or name.
    """
    moment = _as_utc(now or datetime.now(timezone.utc))
    ranks = rotation_rank or {}
    due = [st for st in states if st.is_due(moment)]

    def _key(st: SourceCrawlState):
        # Negated so "most overdue" sorts first; a never-attempted source's
        # infinite overdue-ness becomes -inf, which is exactly where it belongs.
        return (-st.overdue_seconds(moment), ranks.get(st.source_id, 0), st.source_id)

    return sorted(due, key=_key)


# --- Verification: fail closed ------------------------------------------------
#
# Founder, 2026-09-02, verbatim: "If a scheduled check cannot confirm OR cannot
# disconfirm, make no change to the listing (no delete, no cancel, no date
# edit). Only mutate on confirmed same-page evidence. Fetch failure / cap / 429
# / parse miss = last good row stands."
#
# Then, ratifying the policy (2026-09-02, verbatim): "Confirmed check MAY
# update a published listing (time, cancel, postpone, title) only with
# same-page evidence. Unconfirmed = no mutation. Do not delete the row from the
# catalog; mark cancelled/moved and keep evidence. Ambiguous parse = keep."
#
# So a re-check produces a VERDICT, and the verdict is what an update has to
# ask. UNVERIFIED is not a soft "probably fine": it is a hard "we learned
# nothing, so nothing moves". Every failure mode collapses into it, which is
# what makes the rule fail CLOSED — a failure nobody has written yet is
# unverified by default, never confirmed.
#
# WHAT A 404 DOES AND DOES NOT LICENSE — the one place the two directives need
# reading together, flagged rather than quietly resolved. A clear 404 confirms
# the PAGE is gone. It is not same-page evidence about any listing on it,
# because there is no page to have evidence from: a venue that reorganizes its
# URLs, a CMS migration and a genuinely cancelled show all 404 identically.
# Under "only with same-page evidence" and "do not delete the row", a 404
# therefore licenses NO status change on any listing. What it does license is
# re-finding the door — which the loop already does, by falling back to the
# registered start URL and re-discovering from there. A clean parse in which a
# published event is ABSENT is the case that carries same-page evidence, and
# deciding that is the update path's job, not this vocabulary's.
#
# STATE OF PLAY, stated so nobody reads more into this than is here: the
# orchestrator does not update published events. It cannot — it imports no
# promote path, writes only candidates, and issues no UPDATE against `event`.
# The policy is ratified and encoded HERE so the eventual update path has one
# definition to obey rather than inventing a second; building that path is its
# own ticket, and it changes the armed cron's runtime, which the founder has
# capped for this one ("no second wave").

#: The page still says what it said: a clean parse, or bytes identical to the
#: last good read. This is the ONLY verdict that carries same-page evidence,
#: and therefore the only one that could license an update.
VERIFIED_PRESENT = "verified_present"

#: The defining page is confirmed GONE — a clear 404. A fact about the PAGE,
#: never about a listing on it (see the 404 note above): it licenses
#: re-discovery of the source's door and NO listing change at all.
VERIFIED_ABSENT = "verified_absent"

#: We learned nothing. Fetch failure, 429/503 back-off, a budget cap, a wall, a
#: sensor rejection, an off-site landing, an ambiguous or failed parse. The last
#: good row stands, untouched.
UNVERIFIED = "unverified"

#: The fields a confirmed check may ever change on a published listing, from
#: the founder's own enumeration: "time, cancel, postpone, title". `status`
#: carries cancel and postpone (the 4-state moderation vocabulary in
#: migration 0001: scheduled|cancelled|moved) — which is why "cancelled" and
#: "moved" are STATUSES on a row that stays, not reasons to remove one.
UPDATABLE_LISTING_FIELDS = ("start_time", "end_time", "status", "title")

#: Founder, verbatim: "Do not delete the row from the catalog". There is no
#: verdict, no evidence and no confidence level that licenses removing a
#: published listing — which is also Coverage Law's own rule that a legally
#: seen row is never dropped, and the 4-state model's rule that a disputed
#: event is shown, never hidden. Stated as a constant so a caller can assert on
#: it rather than re-derive it, and pinned by a test.
DELETE_IS_NEVER_LICENSED = True

#: Door outcomes that confirm the page still stands. "unchanged" belongs here on
#: purpose: a 304 or an identical body hash is positive evidence that the page
#: says exactly what it said when we last read it — stronger, not weaker, than a
#: fresh parse.
_CONFIRMING_DOORS = frozenset({"changed", "unchanged"})

#: Page-level decisions that mean the parse actually completed. A sensor
#: rejection or a budget deferral did NOT read the page, whatever the fetch did.
_CLEAN_PARSE_DECISIONS = frozenset({"held", "escalated", "ready_to_promote"})


def classify_recheck(
    *,
    door_kind: str,
    page_decision: Optional[str] = None,
    http_status: Optional[int] = None,
) -> Tuple[str, str]:
    """The verdict of one re-check, and the reason in plain words.

    Fail-closed by construction: only the two explicitly-confirming shapes
    return a VERIFIED_* verdict, and everything else — including a shape this
    function has never seen — falls through to UNVERIFIED. There is no
    "probably", and no status is invented for a listing we could not read.
    """
    if door_kind == "unchanged":
        return (VERIFIED_PRESENT,
                "page byte-identical to the last good read (304 or same hash)")
    if door_kind == "changed":
        if page_decision in _CLEAN_PARSE_DECISIONS:
            return (VERIFIED_PRESENT, "page fetched and parsed cleanly")
        return (UNVERIFIED,
                f"page fetched but not parsed ({page_decision or 'no decision'}) "
                "— last good row stands")
    if door_kind == "missed" and http_status == 404:
        return (VERIFIED_ABSENT,
                "defining page returned a clear 404 — the PAGE is gone. No "
                "same-page evidence exists about any listing on it, so this "
                "licenses re-finding the door and no listing change")
    if door_kind == "missed":
        return (UNVERIFIED,
                f"fetch failed ({http_status or 'no status'}) — last good row stands")
    if door_kind == "backoff":
        return (UNVERIFIED, "rate-limited (429/503) — last good row stands")
    if door_kind == "wall":
        return (UNVERIFIED, "closed door (401/403) — last good row stands")
    if door_kind == "deferred":
        return (UNVERIFIED, "budget or politeness deferred the check — last good row stands")
    if door_kind == "offsite":
        return (UNVERIFIED, "landed off-site — a different source; last good row stands")
    return (UNVERIFIED, f"unrecognized check outcome ({door_kind}) — fail closed")


def may_update_listing(verdict: str) -> bool:
    """Whether a verdict licenses updating a published listing's
    UPDATABLE_LISTING_FIELDS — and only ever with the same-page evidence that
    produced it.

    VERIFIED_PRESENT only. VERIFIED_ABSENT is excluded deliberately: a 404
    carries no page, so it carries no same-page evidence, and the founder's
    rule is "only with same-page evidence". UNVERIFIED is excluded always.

    The single place that question is answered, so no caller re-derives it.
    Nothing in this repository updates a published event on a re-check today;
    this exists so that when something does, it asks here.
    """
    return verdict == VERIFIED_PRESENT


def may_delete_listing(verdict: str) -> bool:  # noqa: ARG001 — the answer is the point
    """Always False. No verdict licenses removing a published row.

    The parameter exists so a caller asks the question in the same shape it
    asks may_update_listing, and gets the same answer every time: a listing
    that is gone is marked (cancelled/moved) with its evidence and KEPT.
    Founder-ratified, and it is also Coverage Law ("if we legally saw it, it
    may exist"; dropping a row we saw is a defect) and the 4-state model
    (disputed is shown, never hidden).
    """
    return not DELETE_IS_NEVER_LICENSED


@dataclass(frozen=True)
class EventRefresh:
    """One PAGE that is due a re-read because an event it defines is near.

    Keyed on the page, never on the event: "one page fetch covers all events on
    that page" (founder). A venue calendar listing forty shows is one fetch on
    the day the soonest of them crosses a rung, not forty.

    `overdue_seconds` is how long ago that rung was crossed, so an event-refresh
    item sorts against source items on exactly the same scale — one priority
    order across all three queues, no queue given a standing head start.
    """

    source_id: str
    url: str
    rung_hours: int
    overdue_seconds: float
    events: int = 1

    @property
    def reason(self) -> str:
        if self.rung_hours >= 24:
            near = f"T-{self.rung_hours // 24}d"
        else:
            near = f"day-of (T-{self.rung_hours}h)"
        return (f"event proximity {near}: {self.events} published event(s) on "
                "this page")


def crossed_rung(
    start_time: datetime,
    *,
    last_fetch_at: Optional[datetime],
    now: datetime,
) -> Optional[int]:
    """The ladder rung this event has crossed SINCE we last read its page.

    Returns the rung (in hours before start) that is now due, or None if the
    page has already been read since the last rung the event crossed. The
    NEAREST crossed rung wins, so a page we have not touched in months owes one
    fetch, not six.

    A page never fetched (`last_fetch_at` None) owes its most recent crossed
    rung — one fetch, not one per rung it has ever passed.
    """
    start = _as_utc(start_time)
    moment = _as_utc(now)
    seen = _as_utc(last_fetch_at) if last_fetch_at is not None else None
    for hours in sorted(EVENT_REFRESH_LADDER_HOURS):   # nearest rung first
        rung_at = start - timedelta(hours=hours)
        if rung_at > moment:
            continue          # not crossed yet
        if seen is not None and seen >= rung_at:
            return None       # already read since this rung; nearer rungs too
        return hours
    return None


def plan_event_refreshes(
    rows: Sequence[Sequence[Any]],
    *,
    now: Optional[datetime] = None,
) -> List[EventRefresh]:
    """Group per-event rows into one due item per PAGE, most overdue first.

    `rows` are (source_id, source_url, start_time, end_time, last_fetch_at) for
    published events that have not ended — the SQL below has already applied
    "then stop after end", and dateless rows never appear because the query
    requires a start_time (founder: "dateless rows: source-door schedule
    only"). Nothing here reads a category, a venue, or a name: the only inputs
    are a time and a URL.
    """
    moment = _as_utc(now or datetime.now(timezone.utc))
    best: Dict[Tuple[str, str], EventRefresh] = {}
    for source_id, url, start_time, _end_time, last_fetch_at in rows:
        if not url or start_time is None:
            continue
        rung = crossed_rung(start_time, last_fetch_at=last_fetch_at, now=moment)
        if rung is None:
            continue
        overdue = (moment - (_as_utc(start_time) - timedelta(hours=rung))).total_seconds()
        key = (str(source_id), url)
        existing = best.get(key)
        if existing is None:
            best[key] = EventRefresh(source_id=str(source_id), url=url,
                                     rung_hours=rung, overdue_seconds=overdue)
            continue
        # Same page, another event on it: ONE fetch covers both. Keep the
        # nearest rung (the most urgent reason to look) and count the events.
        best[key] = EventRefresh(
            source_id=existing.source_id, url=url,
            rung_hours=min(existing.rung_hours, rung),
            overdue_seconds=max(existing.overdue_seconds, overdue),
            events=existing.events + 1,
        )
    # NEAREST RUNG FIRST, then most overdue. Sorting on overdue-ness alone was
    # wrong and the test caught it: a T-30d rung crossed a day ago is "more
    # overdue" (86400s) than a day-of rung crossed an hour ago (3600s), so an
    # event a month out would outrank one starting in five hours. The whole
    # point of the ladder is to concentrate attention where a change still
    # matters to somebody tonight.
    return sorted(best.values(), key=lambda r: (r.rung_hours, -r.overdue_seconds, r.url))


def resolve_int_env(env_name: str, default: int, noun: str) -> int:
    """Read + validate a non-negative integer budget knob, FAIL CLOSED.

    Unset (or set to the empty string, which is how an absent CI variable
    arrives) means the default. Anything else MUST parse as a base-10 integer
    >= 0; a malformed value raises so the caller aborts loudly at start — a
    budget knob that cannot be read is a structural failure, and silently
    substituting the default would turn a typo into an unnoticed spend change.
    0 disables the budgeted behaviour; it never means "uncapped".

    ONE implementation for every knob in the pipeline: the render cap, the
    probe ceilings and the tick budgets are the same rule about the same kind
    of value, and two copies of "how a budget is parsed" would drift in the
    direction that costs money. worker/orchestrator.py calls this one.
    """
    raw = os.getenv(env_name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise ValueError(
            f"{env_name} must be a base-10 integer >= 0 (got {raw!r}); "
            f"refusing to run with an unvalidated {noun} budget — fail closed"
        ) from exc
    if value < 0:
        raise ValueError(
            f"{env_name} must be >= 0 (got {value}); a negative {noun} "
            f"budget is meaningless — fail closed (use 0 to disable {noun}s)"
        )
    return value


class TickBudget:
    """What stops a tick, and the honest reason why.

    A tick ends when a REAL limit is hit — wall clock, model spend, or the
    bug-safety fetch cap — or when nothing due is left. It does NOT end at a
    source count: how many sources a tick reached is reported afterwards as an
    OUTCOME (founder: "K=30 is a spend/time safety cap, not the design").

    Host politeness and the discovery share are deliberately NOT tick-stoppers.
    Hitting either means THIS SOURCE waits; the tick moves on to somebody else.
    Ending the whole tick because one host was popular would punish every other
    source for it.

    `clock` is injected (defaults to time.monotonic) so the wall-clock rule is
    unit-testable without sleeping — a budget you cannot test is a budget you
    do not have.
    """

    #: Reasons that end the whole tick, as opposed to deferring one source.
    TICK_STOPPERS = ("wall_clock", "fetch_budget", "model_budget")

    def __init__(
        self,
        *,
        max_seconds: int = MAX_TICK_SECONDS,
        max_fetches: int = MAX_FETCHES_PER_TICK,
        max_extract_calls: int = MAX_EXTRACT_CALLS_PER_TICK,
        max_fetches_per_host: int = MAX_FETCHES_PER_HOST_PER_TICK,
        discover_share: float = DISCOVER_FETCH_SHARE,
        event_share: float = EVENT_FETCH_SHARE,
        clock=None,
    ) -> None:
        for name, value in (("max_seconds", max_seconds),
                            ("max_fetches", max_fetches),
                            ("max_extract_calls", max_extract_calls),
                            ("max_fetches_per_host", max_fetches_per_host)):
            if value < 0:
                # The project-wide budget rule: 0 means "none of this",
                # negative is a misconfiguration, and neither ever means
                # "uncapped". Fail closed, at construction, before any fetch.
                raise ValueError(
                    f"{name}={value} is invalid — a tick budget must be >= 0; "
                    "0 disables that activity, it never means uncapped."
                )
        for name, share in (("discover_share", discover_share),
                            ("event_share", event_share)):
            if not 0.0 <= share <= 1.0:
                raise ValueError(
                    f"{name}={share} is invalid — it is a share of the fetch "
                    "budget and must be between 0 and 1."
                )
        self.max_seconds = max_seconds
        self.max_fetches = max_fetches
        self.max_extract_calls = max_extract_calls
        self.max_fetches_per_host = max_fetches_per_host
        self.discover_share = discover_share
        self.event_share = event_share
        # Until a plan is declared, a share is the whole budget: a share exists
        # to protect the OTHER queues, and with nothing to protect there is
        # nothing to share with. reserve_for_plan() narrows these.
        self.max_discover_fetches = max_fetches
        self.max_event_fetches = max_fetches
        self._clock = clock or time.monotonic
        self._started = self._clock()
        self.fetches = 0
        self.discover_fetches = 0
        self.event_fetches = 0
        self.extract_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.sources_touched = 0
        self.sources_deferred = 0
        self.per_host: Dict[str, int] = {}
        self.stop_reason = "exhausted"

    #: Env knobs, so the armed cron can declare its budgets where the spend
    #: happens. Every one is parsed fail-closed by resolve_int_env.
    ENV = {
        "max_seconds": ("ONELIVE_MAX_TICK_SECONDS", MAX_TICK_SECONDS, "tick wall-clock"),
        "max_fetches": ("ONELIVE_MAX_FETCHES_PER_TICK", MAX_FETCHES_PER_TICK, "tick fetch"),
        "max_extract_calls": ("ONELIVE_MAX_EXTRACT_CALLS_PER_TICK",
                              MAX_EXTRACT_CALLS_PER_TICK, "tick model"),
        "max_fetches_per_host": ("ONELIVE_MAX_FETCHES_PER_HOST",
                                 MAX_FETCHES_PER_HOST_PER_TICK, "per-host fetch"),
    }

    @classmethod
    def from_env(cls, **overrides) -> "TickBudget":
        """A tick budget from the environment, every knob validated fail-closed
        BEFORE the first fetch — a typo aborts the tick, it never silently
        means uncapped."""
        kwargs = {name: resolve_int_env(env, default, noun)
                  for name, (env, default, noun) in cls.ENV.items()}
        kwargs.update(overrides)
        return cls(**kwargs)

    #: Fetches one planned item is expected to cost, by queue. Used ONLY to
    #: size the reservations below — never to bound anything, so an item that
    #: turns out to cost less does not leave budget stranded.
    _EXPECTED_FETCHES = {QUEUE_EVENT: 1, QUEUE_REFRESH: 1, QUEUE_DISCOVER: 2}

    def reserve_for_plan(self, queues: Sequence[str]) -> None:
        """Size the per-queue caps against what this tick actually has to do.

        A flat "discovery gets half" is wrong in the common case and the tests
        caught it: a tick made entirely of discover items would cap itself at
        half its own fetch budget and leave the rest unused, because there was
        no refresh work for the other half to go to. A share is a RESERVATION
        FOR THE OTHER QUEUES, so it should bind only as far as those queues can
        actually use it:

            reserved = min(what the other queues will plausibly spend,
                           the share we promised them)
            this queue's cap = the fetch budget minus that reservation

        With no other work, the reservation is zero and a queue may use the
        whole budget. With more other work than the share, the reservation is
        the share and no more. Both extremes come out right, and so does the
        middle: one refresh item beside a hundred discover items reserves one
        fetch, not half the tick.
        """
        counts: Dict[str, int] = {}
        for q in queues:
            counts[q] = counts.get(q, 0) + 1

        def _cap(queue: str, share: float) -> int:
            others = sum(self._EXPECTED_FETCHES.get(q, 1) * n
                         for q, n in counts.items() if q != queue)
            reserved = min(others, int(self.max_fetches * (1.0 - share)))
            return max(0, self.max_fetches - reserved)

        self.max_discover_fetches = _cap(QUEUE_DISCOVER, self.discover_share)
        self.max_event_fetches = _cap(QUEUE_EVENT, self.event_share)

    # --- what the loop asks --------------------------------------------------

    def elapsed(self) -> float:
        return self._clock() - self._started

    def tick_stop(self) -> Optional[str]:
        """The reason the tick must end NOW, or None to keep going."""
        if self.elapsed() >= self.max_seconds:
            return "wall_clock"
        if self.fetches >= self.max_fetches:
            return "fetch_budget"
        if self.extract_calls >= self.max_extract_calls:
            return "model_budget"
        return None

    def may_fetch(self, host: str, *, queue: str) -> Optional[str]:
        """None if this fetch may happen, else the reason it may not.

        Callers tell a tick-stopper from a source-deferral by membership in
        TICK_STOPPERS rather than by parsing the string.
        """
        stop = self.tick_stop()
        if stop:
            return stop
        if self.per_host.get(host, 0) >= self.max_fetches_per_host:
            return "host_politeness"
        if (queue == QUEUE_DISCOVER
                and self.discover_fetches >= self.max_discover_fetches):
            return "discover_share"
        if (queue == QUEUE_EVENT
                and self.event_fetches >= self.max_event_fetches):
            return "event_share"
        return None

    def may_extract(self) -> bool:
        return self.extract_calls < self.max_extract_calls

    # --- what the loop reports back ------------------------------------------

    def record_fetch(self, host: str, *, queue: str) -> None:
        self.fetches += 1
        self.per_host[host] = self.per_host.get(host, 0) + 1
        if queue == QUEUE_DISCOVER:
            self.discover_fetches += 1
        elif queue == QUEUE_EVENT:
            self.event_fetches += 1

    def record_extract(self) -> None:
        """One PAGE sent to extraction — the unit the model budget bounds.

        Deliberately counts CALLS and nothing else. Tokens are recorded
        separately by record_tokens() from what the provider actually reported,
        because the budget must be enforceable in-flight (calls are known the
        moment they are made) while the spend is only knowable afterwards.
        """
        self.extract_calls += 1

    def record_tokens(self, *, input_tokens: int, output_tokens: int) -> None:
        """The tokens this tick really used, read back from what the provider
        itself reported (ai/claude_provider.py stamps the SDK `usage` object
        into each candidate's `extracted` jsonb; load_extraction_usage sums it).

        Read back rather than threaded through the extractor ON PURPOSE:
        worker/ai_extract.py is extraction-surface code that the attended
        golden exam does not execute, so touching it to carry a telemetry
        number would put a cost report on the wrong side of the extraction
        certification gate. The number is identical either way — it is the
        provider's own count — so the cheaper place to read it is the one that
        certifies nothing.
        """
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def outcomes(self) -> Dict[str, Any]:
        return {
            "sources_touched": self.sources_touched,
            "sources_deferred": self.sources_deferred,
            "fetches": self.fetches,
            "event_fetches": self.event_fetches,
            "discover_fetches": self.discover_fetches,
            "extract_calls": self.extract_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "elapsed_seconds": round(self.elapsed(), 1),
            "stop_reason": self.stop_reason,
        }


def host_of(url: str) -> str:
    """The host a URL belongs to, for politeness accounting. `www.` is folded so
    a site cannot get two budgets by linking itself both ways."""
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def choose_primary_door(
    *,
    start_url: str,
    best_url: Optional[str],
    same_site_fn,
) -> str:
    """The FIRST url to fetch for a source: its best door, else its start URL.

    `best_url` is only honoured when it is on the registered start URL's own
    site. It is read from data the pipeline wrote, and an off-origin door would
    quietly ingest a different source under this one's name — the same rule the
    follow-walk enforces twice, applied here once, at the only other place a
    source's URL is chosen. `same_site_fn` is injected so this module stays
    free of the sourcing package (and unit-testable without it).
    """
    if not best_url or best_url == start_url:
        return start_url
    try:
        on_origin = same_site_fn(best_url, start_url)
    except Exception:  # noqa: BLE001 — a comparison failure must not pick a door
        on_origin = False
    if not on_origin:
        logger.warning(
            "best_url %s is not on %s's site — falling back to the registered "
            "start URL (an off-origin door is a different source)",
            best_url, start_url,
        )
        return start_url
    return best_url


# --- Reads -------------------------------------------------------------------
#
# Two SELECTs, both parameterized, both read-only. They take an optional
# cursor so a caller inside a transaction reads its own snapshot; with none,
# they open the pipeline's normal connection.

_STATE_SQL = """
select s.source_id,
       (select max(rf.fetched_at) from raw_fetch rf
         where rf.source_id = s.source_id) as last_attempt_at,
       -- LAST VERIFIED, kept distinct from last ATTEMPT on purpose (founder:
       -- "record last_attempt vs last_verified"). An attempt is any knock,
       -- including the ones that told us nothing; a verification is a page we
       -- actually read and parsed, and the proof of that is a candidate row
       -- with evidence behind it. Collapsing the two would let a month of
       -- 403s look like a month of confirmations.
       (select max(ec.created_at) from event_candidate ec
         where ec.source_id = s.source_id) as last_verified_at,
       (select max(rf.fetched_at) from raw_fetch rf
         where rf.source_id = s.source_id
           and rf.content_hash not like %(attempt_like)s) as last_success_at,
       (select count(*) from raw_fetch rf
         where rf.source_id = s.source_id
           and rf.content_hash = %(failed)s
           and rf.fetched_at > coalesce(
                 (select max(rf2.fetched_at) from raw_fetch rf2
                   where rf2.source_id = s.source_id
                     and rf2.content_hash <> %(failed)s),
                 '-infinity'::timestamptz)) as fail_streak,
       (select ec.source_url from event_candidate ec
         where ec.source_id = s.source_id
           and ec.source_url is not null
           and ec.created_at > now() - interval '30 days'
         group by ec.source_url
         order by count(*) desc, max(ec.created_at) desc
         limit 1) as best_url
from source s
where s.enabled = true
"""

_EVENT_REFRESH_SQL = """
select c.source_id,
       c.source_url,
       e.start_time,
       e.end_time,
       (select max(rf.fetched_at) from raw_fetch rf
         where rf.source_id = c.source_id
           and rf.fetch_url = c.source_url) as last_fetch_at
from event e
join event_candidate c on c.promoted_event_id = e.event_id
where e.start_time is not null
  and c.source_url is not null
  and coalesce(e.end_time, e.start_time) > now()
"""

_FINGERPRINT_SQL = """
select content_hash, headers->>'etag', headers->>'last_modified'
from raw_fetch
where source_id = %s and fetch_url = %s
  and content_hash not like %s
order by fetched_at desc
limit 1
"""


def rows_to_states(rows: Sequence[Sequence[Any]]) -> Dict[str, SourceCrawlState]:
    """Map _STATE_SQL rows to states, keyed by source id (as text).

    Split out from the query so the shape can be unit-tested without a DB —
    the same split worker/run_once.py::order_for_rotation already uses.
    """
    states: Dict[str, SourceCrawlState] = {}
    for (source_id, last_attempt_at, last_verified_at, last_success_at,
         fail_streak, best_url) in rows:
        key = str(source_id)
        states[key] = SourceCrawlState(
            source_id=key,
            last_attempt_at=last_attempt_at,
            last_verified_at=last_verified_at,
            last_success_at=last_success_at,
            fail_streak=int(fail_streak or 0),
            best_url=best_url,
        )
    return states


def load_crawl_states(cur=None) -> Dict[str, SourceCrawlState]:
    """Per-source crawl state for every ENABLED source, keyed by source id."""
    params = {"attempt_like": f"{ATTEMPT_PREFIX}%", "failed": ATTEMPT_FAILED}
    if cur is not None:
        cur.execute(_STATE_SQL, params)
        return rows_to_states(cur.fetchall())
    from worker.candidate_store import db

    with db() as conn:
        with conn.cursor() as own:
            own.execute(_STATE_SQL, params)
            return rows_to_states(own.fetchall())


def load_door_fingerprint(
    source_id: Optional[str], url: str, cur=None,
) -> Optional[DoorFingerprint]:
    """The last successful read of THIS exact url, or None if never read.

    Per-URL, not per-source: a source has more than one door, and comparing a
    calendar page's body against the homepage's hash would call every fetch
    "changed" and pay for an extraction every run — the precise waste this
    exists to remove. A source with no id (the offline smoke stub) has no
    history and returns None rather than querying.
    """
    if source_id is None:
        return None
    args = (source_id, url, f"{ATTEMPT_PREFIX}%")

    def _read(c) -> Optional[DoorFingerprint]:
        c.execute(_FINGERPRINT_SQL, args)
        row = c.fetchone()
        if not row:
            return None
        content_hash, etag, last_modified = row
        return DoorFingerprint(
            url=url, content_hash=content_hash,
            etag=etag, last_modified=last_modified,
        )

    if cur is not None:
        return _read(cur)
    from worker.candidate_store import db

    with db() as conn:
        with conn.cursor() as own:
            return _read(own)


# Each field is guarded INDEPENDENTLY. A single WHERE on input_tokens would
# still have let a row with a numeric input and a non-numeric output raise on
# the output cast — the failure mode a cost report must not have, since it
# would take down a tick's telemetry over a malformed usage stamp. The
# timestamp is cast explicitly rather than left to parameter-type inference.
_EXTRACTION_USAGE_SQL = """
select coalesce(sum(case
         when jsonb_typeof(extracted->'_usage'->'input_tokens') = 'number'
         then (extracted->'_usage'->>'input_tokens')::bigint else 0 end), 0),
       coalesce(sum(case
         when jsonb_typeof(extracted->'_usage'->'output_tokens') = 'number'
         then (extracted->'_usage'->>'output_tokens')::bigint else 0 end), 0)
from event_candidate
where created_at >= %s::timestamptz
"""


def load_extraction_usage(since, cur=None) -> Tuple[int, int]:
    """(input_tokens, output_tokens) the model reported for work done since
    `since` — the tick's own AI spend, measured.

    ai/claude_provider.py stamps the SDK's `usage` object onto each extraction
    as `_usage`, and worker/ai_extract.py persists the provider meta into the
    candidate's `extracted` jsonb, so the numbers are already on disk. Summing
    them here keeps the cost report entirely OUT of the extraction surface the
    attended exam certifies.

    Two properties make the scope honest:
      * A concurrent importer writing candidates cannot inflate this. Importer
        rows carry no `_usage` (they call no model), and the jsonb_typeof guard
        counts only rows where the provider reported a real number — so a
        malformed or absent usage object contributes nothing rather than
        raising on a cast.
      * A provider that reports no usage at all yields 0, which
        worker/spend_report.py renders as "unknown" — never as free.
    """
    if cur is not None:
        cur.execute(_EXTRACTION_USAGE_SQL, (since,))
        row = cur.fetchone() or (0, 0)
        return int(row[0] or 0), int(row[1] or 0)
    from worker.candidate_store import db

    with db() as conn:
        with conn.cursor() as own:
            own.execute(_EXTRACTION_USAGE_SQL, (since,))
            row = own.fetchone() or (0, 0)
            return int(row[0] or 0), int(row[1] or 0)


def load_event_refresh_rows(cur=None) -> List[Sequence[Any]]:
    """Published events that have not ended, with their DEFINING page and when
    we last read it.

    The defining URL is `event_candidate.source_url` — the page the candidate
    was actually extracted from — reached through `promoted_event_id`, NOT
    `event.source_url`, which migration 0020 fills with the SOURCE's base_url
    (a homepage). Re-reading a homepage would not tell us whether Friday's show
    moved; re-reading the listing page it came from does.

    Three of the founder's rules live in the WHERE clause, so they cannot be
    forgotten by a caller: `e.start_time is not null` (dateless rows follow the
    source-door schedule only), `coalesce(e.end_time, e.start_time) > now()`
    ("then stop after end" — and no invented default duration for events with
    no end_time), and nothing about category, venue, or name anywhere.
    """
    if cur is not None:
        cur.execute(_EVENT_REFRESH_SQL)
        return list(cur.fetchall())
    from worker.candidate_store import db

    with db() as conn:
        with conn.cursor() as own:
            own.execute(_EVENT_REFRESH_SQL)
            return list(own.fetchall())
