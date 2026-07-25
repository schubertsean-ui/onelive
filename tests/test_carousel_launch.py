"""V1 launch versions: reproducibility, validity, warm-start physics.

Covers (founder directive 2026-07-25): every launch assignment is valid
in the closed factor space; each scenario's launch assignment renders the
founder-seen deck through the REAL engine (reproducibility — the v1
version is pinned, not remembered); the bandit warm-start favors launch
levels without locking them (a prior, never a gate); unknown series get
the default; a corrupt launch assignment fails loud.
"""
import pytest

from social.carousel.bandit import ThompsonBandit
from social.carousel.config import FACTORS, validate_assignment
from social.carousel.example_fixtures import EXAMPLE_EVENTS, EXAMPLE_REFERENCE_TIME
from social.carousel.generator import build_carousel
from social.carousel.launch import (
    DEFAULT_LAUNCH,
    LAUNCH_ASSIGNMENTS,
    launch_assignment,
    seed_bandit,
)
from social.carousel.scenarios import SCENARIOS, scenario_config, scenario_events

EXPECTED_HOOKS = {
    "scenario_date_night": "7 date nights to experience Tonight",
    "scenario_music_and_dancing": "7 dance floors to experience Tonight",
    "scenario_weekend_planner": "7 weekend plans to experience This weekend",
    "scenario_free_tonight": "5 free nights to experience Tonight",
    "scenario_family_day": "5 family adventures to experience Today",
}


def test_every_launch_assignment_is_valid_and_complete():
    for series, assignment in LAUNCH_ASSIGNMENTS.items():
        validate_assignment(assignment)
    validate_assignment(DEFAULT_LAUNCH)
    assert set(LAUNCH_ASSIGNMENTS) == set(EXPECTED_HOOKS)  # one per scenario


def _render_launch_deck(scenario):
    config = scenario_config(
        scenario,
        surface="instagram_feed",
        city="Austin",
        handle="@onelive.atx",
        short_link_base="https://onelive.app/tonight",
    )
    return build_carousel(
        scenario_events(EXAMPLE_EVENTS, scenario),
        config,
        launch_assignment(f"scenario_{scenario.key}"),
        reference_time=EXAMPLE_REFERENCE_TIME,
    )


def test_launch_decks_reproduce_the_founder_seen_renders_in_full():
    # #69 r1 blocker fixed: the v1 versions are pinned by FULL-DECK
    # equality against a committed golden snapshot — every slide, overlay
    # line, event id, uncertainty marker, caption, hashtag, and the
    # assignment itself. ANY drift fails; a legitimate renderer change
    # must update the golden visibly in its own diff.
    import json
    import pathlib

    golden = json.loads(
        pathlib.Path("tests/golden/carousel_launch_v1.json").read_text()
    )
    assert set(golden) == {f"scenario_{s.key}" for s in SCENARIOS}
    for scenario in SCENARIOS:
        series = f"scenario_{scenario.key}"
        draft = _render_launch_deck(scenario)
        rendered = {
            "assignment": dict(draft.assignment),
            "caption": draft.caption,
            "hashtags": list(draft.hashtags),
            "slides": [
                {
                    "kind": s.kind,
                    "headline": s.headline,
                    "overlay_lines": list(s.overlay_lines),
                    "event_id": s.event_id,
                    "uncertainty_marker": s.uncertainty_marker,
                }
                for s in draft.slides
            ],
        }
        assert rendered == golden[series], f"{series} drifted from the pinned v1"
        assert draft.slides[0].headline == EXPECTED_HOOKS[series]
    # r2 nit: the snapshot serializer must not silently omit a
    # publish-relevant field — any CarouselDraft schema change forces a
    # conscious decision here.
    import dataclasses as _dc

    draft_fields = {f.name for f in _dc.fields(_render_launch_deck(SCENARIOS[0]))}
    covered = {"assignment", "caption", "hashtags", "slides"}
    identity = {"series_key", "surface", "tier", "timeframe", "city", "handle",
                "listicle_noun", "short_link_base", "domain_ids", "author",
                "short_link", "post_slot"}
    derived = {"discovery"}  # hash-bound to slides+caption; verified at release
    assert draft_fields == covered | identity | derived, (
        "CarouselDraft schema changed — decide whether the new field joins "
        "the golden snapshot before this test may pass"
    )


def test_launch_assignment_returns_fresh_validated_copies():
    a = launch_assignment("scenario_date_night")
    a["cta_type"] = "save_this"  # mutating the copy must not leak back
    assert launch_assignment("scenario_date_night")["cta_type"] == "send_to_friend"
    assert launch_assignment("t1_live-music") == DEFAULT_LAUNCH
    assert launch_assignment("t1_live-music") is not DEFAULT_LAUNCH


def test_unknown_or_misspelled_series_fails_loud():
    # #69 r1 blocker fixed: a typo must never silently post a default deck
    # disguised as the founder's v1.
    for bad in (
        "scenario_free_tonite", "scenario_", "flagship", "t9_music", "t1_",
        # r2: prefix alone never suffices — the domain must be canonical.
        "t1_liv-music", "t2_nonexistent", "t3_scenario_date_night",
    ):
        with pytest.raises(ValueError, match="unknown launch series"):
            launch_assignment(bad)
    # Registry-bound tier keys DO resolve for every canonical domain.
    from social.carousel.geo import DOMAIN_TAGS

    for domain in DOMAIN_TAGS:
        assert launch_assignment(f"t2_{domain}") == DEFAULT_LAUNCH


def test_corrupt_launch_table_fails_loud(monkeypatch):
    import social.carousel.launch as launch

    monkeypatch.setitem(
        launch.LAUNCH_ASSIGNMENTS, "scenario_date_night",
        dict(DEFAULT_LAUNCH, hook_type="clickbait"),
    )
    with pytest.raises(ValueError, match="unknown level"):
        launch_assignment("scenario_date_night")


def test_seed_bandit_favors_launch_levels_without_locking_them():
    # #69 r1 nit fixed: DIRECT posterior-state assertions across every
    # factor and level (sampling is a secondary behavior check only).
    bandit = ThompsonBandit(seed=7)
    baseline = ThompsonBandit(seed=7)
    seed_bandit(bandit, weight=3.0)
    launch_levels = {
        (f, l)
        for a in list(LAUNCH_ASSIGNMENTS.values()) + [DEFAULT_LAUNCH]
        for f, l in a.items()
    }
    for factor, levels in FACTORS.items():
        for level in levels:
            post = bandit.posteriors[factor][level]
            base = baseline.posteriors[factor][level]
            if (factor, level) in launch_levels:
                # Favored: exactly the seed weight added, once, as alpha.
                assert post["alpha"] == base["alpha"] + 3.0
            else:
                # Never locked: non-launch levels keep their full prior —
                # present, sampleable, and untouched.
                assert post["alpha"] == base["alpha"]
            assert post["beta"] == base["beta"]
    # Secondary behavior check: launch hook dominates early sampling.
    picks = [bandit.sample_assignment()["hook_type"] for _ in range(200)]
    assert picks.count("edition_anchor") > picks.count("number_promise")
    for bad_weight in (0, -1.0, float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="FINITE|positive"):
            seed_bandit(ThompsonBandit(seed=1), weight=bad_weight)
        with pytest.raises(ValueError, match="FINITE|positive"):
            ThompsonBandit(seed=1).add_prior("hook_type", "edition_anchor", bad_weight)
    with pytest.raises(ValueError, match="unknown factor/level"):
        bandit.add_prior("hook_type", "clickbait", 1.0)
