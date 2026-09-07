"""A happening that only ever became a CANDIDATE still gets published.

Founder ticket, 2026-09-07: "Skip-to-promote: a Happening from a trusted door
(local_desk, civic, official_list, marketplace public HTML) with title + when +
place that exists only as a candidate must still promote. Same statement
already PUBLIC -> skip. Field holes stay holes (held or labelled). Existence is
not a field test (ONE-LIVE-TRUST.md)."

WHAT WAS WRONG. `tools/desk_ingest.py` skipped on EXISTENCE IN THE STORE: any
key already carrying a candidate was skipped, whatever had become of that
candidate. A happening a trusted door stated -- title, night AND place -- that
was written once and never published (the gate held it that day, its place
arrived on a later walk, the promote raised, the job was cancelled mid-wave)
was then skipped by every run afterwards, for ever. The queue is not the map:
what a friend can see is the published row, and a statement we have never
published is work left undone rather than work already done.

WHAT MUST NOT MOVE WITH IT, and is pinned here as hard as the fix:
  * a hole is still a hole -- a retry cannot promote a row into a public
    "Date TBA" (R-111);
  * the trust gate still decides -- every publish goes through
    `promote_candidate`, which may hold the row again;
  * a PUBLISHED row that a desk now contradicts is still recorded and
    disputed, never re-published beside itself (evaluator, PR #229).

Hermetic: no network, no database, no clock. The three DB seams are injected.
"""
from __future__ import annotations

import importlib.util
import os

import pytest
from zoneinfo import ZoneInfo

from worker.locale.desk_publish import DESK_KEY, DeskRegistration, plan
from worker.locale.desk_read import Happening
from worker.locale.desk_union import union
from worker.locale.desk_walk import DeskWalk, PageVisit

CAPCOG = "us-tx-capcog"
TZ_ID = "America/Chicago"
TZ = ZoneInfo(TZ_ID)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: The four door types a happening may be LISTED from (ONE-LIVE-TRUST.md).
#: Every one of them is a trusted door: one is enough to exist.
TRUSTED_DOOR_TYPES = ("local_desk", "civic", "official_list", "marketplace")

VIA = "The Desk"
DOOR = "a-trusted-door"
REGS = {VIA: DeskRegistration(
    door_id=DOOR, via=VIA, source_name="The Desk", source_class="local_media",
    base_url="https://desk.example/", catalog_id="the_desk")}


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "_tool_desk_ingest_skip", os.path.join(ROOT, "tools", "desk_ingest.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tool = _load_tool()


def _writes(*, door_type="local_desk", when="2026-09-12T20:00:00-05:00",
            place="Shape Hall", title="A Real Show"):
    row = Happening(
        title=title, when=when, when_text=None,
        when_precision=("datetime" if when else None), place_text=place,
        via=VIA, kind="other", door_id=DOOR, door_type=door_type,
        locale_id=CAPCOG, source_url="https://desk.example/page",
        listing_url="https://desk.example/e/1")
    walk = DeskWalk(
        door_id=DOOR, door_type=door_type, via=VIA,
        start_url="https://desk.example/",
        pages=[PageVisit(n=1, url="https://desk.example/", status=200,
                         rows_seen=1, new_rows=1)],
        rows=[row], stopped_because="no_next_link")
    return plan(union([walk], timezone=TZ, timezone_id=TZ_ID, mode="LIVE"), REGS)


class _Seams:
    """The three injected DB seams, recording what each was asked to do."""

    def __init__(self, *, promote_raises=None):
        self.created = []
        self.evidence = []
        self.promoted = []
        self.disputed = []
        self._promote_raises = promote_raises

    def create(self, **kw):
        self.created.append(kw)
        return f"cand-new-{len(self.created)}"

    def add_evidence(self, *a):
        self.evidence.append(a)

    def promote(self, cid):
        self.promoted.append(cid)
        if self._promote_raises:
            raise self._promote_raises
        return f"event-for-{cid}"

    def dispute(self, event_id):
        self.disputed.append(event_id)
        return f"disputed {event_id}"

    def run(self, writes, seen):
        return tool.ingest(writes, seen=seen, create=self.create,
                           add_evidence=self.add_evidence, promote=self.promote,
                           dispute=self.dispute)


def _statement(w):
    return w.extracted[DESK_KEY]["statement"]


# --------------------------------------------------------------------------
# The fix
# --------------------------------------------------------------------------

@pytest.mark.parametrize("door_type", TRUSTED_DOOR_TYPES)
def test_a_complete_triple_that_only_exists_as_a_candidate_is_promoted(door_type):
    """THE TICKET. Title + night + place, from a trusted door, never published.

    Parametrised over all four door types a happening may be listed from,
    because "one trusted door is enough to exist" is a statement about every
    one of them — a fix that only rescued the desks would leave the civic
    calendars and the official lists exactly as starved.
    """
    writes = _writes(door_type=door_type)
    assert not writes[0].hold_reason, "this row is a complete triple"
    seen = {writes[0].ingest_key: ("cand-1", "needs_review", None,
                                   _statement(writes[0]))}
    seams = _Seams()
    result = seams.run(writes, seen)

    assert len(result["promoted"]) == 1, (
        f"a {door_type} stated a title, a night and a place, we hold it as a "
        f"candidate and have never published it — it is not a re-run, it is "
        f"work left undone: {result}")
    assert not result["skipped"]
    assert seams.promoted == ["cand-1"], (
        "the candidate ALREADY in the store is the one that publishes")


def test_no_second_candidate_is_written_for_a_statement_we_already_hold():
    """One happening, one handle. The candidate was never the missing piece."""
    writes = _writes()
    seen = {writes[0].ingest_key: ("cand-1", "needs_review", None,
                                   _statement(writes[0]))}
    seams = _Seams()
    seams.run(writes, seen)

    assert seams.created == [], "a second candidate for one statement"
    assert seams.evidence == [], (
        "re-adding evidence would duplicate the gate's own inputs and could "
        "turn one desk into two corroborating rows")


def test_the_same_statement_already_public_is_skipped():
    """The only skip: it is on the map and the desk still says the same thing."""
    writes = _writes()
    seen = {writes[0].ingest_key: ("cand-1", "promoted", "event-1",
                                   _statement(writes[0]))}
    seams = _Seams()
    result = seams.run(writes, seen)

    assert len(result["skipped"]) == 1
    assert seams.promoted == [] and seams.created == []
    assert "already PUBLIC" in result["skipped"][0][1]


def test_a_drift_candidate_does_not_make_a_published_happening_look_unpublished():
    """The one that bit: PUBLIC is a fact about the KEY, not about a row.

    A drift candidate is written deliberately UNPROMOTED — recorded, the
    published row disputed, never re-published beside the listing already on
    the feed. It is also the NEWEST candidate for its key, and it carries no
    event id. So a skip test that reads "did the newest candidate promote?"
    answers "never published" for a happening that is public, and publishes a
    second listing at the corrected time — the exact harm the drift seam
    exists to prevent (`tests/integration/test_desk_ingest_pg.py` caught this
    against real SQL; `existing_keys` now reads the event id from whichever
    candidate of the key actually promoted).

    Here that store shape is handed straight to the decision: newest candidate
    unpromoted, key public, desk still saying what the drift candidate says.
    """
    writes = _writes()
    seen = {writes[0].ingest_key: ("cand-drift", "needs_review", "event-1",
                                   _statement(writes[0]))}
    seams = _Seams()
    result = seams.run(writes, seen)

    assert len(result["skipped"]) == 1, (
        f"a happening already on the feed was treated as never published: "
        f"{result}")
    assert seams.promoted == [], "a second listing for one happening"
    assert seams.created == []


def test_a_desk_that_changed_its_word_about_an_unpublished_row_publishes():
    """Drift with nothing published is not a dispute — it is the newer word.

    The "recorded, not re-published" refusal exists to stop a SECOND listing
    appearing beside one already on the feed. There is no such listing here,
    so the newer statement is written and published, and the older candidate
    is named in `supersedes` so the store still shows what we were told first.
    """
    writes = _writes()
    stale = dict(_statement(writes[0]), clocks=["2026-09-12T18:00:00-05:00"])
    seen = {writes[0].ingest_key: ("cand-1", "needs_review", None, stale)}
    seams = _Seams()
    result = seams.run(writes, seen)

    assert len(result["promoted"]) == 1 and not result["changed"]
    assert seams.disputed == [], "there is no published row to dispute"
    assert len(seams.created) == 1, "the newer statement is recorded"
    note = seams.created[0]["extracted"][DESK_KEY]["supersedes"]
    assert note["candidate_id"] == "cand-1" and note["published"] is False


# --------------------------------------------------------------------------
# What must not move with it
# --------------------------------------------------------------------------

@pytest.mark.parametrize("hole", ["place", "night"])
def test_a_field_hole_still_holds_on_the_retry_path(hole):
    """Field holes stay holes. Existence is retried; a hole is not filled.

    `event` has one clock column and a NULL in it renders as "Date TBA", so a
    retry that promoted a holed row would tell a reader we do not know a date
    a desk gave us (R-111) or put a placeless row on a discovery surface.
    """
    writes = _writes(**{("place" if hole == "place" else "when"): None})
    assert writes[0].hold_reason, "this row is supposed to have a hole"
    seen = {writes[0].ingest_key: ("cand-1", "needs_review", None,
                                   _statement(writes[0]))}
    seams = _Seams()
    result = seams.run(writes, seen)

    assert len(result["held"]) == 1 and not result["promoted"]
    assert seams.promoted == [], "a hole must never reach the publisher"
    assert "already in the store" in result["held"][0][1]


def test_the_gate_still_decides_what_publishes():
    """A retry asks the publication question again; it does not answer it.

    `promote_candidate` re-runs the full trust gate, and a HOLD from it is a
    correct outcome, not an error: the candidate stays in the store where ops
    can see it, and the next run will ask again.
    """
    writes = _writes()
    seen = {writes[0].ingest_key: ("cand-1", "needs_review", None,
                                   _statement(writes[0]))}
    seams = _Seams(promote_raises=ValueError("gate: HOLD (weak corroboration)"))
    result = seams.run(writes, seen)

    assert not result["promoted"] and len(result["held"]) == 1
    assert "HOLD" in result["held"][0][1]


def test_a_published_row_a_desk_now_contradicts_is_recorded_and_disputed():
    """The seam the evaluators built, unchanged (PR #229 r1/r2/r6/r9).

    Regression guard: the fix above must not turn a contradicted PUBLISHED row
    into a second listing on the feed.
    """
    writes = _writes()
    stale = dict(_statement(writes[0]), clocks=["2026-09-12T18:00:00-05:00"])
    seen = {writes[0].ingest_key: ("cand-1", "promoted", "event-1", stale)}
    seams = _Seams()
    result = seams.run(writes, seen)

    assert len(result["changed"]) == 1 and not result["promoted"]
    assert seams.disputed == ["event-1"]
    assert seams.promoted == [], "a published row is never re-published"


def test_every_row_still_lands_in_exactly_one_bucket():
    """The loop's cardinality invariant, over the new paths as well."""
    rows = [_writes(title="Public Already")[0], _writes(title="Only A Candidate")[0],
            _writes(title="Brand New")[0]]
    seen = {
        rows[0].ingest_key: ("cand-1", "promoted", "event-1", _statement(rows[0])),
        rows[1].ingest_key: ("cand-2", "needs_review", None, _statement(rows[1])),
    }
    seams = _Seams()
    result = seams.run(rows, seen)

    counted = sum(len(result[b]) for b in tool.ROW_BUCKETS)
    assert counted == len(rows), f"{counted} outcomes for {len(rows)} rows: {result}"
    assert len(result["skipped"]) == 1 and len(result["promoted"]) == 2
