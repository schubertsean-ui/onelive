#!/usr/bin/env python3
"""Profile a single pure-logic hot-path function by dotted path, N reps.

Usage: tools/profile_target.py worker.confidence:derive_confidence --reps 20000
Prints min/median/mean/max wall time per call (via timeit) + optional
cProfile top-20 by cumulative time with --profile. Targets must be importable
zero-network pure functions (see tests/test_perf_benchmarks.py for the
curated, known-safe target list). Exits 2 if the target can't be imported or
called with its built-in demo args (loud failure, not a silent skip).
"""
from __future__ import annotations

import argparse
import cProfile
import importlib
import io
import pathlib
import pstats
import statistics
import sys
import timeit

# Make `worker.*` / `ai.*` / `api.*` importable regardless of cwd, same as
# tests/conftest.py does for pytest.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# Known-safe demo call args per dotted target, so this tool works standalone
# without the caller having to know each function's signature. Kept in sync
# with tests/test_perf_benchmarks.py's BENCHMARK_TARGETS list by convention
# (not by import, to keep this script runnable with zero test-suite coupling).
_DEMO_ARGS = {
    "worker.confidence:derive_confidence": ((["organizer", "attendee", "attendee"],), {}),
    "worker.gating:multi_confirm_gate": ((["organizer", "attendee", "attendee"],), {}),
    "ai.eval_harness:score_extraction": (
        (
            {"title": "Jazz Night", "start_time": "2026-07-11T20:00:00", "venue_name": "The Blue Room"},
            {"title": "Jazz Night", "start_time": "2026-07-11T20:00:00", "venue_name": "The Blue Room"},
        ),
        {},
    ),
}


def _resolve(dotted: str):
    if ":" not in dotted:
        raise ValueError(f"expected 'module.path:function_name', got: {dotted!r}")
    mod_name, func_name = dotted.split(":", 1)
    try:
        mod = importlib.import_module(mod_name)
    except ImportError as exc:
        raise ImportError(f"could not import module '{mod_name}': {exc}") from exc
    if not hasattr(mod, func_name):
        raise AttributeError(f"module '{mod_name}' has no attribute '{func_name}'")
    return getattr(mod, func_name)


def _demo_call_args(dotted: str):
    if dotted in _DEMO_ARGS:
        return _DEMO_ARGS[dotted]
    raise KeyError(
        f"no known-safe demo args registered for '{dotted}'. Add an entry to "
        f"_DEMO_ARGS in tools/profile_target.py (this tool refuses to guess "
        f"call args for an unknown function signature)."
    )


def run_timeit(func, args, kwargs, reps: int) -> list[float]:
    samples = []
    for _ in range(reps):
        t0 = timeit.default_timer()
        func(*args, **kwargs)
        samples.append(timeit.default_timer() - t0)
    return samples


def run_cprofile(func, args, kwargs, reps: int) -> str:
    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(reps):
        func(*args, **kwargs)
    profiler.disable()
    buf = io.StringIO()
    stats = pstats.Stats(profiler, stream=buf).sort_stats("cumulative")
    stats.print_stats(20)
    return buf.getvalue()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("target", help="dotted target: module.path:function_name")
    ap.add_argument("--reps", type=int, default=2000, help="number of calls to time (default 2000)")
    ap.add_argument("--profile", action="store_true", help="also run cProfile and print top-20 by cumulative time")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        func = _resolve(args.target)
        call_args, call_kwargs = _demo_call_args(args.target)
    except (ValueError, ImportError, AttributeError, KeyError) as exc:
        print(f"profile_target.py: {exc}", file=sys.stderr)
        return 2

    # Correctness check: fail loudly if the demo call itself raises, rather
    # than reporting misleading timing on a function that's actually broken.
    try:
        func(*call_args, **call_kwargs)
    except Exception as exc:
        print(f"profile_target.py: demo call to '{args.target}' raised {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    samples = run_timeit(func, call_args, call_kwargs, args.reps)
    samples_us = sorted(s * 1e6 for s in samples)
    print(f"profile_target.py: {args.target} — {args.reps} reps")
    print(f"  min:    {samples_us[0]:.2f} us")
    print(f"  median: {statistics.median(samples_us):.2f} us")
    print(f"  mean:   {statistics.mean(samples_us):.2f} us")
    print(f"  max:    {samples_us[-1]:.2f} us")

    if args.profile:
        print()
        print(f"profile_target.py: cProfile top-20 by cumulative time ({args.reps} reps)")
        print(run_cprofile(func, call_args, call_kwargs, args.reps))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
