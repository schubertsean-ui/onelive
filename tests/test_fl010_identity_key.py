"""FL-010 / FL-013: same happening is one key.

Live miss: CELSIUS Combine: Texas printed three cards at 11:00 AM.
Cause: ingest_key included clock and Place.

Success: same title + same local date share one key.
A listing URL is enough by itself.
Place and clock-minute changes do not mint a second key.
"""
from worker.locale_pack.happening_key import identity_key
from worker.locale_pack.desk_publish import ingest_key
from tests.test_desk_publish import _union, _walk, _row, CHRONICLE


def _celsius(*, when: str, place: str = "", listing_url=None):
    return _union(_walk(CHRONICLE, "Austin Chronicle", [
        _row(
            "CELSIUS Combine: Texas",
            when=when,
            place=place,
            listing_url=listing_url,
        )
    ])).rows[0]


def test_empty_place_and_filled_place_are_one_key():
    hole = _celsius(when="2026-09-11T11:00:00-05:00", place="")
    filled = _celsius(when="2026-09-11T11:00:00-05:00", place="The Parish")
    assert identity_key(hole) == identity_key(filled)
    assert ingest_key(hole) == identity_key(hole)


def test_naive_utc_and_chicago_same_local_date_are_one_key():
    chicago = _celsius(when="2026-09-11T11:00:00-05:00")
    naive = _celsius(when="2026-09-11T16:00:00")
    assert identity_key(chicago) == identity_key(naive)
    assert identity_key(chicago).endswith("~2026-09-11")


def test_listing_url_is_the_key_without_clock_or_place():
    a = _celsius(
        when="2026-09-11T11:00:00-05:00",
        place="",
        listing_url="https://calendar.austinchronicle.com/event/celsius-1",
    )
    b = _celsius(
        when="2026-09-11T16:00:00Z",
        place="The Parish",
        listing_url="https://calendar.austinchronicle.com/event/celsius-1",
    )
    assert identity_key(a) == identity_key(b)
    assert identity_key(a) == "url:https://calendar.austinchronicle.com/event/celsius-1"


def test_keyable_row_is_title_plus_local_date():
    one = _union(_walk(CHRONICLE, "Austin Chronicle",
                       [_row("Night Music", when="2026-09-12T20:00:00-05:00",
                             place="The Bright Room")]))
    assert ingest_key(one.rows[0]) == "title:night music~2026-09-12"
