"""Tests for the multi-confirm gate, the 4-state confidence model, and the
guarantee that disputed events are never dropped from the public API.

Pure-logic tests run with no database. See conftest.py for the optional
`db_conn` fixture used by @pytest.mark.dbintegration tests.
"""
import inspect

import pytest

from worker.gating import multi_confirm_gate, ANCHOR_CLASSES
from worker.confidence import (
    CONFIDENCE_STATES,
    FEED_PRIORITY,
    derive_confidence,
    is_valid_confidence,
    renders_in_public_feed,
)


# --------------------------------------------------------------------------
# Multi-confirm gate — evidence-count thresholds
# --------------------------------------------------------------------------

def test_gate_single_anchor_promotes():
    result = multi_confirm_gate(["ticketing"])
    assert result.ok_to_promote is True
    assert result.status == "ready_to_promote"


@pytest.mark.parametrize("anchor", sorted(ANCHOR_CLASSES))
def test_gate_every_anchor_class_promotes_alone(anchor):
    assert multi_confirm_gate([anchor]).ok_to_promote is True


def test_gate_single_third_party_social_blocks():
    # Founder ruling 2026-08-05 (verbatim in the decision record): ONLY
    # third-party social chatter waits for a second source.
    result = multi_confirm_gate(["social"])
    assert result.ok_to_promote is False
    assert result.status == "needs_more_confirmation"
    assert "need 2" in result.reason


def test_gate_social_plus_any_second_source_promotes():
    result = multi_confirm_gate(["social", "artist_aggregator"])
    assert result.ok_to_promote is True


def test_gate_duplicate_non_anchor_source_does_not_count_twice():
    # Same class twice is still one unique corroborating source.
    result = multi_confirm_gate(["social", "social"])
    assert result.ok_to_promote is False


def test_gate_sxsw_mode_requires_three_non_anchor():
    assert multi_confirm_gate(["social", "link_hub"], sxsw_mode=True).ok_to_promote is False
    result = multi_confirm_gate(["social", "link_hub", "blog"], sxsw_mode=True)
    assert result.ok_to_promote is True


def test_gate_anchor_short_circuits_sxsw_mode():
    # An anchor promotes even in the stricter SXSW/chaos mode.
    assert multi_confirm_gate(["venue_calendar"], sxsw_mode=True).ok_to_promote is True


def test_gate_ignores_empty_classes():
    assert multi_confirm_gate(["", None, "social"]).ok_to_promote is False


# --------------------------------------------------------------------------
# 4-state confidence model
# --------------------------------------------------------------------------

def test_confidence_is_exactly_four_states():
    assert CONFIDENCE_STATES == ("unverified", "likely", "confirmed", "disputed")
    assert len(CONFIDENCE_STATES) == 4


def test_disputed_is_a_valid_state():
    assert is_valid_confidence("disputed") is True


def test_invalid_confidence_rejected():
    assert is_valid_confidence("pending") is False
    assert is_valid_confidence("") is False


def test_derive_anchor_is_confirmed():
    assert derive_confidence(["ticketing"]) == "confirmed"


def test_derive_corroborated_is_confirmed():
    # Founder ruling 2026-08-04, verbatim: "Just 'confirmed' - remove 'likely'"
    # — 2+ independent sources earn the anchor's label. 'likely' is reserved
    # for the publish policy's single-trusted-source path.
    assert derive_confidence(["social", "artist_aggregator"]) == "confirmed"


def test_derive_single_weak_source_is_unverified():
    assert derive_confidence(["social"]) == "unverified"


def test_derive_never_returns_likely():
    # 'likely' = one credible source (publish-policy path), never a
    # corroboration count (founder ruling 2026-08-04).
    for classes in ([], ["social"], ["social", "artist_aggregator"],
                    ["social", "artist_aggregator", "blog"], ["ticketing"]):
        assert derive_confidence(classes) != "likely"
        assert derive_confidence(classes, sxsw_mode=True) != "likely"


def test_derive_sxsw_needs_three_for_confirmed():
    assert derive_confidence(["social", "link_hub"], sxsw_mode=True) == "unverified"
    assert derive_confidence(["social", "link_hub", "blog"], sxsw_mode=True) == "confirmed"


def test_derive_never_returns_disputed():
    # Disputed is a moderation decision, never inferred from source counts.
    for classes in ([], ["social"], ["social", "artist_aggregator"], ["ticketing"]):
        assert derive_confidence(classes) != "disputed"


# --------------------------------------------------------------------------
# Disputed events are never dropped from the public feed
# --------------------------------------------------------------------------

def test_every_state_renders_including_disputed():
    for state in CONFIDENCE_STATES:
        assert renders_in_public_feed(state) is True


def test_disputed_has_a_feed_priority_slot():
    # Disputed must be orderable (shown last), not excluded.
    assert "disputed" in FEED_PRIORITY
    assert FEED_PRIORITY["disputed"] == max(FEED_PRIORITY.values())


def test_public_api_queries_do_not_filter_by_confidence():
    """Structural guard: neither /events nor /tonight may exclude a confidence
    state in SQL. Confidence may only appear in ORDER BY, never in WHERE."""
    import api.public as public

    for fn in (public.events, public.tonight):
        src = inspect.getsource(fn).lower()
        # Isolate the WHERE clause (from 'where' up to the next ORDER BY / LIMIT).
        assert "where" in src
        after_where = src.split("where", 1)[1]
        for terminator in ("order by", "limit"):
            after_where = after_where.split(terminator)[0]
        assert "confidence" not in after_where, (
            f"{fn.__name__} filters on confidence in its WHERE clause — "
            "disputed events could be silently dropped"
        )

    # /tonight must explicitly rank 'disputed' rather than lump it into a
    # catch-all that a future edit could turn into a filter.
    tonight_src = inspect.getsource(public.tonight).lower()
    assert "'disputed'" in tonight_src


# --------------------------------------------------------------------------
# Optional DB integration: promote sets 4-state confidence; disputed persists
# --------------------------------------------------------------------------

@pytest.mark.dbintegration
def test_promote_sets_confirmed_for_anchor_then_dispute_persists(db_conn):
    from worker import promote

    cur = db_conn.cursor()
    cur.execute("insert into venue(name, city) values ('Test Hall','Austin') returning venue_id")
    venue_id = cur.fetchone()[0]
    cur.execute(
        """insert into event(venue_id, status, confidence)
           values (%s,'scheduled',%s) returning event_id""",
        (venue_id, derive_confidence(["ticketing"])),
    )
    event_id = cur.fetchone()[0]
    db_conn.commit()

    cur.execute("select confidence from event where event_id=%s", (event_id,))
    assert cur.fetchone()[0] == "confirmed"

    # Mark disputed via the shared DSN path.
    import os
    old = os.environ.get("ONELIVE_DB_DSN")
    os.environ["ONELIVE_DB_DSN"] = os.environ["ONELIVE_TEST_DB_DSN"]
    try:
        promote.mark_event_disputed(str(event_id))
    finally:
        if old is not None:
            os.environ["ONELIVE_DB_DSN"] = old

    cur.execute("select confidence from event where event_id=%s", (event_id,))
    assert cur.fetchone()[0] == "disputed"
    # Row still exists — disputed is never deleted.
    cur.execute("select count(*) from event where event_id=%s", (event_id,))
    assert cur.fetchone()[0] == 1


# --------------------------------------------------------------------------
# Founder ruling 2026-08-05: first-party / published sources promote on ONE
# (decision record 2026-08-05_first-party-promotes-on-one-source.md)
# --------------------------------------------------------------------------

import pytest as _pytest


@_pytest.mark.parametrize("cls", [
    "venue_calendar", "ticketing", "festival_feed", "calendar_feed",
    "city_calendar", "university_calendar", "university", "library_calendar",
    # institutions publishing their own programs. These four are LIVE-DB
    # classes with no definition anywhere in this repo (found via PR #191):
    # before this ruling every one of them fell through to the corroboration
    # branch and waited forever for a second museum to confirm the first.
    "theater_arts", "gallery_museum", "food_culinary",
    "claimed_upload", "email_opt_in",
])
def test_first_party_source_promotes_on_one(cls):
    result = multi_confirm_gate([cls])
    assert result.ok_to_promote is True
    assert derive_confidence([cls]) == "confirmed"


@_pytest.mark.parametrize("cls", [
    "social",             # third-party chatter — the ruled exception
    "artist_aggregator",  # republishes others' claims
    "artist_directory", "link_hub", "directory", "blog", "music_platform",
    # a community PLATFORM is not the host of what it lists, so it is not the
    # horse's mouth under the founder's "comes from the source site" test
    "community",
    # local_media HELD pending the masthead/UGC split (R-089). The founder's
    # ruling names publishers under their own masthead; this class also
    # contains four station "community calendars" our own catalog annotates
    # "USER-SUBMITTED (Trumba) … treat unverified". Anchoring the class would
    # let a form submission publish alone at `confirmed`. Moved here from the
    # first-party list above, deliberately and on the record.
    "local_media",
])
def test_third_party_republisher_still_needs_corroboration(cls):
    result = multi_confirm_gate([cls])
    assert result.ok_to_promote is False
    assert "need 2" in result.reason
    assert derive_confidence([cls]) == "unverified"


def test_unclassified_class_holds_but_says_so_out_loud(caplog):
    """A class nobody has ruled on holds — and MUST warn while doing it.

    The silent forever-hold is the defect that stranded the DB-seeded
    institutional classes: their events simply never appeared, with nothing
    in any log to say why. Holding is the right safe direction; holding
    quietly is not.

    The warning is ONCE PER CLASS, not once per call: is_first_party sits in
    the gate's hot path, and the perf budget is 50us over 5,000 reps. Both
    halves are asserted here — the operator learns the class name, and the
    hot path does not pay for it twice.
    """
    import logging
    from worker.gating import _WARNED_UNCLASSIFIED
    _WARNED_UNCLASSIFIED.discard("some_class_nobody_classified")

    with caplog.at_level(logging.WARNING):
        result = multi_confirm_gate(["some_class_nobody_classified"])
    assert result.ok_to_promote is False
    assert sum("UNCLASSIFIED SOURCE CLASS" in m for m in caplog.messages) == 1

    caplog.clear()
    with caplog.at_level(logging.WARNING):
        again = multi_confirm_gate(["some_class_nobody_classified"])
    assert again.ok_to_promote is False  # still held — behavior is unchanged
    assert not any("UNCLASSIFIED SOURCE CLASS" in m for m in caplog.messages), (
        "the same class must not re-warn on every call — that is the flood "
        "the perf gate caught")


def test_gate_and_confidence_never_disagree_about_first_party():
    """One authority, both paths. If these two ever diverge, a source can
    pass the gate while being labelled unverified to users (or worse, the
    reverse) — so the agreement is pinned, not assumed."""
    from worker.gating import ANCHOR_CLASSES, THIRD_PARTY_CLASSES
    for cls in sorted(ANCHOR_CLASSES):
        assert multi_confirm_gate([cls]).ok_to_promote is True
        assert derive_confidence([cls]) == "confirmed"
    for cls in sorted(THIRD_PARTY_CLASSES):
        assert multi_confirm_gate([cls]).ok_to_promote is False
        assert derive_confidence([cls]) == "unverified"
    assert not (ANCHOR_CLASSES & THIRD_PARTY_CLASSES), (
        "a class cannot be both the horse's mouth and hearsay")


def test_third_party_social_promotes_once_any_second_source_arrives():
    # "Then it gets a secondary source" — one is enough, and a first-party
    # second source promotes it immediately as an anchor.
    assert multi_confirm_gate(["social", "directory"]).ok_to_promote is True
    assert multi_confirm_gate(["social", "venue_calendar"]).ok_to_promote is True
