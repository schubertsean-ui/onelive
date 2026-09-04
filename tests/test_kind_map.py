"""A desk's categories map INTO our kinds; they never become our schema.

The founder's rule for this file, verbatim: "Our kinds stay ours; their labels
do not become the schema." So the properties under test are (1) a mapping cannot
introduce a kind, (2) an unmapped label lands on `other` and is REPORTED rather
than guessed at, and (3) every committed row says what kind of claim it is.
"""
from __future__ import annotations

import json
import os

import pytest

from worker.locale import kind_map as km
from worker.locale.pack import load_pack

CAPCOG = "us-tx-capcog"
SHIPPED = "austin-chronicle"


@pytest.fixture(scope="module")
def shipped():
    return km.load_kind_map(SHIPPED)


def write_map(tmp_path, doc, name=SHIPPED):
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return str(tmp_path)


def base_doc(**over):
    doc = {
        "map_id": SHIPPED,
        "kinds_from": CAPCOG,
        "default_kind": "other",
        "applies_to_doors": ["austin-chronicle-eventsearch"],
        "category_signals": [{"how": "label"}],
        "label_rows": [{"desk_category": "Music", "our_kind": "music",
                        "evidence": "language_rule"}],
    }
    doc.update(over)
    return doc


# --- the shipped mapping loads and is internally honest ----------------------

def test_the_shipped_mapping_loads(shipped):
    assert shipped.map_id == SHIPPED
    assert shipped.kinds_from == CAPCOG
    assert shipped.rows, "a committed mapping with no rows can only mislead"


def test_every_our_kind_is_one_of_ours(shipped):
    ours = set(load_pack(CAPCOG).kinds)
    assert {row.our_kind for row in shipped.rows} <= ours


def test_every_row_states_what_kind_of_claim_it_is(shipped):
    assert {row.evidence for row in shipped.rows} <= set(km.EVIDENCE_GRADES)
    # The one row keyed by the desk's OWN id is cited to a committed pack door,
    # not remembered: the id must actually appear in that door's URL.
    pack = load_pack(CAPCOG)
    urls = " ".join(d.url for d in pack.doors)
    for row in shipped.id_rows.values():
        assert row.evidence == "desk_id_cited"
        assert row.desk_category in urls, (
            f"section id {row.desk_category!r} is graded as cited but appears in "
            f"no committed door URL")


def test_the_mapping_claims_only_doors_that_exist(shipped):
    door_ids = {d.door_id for d in load_pack(CAPCOG).doors}
    assert set(shipped.applies_to_doors) <= door_ids


def test_no_two_rows_collide_after_normalisation(shipped):
    keys = [row.key for row in shipped.label_rows.values()]
    assert len(keys) == len(set(keys))


# --- resolving one card's stated category ------------------------------------

def test_a_stated_label_decides_the_kind(shipped):
    assert shipped.resolve(labels=["Live Music"]) == ("music", "Live Music")


def test_labels_match_regardless_of_case_punctuation_or_and(shipped):
    for spelling in ("Food & Drink", "food and drink", "FOOD  &  DRINK"):
        kind, _ = shipped.resolve(labels=[spelling])
        assert kind == "food", spelling


def test_the_desks_own_section_id_in_a_link_decides_the_kind(shipped):
    kind, matched = shipped.resolve(
        hrefs=["https://desk.example/EventSearch?eventSection=2151678&v=g"])
    assert (kind, matched) == ("art", "2151678")


def test_an_id_outranks_a_label(shipped):
    # An id is the desk's own identifier; a label is words that could be a
    # near-miss. When a card states both, the id wins.
    kind, matched = shipped.resolve(
        labels=["Music"],
        hrefs=["https://desk.example/EventSearch?eventSection=2151678"])
    assert (kind, matched) == ("art", "2151678")


def test_an_unmapped_label_decides_nothing_and_is_reported(shipped):
    assert shipped.resolve(labels=["Psychogeography"]) == (None, None)
    assert shipped.unmapped_from(labels=["Psychogeography"]) == ("Psychogeography",)


def test_an_unmapped_section_id_is_reported_too(shipped):
    assert shipped.unmapped_from(
        hrefs=["https://desk.example/EventSearch?eventSection=999999"]) == ("999999",)


def test_a_mapped_label_is_not_reported_as_unmapped(shipped):
    assert shipped.unmapped_from(labels=["Live Music"]) == ()


def test_no_category_at_all_decides_nothing(shipped):
    assert shipped.resolve() == (None, None)
    assert shipped.unmapped_from() == ()


def test_a_url_without_the_param_states_no_section(shipped):
    assert shipped.section_ids_in("https://desk.example/Events/some-listing") == ()


# --- the refusals ------------------------------------------------------------

def test_a_mapping_may_not_introduce_a_kind(tmp_path):
    directory = write_map(tmp_path, base_doc(label_rows=[
        {"desk_category": "Wrestling", "our_kind": "wrestling",
         "evidence": "language_rule"}]))
    with pytest.raises(km.KindMapError) as exc:
        km.load_kind_map(SHIPPED, maps_dir=directory)
    assert "never extends it" in str(exc.value)


def test_an_unknown_evidence_grade_is_refused(tmp_path):
    directory = write_map(tmp_path, base_doc(label_rows=[
        {"desk_category": "Music", "our_kind": "music", "evidence": "vibes"}]))
    with pytest.raises(km.KindMapError):
        km.load_kind_map(SHIPPED, maps_dir=directory)


def test_a_default_kind_outside_our_vocabulary_is_refused(tmp_path):
    directory = write_map(tmp_path, base_doc(default_kind="whatever"))
    with pytest.raises(km.KindMapError):
        km.load_kind_map(SHIPPED, maps_dir=directory)


def test_a_mapping_that_claims_no_door_is_refused(tmp_path):
    directory = write_map(tmp_path, base_doc(applies_to_doors=[]))
    with pytest.raises(km.KindMapError) as exc:
        km.load_kind_map(SHIPPED, maps_dir=directory)
    assert "no door" in str(exc.value)


def test_a_mapping_that_claims_a_door_the_pack_does_not_have_is_refused(tmp_path):
    directory = write_map(tmp_path, base_doc(applies_to_doors=["no-such-door"]))
    with pytest.raises(km.KindMapError):
        km.load_kind_map(SHIPPED, maps_dir=directory)


def test_two_labels_that_normalise_alike_are_refused(tmp_path):
    directory = write_map(tmp_path, base_doc(label_rows=[
        {"desk_category": "Food & Drink", "our_kind": "food", "evidence": "language_rule"},
        {"desk_category": "food and drink", "our_kind": "music", "evidence": "language_rule"}]))
    with pytest.raises(km.KindMapError) as exc:
        km.load_kind_map(SHIPPED, maps_dir=directory)
    assert "never be read" in str(exc.value)


def test_id_rows_without_a_signal_that_could_find_them_are_refused(tmp_path):
    directory = write_map(tmp_path, base_doc(
        category_signals=[{"how": "label"}],
        id_rows=[{"desk_category": "123", "our_kind": "art",
                  "evidence": "desk_id_cited"}]))
    with pytest.raises(km.KindMapError) as exc:
        km.load_kind_map(SHIPPED, maps_dir=directory)
    assert "never match" in str(exc.value)


def test_an_href_param_signal_must_name_its_param(tmp_path):
    directory = write_map(tmp_path, base_doc(
        category_signals=[{"how": "href_param"}]))
    with pytest.raises(km.KindMapError):
        km.load_kind_map(SHIPPED, maps_dir=directory)


def test_a_file_that_does_not_know_its_own_name_is_refused(tmp_path):
    directory = write_map(tmp_path, base_doc(map_id="something-else"))
    with pytest.raises(km.KindMapError) as exc:
        km.load_kind_map(SHIPPED, maps_dir=directory)
    assert "does not know its own name" in str(exc.value)


def test_a_missing_mapping_raises_rather_than_returning_an_empty_one(tmp_path):
    with pytest.raises(km.KindMapError):
        km.load_kind_map("no-such-map", maps_dir=str(tmp_path))


def test_a_map_id_may_not_steer_the_path():
    with pytest.raises(km.KindMapError):
        km.load_kind_map("../../etc/passwd")


def test_a_malformed_file_raises(tmp_path):
    (tmp_path / f"{SHIPPED}.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(km.KindMapError):
        km.load_kind_map(SHIPPED, maps_dir=str(tmp_path))


def test_a_mapping_whose_locale_does_not_load_is_refused(tmp_path):
    directory = write_map(tmp_path, base_doc(kinds_from="no-such-locale"))
    with pytest.raises(km.KindMapError):
        km.load_kind_map(SHIPPED, maps_dir=directory)


# --- door lookup -------------------------------------------------------------

def test_map_for_door_finds_the_mapping_that_claims_the_door():
    found = km.map_for_door("austin-chronicle-eventsearch")
    assert found is not None and found.map_id == SHIPPED


def test_an_unmapped_door_is_not_an_error():
    # Coverage must never depend on a taxonomy being finished: a door with no
    # mapping reads with its declared scope, exactly as before.
    assert km.map_for_door("no-such-door") is None


def test_available_maps_lists_the_committed_ones():
    assert SHIPPED in km.available_maps()


def test_normalize_label_is_empty_for_nothing():
    assert km.normalize_label(None) == ""
    assert km.normalize_label("   ") == ""


# --- href_path: the same category statement, in the shape a path-routed desk
#     publishes it ---------------------------------------------------------

def path_doc(**over):
    """A mapping keyed on PATH segments rather than on a query parameter."""
    doc = base_doc(
        map_id="do512", applies_to_doors=["do512-today"],
        category_signals=[{"how": "href_path", "prefix": "/events/"}],
        id_rows=[{"desk_category": "live-music", "our_kind": "music",
                  "evidence": "desk_id_cited"}],
        label_rows=[],
    )
    doc.update(over)
    return doc


def test_a_path_signal_must_name_the_prefix_its_categories_hang_off(tmp_path):
    directory = write_map(
        tmp_path, path_doc(category_signals=[{"how": "href_path"}]), name="do512")
    with pytest.raises(km.KindMapError) as exc:
        km.load_kind_map("do512", maps_dir=directory)
    assert "path prefix" in str(exc.value)


def test_id_rows_are_satisfied_by_a_path_signal(tmp_path):
    # Before href_path existed this raised: id_rows required an href_param, so a
    # desk that routes by path could commit no cited row at all.
    directory = write_map(tmp_path, path_doc(), name="do512")
    loaded = km.load_kind_map("do512", maps_dir=directory)
    assert loaded.kind_for_id("live-music") == "music"


def test_id_rows_with_no_href_signal_at_all_are_still_refused(tmp_path):
    directory = write_map(
        tmp_path, path_doc(category_signals=[{"how": "label"}]), name="do512")
    with pytest.raises(km.KindMapError) as exc:
        km.load_kind_map("do512", maps_dir=directory)
    assert "could never match" in str(exc.value)


def test_a_path_category_is_read_from_the_desks_own_link(tmp_path):
    loaded = km.load_kind_map("do512", maps_dir=write_map(tmp_path, path_doc(),
                                                          name="do512"))
    assert loaded.resolve(
        hrefs=["https://d.example/events/live-music/today"]) == ("music", "live-music")


def test_a_path_segment_is_read_only_at_the_root_the_map_named():
    # Matching the prefix anywhere would make /tickets/events/art a category.
    assert km.segment_after("https://d.example/events/art/", "/events/") == "art"
    assert km.segment_after("https://d.example/tickets/events/art", "/events/") is None


def test_a_purely_numeric_segment_is_a_date_or_an_id_never_a_category():
    assert km.segment_after("https://d.example/events/2026/9/12/show", "/events/") is None


def test_a_path_with_nothing_after_the_prefix_states_no_category():
    assert km.segment_after("https://d.example/events/", "/events/") is None
    assert km.segment_after("https://d.example/events", "/events/") is None
    assert km.segment_after(None, "/events/") is None
    assert km.segment_after("https://d.example/events/art", "") is None


def test_a_path_category_the_table_misses_is_reported_not_guessed(tmp_path):
    loaded = km.load_kind_map("do512", maps_dir=write_map(tmp_path, path_doc(),
                                                          name="do512"))
    assert loaded.resolve(hrefs=["https://d.example/events/nightlife/"]) == (None, None)
    assert loaded.unmapped_from(
        hrefs=["https://d.example/events/nightlife/"]) == ("nightlife",)


def test_a_desks_own_id_outranks_a_label_that_normalises_the_same_way(tmp_path):
    # `resolve` reads ids before labels, so "live-music" is decided by the CITED
    # id even though the label row "Live Music" normalises to the same words.
    doc = path_doc(category_signals=[{"how": "href_path", "prefix": "/events/"},
                                     {"how": "label"}],
                   label_rows=[{"desk_category": "Live Music", "our_kind": "music",
                                "evidence": "language_rule"}])
    loaded = km.load_kind_map("do512", maps_dir=write_map(tmp_path, doc, name="do512"))
    kind, matched = loaded.resolve(labels=["Live Music"],
                                   hrefs=["https://d.example/events/live-music/today"])
    assert (kind, matched) == ("music", "live-music")
    assert loaded.id_rows[matched].evidence == "desk_id_cited"


# --- one vocabulary across every committed desk -------------------------------

def test_a_language_rule_word_means_the_same_kind_on_every_committed_desk():
    """`language_rule` is a claim about OUR vocabulary, so it cannot be desk-local.

    Each desk gets its own mapping FILE, which means the same English word is
    written down once per desk — and the moment "Comedy" is `comedy` on one desk
    and `theater` on another, the catalog holds two taxonomies wearing one set of
    names, with nothing to show which row came from which. Cited section ids are
    deliberately exempt: `2151678` is one desk's own identifier and means nothing
    on another.
    """
    seen = {}
    for map_id in km.available_maps():
        loaded = km.load_kind_map(map_id)
        for row in loaded.rows:
            if row.evidence != "language_rule":
                continue
            word = km.normalize_label(row.desk_category)
            first_map, first_kind = seen.setdefault(word, (map_id, row.our_kind))
            assert first_kind == row.our_kind, (
                f"{word!r} maps to {first_kind!r} in {first_map} but to "
                f"{row.our_kind!r} in {map_id} — one word, two kinds")
