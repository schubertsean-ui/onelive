"""Existence vs field vs mutation — the Scoot-Inn and Blanton shapes.

Founder ticket 2026-09-03 (Session Contract #56), against ONE-LIVE-TRUST.md:

    "Scoot Inn / Blanton shape: many events, two clocks -> rows exist, door not
     banned, mutation of the uncertain field refused."

Three questions, three separate tests, and this file's whole purpose is that no
one of them may be answered with another:

  EXISTENCE  did a trusted door state a happening?   -> the DOOR alone decides.
  FIELD      is this clock printable as fact?        -> a hole, never a refusal.
  MUTATION   may we overwrite a published value?     -> fail-closed, #214 intact.

Hermetic: no network, no model, no database. The DB shapes are faked at the same
seams the orchestrator tests already fake, and the pure decision layers
(trust_gate3, dedupe, listing_update) are driven directly.
"""
import datetime as dt

import pytest

from worker.candidate_store import _load_gate_signals
from worker.crawl_state import (
    BASE_INTERVAL_MINUTES,
    UNVERIFIED,
    VERIFIED_PRESENT,
    SourceCrawlState,
    classify_recheck,
    may_delete_listing,
    may_update_listing,
)
from worker.dedupe import classify_duplicates
from worker.listing_update import (
    ACTION_NONE,
    ACTION_UPDATE,
    MATCH_COLLISION,
    ParsedListing,
    PublishedListing,
    adjudicate_page,
    match_kind,
)
from worker.trust_gate3 import FIELD_START_TIME, GateDecision, evaluate_gate

UTC = dt.timezone.utc


class FakeCursor:
    """Returns queued rows in call order — enough for _load_gate_signals' two
    queries (the candidate row, then the optional dedupe count)."""

    def __init__(self, results):
        self._results = list(results)
        self._last = None

    def execute(self, sql, params=None):
        self._last = self._results.pop(0) if self._results else None

    def fetchone(self):
        return self._last


# --------------------------------------------------------------------------
# The Scoot Inn shape: a music venue calendar, many events, two clocks on some.
# --------------------------------------------------------------------------

#: One night at a venue that runs several rooms. Two of these carry a second,
#: DIFFERENT clock (the page states one time in its list and another in the
#: detail blurb); the rest are clean. `venue_calendar` is the door.
SCOOT_INN_NIGHT = [
    # (title, column start_time, the extraction's own start_time string)
    ("Bass Drum of Death", dt.datetime(2026, 9, 5, 20, 0, tzinfo=UTC), "2026-09-05T20:00:00Z"),
    ("A Giant Dog",        dt.datetime(2026, 9, 5, 21, 0, tzinfo=UTC), "2026-09-05T21:00:00Z"),
    # two clocks — the list says 19:00, the blurb says 20:30
    ("Being Dead",         dt.datetime(2026, 9, 5, 19, 0, tzinfo=UTC), "2026-09-05T20:30:00Z"),
    ("Sun June",           dt.datetime(2026, 9, 6, 20, 0, tzinfo=UTC), "2026-09-06T20:00:00Z"),
    # two clocks again, this time a doors-vs-show disagreement
    ("例 Night",           dt.datetime(2026, 9, 6, 21, 0, tzinfo=UTC), "2026-09-06T22:00:00Z"),
    ("Croy and the Boys",  dt.datetime(2026, 9, 7, 20, 0, tzinfo=UTC), "2026-09-07T20:00:00Z"),
]


def _signals_for(column_start, extracted_start, *, venue="Scoot Inn", siblings=0):
    """Drive the REAL _load_gate_signals with the shape production produces."""
    row = ({"start_time": extracted_start}, column_start, venue, False)
    return _load_gate_signals(FakeCursor([row, (siblings,)]), "cid")


def test_one_clock_written_two_ways_is_one_claim():
    """The defect this ticket found, pinned so it cannot come back.

    `event_candidate.start_time` is `timestamptz` (migration 0002), so psycopg2
    returns a tz-AWARE datetime whose `.isoformat()` ends `+00:00`, while the
    stored `extracted` jsonb keeps the parser's own string. Compared as strings
    those are two claims; they are one instant. Before the fix every timed
    candidate looked self-contradictory and could never publish.
    """
    extracted, signals = _signals_for(
        dt.datetime(2026, 9, 5, 20, 0, tzinfo=UTC), "2026-09-05T20:00:00Z")
    # The two renderings really are different strings — the fix is in the
    # comparison, not in the data.
    assert len(set(signals["start_times"])) == 2

    verdict = evaluate_gate(source_classes=["venue_calendar"],
                            extracted=extracted, evidence_signals=signals)
    assert verdict.decision is GateDecision.PASS
    assert verdict.field_holes == {}


@pytest.mark.parametrize("naive_and_aware", [
    ("2026-09-05T20:00:00", "2026-09-05T20:00:00+00:00"),
    ("2026-09-05T20:00:00Z", "2026-09-05T20:00:00+00:00"),
    ("2026-09-05T15:00:00-05:00", "2026-09-05T20:00:00Z"),
])
def test_the_same_instant_in_any_notation_is_one_claim(naive_and_aware):
    """A naive value is read as UTC — the same convention crawl_state._as_utc
    uses — so the scheduler and the gate can never disagree about a stored
    naive timestamp."""
    verdict = evaluate_gate(source_classes=["venue_calendar"],
                            evidence_signals={"start_times": list(naive_and_aware)})
    assert verdict.decision is GateDecision.PASS
    assert verdict.field_holes == {}


def test_scoot_inn_every_event_exists_and_only_the_clocks_are_holes():
    """Many events, two clocks. Every row stays listable; the two disagreeing
    clocks are holes, and nothing about the DOOR changes."""
    verdicts = {}
    for title, column_start, extracted_start in SCOOT_INN_NIGHT:
        extracted, signals = _signals_for(column_start, extracted_start)
        verdicts[title] = evaluate_gate(
            source_classes=["venue_calendar"], extracted=extracted,
            evidence_signals=signals)

    # EXISTENCE: every event on the page passes. Zero refusals.
    assert [v.decision for v in verdicts.values()] == [GateDecision.PASS] * 6

    # FIELD: exactly the two rows whose page states two different times.
    holed = {t for t, v in verdicts.items() if FIELD_START_TIME in v.field_holes}
    assert holed == {"Being Dead", "例 Night"}

    # And the hole is honest about being a hole — it never names a winner.
    for title in holed:
        why = verdicts[title].field_holes[FIELD_START_TIME]
        assert "hole" in why
        assert "20:30" not in why and "22:00" not in why


def test_a_two_clock_page_never_bans_the_door():
    """A gate verdict is not a fetch outcome. The crawl schedule is derived
    from whether the source ANSWERED, so no number of holes can push a healthy
    venue onto the backoff ladder or off the queue."""
    state = SourceCrawlState(
        source_id="scoot-inn",
        last_attempt_at=dt.datetime(2026, 9, 5, 0, 0, tzinfo=UTC),
        last_success_at=dt.datetime(2026, 9, 5, 0, 0, tzinfo=UTC),
        fail_streak=0,
        best_url="https://example.test/scoot-inn/calendar",
    )
    assert state.interval_minutes() == BASE_INTERVAL_MINUTES
    assert state.queue == "refresh"
    assert state.is_due(dt.datetime(2026, 9, 6, 0, 0, tzinfo=UTC))


# --------------------------------------------------------------------------
# The Blanton shape: a museum calendar whose events genuinely share a slot.
# --------------------------------------------------------------------------

#: A museum runs concurrent programming: three things start at 18:00 on the
#: same evening in the same building. Under the old rule each of them saw the
#: others as a "dedupe ambiguity" and every one of them escalated.
BLANTON_EVENING = [
    ("Gallery Talk: Contemporary Collection", dt.datetime(2026, 9, 10, 18, 0, tzinfo=UTC)),
    ("Third Thursday: Live Music",            dt.datetime(2026, 9, 10, 18, 0, tzinfo=UTC)),
    ("Family Studio: Print Making",           dt.datetime(2026, 9, 10, 18, 0, tzinfo=UTC)),
]


def test_blanton_concurrent_programming_all_exists():
    """`gallery_museum` is an anchor door (worker/gating.py). Three things at
    one museum at one hour is a Thursday, not an ambiguity about whether they
    happen."""
    for title, start in BLANTON_EVENING:
        extracted, signals = _signals_for(
            start, start.isoformat(), venue="Blanton Museum of Art", siblings=2)
        assert signals["dedupe_ambiguous"] is True
        verdict = evaluate_gate(source_classes=["gallery_museum"],
                                extracted=extracted, evidence_signals=signals)
        assert verdict.decision is GateDecision.PASS, title
        assert verdict.field_holes == {}
        # Recorded, so ops can still see the collision.
        assert any("identity" in n for n in verdict.notes)


def test_a_second_crawl_of_the_same_page_does_not_escalate_it():
    """The hint fires on any other live candidate at the same venue and minute,
    and `create_candidate` inserts rather than upserts — so re-reading a
    calendar created its own ambiguity and zeroed the page."""
    start = dt.datetime(2026, 9, 10, 18, 0, tzinfo=UTC)
    extracted, signals = _signals_for(start, start.isoformat(), siblings=1)
    assert signals["dedupe_ambiguous"] is True
    assert evaluate_gate(source_classes=["venue_calendar"], extracted=extracted,
                         evidence_signals=signals).decision is GateDecision.PASS


def test_a_neighbour_publishes_and_only_a_re_publish_is_refused():
    """worker/dedupe: the publish-side half of the same split. Everything in a
    90-minute window used to be refused outright."""
    at_18 = dt.datetime(2026, 9, 10, 18, 0, tzinfo=UTC)
    existing = [
        ("e-talk",  "Gallery Talk: Contemporary Collection", at_18),
        ("e-music", "Third Thursday: Live Music",            at_18),
        ("e-late",  "Gallery Talk: Contemporary Collection",
         dt.datetime(2026, 9, 10, 19, 30, tzinfo=UTC)),
    ]
    # A genuinely different programme in the same slot: publishes.
    fresh = classify_duplicates(existing, title="Family Studio: Print Making",
                                start_time=at_18)
    assert fresh.is_republish is False
    assert len(fresh.neighbours) == 3

    # The same show read again: refused, which is what the check was for.
    again = classify_duplicates(existing, title="gallery talk: contemporary collection!",
                                start_time=at_18)
    assert again.same_show == ("e-talk",)

    # Same title, a different hour — a repeat occurrence, not a re-publish.
    later = classify_duplicates(existing, title="Gallery Talk: Contemporary Collection",
                                start_time=dt.datetime(2026, 9, 10, 21, 0, tzinfo=UTC))
    assert later.is_republish is False


def test_an_untitled_candidate_is_never_treated_as_a_republish():
    """`normalize_title` returns None for an absent title, and two rows that
    both lack a name have not been shown to be one row (the rule
    worker/listing_update.py reached at r7)."""
    at_18 = dt.datetime(2026, 9, 10, 18, 0, tzinfo=UTC)
    verdict = classify_duplicates([("e1", None, at_18)], title=None, start_time=at_18)
    assert verdict.is_republish is False


# --------------------------------------------------------------------------
# MUTATION — #214 stays fail-closed. Must-do 4.
# --------------------------------------------------------------------------

def _passes(_candidate_id):
    return True


def test_an_uncertain_time_never_overwrites_a_confirmed_published_time():
    """The published row was promoted with a settled 20:00. The re-read parses
    the same show but its clock is unsettled (the page gives a title and no
    time). Nothing is written, and the row keeps 20:00."""
    published = [PublishedListing(
        event_id="e1", title="Being Dead",
        start_time=dt.datetime(2026, 9, 5, 20, 0, tzinfo=UTC))]
    parsed = [ParsedListing(candidate_id="c1", title="Being Dead", start_time=None,
                            source_class="venue_calendar")]

    decisions = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=published, parsed=parsed,
        gate_passes=_passes, page_text="Being Dead — doors TBA")

    assert [d.action for d in decisions] == [ACTION_NONE]
    assert not any(d.mutates for d in decisions)


def test_a_second_clock_on_the_page_does_not_retime_the_published_row():
    """The Scoot Inn shape carried into mutation: the page now states a
    DIFFERENT hour for the same title. `start_time` is unwritable by
    construction (R-099) — a title-only match writes nothing."""
    published = [PublishedListing(
        event_id="e1", title="Being Dead",
        start_time=dt.datetime(2026, 9, 5, 20, 0, tzinfo=UTC))]
    parsed = [ParsedListing(candidate_id="c1", title="Being Dead",
                            start_time=dt.datetime(2026, 9, 5, 20, 30, tzinfo=UTC),
                            source_class="venue_calendar")]

    decisions = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=published, parsed=parsed,
        gate_passes=_passes, page_text="Being Dead 8:30pm")

    assert all(d.action != ACTION_UPDATE for d in decisions)
    assert all("start_time" not in d.fields for d in decisions)


def test_a_collision_still_does_not_rename_a_to_b():
    """Two different shows in one minute is a collision, and a collision is not
    an identity — the founder's own must-do 4. Unchanged by this ticket."""
    published = PublishedListing(
        event_id="e1", title="A Giant Dog",
        start_time=dt.datetime(2026, 9, 5, 21, 0, tzinfo=UTC))
    parsed = ParsedListing(candidate_id="c1", title="Croy and the Boys",
                           start_time=dt.datetime(2026, 9, 5, 21, 0, tzinfo=UTC),
                           source_class="venue_calendar")
    assert match_kind(published, parsed) == MATCH_COLLISION

    decisions = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published], parsed=[parsed],
        gate_passes=_passes, page_text="A Giant Dog 9pm / Croy and the Boys 9pm")
    assert [d.action for d in decisions] == [ACTION_NONE]
    assert all("title" not in d.fields for d in decisions)


@pytest.mark.parametrize("page_decision", ["held", "escalated"])
def test_a_gate_declined_page_still_confirms_nothing(page_decision):
    """#214's own rule, re-pinned here because this ticket loosened what HOLD
    and ESCALATE mean for EXISTENCE and must not have loosened what they mean
    for MUTATION."""
    verdict, _why = classify_recheck(door_kind="changed", page_decision=page_decision)
    assert verdict == UNVERIFIED
    assert may_update_listing(verdict) is False


def test_no_verdict_ever_licenses_a_delete():
    for verdict in ("verified_present", "verified_absent", UNVERIFIED, "anything"):
        assert may_delete_listing(verdict) is False
