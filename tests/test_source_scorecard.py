"""The source registry + scorecard: every source, its status, and its trend.

Founder directive 2026-07-26: an extensive list of every source identified
across the build, portable to any locale, scored on tried/working/remediation/
volume with improvements tracked over time as an ongoing measure.
"""
import json
import pathlib
import re

import pytest

import tools.build_source_registry as reg
import tools.source_scorecard as sc
from worker.sources.taxonomy import (
    EVENT_CLASSES,
    SOURCE_CLASSES,
    VENUE_CLASSES,
    portability_checklist,
)

REPO = pathlib.Path(__file__).resolve().parent.parent


# ---- the taxonomy is the portable half ---------------------------------------

def test_every_class_declares_what_it_provides_and_how_it_fails():
    for name, meta in SOURCE_CLASSES.items():
        assert meta["provides"] in {"EVENTS", "VENUES", "IDENTITY", "SIGNAL"}, name
        assert meta["trust"] in {"FIRST_PARTY", "LICENSED", "AGGREGATE", "USER"}, name
        # A class with no known failure modes is a class nobody has run.
        assert meta["known_failure_modes"], name
        # Portability: the whole point is that a new metro can be asked this.
        assert meta["portable_prompt"], name


def test_venue_sources_are_not_counted_as_event_sources():
    """A liquor-licence dataset and a places API enumerate PLACES; counting them
    as event feeds is how a coverage number gets inflated by rows with no date."""
    assert "alcohol_licensing" in VENUE_CLASSES
    assert "places_api" in VENUE_CLASSES
    assert not (EVENT_CLASSES & VENUE_CLASSES)
    assert "search_benchmark" not in EVENT_CLASSES   # measurement, never ingested
    assert "artist_identity" not in EVENT_CLASSES    # a spine, not a calendar


def test_the_portability_checklist_leads_with_events_then_venues():
    order = [c["provides"] for c in portability_checklist()]
    assert order[0] == "EVENTS"
    assert order.index("VENUES") > 0
    assert len(portability_checklist()) == len(SOURCE_CLASSES)


# ---- the registry must not lose sources --------------------------------------

def test_an_unmapped_catalog_category_FAILS_rather_than_vanishing():
    """A source dropped from the registry disappears from the scorecard, and a
    source you cannot see is worse than one you know is broken."""
    with pytest.raises(SystemExit):
        reg.build([{"id": "x", "name": "X", "category": "a_brand_new_category"}])


def _catalog_with_merge_targets(*extra_rows) -> list:
    """A minimal catalog carrying every id CODE_AND_DECISION_SOURCES merges onto.

    build() fails closed when a merge target is missing — that guard is the
    point — so tests must supply the targets rather than pass an empty list.
    Derived from the merge table itself, so adding a merge entry cannot leave
    the tests silently exercising a shape the real build no longer has.
    """
    rows = [{"id": e["merge_into"], "name": e["merge_into"],
             "category": "ticketing"}
            for e in reg.CODE_AND_DECISION_SOURCES if e.get("merge_into")]
    return rows + list(extra_rows)


def test_the_registry_carries_sources_that_were_never_catalog_rows():
    """TABC and the open-data portal live in code or in a founder decision and
    were never catalog rows. A catalog-only list is how 'extensive' quietly
    becomes 'the ones we already wrote down'."""
    built = reg.build(_catalog_with_merge_targets())
    ids = {s["id"] for s in built}
    for expected in ("tabc_licensed_premises", "city_open_data"):
        assert expected in ids, expected
    for s in built:
        assert s.get("remediation"), s["id"]


def test_a_source_that_is_already_catalogued_MERGES_instead_of_duplicating():
    """The scorecard attributes evidence by id. A source present under two ids
    shows its real throughput on one row and a permanent zero on the twin — a
    live feed rendered half-dead. This shipped, briefly: Ticketmaster appeared
    as both `ticketmaster_discovery` and `ticketmaster_api`, and Eventbrite
    appeared TWICE under the same id."""
    built = reg.build([
        {"id": "ticketmaster_discovery", "name": "Ticketmaster Discovery API",
         "category": "ticketing"},
        {"id": "eventbrite_api", "name": "Eventbrite API", "category": "ticketing"},
        {"id": "seatgeek", "name": "SeatGeek", "category": "ticketing"},
        {"id": "google_places", "name": "Google Places", "category": "directory"},
        {"id": "email_opt_in", "name": "Opt-in Email", "category": "email_opt_in"},
    ])
    ids = [s["id"] for s in built]
    assert len(ids) == len(set(ids)), f"duplicate ids: {ids}"
    names = [(s.get("name") or "").lower() for s in built]
    assert len(names) == len(set(names)), f"duplicate names: {names}"
    # the merge carries the code path's knowledge onto the ONE surviving row
    tm = next(s for s in built if s["id"] == "ticketmaster_discovery")
    assert tm["evidence"] == "worker/importers/ticketmaster.py"
    assert tm["origin"] == "catalog+code_or_decision"
    assert tm["code_id"] == "ticketmaster_api"
    # and Places is scored as what the code actually uses it for
    assert next(s for s in built
                if s["id"] == "google_places")["source_class"] == "places_api"


def test_a_stale_merge_target_FAILS_rather_than_silently_appending():
    """A merge_into pointing at an id the catalog no longer has would fall back
    to an append — reintroducing the very duplicate the merge prevents."""
    original = reg.CODE_AND_DECISION_SOURCES
    reg.CODE_AND_DECISION_SOURCES = [
        {"id": "x_api", "merge_into": "an_id_the_catalog_does_not_have",
         "name": "X", "source_class": "ticketing_api", "needs_credential": True,
         "evidence": "e", "remediation": "r"}]
    try:
        with pytest.raises(SystemExit):
            reg.build([{"id": "unrelated", "name": "U", "category": "ticketing"}])
    finally:
        reg.CODE_AND_DECISION_SOURCES = original


def test_a_catalog_that_repeats_an_id_FAILS():
    with pytest.raises(SystemExit):
        reg.build([{"id": "dup", "name": "A", "category": "ticketing"},
                   {"id": "dup", "name": "B", "category": "ticketing"}])


def test_STATE_does_not_claim_a_source_count_the_artifact_contradicts():
    """`false-confidence-gate`: STATE.md said "123 sources across 20 classes"
    while the generated registry said 118 and 19. A founder-facing inventory
    that overstates itself is launch evidence that cannot be trusted, and the
    only durable fix is to bind the prose claim to the machine artifact."""
    live = json.loads(
        (REPO / "sources" / "source_registry.json").read_text(encoding="utf-8"))
    state = (REPO / "STATE.md").read_text(encoding="utf-8")
    claims = re.findall(r"(\d+)\s+sources?\s+across\s+(\d+)\s+class", state)
    assert claims, "STATE.md no longer states a source/class count — update this test"
    for sources, classes in claims:
        assert int(sources) == live["source_count"], (
            f"STATE.md claims {sources} sources; the registry has "
            f"{live['source_count']}")
        assert int(classes) == live["class_count"], (
            f"STATE.md claims {classes} classes; the registry has "
            f"{live['class_count']}")


def test_every_registry_row_binds_to_a_real_taxonomy_class():
    built = reg.build(_catalog_with_merge_targets(
        {"id": "v", "name": "V", "category": "venue_calendar"}))
    for s in built:
        assert s["source_class"] in SOURCE_CLASSES, s


# ---- the scorecard -----------------------------------------------------------

ENTRY = {"id": "s1", "name": "S1", "source_class": "venue_calendar"}


def _score(entry, rows, attempts, evidence=True):
    ev, ven, owners = sc._index_rows(rows)
    att = sc._index_attempts(attempts)
    return sc.score_source(entry, ev, ven, owners, att, evidence)


def test_no_evidence_is_UNKNOWN_not_broken():
    """'We have not measured this' and 'this is broken' are different facts with
    different remediations, and collapsing them is how a working source gets
    retired."""
    out = _score(ENTRY, [], [], evidence=False)
    assert out["status"] == sc.STATUS_UNKNOWN
    assert out["tried"] is None and out["working"] is None
    assert "No evidence" in out["remediation"]


def test_never_tried_is_distinguished_from_tried_and_failing():
    never = _score(ENTRY, [], [])
    assert never["status"] == sc.STATUS_NEVER_TRIED
    failing = _score(ENTRY, [], [{"source_name": "s1", "ok": False}])
    assert failing["status"] == sc.STATUS_TRIED_FAILING
    empty = _score(ENTRY, [], [{"source_name": "s1", "ok": True}])
    assert empty["status"] == sc.STATUS_TRIED_EMPTY


def test_a_missing_credential_is_its_own_status_with_a_founder_action():
    out = _score({**ENTRY, "needs_credential": True, "credential_present": False},
                 [], [])
    assert out["status"] == sc.STATUS_BLOCKED_CREDENTIAL
    assert "mints" in out["remediation"]


def test_delivered_rows_OUTRANK_any_assumption_about_the_credential():
    """A credentialed source with rows in the store is WORKING, full stop.

    Nothing populates `credential_present`, so it is None for every source. The
    status ladder used to test the credential FIRST and `not None` is true, so
    every credentialed source — Ticketmaster included, with live rows — scored
    BLOCKED_CREDENTIAL and was handed a 'mint the key' action for a key that
    already works.
    """
    entry = {**ENTRY, "needs_credential": True, "credential_present": None}
    out = _score(entry, [{"source_name": "s1", "venue_name": "Mohawk"}],
                 [{"source_name": "s1", "ok": True}])
    assert out["status"] == sc.STATUS_WORKING
    assert out["remediation"] == ""


def test_an_UNKNOWN_credential_state_is_not_evidence_of_a_missing_key():
    """None means 'we did not check'. Reading it as 'absent' fabricates a
    founder action; reading it as 'present' fabricates health. With no attempt
    on record the honest answer is that nobody has tried it."""
    entry = {**ENTRY, "needs_credential": True, "credential_present": None}
    assert _score(entry, [], [])["status"] == sc.STATUS_NEVER_TRIED


def test_a_credentialed_source_that_was_attempted_is_scored_on_the_attempt():
    entry = {**ENTRY, "needs_credential": True, "credential_present": None}
    out = _score(entry, [], [{"source_name": "s1", "ok": False}])
    assert out["status"] == sc.STATUS_TRIED_FAILING


def test_supplied_but_EMPTY_evidence_is_a_measurement_not_an_absence(tmp_path):
    """A database read that legitimately returns nothing must report the
    measured state. Deriving evidence-presence from file CONTENTS made a real
    zero indistinguishable from never having run — so the scorecard could never
    report a genuinely empty pipeline, the state it most needs to report."""
    rows = tmp_path / "rows.json"
    attempts = tmp_path / "attempts.json"
    rows.write_text("[]", encoding="utf-8")
    attempts.write_text("[]", encoding="utf-8")
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"sources": [
        {**ENTRY, "needs_credential": False}]}), encoding="utf-8")

    assert sc.main(["--registry", str(registry), "--rows", str(rows),
                    "--attempts", str(attempts)]) == 0
    scored = sc.score_source({**ENTRY, "needs_credential": False},
                             {}, {}, {}, {}, True)
    assert scored["status"] == sc.STATUS_NEVER_TRIED, (
        "an empty-but-supplied dump must score NEVER_TRIED, not UNKNOWN")


def test_every_non_working_status_yields_a_next_action():
    """A row that says 'broken' and stops is a complaint, not a work item."""
    for status, text in sc.REMEDIATION_BY_STATUS.items():
        if status != sc.STATUS_WORKING:
            assert text, status


def test_unique_venues_credits_reach_no_other_source_provides():
    """Ranking on event volume alone would retire the four-venue first-party
    feeds the long-tail strategy depends on."""
    rows = [{"source_name": "big", "venue_name": "Shared Room"}] * 50 + [
        {"source_name": "small", "venue_name": "Shared Room"},
        {"source_name": "small", "venue_name": "Only Here"},
    ]
    big = _score({"id": "big", "name": "big", "source_class": "ticketing_api"},
                 rows, [{"source_name": "big", "ok": True}])
    small = _score({"id": "small", "name": "small", "source_class": "venue_calendar"},
                   rows, [{"source_name": "small", "ok": True}])
    assert big["events"] > small["events"]        # bigger throughput
    assert big["unique_venues"] == 0              # but no reach of its own
    assert small["unique_venues"] == 1            # this is the value it adds


def test_yield_per_attempt_surfaces_a_source_that_costs_more_than_it_returns():
    out = _score(ENTRY, [{"source_name": "s1", "venue_name": "V"}],
                 [{"source_name": "s1", "ok": True}] * 40)
    assert out["yield_per_attempt"] == 0.03


def test_trend_counts_improvements_for_every_measure():
    prev = {"stamp": "t0", "sources": [
        {"id": "a", "status": sc.STATUS_TRIED_FAILING, "events": 0, "venues": 0,
         "unique_venues": 0, "attempts_ok": 0, "yield_per_attempt": 0.0}]}
    current = [{"id": "a", "status": sc.STATUS_WORKING, "events": 10, "venues": 2,
                "unique_venues": 1, "attempts_ok": 1, "yield_per_attempt": 10.0}]
    t = sc.diff_against(prev, current)
    for measure in sc.MEASURES:
        assert t["improved"][measure] == 1, measure
    assert t["status_improved"] == 1


def test_trend_also_counts_regressions_so_decay_is_visible():
    prev = {"stamp": "t0", "sources": [
        {"id": "a", "status": sc.STATUS_WORKING, "events": 10, "venues": 2,
         "unique_venues": 1, "attempts_ok": 5, "yield_per_attempt": 2.0}]}
    current = [{"id": "a", "status": sc.STATUS_TRIED_EMPTY, "events": 0, "venues": 0,
                "unique_venues": 0, "attempts_ok": 1, "yield_per_attempt": 0.0}]
    t = sc.diff_against(prev, current)
    assert t["regressed"]["events"] == 1
    assert t["status_improved"] == 0


def test_the_live_registry_builds_and_covers_every_source():
    """The shipped registry parses and every row is class-bound."""
    import pathlib
    doc = json.loads((pathlib.Path(reg.REPO) / "sources" / "source_registry.json")
                     .read_text(encoding="utf-8"))
    assert doc["source_count"] >= 116
    assert all(s["source_class"] in SOURCE_CLASSES for s in doc["sources"])


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
    months = [{"location_name": "MOHAWK", "location_city": "AUSTIN",
               "location_county": "227",
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
