"""CAPCOG boundary: the 10 member counties, not a radius.

The defect these tests pin: importers scoped the market as a 75-mile circle
around downtown Austin, and San Antonio is ~75 miles away — so Bexar County was
inside the query by construction and the live feed carried San Antonio venues.
"""
import pytest

from worker.region.capcog import (
    CAPCOG_COUNTIES,
    CAPCOG_PLACES,
    KNOWN_OUTSIDE,
    county_for_place,
    in_capcog,
    normalize_place,
    region_report,
)


def test_capcog_is_exactly_ten_counties_and_excludes_bexar():
    assert len(CAPCOG_COUNTIES) == 10
    assert CAPCOG_COUNTIES == {
        "bastrop", "blanco", "burnet", "caldwell", "fayette",
        "hays", "lee", "llano", "travis", "williamson",
    }
    # The whole point: Bexar is not a member, however near the radius put it.
    assert "bexar" not in CAPCOG_COUNTIES
    assert "comal" not in CAPCOG_COUNTIES      # New Braunfels
    assert "guadalupe" not in CAPCOG_COUNTIES  # Seguin
    assert "bell" not in CAPCOG_COUNTIES       # Killeen / Temple / Belton


def test_the_san_antonio_venues_that_reached_the_live_feed_are_excluded():
    """The named casualties from the live run: Majestic Theatre, Freeman Expo
    Hall, Jo Long Theatre — all San Antonio, all Bexar, all must be False."""
    assert in_capcog("San Antonio") is False
    assert in_capcog("san antonio") is False
    assert in_capcog("San Antonio, TX") is False


def test_capcog_cities_across_all_ten_counties_are_included():
    for city, county in [
        ("Austin", "travis"), ("Round Rock", "williamson"), ("San Marcos", "hays"),
        ("Bastrop", "bastrop"), ("Lockhart", "caldwell"), ("Marble Falls", "burnet"),
        ("Johnson City", "blanco"), ("Llano", "llano"), ("Giddings", "lee"),
        ("La Grange", "fayette"),
    ]:
        assert in_capcog(city) is True, city
        assert county_for_place(city) == county, city


def test_near_misses_inside_a_75_mile_radius_are_correctly_outside():
    """Each of these is close enough to Austin to fall in the old circle."""
    for city in ("New Braunfels", "Seguin", "Killeen", "Temple", "Belton",
                 "Lampasas", "Bulverde", "Schertz", "Cibolo"):
        assert in_capcog(city) is False, city


def test_membership_is_tri_state_and_unknown_is_not_a_guess():
    """An unknown place must be None. Guessing True publishes out-of-market
    events; guessing False silently deletes real coverage. Both are defects, so
    the answer is 'we do not know' and the report surfaces it."""
    assert in_capcog("Nowheresville") is None
    assert in_capcog(None) is None
    assert in_capcog("") is None
    assert in_capcog("   ") is None


def test_state_suffixes_do_not_defeat_the_lookup():
    assert in_capcog("Austin, TX") is True
    assert in_capcog("Austin, Texas") is True
    assert normalize_place("  Round Rock, TX ") == "round rock"


def test_no_place_is_both_inside_and_outside():
    """The two tables must not disagree — that would make membership depend on
    lookup order (the incomplete-enumeration class)."""
    assert not (set(CAPCOG_PLACES) & set(KNOWN_OUTSIDE))


def test_every_place_maps_to_a_real_member_county():
    for place, county in CAPCOG_PLACES.items():
        assert county in CAPCOG_COUNTIES, f"{place} -> {county}"


def test_region_report_separates_outside_from_unknown():
    rows = [
        {"venue_city": "Austin"}, {"venue_city": "Austin"},
        {"venue_city": "San Marcos"},
        {"venue_city": "San Antonio"},          # outside — a defect
        {"venue_city": "Flavortown"},           # unknown — a worklist item
        {"venue_city": None},                   # no city at all
    ]
    r = region_report(rows)
    assert r["inside_count"] == 3
    assert r["outside_count"] == 1
    assert r["unknown_count"] == 1
    assert r["missing_city_count"] == 1
    assert r["outside_by_place"] == {"san antonio": 1}
    assert r["unknown_by_place"] == {"flavortown": 1}
    assert set(r["counties_covered"]) == {"travis", "hays"}
    # The eight counties with no coverage are named, not implied by absence.
    assert "llano" in r["counties_absent"]
    assert len(r["counties_absent"]) == 8


def test_coverage_refuses_a_self_grading_denominator():
    """With no target list, coverage must NOT report a percentage — 100% of
    what we found is what we found, and that reads as success."""
    import tools.capcog_coverage as cc
    out = cc.coverage([{"venue_name": "X", "venue_city": "Austin"}], None)
    assert out["status"] == "NO_TARGET_LIST"
    assert "coverage_pct" not in out


def test_coverage_measures_against_a_real_denominator():
    import tools.capcog_coverage as cc
    rows = [{"venue_name": "Mohawk", "venue_city": "Austin"}]
    targets = [
        {"name": "Mohawk", "city": "Austin", "county": "travis"},
        {"name": "Cheatham Street Warehouse", "city": "San Marcos", "county": "hays"},
        {"name": "Majestic Theatre", "city": "San Antonio", "county": "bexar"},
    ]
    out = cc.coverage(rows, targets)
    assert out["status"] == "MEASURED"
    # The Bexar row is dropped from the denominator, not counted as a miss.
    assert out["target_venue_count"] == 2
    assert out["covered_venue_count"] == 1
    assert out["coverage_pct"] == 50.0
    assert out["per_county"]["hays"]["missing"] == ["Cheatham Street Warehouse"]
