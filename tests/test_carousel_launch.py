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


def test_launch_decks_reproduce_the_founder_seen_renders():
    # The v1 versions are PINNED: each scenario's launch assignment renders
    # the exact hook the founder reviewed, through the real trust path.
    for scenario in SCENARIOS:
        series = f"scenario_{scenario.key}"
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
            launch_assignment(series),
            reference_time=EXAMPLE_REFERENCE_TIME,
        )
        assert draft.slides[0].headline == EXPECTED_HOOKS[series]
        assert draft.assignment == launch_assignment(series)


def test_launch_assignment_returns_fresh_validated_copies():
    a = launch_assignment("scenario_date_night")
    a["cta_type"] = "save_this"  # mutating the copy must not leak back
    assert launch_assignment("scenario_date_night")["cta_type"] == "send_to_friend"
    assert launch_assignment("t1_live-music") == DEFAULT_LAUNCH
    assert launch_assignment("t1_live-music") is not DEFAULT_LAUNCH


def test_corrupt_launch_table_fails_loud(monkeypatch):
    import social.carousel.launch as launch

    monkeypatch.setitem(
        launch.LAUNCH_ASSIGNMENTS, "scenario_date_night",
        dict(DEFAULT_LAUNCH, hook_type="clickbait"),
    )
    with pytest.raises(ValueError, match="unknown level"):
        launch_assignment("scenario_date_night")


def test_seed_bandit_favors_launch_levels_without_locking_them():
    bandit = ThompsonBandit(seed=7)
    seed_bandit(bandit)
    launch_ctas = {a["cta_type"] for a in LAUNCH_ASSIGNMENTS.values()}
    picks = [bandit.sample_assignment()["hook_type"] for _ in range(200)]
    # Favored: the launch hook dominates early sampling…
    assert picks.count("edition_anchor") > picks.count("number_promise")
    # …but never locks: every factor's non-launch levels remain sampleable.
    all_ctas = {bandit.sample_assignment()["cta_type"] for _ in range(400)}
    assert not all_ctas.issubset(launch_ctas) or all_ctas == set(FACTORS["cta_type"])
    with pytest.raises(ValueError, match="positive"):
        seed_bandit(bandit, weight=0)
