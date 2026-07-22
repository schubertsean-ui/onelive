"""Subjective Logic substrate for the convergence model (C1, SHADOW-ONLY).

Greppable summary: pure-stdlib implementation of binomial Subjective Logic
(Josang) per docs/strategy/ONE_LIVE_CONVERGENCE_v1.md §3 — the `Opinion`
dataclass (belief/disbelief/uncertainty/base-rate, b+d+u=1 validated
fail-loud), the bijective mapping to/from Beta evidence counts (prior
weight W=2), the fusion operators (cumulative for independent sources,
averaging for dependent ones), trust discounting, evidence aging, and the
4-state threshold mapping (`four_state`) onto the ratified confidence
states unverified/likely/confirmed/disputed. Everything here is a pure
function over immutable values: no I/O, no DB, no imports from (or into)
the live pipeline — the count-based gate keeps deciding until the founder
ratifies coupling per spec §11 (C5).

Scope note (spec §11, phase C1): BINOMIAL opinions only — one boolean
proposition per opinion. The multinomial/Dirichlet generalization (needed
for multi-way fields like full tag distributions) is deliberately OUT of
scope for C1; multi-label tags are modelled per-tag as independent binomial
opinions until a later phase introduces Dirichlet opinions.
"""
from __future__ import annotations

from dataclasses import dataclass

# Non-informative prior weight W of the Beta/Dirichlet correspondence
# (spec §3: "prior weight 2"). Fixed, not parameterized: the evidence
# bijection must mean the same thing everywhere or per-field opinions stop
# being comparable ledgers.
PRIOR_WEIGHT = 2.0

# Float-dust tolerance for the b+d+u=1 constraint and component ranges.
# Tight enough that any real arithmetic error fails loudly; loose enough
# that closed-form operator outputs (ratios over a shared denominator,
# error ~1e-16) never trip it.
_EPS = 1e-9


@dataclass(frozen=True)
class Opinion:
    """A binomial Subjective Logic opinion about one boolean proposition.

    Spec §3: belief `b`, disbelief `d`, uncertainty `u` (b+d+u=1), and base
    rate `a` — the prior probability we'd assign knowing nothing but the
    category/venue. Mathematically identical to a Beta distribution (see
    `from_evidence`/`to_evidence`), which is what makes an opinion an
    auditable evidence ledger and a samplable distribution at once.

    Validation is fail-loud (docs/CODING_CONVENTIONS.md, fail-loud-on-
    misconfiguration): any component outside [0,1] or a mass sum off 1
    raises ValueError at construction — a malformed belief state must never
    propagate silently through trust arithmetic.
    """

    b: float
    d: float
    u: float
    a: float

    def __post_init__(self) -> None:
        for name in ("b", "d", "u", "a"):
            value = getattr(self, name)
            if not (-_EPS <= value <= 1.0 + _EPS):
                raise ValueError(
                    f"Opinion.{name}={value!r} is outside [0, 1]; refusing to "
                    f"construct a malformed opinion (spec §3: b, d, u, a are "
                    f"probability masses)."
                )
        total = self.b + self.d + self.u
        if abs(total - 1.0) > _EPS:
            raise ValueError(
                f"Opinion mass must satisfy b+d+u=1 (spec §3); got "
                f"b={self.b!r} d={self.d!r} u={self.u!r} (sum={total!r})."
            )

    @property
    def expectation(self) -> float:
        """Projected probability E = b + a*u (spec §3: the opinion viewed as
        a probability distribution; uncertainty mass falls to the base rate).
        """
        return self.b + self.a * self.u

    @classmethod
    def from_evidence(cls, r: float, s: float, a: float = 0.5) -> "Opinion":
        """Map Beta evidence counts to an opinion (spec §3 evidence ledger).

        r = positive (confirming) evidence, s = negative (denying) evidence,
        with the fixed non-informative prior weight W=2:

            b = r / (r + s + W)    d = s / (r + s + W)    u = W / (r + s + W)

        Zero evidence yields the vacuous opinion (u=1). Negative counts are
        a caller bug and fail loudly.
        """
        if r < 0 or s < 0:
            raise ValueError(
                f"Evidence counts must be non-negative; got r={r!r} s={s!r} "
                f"(spec §3: an evidence ledger cannot hold negative evidence)."
            )
        denom = r + s + PRIOR_WEIGHT
        return cls(b=r / denom, d=s / denom, u=PRIOR_WEIGHT / denom, a=a)

    def to_evidence(self) -> tuple[float, float]:
        """Inverse of `from_evidence` (spec §3 — the mapping is bijective):

            r = W*b / u        s = W*d / u

        A dogmatic opinion (u=0) corresponds to infinite evidence and has no
        finite ledger; asking for one is a modelling error and fails loudly
        rather than returning a fabricated count (never-fabricate rule,
        docs/CODING_CONVENTIONS.md).
        """
        if self.u <= 0.0:
            raise ValueError(
                f"Dogmatic opinion (u={self.u!r}) has no finite evidence "
                f"ledger: r,s would be infinite (spec §3). Nothing produced "
                f"by from_evidence() is dogmatic, so this opinion did not "
                f"come from evidence counts."
            )
        return (PRIOR_WEIGHT * self.b / self.u, PRIOR_WEIGHT * self.d / self.u)


@dataclass(frozen=True)
class FourStateThresholds:
    """Explicit b/d/u cutlines for the 4-state mapping (spec §3 table).

    Passed explicitly to `four_state` — never defaulted here — because the
    concrete numbers become the user-facing meaning of the confidence words
    and are a founder-crucial ratification at C5 (spec §11, decision 3).
    Keeping them a versioned value object (not constants buried in logic)
    makes every threshold change a visible diff on the trust path.

    Fields (all probability masses in [0,1]):
      disputed_min_b / disputed_min_d — both-high signature of live conflict.
      confirmed_min_b / confirmed_max_u — strong corroborated belief.
      likely_min_b — moderate-belief floor.
      unverified_min_u — the "nobody really knows yet" uncertainty floor.
    """

    disputed_min_b: float
    disputed_min_d: float
    confirmed_min_b: float
    confirmed_max_u: float
    likely_min_b: float
    unverified_min_u: float

    def __post_init__(self) -> None:
        for name in (
            "disputed_min_b", "disputed_min_d", "confirmed_min_b",
            "confirmed_max_u", "likely_min_b", "unverified_min_u",
        ):
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                raise ValueError(
                    f"FourStateThresholds.{name}={value!r} is outside [0, 1]."
                )
        if self.disputed_min_b + self.disputed_min_d > 1.0:
            raise ValueError(
                f"disputed_min_b + disputed_min_d = "
                f"{self.disputed_min_b + self.disputed_min_d!r} > 1: no valid "
                f"opinion could ever be disputed (b+d<=1 always), which would "
                f"silently disable the conflict state — fail loud instead."
            )
        if self.likely_min_b > self.confirmed_min_b:
            raise ValueError(
                f"likely_min_b={self.likely_min_b!r} exceeds confirmed_min_b="
                f"{self.confirmed_min_b!r}: 'confirmed' must demand at least "
                f"as much belief as 'likely' (spec §3 table ordering)."
            )
        if self.confirmed_max_u >= self.unverified_min_u:
            raise ValueError(
                f"confirmed_max_u={self.confirmed_max_u!r} must be strictly "
                f"below unverified_min_u={self.unverified_min_u!r}: an opinion "
                f"must never satisfy 'strong corroborated belief' and 'nobody "
                f"really knows' at once (spec §3 table)."
            )


def four_state(opinion: Opinion, thresholds: FourStateThresholds) -> str:
    """Map an opinion onto the ratified 4-state confidence model (spec §3).

    Threshold table (spec §3): high u -> "unverified"; moderate b ->
    "likely"; high b + low u -> "confirmed"; high b AND high d ->
    "disputed". Disputed and unverified are STRUCTURALLY different states —
    conflict (b and d both high, u squeezed out) versus ignorance (u high)
    — which is the distinction the disputed-shown-never-hidden invariant
    needs the data model to respect.

    Precedence, most specific first: disputed > confirmed > unverified >
    likely. Disputed outranks everything (spec §6.6: a b/d collision routes
    to disputed even against a confirmed-strength belief — shown, never
    hidden). An opinion clearing no cutline falls back to "unverified":
    thin evidence that hasn't reached even the moderate-belief bar is
    still "nobody really knows yet", the fail-closed reading.
    """
    if opinion.b >= thresholds.disputed_min_b and opinion.d >= thresholds.disputed_min_d:
        return "disputed"
    if opinion.b >= thresholds.confirmed_min_b and opinion.u <= thresholds.confirmed_max_u:
        return "confirmed"
    if opinion.u >= thresholds.unverified_min_u:
        return "unverified"
    if opinion.b >= thresholds.likely_min_b:
        return "likely"
    return "unverified"


def _fused_base_rate(x: Opinion, y: Opinion) -> float:
    """Base-rate combination for cumulative fusion (Josang; spec §3).

    Weights each base rate by the other opinion's uncertainty (the more
    certain party contributes more of the shared prior):

        a = (aX*uY + aY*uX - (aX+aY)*uX*uY) / (uX + uY - 2*uX*uY)

    degenerating to the plain average when the denominator vanishes (both
    vacuous or both dogmatic). Equal inputs pass through unchanged.
    """
    denom = x.u + y.u - 2.0 * x.u * y.u
    if denom <= _EPS:
        return (x.a + y.a) / 2.0
    return (x.a * y.u + y.a * x.u - (x.a + y.a) * x.u * y.u) / denom


def cumulative_fusion(x: Opinion, y: Opinion) -> Opinion:
    """Fuse two opinions from INDEPENDENT sources (spec §3 cumulative fusion).

    Equivalent to pooling the two Beta evidence ledgers — fusing
    from_evidence(r1,s1) with from_evidence(r2,s2) equals
    from_evidence(r1+r2, s1+s2) — which is why it applies only to sources
    that did not copy each other (use `averaging_fusion` for suspected
    syndication, spec §3: "two aggregators syndicating one feed must not
    count twice"). Closed form (kappa = uX + uY - uX*uY):

        b = (bX*uY + bY*uX) / kappa      u = uX*uY / kappa

    Two dogmatic opinions (uX=uY=0) have no defined cumulative fusion
    without a relative-dogmatism weighting we deliberately do not model
    (nothing evidence-derived is dogmatic); that case fails loudly.
    """
    kappa = x.u + y.u - x.u * y.u
    if kappa <= _EPS:
        raise ValueError(
            f"Cumulative fusion of two dogmatic opinions (uX={x.u!r}, "
            f"uY={y.u!r}) is undefined without relative-dogmatism weights, "
            f"which C1 deliberately does not model (spec §3: opinions here "
            f"are evidence ledgers, and finite evidence is never dogmatic)."
        )
    b = (x.b * y.u + y.b * x.u) / kappa
    d = (x.d * y.u + y.d * x.u) / kappa
    u = (x.u * y.u) / kappa
    return Opinion(b=b, d=d, u=u, a=_fused_base_rate(x, y))


def averaging_fusion(x: Opinion, y: Opinion) -> Opinion:
    """Fuse two opinions from DEPENDENT sources (spec §3 averaging fusion).

    For sources suspected of copying each other — two aggregators
    syndicating one feed must not count twice, so their shared evidence is
    averaged instead of pooled. Closed form:

        b = (bX*uY + bY*uX) / (uX + uY)      u = 2*uX*uY / (uX + uY)

    Fusing an opinion with itself returns it unchanged (idempotence — the
    defining contrast with cumulative fusion, which would double-count).
    Two dogmatic opinions take the well-defined limit: the component-wise
    average. Base rate is the plain average of the two priors.
    """
    denom = x.u + y.u
    if denom <= _EPS:
        # Limit case uX=uY=0: averaging fusion degenerates to the
        # component-wise mean (still a valid opinion since masses sum to 1).
        return Opinion(
            b=(x.b + y.b) / 2.0,
            d=(x.d + y.d) / 2.0,
            u=0.0,
            a=(x.a + y.a) / 2.0,
        )
    b = (x.b * y.u + y.b * x.u) / denom
    d = (x.d * y.u + y.d * x.u) / denom
    u = 2.0 * x.u * y.u / denom
    return Opinion(b=b, d=d, u=u, a=(x.a + y.a) / 2.0)


def trust_discount(opinion: Opinion, trust: "Opinion | float") -> Opinion:
    """Discount an opinion by how much we trust its source (spec §3).

    `trust` is either a full SL opinion about the source's reliability (its
    projected probability t = b + a*u does the discounting — Josang's
    probability-sensitive transitivity) or a plain scalar t in [0,1] (e.g.
    a measured per-source reliability weight, spec §7). Effect:

        b' = t*b      d' = t*d      u' = 1 - t*(b + d)      a' = a

    Distrust converts the source's claimed evidence into uncertainty — it
    never flips belief into disbelief (a liar's claim is not evidence of
    the opposite, it is no evidence at all). t=1 is the identity; t=0
    discards the source entirely, leaving the vacuous opinion.
    """
    if isinstance(trust, Opinion):
        t = trust.expectation
    elif isinstance(trust, (int, float)) and not isinstance(trust, bool):
        t = float(trust)
        if not (0.0 <= t <= 1.0):
            raise ValueError(
                f"Scalar trust must be in [0, 1]; got {trust!r} (spec §3: "
                f"trust discounting weakens an opinion, never amplifies it)."
            )
    else:
        raise TypeError(
            f"trust must be an Opinion or a scalar in [0, 1]; got "
            f"{type(trust).__name__}."
        )
    return Opinion(
        b=t * opinion.b,
        d=t * opinion.d,
        u=1.0 - t * (opinion.b + opinion.d),
        a=opinion.a,
    )


def age_evidence(opinion: Opinion, factor: float) -> Opinion:
    """Age an opinion by exponentially decaying its evidence counts (spec §3
    "evidence aging so stale confirmations fade"; spec §6.2 "staleness is
    evidence": between observations a deterministic decay step inflates u).

    `factor` in (0, 1] is the exponential decay multiplier for one aging
    step (the caller computes it from elapsed time, e.g. exp(-dt/tau));
    factor=1 is the identity. Both evidence counts shrink by the same
    factor, so the belief/disbelief RATIO is preserved while uncertainty
    grows — staleness makes us less sure, not differently opinionated.
    Values outside (0, 1] fail loudly: an exponential decay factor cannot
    be 0, negative, or amplifying. Dogmatic opinions (u=0) have no evidence
    ledger to age and fail loudly via `to_evidence`.
    """
    if not (0.0 < factor <= 1.0):
        raise ValueError(
            f"Aging factor must be in (0, 1]; got {factor!r} (an exponential "
            f"decay multiplier can neither amplify evidence nor erase it in "
            f"one step)."
        )
    r, s = opinion.to_evidence()
    return Opinion.from_evidence(r * factor, s * factor, a=opinion.a)
