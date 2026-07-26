"""CAPCOG boundary: the 10 member counties, not a radius.

The defect these tests pin: importers scoped the market as a 75-mile circle
around downtown Austin, and San Antonio is ~75 miles away — so Bexar County was
inside the query by construction and the live feed carried San Antonio venues.
"""
import json
import pathlib

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


def test_state_suffixes_do_not_defeat_the_lookup():
    assert in_capcog("Austin, TX") is True
    assert in_capcog("Austin, Texas") is True
    assert normalize_place("  Round Rock, TX ") == "round rock"


def test_a_city_whose_name_merely_ends_in_a_qualifier_is_untouched():
    """Two-letter qualifiers require a comma so trimming cannot eat a name."""
    assert normalize_place("Columbus") == "columbus"
    assert normalize_place("Texas City") == "texas city"


def test_no_place_is_both_inside_and_outside():
    """The two tables must not disagree — that would make membership depend on
    lookup order (the incomplete-enumeration class)."""
    assert not (set(CAPCOG_PLACES) & set(KNOWN_OUTSIDE))


def test_every_place_maps_to_a_real_member_county():
    for place, county in CAPCOG_PLACES.items():
        assert county in CAPCOG_COUNTIES, f"{place} -> {county}"


def test_a_zip_code_does_not_hide_a_known_city():
    """Venue addresses arrive as 'Austin, TX 78701'; the ZIP used to survive the
    suffix strip and turn a known Austin venue into UNKNOWN — a false gap."""
    from worker.region.capcog import in_capcog, normalize_place
    assert normalize_place("Austin, TX 78701") == "austin"
    assert in_capcog("Austin, TX 78701") is True
    assert in_capcog("San Antonio, TX 78205") is False


def test_the_web_boundary_file_is_generated_and_has_not_drifted():
    """ONE market boundary. The server filters by the Python tables and the site
    filters by the generated JSON; if they diverge, the two layers enforce two
    different markets — incomplete-enumeration in the place it does the most
    damage. Regenerate with tools/gen_region_boundary.py."""
    import json
    import pathlib
    import tools.gen_region_boundary as gen
    committed = json.loads(
        (pathlib.Path(gen.REPO) / "web" / "lib" / "capcog-boundary.json")
        .read_text(encoding="utf-8"))
    assert committed == gen.build(), (
        "web/lib/capcog-boundary.json is stale — run tools/gen_region_boundary.py")


def test_export_includes_code_not_only_markdown():
    """r3 blocker: the founder asked for 'every file' and the export globbed
    *.md only, silently omitting workflows, code, tests and the boundary JSON —
    while the index claimed to be the complete record."""
    import tools.export_context as ec
    tools_files = ec._files_for("tools")
    suffixes = {p.suffix for p in tools_files}
    assert ".py" in suffixes, "code must be exported, not just docs"
    wf = ec._files_for(".github/workflows")
    assert any(p.suffix in {".yml", ".yaml"} for p in wf)
    # and the noise stays out
    assert all("node_modules" not in p.parts for p in ec._files_for("web/lib"))


def test_membership_is_tri_state_and_unknown_is_not_a_guess():
    """An unknown place must be None. Guessing True publishes out-of-market
    events; guessing False silently deletes real coverage. Both are defects, so
    the answer is 'we do not know' and the report surfaces it."""
    assert in_capcog("Nowheresville") is None
    assert in_capcog(None) is None
    assert in_capcog("") is None
    assert in_capcog("   ") is None


def test_a_country_suffix_does_not_smuggle_a_known_outside_city_through():
    """The founder's invariant, failing open through formatting alone.

    Stripping one qualifier per pass left "San Antonio, TX, USA" intact, so it
    matched neither table and came back UNKNOWN — and the read path KEEPS
    unknowns (deliberately, so coverage gaps stay visible). A known-outside city
    would therefore be shown to a reader because a feed wrote the country.
    """
    for shape in ("San Antonio, TX, USA",
                  "San Antonio, Texas, United States",
                  "SAN ANTONIO, TX 78205, USA",
                  "san antonio, tx, us"):
        assert normalize_place(shape) == "san antonio", shape
        assert in_capcog(shape) is False, shape
    # and the same shapes must not break a city that IS in the market
    for shape in ("Austin, TX, USA", "Austin, Texas, United States",
                  "Austin, TX 78701-1234"):
        assert in_capcog(shape) is True, shape


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


