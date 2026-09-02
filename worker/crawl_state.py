"""Fair-crawl state — whose turn it is, which door to knock on, has it changed.

The problem this exists to fix (founder, 2026-09-02): the ingest run spent its
page budget IN SOURCE ORDER, so the first two link-heavy calendars consumed all
30 follow-pages and every source behind them got zero. Coverage Law makes a
missing locale or category a defect; a budget that starves all but two sources
is that defect in scheduler form. The fix is fairness, not more spend: MANY
sources per wave, FEW pages each.

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
point at a different source than it did last run, which is silent coverage
loss. The cursor is the least-recently-ATTEMPTED ordering
(worker/run_once.py::order_for_rotation), persisted as raw_fetch rows and
correct under insertion and deletion: whoever waited longest goes next.

DUE-NESS IS A SUPPRESSOR, NOT THE SCHEDULER. The cursor decides the order; the
due window only REMOVES sources that should not be touched yet — a failing
source backing off, a source visited minutes ago. That split is deliberate:
if due-ness were the scheduler, a clock skew or an empty raw_fetch table would
decide coverage. With the cursor scheduling, the worst a wrong due window can
do is under-fill one wave.

Pure functions plus three narrow SELECTs. No writes, no AI, no network.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

# --- raw_fetch vocabulary ----------------------------------------------------
#
# http_fetch writes attempt rows as "attempt:<outcome>" in content_hash (see
# ATTEMPT_HASH_PREFIX there). We read that vocabulary rather than re-define it;
# the two markers below are the outcomes that exist today.
ATTEMPT_PREFIX = "attempt:"
ATTEMPT_FAILED = "attempt:failed"
ATTEMPT_NOT_MODIFIED = "attempt:not_modified"

# --- Wave shape --------------------------------------------------------------

#: K — how many sources one wave crawls, and the armed cron's own ceiling.
#:
#: K is NOT a new knob: it is the existing per-run source ceiling
#: (--max-sources / ONELIVE_MAX_SOURCES_PER_RUN), which already fails closed on
#: a bad value. This constant is that ceiling's documented value, kept here
#: next to the arithmetic it belongs to.
#:
#: WHY 30, when the founder's rule for this pass is "many sources per wave, few
#: pages each": the fairness bound moved. It used to be K, because 30 sources
#: shared a 30-page follow budget IN SOURCE ORDER and the first two link-heavy
#: calendars took all of it. It is now the per-source DOOR (one), so a smaller
#: K would buy no fairness at all — it would only sweep the catalog slower, and
#: the 30 is a founder decision of its own (2026-08-04 freshness escalation,
#: docs/memory/decisions/2026-08-04_ingest-cap-raise-30.md: "every source
#: ~every 3h"). Undoing that to re-solve a problem the door cap already solves
#: would be trading real freshness for nothing.
#:
#: The arithmetic, at the armed cadence of one run every 20 minutes (72
#: waves/day) and <=2 doors per source: <=60 fetches per wave — the SAME
#: ceiling as before this pass, since 30 sources + 30 follow-pages was also 60
#: — and 2,160 source-slots/day, i.e. every source in a ~270-row catalog is
#: reached roughly every 3 hours. The difference is not the size of the wave;
#: it is that all 30 sources now get a door instead of two of them getting
#: fifteen. Extraction spend goes DOWN, because an unchanged door no longer
#: pays for one.
DEFAULT_SOURCES_PER_WAVE = 30

# --- Backoff policy ----------------------------------------------------------
#
# Minutes. Deliberately few numbers, none of them env knobs: every knob is a
# way for a scheduled loop to be mis-tuned in production without a code review.

#: A healthy source is not re-crawled more often than this. It sits just UNDER
#: the ~3h return interval K produces on the live catalog (see the arithmetic
#: above), and that ordering is the whole design: the cursor picks the wave,
#: the floor only catches a catalog small enough to lap itself, plus politeness
#: on a source we read minutes ago. A floor ABOVE the natural interval would
#: quietly become the scheduler and undo the founder's freshness setting —
#: which is exactly what an unexamined "6 hours sounds polite" would have done.
BASE_INTERVAL_MINUTES = 150

#: First failure waits an hour, then doubles: 1h, 2h, 4h, 8h ... A source
#: refusing an unauthenticated read (class D, 401/403) fails every time, so
#: this is what makes "we knock once" true over days instead of only within a
#: single run — no persisted closed-door flag to keep in sync with reality.
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
    last_success_at: Optional[datetime] = None
    fail_streak: int = 0
    best_url: Optional[str] = None

    def interval_minutes(self) -> int:
        """How long this source waits between waves, from its own history."""
        if self.fail_streak <= 0:
            return BASE_INTERVAL_MINUTES
        backoff = FAIL_BACKOFF_MINUTES * (2 ** (self.fail_streak - 1))
        return min(backoff, MAX_BACKOFF_MINUTES)

    def due_at(self) -> Optional[datetime]:
        """When this source may next be crawled. None = now (never attempted).

        A never-attempted source is due immediately and, being the oldest in
        the rotation, leads the cursor — new catalog rows are crawled first,
        which is what makes an import visible in the same day.
        """
        if self.last_attempt_at is None:
            return None
        return _as_utc(self.last_attempt_at) + timedelta(minutes=self.interval_minutes())

    def is_due(self, now: Optional[datetime] = None) -> bool:
        due = self.due_at()
        if due is None:
            return True
        return _as_utc(now or datetime.now(timezone.utc)) >= due


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


def due_source_ids(
    states: Sequence[SourceCrawlState],
    *,
    now: Optional[datetime] = None,
) -> List[str]:
    """The ids of the sources that may be crawled right now, order preserved.

    Order in = order out: the caller (worker/run_once.py) has already sorted
    least-recently-attempted first, and re-sorting here would put two
    definitions of "the cursor" in the tree. Truncating to K is likewise NOT
    done here — that is the budget ceiling, and it already has exactly one
    fail-closed implementation (run_once.apply_source_ceiling). This function
    does one job: drop what is not yet due.
    """
    moment = _as_utc(now or datetime.now(timezone.utc))
    return [s.source_id for s in states if s.is_due(moment)]


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
    for source_id, last_attempt_at, last_success_at, fail_streak, best_url in rows:
        key = str(source_id)
        states[key] = SourceCrawlState(
            source_id=key,
            last_attempt_at=last_attempt_at,
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
