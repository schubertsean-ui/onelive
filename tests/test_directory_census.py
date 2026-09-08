"""Directory census: Place/Actor rows from founder-named directories.

These pages must NEVER become Happenings. Event permalinks on the same HTML
are ignored. No date is invented.
"""
from __future__ import annotations

import os

import pytest

from worker.locale_pack.directory_read import (
    DirectoryReadError, load_directories, read, spec_for,
)
from tools.directory_census import main as census_main

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fixtures", "directory_pages")


def fixture(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return fh.read()


def test_the_table_loads_the_founder_named_directories():
    ids = {s.directory_id for s in load_directories()}
    assert ids == {"do512-venues", "do512-artists"}


def test_venues_page_yields_places_not_events():
    spec = spec_for("do512-venues")
    result = read(spec, fixture("do512-venues.html"))
    names = [e.name for e in result.entities]
    assert names == [
        "Emo's",
        "Stubb's",
        "ACL Live at the Moody Theater",
        "Cheer Up Charlies",
    ]
    assert {e.kind for e in result.entities} == {"place"}
    assert all(e.city == "Austin" for e in result.entities)
    assert all("/venues/" in e.url for e in result.entities)
    assert all("/events/" not in e.url for e in result.entities)


def test_artists_page_yields_actors_not_events():
    spec = spec_for("do512-artists")
    result = read(spec, fixture("do512-artists.html"))
    names = [e.name for e in result.entities]
    assert names == ["Gary Clark Jr.", "Ghostland Observatory", "Black Pumas"]
    assert {e.kind for e in result.entities} == {"actor"}
    assert all(e.city is None for e in result.entities)


def test_an_event_permalink_on_a_directory_is_ignored():
    spec = spec_for("do512-venues")
    result = read(spec, fixture("do512-venues.html"))
    urls = [e.url for e in result.entities]
    assert not any("bright-room-quartet" in u for u in urls)


def test_follow_and_nav_and_off_host_are_ignored():
    spec = spec_for("do512-venues")
    result = read(spec, fixture("do512-venues.html"))
    names = [e.name.lower() for e in result.entities]
    assert "follow" not in names
    assert "venues" not in names
    assert "events" not in names
    assert all("other.example" not in e.url for e in result.entities)


def test_no_date_is_invented():
    spec = spec_for("do512-venues")
    result = read(spec, fixture("do512-venues.html"))
    for entity in result.entities:
        assert not hasattr(entity, "when") or getattr(entity, "when", None) is None
        assert "start" not in entity.__dict__


def test_an_empty_page_is_unread_not_empty_city():
    spec = spec_for("do512-venues")
    result = read(spec, "<html><body><p>nothing</p></body></html>")
    assert result.count == 0
    assert any("UNREAD" in n for n in result.notes)


def test_read_refuses_a_bare_id():
    with pytest.raises(DirectoryReadError):
        read("do512-venues", "<html></html>")


def test_fixture_cli_is_a_dry_run(capsys):
    code = census_main([])
    out = capsys.readouterr().out
    assert code == 0
    assert "FIXTURE" in out
    assert "Dry run" in out
    assert "Emo's" in out
    assert "Gary Clark Jr." in out


def test_write_without_real_is_refused(capsys):
    code = census_main(["--write"])
    err = capsys.readouterr().err
    assert code == 2
    assert "fixture" in err.lower()
