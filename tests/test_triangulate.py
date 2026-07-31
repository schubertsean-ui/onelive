"""Unit tests for cross-source triangulation (worker/triangulate.py). PURE — no
DB, no network. Proves the same-event matcher and the corroboration assembly that
feeds the existing derive_confidence, including the invariants: a source never
corroborates itself, duplicate sources count once, missing fields are unmatchable
(never matched on partial data), and triangulation never manufactures 'disputed'.
"""
from worker.triangulate import (
    Corroboration,
    corroborate,
    same_event,
    triangulated_confidence,
)

# An AI-extracted candidate from a NON-anchor source (local media / radio blurb).
TARGET = {
    "source_class": "local_media",
    "source_id": "kutx",
    "venue_name": "Mohawk Austin",
    "start_time": "2026-08-01T20:00:00Z",
    "title": "Spoon live at the Mohawk",
}

# A Ticketmaster row for the SAME show: venue token overlaps ('mohawk'), start
# 30 min off (a listing vs a doors time), title overlaps ('spoon'). ANCHOR class.
TM_ROW = {
    "source_provider": "ticketing",
    "source_id": "ticketmaster",
    "venue_name": "Mohawk",
    "start_time": "2026-08-01T20:30:00Z",
    "title": "Spoon",
}


# ---- same_event -------------------------------------------------------------

def test_same_event_matches_across_sources():
    assert same_event(TARGET, TM_ROW) is True


def test_same_event_rejects_different_venue():
    other = dict(TM_ROW, venue_name="Stubb's Austin")
    assert same_event(TARGET, other) is False


def test_same_event_rejects_far_apart_start():
    other = dict(TM_ROW, start_time="2026-08-02T20:30:00Z")  # a day later
    assert same_event(TARGET, other) is False


def test_same_event_rejects_unrelated_title():
    other = dict(TM_ROW, title="Khruangbin")  # same venue+time, different show
    assert same_event(TARGET, other) is False


def test_same_event_unmatchable_when_field_missing():
    assert same_event(TARGET, dict(TM_ROW, start_time=None)) is False
    assert same_event(TARGET, dict(TM_ROW, venue_name=None)) is False
    assert same_event(TARGET, dict(TM_ROW, title=None)) is False


def test_same_event_tolerates_datetime_and_bare_date():
    import datetime as dt
    # A tz-naive datetime is treated as UTC — 20:00 naive vs TM_ROW 20:30Z = 30 min.
    a = dict(TARGET, start_time=dt.datetime(2026, 8, 1, 20, 0))
    assert same_event(a, TM_ROW) is True
    # A bare date (all-day) parses to midnight UTC; a same-venue show near that
    # midnight matches on the date bucket.
    allday = dict(TARGET, start_time="2026-08-02", title="Spoon")
    near_midnight = dict(TM_ROW, start_time="2026-08-02T00:30:00Z", title="Spoon")
    assert same_event(allday, near_midnight) is True


def test_same_event_converts_non_utc_offset_to_utc():
    """The regression the reviewer caught: an offset-bearing start must be
    CONVERTED to UTC, not stripped in place. 19:30-05:00 == 00:30Z the next day;
    it must match a 00:30Z row (0 min apart). A naive strip would read them as
    19:30 vs 00:30 (~23h apart) and wrongly REJECT — proving conversion happened."""
    src_offset = {"source_id": "s1", "source_class": "blog", "venue_name": "Mohawk",
                  "start_time": "2026-08-01T19:30:00-05:00", "title": "Spoon"}
    utc_row = {"source_id": "s2", "source_provider": "ticketing", "venue_name": "Mohawk",
               "start_time": "2026-08-02T00:30:00Z", "title": "Spoon"}
    assert same_event(src_offset, utc_row) is True

    # And the inverse: the SAME wall-clock string with vs without offset must NOT
    # be treated as identical instants. 20:00-05:00 (01:00Z Aug 2) is 5h from a
    # 20:00Z Aug 1 row → no match, where a naive strip would have fused them.
    aware = dict(TARGET, start_time="2026-08-01T20:00:00-05:00")
    naive_utc = dict(TM_ROW, start_time="2026-08-01T20:00:00Z")
    assert same_event(aware, naive_utc) is False


def test_same_event_non_string_field_does_not_raise():
    # A raw int/bool in a title/venue field must not raise (unmatchable, not crash).
    weird = dict(TM_ROW, title=12345, venue_name=True)
    assert same_event(TARGET, weird) is False


# ---- corroborate ------------------------------------------------------------

def test_corroborate_single_source_no_pool():
    corr = corroborate(TARGET, [])
    assert corr == Corroboration(source_classes=("local_media",), matches=0)


def test_corroborate_counts_independent_anchor():
    corr = corroborate(TARGET, [TM_ROW])
    assert corr.matches == 1
    assert set(corr.source_classes) == {"local_media", "ticketing"}


def test_corroborate_target_does_not_corroborate_itself():
    # A pool row from the SAME source id as the target must not be counted.
    echo = dict(TM_ROW, source_id="kutx", source_provider=None)
    corr = corroborate(TARGET, [echo])
    assert corr.matches == 0
    assert corr.source_classes == ("local_media",)


def test_corroborate_duplicate_source_counts_once():
    # Two Ticketmaster rows for the same show (same source id) count once.
    corr = corroborate(TARGET, [TM_ROW, dict(TM_ROW, title="Spoon (Standing)")])
    assert corr.matches == 1
    assert set(corr.source_classes) == {"local_media", "ticketing"}


def test_corroborate_ignores_non_matching_pool_events():
    noise = {"source_id": "sg", "source_provider": "ticketing",
             "venue_name": "Emo's", "start_time": "2026-08-01T20:00:00Z", "title": "Turnstile"}
    corr = corroborate(TARGET, [noise])
    assert corr.matches == 0
    assert corr.source_classes == ("local_media",)


# ---- triangulated_confidence (reuses derive_confidence) ---------------------

def test_confidence_single_source_is_unverified():
    assert triangulated_confidence(TARGET, []) == "unverified"


def test_confidence_anchor_corroboration_is_confirmed():
    # local_media + ticketing (anchor) → confirmed.
    assert triangulated_confidence(TARGET, [TM_ROW]) == "confirmed"


def test_confidence_two_nonanchor_sources_is_likely():
    blog = {"source_id": "chron", "source_class": "blog",
            "venue_name": "Mohawk", "start_time": "2026-08-01T20:15:00Z",
            "title": "Spoon at Mohawk"}
    # local_media + blog = two distinct non-anchor classes → likely (not confirmed).
    assert triangulated_confidence(TARGET, [blog]) == "likely"


def test_confidence_never_disputed_from_triangulation():
    # Even a same-venue/time but different-title pool event yields no dispute —
    # it simply doesn't corroborate; confidence stays the single-source value.
    conflicting = dict(TM_ROW, title="Some Other Band")
    assert triangulated_confidence(TARGET, [conflicting]) == "unverified"
