"""The autonomous cycle: tier -> sample -> generate -> propose; measure -> learn.

Greppable summary: run_cycle() derives the portfolio from live volume,
samples a creative assignment per series from the bandit, builds drafts,
and returns them FOR HUMAN CUSTODY — this module never imports
publish_gate (the import guard test reads this file's import block), so
the autonomous loop is structurally unable to post. ingest_results() folds
measured outcomes back into the ledger and the bandit — the founder's
create -> measure -> learn -> revise -> repost loop, with only the
approve/post step outside it. Scheduling this cycle on a cron is gated on
the Sentinel rule (dead-man ping + budget caps first) [R-027].
"""
from __future__ import annotations

from dataclasses import dataclass, field

from social.carousel.bandit import ThompsonBandit
from social.carousel.config import CarouselConfig
from social.carousel.generator import CarouselDraft, NoFeaturableEvents, build_carousel
from social.carousel.metrics import MetricsLedger, PostMetrics
from social.carousel.scenarios import SCENARIOS, scenario_config, scenario_events
from social.carousel.tiers import TierThresholds, plan_portfolio


@dataclass(frozen=True)
class BrandIdentity:
    """The fixed brand fields every series shares."""

    city: str
    handle: str
    short_link_base: str
    surface: str = "instagram_feed"


@dataclass
class CycleResult:
    """One cycle's output: drafts awaiting custody + inspectable telemetry.
    Each draft CARRIES its discovery bundle (r4: hash-bound custody — no
    separate machine-facing artifact stream exists to drift)."""

    drafts: list[CarouselDraft] = field(default_factory=list)
    skipped_series: list[tuple[str, str]] = field(default_factory=list)
    posterior_means: dict = field(default_factory=dict)


def run_cycle(
    *,
    events: list[dict],
    weekly_confirmed_counts: dict[str, float],
    bandit: ThompsonBandit,
    brand: BrandIdentity,
    max_drafts: int,
    reference_time: str,
    thresholds: TierThresholds | None = None,
    include_scenarios: bool = True,
    deadman_ping=None,
) -> CycleResult:
    """Generate this cycle's carousel drafts: the volume-tiered domain
    portfolio plus the founder's named scenario series. max_drafts is the
    hard budget cap (charter cost discipline: every loop runs under a
    ceiling); a non-positive cap is a configuration defect, not a silent
    no-op. reference_time (full ISO timestamp) anchors every series'
    truthful FUTURE-ONLY window — a 6pm cycle never features a 5:30 start."""
    if max_drafts <= 0:
        raise ValueError(f"max_drafts must be positive, got {max_drafts}")
    if deadman_ping is not None:
        deadman_ping("start")
    try:
        result = _run_cycle_body(
            events=events,
            weekly_confirmed_counts=weekly_confirmed_counts,
            bandit=bandit,
            brand=brand,
            max_drafts=max_drafts,
            reference_time=reference_time,
            thresholds=thresholds,
            include_scenarios=include_scenarios,
        )
    except BaseException:
        # A loud trust error must still be VISIBLE to the dead-man channel
        # (r7 nit): ping failure explicitly, then propagate unchanged —
        # "end" means completed and never fires on the error path.
        if deadman_ping is not None:
            deadman_ping("error")
        raise
    if deadman_ping is not None:
        deadman_ping("end")
    return result


def _run_cycle_body(
    *,
    events,
    weekly_confirmed_counts,
    bandit,
    brand,
    max_drafts,
    reference_time,
    thresholds,
    include_scenarios,
) -> CycleResult:
    result = CycleResult()

    def _attempt(series_key: str, series_events: list[dict], config: CarouselConfig) -> None:
        if len(result.drafts) >= max_drafts:
            result.skipped_series.append((series_key, "budget cap reached"))
            return
        assignment = bandit.sample_assignment()
        try:
            draft = build_carousel(
                series_events, config, assignment, reference_time=reference_time
            )
        except NoFeaturableEvents as exc:
            # The ONE expected skip: nothing featurable in this series'
            # window is volume weather, RECORDED in telemetry (never
            # silent). Every other generator error — CarouselTrustError,
            # bad config, unknown states — propagates LOUD (evaluator r1:
            # the autonomous loop must never swallow a trust failure).
            result.skipped_series.append((series_key, str(exc)))
            return
        result.drafts.append(draft)

    for series in plan_portfolio(weekly_confirmed_counts, thresholds):
        _attempt(
            series.series_key,
            [e for e in events if e.get("domain_id") in series.domain_ids],
            CarouselConfig(
                surface=brand.surface,
                series_key=series.series_key,
                city=brand.city,
                handle=brand.handle,
                short_link_base=brand.short_link_base,
                domain_ids=series.domain_ids,
                tier=series.tier,
                timeframe=series.timeframe,
            ),
        )
    if include_scenarios:
        for scenario in SCENARIOS:
            _attempt(
                f"scenario_{scenario.key}",
                scenario_events(events, scenario),
                scenario_config(
                    scenario,
                    surface=brand.surface,
                    city=brand.city,
                    handle=brand.handle,
                    short_link_base=brand.short_link_base,
                ),
            )

    result.posterior_means = bandit.posterior_means()
    return result


def ingest_results(
    *,
    bandit: ThompsonBandit,
    ledger: MetricsLedger,
    outcomes: list[tuple[dict, PostMetrics]],
    decay_gamma: float | None = None,
) -> dict:
    """Fold measured outcomes (assignment, metrics) into the learner and the
    ledger; returns the improvement report (rolling baseline + regression
    flags) so every cycle's learning is inspectable."""
    for assignment, metrics in outcomes:
        ledger.record(metrics, assignment)
        bandit.update(assignment, metrics.interaction_rate, metrics.reach)
    if decay_gamma is not None:
        bandit.decay(decay_gamma)
    return ledger.improvement_report()
