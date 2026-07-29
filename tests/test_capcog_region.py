"""CAPCOG boundary: the 10 member counties, not a radius.

The defect these tests pin: importers scoped the market as a 75-mile circle
around downtown Austin, and San Antonio is ~75 miles away — so Bexar County was
inside the query by construction and the live feed carried San Antonio venues.
"""
import pytest

from worker.region.capcog import (
    CAPCOG_COUNTIES,
    county_in_place,
    normalize_county,
    row_verdict,
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


# ---- r12 evaluator findings: five ways the boundary was still defeatable -----

def test_a_county_qualifier_does_not_smuggle_an_outside_city_through():
    """'San Antonio, Bexar County, TX' stripped ZIP, state and country but not
    the COUNTY, so it matched neither table, returned UNKNOWN — and the read
    path KEEPS unknowns. The invariant was defeatable by naming the county."""
    for shape in ("San Antonio, Bexar County, TX",
                  "san antonio, bexar county",
                  "SAN ANTONIO, BEXAR COUNTY, TEXAS, USA"):
        assert normalize_place(shape) == "san antonio", shape
        assert in_capcog(shape) is False, shape
    # and it must not damage an in-market city written the same way
    assert normalize_place("Austin, Travis County, TX") == "austin"
    assert in_capcog("Austin, Travis County, TX") is True


def test_a_blank_preferred_field_does_not_hide_a_real_one():
    """`venue_city or city` looks safe but '' and '   ' are the two shapes that
    beat it: '' is falsy in Python yet wins outright under JavaScript's ??, and
    '   ' is TRUTHY in Python. Either way {venue_city: blank, city: 'San
    Antonio'} was reported as a row with no city rather than an out-of-market
    row — and unknown rows are kept."""
    for blank in ("", "   ", "\t", ",", None):
        row = {"venue_city": blank, "city": "San Antonio"}
        assert row_verdict(row) is False, repr(blank)
    assert row_verdict({"venue_city": "", "city": "Austin"}) is True


def test_county_evidence_decides_a_row_the_city_cannot():
    """CAPCOG IS ten counties. A row that names Bexar is out of market even
    when its city is blank, unrecognised, or a town we have never catalogued —
    ignoring the decisive field was the county-boundary-evidence-ignored
    finding."""
    assert row_verdict({"county": "Bexar", "venue_city": None}) is False
    assert row_verdict({"venue_county": "Bexar County, TX", "city": "Nowhere"}) is False
    assert row_verdict({"venue_county": "Travis"}) is True
    assert row_verdict({"county": "Llano", "city": "Somewhere Unlisted"}) is True
    # A county we do not know is still not a guess.
    assert row_verdict({"county": "Nowhere County"}) is None


def test_a_known_outside_signal_drops_the_row_even_against_an_in_market_county():
    """PR #107: county-first precedence let a contradictory in-market county
    field carry a known-outside CITY onto /tonight. A boundary whose job is
    "never show San Antonio" resolves a contradiction to DROP, and this rule is
    identical to the TypeScript rowVerdict so the two paths are one boundary."""
    # Known-outside county still drops an in-market-looking city (unchanged):
    assert row_verdict({"county": "Bexar", "city": "Austin"}) is False
    # Known-outside CITY now vetoes an in-market county (the fix):
    assert row_verdict({"venue_county": "Travis", "city": "San Antonio"}) is False
    assert row_verdict({"venue_county": "Travis", "venue_city": "San Antonio"}) is False
    # A city string embedding a contradictory in-market county still drops on its
    # known-outside city:
    assert row_verdict({"venue_city": "San Antonio, Travis County, TX"}) is False
    # County still RESCUES a merely-unrecognised city (True beats None):
    assert row_verdict({"venue_county": "Travis", "venue_city": "Rollingwood"}) is True


def test_a_bare_outside_county_name_in_the_city_field_is_dropped():
    """PR #107 r2: a BARE outside county name in the city field — "Bexar",
    "Comal", no word "County" — matched no city and no county_in_place, so it
    returned UNKNOWN and the read path KEEPS unknowns. The city value is now read
    as a bare county name too."""
    for outside in ("Bexar", "Comal", "Guadalupe", "Bell"):
        assert row_verdict({"venue_city": outside}) is False, outside
    # A member county's name as the city value is in-market (kept):
    for inside in ("Travis", "Llano", "Bastrop"):
        assert row_verdict({"venue_city": inside}) is True, inside
    # A real city and an unrecognised one are untouched:
    assert row_verdict({"venue_city": "Austin"}) is True
    assert row_verdict({"venue_city": "Nowheresville"}) is None


def test_normalize_county_is_the_same_fact_written_four_ways():
    for shape in ("Bexar County, TX", "bexar", "BEXAR COUNTY", "Bexar County, Texas"):
        assert normalize_county(shape) == "bexar", shape
    assert normalize_county(None) is None
    assert normalize_county("   ") is None


def test_a_county_known_row_is_not_filed_as_a_MISSING_city():
    """A row decided by its county must not land in missing_city_count, which
    reads as 'nothing to see here' — it is a real in/out fact."""
    rows = [
        {"venue_county": "Travis"},                       # inside, no city
        {"county": "Bexar"},                              # outside, no city
        {"venue_city": None},                             # genuinely nothing
        {"venue_city": "", "city": "San Antonio"},        # blank-field smuggle
    ]
    r = region_report(rows)
    assert r["missing_city_count"] == 1
    assert r["inside_count"] == 1
    assert r["outside_count"] == 2
    assert r["inside_by_county"] == {"travis": 1}
    assert r["outside_by_county"] == {"bexar": 1}
    assert "travis" in r["counties_covered"]


def test_county_evidence_INSIDE_a_city_string_survives_a_state_suffix():
    """r13: the county search ran on the RAW string while _COUNTY_RE is anchored
    at the end, so ", TX" defeated the anchor and the decisive fact was dropped.
    An unlisted venue in Bexar came back UNKNOWN — which the read path KEEPS."""
    for shape in ("Unlisted Spot, Bexar County, TX",
                  "Unlisted Spot, Bexar County, TX, USA",
                  "Unlisted Spot, Bexar County, TX 78205",
                  "unlisted spot, bexar county"):
        assert county_in_place(shape) == "bexar", shape
        assert row_verdict({"venue_city": shape}) is False, shape
    # the same shape for a MEMBER county must resolve inside, not merely unknown
    assert row_verdict({"venue_city": "Nowhere Bar, Travis County, TX"}) is True
    # and a place with no county in it still reads as no county evidence
    assert county_in_place("Austin, TX") is None
    assert county_in_place(None) is None


def test_a_county_named_only_INSIDE_the_city_string_is_still_CREDITED():
    """r14: row_verdict reads county evidence from the city string, but
    region_report's credit pass read only the county FIELDS — so a row decided
    INSIDE by an embedded county credited nothing, and its county was reported
    ABSENT. A covered county in the 'no coverage here' list is the worklist
    reading backwards."""
    r = region_report([
        {"venue_city": "Nowhere Bar, Travis County, TX"},
        {"venue_city": "Unlisted Room, Llano County, TX"},
    ])
    assert r["inside_count"] == 2
    assert set(r["counties_covered"]) == {"travis", "llano"}
    assert "travis" not in r["counties_absent"]
    assert "llano" not in r["counties_absent"]
    assert len(r["counties_absent"]) == 8


def test_a_county_name_ALONE_in_the_field_is_still_county_evidence():
    """r15: _COUNTY_RE required a leading separator, so a field holding just
    "Bexar County" (or "Bexar County, TX") matched nothing, returned UNKNOWN,
    and the read path KEEPS unknowns — a Bexar row rendered to a reader.

    The guard felt safe and was not, and every vector I had written put a city
    in front of the county, so the whole test set agreed with the bug."""
    for shape in ("Bexar County", "Bexar County, TX", "bexar county",
                  "BEXAR COUNTY, TEXAS"):
        assert county_in_place(shape) == "bexar", shape
        assert row_verdict({"venue_city": shape}) is False, shape
    for shape in ("Travis County", "Travis County, TX"):
        assert row_verdict({"venue_city": shape}) is True, shape
    # and a real place is untouched
    assert row_verdict({"venue_city": "Austin"}) is True
    assert county_in_place("Columbus") is None
