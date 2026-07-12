"""Perf regression budgets for pure-logic hot-path functions. Opt-in only
(marked @pytest.mark.perf, auto-skipped by default — see conftest.py). Run
with `pytest -m perf -v` or profile a single target directly via
`tools/profile_target.py module.path:func_name --reps N [--profile]`.

Each budget is intentionally generous (10-50x the observed baseline on this
sandbox) so these catch a real algorithmic regression (e.g. an accidental
O(n^2) loop, an added network/DB call) rather than flaking on machine noise.
"""
import statistics
import timeit

import pytest

from ai.eval_harness import score_extraction
from worker.confidence import derive_confidence
from worker.gating import multi_confirm_gate

# (label, callable, args, kwargs, reps, budget_median_seconds)
BENCHMARK_TARGETS = [
    (
        "worker.confidence:derive_confidence",
        derive_confidence,
        (["organizer", "attendee", "attendee"],),
        {},
        5000,
        50e-6,  # 50 us/call budget; observed baseline ~0.3-0.4 us
    ),
    (
        "worker.gating:multi_confirm_gate",
        multi_confirm_gate,
        (["organizer", "attendee", "attendee"],),
        {},
        5000,
        50e-6,  # observed baseline ~1.0 us
    ),
    (
        "ai.eval_harness:score_extraction",
        score_extraction,
        (
            {"title": "Jazz Night", "start_time": "2026-07-11T20:00:00", "venue_name": "The Blue Room"},
            {"title": "Jazz Night", "start_time": "2026-07-11T20:00:00", "venue_name": "The Blue Room"},
        ),
        {},
        2000,
        100e-6,  # observed baseline ~3.5-4 us
    ),
]


@pytest.mark.perf
@pytest.mark.parametrize(
    "label,func,args,kwargs,reps,budget_s",
    BENCHMARK_TARGETS,
    ids=[t[0] for t in BENCHMARK_TARGETS],
)
def test_perf_budget(label, func, args, kwargs, reps, budget_s):
    samples = []
    for _ in range(reps):
        t0 = timeit.default_timer()
        func(*args, **kwargs)
        samples.append(timeit.default_timer() - t0)
    median = statistics.median(samples)
    assert median < budget_s, (
        f"{label}: median call time {median * 1e6:.2f}us exceeds budget "
        f"{budget_s * 1e6:.2f}us over {reps} reps — investigate with "
        f"`tools/profile_target.py {label} --reps {reps} --profile`"
    )


@pytest.mark.perf
def test_derive_confidence_is_not_accidentally_quadratic():
    """Guard against an accidental O(n^2) creeping into derive_confidence.
    The function is expected O(n) in len(source_classes) (one pass to build a
    set). We compare two input sizes that are large enough that real work
    dominates timer/loop overhead (unlike a handful of microseconds, which is
    noise-dominated on a shared sandbox), and use best-of-many timeit.repeat
    instead of a naive average to reject GC/scheduler-noise outliers rather
    than a strict n vs 2n ratio check."""
    small = ["organizer"] + ["attendee"] * 5_000
    large = ["organizer"] + ["attendee"] * 500_000  # 100x larger

    def best_of(source_classes, number=20, repeat=5):
        return min(timeit.repeat(lambda: derive_confidence(source_classes), number=number, repeat=repeat)) / number

    t_small = best_of(small)
    t_large = best_of(large)
    ratio = t_large / t_small if t_small > 0 else float("inf")
    # At these sizes, timer/loop overhead is negligible, so a genuinely O(n)
    # implementation scales ~1:1 with input size: measured ~100-105x for a
    # 100x-larger input across repeated runs on this sandbox. A quadratic
    # regression would instead show ~10,000x (100x squared). Set the bar
    # comfortably between the two so this only fires on a real complexity
    # regression, not on linear behavior or ordinary timing jitter.
    assert ratio < 400, (
        f"derive_confidence scaled {ratio:.1f}x from a 5,001-item to a "
        f"500,001-item input (100x the size) — expected roughly 100x for "
        f"O(n), got much worse; investigate "
        f"with `tools/profile_target.py worker.confidence:derive_confidence --profile`."
    )
