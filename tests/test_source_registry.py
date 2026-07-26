"""The source registry: every ingestion source, catalogued exactly once.

Founder directive 2026-07-26: an extensive list of every source identified
across the build, portable to any locale. The SCORING of those sources —
tried / working / remediation / volume, trended over time — is a separate
change; this file pins only that the registry cannot lose or duplicate a
source, and that every row binds to a real taxonomy class.
"""
import json
import pathlib
import re

import pytest

import tools.build_source_registry as reg
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


def test_discovered_sources_are_LEADS_never_equal_to_a_licence_record():
    """Web-search findings enter the registry, but marked.

    A search result is a far weaker claim than a TABC licence. If the two were
    indistinguishable, the scorecard could report an unverified lead as a
    working source — and the whole point of the scorecard is that status is
    derived from evidence, never asserted.
    """
    live = json.loads(
        (REPO / "sources" / "source_registry.json").read_text(encoding="utf-8"))
    discovered = [s for s in live["sources"] if s.get("origin") == "web_discovery"]
    assert discovered, "no discovered sources in the registry — did the loader run?"
    for s in discovered:
        assert s.get("verified") is False, s["id"]
        assert s.get("evidence"), f"{s['id']} has no URL to trace the claim to"
        assert s.get("remediation"), f"{s['id']} names no next action"
        # Unverified means UNKNOWN credential state, never an implied working one.
        assert s.get("credential_present") is None, s["id"]


def test_discovery_reached_the_counties_that_had_NO_sources():
    """Seven of the ten counties had zero curated sources. A denominator that
    lists venues in counties we have no way to hear from is a gap that looks
    like a finding."""
    live = json.loads(
        (REPO / "sources" / "source_registry.json").read_text(encoding="utf-8"))
    have = {s.get("county") for s in live["sources"] if s.get("county")}
    for county in ("bastrop", "blanco", "caldwell", "fayette", "lee", "llano"):
        assert county in have, f"{county} still has no source of any kind"


def test_a_discovered_id_that_collides_with_a_curated_row_FAILS():
    """KUTX and KUT were 'discovered' and turned out to be already catalogued.
    Silently overwriting a curated row with an unverified lead would be the
    duplicate-source defect again, in the direction that loses information."""
    original = reg.load_discovered
    reg.load_discovered = lambda: [
        {"id": "mohawk_austin", "name": "Mohawk (rediscovered)",
         "source_class": "venue_calendar", "origin": "web_discovery"}]
    try:
        with pytest.raises(SystemExit, match="collide"):
            reg.main(["--out", "/dev/null"])
    finally:
        reg.load_discovered = original


def test_every_registry_row_binds_to_a_real_taxonomy_class():
    built = reg.build(_catalog_with_merge_targets(
        {"id": "v", "name": "V", "category": "venue_calendar"}))
    for s in built:
        assert s["source_class"] in SOURCE_CLASSES, s


def test_the_live_registry_builds_and_covers_every_source():
    """The shipped registry parses and every row is class-bound."""
    import pathlib
    doc = json.loads((pathlib.Path(reg.REPO) / "sources" / "source_registry.json")
                     .read_text(encoding="utf-8"))
    assert doc["source_count"] >= 116
    assert all(s["source_class"] in SOURCE_CLASSES for s in doc["sources"])


