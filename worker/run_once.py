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
from typing import Sequence

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

class TotalRunFailure(RuntimeError):
    """Every attempted source errored — the run did no useful work.

    Raised (never returned as a code) so the deadman() context pings /fail:
    healthchecks must alert on a run that produced nothing, not log a
    heartbeat for it (first-real-run finding, 2026-07-15).
    """


def enforce_useful_work(counts: dict, attempted: int) -> None:
    """Fail LOUD when every attempted source errored (zero useful work).

    Raises TotalRunFailure (never returns a code) so the deadman() context
    pings /fail — healthchecks must alert on a dead run, not log a healthy
    heartbeat for it. Caught on the FIRST real run (2026-07-15): 3/3 sources
    errored on a stale model id, yet the job went green and the dead-man
    pinged success. Partial errors remain a success with a loud warning —
    some work happened, and per-source detail is in the RunReport/replay.
    """
    errors = counts.get("errors", 0)
    if attempted and errors >= attempted:
        raise TotalRunFailure(
            f"all {attempted} attempted source(s) errored — refusing to "
            "report success for a run that did zero useful work."
        )
    if errors:
        logger.warning(
            "%d of %d source(s) errored this run — run succeeds because other "
            "sources progressed; per-source detail is in the RunReport and "
            "the replay log.", errors, attempted,
        )


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


def _positive_int(raw: str) -> int:
    """argparse type for --max-sources: a budget ceiling is positive or it is
    rejected — 0/negative must never mean "uncapped" (fail-closed, evaluator
    finding PR #12 round 1)."""
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{raw!r} is not an integer") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError(
            f"{value} is not a valid budget ceiling — must be a positive "
            "integer; a ceiling of 0 does not mean uncapped, it means no run."
        )
    return value


def apply_source_ceiling(sources: Sequence[dict], cap: int | None) -> list:
    """Cap how many sources one real run may process (FinOps §14.3: budget
    ceilings exist BEFORE the recurring loop, not after the first surprise
    bill). cap=None means uncapped — the caller logs that loudly, so an
    uncapped run is always a visible, deliberate choice. Any other value must
    be a positive int: 0/negative is a misconfiguration and FAILS CLOSED
    (raises) instead of silently disabling the guard. Order is preserved
    (DB order), so the ceiling truncates the tail, deterministically.
    """
    if cap is None:
        return list(sources)
    if cap <= 0:
        raise ValueError(
            f"source ceiling {cap} is invalid — a budget cap must be positive; "
            "0/negative fails closed, it never means uncapped."
        )
    if len(sources) > cap:
        logger.warning(
            "budget ceiling: processing %d of %d enabled sources this run "
            "(raise --max-sources / ONELIVE_MAX_SOURCES_PER_RUN deliberately).",
            cap, len(sources),
        )
    return list(sources[:cap])


def order_for_rotation(rows: Sequence[tuple]) -> list:
    """Order source rows least-recently-ATTEMPTED first (never-attempted
    before everything), deterministic tiebreak by source_id.

    The invariant: under a per-run budget cap, ORDER IS COVERAGE — this
    ordering makes the capped recurring loop sweep the whole catalog
    instead of re-feeding the same head-of-table slice. "Attempted"
    includes failed and not-modified fetches (the adapter records them as
    raw_fetch attempt rows — worker/fetch/http_fetch.py), so a
    permanently-dead source cannot monopolize the window.

    Rows are (source_id, name, base_url, source_type, config,
    last_fetched_at);
    the key unpacks first/last by position-name so middle-column changes
    cannot shift what gets sorted, and its leading bucket element keeps
    the never-attempted sentinel from ever meeting a datetime. Python-side
    sort is deliberate (unit-testable, microseconds at this scale);
    revisit trigger: enabled-source count > 2,000 (printed by every capped
    run's budget-ceiling log line) -> move this ordering into the SELECT.
    Design history: FRICTION_LOG entry #3, PR #43 rounds 1-5.
    """
    def _key(row):
        source_id, *_middle, last_fetched_at = row
        never_fetched = last_fetched_at is None
        return (not never_fetched,
                _NEVER_FETCHED_SENTINEL if never_fetched else last_fetched_at,
                str(source_id))

    return sorted(rows, key=_key)


# Placeholder sort value for never-fetched sources. Any constant works: the
# bucket element of the key above guarantees it is never compared against a
# real timestamp — it only ties with itself, then source_id breaks the tie.
_NEVER_FETCHED_SENTINEL = 0


def _resolve_source_cap(cli_value: int | None) -> int | None:
    """--max-sources wins; else ONELIVE_MAX_SOURCES_PER_RUN; else uncapped
    (logged loudly by the caller). Any non-positive or non-integer value from
    either channel is a misconfig and fails loud (closed) rather than silently
    running uncapped."""
    if cli_value is not None:
        if cli_value <= 0:
            raise SystemExit(
                f"--max-sources={cli_value} is invalid — the budget ceiling "
                "must be a positive integer (fails closed)."
            )
        return cli_value
    raw = os.getenv("ONELIVE_MAX_SOURCES_PER_RUN")
    if raw is None:
        return None
    if raw == "":
        # Set-but-empty is a misconfiguration, not "uncapped": CI forwards
        # unset variables as empty strings (the exact failure mode that broke
        # OPENAI_REVIEW_MODEL in PR #11), so an empty budget cap fails closed.
        raise SystemExit(
            "ONELIVE_MAX_SOURCES_PER_RUN is set but empty — the budget ceiling "
            "must be a positive integer, or the variable must be fully unset "
            "for a deliberate (loudly logged) uncapped run. Fails closed."
        )
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(
            f"ONELIVE_MAX_SOURCES_PER_RUN={raw!r} is not an integer — refusing "
            "to guess whether this run should be capped."
        ) from exc
    if value <= 0:
        raise SystemExit(
            f"ONELIVE_MAX_SOURCES_PER_RUN={value} is invalid — the budget "
            "ceiling must be a positive integer (fails closed)."
        )
    return value


def filter_by_coverage_class(sources: Sequence[dict], letter: str | None) -> list:
    """Keep only sources the CATALOG declares to be Coverage Law class `letter`.

    Dispatch-only selection, never a schedule behaviour: the armed cron passes
    None and every enabled source is processed exactly as before. It exists so
    a deliberate run can be aimed at one class (e.g. "the class B follow-pages
    walk, on ten public-HTML sources") without hand-picking source names, and
    so the run's own report says which class it ran.

    The verdict comes from worker.sourcing.source_class.classify_entry over the
    posture worker.sourcing.catalog_posture resolves (the row's own stored
    declaration, else the committed catalog's entry for it) — the same two
    authorities the follow-pages walk uses, so a source cannot be selected as
    class B here and judged otherwise three lines later. An unknown letter FAILS CLOSED (SystemExit) rather than
    silently matching nothing, which would look like an empty catalog.
    """
    if letter is None:
        return list(sources)
    from worker.sourcing.catalog_posture import resolve_entry
    from worker.sourcing.source_class import CLASS_LETTERS, classify_entry

    letter = letter.strip().upper()
    if letter not in CLASS_LETTERS:
        raise SystemExit(
            f"--source-class={letter!r} is not a Coverage Law class letter "
            f"({', '.join(sorted(CLASS_LETTERS))}) — refusing to run a filter "
            "that would silently match nothing."
        )
    kept = []
    distribution: dict = {}
    reasons: dict = {}
    empty_config = 0
    for source in sources:
        config = source.get("config") or {}
        if not config:
            empty_config += 1
        verdict = classify_entry(resolve_entry(
            name=source.get("name"), url=source.get("url"), config=config))
        distribution[verdict.source_class] = distribution.get(verdict.source_class, 0) + 1
        reasons[verdict.reason] = reasons.get(verdict.reason, 0) + 1
        if verdict.source_class == letter:
            kept.append(source)
    logger.warning(
        "class filter --source-class=%s: %d of %d enabled source(s) match "
        "(dispatch-only; the scheduled loop never filters).",
        letter, len(kept), len(sources),
    )
    if not kept:
        # A filter that keeps nothing is a DIAGNOSIS, not a shrug: the same
        # verdict decides whether the follow-pages walk ever fires, so "zero
        # class B sources" must say WHY in the run's own output rather than
        # send a human to guess at the database. Counts and the classifier's
        # own reason strings only — no source names, no URLs, no config
        # values, so a fail-closed diagnostic can never become a data leak.
        logger.warning(
            "class distribution across all %d source(s): %s; rows with an "
            "EMPTY config (nothing declared, so classify_entry falls to its "
            "unrecognized-posture rule): %d",
            len(sources), sorted(distribution.items()), empty_config,
        )
        for reason, count in sorted(reasons.items(), key=lambda kv: -kv[1])[:5]:
            logger.warning("  %4d source(s): %s", count, reason)
    return kept


def _run_real(max_sources: int | None = None, source_class: str | None = None) -> int:
    # Budget-cap misconfiguration must fail loud DETERMINISTICALLY — before
    # any provider/DB access, so it can never hide behind "no enabled sources
    # found" or a connection error (evaluator finding, PR #12 round 2).
    cap = _resolve_source_cap(max_sources)

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
            # last_fetched_at feeds order_for_rotation() below — the capped
            # recurring loop must sweep the catalog, not re-fetch the same
            # head-of-table slice every run. The correlated max() rides
            # idx_raw_fetch_source_time (migration 0003).
            # s.config is the catalog entry tools/import_sources.py stored
            # verbatim on the row. The orchestrator's class B follow-pages
            # walk reads its DECLARED access posture (access_method/allowed)
            # to decide whether a source's own event pages may be followed —
            # the class letter is the catalog's verdict, never inferred from
            # the URL. A row with no config classifies D and is simply not
            # followed; it is still FETCHED exactly as before, so reading
            # this column can only add coverage, never remove any.
            cur.execute(
                "select s.source_id, s.name, s.base_url, s.source_type, s.config, "
                "       (select max(rf.fetched_at) from raw_fetch rf "
                "         where rf.source_id = s.source_id) as last_fetched_at "
                "from source s where s.enabled = true"
            )
            rows = cur.fetchall()
    rows = order_for_rotation(rows)
    sources = []
    skipped_no_url = []
    for (sid, name, base_url, source_type, config, _last_fetched_at) in rows:
        if not base_url:
            skipped_no_url.append(name)
            continue
        sources.append({
            "source_id": str(sid),
            "name": name,
            "url": base_url,
            "source_class": source_type,
            "config": config if isinstance(config, dict) else {},
        })
    if skipped_no_url:
        logger.warning(
            "skipped %d enabled source(s) with no base_url: %s",
            len(skipped_no_url), ", ".join(skipped_no_url[:10]),
        )
    if not sources:
        logger.error("no enabled, fetchable sources found in the `source` table.")
        return 1

    # The class filter runs BEFORE the budget ceiling so a "10 class B
    # sources" run means ten class B sources, not ten rotation slots of which
    # some happen to be class B.
    sources = filter_by_coverage_class(sources, source_class)
    if not sources:
        logger.error(
            "no enabled source matches --source-class=%s — nothing to run.",
            source_class)
        return 1

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
    # Attempted = per-source results actually recorded by the loop (a source
    # skipped before attempt has no result row), falling back to the input
    # list only if the report carries none — evaluator nit, PR #21 r2.
    enforce_useful_work(report.counts, len(report.results) or len(sources))
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
        type=_positive_int,
        default=None,
        help="Budget ceiling: process at most N sources this run (positive "
             "integer; falls back to ONELIVE_MAX_SOURCES_PER_RUN; unset = "
             "uncapped, logged loudly).",
    )
    parser.add_argument(
        "--source-class",
        default=None,
        help="Dispatch-only: run ONLY sources the catalog declares to be this "
             "Coverage Law class letter (A/B/C/D/E/F). The scheduled loop "
             "never passes it and is unfiltered.",
    )
    args = parser.parse_args()
    # Sentinel minimum (Session Contract #1): this is the scheduled entrypoint,
    # so it carries both signals — Sentry (no-op without SENTRY_DSN) and the
    # healthchecks dead-man ping (no-op without ORCHESTRATOR_PING_URL). The
    # charter forbids scheduling a recurring loop until both env vars exist.
    init_sentry("worker")
    with deadman():
        if args.real:
            return _run_real(args.max_sources, args.source_class)
        if args.source_class:
            raise SystemExit(
                "--source-class applies to --real runs only (the stub path "
                "has one in-memory source and no catalog to classify).")
        return _run_stub()


if __name__ == "__main__":
    raise SystemExit(main())
