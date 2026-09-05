"""The desks' rows become candidates — and only what the desks stated.

`worker/locale/desk_publish.py` is the seam between a walk that reads and a
catalog that publishes, so what it decides is what a friend eventually sees.
These tests pin the five rules the module's docstring states, and each one is
here because getting it wrong puts something false, something duplicated, or
something fixture-shaped on the live site.

Hermetic: no network, no database, no clock. The walks are built in-process
from the committed fixtures (a page someone already fetched) or from rows
constructed here; the three DB seams are injected as plain functions.
"""
from __future__ import annotations

import dataclasses
import importlib.util
import os

import pytest
from zoneinfo import ZoneInfo

from worker.locale import pack as lp
from worker.locale.desk_read import Happening
from worker.locale.desk_publish import (
    DESK_KEY,
    list_page_index,
    DeskPublishError,
    DeskRegistration,
    contradicts,
    drift,
    ingest_key,
    plan,
    plan_digest,
    refuse_fixture_write,
    registration_for,
    write_for,
)
from worker.locale.desk_union import union
from worker.locale.desk_walk import DeskWalk, PageVisit
from worker.locale.kind_map import map_for_door

CAPCOG = "us-tx-capcog"
CHRONICLE = "austin-chronicle-eventsearch"
DO512 = "do512-today"
TZ_ID = "America/Chicago"
TZ = ZoneInfo(TZ_ID)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_tool(name):
    spec = importlib.util.spec_from_file_location(
        f"_tool_{name}", os.path.join(ROOT, "tools", f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


coverage_tool = _load_tool("desk_coverage")
ingest_tool = _load_tool("desk_ingest")


# --------------------------------------------------------------------------
# Builders
# --------------------------------------------------------------------------

def _row(title, *, when=None, when_precision=None, place="Shape Hall",
         via="Austin Chronicle", door_id=CHRONICLE, listing_url=None,
         when_text=None, kind="other"):
    if when and when_precision is None:
        when_precision = "date" if len(when) == 10 else "datetime"
    return Happening(
        title=title, when=when, when_text=when_text,
        when_precision=when_precision, place_text=place, via=via, kind=kind,
        door_id=door_id, door_type="local_desk", locale_id=CAPCOG,
        source_url="https://desk.example/page", listing_url=listing_url)


def _walk(door_id, via, rows, *, blocked=None, stopped="no_next_link"):
    pages = [PageVisit(n=1, url="https://desk.example/", status=200,
                       rows_seen=len(rows), new_rows=len(rows))]
    if blocked:
        pages = [PageVisit(n=1, url="https://desk.example/", status=403,
                           blocked_reason=blocked)]
    return DeskWalk(door_id=door_id, door_type="local_desk", via=via,
                    start_url="https://desk.example/", pages=pages,
                    rows=list(rows), stopped_because=stopped)


def _union(*walks, mode="LIVE"):
    return union(list(walks), timezone=TZ, timezone_id=TZ_ID, mode=mode)


REGS = {
    "Austin Chronicle": DeskRegistration(
        door_id=CHRONICLE, via="Austin Chronicle",
        source_name="Austin Chronicle Events", source_class="local_media",
        base_url="https://www.austinchronicle.com/events/", catalog_id="austin_chronicle"),
    "Do512": DeskRegistration(
        door_id=DO512, via="Do512", source_name="Do512",
        source_class="local_media", base_url="https://do512.com/",
        catalog_id="do512"),
}


@pytest.fixture(scope="module")
def doors():
    return {d.door_id: d for d in lp.hunt(CAPCOG)}


@pytest.fixture(scope="module")
def catalog():
    import json
    with open(os.path.join(ROOT, "sources", "master_sources_catalog_120.json"),
              encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# The label — read from the committed catalog, or refuse to write
# --------------------------------------------------------------------------

def test_each_founder_named_desk_resolves_to_its_catalog_row(doors, catalog):
    """The founder asked for the source to be LABELLED. The label is the
    registry's own name because that is the string promote.py matches the
    `source` table on — the pack's `via` ("Austin Chronicle") would match
    nothing and publish a NULL label.
    """
    chronicle = registration_for(doors[CHRONICLE], catalog)
    assert chronicle.source_name == "Austin Chronicle Events"
    do512 = registration_for(doors[DO512], catalog)
    assert do512.source_name == "Do512"


def test_both_desks_carry_a_class_the_gate_promotes_on_one_source(doors, catalog):
    """"Do not require a second desk to publish" needs no gate change: both
    desks are `local_media`, which worker/gating.py has treated as an anchor
    since the founder's 2026-08-05 ruling. If a catalog edit ever moved them
    out of that class, single-desk rows would silently start holding — this
    test is what makes that loud.
    """
    from worker.gating import is_first_party
    for door_id in (CHRONICLE, DO512):
        reg = registration_for(doors[door_id], catalog)
        assert is_first_party(reg.source_class), (
            f"{reg.source_name} is class {reg.source_class!r}, which is not an "
            f"anchor — its rows would wait for a second desk")


def test_a_door_on_a_subdomain_still_matches_its_publisher(doors, catalog):
    """The Chronicle's calendar lives on `calendar.austinchronicle.com` while
    the catalog row says `www.austinchronicle.com`. An exact-host match would
    refuse the founder's own primary desk.
    """
    door = doors[CHRONICLE]
    assert "calendar.austinchronicle.com" in door.url
    assert registration_for(door, catalog).catalog_id == "austin_chronicle"


def test_a_lookalike_domain_is_not_the_publisher(doors):
    """`notaustinchronicle.com` ends with `austinchronicle.com` as a STRING.
    Matching on that would print somebody else's masthead on our listings.
    """
    door = doors[CHRONICLE]
    with pytest.raises(DeskPublishError):
        registration_for(door, [{"id": "x", "name": "Not The Chronicle",
                                 "category": "blog",
                                 "base_url": "https://notaustinchronicle.com/"}])


def test_an_unregistered_door_refuses_rather_than_publishing_unlabelled(doors):
    with pytest.raises(DeskPublishError) as exc:
        registration_for(doors[DO512], [])
    assert "LABELLED" in str(exc.value)


def test_two_catalog_rows_claiming_one_door_refuse_rather_than_guess(doors):
    twins = [{"id": "a", "name": "A", "category": "local_media",
              "base_url": "https://do512.com/"},
             {"id": "b", "name": "B", "category": "blog",
              "base_url": "https://do512.com/events/"}]
    with pytest.raises(DeskPublishError) as exc:
        registration_for(doors[DO512], twins)
    assert "guess" in str(exc.value)


# --------------------------------------------------------------------------
# The key — one happening, one row, across desks AND across runs
# --------------------------------------------------------------------------

def test_one_show_on_two_desks_is_one_write_with_two_evidence_rows():
    """The founder's whole reason for a key: a second desk must widen the
    catalog, never double it.
    """
    when = "2026-09-12T21:30:00-05:00"
    one = _union(
        _walk(CHRONICLE, "Austin Chronicle",
              [_row("Shape Town Brass", when=when, place="The Fixture Room")]),
        _walk(DO512, "Do512",
              [_row("Shape Town Brass", when=when, place="The Fixture Room",
                    via="Do512", door_id=DO512)]))
    writes = plan(one, REGS)
    assert len(writes) == 1
    assert writes[0].vias == ("Austin Chronicle", "Do512")
    assert [e.source_name for e in writes[0].evidence] == [
        "Austin Chronicle Events", "Do512"]


def test_a_single_desk_row_is_written_and_labelled_not_held_back():
    """Founder Must-do: "Single-source rows stay and are labelled. Do not
    require a second desk to publish."
    """
    one = _union(_walk(CHRONICLE, "Austin Chronicle",
                       [_row("Solo Listing", when="2026-09-12T20:00:00-05:00")]))
    writes = plan(one, REGS)
    assert len(writes) == 1
    assert writes[0].single_desk
    assert writes[0].source_name == "Austin Chronicle Events"
    assert writes[0].source_class == "local_media"


def test_the_key_of_a_keyable_row_is_the_founders_own_rule():
    one = _union(_walk(CHRONICLE, "Austin Chronicle",
                       [_row("Night Music", when="2026-09-12T20:00:00-05:00",
                             place="The Bright Room")]))
    assert ingest_key(one.rows[0]) == "2026-09-12~bright room~night music"


def test_an_unkeyable_rows_key_does_not_move_when_the_desk_reorders():
    """THE re-run defect. `desk_union` gives an unkeyable row a desk-local key
    containing its ORDINAL in the walk, which is a position in a list that
    reorders every night. Keyed on that, tomorrow's walk writes a second copy
    of the same undated listing, and the catalog grows a duplicate a day.
    """
    undated = _row("Chapbook Swap", place="Back room, address not printed")
    today = _union(_walk(DO512, "Do512", [undated]))
    tomorrow = _union(_walk(DO512, "Do512", [
        _row("Something Else", when="2026-09-13T20:00:00-05:00", place="Elsewhere"),
        undated]))
    same = [r for r in tomorrow.rows if r.title == "Chapbook Swap"][0]
    assert ingest_key(today.rows[0]) == ingest_key(same)
    assert "#" not in ingest_key(same)


def test_an_unkeyable_row_that_stated_its_own_address_is_keyed_on_it():
    one = _union(_walk(DO512, "Do512", [
        _row("Story Circle", place="Riverside Lawn", via="Do512", door_id=DO512,
             listing_url="https://do512.com/events/story-circle")]))
    assert ingest_key(one.rows[0]) == "url:https://do512.com/events/story-circle"


# --------------------------------------------------------------------------
# The clock — only what a desk stated
# --------------------------------------------------------------------------

def test_a_stated_time_is_published_as_the_start():
    one = _union(_walk(CHRONICLE, "Austin Chronicle",
                       [_row("Late Set", when="2026-09-13T00:30:00-05:00")]))
    w = write_for(one.rows[0], REGS, mode="LIVE")
    assert w.start_time == "2026-09-13T00:30:00-05:00"
    assert w.clock_hole is None


def test_a_date_with_no_time_publishes_with_a_null_start_never_midnight():
    """A desk that printed "Sun., Sept. 13" stated a night. Writing 00:00 would
    invent the one field this pipeline exists to be honest about, and would put
    every such row at the top of a feed sorted by time.
    """
    one = _union(_walk(CHRONICLE, "Austin Chronicle",
                       [_row("Farm Stand", when="2026-09-13", when_text="Sun., Sept. 13")]))
    w = write_for(one.rows[0], REGS, mode="LIVE")
    assert w.start_time is None
    assert w.clock_hole == "the desk stated a night, not a time"
    assert w.extracted[DESK_KEY]["night"] == "2026-09-13"


def test_two_desks_disagreeing_on_the_time_publish_the_row_with_a_hole():
    """ONE-LIVE-TRUST.md: a disagreement about a FIELD is a hole on that field,
    never a reason to withhold the listing and never a tiebreak — neither desk
    is the venue. Both claims are kept so an audit can see the conflict.
    """
    one = _union(
        _walk(CHRONICLE, "Austin Chronicle",
              [_row("Double Bill", when="2026-09-12T20:00:00-05:00", place="The Fixture Room")]),
        _walk(DO512, "Do512",
              [_row("Double Bill", when="2026-09-12T21:30:00-05:00",
                    place="The Fixture Room", via="Do512", door_id=DO512)]))
    w = write_for(one.rows[0], REGS, mode="LIVE")
    assert w.start_time is None
    assert "different times" in w.clock_hole
    assert w.extracted[DESK_KEY]["clocks_stated"] == [
        "2026-09-12T20:00:00-05:00", "2026-09-12T21:30:00-05:00"]


def test_two_desks_stating_the_same_clock_is_one_claim_not_a_conflict():
    when = "2026-09-12T21:30:00-05:00"
    one = _union(
        _walk(CHRONICLE, "Austin Chronicle", [_row("Brass", when=when, place="Room")]),
        _walk(DO512, "Do512", [_row("Brass", when=when, place="Room",
                                    via="Do512", door_id=DO512)]))
    w = write_for(one.rows[0], REGS, mode="LIVE")
    assert w.start_time == when
    assert w.clock_hole is None


# --------------------------------------------------------------------------
# No field is invented to fill a column
# --------------------------------------------------------------------------

def test_nothing_is_invented_to_fill_a_column():
    one = _union(_walk(CHRONICLE, "Austin Chronicle",
                       [_row("A Show", when="2026-09-12T20:00:00-05:00",
                             listing_url="https://desk.example/Events/a-show")]))
    w = write_for(one.rows[0], REGS, mode="LIVE")
    # No artists: the performer this module could derive is a de-dup heuristic
    # over a title, and minting artist entities from it puts a guess in the graph.
    assert w.extracted["artist_names"] == []
    # No city: these desks name a venue, not a city. The publish seam applies
    # its own default rather than this module asserting one.
    assert w.extracted["city"] is None
    # A listing page is not a ticket.
    assert w.extracted["ticket_link"] is None
    # The row's own address IS its identity (worker/identity.py reads this key).
    assert w.extracted["listing_url"] == "https://desk.example/Events/a-show"


def test_the_published_title_and_place_are_the_desks_own_words():
    one = _union(_walk(DO512, "Do512",
                       [_row("Gallery Walk: East Side", when="2026-09-16T18:00:00-05:00",
                             place="East Side blocks", via="Do512", door_id=DO512)]))
    w = write_for(one.rows[0], REGS, mode="LIVE")
    assert w.extracted["title"] == "Gallery Walk: East Side"
    assert w.extracted["venue_name"] == "East Side blocks"


def test_every_write_records_the_desks_that_carried_it():
    one = _union(_walk(DO512, "Do512",
                       [_row("Solo", when="2026-09-16T18:00:00-05:00",
                             via="Do512", door_id=DO512)]))
    note = write_for(one.rows[0], REGS, mode="LIVE").extracted[DESK_KEY]
    assert note["vias"] == ["Do512"]
    assert note["doors"] == [DO512]
    assert note["walk_mode"] == "LIVE"


# --------------------------------------------------------------------------
# Fixtures never reach a database
# --------------------------------------------------------------------------

def test_a_fixture_union_is_refused_at_the_write_seam():
    """Founder Must-not: "Do not ship fixture titles to production." The
    committed fixtures say "Fixture Quartet at the Shape Hall"; a catalog
    holding that is worse than an empty one.
    """
    one = _union(_walk(CHRONICLE, "Austin Chronicle", [_row("Fixture Quartet")]),
                 mode="FIXTURE")
    with pytest.raises(DeskPublishError) as exc:
        refuse_fixture_write(one)
    assert "fixture" in str(exc.value).lower()


def test_a_live_union_passes_the_write_seam():
    """The refusal must be about the MODE, not about writing at all — a guard
    that also blocked live walks would be a guard against the ticket.
    """
    one = _union(_walk(CHRONICLE, "Austin Chronicle",
                       [_row("Real Show", when="2026-09-12T20:00:00-05:00")]))
    assert refuse_fixture_write(one) is None
    assert plan(one, REGS), "a live union still plans its rows"


def test_the_cli_refuses_write_without_real(capsys):
    assert ingest_tool.main(["--write"]) == 2
    assert "requires --real" in capsys.readouterr().err


# --------------------------------------------------------------------------
# A blocked desk is unknown, never empty
# --------------------------------------------------------------------------

def test_a_blocked_desk_writes_nothing_and_deletes_nothing():
    one = _union(
        _walk(CHRONICLE, "Austin Chronicle",
              [_row("Readable Show", when="2026-09-12T20:00:00-05:00")]),
        _walk(DO512, "Do512", [], blocked="403", stopped="blocked"))
    writes = plan(one, REGS)
    assert [w.title for w in writes] == ["Readable Show"]
    blocked = [d for d in one.desks if d.door_id == DO512][0]
    assert not blocked.readable


# --------------------------------------------------------------------------
# The write loop — every row lands in exactly one bucket
# --------------------------------------------------------------------------

def _writes(n=3):
    rows = [_row(f"Show {i}", when=f"2026-09-1{i}T20:00:00-05:00", place=f"Place {i}")
            for i in range(1, n + 1)]
    return plan(_union(_walk(CHRONICLE, "Austin Chronicle", rows)), REGS)


def test_a_key_already_in_the_store_is_skipped_not_written_again():
    writes = _writes(2)
    # The 4th element is the desk's stored statement — same as the fresh one
    # here, so this is a true re-run and not drift.
    seen = {writes[0].ingest_key: (
        "cand-1", "promoted", "event-1",
        writes[0].extracted[DESK_KEY]["statement"])}
    calls = []
    result = ingest_tool.ingest(
        writes, seen=seen,
        create=lambda **kw: calls.append(kw) or "cand-new",
        add_evidence=lambda *a: None,
        promote=lambda cid: "event-new")
    assert len(result["skipped"]) == 1
    assert len(result["promoted"]) == 1
    assert len(calls) == 1, "the row already in the store must not be re-created"


def test_a_gate_hold_is_reported_never_swallowed():
    writes = _writes(1)

    def refuse(cid):
        raise ValueError("promotion refused: trust gate did not PASS (hold: weak)")

    result = ingest_tool.ingest(
        writes, seen={}, create=lambda **kw: "cand-1",
        add_evidence=lambda *a: None, promote=refuse)
    assert len(result["held"]) == 1
    assert not result["promoted"]
    assert "trust gate" in result["held"][0][1]


def test_a_failed_write_is_reported_and_does_not_stop_the_rest():
    writes = _writes(3)
    made = []

    def create(**kw):
        if kw["extracted"]["title"] == "Show 2":
            raise RuntimeError("connection lost")
        made.append(kw["extracted"]["title"])
        return f"cand-{len(made)}"

    result = ingest_tool.ingest(
        writes, seen={}, create=create, add_evidence=lambda *a: None,
        promote=lambda cid: f"event-{cid}")
    assert len(result["promoted"]) == 2
    assert len(result["failed"]) == 1
    assert made == ["Show 1", "Show 3"]


def test_every_planned_row_lands_in_exactly_one_bucket():
    """Cardinality: a row that vanished between the plan and the report would
    be a listing we believe we published and did not.
    """
    writes = _writes(4)
    seen = {writes[3].ingest_key: (
        "c", "needs_review", None,
        writes[3].extracted[DESK_KEY]["statement"])}
    n = [0]

    def promote(cid):
        n[0] += 1
        if n[0] == 1:
            raise ValueError("Already published: this venue/minute/title")
        return "event"

    result = ingest_tool.ingest(
        writes, seen=seen, create=lambda **kw: "cand",
        add_evidence=lambda *a: None, promote=promote)
    assert sum(len(result[b]) for b in ingest_tool.ROW_BUCKETS) == len(writes)


# --------------------------------------------------------------------------
# The committed fixtures, end to end
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def fixture_union(doors):
    from worker.locale.desk_walk import walk as run_walk
    walks = []
    for door_id in (CHRONICLE, DO512):
        fetch, start, _ = coverage_tool.fixture_fetcher(door_id)
        walks.append(run_walk(doors[door_id], fetch, start_url=start,
                              kind_map=map_for_door(door_id)))
    return union(walks, timezone=TZ, timezone_id=TZ_ID, mode="FIXTURE")


def test_no_union_row_is_dropped_on_the_way_to_the_write_plan(fixture_union):
    writes = plan(fixture_union, REGS)
    assert len(writes) == fixture_union.total
    assert len({w.ingest_key for w in writes}) == len(writes), "keys must be unique"


def test_the_digest_adds_up(fixture_union):
    writes = plan(fixture_union, REGS)
    d = plan_digest(writes)
    assert d["timed"] + d["clock_holes"] == d["rows"]
    assert d["single_desk"] + d["multi_desk"] == d["rows"]


def test_the_counts_table_reads_as_a_delta():
    table = ingest_tool.counts_table(
        {"events": 1, "tonight_12h": 1, "tonight_168h": 1},
        {"events": 26, "tonight_12h": 4, "tonight_168h": 25},
        city="Austin", hours=168)
    assert "| 1 | 26 | +25 |" in table
    assert table.count("\n") == 4, "header, rule, and one row per surface"


# --------------------------------------------------------------------------
# The allowlist entry this tool holds in tools/trust_gate.py
# --------------------------------------------------------------------------

def test_the_ingest_cli_publishes_only_through_the_gate():
    """`tools/desk_ingest.py` is on trust_gate's promote allowlist, which is a
    widening of the surface that may reach the publish step. This is the
    compensation, and it is narrower than the hole: the tool may call
    `promote_candidate` (which re-runs the FULL trust gate on every row) and
    NOTHING else on that path. If it ever grows its own gate call, its own
    `insert into event`, or its own confidence decision, this fails — the
    allowlist entry would then be covering something it was never argued for.
    """
    import ast

    source = open(os.path.join(ROOT, "tools", "desk_ingest.py"), encoding="utf-8").read()
    tree = ast.parse(source)

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("worker."):
            imported.update(f"{node.module}.{a.name}" for a in node.names)
        elif isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)

    assert imported & {"worker.promote.promote_candidate"}, (
        "the tool must publish through promote_candidate, the seam that "
        "re-runs the whole gate")
    # NARROWED, deliberately, at PR #229 r2. `mark_event_disputed` is now
    # imported and that is not a hole in this guard: it can move a published
    # row to exactly ONE state — `disputed`, the shown-never-hidden state the
    # 4-state model reserves for "our evidence no longer agrees with itself" —
    # and it is what stops a row from reading `confirmed` after its own desk
    # contradicts it. `set_event_confidence` stays forbidden because it takes
    # the state as an ARGUMENT, so a walker holding it could raise a row to
    # `confirmed`; that direction is the publish step's alone. The rest of the
    # list is unchanged: nothing here may re-decide the gate.
    forbidden = {
        "worker.promote.set_event_confidence",
        "worker.promote.assert_promotable",
        "worker.gating.multi_confirm_gate",
        "worker.trust_gate3.evaluate_gate",
        "worker.confidence.derive_confidence",
    }
    assert not (imported & forbidden), (
        f"the ingest CLI reached past promote_candidate: {sorted(imported & forbidden)}. "
        f"Re-deciding the gate, or setting an ARBITRARY confidence, is the "
        f"publish step's job — not a walker's.")
    assert "worker.promote.set_event_confidence" not in imported, (
        "a walker that can set any confidence can promote a row to confirmed "
        "without the gate; only the one-way `mark_event_disputed` is allowed")
    assert "insert into event" not in source.lower(), (
        "the ingest CLI must never write the canonical event table itself")


def test_a_row_whose_evidence_failed_is_not_promoted_on_a_partial_record():
    """Found by red class swallowed-corrupt-data while answering it.

    The first version reported an evidence failure and then promoted anyway.
    Two harms: the gate reads its source classes FROM those rows, so the
    candidate would be judged (and published) on a record we already knew was
    incomplete; and the row landed in `failed` and again in `promoted`, so the
    printed buckets over-counted the plan they claim to account for.
    """
    writes = _writes(2)
    promoted = []

    def add_evidence(cid, *a):
        raise RuntimeError("evidence write lost")

    result = ingest_tool.ingest(
        writes, seen={}, create=lambda **kw: "cand",
        add_evidence=add_evidence,
        promote=lambda cid: promoted.append(cid) or "event")
    assert promoted == [], "a candidate with incomplete evidence must not publish"
    assert len(result["failed"]) == 2
    assert sum(len(result[b]) for b in ingest_tool.ROW_BUCKETS) == len(writes), (
        "every planned row lands in exactly ONE bucket")
    assert "NOT promoted" in result["failed"][0][1]


# --------------------------------------------------------------------------
# A re-run asks TWO questions (evaluator, PR #229 r1 — openai/absence-only)
# --------------------------------------------------------------------------

def _stmt(title="Brass Union", when="2026-09-12T20:00:00-05:00", place="The Mercury",
          via="Austin Chronicle", door_id=CHRONICLE, url=None):
    one = _union(_walk(door_id, via, [
        _row(title, when=when, place=place, via=via, door_id=door_id,
             listing_url=url)]))
    return write_for(one.rows[0], REGS, mode="LIVE").extracted[DESK_KEY]["statement"]


def test_every_write_records_what_the_desk_said_not_only_that_it_said_it():
    """The key answers "is this the same happening?" and nothing else. The
    statement is what lets a re-run ask the second question.
    """
    s = _stmt()
    assert s["title"] == "Brass Union"
    assert s["place"] == "The Mercury"
    assert s["night"] == "2026-09-12"
    assert s["clocks"] == ["2026-09-12T20:00:00-05:00"]
    assert s["vias"] == ["Austin Chronicle"]


def test_a_desk_correcting_the_time_on_the_same_night_is_drift_not_a_re_run():
    """THE BLOCKING FINDING, as a test. A corrected time keys IDENTICALLY —
    same night, same place, same title — so a re-run that skips on the key
    alone leaves 8pm published under this desk's name after the desk moved the
    show to 9:30pm. That is a false detail shown to a reader under a trusted
    label, which is the one thing this pipeline exists not to do.
    """
    published = _stmt(when="2026-09-12T20:00:00-05:00")
    corrected = _stmt(when="2026-09-12T21:30:00-05:00")

    one = _union(_walk(CHRONICLE, "Austin Chronicle", [
        _row("Brass Union", when="2026-09-12T20:00:00-05:00", place="The Mercury")]))
    two = _union(_walk(CHRONICLE, "Austin Chronicle", [
        _row("Brass Union", when="2026-09-12T21:30:00-05:00", place="The Mercury")]))
    assert ingest_key(one.rows[0]) == ingest_key(two.rows[0]), (
        "the premise: a re-time on the same night is the SAME key")
    assert drift(published, corrected) == ["clocks"]


def test_a_moved_venue_and_a_renamed_show_are_drift():
    assert drift(_stmt(), _stmt(place="Some Other Room")) == ["place"]
    assert drift(_stmt(), _stmt(title="Brass Union (moved)")) == ["title"]


def test_a_changed_listing_address_is_drift():
    assert drift(_stmt(url="https://d.example/a"),
                 _stmt(url="https://d.example/b")) == ["listing_url"]


def test_a_second_desk_picking_up_a_published_row_is_drift_but_not_a_contradiction():
    """Evaluator, PR #229 r6, and my own earlier test documented the bug: this
    IS drift worth recording (the row has corroboration it did not have), and
    it is NOT a disagreement. Treating it as one marks an already-correct
    listing `disputed` — showing a reader STRONGER agreement as a dispute,
    which is the r2 harm inverted.
    """
    one_desk = _stmt()
    both = _union(
        _walk(CHRONICLE, "Austin Chronicle", [
            _row("Brass Union", when="2026-09-12T20:00:00-05:00", place="The Mercury")]),
        _walk(DO512, "Do512", [
            _row("Brass Union", when="2026-09-12T20:00:00-05:00", place="The Mercury",
                 via="Do512", door_id=DO512)]))
    two_desks = write_for(both.rows[0], REGS, mode="LIVE").extracted[DESK_KEY]["statement"]
    assert drift(one_desk, two_desks) == ["vias"]
    assert contradicts(one_desk, two_desks) == [], (
        "a second desk agreeing is not the first desk changing its mind")


def test_an_unchanged_desk_is_not_drift():
    assert drift(_stmt(), _stmt()) == []


def test_a_row_written_before_statements_existed_is_not_reported_as_changed():
    """Fail-safe direction. Rows already in the store have no statement to
    compare against; inventing a difference from a hole would report EVERY one
    of them as changed on the first run after this ships, which is a false
    alarm on the whole catalog.
    """
    assert drift(None, _stmt()) == []
    assert drift({}, _stmt()) == []


def test_drift_records_the_desks_new_word_and_never_publishes_it():
    """A second listing beside the first is strictly worse for a reader than
    the stale field this row exists to report, so the drift candidate is
    written and NOT promoted. Rewriting the published row is a MUTATION and
    belongs to worker/listing_update.py, the one reviewed seam for it (R-105).
    """
    writes = _writes(1)
    key = writes[0].ingest_key
    stale = dict(writes[0].extracted[DESK_KEY]["statement"])
    stale["clocks"] = ["2026-09-01T01:00:00-05:00"]  # what we published earlier
    seen = {key: ("cand-old", "promoted", "event-old", stale)}
    created, promoted = [], []

    result = ingest_tool.ingest(
        writes, seen=seen,
        create=lambda **kw: created.append(kw) or "cand-new",
        add_evidence=lambda *a: None,
        promote=lambda cid: promoted.append(cid) or "event-new",
        # Injected like every other DB seam: the dispute now runs BEFORE the
        # record (r9), so a test that let it fall through to the real one would
        # be exercising a failed connection, not this branch.
        dispute=lambda eid: "DISPUTED")

    assert len(result["changed"]) == 1, result
    assert not result["skipped"] and not result["promoted"]
    assert promoted == [], "a drift row must never publish a second listing"
    assert len(created) == 1, "the desk's new word is recorded as a candidate"
    assert result["dispute_failures"] == []
    note = created[0]["extracted"][DESK_KEY]
    assert note["supersedes"]["event_id"] == "event-old"
    assert note["supersedes"]["changed"] == ["clocks"]
    assert "event-old" in result["changed"][0][1]
    assert sum(len(result[b]) for b in ingest_tool.ROW_BUCKETS) == len(writes)


def test_an_unchanged_row_still_skips_and_writes_nothing():
    writes = _writes(1)
    key = writes[0].ingest_key
    same = writes[0].extracted[DESK_KEY]["statement"]
    created = []
    result = ingest_tool.ingest(
        writes, seen={key: ("cand-old", "promoted", "event-old", same)},
        create=lambda **kw: created.append(kw) or "c",
        add_evidence=lambda *a: None, promote=lambda cid: "e")
    assert len(result["skipped"]) == 1
    assert created == []


def test_a_superseded_row_is_disputed_not_left_reading_confirmed():
    """Evaluator, PR #229 r2. r1 recorded the desk's correction and left the
    published row reading `confirmed` — so a reader still saw the older detail
    presented as settled. `disputed` is the state for this, and the feed shows
    it rather than hiding the row.
    """
    writes = _writes(1)
    stale = dict(writes[0].extracted[DESK_KEY]["statement"])
    stale["clocks"] = ["2026-09-01T01:00:00-05:00"]
    disputed = []

    result = ingest_tool.ingest(
        writes, seen={writes[0].ingest_key: ("cand-old", "promoted", "event-old", stale)},
        create=lambda **kw: "cand-new", add_evidence=lambda *a: None,
        promote=lambda cid: "never", dispute=lambda eid: disputed.append(eid) or "DISPUTED")
    assert disputed == ["event-old"], "the superseded row must be flagged"
    assert "DISPUTED" in result["changed"][0][1]


def test_a_dispute_that_fails_records_nothing_so_the_next_run_retries():
    """Evaluator, PR #229 r9. `existing_keys` reads the NEWEST statement for a
    key, so a drift candidate written after a FAILED dispute becomes what
    tomorrow's run compares against — no drift is seen, the row is skipped, and
    the published event stays `confirmed` while its desk contradicts it. The
    run even PRINTS "re-run this tool" while that path is dead.

    Disputing first means a failure leaves the store exactly as it was.
    """
    writes = _writes(1)
    stale = dict(writes[0].extracted[DESK_KEY]["statement"])
    stale["clocks"] = ["2026-09-01T01:00:00-05:00"]
    created = []

    def boom(event_id):
        raise RuntimeError("connection lost")

    result = ingest_tool.ingest(
        writes, seen={writes[0].ingest_key: ("c", "promoted", "event-old", stale)},
        create=lambda **kw: created.append(kw) or "cand-new",
        add_evidence=lambda *a: None, promote=lambda cid: "never", dispute=boom)

    assert created == [], (
        "recording the correction would make the next run see no drift and "
        "skip the row it must retry")
    assert not result["changed"]
    assert len(result["failed"]) == 1
    assert "COULD NOT DISPUTE" in result["failed"][0][1]
    assert "NOTHING was recorded" in result["failed"][0][1]
    assert result["dispute_failures"][0][0] == "event-old"
    assert sum(len(result[b]) for b in ingest_tool.ROW_BUCKETS) == len(writes)


# --------------------------------------------------------------------------
# A hole must reach a reader as the hole it actually is
# (evaluator, PR #229 r3 — openai/attacker-smuggle)
# --------------------------------------------------------------------------

def test_a_date_only_row_is_held_rather_than_published_as_date_unknown():
    """THE BLOCKING FINDING. `event` has one clock column, so a date-only row
    can only be published with a NULL start — which the feed renders as "Date
    TBA". That tells a reader we do not know a date the desk GAVE us, under
    that desk's masthead. Manufacturing an absence is the mirror image of
    fabricating a fact, so the row is held instead of published.
    """
    one = _union(_walk(CHRONICLE, "Austin Chronicle",
                       [_row("Farm Stand", when="2026-09-13",
                             when_text="Sun., Sept. 13")]))
    w = write_for(one.rows[0], REGS, mode="LIVE")
    assert w.start_time is None
    assert w.hold_reason and "2026-09-13" in w.hold_reason
    assert not w.clock_disputed
    assert w.extracted[DESK_KEY]["night"] == "2026-09-13", (
        "the night the desk stated is kept on the record even while held")


def test_a_row_with_no_date_at_all_still_publishes_because_tba_is_true():
    """The neighbouring branch, and it must NOT be held: when no desk stated a
    date, "Date TBA" is exactly what we know. Holding it would drop coverage
    for a display that is already honest.
    """
    one = _union(_walk(DO512, "Do512",
                       [_row("Chapbook Swap", place="Back room", via="Do512",
                             door_id=DO512)]))
    w = write_for(one.rows[0], REGS, mode="LIVE")
    assert w.hold_reason is None
    assert w.start_time is None
    assert w.clock_hole == "no desk stated a date for this row"


def test_desks_disagreeing_on_the_time_publish_disputed_not_merely_unknown():
    """A contested clock reaching a reader as a generic TBA beside `confirmed`
    says "nobody told us" when in fact two desks told us different things.
    """
    one = _union(
        _walk(CHRONICLE, "Austin Chronicle",
              [_row("Double Bill", when="2026-09-12T20:00:00-05:00", place="Room")]),
        _walk(DO512, "Do512",
              [_row("Double Bill", when="2026-09-12T21:30:00-05:00", place="Room",
                    via="Do512", door_id=DO512)]))
    w = write_for(one.rows[0], REGS, mode="LIVE")
    assert w.clock_disputed is True
    assert w.hold_reason is None, "existence is not in doubt — only the clock"
    assert w.start_time is None


def test_the_three_holes_are_counted_apart(fixture_union):
    """Cardinality over the branches: held + disputed + true-TBA + timed must
    account for every planned row, or a summary line is describing something
    other than the plan.
    """
    d = plan_digest(plan(fixture_union, REGS))
    true_tba = d["clock_holes"] - d["held"] - d["clock_disputed"]
    assert d["timed"] + d["clock_disputed"] + true_tba + d["held"] == d["rows"]
    assert d["publishable"] + d["held"] == d["rows"]


def test_a_held_row_is_written_but_never_promoted():
    one = _union(_walk(CHRONICLE, "Austin Chronicle",
                       [_row("Farm Stand", when="2026-09-13")]))
    writes = plan(one, REGS)
    promoted, created = [], []
    result = ingest_tool.ingest(
        writes, seen={},
        create=lambda **kw: created.append(kw) or "cand-held",
        add_evidence=lambda *a: None,
        promote=lambda cid: promoted.append(cid) or "event")
    assert len(created) == 1, "a held row is still IN the catalog as a candidate"
    assert promoted == [], "a held row must not publish"
    assert len(result["held"]) == 1
    assert "R-111" in result["held"][0][1]
    assert sum(len(result[b]) for b in ingest_tool.ROW_BUCKETS) == len(writes)


def test_a_contested_clock_is_never_flagged_by_a_SECOND_write():
    """Evaluator, PR #229 r5. Promoting and THEN marking the row disputed
    leaves a window in which a contested listing is public and labelled
    `confirmed`, and a failure in between makes that window permanent. The
    publisher writes `disputed` inside the same transaction as the insert
    (`worker/promote.py`), so this tool must NOT write it again — a second
    answer to the same question is the race, not the fix.
    """
    one = _union(
        _walk(CHRONICLE, "Austin Chronicle",
              [_row("Double Bill", when="2026-09-12T20:00:00-05:00", place="Room")]),
        _walk(DO512, "Do512",
              [_row("Double Bill", when="2026-09-12T21:30:00-05:00", place="Room",
                    via="Do512", door_id=DO512)]))
    disputed = []
    result = ingest_tool.ingest(
        plan(one, REGS), seen={}, create=lambda **kw: "cand",
        add_evidence=lambda *a: None, promote=lambda cid: "event-new",
        dispute=lambda eid: disputed.append(eid) or "DISPUTED")
    assert len(result["promoted"]) == 1
    assert disputed == [], (
        "the contested clock is disputed AT PUBLISH; a post-hoc write here "
        "would re-open the window this invariant exists to close")
    assert "disputed at publish" in result["promoted"][0][1]


# --------------------------------------------------------------------------
# A row left mislabelled fails the RUN (evaluator, PR #229 r4)
# --------------------------------------------------------------------------

def test_a_failed_dispute_on_a_superseded_row_is_recorded_as_a_run_failure():
    """Reporting a failed dispute in the table is not enough. The published row
    is live and reading `confirmed` while its own desk contradicts it, so the
    RUN must not be able to report success over it.
    """
    writes = _writes(1)
    stale = dict(writes[0].extracted[DESK_KEY]["statement"])
    stale["clocks"] = ["2026-09-01T01:00:00-05:00"]

    def boom(event_id):
        raise RuntimeError("connection lost")

    result = ingest_tool.ingest(
        writes, seen={writes[0].ingest_key: ("c", "promoted", "event-old", stale)},
        create=lambda **kw: "cand", add_evidence=lambda *a: None,
        promote=lambda cid: "never", dispute=boom)
    assert len(result["dispute_failures"]) == 1
    event_id, why = result["dispute_failures"][0]
    assert event_id == "event-old"
    assert "COULD NOT DISPUTE" in why and "connection lost" in why
    assert sum(len(result[b]) for b in ingest_tool.ROW_BUCKETS) == len(writes), (
        "the failure list is NOT a row bucket — cardinality is unchanged")
    assert len(result["failed"]) == 1, (
        "the row lands in `failed`, not `changed`: nothing was recorded for it")


def test_a_contested_clock_cannot_fail_a_dispute_because_it_never_makes_one():
    """The r4 failure mode, deleted rather than reported at r5: with the
    dispute written by the publisher, a dispute call that would fail is never
    made for a contested clock, so no window and no failure list entry.
    """
    one = _union(
        _walk(CHRONICLE, "Austin Chronicle",
              [_row("Double Bill", when="2026-09-12T20:00:00-05:00", place="Room")]),
        _walk(DO512, "Do512",
              [_row("Double Bill", when="2026-09-12T21:30:00-05:00", place="Room",
                    via="Do512", door_id=DO512)]))

    def boom(event_id):
        raise RuntimeError("connection lost")

    result = ingest_tool.ingest(
        plan(one, REGS), seen={}, create=lambda **kw: "cand",
        add_evidence=lambda *a: None, promote=lambda cid: "event-new",
        dispute=boom)
    assert len(result["promoted"]) == 1
    assert result["dispute_failures"] == [], (
        "nothing to fail: the contested clock is disputed inside the publish "
        "transaction, not by a second write from here")


def test_a_clean_run_records_no_dispute_failures():
    writes = _writes(2)
    result = ingest_tool.ingest(
        writes, seen={}, create=lambda **kw: "cand",
        add_evidence=lambda *a: None, promote=lambda cid: "event")
    assert result["dispute_failures"] == []
    assert len(result["promoted"]) == 2


# --------------------------------------------------------------------------
# Corroboration is not contradiction (evaluator, PR #229 r6)
# --------------------------------------------------------------------------

def test_corroboration_records_the_desk_but_leaves_the_published_row_alone():
    """The blocking finding as a test: a row published from one desk and later
    carried by a second with identical details must NOT be marked disputed.
    """
    writes = _writes(1)
    stored = dict(writes[0].extracted[DESK_KEY]["statement"])
    stored["vias"] = ["Do512"]          # published from one desk...
    fresh = writes[0].extracted[DESK_KEY]["statement"]
    fresh["vias"] = ["Do512", "Austin Chronicle"]   # ...now carried by two
    disputed, created = [], []

    result = ingest_tool.ingest(
        writes, seen={writes[0].ingest_key: ("c", "promoted", "event-old", stored)},
        create=lambda **kw: created.append(kw) or "cand-new",
        add_evidence=lambda *a: None, promote=lambda cid: "never",
        dispute=lambda eid: disputed.append(eid) or "DISPUTED")

    assert disputed == [], "corroboration must never dispute a correct row"
    assert len(created) == 1, "the second desk's word is still recorded"
    assert len(result["changed"]) == 1
    assert "corroboration, not a contradiction" in result["changed"][0][1]
    assert result["dispute_failures"] == []


def test_a_contradiction_still_disputes():
    """The other side of the same branch — r2's fix must survive r6's."""
    writes = _writes(1)
    stored = dict(writes[0].extracted[DESK_KEY]["statement"])
    stored["clocks"] = ["2026-09-01T01:00:00-05:00"]
    disputed = []

    result = ingest_tool.ingest(
        writes, seen={writes[0].ingest_key: ("c", "promoted", "event-old", stored)},
        create=lambda **kw: "cand-new", add_evidence=lambda *a: None,
        promote=lambda cid: "never",
        dispute=lambda eid: disputed.append(eid) or "DISPUTED")
    assert disputed == ["event-old"]
    assert result["changed"][0][0].extracted[DESK_KEY]["supersedes"]["contradicts"] == ["clocks"]


def test_every_watched_field_is_classified_as_one_or_the_other():
    """Cardinality over the split: a field added to the statement without a
    decision about what its change MEANS would otherwise be silently treated as
    a contradiction (or silently ignored), and both are wrong by default.
    """
    from worker.locale.desk_publish import CONTRADICTING, CORROBORATING, WATCHED
    assert set(CONTRADICTING) | set(CORROBORATING) == set(WATCHED)
    assert not (set(CONTRADICTING) & set(CORROBORATING))


def test_each_contested_clock_claim_names_the_desk_that_stated_it():
    """Evaluator, PR #229 r7. A bare list of instants says "these were claimed"
    and nothing about BY WHOM, so the publisher could only count evidence rows
    and hope they matched. Attribution is what lets it check each claim.
    """
    one = _union(
        _walk(CHRONICLE, "Austin Chronicle",
              [_row("Double Bill", when="2026-09-12T20:00:00-05:00", place="Room")]),
        _walk(DO512, "Do512",
              [_row("Double Bill", when="2026-09-12T21:30:00-05:00", place="Room",
                    via="Do512", door_id=DO512)]))
    claims = write_for(one.rows[0], REGS, mode="LIVE").extracted["start_times"]
    assert claims == [
        {"source": "Austin Chronicle Events", "at": "2026-09-12T20:00:00-05:00"},
        {"source": "Do512", "at": "2026-09-12T21:30:00-05:00"},
    ]
    assert {c["source"] for c in claims} == {r.source_name for r in REGS.values()}, (
        "every claim's source must be a REGISTRY name — the same string the "
        "evidence row is written under, or the publisher cannot match them")


def test_an_uncontested_row_states_no_clock_claims_at_all():
    one = _union(_walk(CHRONICLE, "Austin Chronicle",
                       [_row("Solo", when="2026-09-12T20:00:00-05:00")]))
    assert "start_times" not in write_for(one.rows[0], REGS, mode="LIVE").extracted


def test_one_moment_written_two_ways_is_not_a_contested_clock():
    """Evaluator, PR #229 r8, and this shape is IN the committed fixtures:
    one desk writes `...T01:00:00Z` and the other `...T20:00:00-05:00` for the
    same moment. Compared as strings that is a disagreement; compared as
    instants it is one clock, and treating it as a conflict would throw away a
    time both desks agreed on.
    """
    one = _union(
        _walk(CHRONICLE, "Austin Chronicle",
              [_row("Same Moment", when="2026-09-13T01:00:00Z", place="Room")]),
        _walk(DO512, "Do512",
              [_row("Same Moment", when="2026-09-12T20:00:00-05:00", place="Room",
                    via="Do512", door_id=DO512)]))
    w = write_for(one.rows[0], REGS, mode="LIVE")
    assert not w.clock_disputed, "one instant in two forms is one instant"
    assert w.start_time == "2026-09-13T01:00:00Z", "the first form is kept"
    assert w.clock_hole is None
    assert "start_times" not in w.extracted


def test_genuinely_different_instants_are_still_contested():
    """The other side: the instant comparison must not swallow a real conflict."""
    one = _union(
        _walk(CHRONICLE, "Austin Chronicle",
              [_row("Real Conflict", when="2026-09-13T01:00:00Z", place="Room")]),
        _walk(DO512, "Do512",
              [_row("Real Conflict", when="2026-09-12T21:30:00-05:00", place="Room",
                    via="Do512", door_id=DO512)]))
    assert write_for(one.rows[0], REGS, mode="LIVE").clock_disputed


def test_one_desk_stating_two_times_is_held_not_published_as_a_settled_tba():
    """Evaluator, PR #229 r9. A conflict is a disagreement BETWEEN desks. One
    desk printing two same-night/same-place/same-title rows with different
    times is either self-contradiction or the de-dup key merging two showings —
    and the publisher correctly refuses a same-source contradiction, which
    would leave the row `confirmed` with an empty clock: a settled "Date TBA"
    for a listing whose desk DID state times.
    """
    one = _union(_walk(DO512, "Do512", [
        _row("Twice Tonight", when="2026-09-12T20:00:00-05:00", place="Room",
             via="Do512", door_id=DO512),
        _row("Twice Tonight", when="2026-09-12T22:00:00-05:00", place="Room",
             via="Do512", door_id=DO512)]))
    assert len(one.rows) == 1, "the founder's key merges these into one row"
    w = write_for(one.rows[0], REGS, mode="LIVE")
    assert not w.clock_disputed, "one desk cannot contest itself"
    assert w.hold_reason and "one desk states 2 different times" in w.hold_reason
    assert w.start_time is None

    promoted = []
    result = ingest_tool.ingest(
        plan(one, REGS), seen={}, create=lambda **kw: "cand",
        add_evidence=lambda *a: None,
        promote=lambda cid: promoted.append(cid) or "event")
    assert promoted == [], "it must not reach the feed as a confirmed TBA"
    assert len(result["held"]) == 1


# --------------------------------------------------------------------------
# A row whose identity is the desk's own front door is not a happening
# --------------------------------------------------------------------------
#
# These pin the defect the 2026-09-05 master dry run printed from a GitHub
# runner (run 33986288662): the Chronicle walk read 40 pages and produced ONE
# row, keyed `url:https://www.austinchronicle.com`, whose title was ten event
# names glued together and whose place was forty venues glued together, with no
# date — and the plan said `1 publish`. Arming a schedule against that would
# have written a happening nobody is holding, under a real paper's masthead,
# every six hours. The test is on the row's IDENTITY, never on how its text
# looks, because a "does this title look wrong?" heuristic is the generic card
# parser this ticket's Must-not list excludes.

def _front_door_write(listing_url):
    one = _union(_walk(CHRONICLE, "Austin Chronicle", [
        _row("Promoted Events Back To The Ranch Austin Steel Guitar Fest "
             "Barbie Dream Heist Day of Dance",
             place="Butterfly Bar at the Vortex 2307 Manor Rd. East Saengerrunde "
                   "Hall 1607 San Jacinto TexARTS 1110 S RR 620",
             listing_url=listing_url)]))
    return write_for(one.rows[0], REGS, mode="LIVE")


def test_the_papers_bare_front_door_is_held_not_published():
    write = _front_door_write("https://www.austinchronicle.com")
    assert write.hold_reason, "the site root published as a happening"
    assert "front door" in write.hold_reason
    assert "https://www.austinchronicle.com" in write.hold_reason


def test_a_front_door_row_is_still_written_as_a_candidate():
    """HELD is not DROPPED. The row stays auditable in the store and the ops
    queue — the walk's own evidence that a desk gave us no per-listing address —
    and only the PUBLIC step is withheld."""
    write = _front_door_write("https://www.austinchronicle.com")
    assert write.ingest_key and write.evidence
    assert write.source_name == "Austin Chronicle Events"


def test_the_door_the_walk_started_at_is_held():
    """The Chronicle's calendar lives on its own subdomain, so the door the
    walk enters by is neither the bare origin nor the catalog's base_url — a
    row keyed at it would have slipped both other tests."""
    door = "https://calendar.austinchronicle.com/austin/EventSearch?sortType=date&v=g"
    regs = dict(REGS)
    regs["Austin Chronicle"] = dataclasses.replace(regs["Austin Chronicle"],
                                                   door_url=door)
    one = _union(_walk(CHRONICLE, "Austin Chronicle", [
        _row("Everything On This Page",
             listing_url="https://calendar.austinchronicle.com/austin/EventSearch")]))
    write = write_for(one.rows[0], regs, mode="LIVE")
    assert write.hold_reason and "door this walk started at" in write.hold_reason


def test_the_real_door_url_is_carried_from_the_pack_not_typed_here(doors, catalog):
    """The door_url must come from the locale pack the walk actually uses, or
    the check above compares against a string nobody walks."""
    reg = registration_for(doors[CHRONICLE], catalog)
    assert reg.door_url == doors[CHRONICLE].url
    assert reg.door_url.startswith("https://")


def test_the_events_index_itself_is_held():
    """The catalog row's own base_url is the LIST, not anything on it."""
    write = _front_door_write("https://www.austinchronicle.com/events/")
    assert write.hold_reason and "events index" in write.hold_reason


def test_the_index_matches_whatever_trailing_slash_or_query_it_wears():
    for url in ("https://www.austinchronicle.com/events",
                "https://www.austinchronicle.com/events/?page=2",
                "https://austinchronicle.com/events/"):
        assert _front_door_write(url).hold_reason, url


def test_a_real_listing_under_the_same_host_still_publishes():
    """The guard must not cost us a single real row — that would be the
    Coverage Law failure (do not drop rows) answering the fabrication one."""
    one = _union(_walk(CHRONICLE, "Austin Chronicle", [
        _row("Quartet at the Shape Hall", when="2026-09-14T20:00:00",
             listing_url="https://www.austinchronicle.com/events/12345/")]))
    write = write_for(one.rows[0], REGS, mode="LIVE")
    assert write.hold_reason is None
    assert write.start_time


def test_a_front_door_row_is_not_counted_as_publishable():
    one = _union(_walk(CHRONICLE, "Austin Chronicle", [
        _row("Everything On This Page", listing_url="https://www.austinchronicle.com"),
        _row("Quartet at the Shape Hall", when="2026-09-14T20:00:00",
             listing_url="https://www.austinchronicle.com/events/12345/")]))
    digest = plan_digest(plan(one, REGS))
    assert digest["rows"] == 2
    assert digest["held"] == 1
    assert digest["publishable"] == 1


def test_the_front_door_hold_outranks_a_clock_hold():
    """A clock hole is a hole in a real listing. This is not a listing, so the
    reason a person reads has to say THAT, not "no time stated"."""
    one = _union(_walk(CHRONICLE, "Austin Chronicle", [
        _row("Everything On This Page", when="2026-09-14",
             listing_url="https://www.austinchronicle.com")]))
    write = write_for(one.rows[0], REGS, mode="LIVE")
    assert "front door" in (write.hold_reason or "")
    assert "R-111" not in (write.hold_reason or "")


# The evaluator's blocking finding on PR #232 (absence-only lens): the three
# identities above are special cases, and a composite keyed at some OTHER page
# of the same pagination still published. These pin the general invariant — a
# row's identity is never any URL the walk itself read as a list.

def _paginated_walk(rows, *, pages=("https://desk.example/list?p=1",
                                    "https://desk.example/list?p=2",
                                    "https://desk.example/list?p=3")):
    visits = [PageVisit(n=i, url=u, status=200, rows_seen=len(rows),
                        new_rows=len(rows),
                        next_url=(pages[i] if i < len(pages) else None))
              for i, u in enumerate(pages, start=1)]
    return DeskWalk(door_id=CHRONICLE, door_type="local_desk",
                    via="Austin Chronicle", start_url=pages[0], pages=visits,
                    rows=list(rows), stopped_because="no_next_link")


def test_a_row_keyed_at_a_middle_page_of_the_pagination_is_held():
    """Page 2 is neither the origin, nor the catalog index, nor the door."""
    one = _union(_paginated_walk([
        _row("Everything On Page Two",
             listing_url="https://desk.example/list?p=2")]))
    write = plan(one, REGS)[0]
    assert write.hold_reason, "a list page published as a happening"
    assert "READ AS A LIST" in write.hold_reason


def test_the_query_string_cannot_dodge_the_list_page_hold():
    """`?p=2` and `?p=2&v=g` are the same document; identity is host+path."""
    one = _union(_paginated_walk([
        _row("Everything On Page Two",
             listing_url="https://desk.example/list?p=2&v=g")]))
    assert plan(one, REGS)[0].hold_reason


def test_a_next_link_the_walk_followed_counts_as_a_list_page():
    one = _union(_paginated_walk([
        _row("Everything On Page Three",
             listing_url="https://desk.example/list?p=3")]))
    assert plan(one, REGS)[0].hold_reason


def test_a_real_listing_on_a_paginated_desk_still_publishes():
    """The invariant must not cost a single real row (Coverage Law)."""
    one = _union(_paginated_walk([
        _row("Quartet at the Shape Hall", when="2026-09-14T20:00:00",
             listing_url="https://desk.example/event/12345")]))
    write = plan(one, REGS)[0]
    assert write.hold_reason is None
    assert write.start_time


def test_the_product_path_supplies_the_list_pages_not_just_a_careful_caller():
    """`plan()` is the only path `tools/desk_ingest.py` writes through. If it
    stopped passing the index, `write_for`'s default would silently reopen the
    hole — so the coupling is pinned, not trusted."""
    one = _union(_paginated_walk([
        _row("Everything On Page Two",
             listing_url="https://desk.example/list?p=2")]))
    assert plan(one, REGS)[0].hold_reason
    # ...and the index really is derived from the walk, not from the row.
    index = list_page_index(one)
    assert ("desk.example", "/list") in index


def test_a_desk_that_read_nothing_contributes_no_list_pages_and_no_rows():
    one = _union(_walk(DO512, "Do512", [], blocked="403", stopped="wall"))
    assert plan(one, REGS) == []


def test_a_row_with_no_listing_url_is_judged_on_its_other_facts():
    """No URL is not a front door — the desk simply printed no address, which
    the union already keys desk-locally. Holding those would be a silent
    coverage cut."""
    one = _union(_walk(CHRONICLE, "Austin Chronicle", [
        _row("Quartet at the Shape Hall", when="2026-09-14T20:00:00")]))
    assert write_for(one.rows[0], REGS, mode="LIVE").hold_reason is None


# --------------------------------------------------------------------------
# An unreadable desk is a FAILED run
# --------------------------------------------------------------------------
#
# Founder ticket 2026-09-05: "UNREADABLE desk = failed check + ops-visible
# report, never '0 events' and never delete existing rows." Both master dry
# runs (33986288662, 33988204239) recorded `do512-today` at 0 pages read and
# exited GREEN, which is the state these pin shut.

class _Unread:
    def __init__(self, door_id):
        self.door_id = door_id


def test_an_unread_desk_exits_nonzero():
    assert ingest_tool._unreadable_exit([_Unread(DO512)]) == 3


def test_a_clean_run_still_exits_zero():
    assert ingest_tool._unreadable_exit([]) == 0


def test_the_failure_names_the_desk_and_says_nothing_was_deleted(capsys):
    ingest_tool._unreadable_exit([_Unread(DO512), _Unread(CHRONICLE)])
    err = capsys.readouterr().err
    assert DO512 in err and CHRONICLE in err
    assert "UNKNOWN, not absent" in err
    assert "nothing was deleted" in err


def test_both_exits_route_through_one_answer():
    """The dry run and the write must not be able to disagree about whether an
    unread desk is a failure — that is how one of them grows a green path."""
    source = open(os.path.join(ROOT, "tools", "desk_ingest.py"), encoding="utf-8").read()
    assert source.count("return _unreadable_exit(unreadable)") == 2
    body = source.split("def main(")[1].split("\ndef ")[0]
    assert "    return 0\n" not in body, (
        "main() grew a bare `return 0` that bypasses the unreadable check")
