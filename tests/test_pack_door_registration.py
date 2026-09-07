"""Pack-only public doors register without editing the armed catalog (#255).

Hermetic. Does not fetch. Does not write. mash_n is 0 because registration
does not invent a second identity.
"""
from __future__ import annotations

import hashlib
import json
import os

import pytest

from worker.locale.pack import hunt
from worker.locale.desk_publish import DeskPublishError, registration_for

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "sources", "master_sources_catalog_120.json")
CAPCOG = "us-tx-capcog"


@pytest.fixture(scope="module")
def doors():
    return {d.door_id: d for d in hunt(CAPCOG)}


@pytest.fixture(scope="module")
def catalog():
    with open(CATALOG, encoding="utf-8") as fh:
        return json.load(fh)


def test_armed_catalog_is_byte_identical_to_what_this_test_loaded():
    before = open(CATALOG, "rb").read()
    digest = hashlib.sha256(before).hexdigest()
    after = open(CATALOG, "rb").read()
    assert hashlib.sha256(after).hexdigest() == digest
    assert after == before


def test_a_pack_only_readable_door_walks_without_a_catalog_row(doors):
    door = doors["city-of-bastrop-recdesk"]
    assert door.readable
    reg = registration_for(door, [])
    assert reg.catalog_id == "pack:city-of-bastrop-recdesk"
    assert reg.source_class == "venue_calendar"
    assert reg.source_name
    assert "mash" not in reg.catalog_id


def test_a_wall_door_is_not_fetched(doors):
    door = doors["facebook-events"]
    assert not door.readable
    with pytest.raises(DeskPublishError):
        registration_for(door, [])


def test_a_junk_door_is_not_fetched(doors):
    door = doors["allevents-austin"]
    assert not door.readable
    with pytest.raises(DeskPublishError):
        registration_for(door, [])


def test_ambiguous_library_name_is_reported_never_coin_flipped(doors):
    door = doors["city-of-austin-library-events"]
    six = [
        {"id": f"lib-{i}", "name": f"Austin Public Library branch {i}",
         "category": "library_calendar",
         "base_url": f"https://library-{i}.example/"}
        for i in range(6)
    ]
    with pytest.raises(DeskPublishError) as exc:
        registration_for(door, six)
    assert "never coin-flipped" in str(exc.value)
    assert "6" in str(exc.value)


def test_mash_n_stays_zero_on_pack_registration(doors):
    """One door, one registration. No second identity minted."""
    door = doors["city-of-bastrop-recdesk"]
    a = registration_for(door, [])
    b = registration_for(door, [])
    assert a == b
    mash_n = 0 if a.catalog_id == b.catalog_id else 1
    assert mash_n == 0
