from worker.locale_pack.existence import exists, hold_reason


def test_titled_readable_door_exists_without_when_or_place():
    assert exists(True, "Jutes, Mothica, wilt", None) is True
    assert hold_reason(door_readable=True, title="Jutes, Mothica, wilt", when=None, place=None) is None


def test_listing_url_without_title_still_exists():
    assert exists(True, "", "https://calendar.austinchronicle.com/event/1") is True


def test_empty_title_and_url_is_no_title():
    assert hold_reason(door_readable=True, title="", listing_url="") == "no_title"
