"""The union of two desks — the founder's de-dup rule, and its four refusals.

Founder's ticket, verbatim where it decides a test: "One happening table from
the two dumps already on master: unique key, via (Chronicle / Do512 / both),
kind or other, dated or not." / "Board: Chronicle-only | Do512-only | both |
unique total. Label fixture vs live. 403 is not a zero list." / "Dedup: same
night + same place-text + same title-or-performer -> one row, many vias. No
identity service. No invented dates."

So the properties under test are: a night comes only from a date a desk stated,
projected onto the locale's own clock (the fixture whose markup says
`2026-09-12T01:00:00Z` is the September 11th night its page prints, and slicing
the string would say otherwise); the match is three equalities and nothing else;
a row that cannot be keyed is still IN the table, single-source, never dropped;
a desk that answered 403 makes every "<other desk> only" count unknown rather
than turning into a zero; and the table a founder reads has the columns it
declares — a key carrying a markdown pipe would silently split a row.
"""
from __future__ import annotations

import importlib.util
import json
import os
from zoneinfo import ZoneInfo

import pytest

from worker.locale import pack as lp
from worker.locale.desk_read import Happening
from worker.locale.desk_union import (
    BASIS_LOCAL, BASIS_PERFORMER, BASIS_UNION, DeskUnionError, board_table,
    desk_table, held_apart_table, local_night, near_miss_table, near_misses,
    performer_key, place_key, union, union_table,
)
from worker.locale.desk_walk import DeskWalk, PageVisit, walk
from worker.locale.kind_map import map_for_door

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPCOG = "us-tx-capcog"
CHRONICLE = "austin-chronicle-eventsearch"
DO512 = "do512-today"
TZ_ID = "America/Chicago"
TZ = ZoneInfo(TZ_ID)


def _load_tool():
    path = os.path.join(REPO, "tools", "desk_union.py")
    spec = importlib.util.spec_from_file_location("desk_union_tool", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


@pytest.fixture(scope="module")
def doors():
    return {d.door_id: d for d in lp.hunt(CAPCOG)}


def _walk(door_id, doors):
    fetch, start, _manifest = tool.fixture_fetcher(door_id)
    return walk(doors[door_id], fetch, start_url=start,
                kind_map=map_for_door(door_id))


@pytest.fixture(scope="module")
def walks(doors):
    return [_walk(CHRONICLE, doors), _walk(DO512, doors)]


@pytest.fixture(scope="module")
def one(walks):
    return union(walks, timezone=TZ, timezone_id=TZ_ID, mode="FIXTURE")


def _row(title, *, when=None, when_text=None, place="Shape Hall", kind="other",
         kind_source="default", door_id=CHRONICLE, via="Austin Chronicle",
         listing_url=None):
    return Happening(
        title=title, when=when, when_text=when_text,
        when_precision=("date" if when and len(when) == 10 else
                        ("datetime" if when else None)),
        place_text=place, via=via, kind=kind, door_id=door_id,
        door_type="local_desk", locale_id=CAPCOG,
        source_url="https://desk.example/page", listing_url=listing_url,
        kind_source=kind_source)


def _fake_walk(door_id, via, rows, *, blocked=None, stopped="no_next_link"):
    pages = [PageVisit(n=1, url="https://desk.example/", status=200,
                       rows_seen=len(rows), new_rows=len(rows))]
    if blocked:
        pages = [PageVisit(n=1, url="https://desk.example/", status=403,
                           blocked_reason=blocked)]
    return DeskWalk(door_id=door_id, door_type="local_desk", via=via,
                    start_url="https://desk.example/", pages=pages,
                    rows=list(rows), stopped_because=stopped)


# --------------------------------------------------------------------------
# "Same night" — from a stated date only, on the locale's clock
# --------------------------------------------------------------------------

def test_night_projects_a_utc_instant_onto_the_locale_clock():
    """The Chronicle fixture's opening listing states `2026-09-12T01:00:00Z`
    and PRINTS "Fri., Sept. 11, 8pm". The night is the desk's own words."""
    assert local_night("2026-09-12T01:00:00Z", TZ) == ("2026-09-11", None)
    assert local_night("2026-09-13T01:00:00Z", TZ) == ("2026-09-12", None)


def test_night_of_a_naive_offset_form_is_its_own_date():
    assert local_night("2026-09-12T21:30:00-05:00", TZ) == ("2026-09-12", None)
    assert local_night("2026-09-12T21:30:00", TZ) == ("2026-09-12", None)


def test_a_bare_date_is_used_as_stated():
    assert local_night("2026-09-13", TZ) == ("2026-09-13", None)


def test_no_stated_date_is_no_night_and_never_a_guess():
    night, why = local_night(None, TZ)
    assert night is None and why
    night, why = local_night("this Saturday, late afternoon", TZ)
    assert night is None and "unparsed" in why


def test_prose_never_becomes_a_night(one):
    """`when_text` is carried, never parsed: the fixtures print "Ongoing",
    "This weekend" and "this Saturday, late afternoon", and not one of them
    yields a date."""
    prose = [r for r in one.rows if not r.dated]
    assert prose, "the fixtures contain undated rows"
    assert all(r.night is None for r in prose)


# --------------------------------------------------------------------------
# The other two key parts
# --------------------------------------------------------------------------

def test_place_key_ignores_an_article_and_punctuation():
    assert place_key("The Fixture Room") == place_key("Fixture Room!") == "fixture room"
    assert place_key("Fixture Annex") != place_key("Fixture Room")
    assert place_key(None) == ""


def test_a_latin_diacritic_never_erases_the_letter_it_sits_on():
    """`destructive-normalization` (docs/memory/RED_CLASSES.md): a normaliser
    that deletes what it cannot represent makes two spellings of one venue stop
    comparing equal. One desk writes the accent, the other does not."""
    assert place_key("Cafe\u0301 Blue") == place_key("Café Blue") == place_key("Cafe Blue")
    assert place_key("Currás") == place_key("Curra's") == place_key("Curras")


def test_a_non_latin_title_keeps_its_own_words():
    """The same class, the worse half: `[^0-9a-z]` would reduce this to the one
    Latin word it happens to carry."""
    assert performer_key("Кино Night", "") == "кино night"
    assert performer_key("東京ナイト", "") == "東京ナイト"


def test_a_meaning_bearing_mark_is_not_folded_away():
    """Folding harder is not safer here: in this module a wrong merge prints two
    happenings as one, and a Devanagari nukta changes the consonant."""
    assert performer_key("क़ा", "") != performer_key("का", "")


def test_performer_strips_a_venue_tail_only_when_it_is_this_rows_venue():
    assert performer_key("Fixture Quartet at the Shape Hall",
                         "shape hall") == "fixture quartet"
    # The same title at a DIFFERENT place keeps its "at": an "at" that names
    # something else is part of the title, and guessing is what we refuse.
    assert performer_key("Breakfast at Tiffany's",
                         "marquee room") == "breakfast at tiffanys"


def test_performer_strips_a_support_tail_but_never_a_presents_lead():
    assert performer_key("Shape Town Brass w/ The Fixtures", "") == "shape town brass"
    assert performer_key("Shape Town Brass feat. Someone", "") == "shape town brass"
    # "Venue presents Artist" runs the other way — stripping the tail would keep
    # the promoter and throw away the act, so `presents` is not a separator.
    assert performer_key("Fixture Room presents Shape Town Brass",
                         "") == "fixture room presents shape town brass"


def test_performer_never_empties_a_title():
    assert performer_key("w/ Someone", "") == "w someone"


# --------------------------------------------------------------------------
# The union over the two committed dumps
# --------------------------------------------------------------------------

def test_the_one_row_both_desks_printed_becomes_one_row_two_vias(one):
    both = [r for r in one.rows if len(r.vias) > 1]
    assert len(both) == 1
    row = both[0]
    assert row.title == "Shape Town Brass"
    assert set(row.vias) == {"Austin Chronicle", "Do512"}
    assert row.basis == BASIS_UNION
    assert row.night == "2026-09-12"


def test_the_board_adds_up(one, walks):
    printed = sum(len(w.rows) for w in walks)
    assert one.total == printed - one.both
    assert one.only("Austin Chronicle") + one.only("Do512") + one.both == one.total


def test_no_row_is_ever_dropped(one, walks):
    """Coverage Law: do not drop single-source rows. Every row either merged or
    stands on its own — no row leaves the table."""
    members = [m for r in one.rows for m in r.members]
    assert len(members) == sum(len(w.rows) for w in walks)
    titles = sorted(m.row.title for m in members)
    assert titles == sorted(r.title for w in walks for r in w.rows)


def test_unkeyable_rows_stay_in_the_table_as_themselves(one):
    local = [r for r in one.rows if r.basis == BASIS_LOCAL]
    assert local, "the fixtures contain rows with no stated night"
    for row in local:
        assert len(row.vias) == 1        # single-source, and it stays that way
        assert row.key.count("#") == 1   # a desk-local key, not a union key
    assert len(one.held_apart) == len(local)


def test_two_desks_with_no_shared_row_still_union_to_the_sum(doors):
    a = _fake_walk("desk-a", "A", [_row("Alpha", when="2026-09-12T20:00:00-05:00")])
    b = _fake_walk("desk-b", "B", [_row("Beta", when="2026-09-12T20:00:00-05:00",
                                        door_id="desk-b", via="B")])
    got = union([a, b], timezone=TZ, timezone_id=TZ_ID)
    assert got.total == 2 and got.both == 0


def test_a_performer_match_merges_and_is_listed_as_one():
    """One desk prints the venue in the title, the other does not."""
    a = _fake_walk("desk-a", "A", [
        _row("Fixture Quartet at the Shape Hall", when="2026-09-12T20:00:00-05:00")])
    b = _fake_walk("desk-b", "B", [
        _row("Fixture Quartet", when="2026-09-12T20:00:00-05:00",
             door_id="desk-b", via="B")])
    got = union([a, b], timezone=TZ, timezone_id=TZ_ID)
    assert got.total == 1
    assert got.rows[0].basis == BASIS_PERFORMER
    assert set(got.rows[0].vias) == {"A", "B"}
    assert len(got.performer_merges) == 1, "a judged merge is always listed"


def test_a_different_night_or_place_never_merges():
    base = dict(when="2026-09-12T20:00:00-05:00")
    a = _fake_walk("desk-a", "A", [_row("Same Name", **base)])
    other_night = _fake_walk("desk-b", "B", [
        _row("Same Name", when="2026-09-13T20:00:00-05:00", door_id="desk-b", via="B")])
    other_place = _fake_walk("desk-c", "C", [
        _row("Same Name", place="Fixture Annex", door_id="desk-c", via="C", **base)])
    assert union([a, other_night], timezone=TZ, timezone_id=TZ_ID).total == 2
    assert union([a, other_place], timezone=TZ, timezone_id=TZ_ID).total == 2


def test_two_undated_rows_never_merge_across_desks():
    """Both desks print the same title at the same venue with no date. Merging
    them would assert a night nobody stated."""
    a = _fake_walk("desk-a", "A", [_row("Open Mic", when_text="Ongoing")])
    b = _fake_walk("desk-b", "B", [_row("Open Mic", when_text="Ongoing",
                                        door_id="desk-b", via="B")])
    got = union([a, b], timezone=TZ, timezone_id=TZ_ID)
    assert got.total == 2
    assert all(r.basis == BASIS_LOCAL for r in got.rows)


def test_a_desk_stated_kind_outranks_the_other_desks_default():
    a = _fake_walk("desk-a", "A", [_row("Shape Town Brass",
                                        when="2026-09-12T20:00:00-05:00")])
    b = _fake_walk("desk-b", "B", [_row("Shape Town Brass",
                                        when="2026-09-12T20:00:00-05:00",
                                        kind="music", kind_source="desk_category",
                                        door_id="desk-b", via="B")])
    got = union([a, b], timezone=TZ, timezone_id=TZ_ID)
    assert got.total == 1
    assert got.rows[0].kind == "music" and got.rows[0].kind_source == "desk_category"


def test_a_within_desk_collapse_is_reported_not_silent():
    """The rule applies to every pair, so it can collapse two rows on ONE desk.
    That makes this table's per-desk count differ from desk_coverage's, and an
    unexplained difference is a defect."""
    twice = _fake_walk("desk-a", "A", [
        _row("Shape Town Brass", when="2026-09-12T20:00:00-05:00",
             listing_url="https://desk.example/a"),
        _row("Shape Town Brass", when="2026-09-12T20:00:00-05:00",
             listing_url="https://desk.example/b")])
    got = union([twice], timezone=TZ, timezone_id=TZ_ID)
    assert got.total == 1
    assert len(got.within_desk_merges) == 1


# --------------------------------------------------------------------------
# 403 is not a zero list
# --------------------------------------------------------------------------

def test_a_blocked_desk_is_unreadable_never_empty():
    live = _fake_walk("desk-a", "Austin Chronicle",
                      [_row("Alpha", when="2026-09-12T20:00:00-05:00")])
    shut = _fake_walk("desk-b", "Do512", [], blocked="wall on contact — HTTP 403",
                      stopped="blocked")
    got = union([live, shut], timezone=TZ, timezone_id=TZ_ID, mode="LIVE")
    assert got.all_readable is False
    board = board_table(got)
    assert "403 is not a zero list" in board
    assert "unknown" in board
    # The readable desk's rows are never presented as that desk's exclusive
    # list, because nobody read the other one.
    assert "| Austin Chronicle only | 0 |" not in board
    assert "| Do512 only | 0 |" not in board
    # Evaluator r2 (openai/attacker-smuggle, PR #226): the buckets said
    # `unknown` while the TOTAL still printed a bold exact number beside them,
    # which reads as the complete cross-desk count. The word "floor" in a note
    # does not undo a number that looks measured.
    assert "| **unique total** | **at least 1** |" in board
    assert "| **unique total** | **1** |" not in board
    assert "UNREADABLE" in desk_table(got)


def test_a_bucket_states_no_bound_when_every_desk_stopped_short():
    """Both desks partial: the other's unread pages can take rows OUT of this
    bucket and this desk's own can put new ones IN, so neither "at most" nor
    "at least" is true of it."""
    a = _fake_walk("desk-a", "A", [_row("Alpha", when="2026-09-12T20:00:00-05:00")],
                   stopped="next_control_not_a_link")
    b = _fake_walk("desk-b", "B", [_row("Beta", when="2026-09-12T20:00:00-05:00",
                                        door_id="desk-b", via="B")],
                   stopped="next_control_not_a_link")
    board = board_table(union([a, b], timezone=TZ, timezone_id=TZ_ID))
    assert "| A only | **1 so far** |" in board
    assert "| B only | **1 so far** |" in board
    assert "at most" not in board
    # The two-sided buckets are still floors, and still print as floors.
    assert "| both | **at least** 0 |" in board
    assert "| **unique total** | **at least 2** |" in board


def test_an_only_bucket_never_looks_exact_while_another_desk_is_partial(one):
    """Evaluator finding (openai/absence-only, PR #226): "X only" is a claim
    about the OTHER desk's WHOLE list. The Do512 fixture stops at a Load More
    button, so "Chronicle only" can still shrink as those pages are read — an
    exact-looking count there overstates one desk's exclusive coverage."""
    board = board_table(one)
    assert "| Austin Chronicle only | **at most** 16 |" in board
    assert "| Austin Chronicle only | 16 |" not in board
    # Do512 is the partial one and the Chronicle was read to the end: nothing
    # left to read can claim its rows, so its own count can only grow.
    assert "| Do512 only | **at least** 15 |" in board
    assert "| both | **at least** 1 |" in board
    assert "at least 32" in board


def test_every_bucket_is_exact_once_both_desks_are_exhausted():
    a = _fake_walk("desk-a", "A", [_row("Alpha", when="2026-09-12T20:00:00-05:00")])
    b = _fake_walk("desk-b", "B", [_row("Beta", when="2026-09-12T20:00:00-05:00",
                                        door_id="desk-b", via="B")])
    board = board_table(union([a, b], timezone=TZ, timezone_id=TZ_ID))
    assert "| A only | 1 |" in board and "| B only | 1 |" in board
    assert "at most" not in board and "at least" not in board


def test_a_partial_walk_is_a_floor(one):
    """The Do512 fixture ends on a Load More button. Its list continues, so no
    count here may be presented as the desk's whole output."""
    assert one.any_floor is True
    assert "FLOOR" in board_table(one)


# --------------------------------------------------------------------------
# The tables a founder actually reads
# --------------------------------------------------------------------------

def test_every_table_row_has_the_columns_it_declares(one):
    """A key carrying a markdown pipe splits its row silently, and the founder
    reads a table with the wrong number of columns. Pinned per table."""
    for table in (union_table(one), desk_table(one), board_table(one),
                  held_apart_table(one), near_miss_table(one)):
        lines = [ln for ln in table.splitlines() if ln.startswith("|")]
        if not lines:
            continue
        width = lines[0].count("|") - lines[0].count("\\|")
        for line in lines:
            assert line.count("|") - line.count("\\|") == width, line


def test_the_table_states_via_kind_and_dated_for_every_row(one):
    body = [ln for ln in union_table(one).splitlines()
            if ln.startswith("| ") and not ln.startswith("| # |")]
    assert len(body) == one.total
    for line in body:
        assert ("Austin Chronicle" in line) or ("Do512" in line)
        assert "`" in line                       # the kind, in code ticks
        assert ("| yes |" in line) or ("| **no** |" in line)


def test_near_misses_are_reported_and_never_merged():
    a = _fake_walk("desk-a", "A", [_row("Quartet Night",
                                        when="2026-09-12T20:00:00-05:00")])
    b = _fake_walk("desk-b", "B", [_row("An Evening of Strings",
                                        when="2026-09-12T20:00:00-05:00",
                                        door_id="desk-b", via="B")])
    got = union([a, b], timezone=TZ, timezone_id=TZ_ID)
    assert got.total == 2, "a shared night and place is two of three parts"
    assert len(near_misses(got)) == 1


def test_the_fixture_union_has_no_near_misses(one):
    assert near_misses(one) == []


# --------------------------------------------------------------------------
# Fail loudly
# --------------------------------------------------------------------------

def test_no_timezone_raises_rather_than_assuming_a_home_town():
    a = _fake_walk("desk-a", "A", [_row("Alpha", when="2026-09-12T20:00:00-05:00")])
    with pytest.raises(DeskUnionError):
        union([a], timezone=None, timezone_id="")


def test_an_empty_union_raises():
    with pytest.raises(DeskUnionError):
        union([], timezone=TZ, timezone_id=TZ_ID)


# --------------------------------------------------------------------------
# The pack states the clock — code does not
# --------------------------------------------------------------------------

def test_the_pack_states_this_locales_timezone():
    assert lp.load_pack(CAPCOG).timezone == TZ_ID


def test_a_half_stated_timezone_raises(tmp_path):
    raw = json.loads(open(os.path.join(REPO, "sources", "locale_packs",
                                       f"{CAPCOG}.json"), encoding="utf-8").read())
    raw["locale"]["timezone"] = ""
    (tmp_path / f"{CAPCOG}.json").write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(lp.LocalePackError):
        lp.load_pack(CAPCOG, packs_dir=str(tmp_path))


def test_a_pack_may_state_no_timezone_at_all(tmp_path):
    """Optional in the pack, required by the caller that needs it: an unmapped
    locale still loads, and it is `union()` that refuses to guess."""
    raw = json.loads(open(os.path.join(REPO, "sources", "locale_packs",
                                       f"{CAPCOG}.json"), encoding="utf-8").read())
    raw["locale"].pop("timezone", None)
    (tmp_path / f"{CAPCOG}.json").write_text(json.dumps(raw), encoding="utf-8")
    assert lp.load_pack(CAPCOG, packs_dir=str(tmp_path)).timezone is None


# --------------------------------------------------------------------------
# The tool
# --------------------------------------------------------------------------

def test_the_tool_prints_the_five_tables_and_labels_the_mode(capsys):
    assert tool.main([]) == 0
    out = capsys.readouterr().out
    for heading in ("## 1. Desks", "## 2. Happenings", "## 3. Board",
                    "## 4. Held apart", "## 5. Near misses",
                    "## Next doors we still miss"):
        assert heading in out
    assert "FIXTURE walk" in out and "FIXTURE run" in out
    assert "wrote nothing" in out


def test_the_tool_names_next_doors_without_fetching_them(capsys):
    assert tool.main([]) == 0
    out = capsys.readouterr().out
    assert "Nothing above was fetched" in out
    # The two desks this run DID open are not on the list of what we still miss.
    tail = out.split("## Next doors we still miss", 1)[1].split("## Limits", 1)[0]
    assert CHRONICLE not in tail and DO512 not in tail
    # Walls and copy farms are named as never-open, not as a gap to close.
    assert "facebook-events" in tail and "do not log in" in tail.lower()


def test_an_unknown_door_is_refused(capsys):
    assert tool.main(["--door", "no-such-desk"]) == 2
    assert "no door" in capsys.readouterr().err
