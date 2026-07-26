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


# ---- the denominator builder -------------------------------------------------

def test_targets_never_get_an_invented_county():
    """A venue whose county cannot be read off the row is listed as UNRESOLVED,
    not assigned a plausible one. Inventing 'travis' would inflate Travis and
    hide a gap in the county the venue is actually in."""
    import tools.build_capcog_targets as bt
    targets, unresolved = bt.from_catalog([
        {"category": "venue_calendar", "name": "Mohawk Austin"},          # name says Austin
        {"category": "venue_calendar", "name": "Cheatham Street",
         "county": "hays"},                                               # county field
        {"category": "venue_calendar", "name": "The Saxon Pub"},          # says nothing
    ])
    by_name = {t["name"]: t for t in targets}
    assert by_name["Mohawk Austin"]["county"] == "travis"
    assert by_name["Mohawk Austin"]["county_resolved_by"] == "name_text"
    assert by_name["Cheatham Street"]["county"] == "hays"
    assert [u["name"] for u in unresolved] == ["The Saxon Pub"]


def test_name_matching_needs_a_word_boundary():
    """'Austintatious' is not Austin. A substring match would silently place
    venues in the wrong county."""
    import tools.build_capcog_targets as bt
    _, unresolved = bt.from_catalog(
        [{"category": "venue_calendar", "name": "Austintatious Balloons"}])
    assert len(unresolved) == 1


def test_channels_are_not_counted_as_venues():
    """Ticketing aggregators and social accounts have no address; counting them
    would inflate the denominator with things nobody can attend."""
    import tools.build_capcog_targets as bt
    targets, unresolved = bt.from_catalog([
        {"category": "ticketing", "name": "Ticketmaster", "county": "travis"},
        {"category": "social", "name": "Some IG Account", "county": "travis"},
    ])
    assert targets == [] and unresolved == []


def test_a_festival_or_a_city_calendar_is_not_a_VENUE_in_the_denominator():
    """The launch metric is "X of Y CAPCOG VENUES".

    Every admitted category used to count as a venue, so "Visit Austin Events"
    (a city calendar), "Fusebox Festival" (an annual event) and "Austin Symphony
    Orchestra" (a company performing in halls it does not own) each added 1 to
    the denominator. None is a place that can be covered, so the percentage was
    structurally false. They are LABELLED, not dropped.
    """
    import tools.build_capcog_targets as bt
    targets, _ = bt.from_catalog([
        {"id": "mohawk_austin", "category": "venue_calendar",
         "name": "Mohawk Austin", "county": "travis"},
        {"id": "visit_austin", "category": "city_calendar",
         "name": "Visit Austin Events", "county": "travis"},
        {"id": "fusebox_festival", "category": "festival_feed",
         "name": "Fusebox Festival", "county": "travis"},
        {"id": "austin_symphony", "category": "venue_calendar",
         "name": "Austin Symphony Orchestra", "county": "travis"},
        {"id": "ut_austin_localist", "category": "university_calendar",
         "name": "UT Austin Events Calendar", "county": "travis"},
    ])
    kinds = {t["catalog_id"]: t["target_kind"] for t in targets}
    assert kinds == {
        "mohawk_austin": bt.KIND_VENUE,
        "visit_austin": bt.KIND_CHANNEL,
        "fusebox_festival": bt.KIND_FESTIVAL,
        "austin_symphony": bt.KIND_PRODUCER,
        "ut_austin_localist": bt.KIND_CHANNEL,
    }
    # kept, never silently discarded — a dropped row is an invisible change to
    # the denominator, and shrinking it RAISES the coverage percentage
    assert len(targets) == 5


def test_the_coverage_report_divides_by_venues_only_and_says_so():
    import tools.capcog_coverage as cc
    import tempfile
    doc = {"venues": [
        {"name": "Mohawk", "county": "travis", "target_kind": "venue"},
        {"name": "Fusebox Festival", "county": "travis", "target_kind": "festival"},
        {"name": "Visit Austin", "county": "travis", "target_kind": "channel"},
    ]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(doc, fh)
        path = pathlib.Path(fh.name)
    venues, meta = cc.load_targets(path)
    assert [v["name"] for v in venues] == ["Mohawk"]
    assert meta["non_venue_targets_excluded"] == 2
    assert meta["non_venue_by_kind"] == {"channel": 1, "festival": 1}


def test_a_target_list_without_kinds_is_still_all_venues():
    """Defaulting the other way would silently delete the denominator when run
    against a target file generated before the field existed."""
    import tools.capcog_coverage as cc
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"venues": [{"name": "Mohawk", "county": "travis"}]}, fh)
        path = pathlib.Path(fh.name)
    venues, meta = cc.load_targets(path)
    assert len(venues) == 1
    assert meta["non_venue_targets_excluded"] == 0


def test_a_stale_kind_override_FAILS_rather_than_reverting_silently():
    """A stale override stops applying and the row falls back to its category
    default — a festival counted as a venue again, with nothing to notice."""
    import tools.build_capcog_targets as bt
    original = bt.KIND_OVERRIDE
    bt.KIND_OVERRIDE = {"an_id_the_catalog_does_not_have": bt.KIND_FESTIVAL}
    try:
        with pytest.raises(SystemExit):
            bt.assert_overrides_are_live(
                [{"id": "mohawk_austin", "category": "venue_calendar"}])
    finally:
        bt.KIND_OVERRIDE = original


def test_every_kind_override_still_names_a_real_catalog_row():
    """The guard, run against the catalog that actually ships."""
    import tools.build_capcog_targets as bt
    catalog = json.loads(bt.CATALOG.read_text(encoding="utf-8"))
    if isinstance(catalog, dict):
        catalog = catalog.get("sources") or catalog.get("catalog")
    live_ids = {r.get("id") for r in catalog}
    assert set(bt.KIND_OVERRIDE) <= live_ids, (
        f"KIND_OVERRIDE names ids the catalog no longer has: "
        f"{sorted(set(bt.KIND_OVERRIDE) - live_ids)}")
    bt.assert_overrides_are_live(catalog)


# ---- the false-zero-coverage defect (Gemini seat, spec-vs-contract) ----------

def test_a_cityless_target_still_matches_an_ingested_row_with_a_city():
    """THE defect. 61 of 69 targets carry no city (the catalog states a county),
    so an exact name|city key computed 'name|' for the target and 'name|austin'
    for the ingested row — every one missed and coverage read ~0%. A measurement
    tool that under-reports to zero is worse than no tool: it would have had me
    report that we cover nothing."""
    import tools.capcog_coverage as cc
    rows = [{"venue_name": "Mohawk", "venue_city": "Austin"}]
    targets = [{"name": "Mohawk", "city": None, "county": "travis"}]
    out = cc.coverage(rows, targets)
    assert out["covered_venue_count"] == 1
    assert out["coverage_pct"] == 100.0


def test_city_still_separates_same_named_venues_when_both_state_one():
    """City remains a real discriminator where the data supports it."""
    import tools.capcog_coverage as cc
    rows = [{"venue_name": "The Grand", "venue_city": "Austin"}]
    targets = [{"name": "The Grand", "city": "Llano", "county": "llano"}]
    assert cc.coverage(rows, targets)["covered_venue_count"] == 0


def test_the_county_disambiguates_a_cityless_target_across_towns():
    """r3 sharpened this: a Travis target matching same-named rooms in Austin
    AND Llano is no longer 'ambiguous' — the county settles it. Only the Austin
    row counts."""
    import tools.capcog_coverage as cc
    rows = [{"venue_name": "The Grand", "venue_city": "Austin"},
            {"venue_name": "The Grand", "venue_city": "Llano"}]
    targets = [{"name": "The Grand", "city": None, "county": "travis"}]
    out = cc.coverage(rows, targets)
    assert out["covered_venue_count"] == 1
    assert out["ambiguous_matches"] == []


def test_a_cityless_target_is_NOT_covered_by_a_venue_in_another_county():
    """THE r3 blocker, and it is a defect I introduced fixing r1. Making the
    match name-first stopped 61 city-less targets reading as misses — and let a
    name match cross county lines, OVERSTATING coverage. Under-reporting and
    over-reporting are the same defect pointed opposite ways."""
    import tools.capcog_coverage as cc
    rows = [{"venue_name": "The Parish", "venue_city": "Llano"}]
    targets = [{"name": "The Parish", "city": None, "county": "travis"}]
    assert cc.coverage(rows, targets)["covered_venue_count"] == 0


def test_a_cityless_target_is_NOT_covered_by_an_out_of_market_venue():
    import tools.capcog_coverage as cc
    rows = [{"venue_name": "Majestic Theatre", "venue_city": "San Antonio"}]
    targets = [{"name": "Majestic Theatre", "city": None, "county": "travis"}]
    assert cc.coverage(rows, targets)["covered_venue_count"] == 0


def test_two_towns_in_the_SAME_county_are_still_ambiguous():
    """Where the county cannot settle it, we still refuse to pick."""
    import tools.capcog_coverage as cc
    rows = [{"venue_name": "The Grand", "venue_city": "Austin"},
            {"venue_name": "The Grand", "venue_city": "Pflugerville"}]
    targets = [{"name": "The Grand", "city": None, "county": "travis"}]
    assert cc.coverage(rows, targets)["ambiguous_matches"] == ["The Grand"]


def test_malformed_target_rows_are_excluded_AND_reported():
    """A corrupt denominator row is corrupt input, not a smaller market.
    Silently skipping it shrank the denominator and inflated the percentage."""
    import tools.capcog_coverage as cc
    targets = [
        {"name": "Mohawk", "city": "Austin", "county": "travis"},
        {"name": "", "county": "travis"},                       # nameless
        {"name": "Majestic", "city": "San Antonio", "county": "bexar"},  # not CAPCOG
    ]
    out = cc.coverage([{"venue_name": "Mohawk", "venue_city": "Austin"}], targets)
    assert out["target_venue_count"] == 1
    assert len(out["malformed_target_rows"]) == 2


def test_merge_keeps_same_named_venues_in_different_counties():
    """r3: keying the merge on name alone let a city-less Travis entry absorb a
    genuinely different same-named venue in Llano — undercounting."""
    import tools.build_capcog_targets as bt
    existing = [{"name": "The Grand", "city": None, "county": "travis"}]
    incoming = [{"name": "The Grand", "city": "llano", "county": "llano"}]
    assert len(bt.merge(existing, incoming)) == 2


def test_layers_dedupe_a_cityless_catalog_venue_against_a_cited_import():
    """A city-less layer-1 venue must absorb the same venue arriving from TABC
    with a city, or the denominator double-counts it."""
    import tools.build_capcog_targets as bt
    existing = [{"name": "Mohawk", "city": None, "county": "travis"}]
    incoming = [{"name": "Mohawk", "city": "austin", "county": "travis"}]
    assert len(bt.merge(existing, incoming)) == 1


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
