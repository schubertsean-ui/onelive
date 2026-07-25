"""V1 launch versions of each carousel series (founder-directed 2026-07-25).

Greppable summary: the founder reviewed the five engine-rendered scenario
carousels and directed that, with rapid adoption and the 100%-interaction
goal in view, those exact renders BE each series' initial version. This
module pins that decision as code: one launch creative assignment per
series (the same assignments that produced the founder-seen decks —
reproducibility is test-pinned), plus a bandit warm-start that makes the
learner's first samples favor the launch creative while every other level
stays explorable. Physics unchanged: launch assignments pass through the
SAME validate_assignment/build_carousel trust path as any sample; the
warm-start is a PRIOR on the learner, never a gate change; and posting
still goes through publish-gate custody (nothing here can release —
release happens only at R-026's posting surface, where a series' FIRST
post uses launch_assignment and the bandit takes over from post two).

Rationale per choice (spec §3-§7 research, engagement-first):
- edition_anchor hooks: the curated noun IS the promise ("7 date nights")
  — highest-clarity 3-second gate, zero unverifiable words.
- listicle_size 7 for tonight/weekend volume series (more swipe depth =
  more ranked engagement), 5 where honest supply is thinner (free/family).
- CTA mapping: save_this for planner-type series (saves are Meta's
  strongest ranking signal and the "I'm considering going" act);
  send_to_friend for date_night and free_tonight (the plan-share loop —
  every send recruits at peak intent); tag_who for music_and_dancing
  (going-out is social; tags recruit publicly).
- caption styles: mini_story for date_night (narrative fits the use),
  list for weekend_planner (scannable plan), short_punch elsewhere.
- post_slot late_afternoon: the Duhigg cue — the "what's tonight?"
  decision window.
"""
from __future__ import annotations

import math

from social.carousel.config import validate_assignment
from social.carousel.geo import DOMAIN_TAGS

_BASE = dict(
    hook_type="edition_anchor",
    emotion_register="excitement",
    listicle_size="7",
    caption_style="short_punch",
    cta_type="send_to_friend",
    post_slot="late_afternoon",
    media_type="image",
)

# Series key -> the founder-seen v1 assignment. Scenario keys are exact;
# tier series (t1_*/t2_*/t3_*) use the default launch below.
LAUNCH_ASSIGNMENTS: dict[str, dict[str, str]] = {
    "scenario_date_night": dict(_BASE, caption_style="mini_story", cta_type="send_to_friend"),
    "scenario_music_and_dancing": dict(_BASE, cta_type="tag_who"),
    "scenario_weekend_planner": dict(_BASE, caption_style="list", cta_type="save_this"),
    "scenario_free_tonight": dict(_BASE, listicle_size="5", cta_type="send_to_friend"),
    "scenario_family_day": dict(
        _BASE, listicle_size="5", emotion_register="belonging", cta_type="save_this"
    ),
}

DEFAULT_LAUNCH = dict(_BASE)


_TIER_PREFIXES = ("t1_", "t2_", "t3_")


def launch_assignment(series_key: str) -> dict[str, str]:
    """The v1 assignment for a series' FIRST post (cold start). Always a
    fresh dict, always validated. FAIL-LOUD enumeration (#69 r1): an exact
    scenario key gets its pinned assignment; a tier series (t1_/t2_/t3_)
    gets the default; ANYTHING else — including a misspelled scenario key
    — refuses, because a typo must never silently post a non-pinned deck
    while looking like the founder's v1."""
    if series_key in LAUNCH_ASSIGNMENTS:
        assignment = dict(LAUNCH_ASSIGNMENTS[series_key])
    elif (
        series_key[:3] in _TIER_PREFIXES
        # Registry-bound, not prefix-only (#69 r2): a tier series is valid
        # ONLY for a canonical domain id — "t1_liv-music" refuses.
        and series_key[3:] in DOMAIN_TAGS
    ):
        assignment = dict(DEFAULT_LAUNCH)
    else:
        raise ValueError(
            f"unknown launch series {series_key!r} — pinned scenarios: "
            f"{sorted(LAUNCH_ASSIGNMENTS)}; tier series use prefixes "
            f"{_TIER_PREFIXES}. A launch typo fails loud, never posts a "
            "default deck disguised as the founder's v1"
        )
    validate_assignment(assignment)
    return assignment


def seed_bandit(bandit, weight: float = 3.0) -> None:
    """Warm-start the learner toward the launch creative: each launch
    level gets `weight` prior pseudo-successes at a nominal reach. A PRIOR,
    not a lock — the exploration floor and every other level's live data
    remain in force, so the bandit can dethrone any launch choice the
    moment Austin disagrees. Weight 3.0 ≈ a few good early posts; small by
    design (the 100%-interaction goal is served by learning speed, not by
    freezing the founder's first pick)."""
    if not math.isfinite(weight) or weight <= 0:
        raise ValueError(
            f"seed weight must be a positive FINITE number, got {weight!r} — "
            "the public contract validates here too, not only in add_prior (#69 r2)"
        )
    seen: set[tuple[str, str]] = set()
    for assignment in list(LAUNCH_ASSIGNMENTS.values()) + [DEFAULT_LAUNCH]:
        validate_assignment(assignment)
        for factor, level in assignment.items():
            if (factor, level) in seen:
                continue
            seen.add((factor, level))
            bandit.add_prior(factor, level, weight)
