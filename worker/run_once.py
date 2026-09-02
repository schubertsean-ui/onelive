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
from worker.crawl_state import TickBudget
from worker.orchestrator import render_run_table, run_loop
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
    blocked = counts.get("blocked", 0)
    if attempted and blocked >= attempted:
        # LOUD, but NOT a failure. A wall (401/403) or a back-off (429/503) is
        # a classified outcome routed to the claim queue — the catalog telling
        # us something true — not the harness being broken, which is what
        # TotalRunFailure and the dead-man alarm exist to catch. Failing the
        # cron on a wave that legitimately hit walled sources would train the
        # founder to ignore the alarm, and that costs more than this wave did.
        logger.warning(
            "every one of the %d source(s) in this wave was blocked (wall or "
            "back-off) — no extraction ran. The run is a SUCCESS: each block is "
            "classified and logged (grep INGEST_WALL_OBSERVED_CLASS_D for the "
            "claim queue). If this repeats across waves, the catalog's access "
            "postures are the thing to look at, not the loop.", attempted,
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
    print()
    print(render_run_table(report))
    print()
    print(render_outcomes(report, model_id=_provider_model_id(ai)))
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


def _provider_model_id(ai) -> str | None:
    """The model id a provider exposes, whatever it calls the attribute.

    ClaudeProvider names it `model`; BedrockProvider names it `model_id`.
    Asking for only one of them meant the cost line printed "unknown" against
    the other — not a wrong number, but a missing one, and the founder asked
    for $ as an outcome (evaluator nit, seat openai / lens absence-only).
    Reading both is the fix; an unknown id still prints as unknown, never as a
    guess.
    """
    for attr in ("model", "model_id"):
        value = getattr(ai, attr, None)
        if value:
            return str(value)
    return None


def render_outcomes(report, *, model_id=None) -> str:
    """The tick's OUTCOMES line: fetches, extracts, dollars, and why it stopped.

    Founder, 2026-09-02: "Report fetches/extracts/$ as outcomes." Everything
    here is measured, not planned — fetches and extract calls are counted as
    the loop makes them, tokens are what the provider itself reported, and the
    dollar figure prices those tokens from the committed table in
    docs/MODEL_ROUTING.md. When the model id is not in that table, or the
    provider reported no usage, the cost cell says "unknown" rather than
    showing a number nobody could stand behind.

    `sources reached` is deliberately printed as an outcome and not as a
    setting: it is what the budgets allowed, which is the whole point.
    """
    from worker.spend_report import format_spend

    o = report.outcomes or {}
    spend = format_spend(
        model_id=model_id,
        input_tokens=o.get("input_tokens", 0),
        output_tokens=o.get("output_tokens", 0),
    )
    return "\n".join([
        "OUTCOMES (measured, not planned):",
        f"  sources reached:   {o.get('sources_touched', 0)}"
        f"   (deferred to a later tick: {o.get('sources_deferred', 0)})",
        f"  fetches:           {o.get('fetches', 0)}"
        f"   (discovery probes: {o.get('discover_fetches', 0)})",
        f"  extract calls:     {o.get('extract_calls', 0)}"
        f"   (pages sent to the model — the only stage that calls Anthropic)",
        f"  tokens in/out:     {o.get('input_tokens', 0)} / {o.get('output_tokens', 0)}",
        f"  estimated cost:    {spend}",
        f"  elapsed:           {o.get('elapsed_seconds', 0)}s",
        f"  tick stopped on:   {o.get('stop_reason', 'exhausted')}",
        f"  unchanged (no extract): {report.counts.get('skipped_unchanged', 0)}",
    ])


def plan_tick(sources, states, event_refreshes=(), *, now=None):
    """The work one tick will attempt, most overdue first, deduped by page.

    Founder, 2026-09-02: a tick is not "K sources". This function decides WHAT
    is worth doing and in what order; worker/orchestrator.py decides how much
    of it fits inside the tick's real budgets. Three queues feed it:

      EVENT    a published event is approaching a rung of the proximity ladder
               (T-30d, T-14d, T-7d, T-3d, T-1d, day-of), so its DEFINING page
               is re-read. One item per page, however many events sit on it.
      REFRESH  a source whose door we know. One fetch, straight at it.
      DISCOVER a source whose door we do not. The start URL, then at most one
               probe of the events/calendar/shows page it advertises.

    EVENT items go FIRST, nearest rung first. They are the only work with a
    deadline: a show tonight that was cancelled is a user-visible error now,
    while a source taking its routine turn is not. That priority is bounded,
    not absolute — TickBudget caps event fetches at EVENT_FETCH_SHARE of the
    tick, so a night full of near events cannot freeze the rotation.

    SOURCE items follow, most overdue first, with round-robin (least-recently-
    attempted) as the tie-break between equally-overdue sources and source_id
    after that. Nothing here reads a source's category, type, city or name.

    DEDUPE: one page fetch covers all events on that page, and it also covers a
    source whose door is the same page. When an EVENT item and a source item
    would fetch the same URL this tick, the event item wins (it is the more
    urgent reason to look) and the source item is dropped for this tick only.

    Returns (items, deferred_count). Items are the source dicts the loop takes,
    each carrying `queue` and — for event items — the specific `door` to read.
    """
    from worker.crawl_state import (
        QUEUE_EVENT, SourceCrawlState, choose_primary_door, order_due,
    )
    from worker.sourcing.page_discovery import same_site

    by_id = {str(src.get("source_id")): src for src in sources}
    rotation_rank = {str(src.get("source_id")): i for i, src in enumerate(sources)}

    items = []
    claimed_urls = set()

    # 1. EVENT PROXIMITY first into the dedupe set, so a source item pointing
    #    at the same page yields to it rather than duplicating the fetch.
    for refresh in event_refreshes:
        src = by_id.get(str(refresh.source_id))
        if src is None:
            # The event's source is disabled or gone. Not an error and not a
            # silent drop: there is nothing to fetch it WITH, and the published
            # row is untouched either way (the loop never mutates one).
            logger.warning(
                "event-proximity refresh for %s skipped: its source is not in "
                "the enabled catalog this tick.", refresh.url)
            continue
        items.append({**src, "queue": QUEUE_EVENT, "door": refresh.url,
                      "queue_reason": refresh.reason,
                      "crawl_state": states.get(str(refresh.source_id))})
        claimed_urls.add((str(refresh.source_id), refresh.url))

    # 2. SOURCES that are due, on the same overdue scale.
    ordered_states = [
        states.get(str(src.get("source_id")))
        or SourceCrawlState(source_id=str(src.get("source_id")))
        for src in sources
    ]
    due_states = order_due(ordered_states, now=now, rotation_rank=rotation_rank)
    for state in due_states:
        src = by_id.get(state.source_id)
        if src is None:
            continue
        door = choose_primary_door(
            start_url=src["url"], best_url=state.best_url, same_site_fn=same_site)
        if (state.source_id, door) in claimed_urls:
            # Already being fetched this tick for a nearer reason: one page
            # fetch covers everything that page defines.
            continue
        items.append({**src, "queue": state.queue, "crawl_state": state})
        claimed_urls.add((state.source_id, door))

    # `event_refreshes` arrives nearest-rung-first and `due_states` arrives
    # most-overdue-first, so the concatenation is already in priority order —
    # re-sorting the two together would need one scale for two different kinds
    # of urgency, and inventing that scale is how a schedule starts lying.
    planned = items
    # Enabled sources with NO item in this tick's plan: inside their own crawl
    # interval, or backing off. Deferred, never dropped — they lead a later
    # tick. Counted from source ids, so a source that appears twice (an event
    # page AND its own turn) is not double-counted as present or absent.
    planned_ids = {str(item.get("source_id")) for item in planned}
    deferred = sum(1 for src in sources
                   if str(src.get("source_id")) not in planned_ids)
    return planned, deferred


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
    from worker.crawl_state import (
        load_crawl_states, load_event_refresh_rows, load_extraction_usage,
        plan_event_refreshes,
    )

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
            # Fair-crawl state for every enabled source, read on THIS cursor
            # so the wave is chosen from the same snapshot the rotation
            # ordering below sees. Derived from raw_fetch + event_candidate —
            # no new table, no new column (worker/crawl_state.py says why).
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
            crawl_states = load_crawl_states(cur)
            # Published events approaching a proximity rung, with the page
            # that defines them. Read on the SAME cursor/snapshot as the
            # source rows so the tick plan is internally consistent.
            event_rows = load_event_refresh_rows(cur)
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
            # The orchestrator reads best_url off this to pick the primary
            # door. Absent (a source with no history) simply means "start
            # URL", which is exactly what the loop did before fair crawl.
            "crawl_state": crawl_states.get(str(sid)),
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

    # THE TICK PLAN: what is worth doing, most overdue first, across all three
    # queues. How much of it actually happens is decided by the tick's real
    # budgets inside run_loop — wall clock, model spend, host politeness — not
    # by a source count picked in advance.
    total_enabled = len(sources)
    event_refreshes = plan_event_refreshes(event_rows)
    sources, deferred = plan_tick(sources, crawl_states, event_refreshes)
    logger.warning(
        "tick plan: %d item(s) across %d enabled source(s) — %d event-proximity "
        "page(s), %d not due this tick. The tick stops on wall clock, model "
        "budget, or the fetch cap, whichever comes first.",
        len(sources), total_enabled, len(event_refreshes), deferred,
    )
    if cap is not None:
        # The legacy per-run SOURCE ceiling, kept for exactly what the founder
        # called it: a spend/time safety cap, not the design. It is an outer
        # net above the tick budgets, and it truncates the TAIL of an
        # already-prioritised plan, so the most overdue work is never what it
        # cuts.
        sources = apply_source_ceiling(sources, cap)
    else:
        logger.warning(
            "NO outer source ceiling set (--max-sources / "
            "ONELIVE_MAX_SOURCES_PER_RUN) — the tick is bounded by its own "
            "wall-clock, model and fetch budgets alone.")
    if not sources:
        # Not a failure: every source is inside its own interval, so the
        # correct amount of work this wave is zero. The cron stays green and
        # the dead-man still pings — a run that correctly did nothing is not a
        # dead run. Loud, because a catalog small enough to lap itself is
        # worth seeing in the log.
        logger.warning(
            "nothing is due this tick (%d enabled source(s), all inside their "
            "crawl interval, and no published event near a proximity rung) — "
            "nothing to fetch; the next tick picks up whoever comes due first.",
            total_enabled,
        )
        return 0

    tick_budget = TickBudget.from_env()
    report = run_loop(ai=ai, sources=sources, sxsw_mode=False, dsn=dsn,
                      budget=tick_budget)
    # The tick's real AI spend, read back from what the provider itself
    # reported on the rows this tick wrote. Read AFTER the loop, and never
    # allowed to fail it: a cost report is telemetry, and losing it must not
    # lose a tick's actual work.
    try:
        tokens_in, tokens_out = load_extraction_usage(report.started)
        tick_budget.record_tokens(input_tokens=tokens_in, output_tokens=tokens_out)
        report.counts["input_tokens"] = tokens_in
        report.counts["output_tokens"] = tokens_out
        report.outcomes = tick_budget.outcomes()
    except Exception as exc:  # noqa: BLE001 — telemetry, never the work
        logger.warning(
            "could not read this tick's token usage (%s) — the outcomes line "
            "will say the cost is unknown rather than guess it.", exc)
    print("RunReport:")
    print(f"  run_id:   {report.run_id}")
    print(f"  counts:   {report.counts}")
    for r in report.results:
        print(f"  - {r.source_name}: stage={r.stage_reached} decision={r.decision} detail={r.detail}")
    print()
    print(render_run_table(report))
    print()
    print(render_outcomes(report, model_id=_provider_model_id(ai)))
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
        help="Outer SAFETY cap: attempt at most N planned items this tick "
             "(positive integer; falls back to ONELIVE_MAX_SOURCES_PER_RUN; "
             "unset = no outer cap, logged loudly). This is a spend/time "
             "safety net, NOT the schedule — the tick really stops on its "
             "wall-clock, model-spend and fetch budgets "
             "(worker/crawl_state.py), and how many sources it reached is "
             "reported afterwards as an outcome.",
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
