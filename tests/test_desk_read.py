"""read(public_desk) — a desk row exists because a desk printed it.

The rules under test are the founder's three: `when` only if the page states it,
unknown kind = other, via = desk. Plus the gate this path REPLACES: a happening
must not need an identity, or a clock, in order to exist (ONE-LIVE-TRUST.md).
"""
from __future__ import annotations

import os
from dataclasses import replace

import pytest

from worker.importers.structured_feed import normalize_structured, parse_jsonld
from worker.locale_pack import pack as lp
from worker.locale_pack.desk_read import DeskReadError, Happening, read

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fixtures", "locale_desks")
CAPCOG = "us-tx-capcog"


def fixture(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def doors():
    return {d.door_id: d for d in lp.hunt(CAPCOG)}


@pytest.fixture()
def desk(doors):
    return doors["austin-chronicle-eventsearch"]


# --- the four page shapes read ----------------------------------------------

def test_a_desk_list_yields_one_row_per_listing(desk):
    result = read(desk, fixture("desk_listing.html"))
    titles = [r.title for r in result.rows]
    assert titles == [
        "Hot Luck Block Party",
        "Blanton Late Night",
        "East Side Artisan Market",
        "County Line Fiddle Contest",
        "Lockhart Lecture Series: Caldwell County Water",
    ]
    assert result.skipped_untitled == 0


def test_a_json_ld_calendar_is_read_through_the_repos_one_json_ld_parser(doors):
    result = read(doors["ut-austin-localist"], fixture("civic_jsonld.html"))
    assert [r.title for r in result.rows] == [
        "Open Rehearsal: Wind Ensemble",
        "Public Lecture: Groundwater in the Hill Country",
        "Farmers Market on the Plaza",
    ]
