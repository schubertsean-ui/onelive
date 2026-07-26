"""The denominator, and coverage measured against it.

The launch metric was scored against whatever we had already ingested, which
makes 100% coverage of nothing look like success. These tests pin the two
halves of the fix: `build_capcog_targets` turns a source catalog into a venue
denominator without inventing counties or counting non-venues, and
`capcog_coverage` refuses to print a percentage it cannot honestly compute.

Split out of tests/test_capcog_region.py, which had grown to hold boundary
tests, denominator tests and coverage tests in one file.
"""
import json
import pathlib

import pytest

from worker.region.capcog import CAPCOG_COUNTIES


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


def test_a_corrupt_denominator_EXITS_NON_ZERO_and_prints_no_percentage(capsys):
    """Reporting corrupt rows and then printing the percentage anyway was the
    swallowed-corrupt-data class: the caveat stays in the log, the number
    travels everywhere else, and the number outlives its warning.

    A share of a corrupt market is not a measurement, so the tool must refuse
    to state one and must fail — otherwise the workflow uploads a coverage
    artifact built on a denominator it already knows is broken.
    """
    import tools.capcog_coverage as cc
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        rows = pathlib.Path(d) / "rows.json"
        targets = pathlib.Path(d) / "targets.json"
        rows.write_text(json.dumps(
            [{"venue_name": "Mohawk", "venue_city": "austin"}]), encoding="utf-8")
        targets.write_text(json.dumps({"venues": [
            {"name": "Mohawk", "county": "travis", "target_kind": "venue"},
            {"name": "", "county": "travis", "target_kind": "venue"},
        ]}), encoding="utf-8")
        code = cc.main(["--rows", str(rows), "--targets", str(targets)])
    out = capsys.readouterr()
    assert code != 0, "a corrupt denominator must fail the run, not warn"
    assert "PERCENTAGE SUPPRESSED" in out.out
    assert "%)" not in out.out, "no percentage may be printed from corrupt input"


def test_one_ingested_row_cannot_cover_MANY_same_named_premises():
    """Correcting TABC to count premises by ADDRESS made the denominator
    premise-accurate — two Torchy's are two venues — while the matcher still
    keyed on name. A single ingested "Torchy's / Austin" row would then satisfy
    every Torchy's target in the county: a fix to one side of a ratio silently
    overstating the other. Coverage cannot exceed what we actually hold."""
    import tools.capcog_coverage as cc
    idx = cc.index_by_name([{"venue_name": "Torchy's", "venue_city": "austin"}])
    targets = [{"name": "Torchy's", "county": "travis", "city": "austin",
                "target_kind": "venue"} for _ in range(4)]
    cov = cc.coverage([{"venue_name": "Torchy's", "venue_city": "austin"}], targets)
    assert cov["covered_venue_count"] == 1, (
        f"one ingested venue may cover one premise, not four: {cov}")
    assert cov["target_venue_count"] == 4
    assert idx  # the index itself is unchanged; the CAP is what is new


def test_an_ambiguous_match_is_NOT_counted_as_covered():
    """Naming the ambiguity in the report while still incrementing `covered`
    meant the percentage already contained the matches we said we would never
    resolve silently. The caveat travelled in prose; the number travelled
    everywhere."""
    import tools.capcog_coverage as cc
    rows = [
        {"venue_name": "The Tavern", "venue_city": "austin"},
        {"venue_name": "The Tavern", "venue_city": "pflugerville"},
    ]
    targets = [{"name": "The Tavern", "county": "travis", "target_kind": "venue"}]
    cov = cc.coverage(rows, targets)
    assert cov["ambiguous_matches"] == ["The Tavern"]
    assert cov["covered_venue_count"] == 0, (
        f"an ambiguous match must not inflate coverage: {cov}")


def test_the_committed_target_file_declares_itself_a_floor_not_the_market():
    """The committed artifact is catalog-only — the sandbox cannot fetch TABC —
    so its per-county zeros sit in the repo looking like findings about those
    counties while the docs quote the measured 2,873. It has to say so in its
    own first field, not rely on a reader knowing."""
    doc = json.loads((pathlib.Path(__file__).resolve().parent.parent
                      / "sources" / "capcog_venue_targets.json"
                      ).read_text(encoding="utf-8"))
    banner = doc.get("_READ_THIS_FIRST", "")
    assert banner, "the committed denominator states nothing about its own scope"
    if set(doc.get("layers_present", [])) == {"catalog"}:
        assert "CATALOG-ONLY FLOOR" in banner
        assert "NOT counties without venues" in banner


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




# ---- r1 evaluator findings ---------------------------------------------------

def test_layers_2_and_3_are_held_to_the_SAME_shape_as_layer_1(
        tmp_path, capsys, monkeypatch):
    """Layer 1 strips names and refuses blank ones; layers 2 and 3 took
    r.get("name") RAW. A nameless import went into the denominator, and the
    coverage tool then read the target file as corrupt and refused to run — a
    defect in the builder surfacing as a failure two tools downstream."""
    import json
    import tools.build_capcog_targets as bt
    # The stale-override guard is a different rule with its own test; an empty
    # catalog would trip it and mask what this test is actually pinning.
    monkeypatch.setattr(bt, "KIND_OVERRIDE", {})
    src = tmp_path / "tabc.json"
    src.write_text(json.dumps([
        {"name": "  Mohawk  ", "city": "Austin", "county": "travis"},
        {"name": "", "city": "Austin", "county": "travis"},
        {"name": None, "city": "Austin", "county": "travis"},
        None,
        {"name": "Cheatham", "city": "San Marcos", "county": "hays"},
    ]), encoding="utf-8")
    cat = tmp_path / "cat.json"
    cat.write_text(json.dumps([]), encoding="utf-8")
    out = tmp_path / "targets.json"
    assert bt.main(["--catalog", str(cat), "--tabc", str(src),
                    "--out", str(out)]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    names = sorted(t["name"] for t in doc["venues"])
    assert names == ["Cheatham", "Mohawk"], names   # stripped, blanks dropped
    printed = capsys.readouterr().out
    assert "EXCLUDED and named" in printed
    assert "no name" in printed and "not an object" in printed


def test_an_unreadable_NUMERATOR_fails_the_same_way_as_the_denominator(tmp_path):
    """One input raising a bare JSONDecodeError while the other prints a
    structured refusal makes one look like a crash and the other a decision."""
    import pytest as _pytest
    import tools.capcog_coverage as cc
    bad = tmp_path / "rows.json"
    bad.write_text("{not json", encoding="utf-8")
    with _pytest.raises(SystemExit, match="could not be read as JSON"):
        cc.load_rows(str(bad))
    notalist = tmp_path / "rows2.json"
    notalist.write_text('{"a": 1}', encoding="utf-8")
    with _pytest.raises(SystemExit, match="not a list"):
        cc.load_rows(str(notalist))


def test_NO_numerator_suppresses_EVERY_numerator_derived_output(tmp_path, capsys):
    """r3 blocker, and the shape is the one worth remembering: r1 guarded
    coverage() and left its SIBLINGS printing zeros from `rows or []`.

    "inside CAPCOG: 0", "counties covered: NONE" and an ingested-venue count
    are real-looking facts about data the run never read — printed on the very
    path that exists BECAUSE it cannot read it. Guarding one output and leaving
    the others is how a fix looks complete and is not."""
    import json
    import tools.capcog_coverage as cc
    targets = tmp_path / "t.json"
    targets.write_text(json.dumps({"venues": [
        {"name": "Mohawk", "city": "Austin", "county": "travis"}]}),
        encoding="utf-8")
    assert cc.main(["--targets", str(targets)]) == 0
    out = capsys.readouterr().out
    assert "NOT MEASURED" in out
    assert "DENOMINATOR ONLY" in out
    for zero_claim in ("inside CAPCOG : 0", "OUTSIDE CAPCOG: 0",
                       "counties covered: NONE", "unknown place : 0"):
        assert zero_claim not in out, (
            f"{zero_claim!r} is a fact about data this run never read")


def test_no_numerator_AND_no_denominator_measured_nothing(tmp_path, capsys):
    """With neither, the honest report is that the run measured nothing — not
    an ingested count of zero."""
    import tools.capcog_coverage as cc
    assert cc.main(["--targets", str(tmp_path / "absent.json")]) == 2
    out = capsys.readouterr().out
    assert "measured nothing at all" in out
    assert "0 distinct venue" not in out
