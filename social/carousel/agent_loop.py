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
from social.carousel.generator import CarouselDraft, build_carousel
from social.carousel.geo import discovery_bundle
from social.carousel.metrics import MetricsLedger, PostMetrics
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
    """One cycle's output: drafts awaiting custody + inspectable telemetry."""

    drafts: list[CarouselDraft] = field(default_factory=list)
    discovery_bundles: list[dict] = field(default_factory=list)
    skipped_series: list[tuple[str, str]] = field(default_factory=list)
    posterior_means: dict = field(default_factory=dict)


def run_cycle(
    *,
    events: list[dict],
    weekly_confirmed_counts: dict[str, float],
    bandit: ThompsonBandit,
    brand: BrandIdentity,
    max_drafts: int,
    thresholds: TierThresholds | None = None,
    deadman_ping=None,
) -> CycleResult:
    """Generate this cycle's carousel drafts. max_drafts is the hard budget
    cap (charter cost discipline: every loop runs under a ceiling); a
    non-positive cap is a configuration defect, not a silent no-op."""
    if max_drafts <= 0:
        raise ValueError(f"max_drafts must be positive, got {max_drafts}")
    if deadman_ping is not None:
        deadman_ping("start")

    portfolio = plan_portfolio(weekly_confirmed_counts, thresholds)
    result = CycleResult()
    for series in portfolio:
        if len(result.drafts) >= max_drafts:
            result.skipped_series.append((series.series_key, "budget cap reached"))
            continue
        series_events = [e for e in events if e.get("domain_id") in series.domain_ids]
        config = CarouselConfig(
            surface=brand.surface,
            series_key=series.series_key,
            city=brand.city,
            handle=brand.handle,
            short_link_base=brand.short_link_base,
            domain_ids=series.domain_ids,
            tier=series.tier,
        )
        assignment = bandit.sample_assignment()
        try:
            draft = build_carousel(series_events, config, assignment)
        except ValueError as exc:
            # A series with nothing featurable this cycle is expected volume
            # weather; the skip is RECORDED in telemetry (never silent) and
            # the portfolio moves on.
            result.skipped_series.append((series.series_key, str(exc)))
            continue
        featured_ids = {s.event_id for s in draft.slides if s.kind == "event"}
        featured = [e for e in series_events if e["event_id"] in featured_ids]
        result.drafts.append(draft)
        result.discovery_bundles.append(discovery_bundle(draft, featured, brand.city))

    result.posterior_means = bandit.posterior_means()
    if deadman_ping is not None:
        deadman_ping("end")
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
