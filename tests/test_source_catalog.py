"""Tests for worker.source_catalog — the source -> curated cultural_domain join
that finally feeds the promote-time classifier (founder: "read what the source IS").

Kept robust to catalog edits: rather than hardcoding a source name (which a future
catalog edit could rename), the happy-path tests pick a real tagged row out of the
live catalog and assert the lookup reproduces it. The invariants (only valid domain
ids ever returned; unknown/untagged -> None; fail-safe on a bad file) are asserted
directly.
"""
import json

import pytest

from worker.importers.domain_map import DOMAINS
import worker.source_catalog as sc
from worker.source_catalog import cultural_domain_for_source
from worker.promote import card_fields

_VALID = set(DOMAINS)


def _reset_cache():
    sc._NAME_TO_DOMAIN = None


@pytest.fixture(autouse=True)
def _fresh_module_cache():
    # Each test starts from an unloaded cache so monkeypatching the path takes
    # effect and tests don't leak a built map into one another.
    _reset_cache()
    yield
    _reset_cache()


def _a_tagged_row():
    """Return (name, cultural_domain) for some catalog row that carries a VALID
    curated domain — the real signal this module exists to surface."""
    rows = json.load(open(sc._CATALOG_PATH, encoding="utf-8"))
    for r in rows:
        d = r.get("cultural_domain")
        if r.get("name") and d in _VALID:
            return r["name"], d
    pytest.skip("no catalog row carries a valid cultural_domain")


def test_known_tagged_source_resolves_to_its_curated_domain():
    name, domain = _a_tagged_row()
    assert cultural_domain_for_source(name) == domain


def test_lookup_is_case_and_whitespace_insensitive():
    name, domain = _a_tagged_row()
    assert cultural_domain_for_source(f"  {name.upper()}  ") == domain


def test_every_returned_value_is_a_real_domain_id_never_a_raw_string():
    # The whole point: no fabrication. Sweep the live catalog through the lookup
    # and confirm every non-None answer is a real OneLive domain id.
    rows = json.load(open(sc._CATALOG_PATH, encoding="utf-8"))
    seen_any = False
    for r in rows:
        got = cultural_domain_for_source(r.get("name"))
        if got is not None:
            seen_any = True
            assert got in _VALID, f"{r.get('name')!r} -> {got!r} is not a domain id"
    assert seen_any, "expected at least one curated source in the catalog"


def test_unknown_source_returns_none():
    assert cultural_domain_for_source("a source that is not in the catalog at all") is None


def test_empty_or_none_name_returns_none():
    assert cultural_domain_for_source(None) is None
    assert cultural_domain_for_source("") is None
    assert cultural_domain_for_source("   ") is None


def test_invalid_domain_value_is_never_indexed(tmp_path, monkeypatch):
    # A row whose cultural_domain is not a real id must yield None, not the bad
    # string — the guard that prevents a typo from becoming a user-facing category.
    bad = tmp_path / "cat.json"
    bad.write_text(json.dumps([
        {"name": "Bad Domain Source", "cultural_domain": "not-a-real-domain"},
        {"name": "Good Source", "cultural_domain": sorted(_VALID)[0]},
    ]))
    monkeypatch.setattr(sc, "_CATALOG_PATH", str(bad))
    _reset_cache()
    assert cultural_domain_for_source("Bad Domain Source") is None
    assert cultural_domain_for_source("Good Source") == sorted(_VALID)[0]


def test_untagged_source_row_returns_none(tmp_path, monkeypatch):
    cat = tmp_path / "cat.json"
    cat.write_text(json.dumps([{"name": "No Domain Source"}]))  # no cultural_domain key
    monkeypatch.setattr(sc, "_CATALOG_PATH", str(cat))
    _reset_cache()
    assert cultural_domain_for_source("No Domain Source") is None


def test_missing_catalog_file_fails_safe_to_none_not_crash(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(sc, "_CATALOG_PATH", str(tmp_path / "does_not_exist.json"))
    _reset_cache()
    # Must not raise, must return None, and must have logged the degrade loudly.
    assert cultural_domain_for_source("anything") is None
    assert any("could not load" in rec.message for rec in caplog.records)


def test_hint_flows_through_card_fields_to_the_category():
    # The wiring proof: a curated domain hint becomes the card's category, above
    # any title read. Uses card_fields directly (pure function, no DB).
    domain = sorted(_VALID)[0]
    card = card_fields("Some Ambiguous Title", "https://tix.example/x",
                       venue_domain_hint=domain)
    assert card["category"] == domain


def test_no_hint_leaves_category_to_the_title_read():
    # Without a hint an ambiguous title stays honest ('Other' -> None), never a
    # fabricated category — the pre-existing behavior is unchanged when unknown.
    card = card_fields("zzzz nondescript gathering", None)
    assert card["category"] is None
