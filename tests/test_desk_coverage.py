"""tools/desk_coverage.py — the founder's three tables, and the honesty in them.

The properties under test are the ones a coverage number lives or dies on:
`in_store` never renders "we could not check" as "we have none"; a walk that
stopped early is never printed as the desk's whole list; a fixture run says it
is a fixture run; and the store match rule is the one the file documents.
"""
from __future__ import annotations

import importlib.util
import os

import pytest

from worker.locale import pack as lp
from worker.locale.desk_read import Happening
from worker.locale.desk_walk import PageFetch, walk
from worker.locale.kind_map import load_kind_map

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPCOG = "us-tx-capcog"
DOOR = "austin-chronicle-eventsearch"


def _load_tool():
    path = os.path.join(REPO, "tools", "desk_coverage.py")
    spec = importlib.util.spec_from_file_location("desk_coverage_tool", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


@pytest.fixture(scope="module")
def desk():
    return {d.door_id: d for d in lp.hunt(CAPCOG)}[DOOR]


@pytest.fixture()
def committed_walk(desk):
    fetch, start_url, _ = tool.fixture_fetcher(DOOR)
    return walk(desk, fetch, start_url=start_url,
                kind_map=load_kind_map("austin-chronicle"))


def happening(title, when=None, kind="other", **over):
    fields = dict(
        title=title, when=when, when_text=None, when_precision=None,
        place_text=None, via="Desk", kind=kind, door_id=DOOR,
        door_type="local_desk", locale_id=CAPCOG,
        source_url="https://desk.example/list", listing_url=None)
    fields.update(over)
    return Happening(**fields)


# --- the fixture fetcher -----------------------------------------------------

def test_the_fixture_fetcher_serves_the_committed_pages():
    fetch, start_url, manifest = tool.fixture_fetcher(DOOR)
    assert start_url and start_url in manifest["pages"]
    first = fetch(start_url)
    assert isinstance(first, PageFetch) and first.status == 200 and first.body


def test_a_url_the_manifest_does_not_list_answers_404_not_an_empty_page():
    fetch, _, _ = tool.fixture_fetcher(DOOR)
    assert fetch("https://desk.example/nope").status == 404


def test_the_committed_manifest_says_the_pages_are_synthetic():
    _, _, manifest = tool.fixture_fetcher(DOOR)
    note = manifest["note"].lower()
    assert "not a saved copy" in note and "synthetic" in note


# --- in_store matching -------------------------------------------------------

def test_a_dated_row_matches_only_on_the_same_day():
    rows = [happening("Brass Band", when="2026-09-11T20:00:00-05:00")]
    same_day = tool.store_matches(
        rows, lambda titles: [("Brass Band", "2026-09-11T20:00:00-05:00")])
    other_day = tool.store_matches(
        rows, lambda titles: [("Brass Band", "2026-10-30T20:00:00-05:00")])
    assert same_day["matched"] == 1 and same_day["dated_match"] == 1
    # A title-only match on a different day is a recurring series, not this
    # night (the defect R-094/MATCH_COLLISION already records).
    assert other_day["matched"] == 0


def test_an_undated_row_matches_on_title_and_is_counted_separately():
    rows = [happening("Open Mic")]
    counts = tool.store_matches(rows, lambda titles: [("Open Mic", None)])
    assert counts == {"matched": 1, "dated_match": 0, "title_only": 1}


def test_titles_match_regardless_of_case_and_spacing():
    rows = [happening("  BRASS   Band ", when="2026-09-11T20:00:00-05:00")]
    counts = tool.store_matches(
        rows, lambda titles: [("brass band", "2026-09-11T00:00:00Z")])
    assert counts["matched"] == 1


def test_a_row_we_do_not_hold_is_a_gap():
    rows = [happening("Nobody Has This", when="2026-09-11T20:00:00-05:00")]
    assert tool.store_matches(rows, lambda titles: [])["matched"] == 0


def test_the_store_is_asked_only_about_the_titles_in_hand():
    asked = {}

    def fetch_rows(titles):
        asked["titles"] = list(titles)
        return []

    tool.store_matches([happening("A"), happening("B")], fetch_rows)
    assert asked["titles"] == ["a", "b"]


# --- the coverage table ------------------------------------------------------

def test_an_unasked_store_prints_unverified_never_zero(committed_walk):
    table = tool.coverage_table(committed_walk, None, live=True,
                                reason_when_unknown="no DSN in this environment")
    total = [ln for ln in table.splitlines() if ln.startswith("| **TOTAL")][0]
    assert "unverified" in total and "| **0** |" not in total
    assert "no DSN in this environment" in total


def test_a_counted_store_prints_the_gap_and_the_rule(committed_walk):
    store = {"matched": 4, "dated_match": 3, "title_only": 1}
    table = tool.coverage_table(committed_walk, store, live=True,
                                reason_when_unknown="unused")
    total = [ln for ln in table.splitlines() if ln.startswith("| **TOTAL")][0]
    assert f"**{committed_walk.count}**" in total and "**4**" in total
    assert f"**{committed_walk.count - 4}**" in total
    assert "matched on title+day" in total


def test_a_fixture_run_says_so_in_the_table(committed_walk):
    table = tool.coverage_table(committed_walk, None, live=False,
                                reason_when_unknown="x")
    assert "not from the live desk" in table


def test_an_incomplete_walk_is_never_printed_as_the_desks_whole_list(desk):
    def fetch(url):
        return PageFetch(url=url, status=403)

    blocked = walk(desk, fetch, start_url="https://desk.example/p1")
    table = tool.coverage_table(blocked, None, live=True, reason_when_unknown="x")
    assert "on_desk is a FLOOR" in table and "`wall`" in table


def test_per_kind_store_counts_are_not_invented(committed_walk):
    store = {"matched": 4, "dated_match": 4, "title_only": 0}
    table = tool.coverage_table(committed_walk, store, live=True,
                                reason_when_unknown="x")
    kind_rows = [ln for ln in table.splitlines() if ln.startswith("| kind ")]
    assert kind_rows and all("see TOTAL" in ln for ln in kind_rows)
    assert "would be inferred rather than counted" in table


# --- the category table ------------------------------------------------------

def test_the_category_table_shows_their_label_our_kind_and_the_evidence(
        committed_walk):
    table = tool.category_table(committed_walk, load_kind_map("austin-chronicle"))
    assert "| Live Music | `music` |" in table
    assert "language_rule" in table and "desk_id_cited" in table


def test_rows_with_no_mapped_category_are_shown_not_hidden(committed_walk):
    table = tool.category_table(committed_walk, load_kind_map("austin-chronicle"))
    assert "_(no mapped category stated)_" in table


# --- end to end --------------------------------------------------------------

def test_the_fixture_run_prints_all_three_tables(capsys):
    assert tool.main(["--door", DOOR]) == 0
    out = capsys.readouterr().out
    assert "## 1. Pages" in out and "## 2. Categories" in out and "## 3. Coverage" in out
    assert "| scope | on_desk | in_store | gap | reason |" in out
    assert "wrote nothing" in out
    assert "**Fixture run.**" in out


def test_an_unknown_door_is_an_error_not_an_empty_table(capsys):
    assert tool.main(["--door", "no-such-door"]) == 2
    assert "no door" in capsys.readouterr().err


def test_store_without_a_dsn_refuses_rather_than_printing_zero(capsys, monkeypatch):
    monkeypatch.delenv("ONELIVE_DB_DSN", raising=False)
    assert tool.main(["--door", DOOR, "--store"]) == 2
    assert "ONELIVE_DB_DSN" in capsys.readouterr().err


def test_a_door_with_no_committed_fixtures_says_so(capsys):
    assert tool.main(["--door", "ut-austin-localist"]) == 2
    assert "no committed fixtures" in capsys.readouterr().err
