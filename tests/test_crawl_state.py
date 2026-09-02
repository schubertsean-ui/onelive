"""worker/crawl_state.py — the fair-crawl cursor, backoff, door and fingerprint.

Pure logic plus two SELECTs exercised through a fake cursor: nothing here
touches a network, a model, or a database. What these pin, in the order the
founder's rules matter:

  1. K sources per wave are chosen by the ROTATION CURSOR; due-ness only
     removes. A never-attempted source is always due — "no history" must never
     read as "skip it".
  2. The backoff ladder: a healthy source has a floor, a failing one doubles,
     and the doubling has a ceiling. This is what makes "we knock once" true
     over days without persisting a closed-door flag.
  3. The door: best_url wins, but ONLY on the registered start URL's own site.
  4. The fingerprint: identical bytes mean no extraction, and the comparison is
     per-URL — a source has more than one door.
  5. Both queries are parameterized. A crawl scheduler that interpolates a URL
     into SQL is a source-controlled injection surface.
"""
import datetime as _dt

import pytest

from worker.crawl_state import (
    ATTEMPT_FAILED,
    BASE_INTERVAL_MINUTES,
    FAIL_BACKOFF_MINUTES,
    MAX_BACKOFF_MINUTES,
    DoorFingerprint,
    SourceCrawlState,
    choose_primary_door,
    due_source_ids,
    load_crawl_states,
    load_door_fingerprint,
    rows_to_states,
)

_TZ = _dt.timezone.utc
NOW = _dt.datetime(2026, 9, 2, 12, 0, tzinfo=_TZ)


def _ago(minutes):
    return NOW - _dt.timedelta(minutes=minutes)


# --- 2. the backoff ladder ---------------------------------------------------

def test_a_healthy_source_has_a_floor_not_a_backoff():
    assert SourceCrawlState("s").interval_minutes() == BASE_INTERVAL_MINUTES


@pytest.mark.parametrize("streak,expected", [
    (1, FAIL_BACKOFF_MINUTES),
    (2, FAIL_BACKOFF_MINUTES * 2),
    (3, FAIL_BACKOFF_MINUTES * 4),
])
def test_failures_double_the_wait(streak, expected):
    assert SourceCrawlState("s", fail_streak=streak).interval_minutes() == expected


def test_the_doubling_has_a_ceiling():
    """A permanently walled source must cost a few fetches a month, not stop
    forever: the cap is what lets a venue that fixes its site come back with no
    human touching anything."""
    assert SourceCrawlState("s", fail_streak=40).interval_minutes() == MAX_BACKOFF_MINUTES


# --- 1. due-ness removes; it never schedules --------------------------------

def test_never_attempted_is_always_due():
    state = SourceCrawlState("new-row")
    assert state.due_at() is None
    assert state.is_due(NOW)


def test_a_source_read_minutes_ago_is_not_due():
    assert not SourceCrawlState("s", last_attempt_at=_ago(5)).is_due(NOW)


def test_a_source_past_its_interval_is_due():
    state = SourceCrawlState("s", last_attempt_at=_ago(BASE_INTERVAL_MINUTES + 1))
    assert state.is_due(NOW)


def test_a_failing_source_waits_longer_than_a_healthy_one():
    age = BASE_INTERVAL_MINUTES + 1
    assert SourceCrawlState("ok", last_attempt_at=_ago(age)).is_due(NOW)
    assert not SourceCrawlState(
        "bad", last_attempt_at=_ago(age), fail_streak=6).is_due(NOW), (
        "a source that refuses every knock must not re-claim a wave slot")


def test_due_ids_preserve_the_cursor_order_and_only_remove():
    states = [
        SourceCrawlState("stalest", last_attempt_at=_ago(10_000)),
        SourceCrawlState("fresh", last_attempt_at=_ago(1)),
        SourceCrawlState("never"),
    ]
    assert due_source_ids(states, now=NOW) == ["stalest", "never"], (
        "order in is order out — the cursor is the schedule, not this function")


def test_a_naive_timestamp_is_read_as_utc_not_rejected():
    naive = _dt.datetime(2026, 9, 1, 12, 0)  # a fixture or a non-tz column
    assert SourceCrawlState("s", last_attempt_at=naive).is_due(NOW)


# --- 3. the door -------------------------------------------------------------

def _same_site(a, b):
    from worker.sourcing.page_discovery import same_site
    return same_site(a, b)


def test_best_url_on_the_same_site_becomes_the_primary_door():
    assert choose_primary_door(
        start_url="https://venue.example/",
        best_url="https://venue.example/events",
        same_site_fn=_same_site) == "https://venue.example/events"


def test_an_off_site_best_url_is_refused_and_the_start_url_is_used():
    """Coverage Law: an off-origin page is a DIFFERENT source with its own
    catalog row and class. Remembering one must never turn into ingesting it
    under this source's name."""
    assert choose_primary_door(
        start_url="https://venue.example/",
        best_url="https://tickets.example.com/venue",
        same_site_fn=_same_site) == "https://venue.example/"


def test_no_best_url_means_the_start_url():
    assert choose_primary_door(
        start_url="https://venue.example/", best_url=None,
        same_site_fn=_same_site) == "https://venue.example/"


def test_a_broken_same_site_check_falls_back_rather_than_guessing():
    def _boom(a, b):
        raise ValueError("malformed url")

    assert choose_primary_door(
        start_url="https://venue.example/",
        best_url="https://venue.example/events",
        same_site_fn=_boom) == "https://venue.example/"


# --- 4. the fingerprint ------------------------------------------------------

def test_identical_bytes_are_unchanged_and_anything_else_is_not():
    fp = DoorFingerprint(url="u", content_hash="abc123")
    assert fp.unchanged("abc123")
    assert not fp.unchanged("def456")
    assert not fp.unchanged(None), "an unknown hash is never 'unchanged'"


def test_a_source_with_no_id_has_no_history_and_never_queries():
    """The offline smoke stub has no source_id; asking the DB for its history
    would turn a zero-config smoke run into a DB dependency."""
    assert load_door_fingerprint(None, "https://example.com/") is None


class _FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


def test_fingerprint_reads_the_last_success_for_that_exact_url():
    cur = _FakeCursor([("hash-of-calendar", 'W/"e1"', "Mon, 01 Sep 2026 00:00:00 GMT")])
    fp = load_door_fingerprint("src-1", "https://venue.example/events", cur=cur)
    assert fp == DoorFingerprint(
        url="https://venue.example/events", content_hash="hash-of-calendar",
        etag='W/"e1"', last_modified="Mon, 01 Sep 2026 00:00:00 GMT")
    sql, params = cur.calls[0]
    assert params[:2] == ("src-1", "https://venue.example/events")


def test_a_url_never_read_before_has_no_fingerprint():
    assert load_door_fingerprint("src-1", "https://venue.example/new", cur=_FakeCursor([])) is None


def test_states_are_keyed_by_source_id_and_carry_the_four_facts():
    rows = [("11111111-1111-1111-1111-111111111111", _ago(30), _ago(30), 0,
             "https://venue.example/events")]
    states = rows_to_states(rows)
    state = states["11111111-1111-1111-1111-111111111111"]
    assert state.best_url == "https://venue.example/events"
    assert state.fail_streak == 0
    assert state.last_success_at == _ago(30)


def test_a_null_fail_streak_reads_as_zero_not_as_a_crash():
    states = rows_to_states([("s", None, None, None, None)])
    assert states["s"].fail_streak == 0


# --- 5. parameterized, always -------------------------------------------------

def test_both_queries_bind_their_values_rather_than_interpolating():
    """CLAUDE.md coding standards: parameterized queries only. The values here
    include a URL read out of fetched content, so this is not a formality."""
    cur = _FakeCursor([])
    load_crawl_states(cur=cur)
    load_door_fingerprint("src-1", "https://venue.example/x", cur=cur)
    for sql, params in cur.calls:
        assert params is not None, "every value must be bound"
        assert "https://" not in sql, "no URL is ever interpolated into SQL"
    state_sql, state_params = cur.calls[0]
    assert state_params["failed"] == ATTEMPT_FAILED
    assert "%(failed)s" in state_sql
