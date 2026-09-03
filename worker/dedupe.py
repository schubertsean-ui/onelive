"""Duplicate detection for canonical events (same venue + overlapping time window).

COLLISION IS NOT IDENTITY (founder, 2026-09-03; ONE-LIVE-TRUST.md). A neighbour
in the window is a COLLISION — two things at one venue near one time — and the
listing-update path has already had to learn, three times over, that a collision
identifies nothing (R-095, R-097, R-099). This module keeps the same split, in
the same words, on the publish side: `classify_duplicates` separates the one
shape that IS the same show (same venue AND the same start minute AND the same
normalized title) from a mere neighbour, so the publisher can refuse a genuine
re-publish while a double bill, a second stage, and an early-and-late set all
reach the map. The window is 90 minutes wide and a venue putting two acts on
inside 90 minutes is ordinary, so treating the whole window as identity answered
"does this exist?" with a dedupe test — the inversion ONE-LIVE-TRUST.md forbids.

Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/dedupe.py)
"""
from dataclasses import dataclass
from datetime import timezone
from typing import Any, List, Optional, Sequence, Tuple

import psycopg2

from worker.db_config import resolve_dsn
# ONE authority for what a title reduces to. Imported rather than re-derived:
# the publish side and the mutation side must never disagree about whether two
# listings carry the same name (R-095's whole subject).
from worker.listing_update import normalize_title


def db():
    return psycopg2.connect(resolve_dsn())


_DUP_SQL = """
  select event_id, title, start_time
  from event
  where venue_id=%s
    and start_time between %s - interval '%s minutes'
                    and %s + interval '%s minutes'
"""


@dataclass(frozen=True)
class DuplicateVerdict:
    """What the window around a candidate's slot actually contains.

    `same_show` holds the event ids that are the SAME listing (identity: venue,
    start minute, and normalized title all agree) — publishing again would put
    one show on the map twice. `neighbours` holds everything else in the window:
    real, separate happenings that must not be refused.
    """

    same_show: Tuple[str, ...] = ()
    neighbours: Tuple[str, ...] = ()

    @property
    def is_republish(self) -> bool:
        return bool(self.same_show)


def _same_minute(a: Any, b: Any) -> bool:
    """Equal to the minute, in UTC. Both must exist.

    Same convention as worker.crawl_state._as_utc and
    worker.listing_update._same_minute: a naive timestamp is read as UTC, so a
    fixture and a `timestamptz` column mean the same thing.
    """
    if a is None or b is None:
        return False
    if getattr(a, "tzinfo", "missing") == "missing" or getattr(b, "tzinfo", "missing") == "missing":
        return False  # not a datetime on one side — not a match, never a crash
    ua = (a if a.tzinfo is not None else a.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    ub = (b if b.tzinfo is not None else b.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    return ua.replace(second=0, microsecond=0) == ub.replace(second=0, microsecond=0)


def classify_duplicates(
    rows: Sequence[Sequence[Any]],
    *,
    title: Optional[str],
    start_time: Any,
) -> DuplicateVerdict:
    """Split window rows into same-show and neighbour. Pure — unit-testable
    without a database, which is the point: this decides whether a real show
    reaches the map.

    A row is the SAME SHOW only when all three agree: the venue (already true —
    the query filters on it), the start MINUTE, and the normalized title. A
    missing title on either side is NOT a match: `normalize_title` returns None
    for an absent title, and two rows that both lack a name have not been shown
    to be one row (the same rule worker/listing_update.py reached at r7, for the
    same reason — an anonymous listing confirms nothing).
    """
    ours = normalize_title(title)
    same: List[str] = []
    others: List[str] = []
    for row in rows:
        event_id, other_title, other_start = row[0], row[1], row[2]
        theirs = normalize_title(other_title)
        if ours is not None and theirs == ours and _same_minute(start_time, other_start):
            same.append(str(event_id))
        else:
            others.append(str(event_id))
    return DuplicateVerdict(same_show=tuple(same), neighbours=tuple(others))


def _window_rows(venue_id: str, start_time, window_minutes: int, cur=None):
    params = (venue_id, start_time, window_minutes, start_time, window_minutes)
    if cur is not None:
        cur.execute(_DUP_SQL, params)
        return cur.fetchall()
    with db() as conn:
        with conn.cursor() as own:
            own.execute(_DUP_SQL, params)
            return own.fetchall()


def find_possible_duplicates(venue_id: str, start_time, window_minutes: int = 90, cur=None) -> List[str]:
    """Return ids of existing canonical events in this candidate's window.

    Kept as-is for callers that only want the neighbourhood; it answers "what
    else is here?", never "is this the same show?" — ask `classify_window` for
    that.

    Pass `cur` to run inside the caller's transaction (so the dedupe check shares
    a consistent snapshot with any entities just resolved). If omitted, a
    short-lived read-only connection is opened.
    """
    return [str(r[0]) for r in _window_rows(venue_id, start_time, window_minutes, cur=cur)]


def classify_window(
    venue_id: str,
    start_time,
    *,
    title: Optional[str],
    window_minutes: int = 90,
    cur=None,
) -> DuplicateVerdict:
    """`find_possible_duplicates` + the identity split, in one call."""
    rows = _window_rows(venue_id, start_time, window_minutes, cur=cur)
    return classify_duplicates(rows, title=title, start_time=start_time)
