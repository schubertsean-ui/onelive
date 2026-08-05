"""Unit tests for the authority-based Verification Cascade decision core
(worker/authority.py). PURE — no DB, no network. Proves the founder's model
(2026-07-31): a first-party authority is verified full stop; a weak signal must
resolve to an authority or find an independent second signal, else HOLD with a
machine-readable reason for the held-and-learn loop; a spoof suspicion stops even
an authority.
"""
from worker.authority import (
    AUTHORITATIVE,
    BASIS_FIRST_PARTY_FEED,
    BASIS_REGISTERED_IDENTITY,
    BASIS_RESOLVED,
    BASIS_SECOND_SIGNAL,
    HOLD,
    HOLD_NO_AUTHORITY,
    HOLD_NO_SECOND_SIGNAL,
    HOLD_SPOOF,
    VALIDATED,
    VERIFIED,
    WEAK,
    Provenance,
    ResolutionOutcome,
    classify_source_authority,
    decide_verification,
)


# ---- classify_source_authority ----------------------------------------------

def test_venue_calendar_is_first_party_authority():
    p = classify_source_authority({"category": "venue_calendar", "source_name": "mohawk"})
    assert p.authority == AUTHORITATIVE
    assert p.kind == "venue" and p.basis == BASIS_FIRST_PARTY_FEED
    assert p.is_authoritative


def test_ticketing_and_festival_are_authoritative():
    assert classify_source_authority({"category": "ticketing"}).is_authoritative
    assert classify_source_authority({"category": "festival_feed"}).kind == "organizer"


def test_social_and_media_are_weak_without_registry():
    assert classify_source_authority({"category": "social", "source_name": "some_fan"}).authority == WEAK
    assert classify_source_authority({"category": "local_media"}).authority == WEAK
    assert classify_source_authority({"category": "artist_aggregator"}).authority == WEAK


def test_registry_makes_the_entitys_own_handle_authoritative():
    # "social media can verify alone" when it is the artist's OWN verified handle.
    registry = {"@spoontheband": {"kind": "artist", "entity": "Spoon"}}
    p = classify_source_authority(
        {"category": "social", "handle": "@SpoonTheBand"}, registry=registry)
    assert p.is_authoritative
    assert p.kind == "artist" and p.entity == "Spoon"
    assert p.basis == BASIS_REGISTERED_IDENTITY


def test_registry_miss_stays_weak():
    registry = {"@spoontheband": {"kind": "artist", "entity": "Spoon"}}
    p = classify_source_authority({"category": "social", "handle": "@rando"}, registry=registry)
    assert p.authority == WEAK


# ---- decide_verification: the cascade ---------------------------------------

def test_authority_verifies_full_stop():
    d = decide_verification(classify_source_authority({"category": "venue_calendar"}))
    assert d.status == VERIFIED and d.confidence == "confirmed"
    assert d.publishable


def test_spoof_suspected_holds_even_an_authority():
    p = classify_source_authority({"category": "venue_calendar", "spoof_suspected": True})
    d = decide_verification(p)
    assert d.status == HOLD and d.hold_reason == HOLD_SPOOF
    assert not d.publishable


def test_weak_resolved_to_authority_verifies():
    weak = Provenance(WEAK)
    res = ResolutionOutcome(resolved_to_authority=True, resolved_kind="venue",
                            resolved_entity="Mohawk")
    d = decide_verification(weak, res)
    assert d.status == VERIFIED and d.confidence == "confirmed"
    assert d.basis == BASIS_RESOLVED and d.authority_kind == "venue"


def test_weak_with_two_second_signals_is_validated_confirmed():
    # 2026-08-04 founder ruling: the corroborated tier publishes CONFIRMED;
    # 'likely' is exclusively the single-trusted-source publish-policy tier.
    d = decide_verification(Provenance(WEAK), ResolutionOutcome(second_signals=2))
    assert d.status == VALIDATED and d.confidence == "confirmed"
    assert d.basis == BASIS_SECOND_SIGNAL and d.publishable


def test_weak_with_one_second_signal_is_validated_but_unverified():
    d = decide_verification(Provenance(WEAK), ResolutionOutcome(second_signals=1))
    assert d.status == VALIDATED and d.confidence == "unverified"  # shown with the marker
    assert d.publishable


def test_weak_no_authority_no_signal_holds():
    d = decide_verification(Provenance(WEAK), ResolutionOutcome())
    assert d.status == HOLD and not d.publishable
    assert d.hold_reason == HOLD_NO_AUTHORITY  # nothing was reachable


def test_hold_reason_reflects_unreachable_authority_for_learning():
    # The active cascade tried an authority and it was blocked/absent, and found
    # no second signal → held, tagged so the learn loop knows to fix the fetch.
    d = decide_verification(
        Provenance(WEAK), ResolutionOutcome(authority_unreachable=True, second_signals=0))
    assert d.status == HOLD and d.hold_reason == HOLD_NO_SECOND_SIGNAL


def test_no_resolution_defaults_to_hold_not_publish():
    # A weak signal with NO resolution attempt passed must never default to publish.
    d = decide_verification(Provenance(WEAK))
    assert d.status == HOLD and not d.publishable
