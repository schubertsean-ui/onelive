"""Auto-promote entrypoint — drives worker.autopromote.run_autopromote.

A SEPARATE entrypoint from worker/run_once.py by design: the extraction loop
(orchestrator) and the publish pass (autopromote) are two independently
auditable stages with the trust gate between them, and the orchestrator must
stay structurally unable to reach worker.promote (tests/test_orchestrator.py).
This file is the only scheduled path that publishes, and everything about it
fails closed:

  * `--real` is mandatory to touch the database at all. Without it this
    entrypoint refuses to run (exit 2) rather than inventing a stub publish —
    there is no meaningful offline smoke for a pass whose entire job is a
    DB-state transition, and a publish path must never run by accident.
  * `--limit` is a REQUIRED positive integer (argparse type check): the batch
    ceiling exists before the first scheduled run, and 0/negative is rejected
    — it never means "uncapped" (same rule as run_once's --max-sources).
  * The DSN comes from worker.db_config.resolve_dsn (loud RuntimeError when
    unset — never a silent localhost fallback).
  * AUTO_PUBLISH_RATIFIED off makes the pass itself a loud no-op that promotes
    nothing (worker/autopromote.py) — a scheduled run with the switch off is a
    healthy heartbeat, not a publish.

Sentinel minimum (CLAUDE.md): Sentry init + healthchecks dead-man ping wrap
the run, exactly as run_once.py does — no scheduled loop ships without both.
"""
import argparse
import logging
import os
import sys

import psycopg2

logger = logging.getLogger(__name__)

# Make the repo root importable when this file is invoked directly as a
# script (`python worker/run_autopromote.py`) — mirrors worker/run_once.py's
# identical fix for the identical reason. A no-op under `-m` or pytest.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.autopromote import run_autopromote
from worker.db_config import resolve_dsn
from worker.sentinel import deadman, init_sentry


def _positive_int(raw: str) -> int:
    """argparse type for --limit: the batch ceiling is positive or it is
    rejected — 0/negative must never mean "uncapped" (fail-closed, the same
    contract as run_once's --max-sources)."""
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{raw!r} is not an integer") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError(
            f"{value} is not a valid batch ceiling — must be a positive "
            "integer; a ceiling of 0 does not mean uncapped, it means no run."
        )
    return value


def _run_real(limit: int) -> int:
    """Open the real DB (resolve_dsn fails loud when unconfigured) and run one
    bounded pass. The connection is closed even when the pass raises."""
    conn = psycopg2.connect(resolve_dsn())
    try:
        report = run_autopromote(conn, limit=limit)
    finally:
        conn.close()

    print("AutopromoteReport:")
    print(f"  enabled:  {report.enabled}")
    print(f"  counts:   {report.counts}")
    for o in report.outcomes:
        suffix = f" event_id={o.event_id}" if o.event_id else ""
        print(f"  - {o.candidate_id}: action={o.action}{suffix} detail={o.detail}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one bounded OneLive auto-promote pass (ratified "
                    "earned-confidence publish; fail-closed behind "
                    "AUTO_PUBLISH_RATIFIED).",
    )
    parser.add_argument(
        "--real",
        action="store_true",
        help="Operate on the real database (ONELIVE_DB_DSN via resolve_dsn). "
             "Required: this entrypoint publishes, so it has no stub mode.",
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        required=True,
        help="Batch ceiling: examine at most N ready_to_promote candidates "
             "this pass (required positive integer; there is no uncapped mode).",
    )
    args = parser.parse_args()
    if not args.real:
        logger.error(
            "run_autopromote refuses to run without --real: this entrypoint's "
            "only job is a real DB publish pass, and a publish path must never "
            "start by accident. Re-run with --real (and --limit)."
        )
        return 2
    # Sentinel minimum (CLAUDE.md): Sentry + dead-man ping around the pass,
    # matching worker/run_once.py — no scheduled loop without both signals.
    init_sentry("worker")
    with deadman():
        return _run_real(args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
