"""Meta carousel engine: trust physics, gate custody, learning, GEO.

Covers (spec: docs/strategy/ONE_LIVE_META_CAROUSEL_ENGINE_v1.md; hardened
at the PR #63 evaluator's r1):
- selection rules: confirmed/likely featurable, unverified/disputed never,
  CANONICAL-origin rows only, event_status `scheduled` only, unknown
  states fail loud (the 4-state canon + status axis extended to marketing);
- truthful time framing: events outside the series window are excluded and
  copy claims exactly the verified window;
- publish-gate custody: approvals are HMAC-signed under the founder-held
  key (a name string alone approves nothing), hash-bound (edit-after-
  approval voids), release re-checks CURRENT confidence + status and
  rescans the FULL draft text surface; autonomy records must be signed or
  everything refuses;
- the structural guard: agent_loop cannot import publish_gate/autonomy;
- the typed error boundary: run_cycle records ONLY NoFeaturableEvents as a
  skip — every trust error propagates loud;
- bandit determinism, learning direction, exploration floor, decay;
- tiering by volume with the no-thin-carousel floor; GEO bundle validity.
"""
import ast
import dataclasses
import json
import os

import pytest

from social.carousel.agent_loop import BrandIdentity, ingest_results, run_cycle
from social.carousel.autonomy import (
    AutonomyPolicy,
    AutonomyRecordError,
    load_policy,
    sign_autonomy_record,
)
from social.carousel.bandit import ThompsonBandit
from social.carousel.config import CarouselConfig, FACTORS, validate_assignment
from social.carousel.generator import (
    CarouselTrustError,
    NoFeaturableEvents,
    build_carousel,
    content_hash,
    select_featurable,
    within_timeframe,
)
from social.carousel.geo import DOMAIN_TAGS, discovery_bundle, event_jsonld, hashtags_for
from social.carousel.metrics import MetricsLedger, PostMetrics
from social.carousel.publish_gate import Approval, approve, release_for_publish
from social.carousel.tiers import TierThresholds, assign_tiers, plan_portfolio

TEST_KEY = "test-founder-approval-key"
REF_DATE = "2026-07-24"


def _event(i=1, confidence="confirmed", domain="live-music", **over):
    base = dict(
        event_id=f"ev-{i}",
        name=f"Test Show {i}",
        venue_name="Mohawk",
        start_time=f"2026-07-24T2{i % 4}:00:00-05:00",
        confidence=confidence,
        event_status="scheduled",
        origin="canonical_event",
        domain_id=domain,
        source="ticketmaster",
        price_min=20,
        image_url=f"https://img.example/{i}.jpg",
    )
    base.update(over)
    return base


def _config(**over):
    base = dict(
        surface="instagram_feed",
        series_key="t1_live-music",
        city="Austin",
        handle="@onelive.atx",
        short_link_base="https://onelive.app/tonight",
        domain_ids=("live-music",),
        tier="T1",
        timeframe="tonight",
    )
    base.update(over)
    return CarouselConfig(**base)


def _assignment(**over):
    base = dict(
        hook_type="edition_anchor",
        emotion_register="excitement",
        slide_count_band="5-7",
        caption_style="short_punch",
        cta_type="send_to_friend",
        post_slot="late_afternoon",
        media_type="image",
    )
    base.update(over)
    return base


def _events(n=6, confidence="confirmed"):
    return [_event(i, confidence=confidence) for i in range(1, n + 1)]


def _draft(events=None, config=None, **assign_over):
    return build_carousel(
        events or _events(),
        config or _config(),
        _assignment(**assign_over),
        reference_date=REF_DATE,
    )


def _current_states(draft, confidence="confirmed", status="scheduled"):
    return {
        s.event_id: {"confidence": confidence, "event_status": status}
        for s in draft.slides
        if s.kind == "event"
    }


def _approve(draft, who="Sean Schubert"):
    return approve(draft, who, "2026-07-24T18:00:00-05:00", signing_key=TEST_KEY)


def _release(draft, approval=None, policy=None, states=None):
    return release_for_publish(
        draft,
        states if states is not None else _current_states(draft),
        approval,
        policy,
        verification_key=TEST_KEY,
    )


# --- Trust selection (spec SS1) ------------------------------------------------

def test_confirmed_and_likely_are_featurable_disputed_unverified_never():
    events = [
        _event(1, "confirmed"),
        _event(2, "likely"),
        _event(3, "disputed"),
        _event(4, "unverified"),
    ]
    selected = select_featurable(events)
    ids = {e["event_id"] for e in selected}
    assert ids == {"ev-1", "ev-2"}


def test_confirmed_sorts_ahead_of_likely():
    events = [_event(1, "likely"), _event(2, "confirmed")]
    assert [e["event_id"] for e in select_featurable(events)] == ["ev-2", "ev-1"]


def test_unknown_confidence_state_fails_loud():
    with pytest.raises(CarouselTrustError, match="unknown confidence"):
        select_featurable([_event(1, confidence="banana")])


def test_non_canonical_origin_is_refused():
    with pytest.raises(CarouselTrustError, match="never amplified"):
        select_featurable([_event(1, origin="candidate_store")])


def test_cancelled_and_moved_events_are_not_featured():
    events = [
        _event(1, event_status="cancelled"),
        _event(2, event_status="moved"),
        _event(3, event_status="scheduled"),
    ]
    assert [e["event_id"] for e in select_featurable(events)] == ["ev-3"]


def test_unknown_event_status_fails_loud():
    with pytest.raises(CarouselTrustError, match="unknown event_status"):
        select_featurable([_event(1, event_status="postponed?")])


def test_missing_required_fields_fail_loud():
    broken = _event(1)
    del broken["venue_name"]
    with pytest.raises(CarouselTrustError, match="missing required fields"):
        select_featurable([broken])


def test_likely_slides_carry_the_uncertainty_marker():
    draft = _draft([_event(1, "likely"), _event(2, "confirmed"), _event(3)])
    likely = [s for s in draft.slides if s.event_id == "ev-1"]
    confirmed = [s for s in draft.slides if s.event_id == "ev-2"]
    assert likely[0].uncertainty_marker is True
    assert confirmed[0].uncertainty_marker is False


def test_empty_or_all_unfeaturable_lineup_refuses_to_build():
    with pytest.raises(NoFeaturableEvents):
        build_carousel(
            [_event(1, "disputed")], _config(), _assignment(), reference_date=REF_DATE
        )


def test_descriptor_without_foundry_provenance_is_refused():
    bad = _event(1, foundry_descriptor={"text": "great vibes"})
    with pytest.raises(CarouselTrustError, match="Descriptor Foundry provenance"):
        select_featurable([bad])


def test_descriptor_with_provenance_lands_on_slide():
    good = _event(
        1,
        foundry_descriptor={"text": "Loud honest rock", "provenance": "foundry:v3:abc"},
    )
    draft = _draft([good, _event(2), _event(3)])
    slide = next(s for s in draft.slides if s.event_id == "ev-1")
    assert "Loud honest rock" in slide.overlay_lines


# --- Truthful time framing (evaluator r1) --------------------------------------

def test_timeframe_windows():
    assert within_timeframe("2026-07-24T21:00:00-05:00", REF_DATE, "tonight")
    assert not within_timeframe("2026-07-25T21:00:00-05:00", REF_DATE, "tonight")
    assert within_timeframe("2026-07-29T21:00:00-05:00", REF_DATE, "this_week")
    assert not within_timeframe("2026-08-10T21:00:00-05:00", REF_DATE, "this_week")
    assert not within_timeframe("2026-07-23T21:00:00-05:00", REF_DATE, "this_week")  # past


def test_tonight_carousel_excludes_out_of_window_events():
    events = [_event(1), _event(2), _event(3, start_time="2026-08-02T20:00:00-05:00")]
    draft = _draft(events)
    assert "ev-3" not in {s.event_id for s in draft.slides}


def test_all_events_outside_window_is_a_no_featurable_skip():
    with pytest.raises(NoFeaturableEvents, match="window"):
        build_carousel(
            [_event(1, start_time="2026-09-01T20:00:00-05:00")],
            _config(),
            _assignment(),
            reference_date=REF_DATE,
        )


def test_weekly_series_copy_claims_this_week_not_tonight():
    events = [_event(1, start_time="2026-07-27T20:00:00-05:00"), _event(2, start_time="2026-07-28T20:00:00-05:00")]
    draft = _draft(events, config=_config(timeframe="this_week"))
    assert "This week" in draft.caption
    copy_body = draft.caption.split("\nReal listings")[0]  # copy, not the URL path
    assert "tonight" not in copy_body.lower()
    # Beyond tonight the date is part of the fact on every event slide.
    event_slide = next(s for s in draft.slides if s.kind == "event")
    assert "Jul" in event_slide.overlay_lines[1]


# --- Draft anatomy + format physics (spec SS2) ---------------------------------

def test_draft_anatomy_hook_events_cta():
    draft = _draft()
    kinds = [s.kind for s in draft.slides]
    assert kinds[0] == "hook"
    assert kinds[-1] == "cta"
    assert all(k == "event" for k in kinds[1:-1])


def test_every_slide_has_alt_text_and_events_have_provenance():
    draft = _draft()
    assert all(s.alt_text for s in draft.slides)
    for slide in draft.slides:
        if slide.kind == "event":
            assert slide.event_id and slide.source and slide.confidence


def test_slide_count_respects_band_and_surface_bounds():
    draft = _draft(_events(20), slide_count_band="5-7")
    assert len(draft.slides) <= 7
    fb = build_carousel(
        _events(20),
        _config(surface="facebook_page"),
        _assignment(slide_count_band="11-14"),
        reference_date=REF_DATE,
    )
    assert len(fb.slides) <= 10  # surface cap binds under the wider band


def test_number_promise_hook_uses_real_counts_only():
    events = _events(3)
    draft = _draft(events, hook_type="number_promise")
    assert "3" in draft.slides[0].headline


def test_banned_claim_language_refused_at_generation():
    shady = _event(1, name="Confirmed sellout night")
    with pytest.raises(CarouselTrustError, match="banned claim phrase"):
        _draft([shady, _event(2), _event(3)])


def test_caption_carries_utm_short_link():
    draft = _draft()
    assert "utm_source=instagram_feed" in draft.short_link
    assert draft.short_link in draft.caption


def test_invalid_assignment_fails_loud():
    with pytest.raises(ValueError, match="unknown level"):
        _draft(hook_type="clickbait")
    with pytest.raises(ValueError, match="missing factors"):
        validate_assignment({"hook_type": "awe"})


# --- Publish gate custody (spec SS1/SS10) --------------------------------------

def test_ai_identities_cannot_approve():
    draft = _draft()
    for identity in ("onelive-carousel-agent", "Claude", "gpt-5.5", "some-bot"):
        with pytest.raises(ValueError, match="AI never publishes"):
            approve(draft, identity, "2026-07-24T18:00:00-05:00", signing_key=TEST_KEY)


def test_approval_without_key_is_refused(monkeypatch):
    monkeypatch.delenv("ONELIVE_APPROVAL_KEY", raising=False)
    with pytest.raises(ValueError, match="no approval key"):
        approve(_draft(), "Sean Schubert", "2026-07-24T18:00:00-05:00")


def test_release_without_key_is_refused(monkeypatch):
    monkeypatch.delenv("ONELIVE_APPROVAL_KEY", raising=False)
    draft = _draft()
    approval = _approve(draft)
    with pytest.raises(ValueError, match="no approval key"):
        release_for_publish(draft, _current_states(draft), approval)


def test_forged_approval_signature_is_refused():
    draft = _draft()
    forged = Approval(
        draft_hash=content_hash(draft),
        approved_by="Sean Schubert",
        approved_at="2026-07-24T18:00:00-05:00",
        signature="deadbeef" * 8,
    )
    with pytest.raises(ValueError, match="signature does not verify"):
        _release(draft, forged)


def test_approval_signed_with_wrong_key_is_refused():
    draft = _draft()
    wrong = approve(
        draft, "Sean Schubert", "2026-07-24T18:00:00-05:00", signing_key="not-the-key"
    )
    with pytest.raises(ValueError, match="signature does not verify"):
        _release(draft, wrong)


def test_signed_human_approval_releases():
    draft = _draft()
    release = _release(draft, _approve(draft))
    assert release.draft_hash == content_hash(draft)
    assert release.released_by == "Sean Schubert"


def test_edit_after_approval_voids_the_approval():
    draft = _draft()
    approval = _approve(draft)
    edited = _draft(caption_style="list")
    assert content_hash(edited) != content_hash(draft)
    with pytest.raises(ValueError, match="approval is void"):
        _release(edited, approval)


def test_release_rechecks_current_confidence():
    draft = _draft()
    approval = _approve(draft)
    states = _current_states(draft)
    first = next(iter(states))
    states[first] = {"confidence": "disputed", "event_status": "scheduled"}
    with pytest.raises(ValueError, match="not settled"):
        _release(draft, approval, states=states)


def test_release_rechecks_current_event_status():
    draft = _draft()
    approval = _approve(draft)
    states = _current_states(draft)
    first = next(iter(states))
    states[first] = {"confidence": "confirmed", "event_status": "cancelled"}
    with pytest.raises(ValueError, match="only scheduled"):
        _release(draft, approval, states=states)


def test_release_refuses_unknown_current_state():
    draft = _draft()
    with pytest.raises(ValueError, match="no current state"):
        _release(draft, _approve(draft), states={})


def test_release_rescans_full_draft_content():
    draft = _draft()
    # A mutated/hand-built draft with banned caption language must be caught
    # by the FINAL guard itself, regardless of what the generator did.
    tampered = dataclasses.replace(draft, caption=draft.caption + " Guaranteed sellout!")
    with pytest.raises(ValueError, match="banned claim phrase"):
        _release(tampered, _approve(tampered))


def test_no_approval_defaults_to_l0_refusal():
    draft = _draft()
    with pytest.raises(ValueError, match="human in the loop"):
        _release(draft, policy=AutonomyPolicy(level="L0"))


# --- Autonomy ratification (spec SS10) -----------------------------------------

def _signed_record(tmp_path, payload, key=TEST_KEY):
    payload = dict(payload)
    payload["signature"] = sign_autonomy_record(payload, key)
    record = tmp_path / "a.json"
    record.write_text(json.dumps(payload))
    return str(record)


def _l1_payload():
    return {
        "level": "L1",
        "scopes": [{"surface": "instagram_feed", "tier": "T1"}],
        "founder": "Sean Schubert",
        "ratified_on": "2026-08-01",
        "decision_record": "docs/memory/decisions/2026-08-01_autonomy-l1.md",
    }


def test_absent_record_is_l0(tmp_path):
    policy = load_policy(str(tmp_path / "nope.json"), verification_key=TEST_KEY)
    assert policy.level == "L0"
    assert not policy.allows_auto_release("instagram_feed", "T1")


def test_signed_l1_scope_enumeration_is_exact(tmp_path):
    path = _signed_record(tmp_path, _l1_payload())
    policy = load_policy(path, verification_key=TEST_KEY)
    assert policy.allows_auto_release("instagram_feed", "T1")
    assert not policy.allows_auto_release("instagram_feed", "T2")
    assert not policy.allows_auto_release("facebook_page", "T1")
    draft = _draft()
    release = _release(draft, policy=policy)
    assert release.released_by == "autonomy:L1"


def test_unsigned_record_refuses(tmp_path):
    payload = _l1_payload()
    record = tmp_path / "a.json"
    record.write_text(json.dumps(payload))
    with pytest.raises(AutonomyRecordError, match="UNSIGNED"):
        load_policy(str(record), verification_key=TEST_KEY)


def test_wrong_key_signature_refuses(tmp_path):
    path = _signed_record(tmp_path, _l1_payload(), key="attacker-key")
    with pytest.raises(AutonomyRecordError, match="does not verify"):
        load_policy(path, verification_key=TEST_KEY)


def test_tampered_record_refuses(tmp_path):
    payload = _l1_payload()
    payload["signature"] = sign_autonomy_record(payload, TEST_KEY)
    payload["scopes"] = [{"surface": "facebook_page", "tier": "T3"}]  # post-sign edit
    record = tmp_path / "a.json"
    record.write_text(json.dumps(payload))
    with pytest.raises(AutonomyRecordError, match="does not verify"):
        load_policy(str(record), verification_key=TEST_KEY)


def test_no_verification_key_refuses_grants(tmp_path, monkeypatch):
    monkeypatch.delenv("ONELIVE_APPROVAL_KEY", raising=False)
    path = _signed_record(tmp_path, _l1_payload())
    with pytest.raises(AutonomyRecordError, match="cannot authenticate"):
        load_policy(path)


def test_l2_requires_attribution(tmp_path):
    with pytest.raises(AutonomyRecordError, match="unattributed grant"):
        load_policy(_signed_record(tmp_path, {"level": "L2"}), verification_key=TEST_KEY)
    payload = {
        "level": "L2",
        "founder": "Sean Schubert",
        "ratified_on": "2026-09-01",
        "decision_record": "docs/memory/decisions/2026-09-01_autonomy-l2.md",
    }
    policy = load_policy(_signed_record(tmp_path, payload), verification_key=TEST_KEY)
    assert policy.allows_auto_release("facebook_page", "T3")


def test_malformed_record_fails_closed_not_open(tmp_path):
    record = tmp_path / "a.json"
    record.write_text("{not json")
    with pytest.raises(AutonomyRecordError):
        load_policy(str(record), verification_key=TEST_KEY)
    record.write_text(json.dumps({"level": "L9"}))
    with pytest.raises(AutonomyRecordError, match="unknown level"):
        load_policy(str(record), verification_key=TEST_KEY)
    payload = {"level": "L1", "founder": "S", "ratified_on": "d", "decision_record": "r"}
    with pytest.raises(AutonomyRecordError, match="enumerate scopes"):
        load_policy(_signed_record(tmp_path, payload), verification_key=TEST_KEY)


def test_no_ratification_record_is_committed_yet():
    # The repo must ship in L0: the record appears only via the founder's
    # three-step sign-off (spec SS10).
    from social.carousel.autonomy import DEFAULT_RECORD_PATH

    assert not os.path.exists(DEFAULT_RECORD_PATH)


# --- The structural import guard -----------------------------------------------

def test_agent_loop_cannot_import_the_publish_path():
    """Same physics as orchestrator-cannot-import-promote: the autonomous
    loop must be structurally unable to reach the publisher or read the
    autonomy record. Parses the module source, so indirect renames fail too."""
    import social.carousel.agent_loop as agent_loop

    with open(agent_loop.__file__, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    for forbidden in ("publish_gate", "autonomy"):
        assert not any(forbidden in mod for mod in imported), (
            f"agent_loop imports {forbidden} — the autonomous loop must never "
            "hold the publish path"
        )


# --- Bandit learning (spec SS6) ------------------------------------------------

def test_bandit_is_deterministic_under_a_seed():
    a = ThompsonBandit(seed=7)
    b = ThompsonBandit(seed=7)
    assert [a.sample_assignment() for _ in range(5)] == [
        b.sample_assignment() for _ in range(5)
    ]


def test_bandit_learns_toward_the_winning_level():
    bandit = ThompsonBandit(seed=3, exploration_floor=0.0)
    win = _assignment(hook_type="humor")
    lose = _assignment(hook_type="awe")
    for _ in range(60):
        bandit.update(win, reward=0.6, reach=2000)
        bandit.update(lose, reward=0.05, reach=2000)
    means = bandit.posterior_means()["hook_type"]
    assert means["humor"] > means["awe"]
    picks = [bandit.sample_assignment()["hook_type"] for _ in range(50)]
    assert picks.count("humor") > picks.count("awe")


def test_bandit_rejects_bad_reward_and_reach():
    bandit = ThompsonBandit(seed=1)
    with pytest.raises(ValueError, match="reward"):
        bandit.update(_assignment(), reward=1.5, reach=100)
    with pytest.raises(ValueError, match="reach"):
        bandit.update(_assignment(), reward=0.5, reach=0)


def test_viral_outlier_cannot_freeze_learning():
    bandit = ThompsonBandit(seed=1)
    bandit.update(_assignment(), reward=1.0, reach=10_000_000)
    post = bandit.posteriors["hook_type"][_assignment()["hook_type"]]
    assert post["alpha"] + post["beta"] <= 2.0 + 20.0 + 1e-9  # priors + MAX_PSEUDO cap


def test_decay_shrinks_toward_prior_and_roundtrip_serialization():
    bandit = ThompsonBandit(seed=2)
    bandit.update(_assignment(), reward=0.9, reach=5000)
    before = bandit.posteriors["hook_type"][_assignment()["hook_type"]]["alpha"]
    bandit.decay(0.5)
    after = bandit.posteriors["hook_type"][_assignment()["hook_type"]]["alpha"]
    assert 1.0 < after < before
    restored = ThompsonBandit.from_json(bandit.to_json(), seed=2)
    assert restored.posteriors == bandit.posteriors


def test_exploration_floor_keeps_losers_measurable():
    bandit = ThompsonBandit(seed=5, exploration_floor=0.5)
    lose = _assignment(hook_type="awe")
    for _ in range(40):
        bandit.update(lose, reward=0.01, reach=2000)
    picks = {bandit.sample_assignment()["hook_type"] for _ in range(200)}
    assert "awe" in picks  # even a loser keeps getting occasional data


# --- Metrics + the improvement ratchet (spec SS6) ------------------------------

def _metrics(i, rate, surface="instagram_feed", tier="T1"):
    reach = 1000
    return PostMetrics(
        post_id=f"p{i}",
        surface=surface,
        tier=tier,
        posted_at=f"2026-07-{10 + i:02d}T17:00:00-05:00",
        reach=reach,
        unique_interactions=int(reach * rate),
        saves=10,
        shares=5,
        link_clicks=8,
    )


def test_metrics_validation_fails_loud():
    with pytest.raises(ValueError, match="reach"):
        PostMetrics(
            post_id="p", surface="instagram_feed", tier="T1",
            posted_at="2026-07-24", reach=0, unique_interactions=0,
        ).validate()
    with pytest.raises(ValueError, match="cannot exceed reach"):
        PostMetrics(
            post_id="p", surface="instagram_feed", tier="T1",
            posted_at="2026-07-24", reach=10, unique_interactions=11,
        ).validate()


def test_improvement_ratchet_flags_progress_and_regression():
    ledger = MetricsLedger()
    for i, rate in enumerate((0.10, 0.12, 0.15), start=1):
        ledger.record(_metrics(i, rate), _assignment())
    report = ledger.improvement_report()["instagram_feed|T1"]
    assert report["improved"] is True and report["regressed"] is False
    ledger.record(_metrics(4, 0.05), _assignment())
    report = ledger.improvement_report()["instagram_feed|T1"]
    assert report["regressed"] is True


def test_ledger_roundtrip():
    ledger = MetricsLedger()
    ledger.record(_metrics(1, 0.2), _assignment())
    restored = MetricsLedger.from_json(ledger.to_json())
    assert restored.rows[0].metrics.interaction_rate == pytest.approx(0.2)


# --- Tiering (spec SS5) --------------------------------------------------------

def test_tiers_follow_volume():
    counts = {"live-music": 30.0, "comedy": 7.0, "dance": 2.0, "film": 0.2}
    tiers = assign_tiers(counts)
    assert tiers == {"live-music": "T1", "comedy": "T2", "dance": "T3", "film": None}


def test_negative_count_fails_loud():
    with pytest.raises(ValueError, match="negative"):
        assign_tiers({"live-music": -1.0})


def test_portfolio_shapes_no_thin_solo_carousels_and_truthful_timeframes():
    counts = {"live-music": 30.0, "comedy": 7.0, "dance": 2.0, "literary": 1.5, "film": 0.2}
    portfolio = plan_portfolio(counts)
    by_key = {s.series_key: s for s in portfolio}
    assert "tonight_all" in by_key and "t1_live-music" in by_key and "t2_comedy" in by_key
    combined = by_key["t3_everything_else"]
    assert set(combined.domain_ids) == {"dance", "literary"}
    assert not any(k.startswith("t3_") and k != "t3_everything_else" for k in by_key)
    assert "film" not in {
        d for s in portfolio for d in s.domain_ids if s.series_key != "tonight_all"
    }
    # cadence and claimed window can never disagree
    assert by_key["t1_live-music"].timeframe == "tonight"
    assert by_key["t2_comedy"].timeframe == "this_week"
    assert combined.timeframe == "this_month"


def test_threshold_ordering_enforced():
    with pytest.raises(ValueError, match="strictly ordered"):
        assign_tiers({"a": 1.0}, TierThresholds(t1_weekly=2, t2_weekly=5, t3_weekly=1))


# --- GEO / discovery (spec SS8) ------------------------------------------------

def test_domain_tags_cover_the_full_canonical_taxonomy():
    from worker.importers.domain_map import DOMAINS

    assert set(DOMAIN_TAGS) == set(DOMAINS)


def test_event_jsonld_is_valid_and_attributed():
    doc = event_jsonld(_event(1), "Austin")
    assert doc["@type"] == "Event"
    assert doc["isBasedOn"] == "ticketmaster"
    assert doc["location"]["address"]["addressLocality"] == "Austin"
    json.dumps(doc)  # serializable


def test_event_jsonld_never_invents_missing_fields():
    minimal = _event(1)
    minimal.pop("price_min")
    minimal.pop("image_url")
    doc = event_jsonld(minimal, "Austin")
    assert "offers" not in doc and "image" not in doc


def test_hashtags_specific_capped_and_deduped():
    tags = hashtags_for("Austin", _events(8))
    assert 3 <= len(tags) <= 5
    assert len(set(tags)) == len(tags)
    assert tags[0] == "#austin"


def test_discovery_bundle_complete():
    draft = _draft()
    featured_ids = {s.event_id for s in draft.slides if s.kind == "event"}
    featured = [e for e in _events() if e["event_id"] in featured_ids]
    bundle = discovery_bundle(draft, featured, "Austin")
    assert bundle["carousel_jsonld"]["@type"] == "SocialMediaPosting"
    assert len(bundle["event_jsonld"]) == len(featured)
    assert bundle["og_tags"]["og:site_name"] == "OneLive"
    assert "confidence:" in bundle["llms_txt_block"]
    assert all(bundle["alt_texts"])


# --- The agent cycle (spec SS6) ------------------------------------------------

def _brand():
    return BrandIdentity(
        city="Austin", handle="@onelive.atx", short_link_base="https://onelive.app/tonight"
    )


def _cycle(events, counts, **over):
    base = dict(
        events=events,
        weekly_confirmed_counts=counts,
        bandit=ThompsonBandit(seed=11),
        brand=_brand(),
        max_drafts=10,
        reference_date=REF_DATE,
    )
    base.update(over)
    return run_cycle(**base)


def test_run_cycle_produces_drafts_and_telemetry():
    events = _events(8) + [_event(20, domain="comedy"), _event(21, domain="comedy")]
    pings = []
    result = _cycle(
        events, {"live-music": 20.0, "comedy": 6.0}, deadman_ping=pings.append
    )
    assert pings == ["start", "end"]
    assert result.drafts and len(result.discovery_bundles) == len(result.drafts)
    assert result.posterior_means
    assert all(d.author == "onelive-carousel-agent" for d in result.drafts)


def test_run_cycle_budget_cap_is_hard_and_skips_are_recorded():
    events = _events(8) + [_event(20, domain="comedy"), _event(21, domain="comedy")]
    result = _cycle(events, {"live-music": 20.0, "comedy": 6.0}, max_drafts=1)
    assert len(result.drafts) == 1
    assert any("budget cap" in reason for _, reason in result.skipped_series)
    with pytest.raises(ValueError, match="max_drafts"):
        _cycle(events, {"live-music": 20.0}, max_drafts=0)


def test_run_cycle_records_only_the_no_featurable_skip():
    result = _cycle([_event(1, "disputed", domain="comedy")], {"comedy": 6.0})
    assert not result.drafts
    assert result.skipped_series and all(reason for _, reason in result.skipped_series)


def test_run_cycle_propagates_trust_errors_loud():
    # Unknown confidence must NOT become a silent skip (evaluator r1).
    with pytest.raises(CarouselTrustError, match="unknown confidence"):
        _cycle([_event(1, confidence="banana", domain="comedy")], {"comedy": 6.0})
    # Non-canonical origin propagates.
    with pytest.raises(CarouselTrustError, match="never amplified"):
        _cycle([_event(1, origin="candidate_store", domain="comedy")], {"comedy": 6.0})
    # Foundry-less descriptor propagates.
    with pytest.raises(CarouselTrustError, match="Descriptor Foundry"):
        _cycle(
            [_event(1, domain="comedy", foundry_descriptor={"text": "vibes"})],
            {"comedy": 6.0},
        )
    # Banned claim language propagates.
    with pytest.raises(CarouselTrustError, match="banned claim phrase"):
        _cycle([_event(1, domain="comedy", name="Guaranteed fun")], {"comedy": 6.0})


def test_ingest_results_updates_learner_and_reports():
    bandit = ThompsonBandit(seed=9)
    ledger = MetricsLedger()
    outcomes = [
        (_assignment(), _metrics(1, 0.10)),
        (_assignment(hook_type="humor"), _metrics(2, 0.30)),
    ]
    report = ingest_results(bandit=bandit, ledger=ledger, outcomes=outcomes, decay_gamma=0.99)
    assert bandit.updates_seen == 2
    assert "instagram_feed|T1" in report
