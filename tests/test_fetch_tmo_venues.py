"""Texas Music Office directory — denominator layer 3.

Two properties are load-bearing and both are about refusing to be quietly wrong:

1. An unwritten parser must REFUSE, not return []. An empty list from a parser
   that was never implemented is indistinguishable from "this directory has no
   venues" — and the directory advertises ~610 in the Austin area alone.

2. Membership is decided by the CAPCOG BOUNDARY, never by the TMO's own
   "austin region". TMO's region is area codes 512/737; CAPCOG is ten named
   counties. Fayette and Lee are largely 979, so trusting the region would
   silently omit the two counties with the thinnest coverage.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import tools.fetch_tmo_venues as tmo  # noqa: E402


def test_an_unwritten_parser_REFUSES_rather_than_returning_nothing():
    with pytest.raises(NotImplementedError, match="not written yet"):
        tmo.parse_rows("<html><body>anything at all</body></html>")


def test_membership_comes_from_the_BOUNDARY_not_the_TMO_region():
    inside, unplaceable = tmo.to_capcog_rows([
        {"name": "Mohawk", "city": "Austin"},
        {"name": "Gruene Hall", "city": "New Braunfels"},   # Comal — NOT CAPCOG
        {"name": "Somewhere", "city": "San Antonio"},        # Bexar — NOT CAPCOG
        {"name": "Sengelmann", "city": "Schulenburg"},       # Fayette — 979, in CAPCOG
    ])
    names = [r["name"] for r in inside]
    assert "Mohawk" in names
    assert "Gruene Hall" not in names, "Comal county is not CAPCOG"
    assert "Somewhere" not in names, "Bexar county is not CAPCOG"
    # and nothing known-outside leaks into the worklist either
    assert not any(r["name"] in {"Gruene Hall", "Somewhere"} for r in unplaceable)


def test_an_unrecognised_city_is_a_WORKLIST_ITEM_not_a_silent_drop():
    """These rows are the likeliest outer-county venues the boundary has not
    learned. Dropping them silently would hide exactly the coverage we lack."""
    inside, unplaceable = tmo.to_capcog_rows(
        [{"name": "Some Hall", "city": "A Town Nobody Listed"}])
    assert inside == []
    assert [r["name"] for r in unplaceable] == ["Some Hall"]


def test_rows_that_survive_carry_their_county_and_layer():
    inside, _ = tmo.to_capcog_rows([{"name": "Mohawk", "city": "Austin"}])
    row = inside[0]
    assert row["county"] == "travis"
    assert row["source_layer"] == "tmo"
    assert row["target_kind"] == "venue"


def test_only_place_categories_are_fetched_as_venues():
    """Radio stations and weekly publications are SOURCES, not rooms. Counting
    a newspaper as a venue would corrupt the denominator."""
    assert "venues" in tmo.VENUE_CATEGORIES
    assert "nightclubs-dancehalls-small-venues" in tmo.VENUE_CATEGORIES
    for not_a_place in ("weekly-publications", "radio", "RadStaDefault"):
        assert not any(not_a_place in c for c in tmo.VENUE_CATEGORIES)


def test_the_region_is_documented_as_a_hint_not_a_market_definition():
    """The distinction is the whole reason Fayette and Lee do not vanish."""
    doc = tmo.__doc__ or ""
    assert "979" in doc, "the area-code mismatch must be stated, not assumed"
    assert "Fayette" in doc and "Lee" in doc
