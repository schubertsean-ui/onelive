"""Thompson-sampling learner over the factored creative space (spec §6).

Greppable summary: per-factor Beta posteriors updated with reach-scaled
fractional pseudo-counts from each post's interaction rate; Thompson
sampling picks the next assignment; an exploration floor keeps every level
measurable; evidence decays so the learner tracks a moving culture. The
whole state is plain JSON — learning as inspectable updated weights, never
a black box (same posture as source-reliability priors). Deterministic
under a seed so every choice is reproducible in tests and audits.
"""
from __future__ import annotations

import json
import random

from social.carousel.config import FACTORS, validate_assignment

# One "full-weight" post teaches this many pseudo-observations; reach above
# the cap cannot freeze learning behind one viral outlier (spec §6).
REACH_SCALE = 1000.0
MAX_PSEUDO_PER_POST = 20.0
PRIOR_ALPHA = 1.0
PRIOR_BETA = 1.0
DEFAULT_EXPLORATION_FLOOR = 0.05
DEFAULT_DECAY = 0.99


class ThompsonBandit:
    """Factored Beta-Bernoulli Thompson sampler with exploration floor."""

    def __init__(
        self,
        seed: int,
        exploration_floor: float = DEFAULT_EXPLORATION_FLOOR,
        factors: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        if not 0.0 <= exploration_floor < 1.0:
            raise ValueError(f"exploration_floor out of [0,1): {exploration_floor}")
        self._rng = random.Random(seed)
        self.exploration_floor = exploration_floor
        self.factors = dict(factors or FACTORS)
        self.posteriors: dict[str, dict[str, dict[str, float]]] = {
            f: {lvl: {"alpha": PRIOR_ALPHA, "beta": PRIOR_BETA} for lvl in levels}
            for f, levels in self.factors.items()
        }
        self.updates_seen = 0

    # --- choose ---------------------------------------------------------------
    def sample_assignment(self) -> dict[str, str]:
        """One creative assignment: per factor, Thompson-sample every level
        and take the max — except with exploration-floor probability the
        factor explores uniformly, so no level is ever starved of data."""
        assignment: dict[str, str] = {}
        for factor, levels in self.factors.items():
            if self._rng.random() < self.exploration_floor:
                assignment[factor] = self._rng.choice(list(levels))
                continue
            draws = {
                lvl: self._rng.betavariate(
                    self.posteriors[factor][lvl]["alpha"],
                    self.posteriors[factor][lvl]["beta"],
                )
                for lvl in levels
            }
            assignment[factor] = max(draws, key=lambda k: draws[k])
        validate_assignment(assignment)
        return assignment

    # --- learn ----------------------------------------------------------------
    def add_prior(self, factor: str, level: str, weight: float) -> None:
        """Add prior pseudo-successes to one level (launch warm-starts, #69
        r1 nit: callers use THIS, never the posterior internals — the
        representation can change without breaking seeding). A prior only
        ever ADDS alpha; it cannot erase evidence or remove levels."""
        if weight <= 0:
            raise ValueError(f"prior weight must be positive, got {weight}")
        if factor not in self.posteriors or level not in self.posteriors[factor]:
            raise ValueError(f"unknown factor/level ({factor!r}, {level!r})")
        self.posteriors[factor][level]["alpha"] += weight

    def update(self, assignment: dict[str, str], reward: float, reach: int) -> None:
        """Fold one post's measured interaction rate back into every factor
        level the post used. reward is the interaction rate in [0,1]."""
        validate_assignment(assignment)
        if not 0.0 <= reward <= 1.0:
            raise ValueError(f"reward must be in [0,1], got {reward}")
        if reach <= 0:
            raise ValueError(f"reach must be positive, got {reach}")
        n = min(reach / REACH_SCALE, MAX_PSEUDO_PER_POST)
        for factor, level in assignment.items():
            post = self.posteriors[factor][level]
            post["alpha"] += reward * n
            post["beta"] += (1.0 - reward) * n
        self.updates_seen += 1

    def decay(self, gamma: float = DEFAULT_DECAY) -> None:
        """Shrink accumulated evidence toward the prior so old culture stops
        outvoting the present (spec §6). gamma=1 is a no-op."""
        if not 0.0 < gamma <= 1.0:
            raise ValueError(f"decay gamma must be in (0,1], got {gamma}")
        for levels in self.posteriors.values():
            for post in levels.values():
                post["alpha"] = PRIOR_ALPHA + gamma * (post["alpha"] - PRIOR_ALPHA)
                post["beta"] = PRIOR_BETA + gamma * (post["beta"] - PRIOR_BETA)

    # --- inspect / persist ----------------------------------------------------
    def posterior_means(self) -> dict[str, dict[str, float]]:
        """Human-readable learning state: per level, the posterior mean
        interaction rate — what the ledger and founder digest report."""
        return {
            factor: {
                lvl: post["alpha"] / (post["alpha"] + post["beta"])
                for lvl, post in levels.items()
            }
            for factor, levels in self.posteriors.items()
        }

    def to_json(self) -> str:
        return json.dumps(
            {
                "exploration_floor": self.exploration_floor,
                "factors": {f: list(v) for f, v in self.factors.items()},
                "posteriors": self.posteriors,
                "updates_seen": self.updates_seen,
            },
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, payload: str, seed: int) -> "ThompsonBandit":
        data = json.loads(payload)
        bandit = cls(
            seed=seed,
            exploration_floor=data["exploration_floor"],
            factors={f: tuple(v) for f, v in data["factors"].items()},
        )
        bandit.posteriors = data["posteriors"]
        bandit.updates_seen = data["updates_seen"]
        return bandit
