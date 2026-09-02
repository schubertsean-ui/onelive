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
    EVENT_REFRESH_LADDER_HOURS,
    FAIL_BACKOFF_MINUTES,
    MAX_BACKOFF_MINUTES,
    QUEUE_DISCOVER,
    QUEUE_REFRESH,
    UNVERIFIED,
    VERIFIED_ABSENT,
    VERIFIED_PRESENT,
    DoorFingerprint,
    SourceCrawlState,
    TickBudget,
    choose_primary_door,
    classify_recheck,
    crossed_rung,
    host_of,
    load_crawl_states,
    load_door_fingerprint,
    UPDATABLE_LISTING_FIELDS,
    may_delete_listing,
    may_update_listing,
    order_due,
    plan_event_refreshes,
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
    assert state.next_due_at() is None
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


def test_due_sources_are_ordered_most_overdue_first():
    states = [
        SourceCrawlState("fresh", last_attempt_at=_ago(1)),          # not due
        SourceCrawlState("barely", last_attempt_at=_ago(BASE_INTERVAL_MINUTES + 5)),
        SourceCrawlState("stalest", last_attempt_at=_ago(10_000)),
        SourceCrawlState("never"),
    ]
    assert [s.source_id for s in order_due(states, now=NOW)] == [
        "never", "stalest", "barely"]


def test_round_robin_is_only_the_tie_break_not_the_schedule():
    """Founder, verbatim: "round-robin is only a tie-break among due sources".
    The two orderings genuinely differ: `backing_off` was attempted LONGER ago,
    so pure round-robin would put it first — but it only just came due, while
    `healthy` has been waiting an extra day past its own interval."""
    backing_off = SourceCrawlState(
        "backing_off", last_attempt_at=_ago(8 * 60 + 1), fail_streak=4)  # due 1 min
    healthy = SourceCrawlState(
        "healthy", last_attempt_at=_ago(BASE_INTERVAL_MINUTES + 1440))   # due 1 day
    rank = {"backing_off": 0, "healthy": 1}   # round-robin would say this order
    assert [s.source_id for s in order_due([backing_off, healthy], now=NOW,
                                           rotation_rank=rank)] == [
        "healthy", "backing_off"]


def test_the_cursor_breaks_ties_between_equally_overdue_sources():
    a = SourceCrawlState("a", last_attempt_at=_ago(BASE_INTERVAL_MINUTES + 60))
    b = SourceCrawlState("b", last_attempt_at=_ago(BASE_INTERVAL_MINUTES + 60))
    assert [s.source_id for s in order_due([a, b], now=NOW,
                                           rotation_rank={"b": 0, "a": 1})] == ["b", "a"]


def test_queue_is_decided_by_the_door_alone_never_by_what_kind_of_place_it_is():
    """No category weighting: the ONLY input to the queue is whether we know
    this source's door. There is no field here for a thumb to sit on."""
    assert SourceCrawlState("s").queue == QUEUE_DISCOVER
    assert SourceCrawlState("s", best_url="https://v/events").queue == QUEUE_REFRESH


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


def test_states_carry_last_attempt_and_last_verified_as_separate_facts():
    """Founder: "record last_attempt vs last_verified". Merging them would let
    a month of 403s read as a month of confirmations."""
    rows = [("11111111-1111-1111-1111-111111111111", _ago(5), _ago(4000),
             _ago(30), 0, "https://venue.example/events")]
    state = rows_to_states(rows)["11111111-1111-1111-1111-111111111111"]
    assert state.best_url == "https://venue.example/events"
    assert state.fail_streak == 0
    assert state.last_attempt_at == _ago(5)
    assert state.last_verified_at == _ago(4000)
    assert state.last_attempt_at != state.last_verified_at


def test_a_null_fail_streak_reads_as_zero_not_as_a_crash():
    states = rows_to_states([("s", None, None, None, None, None)])
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


# --- the tick budget: what actually stops a tick -----------------------------

class _Clock:
    """A hand-cranked monotonic clock, so the wall-clock rule is testable
    without sleeping. A budget you cannot test is a budget you do not have."""

    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_a_tick_ends_on_the_wall_clock():
    clock = _Clock()
    budget = TickBudget(max_seconds=600, clock=clock)
    assert budget.tick_stop() is None
    clock.t = 599
    assert budget.tick_stop() is None
    clock.t = 600
    assert budget.tick_stop() == "wall_clock"


def test_a_tick_ends_on_the_fetch_cap():
    budget = TickBudget(max_fetches=2)
    budget.record_fetch("a.example", queue=QUEUE_REFRESH)
    assert budget.tick_stop() is None
    budget.record_fetch("b.example", queue=QUEUE_REFRESH)
    assert budget.tick_stop() == "fetch_budget"


def test_a_tick_ends_on_the_model_budget():
    """Extraction is the only stage that may call Anthropic, so extract CALLS
    are what the model budget bounds — there is no second place for cost to
    hide. Calls are counted in flight (that is what the budget enforces);
    tokens arrive afterwards from what the provider itself reported."""
    budget = TickBudget(max_extract_calls=1)
    assert budget.may_extract()
    budget.record_extract()
    assert not budget.may_extract()
    assert budget.tick_stop() == "model_budget"
    budget.record_tokens(input_tokens=900, output_tokens=100)
    assert budget.outcomes()["input_tokens"] == 900
    assert budget.outcomes()["output_tokens"] == 100


def test_usage_is_summed_from_what_the_provider_reported_not_from_the_extractor():
    """The cost report reads `_usage` back off the candidate rows rather than
    threading a number through worker/ai_extract.py — extraction-surface code
    the attended golden exam does not execute. Same number, on the side of the
    certification gate that certifies nothing."""
    from worker.crawl_state import load_extraction_usage
    cur = _FakeCursor([(12345, 678)])
    assert load_extraction_usage("2026-09-02T00:00:00Z", cur=cur) == (12345, 678)
    sql, params = cur.calls[0]
    assert params == ("2026-09-02T00:00:00Z",), "the window is bound, not interpolated"
    assert "jsonb_typeof" in sql, (
        "a row whose usage is absent or malformed must contribute nothing, "
        "never raise on a cast")


def test_no_usage_at_all_reads_as_zero_which_prints_as_unknown():
    from worker.crawl_state import load_extraction_usage
    from worker.spend_report import format_spend
    assert load_extraction_usage("t", cur=_FakeCursor([(None, None)])) == (0, 0)
    assert "unknown" in format_spend(
        model_id="claude-haiku-4-5", input_tokens=0, output_tokens=0)


def test_host_politeness_defers_the_source_it_does_not_end_the_tick():
    """One popular host must not cost every other source its turn."""
    budget = TickBudget(max_fetches_per_host=1, max_fetches=50)
    budget.record_fetch("busy.example", queue=QUEUE_REFRESH)
    assert budget.may_fetch("busy.example", queue=QUEUE_REFRESH) == "host_politeness"
    assert budget.may_fetch("quiet.example", queue=QUEUE_REFRESH) is None
    assert budget.tick_stop() is None, "the tick goes on"


def test_discovery_cannot_spend_more_than_its_share_when_refresh_needs_it():
    """A catalog import of door-less rows must not fill a tick the live catalog
    needed for refreshing."""
    budget = TickBudget(max_fetches=10, discover_share=0.2)
    budget.reserve_for_plan([QUEUE_DISCOVER] * 20 + [QUEUE_REFRESH] * 20)
    for _ in range(2):                       # 10 - min(20, 8) = 2
        assert budget.may_fetch("a.example", queue=QUEUE_DISCOVER) is None
        budget.record_fetch("a.example", queue=QUEUE_DISCOVER)
    assert budget.may_fetch("b.example", queue=QUEUE_DISCOVER) == "discover_share"
    assert budget.may_fetch("b.example", queue=QUEUE_REFRESH) is None


def test_a_share_never_strands_budget_it_has_nobody_to_share_with():
    """The bug these reservations replaced: a tick made entirely of discover
    items used to cap itself at half its own fetch budget and leave the rest
    unused, because there was no refresh work for the other half to go to."""
    budget = TickBudget(max_fetches=10, discover_share=0.5)
    budget.reserve_for_plan([QUEUE_DISCOVER] * 8)
    for _ in range(10):
        assert budget.may_fetch("a.example", queue=QUEUE_DISCOVER) != "discover_share"
        budget.record_fetch("a.example", queue=QUEUE_DISCOVER)
    assert budget.tick_stop() == "fetch_budget", "the FETCH cap binds, not the share"


def test_one_refresh_item_reserves_one_fetch_not_half_the_tick():
    budget = TickBudget(max_fetches=10, discover_share=0.5)
    budget.reserve_for_plan([QUEUE_DISCOVER] * 50 + [QUEUE_REFRESH])
    assert budget.max_discover_fetches == 9


@pytest.mark.parametrize("kwargs", [
    {"max_seconds": -1}, {"max_fetches": -1}, {"max_extract_calls": -1},
    {"max_fetches_per_host": -1}, {"discover_share": 1.5},
])
def test_a_malformed_budget_fails_closed_at_construction(kwargs):
    with pytest.raises(ValueError):
        TickBudget(**kwargs)


def test_www_is_folded_so_a_site_cannot_get_two_host_budgets():
    assert host_of("https://www.venue.example/x") == host_of("https://venue.example/y")


# --- event proximity ---------------------------------------------------------

def test_the_ladder_is_the_founders_rungs():
    assert EVENT_REFRESH_LADDER_HOURS == (30 * 24, 14 * 24, 7 * 24, 3 * 24, 24, 6)


@pytest.mark.parametrize("days_out,expected_rung", [
    (40, None),          # nothing crossed yet
    (20, 30 * 24),
    (10, 14 * 24),
    (5, 7 * 24),
    (2, 3 * 24),
])
def test_a_never_read_page_owes_exactly_one_fetch_its_nearest_crossed_rung(
        days_out, expected_rung):
    """Not one fetch per rung it ever passed — one fetch, at the nearest."""
    start = NOW + _dt.timedelta(days=days_out)
    assert crossed_rung(start, last_fetch_at=None, now=NOW) == expected_rung


def test_a_page_read_since_the_rung_is_not_due_again():
    start = NOW + _dt.timedelta(days=6)          # T-7d crossed a day ago
    assert crossed_rung(start, last_fetch_at=NOW - _dt.timedelta(hours=1),
                        now=NOW) is None


def test_one_page_fetch_covers_every_event_on_that_page():
    """Founder: "Dedupe: one page fetch covers all events on that page." A
    calendar listing forty shows is ONE item, at the nearest rung any of them
    has crossed."""
    rows = [
        ("s1", "https://venue.example/calendar", NOW + _dt.timedelta(days=6), None, None),
        ("s1", "https://venue.example/calendar", NOW + _dt.timedelta(hours=3), None, None),
        ("s1", "https://venue.example/calendar", NOW + _dt.timedelta(days=20), None, None),
    ]
    planned = plan_event_refreshes(rows, now=NOW)
    assert len(planned) == 1
    assert planned[0].events == 3
    assert planned[0].rung_hours == 6, "the nearest reason to look wins"


def test_a_dateless_row_never_enters_the_proximity_queue():
    """Founder: "Dateless rows: source-door schedule only."""
    assert plan_event_refreshes(
        [("s1", "https://venue.example/x", None, None, None)], now=NOW) == []


def test_the_nearest_event_outranks_the_one_that_has_waited_longer():
    """Caught by this test while writing it, and it was a real ordering bug:
    a T-30d rung crossed a DAY ago is "more overdue" (86400s) than a day-of
    rung crossed an HOUR ago (3600s), so ranking on overdue-ness alone put an
    event a month out ahead of one starting in five hours. The ladder exists to
    concentrate attention where a change still matters to somebody tonight."""
    rows = [
        ("s1", "https://a.example/x", NOW + _dt.timedelta(days=29), None, None),
        ("s1", "https://b.example/x", NOW + _dt.timedelta(hours=5), None, None),
    ]
    assert [r.url for r in plan_event_refreshes(rows, now=NOW)] == [
        "https://b.example/x", "https://a.example/x"]


def test_overdue_ness_still_breaks_ties_within_one_rung():
    rows = [
        ("s1", "https://fresh.example/x", NOW + _dt.timedelta(hours=5), None, None),
        ("s1", "https://stale.example/x", NOW + _dt.timedelta(hours=1), None, None),
    ]
    assert [r.url for r in plan_event_refreshes(rows, now=NOW)] == [
        "https://stale.example/x", "https://fresh.example/x"]


def test_the_event_queue_gets_priority_but_not_a_monopoly():
    """A night full of near events must not freeze the ordinary rotation."""
    from worker.crawl_state import QUEUE_EVENT
    budget = TickBudget(max_fetches=10, event_share=0.3)
    budget.reserve_for_plan([QUEUE_EVENT] * 20 + [QUEUE_REFRESH] * 20)
    for _ in range(3):                       # 10 - min(20, 7) = 3
        assert budget.may_fetch("a.example", queue=QUEUE_EVENT) is None
        budget.record_fetch("a.example", queue=QUEUE_EVENT)
    assert budget.may_fetch("b.example", queue=QUEUE_EVENT) == "event_share"
    assert budget.may_fetch("b.example", queue=QUEUE_REFRESH) is None


# --- verification: fail closed ------------------------------------------------

def test_only_two_shapes_confirm_anything():
    assert classify_recheck(door_kind="unchanged")[0] == VERIFIED_PRESENT
    assert classify_recheck(door_kind="changed",
                            page_decision="held")[0] == VERIFIED_PRESENT
    assert classify_recheck(door_kind="missed",
                            http_status=404)[0] == VERIFIED_ABSENT


@pytest.mark.parametrize("kind,status,decision", [
    ("wall", 403, None),
    ("backoff", 429, None),
    ("backoff", 503, None),
    ("deferred", None, None),
    ("offsite", None, None),
    ("missed", 500, None),
    ("missed", None, None),
    ("changed", None, "sensor_rejected"),
    ("changed", None, "deferred"),
    ("something_new_nobody_wrote_yet", None, None),
])
def test_everything_else_is_unverified_and_the_last_good_row_stands(
        kind, status, decision):
    """Founder, verbatim: "Fetch failure / cap / 429 / parse miss = last good
    row stands." Including the shape nobody has written yet — the default must
    be the closed one, or the next new failure mode fails OPEN."""
    verdict, reason = classify_recheck(
        door_kind=kind, page_decision=decision, http_status=status)
    assert verdict == UNVERIFIED
    assert not may_update_listing(verdict)
    assert reason


def test_an_ambiguous_parse_keeps_rather_than_changes():
    """A page we fetched but could not read tells us nothing about the listing.
    "Ambiguous parse = keep."""
    assert classify_recheck(
        door_kind="changed", page_decision="sensor_rejected")[0] == UNVERIFIED


def test_only_same_page_evidence_licenses_an_update():
    """Founder: "Confirmed check MAY update a published listing (time, cancel,
    postpone, title) only with same-page evidence." VERIFIED_PRESENT is the
    only verdict that HAS a page behind it."""
    assert may_update_listing(VERIFIED_PRESENT)
    assert not may_update_listing(UNVERIFIED)


def test_a_404_licenses_re_finding_the_door_not_changing_a_listing():
    """The one place the two directives had to be read together. A clear 404
    confirms the PAGE is gone — but a venue reorganizing its URLs, a CMS
    migration and a genuinely cancelled show all 404 identically, and there is
    no page left to carry same-page evidence. So it licenses no status change.
    (Re-finding the door is what the loop already does, by falling back to the
    registered start URL.)"""
    verdict, reason = classify_recheck(door_kind="missed", http_status=404)
    assert verdict == VERIFIED_ABSENT
    assert not may_update_listing(verdict), (
        "a 404 has no page, so it has no same-page evidence")
    assert "no listing change" in reason


@pytest.mark.parametrize("verdict", [VERIFIED_PRESENT, VERIFIED_ABSENT, UNVERIFIED,
                                     "something_nobody_wrote_yet"])
def test_no_verdict_ever_licenses_deleting_a_published_row(verdict):
    """Founder: "Do not delete the row from the catalog; mark cancelled/moved
    and keep evidence." Also Coverage Law (a legally seen row is never dropped)
    and the 4-state model (disputed is shown, never hidden)."""
    assert not may_delete_listing(verdict)


def test_the_updatable_fields_are_the_founders_enumeration():
    """"time, cancel, postpone, title" — cancel and postpone are STATUSES on a
    row that stays, which is why there is no delete in this list."""
    assert UPDATABLE_LISTING_FIELDS == ("start_time", "end_time", "status", "title")


def test_the_loop_still_updates_nothing_today():
    """The policy is ratified and encoded; the update path is a separate
    ticket. Pinned so "encoded" can never be mistaken for "wired": the
    scheduler module imports nothing that can write to `event`."""
    import ast
    import pathlib
    import worker.crawl_state as cs
    tree = ast.parse(pathlib.Path(cs.__file__).read_text())
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert "worker.promote" not in imported
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert "update event" not in node.value.lower()
            assert "delete from event" not in node.value.lower()


# --- the budgets come from the environment, fail-closed ----------------------

@pytest.mark.parametrize("env", list(TickBudget.ENV.values()))
def test_every_tick_budget_is_declarable_and_fails_closed(monkeypatch, env):
    """The armed cron declares these where the spend happens. A typo must abort
    the tick before the first fetch — never silently mean "the default", and
    never mean "uncapped"."""
    name, default, _noun = env
    monkeypatch.setenv(name, "12")
    assert TickBudget.from_env() is not None
    monkeypatch.setenv(name, "not-a-number")
    with pytest.raises(ValueError, match=name):
        TickBudget.from_env()
    monkeypatch.setenv(name, "-1")
    with pytest.raises(ValueError, match=name):
        TickBudget.from_env()
    monkeypatch.setenv(name, "")          # how CI forwards an unset variable
    assert TickBudget.from_env() is not None
