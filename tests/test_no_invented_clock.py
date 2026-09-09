"""Date-only when is a date. Do not invent 5:00 PM."""

from worker.locale_pack.desk_publish import _night_as_public_clock


def test_date_only_stays_a_date():
    assert _night_as_public_clock("2026-09-13") == "2026-09-13"
    assert "T17:00:00" not in _night_as_public_clock("2026-09-13")
