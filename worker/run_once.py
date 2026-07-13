"""Orchestrator entrypoint — drives worker.orchestrator.run_loop.

Default (no flags) mode is a smoke test: a stub AI provider (no model call)
over a single in-memory source, so the loop itself — fetch, sensor, extract,
gate3, replay logging — is genuinely exercised end to end without a live
database or an Anthropic key. The loop never promotes (promotion is an
authenticated ops action), so no publish happens here. The one thing it needs is
network for the fetch step: the stub source points at a tiny, stable public
URL (fetch_url is HTTP-only, so a local file:// path is not an option). Only
that fetch step touches the network; sensors, extract, gate3, and replay run
identically regardless of which URL is fetched.

`--real` additionally requires ONELIVE_DB_DSN and an Anthropic API key to be
configured (it swaps in ClaudeProvider and expects real `source` rows from
the DB); it is guarded behind the flag specifically so importing this module,
or running it with no flags, never requires network or DB configuration.

This file drives worker.orchestrator.run_loop, which classifies candidates but
never promotes them: publishing to the canonical event table is an authenticated
ops action only (api/ops_candidates.py). run_once therefore has no publish side
effect of its own.
"""
import argparse
import logging
import os
import sys

logger = logging.getLogger(__name__)

# Make the repo root importable when this file is invoked directly as a
# script (`python worker/run_once.py`), where Python puts this file's own
# directory — not the repo root — at sys.path[0], so `import ai` / `import
# worker` would otherwise fail. Mirrors tests/conftest.py's identical fix for
# the identical reason. A no-op when already run as `python -m worker.run_once`
# or under pytest (repo root already on sys.path in both cases).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.bedrock_provider import BedrockProvider
from worker.orchestrator import run_loop
from worker.sentinel import deadman, init_sentry

# A tiny, stable public endpoint used only for the offline smoke path so
# `python worker/run_once.py` demonstrates a real fetch->sensor->extract->
# gate3 loop with zero configuration. httpbin's /html endpoint returns a
# small, stable static HTML page with real, non-trivial text content (well
# above the sensor's minimum length) and is not rate-limited for single GETs.
_SMOKE_SOURCE = {
    "source_id": None,
    "name": "smoke_stub_source",
    "url": "https://httpbin.org/html",
    "source_class": "social",
}


def _run_stub() -> int:
    ai = BedrockProvider(client=None, model_id="stub")
    report = run_loop(ai=ai, sources=[_SMOKE_SOURCE], sxsw_mode=False)
    print("RunReport:")
    print(f"  run_id:   {report.run_id}")
    print(f"  started:  {report.started}")
    print(f"  finished: {report.finished}")
    print(f"  counts:   {report.counts}")
    for r in report.results:
        print(f"  - {r.source_name}: stage={r.stage_reached} decision={r.decision} detail={r.detail}")
    return 0


def apply_source_ceiling(sources: list, cap) -> list:
    """Cap how many sources one real run may process (FinOps §14.3: budget
    ceilings exist BEFORE the recurring loop, not after the first surprise
    bill). cap None/<=0 means uncapped — but the caller logs that loudly, so
    an uncapped scheduled run is always a visible, deliberate choice. Order is
    preserved (DB order), so the ceiling truncates the tail, deterministically.
    """
    if cap is None or cap <= 0:
        return sources
    if len(sources) > cap:
        logger.warning(
            "budget ceiling: processing %d of %d enabled sources this run "
            "(raise --max-sources / ONELIVE_MAX_SOURCES_PER_RUN deliberately).",
            cap, len(sources),
        )
    return sources[:cap]


def _resolve_source_cap(cli_value) -> "int | None":
    """--max-sources wins; else ONELIVE_MAX_SOURCES_PER_RUN; else uncapped
    (logged loudly by the caller). A non-integer env value is a misconfig and
    fails loud rather than silently running uncapped."""
    if cli_value is not None:
        return cli_value
    raw = os.getenv("ONELIVE_MAX_SOURCES_PER_RUN")
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(
            f"ONELIVE_MAX_SOURCES_PER_RUN={raw!r} is not an integer — refusing "
            "to guess whether this run should be capped."
        ) from exc


def _run_real(max_sources=None) -> int:
    # Imported lazily, inside the guarded branch, so importing run_once.py
    # (or running its stub path) never requires anthropic/psycopg2 network
    # configuration — only `--real` pays that cost.
    from ai.claude_provider import ClaudeProvider
    from worker.candidate_store import db as candidate_db

    dsn = os.getenv("ONELIVE_DB_DSN")
    if not dsn:
        logger.error("--real requires ONELIVE_DB_DSN to be set.")
        return 1

    ai = ClaudeProvider()
    # Column names mirror the `source` schema (migrations 0001 + 0010):
    # source_id / name / base_url / source_type / enabled. The orchestrator's
    # per-source dict contract is {source_id, name, url, source_class} (see
    # worker.orchestrator.run_loop), so base_url -> url and source_type ->
    # source_class are mapped explicitly here. A row with a null base_url is
    # skipped loudly (it cannot be fetched) rather than fed a None url.
    with candidate_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select source_id, name, base_url, source_type "
                "from source where enabled = true"
            )
            rows = cur.fetchall()
    sources = []
    skipped_no_url = []
    for (sid, name, base_url, source_type) in rows:
        if not base_url:
            skipped_no_url.append(name)
            continue
        sources.append({
            "source_id": str(sid),
            "name": name,
            "url": base_url,
            "source_class": source_type,
        })
    if skipped_no_url:
        logger.warning(
            "skipped %d enabled source(s) with no base_url: %s",
            len(skipped_no_url), ", ".join(skipped_no_url[:10]),
        )
    if not sources:
        logger.error("no enabled, fetchable sources found in the `source` table.")
        return 1

    cap = _resolve_source_cap(max_sources)
    if cap is None:
        logger.warning(
            "NO per-run source ceiling set (--max-sources / "
            "ONELIVE_MAX_SOURCES_PER_RUN) — processing all %d sources. A "
            "scheduled run should always set one (§14.3 budget caps).",
            len(sources),
        )
    sources = apply_source_ceiling(sources, cap)

    report = run_loop(ai=ai, sources=sources, sxsw_mode=False, dsn=dsn)
    print("RunReport:")
    print(f"  run_id:   {report.run_id}")
    print(f"  counts:   {report.counts}")
    for r in report.results:
        print(f"  - {r.source_name}: stage={r.stage_reached} decision={r.decision} detail={r.detail}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the OneLive orchestrator loop once.")
    parser.add_argument(
        "--real",
        action="store_true",
        help="Use ClaudeProvider and real `source` rows from ONELIVE_DB_DSN instead of the offline stub.",
    )
    parser.add_argument(
        "--max-sources",
        type=int,
        default=None,
        help="Budget ceiling: process at most N sources this run (falls back to "
             "ONELIVE_MAX_SOURCES_PER_RUN; unset = uncapped, logged loudly).",
    )
    args = parser.parse_args()
    # Sentinel minimum (Session Contract #1): this is the scheduled entrypoint,
    # so it carries both signals — Sentry (no-op without SENTRY_DSN) and the
    # healthchecks dead-man ping (no-op without ORCHESTRATOR_PING_URL). The
    # charter forbids scheduling a recurring loop until both env vars exist.
    init_sentry("worker")
    with deadman():
        return _run_real(args.max_sources) if args.real else _run_stub()


if __name__ == "__main__":
    raise SystemExit(main())
