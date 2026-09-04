"""Do512 as ONE desk instance — the mapping, the walk, and what may be claimed.

Founder's ticket, verbatim where it decides a test: "Treat Do512 as one desk
instance ... Paginate the public dated list until exhausted, or write
blocked_reason per page. No login." / "Each card -> our happening ... No
invented dates. No identity required for the row to exist." / "Mapping table:
Do512 category -> our kind | other. Our kinds stay ours." / "Order-of-magnitude
vs their live list is the pass. Tiny fixture counts are not a pass."

So the properties under test are: the committed mapping cannot introduce a kind
and cannot claim it read a page nobody has read; a card is a row whether or not
it states an address or a date; this desk's categories arrive by PATH, and a
year in a permalink is never one of them; and the fixture walk, which ends on a
control we cannot follow, is never printed as an exhausted desk.
"""
from __future__ import annotations

import importlib.util
import json
import os

import pytest

from worker.locale import pack as lp
from worker.locale.desk_walk import walk
from worker.locale.kind_map import KindMapError, load_kind_map

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPCOG = "us-tx-capcog"
DOOR = "do512-today"
MAP = "do512"
FIXTURES = os.path.join(REPO, "tests", "fixtures", "desk_pages", DOOR)


def _load_tool():
    path = os.path.join(REPO, "tools", "desk_coverage.py")
    spec = importlib.util.spec_from_file_location("desk_coverage_tool_do512", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


@pytest.fixture(scope="module")
def doors():
    return {d.door_id: d for d in lp.hunt(CAPCOG)}


@pytest.fixture(scope="module")
def desk(doors):
    return doors[DOOR]


@pytest.fixture(scope="module")
def kind_map():
    return load_kind_map(MAP)


@pytest.fixture()
def committed_walk(desk, kind_map):
    fetch, start_url, _ = tool.fixture_fetcher(DOOR)
    return walk(desk, fetch, start_url=start_url, kind_map=kind_map)


# --------------------------------------------------------------------------
# The door: one desk instance, read without logging in
# --------------------------------------------------------------------------

def test_the_pack_door_the_founder_named_is_readable(desk):
    assert desk.readable
    assert desk.public and desk.intake == "html"
    assert desk.via == "Do512"          # the card's trust statement, from the pack
    assert desk.blocked_reason is None


def test_every_door_this_mapping_claims_exists_and_is_readable(kind_map, doors):
    for door_id in kind_map.applies_to_doors:
        assert door_id in doors, f"{door_id} is not in pack {CAPCOG}"
        assert doors[door_id].readable


def test_the_sibling_doors_state_their_own_kind_without_reading_a_card(doors):
    # A door scoped to one kind states it for everything behind it; a general
    # desk states nothing and its rows are `other` (never guessed from a title).
    assert doors["do512-live-music-today"].declared_kind == "music"
    assert doors["do512-family"].declared_kind == "family"
    assert doors[DOOR].declared_kind == "other"


# --------------------------------------------------------------------------
# The mapping: our kinds stay ours, and no row claims a reading nobody made
# --------------------------------------------------------------------------

def test_every_our_kind_is_one_of_the_locales_own(kind_map):
    ours = set(lp.load_pack(CAPCOG).kinds)
    assert ours
    for row in kind_map.rows:
        assert row.our_kind in ours, f"{row.desk_category} -> {row.our_kind}"


def test_no_row_claims_to_have_been_observed_on_the_live_desk(kind_map):
    # Egress to do512.com is denied from this build (curl CONNECT 403), so
    # nobody here has read a page of this desk. A `desk_observed` row would be
    # a claim about a reading that never happened.
    assert [r.desk_category for r in kind_map.rows if r.evidence == "desk_observed"] == []


def test_the_one_cited_row_is_cited_to_a_committed_pack_door(kind_map, doors):
    cited = [r for r in kind_map.rows if r.evidence == "desk_id_cited"]
    assert [r.desk_category for r in cited] == ["live-music"]
    # The citation must be checkable against the pack, not against memory.
    assert "/events/live-music/" in doors["do512-live-music-today"].url


def test_every_row_carries_a_grade_and_says_what_kind_of_claim_it_is(kind_map):
    for row in kind_map.rows:
        assert row.evidence in ("desk_observed", "desk_id_cited", "language_rule")
        assert row.note and row.note.strip()


def test_the_mapping_reads_this_desks_paths_not_a_query_parameter(kind_map):
    hows = {s.how for s in kind_map.signals}
    assert "href_path" in hows and "label" in hows
    assert [s.prefix for s in kind_map.signals if s.how == "href_path"] == ["/events/"]


def test_a_category_is_read_from_the_desks_own_path(kind_map):
    assert kind_map.resolve(
        hrefs=["https://do512.com/events/live-music/today"]) == ("music", "live-music")


def test_a_year_in_a_permalink_is_never_a_category(kind_map):
    # /events/<year>/<month>/<day>/<slug> is how a desk addresses ONE listing.
    permalink = "https://do512.com/events/2026/9/12/bright-room-quartet"
    assert kind_map.section_ids_in(permalink) == ()
    assert kind_map.resolve(hrefs=[permalink]) == (None, None)


def test_a_category_this_table_does_not_cover_is_reported_not_guessed(kind_map):
    assert kind_map.resolve(labels=["Nightlife"]) == (None, None)
    assert "Nightlife" in kind_map.unmapped_from(labels=["Nightlife"])


def test_the_mapping_cannot_introduce_a_kind_of_its_own(tmp_path, kind_map):
    doc = json.load(open(os.path.join(REPO, "sources", "kind_maps", f"{MAP}.json"),
                         encoding="utf-8"))
    doc["label_rows"] = [{"desk_category": "Nightlife", "our_kind": "nightlife",
                          "evidence": "language_rule"}]
    (tmp_path / f"{MAP}.json").write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(KindMapError, match="never extends it"):
        load_kind_map(MAP, maps_dir=str(tmp_path))


def test_the_committed_file_is_the_one_the_door_resolves_to(kind_map):
    from worker.locale.kind_map import map_for_door
    assert map_for_door(DOOR).map_id == MAP


# --------------------------------------------------------------------------
# The walk over the committed pages
# --------------------------------------------------------------------------

def test_the_fixtures_say_out_loud_that_they_are_not_the_live_desk():
    manifest = json.load(open(os.path.join(FIXTURES, "manifest.json"), encoding="utf-8"))
    note = manifest["note"]
    assert "NOT a saved copy" in note and "do512.com" in note
    assert "FIXTURE counts" in note


def test_the_walk_follows_the_desks_own_links_across_every_committed_page(committed_walk):
    assert [p.n for p in committed_walk.pages] == [1, 2, 3]
    assert all(p.status == 200 and p.blocked_reason is None
               for p in committed_walk.pages)
    assert committed_walk.pages_read == 3 and committed_walk.pages_blocked == 0


def test_a_list_that_continues_behind_a_button_is_never_called_exhausted(committed_walk):
    assert committed_walk.stopped_because == "next_control_not_a_link"
    assert committed_walk.exhausted is False
    assert any("load more" in n.lower() for n in committed_walk.notes)


def test_both_row_counts_are_kept_so_pagination_can_neither_inflate_nor_hide(
        committed_walk):
    assert committed_walk.rows_seen == 17      # rows the pages printed
    assert committed_walk.count == 16          # unique happenings
    assert committed_walk.duplicates_across_pages == 1
    assert committed_walk.merged_readings == 1
    assert committed_walk.skipped_untitled == 1


def test_every_row_carries_the_doors_own_trust_statement(committed_walk):
    assert committed_walk.rows
    assert {r.via for r in committed_walk.rows} == {"Do512"}
    assert {r.door_id for r in committed_walk.rows} == {DOOR}


def test_a_card_with_no_address_and_no_date_still_exists(committed_walk):
    row = next(r for r in committed_walk.rows if r.title == "No-Address Chapbook Swap")
    assert row.listing_url is None and row.when is None
    # Existence is the door's question. An identity test would delete this row.


def test_prose_where_the_clock_should_be_is_kept_as_prose(committed_walk):
    row = next(r for r in committed_walk.rows if r.title == "Riverside Story Circle")
    assert row.when is None and row.when_precision is None
    assert row.when_text == "this Saturday, late afternoon"


def test_the_dated_rows_carry_only_dates_the_page_stated(committed_walk):
    for row in committed_walk.rows:
        if row.when:
            assert row.when.startswith("2026-09-")
            assert row.when_text, "a stated date should keep the text it was printed as"
    assert committed_walk.dated == 14


def test_a_repeat_on_a_later_page_fills_a_hole_and_overwrites_nothing(committed_walk):
    row = next(r for r in committed_walk.rows if r.title == "Bright Room Quartet")
    # Page 1 stated this card twice — its JSON-LD (a UTC instant, no venue, no
    # printed date text) and its HTML (the same instant written -05:00, with the
    # text it printed). Page 2 repeated it and stated the venue.
    assert row.when == "2026-09-13T01:00:00Z"        # the first reading, untouched
    assert row.when_text == "Sat., Sept. 12, 8pm"    # hole filled by the second
    assert row.place_text == "The Bright Room"       # hole filled from page 2


def test_kinds_come_from_the_desks_own_category(committed_walk):
    by_title = {r.title: r for r in committed_walk.rows}
    assert by_title["Bright Room Quartet"].kind == "music"          # path, cited id
    assert by_title["Bright Room Quartet"].kind_source == "desk_category"
    assert by_title["Taco Alley Pop-Up"].kind == "food"             # printed label
    assert by_title["Council Budget Hearing"].kind == "civic"
    assert by_title["Silent Film Night"].kind == "film"


def test_a_card_stating_nothing_we_map_lands_on_other_and_is_printed(committed_walk):
    row = next(r for r in committed_walk.rows
               if r.title == "Warehouse District Late Set")
    assert row.kind == "other" and row.kind_source == "default"
    assert "nightlife" in [c.lower() for c in committed_walk.unmapped_categories]


# --------------------------------------------------------------------------
# The tables
# --------------------------------------------------------------------------

def test_the_category_table_prints_the_grade_the_row_was_decided_by(
        committed_walk, kind_map):
    table = tool.category_table(committed_walk, kind_map)
    live_music = next(line for line in table.splitlines() if "live-music" in line)
    # Decided by the CITED section id, so the table must not print the
    # language-rule grade of the label that happens to normalise the same way.
    assert "desk_id_cited" in live_music


def test_the_coverage_table_says_this_is_a_floor_not_the_desks_list(committed_walk):
    table = tool.coverage_table(committed_walk, None, live=False,
                                reason_when_unknown="no DSN")
    assert "walk incomplete" in table and "next_control_not_a_link" in table
    assert "FLOOR" in table
    assert "fixture run" in table


def test_an_unchecked_store_prints_unverified_never_zero(committed_walk):
    table = tool.coverage_table(committed_walk, None, live=False,
                                reason_when_unknown="no DSN")
    total = next(line for line in table.splitlines() if line.startswith("| **TOTAL"))
    assert "unverified" in total and "| **0** |" not in total


def test_the_fixture_run_prints_all_three_tables(capsys):
    assert tool.main(["--door", DOOR]) == 0
    out = capsys.readouterr().out
    assert "## 1. Pages" in out and "## 2. Categories" in out and "## 3. Coverage" in out
    assert "FIXTURE walk" in out
    assert "do512.com" in out          # the fixture note names the unreached desk
