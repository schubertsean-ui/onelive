"""Scenario carousels — the founder's named use-cases as standing series.

Greppable summary: founder-directed 2026-07-24 ("Include scenarios we've
identified like date night, music and dancing"). Each scenario is a
curated category-combo carousel grounded in the ratified voice-search
personas (docs/design/ONE_LIVE_VOICE_SEARCH_PERSONAS_v1.md): Date Night
(persona #11), Music & Dancing (the founder's own example, #7, + the
Cheap Dancer #9), the Weekend Planner (#5), Free Tonight (the price axis,
#9/#14), Family Day (Family & Youth + Place-based domains, a daytime
window). A scenario contributes a pre-FILTER (domains, price cap, later
starts) and the listicle noun — selection stays the generator's trust
path unchanged; no scenario may relax any trust rule, and mood-based
filters stay OUT until the Emotion & Vibe proposal is ratified (the
personas doc's own gating), which is why Date Night filters by domain and
start hour, never by "mellow".
"""
from __future__ import annotations

from dataclasses import dataclass, field

from social.carousel.config import CarouselConfig


@dataclass(frozen=True)
class Scenario:
    """One named scenario series: its noun, window, and pre-filter."""

    key: str
    listicle_noun: str
    timeframe: str
    domain_ids: tuple[str, ...]
    tier: str = "T1"
    # Optional pre-filters (None = no constraint). These NARROW the lineup;
    # they can never widen trust rules.
    price_max: float | None = None
    earliest_start_hour: int | None = None


SCENARIOS: tuple[Scenario, ...] = (
    # Persona #11 "The Date Night": dinner-first biases to later starts;
    # mood filtering is gated on the Emotion & Vibe proposal, so the honest
    # v1 filter is domains + a >= 8pm start.
    Scenario(
        key="date_night",
        listicle_noun="date nights",
        timeframe="tonight",
        domain_ids=("live-music", "performing-arts", "theater", "food-drink"),
        earliest_start_hour=20,
    ),
    # Persona #7, the founder's own example ("R&B or good dance music with
    # no or low cover charge") + #9 "The Cheap Dancer".
    Scenario(
        key="music_and_dancing",
        listicle_noun="dance floors",
        timeframe="tonight",
        domain_ids=("live-music", "nightlife", "dance"),
    ),
    # Persona #5 "The Planner": "What's going on this weekend?" —
    # cross-domain best-of.
    Scenario(
        key="weekend_planner",
        listicle_noun="weekend plans",
        timeframe="this_weekend",
        domain_ids=(
            "live-music",
            "comedy",
            "theater",
            "festivals",
            "food-drink",
            "visual-arts",
            "nightlife",
        ),
    ),
    # The price axis (personas #9/#14): free only — price_min == 0.
    Scenario(
        key="free_tonight",
        listicle_noun="free nights",
        timeframe="tonight",
        domain_ids=("live-music", "comedy", "nightlife", "visual-arts", "community"),
        price_max=0,
    ),
    # Family & Youth + Place-based, a DAYTIME window (Today, not Tonight).
    Scenario(
        key="family_day",
        listicle_noun="family adventures",
        timeframe="today",
        domain_ids=("family", "place-based", "library", "seasonal"),
    ),
)


def scenario_by_key(key: str) -> Scenario:
    for scenario in SCENARIOS:
        if scenario.key == key:
            return scenario
    raise ValueError(f"unknown scenario {key!r}; known: {[s.key for s in SCENARIOS]}")


def scenario_events(events: list[dict], scenario: Scenario) -> list[dict]:
    """Apply the scenario's pre-filter. Narrowing only — the generator's
    trust selection runs unchanged afterwards."""
    picked = [e for e in events if e.get("domain_id") in scenario.domain_ids]
    if scenario.price_max is not None:
        picked = [
            e
            for e in picked
            if e.get("price_min") is not None and 0 <= e["price_min"] <= scenario.price_max
        ]
    if scenario.earliest_start_hour is not None:
        picked = [
            e
            for e in picked
            if len(e.get("start_time", "")) >= 13
            and int(e["start_time"][11:13]) >= scenario.earliest_start_hour
        ]
    return picked


def scenario_config(
    scenario: Scenario,
    *,
    surface: str,
    city: str,
    handle: str,
    short_link_base: str,
) -> CarouselConfig:
    return CarouselConfig(
        surface=surface,
        series_key=f"scenario_{scenario.key}",
        city=city,
        handle=handle,
        short_link_base=short_link_base,
        domain_ids=scenario.domain_ids,
        tier=scenario.tier,
        timeframe=scenario.timeframe,
        listicle_noun=scenario.listicle_noun,
    )
