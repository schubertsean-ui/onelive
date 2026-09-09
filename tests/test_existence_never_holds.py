"""A titled card from a readable door publishes. Date and place cannot hold."""
from worker.locale_pack.existence import exists, hold_reason


def test_titled_readable_door_exists_without_when_or_place():
    assert exists(True, "Jutes, Mothica, wilt", None) is True
    assert hold_reason(
        door_readable=True,
        title="Jutes, Mothica, wilt",
        when=None,
        place=None,
    ) is None


def test_listing_url_without_title_still_exists():
    assert exists(True, "", "https://calendar.austinchronicle.com/event/1") is True
    assert hold_reason(
        door_readable=True,
        title="",
        listing_url="https://calendar.austinchronicle.com/event/1",
    ) is None


def test_empty_title_and_url_is_no_title():
    assert hold_reason(door_readable=True, title="", listing_url="") == "no_title"


def test_unreadable_door_does_not_exist():
    assert exists(False, "A show", None) is False
