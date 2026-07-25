"""Meta carousel engine: trust physics, gate custody, learning, GEO.

Covers (spec: docs/strategy/ONE_LIVE_META_CAROUSEL_ENGINE_v1.md; hardened
at the PR #63 evaluator's r1; reshaped by the founder's 2026-07-24
listicle + future-only directive):
- selection rules: confirmed/likely featurable, unverified/disputed never,
  CANONICAL-origin rows only, event_status `scheduled` only, unknown
  states fail loud;
- FUTURE-ONLY truthful windows at timestamp precision: a 6pm carousel
  never contains a 5:30pm start, "Tonight" is an evening claim, and the
  release gate re-checks with its own clock;
- the listicle canon: every hook is "<N> <blank> to experience <Today |
  Tonight | This weekend>", N is exactly 5 or 7, never padded;
- scenario carousels (date night, music & dancing, weekend planner, free
  tonight, family day) grounded in the voice-search personas;
- publish-gate custody: HMAC-signed approvals under the founder-held key,
  hash-bound, current confidence+status+future re-check, full-text rescan;
  signature-verified autonomy record fail-closed L0/L1/L2;
- the structural guard: agent_loop cannot import publish_gate/autonomy;
- the typed error boundary: only NoFeaturableEvents skips; trust errors
  propagate loud;
- bandit determinism/learning/decay; volume tiering; GEO bundle validity.
"""
import ast
import dataclasses
import json
import os
from datetime import datetime

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
from social.carousel.example_fixtures import EXAMPLE_EVENTS, EXAMPLE_REFERENCE_TIME
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
import social.carousel.autonomy as autonomy_module
import social.carousel.publish_gate as publish_gate
from social.carousel.publish_gate import Approval, approve, release_for_publish
from social.carousel.scenarios import (
    SCENARIOS,
    scenario_by_key,
    scenario_config,
    scenario_events,
)
from social.carousel.tiers import TierThresholds, assign_tiers, plan_portfolio

TEST_KEY = "test-founder-approval-key-4f8a2c9d7e1b"  # >=32 bytes (r14 floor)
REF_TIME = "2026-07-24T12:00:00-05:00"  # Friday noon, Austin

# Captured BEFORE any test patches it: the repo's real canonical record path.
_REAL_RECORD_PATH = autonomy_module.DEFAULT_RECORD_PATH


def _default_reader(event_ids):
    # Full canonical rows (r4): regenerate the fixture recipe per id so
    # release-time fact verification sees exactly what generation saw.
    return {eid: _event(int(eid.split("-")[1])) for eid in event_ids}


class _DurableTestJournal:
    """Test double for the release journal. `durable = True` is the r14
    registration attestation — REAL durability lives in the ops-console
    store at R-026; here the flag exercises the gate's requirement."""

    durable = True

    def __init__(self):
        self._by_day = {}

    def count_on(self, day):
        return len(self._by_day.get(day, []))

    def record(self, release, moment):
        self._by_day.setdefault(moment.date(), []).append(release)


@pytest.fixture(autouse=True)
def _custody_env(monkeypatch, tmp_path):
    """Deployment-shaped custody config for every test (r3): the approval
    key lives in env, the canonical record path points at an (absent)
    tmp file so tests start in L0, a canonical-store reader is registered,
    the gate clock (r11: never an API parameter) is pinned to REF_TIME,
    and a fresh release journal is registered. Individual tests override
    by monkeypatching further."""
    monkeypatch.setenv("ONELIVE_APPROVAL_KEY", TEST_KEY)
    monkeypatch.setattr(
        autonomy_module, "DEFAULT_RECORD_PATH", str(tmp_path / "AUTONOMY_RATIFICATION.json")
    )
    monkeypatch.setattr(publish_gate, "_STATE_READER", _default_reader)
    monkeypatch.setattr(publish_gate, "_utcnow", lambda: datetime.fromisoformat(REF_TIME))
    monkeypatch.setattr(publish_gate, "_RELEASE_JOURNAL", _DurableTestJournal())
    # r13: approval is allowlist membership — the deployment registers the
    # humans its auth surface has actually authenticated.
    monkeypatch.setattr(publish_gate, "_APPROVER_REGISTRY", frozenset({"Sean Schubert"}))
    yield


def _event(i=1, confidence="confirmed", domain="live-music", **over):
    base = dict(
        event_id=f"ev-{i}",
        name=f"Test Show {i}",
        venue_name="Mohawk",
        start_time=f"2026-07-24T2{i % 4}:00:00-05:00",  # 20:00-23:00, all tonight
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
        listicle_size="5",
        caption_style="short_punch",
        cta_type="send_to_friend",
        post_slot="late_afternoon",
        media_type="image",
    )
    base.update(over)
    return base


def _events(n=6, confidence="confirmed"):
    return [_event(i, confidence=confidence) for i in range(1, n + 1)]


def _draft(events=None, config=None, reference_time=REF_TIME, **assign_over):
    return build_carousel(
        events or _events(),
        config or _config(),
        _assignment(**assign_over),
        reference_time=reference_time,
    )


def _current_states(draft, confidence="confirmed", status="scheduled"):
    return {
        s.event_id: {"confidence": confidence, "event_status": status}
        for s in draft.slides
        if s.kind == "event"
    }


def _approve(draft, who="Sean Schubert"):
    return approve(draft, who, "2026-07-24T18:00:00-05:00")


def _release(draft, approval=None):
    return release_for_publish(draft, approval)


def _reader_returning(states):
    return lambda event_ids: states


def _rows_for(draft, **overrides):
    rows = _default_reader([s.event_id for s in draft.slides if s.kind == "event"])
    for eid, extra in overrides.items():
        rows[eid] = {**rows[eid], **extra}
    return rows


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
    # Exactly 5 featurable so the likely event is certainly featured.
    events = [_event(1, "likely")] + [_event(i) for i in range(2, 6)]
    draft = _draft(events)
    likely = [s for s in draft.slides if s.event_id == "ev-1"]
    assert likely and likely[0].uncertainty_marker is True
    confirmed = [s for s in draft.slides if s.kind == "event" and s.event_id != "ev-1"]
    assert confirmed and all(s.uncertainty_marker is False for s in confirmed)


def test_descriptor_without_foundry_provenance_is_refused():
    bad = _event(1, foundry_descriptor={"text": "great vibes"})
    with pytest.raises(CarouselTrustError, match="Descriptor Foundry provenance"):
        select_featurable([bad])


def test_descriptor_with_provenance_lands_on_slide():
    good = _event(
        1,
        foundry_descriptor={"text": "Loud honest rock", "provenance": "foundry:v3:abc"},
    )
    draft = _draft([good] + _events(6)[1:])
    slide = next(s for s in draft.slides if s.event_id == "ev-1")
    assert "Loud honest rock" in slide.overlay_lines


# --- Future-only truthful windows (founder directive 2026-07-24) ---------------

def test_already_started_events_never_qualify_in_any_window():
    six_pm = "2026-07-24T18:00:00-05:00"
    for timeframe in ("today", "tonight", "this_weekend"):
        assert not within_timeframe("2026-07-24T17:30:00-05:00", six_pm, timeframe)
        assert not within_timeframe("2026-07-24T12:00:00-05:00", six_pm, timeframe)
        # r2 blocker: starting at this exact instant is not "to happen".
        assert not within_timeframe(six_pm, six_pm, timeframe)


def test_today_vs_tonight_semantics():
    morning = "2026-07-24T11:00:00-05:00"
    matinee = "2026-07-24T14:00:00-05:00"
    evening = "2026-07-24T20:00:00-05:00"
    tomorrow = "2026-07-25T20:00:00-05:00"
    assert within_timeframe(matinee, morning, "today")
    assert not within_timeframe(matinee, morning, "tonight")  # 2pm is not Tonight
    assert within_timeframe(evening, morning, "tonight")
    assert not within_timeframe(tomorrow, morning, "today")
    assert not within_timeframe(tomorrow, morning, "tonight")


def test_weekend_window_covers_fri_through_sun_future_only():
    thursday = "2026-07-23T12:00:00-05:00"
    saturday_show = "2026-07-25T20:00:00-05:00"
    sunday_show = "2026-07-26T12:00:00-05:00"
    monday_show = "2026-07-27T20:00:00-05:00"
    assert within_timeframe(saturday_show, thursday, "this_weekend")
    assert within_timeframe(sunday_show, thursday, "this_weekend")
    assert not within_timeframe(monday_show, thursday, "this_weekend")
    # Mid-weekend reference: the remainder of THIS weekend, future-only.
    saturday_night = "2026-07-25T22:00:00-05:00"
    assert within_timeframe(sunday_show, saturday_night, "this_weekend")
    assert not within_timeframe(saturday_show, saturday_night, "this_weekend")  # started


def test_timezone_mismatch_fails_loud():
    with pytest.raises(CarouselTrustError, match="mismatch"):
        within_timeframe("2026-07-24T20:00:00", REF_TIME, "tonight")


def test_six_pm_carousel_excludes_earlier_start():
    events = _events(6) + [_event(30, start_time="2026-07-24T17:30:00-05:00")]
    draft = _draft(events, reference_time="2026-07-24T18:00:00-05:00")
    assert "ev-30" not in {s.event_id for s in draft.slides}


def test_all_events_outside_window_is_a_no_featurable_skip():
    with pytest.raises(NoFeaturableEvents, match="never padded"):
        build_carousel(
            [_event(1, start_time="2026-09-01T20:00:00-05:00")],
            _config(),
            _assignment(),
            reference_time=REF_TIME,
        )


def test_weekend_series_copy_and_dated_slides():
    events = [
        _event(i, start_time=f"2026-07-25T2{i % 3}:00:00-05:00") for i in range(1, 7)
    ]
    draft = _draft(events, config=_config(timeframe="this_weekend"))
    assert "This weekend" in draft.slides[0].headline
    copy_body = draft.caption.split("\nReal listings")[0]  # copy, not the URL path
    assert "tonight" not in copy_body.lower()
    event_slide = next(s for s in draft.slides if s.kind == "event")
    assert "Jul" in event_slide.overlay_lines[1]  # the date is part of the fact


# --- The listicle canon (founder directive 2026-07-24) -------------------------

def test_hook_is_the_listicle_format():
    draft = _draft()
    assert draft.slides[0].headline == "5 shows to experience Tonight"


def test_listicle_size_is_exactly_five_or_seven():
    draft5 = _draft(_events(20), listicle_size="5")
    assert sum(1 for s in draft5.slides if s.kind == "event") == 5
    draft7 = _draft(_events(20), listicle_size="7")
    assert sum(1 for s in draft7.slides if s.kind == "event") == 7


def test_sampled_seven_falls_back_to_five_when_supply_is_six():
    draft = _draft(_events(6), listicle_size="7")
    assert sum(1 for s in draft.slides if s.kind == "event") == 5
    assert draft.slides[0].headline.startswith("5 ")  # the promise stays exact


def test_below_five_featurable_never_posts():
    with pytest.raises(NoFeaturableEvents, match="never padded"):
        _draft(_events(4))


def test_price_promise_only_when_every_event_is_priced():
    draft = _draft(_events(7), hook_type="number_promise")
    # r5: honest minimum framing — never an "under" ceiling a $20 ticket falsifies.
    assert "from $20" in draft.slides[0].headline
    # Exactly 5 featurable, one unpriced -> the unpriced one IS featured,
    # so the honest fallback drops the price blank.
    unpriced = [_event(1, price_min=None)] + [_event(i) for i in range(2, 6)]
    fallback = _draft(unpriced, hook_type="number_promise")
    assert "under $" not in fallback.slides[0].headline
    assert "shows to experience Tonight" in fallback.slides[0].headline


def test_scenario_noun_lands_in_the_hook():
    config = _config(listicle_noun="date nights")
    draft = _draft(config=config)
    assert draft.slides[0].headline == "5 date nights to experience Tonight"


# --- Scenario carousels (founder directive; personas doc) ----------------------

def test_the_five_scenarios_exist():
    assert {s.key for s in SCENARIOS} == {
        "date_night",
        "music_and_dancing",
        "weekend_planner",
        "free_tonight",
        "family_day",
    }


def test_date_night_filters_to_later_starts():
    scenario = scenario_by_key("date_night")
    early = _event(1, domain="theater", start_time="2026-07-24T18:00:00-05:00")
    late = _event(2, domain="theater", start_time="2026-07-24T20:30:00-05:00")
    off_domain = _event(3, domain="sports", start_time="2026-07-24T21:00:00-05:00")
    picked = scenario_events([early, late, off_domain], scenario)
    assert [e["event_id"] for e in picked] == ["ev-2"]


def test_free_tonight_is_actually_free():
    scenario = scenario_by_key("free_tonight")
    free = _event(1, domain="comedy", price_min=0)
    cheap = _event(2, domain="comedy", price_min=5)
    unpriced = _event(3, domain="comedy", price_min=None)
    picked = scenario_events([free, cheap, unpriced], scenario)
    assert [e["event_id"] for e in picked] == ["ev-1"]


def test_all_five_example_scenarios_render_through_the_engine():
    for scenario in SCENARIOS:
        config = scenario_config(
            scenario,
            surface="instagram_feed",
            city="Austin",
            handle="@onelive.atx",
            short_link_base="https://onelive.app/tonight",
        )
        draft = build_carousel(
            scenario_events(EXAMPLE_EVENTS, scenario),
            config,
            _assignment(),
            reference_time=EXAMPLE_REFERENCE_TIME,
        )
        n = sum(1 for s in draft.slides if s.kind == "event")
        assert n in (5, 7)
        assert draft.slides[0].headline.startswith(f"{n} ")
        assert "to experience" in draft.slides[0].headline
        # the already-started fixture never appears
        assert "ex-28" not in {s.event_id for s in draft.slides}


def test_example_fixtures_are_marked_synthetic():
    assert all(e["source"] == "SYNTHETIC-EXAMPLE" for e in EXAMPLE_EVENTS)


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
            assert slide.start_time  # release-gate future check needs it


def test_banned_claim_language_refused_at_generation():
    shady = _event(1, name="Confirmed sellout night")
    with pytest.raises(CarouselTrustError, match="banned claim phrase"):
        _draft([shady] + _events(6)[1:])


def test_caption_carries_utm_short_link():
    draft = _draft()
    assert "utm_source=instagram_feed" in draft.short_link
    assert draft.short_link in draft.caption


def test_invalid_assignment_fails_loud():
    with pytest.raises(ValueError, match="unknown level"):
        _draft(hook_type="clickbait")
    with pytest.raises(ValueError, match="missing factors"):
        validate_assignment({"hook_type": "edition_anchor"})


# --- Publish gate custody (spec SS1/SS10) --------------------------------------

def test_ai_identities_cannot_approve():
    draft = _draft()
    for identity in ("onelive-carousel-agent", "Claude", "gpt-5.5", "some-bot"):
        with pytest.raises(ValueError, match="AI never publishes"):
            approve(draft, identity, "2026-07-24T18:00:00-05:00")


def test_unregistered_identity_cannot_approve_or_release():
    # r13 blockers: authorization is allowlist membership, not a denylist
    # miss — an unlisted "human" name mints nothing (the signing-oracle
    # shape), and a signed approval naming one still refuses at release.
    draft = _draft()
    with pytest.raises(ValueError, match="not in the registered approver"):
        approve(draft, "Jane Impostor", "2026-07-24T18:00:00-05:00")
    import hashlib as _hl
    import hmac as _hm

    h = content_hash(draft)
    who, when = "Jane Impostor", "2026-07-24T18:00:00-05:00"
    sig = _hm.new(
        TEST_KEY.encode(), "|".join((h, who, when)).encode(), _hl.sha256
    ).hexdigest()
    forged = Approval(draft_hash=h, approved_by=who, approved_at=when, signature=sig)
    with pytest.raises(ValueError, match="not in the registered approver"):
        _release(draft, forged)


def test_no_approver_registry_refuses_everything(monkeypatch):
    # r13: no registry = the gate cannot verify the approver — fail closed.
    draft = _draft()
    approval = _approve(draft)
    monkeypatch.setattr(publish_gate, "_APPROVER_REGISTRY", None)
    with pytest.raises(ValueError, match="no approver registry"):
        approve(draft, "Sean Schubert", "2026-07-24T18:00:00-05:00")
    with pytest.raises(ValueError, match="no approver registry"):
        _release(draft, approval)


def test_approver_registry_is_once_only_and_rejects_ai_names(monkeypatch):
    monkeypatch.setattr(publish_gate, "_APPROVER_REGISTRY", None)
    with pytest.raises(ValueError, match="never enters the approver registry"):
        publish_gate.configure_approvers(["Sean Schubert", "carousel-bot"])
    with pytest.raises(ValueError, match="cannot be empty"):
        publish_gate.configure_approvers([])
    publish_gate.configure_approvers(["Sean Schubert"])
    with pytest.raises(ValueError, match="already configured"):
        publish_gate.configure_approvers(["Sean Schubert"])


def test_approval_without_key_is_refused(monkeypatch):
    monkeypatch.delenv("ONELIVE_APPROVAL_KEY", raising=False)
    with pytest.raises(ValueError, match="no approval key"):
        approve(_draft(), "Sean Schubert", "2026-07-24T18:00:00-05:00")


def test_release_without_key_is_refused(monkeypatch):
    draft = _draft()
    approval = _approve(draft)
    monkeypatch.delenv("ONELIVE_APPROVAL_KEY", raising=False)
    with pytest.raises(ValueError, match="no approval key"):
        _release(draft, approval)


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


def test_approval_signed_under_a_different_key_is_refused(monkeypatch):
    draft = _draft()
    monkeypatch.setenv("ONELIVE_APPROVAL_KEY", "some-other-deployment-key-9c2f7a1e4d")
    wrong = _approve(draft)  # signed under the other key
    monkeypatch.setenv("ONELIVE_APPROVAL_KEY", TEST_KEY)
    with pytest.raises(ValueError, match="signature does not verify"):
        _release(draft, wrong)


def test_release_refuses_ai_identity_even_with_valid_signature():
    # r3 blocker: the custody boundary re-checks the approver identity —
    # a correctly signed approval naming an AI identity still refuses.
    import hashlib as _hl
    import hmac as _hm

    draft = _draft()
    h = content_hash(draft)
    who, when = "onelive-carousel-agent", "2026-07-24T18:00:00-05:00"
    sig = _hm.new(
        TEST_KEY.encode(), "|".join((h, who, when)).encode(), _hl.sha256
    ).hexdigest()
    forged = Approval(draft_hash=h, approved_by=who, approved_at=when, signature=sig)
    with pytest.raises(ValueError, match="AI never publishes"):
        _release(draft, forged)


def test_custody_api_accepts_no_keys_paths_or_state():
    # r3 blockers: the release API must not accept key material, record
    # paths, or caller-supplied trust state — deployment config only.
    import inspect

    release_params = set(inspect.signature(release_for_publish).parameters)
    assert release_params == {"draft", "approval"}  # r11: no clock parameter
    approve_params = set(inspect.signature(approve).parameters)
    assert approve_params == {"draft", "approved_by", "approved_at"}
    # r11 nit: the autonomy loader takes no path either.
    assert set(inspect.signature(load_policy).parameters) == set()


def test_handbuilt_shapeless_draft_never_releases(monkeypatch):
    # r4 blocker: a draft with zero event slides (or any non-listicle
    # shape) refuses at release regardless of a valid approval.
    draft = _draft()
    empty = dataclasses.replace(
        draft, slides=(draft.slides[0], draft.slides[-1]), discovery={}
    )
    approval = _approve(empty)
    with pytest.raises(ValueError, match="listicle canon"):
        _release(empty, approval)


def test_fabricated_name_never_releases(monkeypatch):
    # r4 blocker: a validly-approved draft whose slide asserts a name the
    # canonical store does not carry refuses at release.
    draft = _draft()
    slides = list(draft.slides)
    idx = next(i for i, s in enumerate(slides) if s.kind == "event")
    slides[idx] = dataclasses.replace(slides[idx], headline="Totally Invented Show")
    tampered = dataclasses.replace(draft, slides=tuple(slides))
    approval = _approve(tampered)
    with pytest.raises(ValueError, match="no fabrication"):
        _release(tampered, approval)


def test_tampered_discovery_bundle_never_releases(monkeypatch):
    # r4 blocker: machine-facing Event nodes must match the canonical store.
    draft = _draft()
    bundle = json.loads(json.dumps(draft.discovery))
    bundle["event_jsonld"][0]["name"] = "Totally Invented Show"
    tampered = dataclasses.replace(draft, discovery=bundle)
    approval = _approve(tampered)
    with pytest.raises(ValueError, match="re-derive"):
        _release(tampered, approval)


def test_discovery_bundle_is_hash_bound():
    draft = _draft()
    assert draft.discovery  # the bundle rides inside the draft
    bundle = json.loads(json.dumps(draft.discovery))
    bundle["og_tags"]["og:title"] = "changed"
    assert content_hash(dataclasses.replace(draft, discovery=bundle)) != content_hash(draft)


def test_banned_scan_is_word_boundary_end_to_end(monkeypatch):
    # r4/r5 nit: a band actually named "Confirmedly Great" is legitimate at
    # generation AND at release (both use the same word-boundary regex).
    rows = {1: _event(1, name="Confirmedly Great")}
    events = [rows[1]] + [_event(i) for i in range(2, 6)]
    draft = _draft(events)
    assert any("Confirmedly Great" in s.headline for s in draft.slides)
    reader_rows = {e["event_id"]: e for e in events}
    monkeypatch.setattr(publish_gate, "_STATE_READER", _reader_returning(reader_rows))
    release = _release(draft, _approve(draft))
    assert release.draft_hash == content_hash(draft)


def test_price_labels_are_exact_never_truncated():
    # r5 blockers: $19.99 is $19.99, never $19; $0.01 is never "free".
    cents = [_event(1, price_min=19.99), _event(2, price_min=0.01)] + [
        _event(i) for i in range(3, 6)
    ]
    draft = _draft(cents, hook_type="number_promise")
    texts = [line for s in draft.slides for line in s.overlay_lines]
    assert any("From $19.99" in t for t in texts)
    assert any("From $0.01" in t for t in texts)
    assert "free" not in draft.slides[0].headline.lower()
    assert "from $0.01" in draft.slides[0].headline


def test_duplicate_event_ids_fail_loud_at_generation():
    # r6 blocker: a listicle counts distinct events.
    dupes = [_event(1), _event(1)] + [_event(i) for i in range(2, 6)]
    with pytest.raises(CarouselTrustError, match="duplicate event id"):
        select_featurable(dupes)


def test_duplicate_event_ids_refuse_at_release():
    draft = _draft()
    slides = list(draft.slides)
    idx = next(i for i, s in enumerate(slides) if s.kind == "event")
    slides[idx + 1] = slides[idx]  # repeat the same event slide
    tampered = dataclasses.replace(draft, slides=tuple(slides))
    approval = _approve(tampered)
    with pytest.raises(ValueError, match="distinct events"):
        _release(tampered, approval)


def test_release_rechecks_approval_timestamp_shape():
    draft = _draft()
    good = _approve(draft)
    bad = Approval(
        draft_hash=good.draft_hash,
        approved_by=good.approved_by,
        approved_at="not-a-time",
        signature=good.signature,
    )
    with pytest.raises(ValueError, match="ISO 8601"):
        _release(draft, bad)


def test_missing_discovery_bundle_never_releases():
    # r5 blocker: discovery is required — a draft stripped of it refuses.
    draft = _draft()
    stripped = dataclasses.replace(draft, discovery={})
    approval = _approve(stripped)
    with pytest.raises(ValueError, match="re-derive"):
        _release(stripped, approval)


def test_no_state_reader_refuses_everything(monkeypatch):
    draft = _draft()
    approval = _approve(draft)
    monkeypatch.setattr(publish_gate, "_STATE_READER", None)
    with pytest.raises(ValueError, match="no canonical state reader"):
        _release(draft, approval)


def test_state_reader_registration_is_once_only(monkeypatch):
    monkeypatch.setattr(publish_gate, "_STATE_READER", None)
    publish_gate.configure_state_reader(_default_reader)
    with pytest.raises(ValueError, match="already configured"):
        publish_gate.configure_state_reader(_default_reader)


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


def test_release_rechecks_current_confidence(monkeypatch):
    draft = _draft()
    approval = _approve(draft)
    first = next(s.event_id for s in draft.slides if s.kind == "event")
    rows = _rows_for(draft, **{first: {"confidence": "disputed"}})
    monkeypatch.setattr(publish_gate, "_STATE_READER", _reader_returning(rows))
    with pytest.raises(ValueError, match="not settled"):
        _release(draft, approval)


def test_release_rechecks_current_event_status(monkeypatch):
    draft = _draft()
    approval = _approve(draft)
    first = next(s.event_id for s in draft.slides if s.kind == "event")
    rows = _rows_for(draft, **{first: {"event_status": "cancelled"}})
    monkeypatch.setattr(publish_gate, "_STATE_READER", _reader_returning(rows))
    with pytest.raises(ValueError, match="only scheduled"):
        _release(draft, approval)


def test_release_refuses_already_started_events(monkeypatch):
    draft = _draft()  # events start 20:00-23:00
    approval = _approve(draft)
    # r11: the caller cannot supply a friendlier clock — move the GATE'S
    # clock past the starts and the same approval refuses.
    monkeypatch.setattr(
        publish_gate,
        "_utcnow",
        lambda: datetime.fromisoformat("2026-07-24T23:30:00-05:00"),
    )
    with pytest.raises(ValueError, match="already started"):
        _release(draft, approval)


def test_release_clock_is_never_a_caller_input():
    # r11 blocker: reference_time as a parameter let the release subject
    # choose the clock that judges future-only — it no longer exists.
    draft = _draft()
    approval = _approve(draft)
    with pytest.raises(TypeError):
        release_for_publish(draft, approval, reference_time=REF_TIME)


def test_release_refuses_unknown_current_state(monkeypatch):
    draft = _draft()
    approval = _approve(draft)
    monkeypatch.setattr(publish_gate, "_STATE_READER", _reader_returning({}))
    with pytest.raises(ValueError, match="no state for"):
        _release(draft, approval)


def test_release_rescans_full_draft_content():
    draft = _draft()
    tampered = dataclasses.replace(draft, caption=draft.caption + " Guaranteed sellout!")
    # The total re-render hash catches ANY content drift before the belt.
    with pytest.raises(ValueError, match="re-derive"):
        _release(tampered, _approve(tampered))


def test_no_approval_defaults_to_l0_refusal():
    draft = _draft()
    with pytest.raises(ValueError, match="human in the loop"):
        _release(draft)


def test_unsigned_canonical_record_refuses_release(monkeypatch, tmp_path):
    record = tmp_path / "AUTONOMY_RATIFICATION.json"
    record.write_text(json.dumps(_l1_payload()))
    monkeypatch.setattr(autonomy_module, "DEFAULT_RECORD_PATH", str(record))
    draft = _draft()
    with pytest.raises(AutonomyRecordError, match="UNSIGNED"):
        _release(draft)


def test_bad_autonomy_record_refuses_even_human_approval(monkeypatch, tmp_path):
    # r12 blocker: a malformed/unauthenticated ratification artifact is a
    # corrupted trust-path file — the contract is refuse-EVERYTHING, so a
    # valid human approval must not release over it either.
    draft = _draft()
    approval = _approve(draft)
    record = tmp_path / "AUTONOMY_RATIFICATION.json"
    monkeypatch.setattr(autonomy_module, "DEFAULT_RECORD_PATH", str(record))
    record.write_text(json.dumps(_l1_payload()))  # present but unsigned
    with pytest.raises(AutonomyRecordError, match="UNSIGNED"):
        _release(draft, approval)
    tampered = dict(_l1_payload())
    tampered["signature"] = sign_autonomy_record(tampered, TEST_KEY)
    tampered["max_releases_per_day"] = 999  # post-sign edit
    record.write_text(json.dumps(tampered))
    with pytest.raises(AutonomyRecordError, match="does not verify"):
        _release(draft, approval)
    record.write_text("{not json")
    with pytest.raises(AutonomyRecordError, match="unreadable"):
        _release(draft, approval)
    # Absent file = L0, the ordinary state: the same approval releases.
    record.unlink()
    assert _release(draft, approval).released_by == "Sean Schubert"


def test_broken_tzinfo_clock_refuses_release(monkeypatch):
    # #67 r1: a tzinfo whose utcoffset() is None is NAIVE by Python's own
    # definition — the aware-moment check must catch it, not just tzinfo.
    import datetime as _dt

    class _BrokenTz(_dt.tzinfo):
        def utcoffset(self, dt):
            return None

        def dst(self, dt):
            return None

    draft = _draft()
    approval = _approve(draft)
    broken = datetime.fromisoformat(REF_TIME).replace(tzinfo=_BrokenTz())
    monkeypatch.setattr(publish_gate, "_utcnow", lambda: broken)
    with pytest.raises(ValueError, match="timezone-aware"):
        _release(draft, approval)


def test_event_jsonld_refuses_unscheduled_or_noncanonical_rows():
    # #67 r1: the public helper must not emit EventScheduled markup for a
    # cancelled or candidate row, regardless of caller.
    with pytest.raises(ValueError, match="only ever emitted for scheduled"):
        event_jsonld(_event(1, event_status="cancelled"), "Austin")
    with pytest.raises(ValueError, match="never get discovery markup"):
        event_jsonld(_event(1, origin="candidate_store"), "Austin")


def test_scenario_price_filter_normalizes_like_every_price_surface():
    # #67 r1 (adopting the r15 nit): "0" the string is free; garbage
    # raises the trust-error shape, never a raw TypeError.
    scenario = scenario_by_key("free_tonight")
    free_str = _event(1, domain="comedy", price_min="0")
    assert [e["event_id"] for e in scenario_events([free_str], scenario)] == ["ev-1"]
    with pytest.raises(CarouselTrustError, match="unparseable price_min"):
        scenario_events([_event(2, domain="comedy", price_min="abc")], scenario)


def test_utc_gate_clock_releases_market_tonight_after_utc_midnight(monkeypatch):
    # r12 nit: at 21:00 CDT the UTC calendar has already turned — the
    # window must be judged in the event's own timezone or every Austin
    # "Tonight" release after 19:00 CDT falsely refuses.
    starts = ["21:30", "21:45", "22:00", "22:30", "23:00"]
    events = [
        _event(i + 1, start_time=f"2026-07-24T{t}:00-05:00")
        for i, t in enumerate(starts)
    ]
    draft = _draft(events, reference_time="2026-07-24T20:00:00-05:00")
    monkeypatch.setattr(
        publish_gate, "_STATE_READER", _reader_returning({e["event_id"]: e for e in events})
    )
    # 02:00 UTC Jul 25 == 21:00 CDT Jul 24 — all five starts still ahead.
    monkeypatch.setattr(
        publish_gate,
        "_utcnow",
        lambda: datetime.fromisoformat("2026-07-25T02:00:00+00:00"),
    )
    release = _release(draft, _approve(draft))
    assert release.draft_hash == content_hash(draft)


# --- Autonomy ratification (spec SS10) -----------------------------------------

def _signed_record(tmp_path, payload, key=TEST_KEY):
    payload = dict(payload)
    payload["signature"] = sign_autonomy_record(payload, key)
    record = tmp_path / "a.json"
    record.write_text(json.dumps(payload))
    return str(record)


def _load_policy_at(path):
    # r11 nit: load_policy() reads the canonical path ONLY — hermetic tests
    # point DEFAULT_RECORD_PATH at their record, same as deployment layout.
    import unittest.mock as _mock

    with _mock.patch.object(autonomy_module, "DEFAULT_RECORD_PATH", str(path)):
        return load_policy()


def _l1_payload():
    from social.carousel.generator import renderer_fingerprint

    return {
        "level": "L1",
        "scopes": [{"surface": "instagram_feed", "tier": "T1"}],
        "founder": "Sean Schubert",
        "ratified_on": "2026-08-01",
        "decision_record": "docs/memory/decisions/2026-08-01_autonomy-l1.md",
        "renderer_version": renderer_fingerprint(),
        "series_keys": ["t1_live-music"],
        "max_releases_per_day": 2,
    }


def test_absent_record_is_l0(tmp_path):
    policy = _load_policy_at(tmp_path / "nope.json")
    assert policy.level == "L0"
    assert not policy.allows_auto_release("instagram_feed", "T1")


def test_signed_l1_scope_enumeration_is_exact(tmp_path):
    path = _signed_record(tmp_path, _l1_payload())
    policy = _load_policy_at(path)
    assert policy.allows_auto_release("instagram_feed", "T1")
    assert not policy.allows_auto_release("instagram_feed", "T2")
    assert not policy.allows_auto_release("facebook_page", "T1")
    import unittest.mock as _mock

    with _mock.patch.object(autonomy_module, "DEFAULT_RECORD_PATH", path):
        draft = _draft()
        release = _release(draft)
    assert release.released_by == "autonomy:L1"


def test_unsigned_record_refuses(tmp_path):
    record = tmp_path / "a.json"
    record.write_text(json.dumps(_l1_payload()))
    with pytest.raises(AutonomyRecordError, match="UNSIGNED"):
        _load_policy_at(record)


def test_wrong_key_signature_refuses(tmp_path):
    path = _signed_record(tmp_path, _l1_payload(), key="attacker-key-5b8e2a9c4f7d1e0a3b6c9d")
    with pytest.raises(AutonomyRecordError, match="does not verify"):
        _load_policy_at(path)


def test_tampered_record_refuses(tmp_path):
    payload = _l1_payload()
    payload["signature"] = sign_autonomy_record(payload, TEST_KEY)
    payload["scopes"] = [{"surface": "facebook_page", "tier": "T3"}]  # post-sign edit
    record = tmp_path / "a.json"
    record.write_text(json.dumps(payload))
    with pytest.raises(AutonomyRecordError, match="does not verify"):
        _load_policy_at(record)


def test_no_verification_key_refuses_grants(tmp_path, monkeypatch):
    path = _signed_record(tmp_path, _l1_payload())
    monkeypatch.delenv("ONELIVE_APPROVAL_KEY", raising=False)
    with pytest.raises(AutonomyRecordError, match="cannot authenticate"):
        _load_policy_at(path)


def test_l2_requires_attribution(tmp_path):
    with pytest.raises(AutonomyRecordError, match="unattributed grant"):
        _load_policy_at(_signed_record(tmp_path, {"level": "L2"}))
    from social.carousel.generator import renderer_fingerprint

    payload = {
        "level": "L2",
        "founder": "Sean Schubert",
        "ratified_on": "2026-09-01",
        "decision_record": "docs/memory/decisions/2026-09-01_autonomy-l2.md",
        "renderer_version": renderer_fingerprint(),
        "max_releases_per_day": 3,
    }
    policy = _load_policy_at(_signed_record(tmp_path, payload))
    assert policy.allows_auto_release("facebook_page", "T3")


def test_malformed_record_fails_closed_not_open(tmp_path):
    record = tmp_path / "a.json"
    record.write_text("{not json")
    with pytest.raises(AutonomyRecordError):
        _load_policy_at(record)
    record.write_text(json.dumps({"level": "L9"}))
    with pytest.raises(AutonomyRecordError, match="unknown level"):
        _load_policy_at(record)
    payload = {"level": "L1", "founder": "S", "ratified_on": "d", "decision_record": "r"}
    with pytest.raises(AutonomyRecordError, match="renderer_version"):
        _load_policy_at(_signed_record(tmp_path, payload))
    payload = dict(_l1_payload())
    del payload["scopes"]
    with pytest.raises(AutonomyRecordError, match="enumerate scopes"):
        _load_policy_at(_signed_record(tmp_path, payload))
    payload = dict(_l1_payload())
    payload["max_releases_per_day"] = 0
    with pytest.raises(AutonomyRecordError, match="cadence ceiling"):
        _load_policy_at(_signed_record(tmp_path, payload))


def test_autonomy_grant_is_renderer_bound(tmp_path, monkeypatch):
    # r10 blocker: a grant froze a different renderer -> refuse.
    payload = _l1_payload()
    payload["renderer_version"] = "0" * 64
    path = _signed_record(tmp_path, payload)
    monkeypatch.setattr(autonomy_module, "DEFAULT_RECORD_PATH", path)
    draft = _draft()
    with pytest.raises(ValueError, match="code changed since ratification"):
        _release(draft)


def test_autonomy_grant_is_series_bound(tmp_path, monkeypatch):
    payload = _l1_payload()
    payload["series_keys"] = ["scenario_family_day"]
    path = _signed_record(tmp_path, payload)
    monkeypatch.setattr(autonomy_module, "DEFAULT_RECORD_PATH", path)
    draft = _draft()  # series t1_live-music
    with pytest.raises(ValueError, match="enumerated series"):
        _release(draft)


def test_autonomy_requires_a_release_journal(tmp_path, monkeypatch):
    # r11 blocker: max_releases_per_day must be MECHANICAL — no registered
    # journal means the count cannot be proven, so autonomy refuses.
    path = _signed_record(tmp_path, _l1_payload())
    monkeypatch.setattr(autonomy_module, "DEFAULT_RECORD_PATH", path)
    monkeypatch.setattr(publish_gate, "_RELEASE_JOURNAL", None)
    with pytest.raises(ValueError, match="no release journal"):
        _release(_draft())


def test_autonomy_cadence_ceiling_is_enforced(tmp_path, monkeypatch):
    # r11 blocker: the grant says 2/day — the third auto-release refuses.
    path = _signed_record(tmp_path, _l1_payload())  # max_releases_per_day: 2
    monkeypatch.setattr(autonomy_module, "DEFAULT_RECORD_PATH", path)
    draft = _draft()
    assert _release(draft).released_by == "autonomy:L1"
    assert _release(draft).released_by == "autonomy:L1"
    with pytest.raises(ValueError, match="cadence ceiling"):
        _release(draft)


def test_human_approval_never_depends_on_the_journal(monkeypatch):
    # The ceiling belongs to the autonomy GRANT; per-post human custody
    # stands on its own even before deployment wires a journal.
    monkeypatch.setattr(publish_gate, "_RELEASE_JOURNAL", None)
    draft = _draft()
    assert _release(draft, _approve(draft)).released_by == "Sean Schubert"


def test_release_journal_registration_is_once_only(monkeypatch):
    monkeypatch.setattr(publish_gate, "_RELEASE_JOURNAL", None)
    publish_gate.configure_release_journal(_DurableTestJournal())
    with pytest.raises(ValueError, match="already configured"):
        publish_gate.configure_release_journal(_DurableTestJournal())


def test_volatile_journal_cannot_register(monkeypatch):
    # r14 blocker: a journal that does not attest durability must not be
    # registerable — a restart-reset count fails open on the daily cap.
    monkeypatch.setattr(publish_gate, "_RELEASE_JOURNAL", None)

    class _Volatile(_DurableTestJournal):
        durable = False

    with pytest.raises(ValueError, match="attest durability"):
        publish_gate.configure_release_journal(_Volatile())
    # And no journal implementation ships inside the gate module itself.
    assert not hasattr(publish_gate, "InMemoryReleaseJournal")


def test_weak_approval_key_fails_loud_everywhere(monkeypatch, tmp_path):
    # r14 blockers: ONELIVE_APPROVAL_KEY=1 must refuse to sign or verify
    # anything — approvals AND autonomy records.
    draft = _draft()
    approval = _approve(draft)
    monkeypatch.setenv("ONELIVE_APPROVAL_KEY", "1")
    with pytest.raises(ValueError, match="too weak"):
        approve(draft, "Sean Schubert", "2026-07-24T18:00:00-05:00")
    with pytest.raises(ValueError, match="too weak"):
        _release(draft, approval)
    with pytest.raises(AutonomyRecordError, match="too weak"):
        sign_autonomy_record({"level": "L1"}, "1")
    # A signed grant + a weak deployed verification key refuses loudly too.
    path = _signed_record(tmp_path, _l1_payload())
    with pytest.raises(AutonomyRecordError, match="too weak"):
        _load_policy_at(path)
    # Degenerate padding is weak regardless of length.
    monkeypatch.setenv("ONELIVE_APPROVAL_KEY", "a" * 64)
    with pytest.raises(ValueError, match="too weak"):
        approve(draft, "Sean Schubert", "2026-07-24T18:00:00-05:00")


# --- Fact-derived copy (evaluator r11) -----------------------------------------

_FABRICATED_PHRASES = (
    # The exact class r11 blocked: qualitative claims no canonical row carries.
    "big rooms",
    "local picks",
    "wildcards",
    "couch-defeating",
    "real ones",
    "about to go off",
    "candidates inside",
)


def _family_day_config():
    return _config(
        series_key="t1_family",
        domain_ids=("family",),
        timeframe="today",
        listicle_noun="family adventures",
    )


def _family_events(n=5, price=0):
    return [
        _event(
            i,
            domain="family",
            start_time=f"2026-07-24T1{4 + i % 4}:00:00-05:00",  # 14:00-17:00 today
            price_min=price,
        )
        for i in range(1, n + 1)
    ]


def test_every_hook_and_caption_combination_is_fact_derived():
    # r11 blockers: every copy surface across the whole factor space is
    # assembled from canonical facts + the curated noun — none of the
    # removed fabricated phrases can render, for any series.
    for hook in FACTORS["hook_type"]:
        for style in FACTORS["caption_style"]:
            draft = _draft(
                _family_events(),
                config=_family_day_config(),
                hook_type=hook,
                caption_style=style,
            )
            for text in [s.headline for s in draft.slides] + [draft.caption]:
                lowered = text.lower()
                for phrase in _FABRICATED_PHRASES:
                    assert phrase not in lowered, (hook, style, text)


def test_price_promise_uses_the_series_noun_not_nights():
    # r11 blocker: "5 free nights ... Today" for a daytime family carousel
    # was a false claim — the promise now carries the series' own noun.
    free = _draft(_family_events(price=0), config=_family_day_config(), hook_type="number_promise")
    assert free.slides[0].headline == "5 free family adventures to experience Today"
    priced = _draft(_family_events(price=8), config=_family_day_config(), hook_type="number_promise")
    assert priced.slides[0].headline == "5 family adventures from $8 to experience Today"


def test_hook_overflow_degrades_to_plain_noun_never_truncates():
    # A 2-word noun + "from $X" + "This weekend" would exceed the 8-word
    # recognition cap; the honest degrade drops the price blank, keeps N.
    events = [
        _event(i, start_time=f"2026-07-25T2{i % 3}:00:00-05:00") for i in range(1, 6)
    ]
    config = _config(timeframe="this_weekend", listicle_noun="weekend plans")
    draft = _draft(events, config=config, hook_type="number_promise")
    assert draft.slides[0].headline == "5 weekend plans to experience This weekend"


def test_mini_story_caption_is_built_from_canonical_facts():
    draft = _draft(caption_style="mini_story")
    first = next(s for s in draft.slides if s.kind == "event")
    assert first.headline in draft.caption  # the story is a real listing
    assert "Mohawk" in draft.caption


def test_render_carousel_refuses_nonfeaturable_rows_directly():
    # r13 blocker: the renderer itself (the release re-render path) must
    # refuse disputed/cancelled rows — not rely on upstream selection.
    from social.carousel.generator import render_carousel

    disputed = [_event(1, confidence="disputed")] + [_event(i) for i in range(2, 6)]
    with pytest.raises(CarouselTrustError, match="not featurable"):
        render_carousel(disputed, _config(), _assignment())
    cancelled = [_event(1, event_status="cancelled")] + [_event(i) for i in range(2, 6)]
    with pytest.raises(CarouselTrustError, match="only scheduled"):
        render_carousel(cancelled, _config(), _assignment())


def test_render_carousel_refuses_non_listicle_sizes_directly():
    from social.carousel.generator import render_carousel

    for n in (0, 3, 4, 6, 8):
        with pytest.raises(CarouselTrustError, match="listicle"):
            render_carousel(_events(n), _config(), _assignment())


def test_imageless_event_fails_loud():
    # r10 nit: the spec's image-mandatory rule is enforced, not implied.
    bare = _event(1, image_url="")
    with pytest.raises(CarouselTrustError, match="no image"):
        _draft([bare] + [_event(i) for i in range(2, 6)])


def test_deadman_ping_failure_never_masks_the_trust_error():
    def exploding_ping(stage):
        if stage == "error":
            raise RuntimeError("ping channel down")

    with pytest.raises(CarouselTrustError, match="unknown confidence"):
        _cycle(
            [_event(1, confidence="banana", domain="comedy")],
            {"comedy": 6.0},
            deadman_ping=exploding_ping,
        )


def test_no_ratification_record_is_committed_yet():
    # Checks the REAL repo path captured before the autouse fixture patches it.
    assert not os.path.exists(_REAL_RECORD_PATH)


def test_synthetic_fixtures_never_referenced_by_engine_modules():
    # r3 nit: pin the docstring's claim structurally — no engine module
    # imports the synthetic fixtures or mentions the sentinel.
    import pathlib

    pkg = pathlib.Path("social/carousel")
    for module in pkg.glob("*.py"):
        if module.name == "example_fixtures.py":
            continue
        text = module.read_text(encoding="utf-8")
        assert "example_fixtures" not in text, f"{module} references the fixtures"
        assert "SYNTHETIC-EXAMPLE" not in text, f"{module} references the sentinel"


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
    win = _assignment(cta_type="save_this")
    lose = _assignment(cta_type="tag_who")
    for _ in range(60):
        bandit.update(win, reward=0.6, reach=2000)
        bandit.update(lose, reward=0.05, reach=2000)
    means = bandit.posterior_means()["cta_type"]
    assert means["save_this"] > means["tag_who"]
    picks = [bandit.sample_assignment()["cta_type"] for _ in range(50)]
    assert picks.count("save_this") > picks.count("tag_who")


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
    lose = _assignment(cta_type="tag_who")
    for _ in range(40):
        bandit.update(lose, reward=0.01, reach=2000)
    picks = {bandit.sample_assignment()["cta_type"] for _ in range(200)}
    assert "tag_who" in picks  # even a loser keeps getting occasional data


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
        impressions=1500,
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
    # cadence and claimed window can never disagree (founder windows only)
    assert by_key["t1_live-music"].timeframe == "tonight"
    assert by_key["t2_comedy"].timeframe == "this_weekend"
    assert combined.timeframe == "this_weekend"


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
    bundle = draft.discovery
    assert bundle["carousel_jsonld"]["@type"] == "SocialMediaPosting"
    assert len(bundle["event_jsonld"]) == len(featured)
    assert bundle["og_tags"]["og:site_name"] == "OneLive"
    assert "confidence:" in bundle["llms_txt_block"]
    assert bundle["llms_txt_block"].startswith("## Tonight in Austin")
    assert all(bundle["alt_texts"])


def test_llms_txt_header_matches_the_timeframe():
    # r2 blocker: machine-facing discovery copy must claim the verified
    # window, never a hardcoded "Tonight".
    events = [
        _event(i, start_time=f"2026-07-25T2{i % 3}:00:00-05:00") for i in range(1, 6)
    ]
    draft = _draft(events, config=_config(timeframe="this_weekend"))
    assert draft.discovery["llms_txt_block"].startswith("## This weekend in Austin")


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
        max_drafts=20,
        reference_time=REF_TIME,
    )
    base.update(over)
    return run_cycle(**base)


def _cycle_events():
    return _events(8) + [
        _event(20 + i, domain="comedy", start_time=f"2026-07-24T2{i % 3}:00:00-05:00")
        for i in range(6)
    ]


def test_run_cycle_produces_drafts_and_telemetry():
    pings = []
    result = _cycle(
        _cycle_events(), {"live-music": 20.0, "comedy": 6.0}, deadman_ping=pings.append
    )
    assert pings == ["start", "end"]
    assert result.drafts and all(d.discovery for d in result.drafts)
    assert result.posterior_means
    assert all(d.author == "onelive-carousel-agent" for d in result.drafts)
    # scenario series are attempted; outcomes (draft or recorded skip) exist
    attempted = {d.series_key for d in result.drafts} | {
        k for k, _ in result.skipped_series
    }
    assert any(k.startswith("scenario_") for k in attempted)


def test_run_cycle_budget_cap_is_hard_and_skips_are_recorded():
    result = _cycle(_cycle_events(), {"live-music": 20.0, "comedy": 6.0}, max_drafts=1)
    assert len(result.drafts) == 1
    assert any("budget cap" in reason for _, reason in result.skipped_series)
    with pytest.raises(ValueError, match="max_drafts"):
        _cycle(_cycle_events(), {"live-music": 20.0}, max_drafts=0)


def test_run_cycle_records_only_the_no_featurable_skip():
    result = _cycle([_event(1, "disputed", domain="comedy")], {"comedy": 6.0})
    assert not result.drafts
    assert result.skipped_series and all(reason for _, reason in result.skipped_series)


def test_run_cycle_propagates_trust_errors_loud():
    # Unknown confidence must NOT become a silent skip (evaluator r1).
    with pytest.raises(CarouselTrustError, match="unknown confidence"):
        _cycle([_event(1, confidence="banana", domain="comedy")], {"comedy": 6.0})
    with pytest.raises(CarouselTrustError, match="never amplified"):
        _cycle([_event(1, origin="candidate_store", domain="comedy")], {"comedy": 6.0})
    with pytest.raises(CarouselTrustError, match="Descriptor Foundry"):
        _cycle(
            [_event(1, domain="comedy", foundry_descriptor={"text": "vibes"})],
            {"comedy": 6.0},
        )
    with pytest.raises(CarouselTrustError, match="banned claim phrase"):
        _cycle(
            [_event(i, domain="comedy", name=f"Guaranteed fun {i}") for i in range(1, 6)],
            {"comedy": 6.0},
        )


def test_negative_price_fails_loud_everywhere():
    # r7 blockers: an impossible price is a data defect, never copy.
    with pytest.raises(CarouselTrustError, match="negative price"):
        select_featurable([_event(1, price_min=-5)])
    free = scenario_by_key("free_tonight")
    assert scenario_events([_event(1, domain="comedy", price_min=-5)], free) == []


def test_render_path_validates_config_itself():
    # r7 blocker: the release re-render path fails closed on bad config
    # independently of build_carousel.
    from social.carousel.generator import render_carousel

    bad = _config(surface="myspace_bulletin")
    with pytest.raises(ValueError, match="unknown surface"):
        render_carousel(_events(5), bad, _assignment())


def test_approve_rejects_malformed_timestamp():
    with pytest.raises(ValueError, match="ISO 8601"):
        approve(_draft(), "Sean Schubert", "yesterday-ish")


def test_deadman_error_ping_on_loud_failure():
    pings = []
    with pytest.raises(CarouselTrustError):
        _cycle(
            [_event(1, confidence="banana", domain="comedy")],
            {"comedy": 6.0},
            deadman_ping=pings.append,
        )
    assert pings == ["start", "error"]  # "end" never fires on the error path


def test_false_scenario_claim_refused_at_release(monkeypatch):
    # r8 blocker: a "free nights" carousel over paid canonical rows never
    # releases — the scenario predicate is re-derived at custody.
    paid = [
        _event(i, domain="comedy", price_min=0) for i in range(1, 6)
    ]
    config = _config(
        series_key="scenario_free_tonight",
        domain_ids=("live-music", "comedy", "nightlife", "visual-arts", "community"),
        listicle_noun="free nights",
    )
    draft = _draft(paid, config=config)
    rows = {e["event_id"]: {**e, "price_min": 25} for e in paid}
    monkeypatch.setattr(publish_gate, "_STATE_READER", _reader_returning(rows))
    approval = _approve(draft)
    with pytest.raises(ValueError, match="scenario predicate|re-derive"):
        _release(draft, approval)


def test_malformed_canonical_row_refuses_at_release(monkeypatch):
    # r8 blocker: the release re-render runs the FULL event contract — a
    # canonical row with a provenance-less descriptor refuses.
    draft = _draft()
    rows = _rows_for(draft)
    first = next(iter(rows))
    rows[first] = {**rows[first], "foundry_descriptor": {"text": "vibes"}}
    monkeypatch.setattr(publish_gate, "_STATE_READER", _reader_returning(rows))
    approval = _approve(draft)
    with pytest.raises(ValueError, match="lawful carousel"):
        _release(draft, approval)


def test_out_of_domain_row_fails_loud():
    # r8: a series claim covers only its own domains, at generation too.
    stray = [_event(1, domain="sports")] + [_event(i) for i in range(2, 6)]
    with pytest.raises(CarouselTrustError, match="outside this series"):
        _draft(stray)


def test_out_of_domain_row_refuses_at_release(monkeypatch):
    # r9 blocker: the domain claim is re-derived at custody for tier
    # series too — a canonical row that moved out of the series' domains
    # refuses even under a valid approval.
    draft = _draft()
    assert draft.domain_ids == ("live-music",)
    rows = _rows_for(draft)
    first = next(iter(rows))
    rows[first] = {**rows[first], "domain_id": "sports"}
    monkeypatch.setattr(publish_gate, "_STATE_READER", _reader_returning(rows))
    approval = _approve(draft)
    with pytest.raises(ValueError, match="lawful carousel"):
        _release(draft, approval)


def test_naive_timestamps_refused_as_custody_moments():
    # r9 nit: date-only or tz-naive approval timestamps fail closed.
    for bad in ("2026-07-24", "2026-07-24T18:00:00"):
        with pytest.raises(ValueError, match="moment"):
            approve(_draft(), "Sean Schubert", bad)


def test_subcent_price_and_string_zero():
    # r8 nits: sub-cent prices are a data defect; "0" the string is free.
    with pytest.raises(CarouselTrustError, match="sub-cent"):
        _draft([_event(1, price_min=19.999)] + [_event(i) for i in range(2, 6)])
    draft = _draft([_event(1, price_min="0")] + [_event(i) for i in range(2, 6)])
    texts = [line for sl in draft.slides for line in sl.overlay_lines]
    assert any(t == "Free" for t in texts)


def test_ingest_results_updates_learner_and_reports():
    bandit = ThompsonBandit(seed=9)
    ledger = MetricsLedger()
    outcomes = [
        (_assignment(), _metrics(1, 0.10)),
        (_assignment(hook_type="number_promise"), _metrics(2, 0.30)),
    ]
    report = ingest_results(bandit=bandit, ledger=ledger, outcomes=outcomes, decay_gamma=0.99)
    assert bandit.updates_seen == 2
    assert "instagram_feed|T1" in report
