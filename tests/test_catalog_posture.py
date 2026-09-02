"""The posture fallback that makes the class B walk fire on real rows.

Live ground truth (ingest run 33578656538, 2026-09-02): 264 of 266 enabled
`source` rows declare NO access posture — `access_method=''`, `allowed=[]` —
so classify_entry resolved 265 of them to class D and the follow-pages walk had
nothing to walk. The committed catalog declares a posture for all 180 of its
entries, 140 of them class B. These tests pin the resolution rule that closes
that gap without writing a single row to production.
"""
import json

import pytest

from worker.sourcing import catalog_posture as cp
from worker.sourcing.source_class import classify_entry

CLASS_B_ENTRY = {
    "name": "Stubb's Austin", "base_url": "https://www.stubbsaustin.com/",
    "access_method": "public_web", "allowed": ["public_calendar_pages"],
}
CLASS_A_ENTRY = {
    "name": "City Calendar", "base_url": "https://city.example/events",
    "access_method": "public_web_or_ics", "allowed": ["official_feed"],
}


@pytest.fixture(autouse=True)
def _fresh_index(monkeypatch):
    monkeypatch.setattr(cp, "_INDEX", None)
    yield
    cp._INDEX = None


def _use(tmp_path, monkeypatch, entries):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    monkeypatch.setattr(cp, "CATALOG_PATH", str(path))
    monkeypatch.setattr(cp, "_INDEX", None)


def test_a_silent_row_gets_the_catalogs_posture(tmp_path, monkeypatch):
    """The live case: the row knows its name and URL and nothing else."""
    _use(tmp_path, monkeypatch, [CLASS_B_ENTRY])
    entry = cp.resolve_entry(
        name="Stubb's Austin", url="https://www.stubbsaustin.com/", config={})
    assert classify_entry(entry).source_class == "B"


def test_a_row_that_declares_a_posture_keeps_it(tmp_path, monkeypatch):
    """DB-first: a venue's own claim must outrank a file that predates it.

    The catalog calls this source class B; the row says it is a first-party
    claimed upload. The row wins.
    """
    _use(tmp_path, monkeypatch, [CLASS_B_ENTRY])
    entry = cp.resolve_entry(
        name="Stubb's Austin", url="https://www.stubbsaustin.com/",
        config={"access_method": "claimed_upload"})
    assert classify_entry(entry).source_class == "E"


def test_match_by_name_is_case_insensitive_and_exact(tmp_path, monkeypatch):
    _use(tmp_path, monkeypatch, [CLASS_B_ENTRY])
    assert classify_entry(cp.resolve_entry(
        name="  stubb's austin  ", url="https://elsewhere.example/",
        config={})).source_class == "B"
    assert classify_entry(cp.resolve_entry(
        name="Stubbs Austin", url="https://elsewhere.example/",
        config={})).source_class == "D", "a near-miss name is not a match"


def test_falls_back_to_url_when_the_name_does_not_match(tmp_path, monkeypatch):
    _use(tmp_path, monkeypatch, [CLASS_B_ENTRY])
    # www./trailing-slash differences must not defeat the match.
    assert classify_entry(cp.resolve_entry(
        name="Stubbs (renamed in the DB)", url="https://stubbsaustin.com",
        config={})).source_class == "B"


def test_an_ambiguous_url_resolves_to_nothing(tmp_path, monkeypatch):
    """Two entries, one URL: answering 'probably this one' is how a class D
    door gets walked. The key is dropped, so the row stays D."""
    twin = dict(CLASS_A_ENTRY, name="Another Source",
                base_url=CLASS_B_ENTRY["base_url"])
    _use(tmp_path, monkeypatch, [CLASS_B_ENTRY, twin])
    entry = cp.resolve_entry(
        name="Not In The Catalog", url="https://www.stubbsaustin.com/", config={})
    assert classify_entry(entry).source_class == "D"


def test_a_source_in_neither_place_is_class_d(tmp_path, monkeypatch):
    _use(tmp_path, monkeypatch, [CLASS_B_ENTRY])
    assert classify_entry(cp.resolve_entry(
        name="Unknown Venue", url="https://unknown.example/",
        config={})).source_class == "D"


@pytest.mark.parametrize("content", ["not json at all", '{"not": "a list"}'])
def test_an_unreadable_catalog_fails_closed(tmp_path, monkeypatch, content, caplog):
    path = tmp_path / "catalog.json"
    path.write_text(content, encoding="utf-8")
    monkeypatch.setattr(cp, "CATALOG_PATH", str(path))
    monkeypatch.setattr(cp, "_INDEX", None)
    with caplog.at_level("ERROR"):
        verdict = classify_entry(cp.resolve_entry(
            name="Stubb's Austin", url="https://www.stubbsaustin.com/", config={}))
    assert verdict.source_class == "D", "a lost catalog costs coverage, never grants access"
    assert any("unreadable" in r.message for r in caplog.records)


def test_a_missing_catalog_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(cp, "CATALOG_PATH", str(tmp_path / "nope.json"))
    monkeypatch.setattr(cp, "_INDEX", None)
    assert classify_entry(cp.resolve_entry(
        name="Stubb's Austin", url="https://www.stubbsaustin.com/",
        config={})).source_class == "D"


def test_the_catalog_supplies_posture_only_never_identity(tmp_path, monkeypatch):
    """The row's own URL survives: the fallback answers "may we read it?", it
    never rewrites WHICH page the loop was pointed at."""
    _use(tmp_path, monkeypatch, [CLASS_B_ENTRY])
    entry = cp.resolve_entry(
        name="Stubb's Austin", url="https://rowsown.example/live", config={})
    assert entry["base_url"] == "https://rowsown.example/live"


def test_the_real_committed_catalog_still_declares_class_b():
    """The number this whole change turns on, asserted against the REAL file:
    if a catalog edit ever drops the public-HTML posture, the walk silently
    stops firing — this test makes that loud instead."""
    entries = json.loads(open(cp.CATALOG_PATH, encoding="utf-8").read())
    letters = [
        classify_entry(cp.resolve_entry(
            name=e.get("name"), url=e.get("base_url"), config={})).source_class
        for e in entries if e.get("base_url")
    ]
    assert letters.count("B") >= 100, (
        f"only {letters.count('B')} class B sources in the committed catalog — "
        "the follow-pages walk fires on class B alone")
