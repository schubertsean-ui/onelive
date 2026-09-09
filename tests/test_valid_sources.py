from worker.valid_sources import is_validated, validated_ids


def test_chronicle_door_is_validated():
    assert is_validated(door_id="austin-chronicle-eventsearch")
    assert "do512-today" in validated_ids()


def test_social_alone_is_not_validated():
    assert not is_validated(source_class="social")
