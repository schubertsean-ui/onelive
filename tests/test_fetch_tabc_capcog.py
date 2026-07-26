"""TABC licensed premises — denominator layer 2 (tools/fetch_tabc_capcog.py).

Split out of test_source_scorecard.py: the TABC fetcher belongs to the CAPCOG
denominator, the scorecard does not. One test file per reviewable decision.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def test_a_network_failure_is_not_reported_as_an_empty_county():
    """evaluator nit r4: a URLError fell through as a bare traceback, leaving an
    operator to guess whether CAPCOG had no venues or the network was down."""
    import urllib.error
    import tools.fetch_tabc_capcog as tabc
    import pytest as _pytest

    def boom(url, timeout=60):
        raise urllib.error.URLError("dns go boom")

    orig = tabc._get
    tabc._get = boom
    try:
        with _pytest.raises(SystemExit) as e:
            tabc.fetch({"travis"})
        assert "NOT an empty county" in str(e.value)
    finally:
        tabc._get = orig


def test_tabc_county_is_a_numeric_CODE_not_a_name():
    """The live dataset stores `location_county` as a number (Harris = 101).
    Querying it as a name was rejected outright, and quoting the codes returns
    zero rows — which would read as 'CAPCOG has no bars'."""
    import tools.fetch_tabc_capcog as tabc
    captured = {}

    def fake_get(url, timeout=60):
        captured["url"] = url
        return []

    orig = tabc._get
    tabc._get = fake_get
    try:
        tabc.fetch({"travis"})
    finally:
        tabc._get = orig
    from urllib.parse import unquote
    where = unquote(captured["url"])
    assert "location_county in(227)" in where, where
    assert "'227'" not in where, "codes are numeric; quoting them returns nothing"


def test_a_wrong_county_code_is_CAUGHT_by_the_cities_it_returns():
    """A wrong code returns another county's bars wearing a CAPCOG label — the
    same class as the 75-mile radius. The mapping is not trusted; it is checked
    against the cities on the rows."""
    import tools.fetch_tabc_capcog as tabc
    import pytest as _pytest
    # A code pointing outside the market entirely: the cities are known-outside
    # towns, so the boundary cannot place them in ANY CAPCOG county.
    with _pytest.raises(SystemExit) as e:
        tabc.verify_counties([
            {"county": "travis", "city": "san antonio"},
            {"county": "travis", "city": "new braunfels"},
            {"county": "travis", "city": "seguin"},
        ])
    assert "does not recognise" in str(e.value)

    # A code pointing at the WRONG CAPCOG county: the cities are all real
    # CAPCOG towns, but they belong somewhere else.
    with _pytest.raises(SystemExit) as e:
        tabc.verify_counties([
            {"county": "travis", "city": "round rock"},     # williamson
            {"county": "travis", "city": "georgetown"},     # williamson
            {"county": "travis", "city": "san marcos"},     # hays
        ])
    assert "different county" in str(e.value)


def test_a_city_that_straddles_a_county_line_does_NOT_fail_the_check():
    """Austin sits mostly in Travis but reaches into Williamson and Hays, so a
    single cross-county row is geography. Failing on one row would block every
    run on correct data."""
    import tools.fetch_tabc_capcog as tabc
    rows = [{"county": "travis", "city": "austin"} for _ in range(20)]
    rows.append({"county": "travis", "city": "round rock"})   # Williamson
    stats = tabc.verify_counties(rows)
    assert stats["travis"]["rows"] == 21


def test_monthly_receipt_rows_collapse_to_one_row_per_premise():
    """The dataset is MONTHLY receipts, so a still-trading bar appears dozens of
    times. Counting rows would multiply the denominator by the number of months
    reported and make coverage look far worse than it is."""
    import tools.fetch_tabc_capcog as tabc
    import tempfile
    months = [{"location_name": "MOHAWK", "location_address": "912 RED RIVER ST",
               "location_city": "AUSTIN", "location_county": "227",
               "obligation_end_date_yyyymmdd": "2026-0%d-31T00:00:00.000" % m}
              for m in range(1, 7)]

    orig = tabc._get
    tabc._get = lambda url, timeout=60: months if "offset=0" in url.lower() else []
    try:
        with tempfile.NamedTemporaryFile(suffix=".json") as fh:
            tabc.main(["--out", fh.name, "--active-since", "2020-01-01"])
            written = json.loads(pathlib.Path(fh.name).read_text())
    finally:
        tabc._get = orig
    assert len(written) == 1, f"6 monthly rows must collapse to 1 premise: {written}"


def test_two_branches_of_a_chain_are_TWO_venues_not_one():
    """Grouping on name+city alone merged every branch of a chain into one row.

    Two rooms at two addresses are two places a person can go to. Merging them
    SHRINKS the denominator, which RAISES the coverage percentage — the error
    flattered us, so nothing would have announced it. The address is what makes
    a premise distinct.
    """
    import tools.fetch_tabc_capcog as tabc
    import tempfile
    rows = [
        {"location_name": "TORCHY'S TACOS", "location_address": "2809 S 1ST ST",
         "location_city": "AUSTIN", "location_county": "227",
         "obligation_end_date_yyyymmdd": "2026-06-30T00:00:00.000"},
        {"location_name": "TORCHY'S TACOS", "location_address": "1801 N LAMAR BLVD",
         "location_city": "AUSTIN", "location_county": "227",
         "obligation_end_date_yyyymmdd": "2026-06-30T00:00:00.000"},
    ]
    orig = tabc._get
    tabc._get = lambda url, timeout=60: rows if "offset=0" in url.lower() else []
    try:
        with tempfile.NamedTemporaryFile(suffix=".json") as fh:
            tabc.main(["--out", fh.name, "--active-since", "2020-01-01"])
            written = json.loads(pathlib.Path(fh.name).read_text())
    finally:
        tabc._get = orig
    assert len(written) == 2, (
        f"two addresses are two venues; merging them undercounts the market "
        f"and inflates coverage: {written}")


def test_the_tabc_query_groups_by_ADDRESS_not_just_name_and_city():
    """The server-side grouping is where the collapse actually happened, so the
    local dedupe fix alone would not have been enough."""
    import tools.fetch_tabc_capcog as tabc
    from urllib.parse import unquote
    captured = {}

    def fake_get(url, timeout=60):
        captured["url"] = url
        return []

    orig = tabc._get
    tabc._get = fake_get
    try:
        tabc.fetch({"travis"})
    finally:
        tabc._get = orig
    assert "location_address" in unquote(captured["url"]), unquote(captured["url"])


# ---- r1 evaluator findings: a short denominator must never be silent --------

def _stub_batches(monkeypatch, batches):
    import tools.fetch_tabc_capcog as tabc
    calls = iter(batches)
    monkeypatch.setattr(tabc, "_get", lambda url: next(calls, []))
    return tabc


def test_a_row_MISSING_its_identity_fields_is_reported_not_dropped(monkeypatch):
    """Address is the premise identity key — a blank one MERGES distinct
    branches of a chain into one venue. City carries the evidence the county
    codes are verified against. Silently skipping either makes the denominator
    short in the flattering direction, which is the class this whole tool
    exists to avoid."""
    tabc = _stub_batches(monkeypatch, [[
        {"location_name": "Good Bar", "location_address": "1 Main",
         "location_city": "Austin", "location_county": "227"},
        {"location_name": "", "location_address": "2 Main",
         "location_city": "Austin", "location_county": "227"},
        {"location_name": "No Address", "location_address": "",
         "location_city": "Austin", "location_county": "227"},
        {"location_name": "No City", "location_address": "3 Main",
         "location_city": "", "location_county": "227"},
        {"location_name": "Bad County", "location_address": "4 Main",
         "location_city": "Austin", "location_county": "not-a-number"},
    ], []])
    rows, _pages, _seen, malformed = tabc.fetch({"travis"}, 5, None)
    assert [r["name"] for r in rows] == ["Good Bar"]
    assert len(malformed) == 4, malformed
    whys = " ".join(m["why"] for m in malformed)
    assert "name" in whys and "address" in whys and "city" in whys
    assert "county" in whys
    # each rejection carries enough to find the row upstream
    assert all(m["row"] for m in malformed)


def test_a_TRUNCATED_run_writes_no_artifact_at_all(monkeypatch, tmp_path):
    """The exit code protected the caller, never the FILE. A known-truncated
    run still left a short, entirely plausible denominator on disk — and the
    coverage tool reads the file, not the exit code."""
    import tools.fetch_tabc_capcog as tabc
    monkeypatch.setattr(tabc, "fetch",
                        lambda *a, **k: ([{"name": "X", "address": "1",
                                           "city": "austin", "county": "travis",
                                           "source_layer": "tabc"}],
                                         99, 99, []))
    out = tmp_path / "raw.json"
    assert tabc.main(["--out", str(out), "--max-pages", "99"]) == 1
    assert not out.exists(), (
        "a truncated run must leave NO file — a plausible short denominator on "
        "disk is worse than none, because the next tool reads it")


def test_a_malformed_active_since_fails_BEFORE_the_network(monkeypatch):
    """A bad date otherwise spends a minute fetching and then filters
    everything out, which reads as an empty county rather than a typo."""
    import tools.fetch_tabc_capcog as tabc

    def explode(*a, **k):
        raise AssertionError("the network must not be touched")

    monkeypatch.setattr(tabc, "_get", explode)
    monkeypatch.setattr(tabc, "fetch", explode)
    assert tabc.main(["--active-since", "last-tuesday"]) == 2
    assert tabc.main(["--active-since", "2026-13-45"]) == 2
