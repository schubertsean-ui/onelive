"""Volume-tiered carousel portfolio (spec §5 — "most content first").

Greppable summary: assigns each of the 22 domains a carousel tier from its
rolling confirmed-event volume (content volume IS the tier key, per the
founder's directive), groups the long tail into combined series so no thin
carousel ever posts, and re-derives the whole portfolio every cycle so the
lineup follows the data ("wind vane" logic, same as enrichment attention).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TierThresholds:
    """Founder-tunable weekly confirmed-event floors per tier (spec §5)."""

    t1_weekly: float = 12.0
    t2_weekly: float = 5.0
    t3_weekly: float = 1.0

    def validate(self) -> None:
        if not (self.t1_weekly > self.t2_weekly > self.t3_weekly > 0):
            raise ValueError(
                "thresholds must be strictly ordered t1 > t2 > t3 > 0, got "
                f"{self.t1_weekly}/{self.t2_weekly}/{self.t3_weekly}"
            )


CADENCE_BY_TIER = {"T1": "daily", "T2": "weekly", "T3": "biweekly"}

# The truthful copy window per cadence (config.TIMEFRAMES; founder canon
# 2026-07-24: the only windows are Today, Tonight, This weekend): a daily
# series claims tonight; weekly and biweekly roundups claim the weekend.
# The generator excludes events outside the window (and anything already
# started), so cadence and copy can never disagree.
TIMEFRAME_BY_CADENCE = {"daily": "tonight", "weekly": "this_weekend", "biweekly": "this_weekend"}


@dataclass(frozen=True)
class CarouselSeries:
    """One recurring carousel: its tier, cadence, window, and domains."""

    series_key: str
    tier: str
    cadence: str
    timeframe: str = "tonight"
    domain_ids: tuple[str, ...] = field(default_factory=tuple)


def assign_tiers(
    weekly_confirmed_counts: dict[str, float],
    thresholds: TierThresholds | None = None,
) -> dict[str, str | None]:
    """Map domain id -> tier (or None below the T3 floor). Counts must be
    non-negative; a negative count is a data defect and fails loud."""
    th = thresholds or TierThresholds()
    th.validate()
    tiers: dict[str, str | None] = {}
    for domain, count in weekly_confirmed_counts.items():
        if count < 0:
            raise ValueError(f"negative event count for domain {domain!r}: {count}")
        if count >= th.t1_weekly:
            tiers[domain] = "T1"
        elif count >= th.t2_weekly:
            tiers[domain] = "T2"
        elif count >= th.t3_weekly:
            tiers[domain] = "T3"
        else:
            tiers[domain] = None
    return tiers


def plan_portfolio(
    weekly_confirmed_counts: dict[str, float],
    thresholds: TierThresholds | None = None,
) -> list[CarouselSeries]:
    """Build the carousel lineup from live volume.

    - Every T1 domain gets its own flagship series.
    - T2 domains get their own weekly roundup series.
    - ALL T3 domains share one combined series (no starved solo carousels).
    - A city-wide "tonight" flagship exists whenever anything is featurable
      at all — it is the Duhigg cue anchor (same slot, every day).
    """
    tiers = assign_tiers(weekly_confirmed_counts, thresholds)
    portfolio: list[CarouselSeries] = []

    active = [d for d, t in tiers.items() if t is not None]
    if active:
        portfolio.append(
            CarouselSeries(
                series_key="tonight_all",
                tier="T1",
                cadence=CADENCE_BY_TIER["T1"],
                timeframe=TIMEFRAME_BY_CADENCE[CADENCE_BY_TIER["T1"]],
                domain_ids=tuple(sorted(active)),
            )
        )
    for domain in sorted(d for d, t in tiers.items() if t == "T1"):
        portfolio.append(
            CarouselSeries(
                series_key=f"t1_{domain}",
                tier="T1",
                cadence=CADENCE_BY_TIER["T1"],
                timeframe=TIMEFRAME_BY_CADENCE[CADENCE_BY_TIER["T1"]],
                domain_ids=(domain,),
            )
        )
    for domain in sorted(d for d, t in tiers.items() if t == "T2"):
        portfolio.append(
            CarouselSeries(
                series_key=f"t2_{domain}",
                tier="T2",
                cadence=CADENCE_BY_TIER["T2"],
                timeframe=TIMEFRAME_BY_CADENCE[CADENCE_BY_TIER["T2"]],
                domain_ids=(domain,),
            )
        )
    t3_domains = tuple(sorted(d for d, t in tiers.items() if t == "T3"))
    if t3_domains:
        portfolio.append(
            CarouselSeries(
                series_key="t3_everything_else",
                tier="T3",
                cadence=CADENCE_BY_TIER["T3"],
                timeframe=TIMEFRAME_BY_CADENCE[CADENCE_BY_TIER["T3"]],
                domain_ids=t3_domains,
            )
        )
    return portfolio
