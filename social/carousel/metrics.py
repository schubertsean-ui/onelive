"""Metrics ledger + the continuous-improvement ratchet (spec §6).

Greppable summary: the honest metric set (interaction rate as north star;
save/share rates as the growth-loop metrics Meta's ranking rewards most;
completion, follows, link CTR supporting), a ledger of every post's
measured outcome with its creative assignment, and the Kaizen-style
ratchet: a rolling baseline per (surface x tier) with mechanical
regression flags — "toward 100% interaction" enforced as continuous
MEASURED improvement, never as a claim.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from social.carousel.config import validate_assignment

DEFAULT_BASELINE_WINDOW = 10


@dataclass(frozen=True)
class PostMetrics:
    """One published carousel's measured outcome (Meta Insights shape)."""

    post_id: str
    surface: str
    tier: str
    posted_at: str  # ISO 8601, from the platform record — never generated here
    reach: int
    unique_interactions: int
    saves: int = 0
    shares: int = 0
    comments: int = 0
    likes: int = 0
    profile_visits: int = 0
    link_clicks: int = 0
    follows: int = 0
    # Total views incl. repeats (Insights "impressions"/"views"): the
    # impressions/reach ratio is the audience-fatigue dial the cadence
    # decision reads (spec §5b).
    impressions: int = 0

    def validate(self) -> None:
        if self.reach <= 0:
            raise ValueError(f"reach must be positive, got {self.reach}")
        counters = {
            "unique_interactions": self.unique_interactions,
            "saves": self.saves,
            "shares": self.shares,
            "comments": self.comments,
            "likes": self.likes,
            "profile_visits": self.profile_visits,
            "link_clicks": self.link_clicks,
            "follows": self.follows,
            "impressions": self.impressions,
        }
        for name, value in counters.items():
            if value < 0:
                raise ValueError(f"{name} must be non-negative, got {value}")
        if self.unique_interactions > self.reach:
            raise ValueError(
                "unique_interactions cannot exceed reach "
                f"({self.unique_interactions} > {self.reach})"
            )

    @property
    def interaction_rate(self) -> float:
        """North star: unique interacting accounts / accounts reached."""
        return self.unique_interactions / self.reach

    @property
    def save_rate(self) -> float:
        return self.saves / self.reach

    @property
    def share_rate(self) -> float:
        return self.shares / self.reach

    @property
    def link_ctr(self) -> float:
        return self.link_clicks / self.reach


@dataclass
class LedgerRow:
    metrics: PostMetrics
    assignment: dict[str, str] = field(default_factory=dict)


class MetricsLedger:
    """Append-only record of outcomes + the improvement ratchet."""

    def __init__(self) -> None:
        self.rows: list[LedgerRow] = []

    def record(self, metrics: PostMetrics, assignment: dict[str, str]) -> None:
        metrics.validate()
        # Same closed design space as the bandit (r14 nit): a direct caller
        # cannot accumulate untracked factor levels in the ledger.
        validate_assignment(assignment)
        self.rows.append(LedgerRow(metrics=metrics, assignment=dict(assignment)))

    def _rates(self, surface: str, tier: str) -> list[float]:
        return [
            row.metrics.interaction_rate
            for row in self.rows
            if row.metrics.surface == surface and row.metrics.tier == tier
        ]

    def rolling_baseline(
        self, surface: str, tier: str, window: int = DEFAULT_BASELINE_WINDOW
    ) -> float | None:
        """Mean interaction rate of the last `window` posts BEFORE the most
        recent one — the bar the newest work is measured against. None until
        there is any history to compare to."""
        rates = self._rates(surface, tier)
        if len(rates) < 2:
            return None
        history = rates[:-1][-window:]
        return sum(history) / len(history)

    def improvement_report(
        self, window: int = DEFAULT_BASELINE_WINDOW
    ) -> dict[str, dict[str, float | bool | None]]:
        """Per (surface|tier): latest rate vs rolling baseline, with a
        mechanical regression flag. A regressing period is a defect to
        explain (Kaizen), never something to average away silently."""
        report: dict[str, dict[str, float | bool | None]] = {}
        seen: set[tuple[str, str]] = set()
        for row in self.rows:
            key = (row.metrics.surface, row.metrics.tier)
            if key in seen:
                continue
            seen.add(key)
            rates = self._rates(*key)
            baseline = self.rolling_baseline(*key, window=window)
            latest = rates[-1]
            report[f"{key[0]}|{key[1]}"] = {
                "posts": float(len(rates)),
                "latest_interaction_rate": latest,
                "rolling_baseline": baseline,
                "improved": (baseline is not None and latest > baseline)
                if baseline is not None
                else None,
                "regressed": (baseline is not None and latest < baseline)
                if baseline is not None
                else None,
            }
        return report

    def to_json(self) -> str:
        return json.dumps(
            [
                {"metrics": asdict(row.metrics), "assignment": row.assignment}
                for row in self.rows
            ],
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, payload: str) -> "MetricsLedger":
        ledger = cls()
        for item in json.loads(payload):
            ledger.record(PostMetrics(**item["metrics"]), item["assignment"])
        return ledger
