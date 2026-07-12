"""Tests for tools/coverage_report.py — coverage blindness must be measurable
and honest: empty cells surfaced, debt surfaced, UNVERIFIED never rendered as
zero-coverage.
"""
import json

import pytest

from tools.coverage_report import (
    CATEGORIES,
    COUNTIES,
    METRO_WIDE,
    compute_coverage,
    from_json,
    format_report,
)


def _src(name, county, cats):
    return {"name": name, "county": county, "coverage_categories": cats}


def test_empty_input_reports_all_cells_empty_but_verified():
    res = compute_coverage([])
    assert res.verified is True
    assert res.source_count == 0
    # every county (+metro-wide) x every category is an empty cell
    expected_cells = (len(COUNTIES) + 1) * len(CATEGORIES)
    assert len(res.empty_cells) == expected_cells


def test_single_source_populates_one_cell_and_clears_it():
    res = compute_coverage([_src("Mohawk", "travis", ["music"])])
    assert res.source_count == 1
    assert res.grid["travis"]["music"] == 1
    assert res.county_totals["travis"] == 1
    assert res.category_totals["music"] == 1
    assert ("travis", "music") not in res.empty_cells
    # a different cell is still empty
    assert ("hays", "music") in res.empty_cells


def test_multi_category_source_counts_each_category():
    res = compute_coverage([_src("Long Center", "travis", ["theater", "music", "dance"])])
    assert res.grid["travis"]["theater"] == 1
    assert res.grid["travis"]["music"] == 1
    assert res.grid["travis"]["dance"] == 1
    assert res.category_totals["theater"] == 1


def test_null_county_goes_to_metro_wide_row_not_a_real_county():
    res = compute_coverage([_src("Bandsintown", None, ["music"])])
    assert res.county_totals[METRO_WIDE] == 1
    # not attributed to any real county
    for c in COUNTIES:
        assert res.county_totals[c] == 0


def test_uncategorized_source_is_flagged_as_debt():
    res = compute_coverage([_src("Mystery Feed", "travis", [])])
    assert "Mystery Feed" in res.uncategorized
    # counted in county total (it exists) but adds to no category
    assert res.county_totals["travis"] == 1
    assert sum(res.category_totals.values()) == 0


def test_unknown_category_surfaced_not_silently_added_as_column():
    res = compute_coverage([_src("Weird", "travis", ["music", "sportsball"])])
    # valid category counted
    assert res.grid["travis"]["music"] == 1
    # invalid category surfaced as debt, and no phantom column created
    assert "sportsball" not in CATEGORIES
    assert any("sportsball" in u for u in res.uncategorized)


def test_out_of_domain_county_surfaced_loud_not_dropped():
    res = compute_coverage([_src("Dallas Venue", "dallas", ["music"])])
    assert any("Dallas Venue" in u for u in res.unknown_county)
    # its source count is still reflected (not silently dropped)
    assert res.source_count == 1


def test_from_json_roundtrip(tmp_path):
    catalog = [
        _src("Mohawk", "travis", ["music"]),
        _src("Georgetown Palace", "williamson", ["theater"]),
    ]
    p = tmp_path / "cat.json"
    p.write_text(json.dumps(catalog), encoding="utf-8")
    res = from_json(p)
    assert res.verified is True
    assert res.source_count == 2
    assert res.grid["williamson"]["theater"] == 1


def test_from_json_missing_file_is_unverified_not_empty():
    res = from_json("/nonexistent/path/catalog.json")
    assert res.verified is False
    assert "not found" in res.reason
    # crucial: an unreadable catalog is UNVERIFIED, never rendered as zero coverage
    assert "UNVERIFIED" in format_report(res)


def test_from_json_non_array_is_unverified(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"not": "an array"}', encoding="utf-8")
    res = from_json(p)
    assert res.verified is False
    assert "array" in res.reason


def test_from_json_invalid_json_is_unverified(tmp_path):
    p = tmp_path / "broken.json"
    p.write_text("{not valid json", encoding="utf-8")
    res = from_json(p)
    assert res.verified is False
    assert "invalid JSON" in res.reason


def test_format_report_shows_every_county_row_including_empty():
    res = compute_coverage([_src("Mohawk", "travis", ["music"])])
    report = format_report(res)
    # every county must appear as a row even with zero coverage
    for county in COUNTIES:
        assert county in report
    assert METRO_WIDE in report
    assert "empty cells" in report
