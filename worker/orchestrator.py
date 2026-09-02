"""The Loop — orchestrator-as-Harness.

This module IS the Sensors -> Harness -> Loop structure, not a plain pipeline
runner decorated with trust features later. For each source it drives:

    fetch -> sensors.assess_input -> extract_candidates -> trust_gate3.evaluate_gate
        -> (PASS -> leave ready for ops promote | HOLD/ESCALATE -> needs_review)

FAIR CRAWL (2026-09-02, founder-directed: "many sources per wave, few pages
each"). The earlier multi-page follow let one source walk up to 15 pages and
spent the run's page budget in source order, so two link-heavy calendars
consumed the whole run and every source behind them got nothing — a Coverage
Law defect in scheduler form. Each source now costs AT MOST TWO fetches per
wave (_run_one_source):

  1. its PRIMARY DOOR — `best_url`, the page that produced the most candidates
     in the last 30 days (worker.crawl_state), else its registered start URL;
  2. at most ONE more — the single top-ranked events/calendar/shows page the
     start page advertises (class B only, worker.sourcing.page_discovery's own
     evidence ranking), or a fallback to the start URL when the best door has
     moved.

An unchanged door ends the source for the wave: the previous ETag/Last-Modified
go out as conditional-GET headers so the server can answer 304, and a server
with no validators still gets caught by comparing the body's sha256 against the
last successful raw_fetch row. Either way the extraction — the part that costs
money (R-043) — is not run.

Three rules are load-bearing and are enforced in ONE place, _knock_door:
on-origin only (checked before the fetch by discovery, and again on the FINAL
url after redirects); a wall (401/402/403/407 or a sign-in redirect) demotes
the source to class D and ends it — we knock once; 429/503 is a BACK-OFF, not
a wall (worker.crawl_state.BACKOFF_STATUSES — the founder's rule, and the one
place it differs from source_class.WALL_STATUSES); a 404 is a miss, not a wall.
Following a link buys reach, never trust: every door faces the same sensor, the
same certified extractor and the same gate, and the loop still never promotes.

The orchestrator NEVER promotes. Promotion is the publish step and is the one
place a human/ops decision is mandatory: only an authenticated ops action
(api/ops_candidates.py -> worker.promote.promote_candidate) may publish a
candidate to the canonical `event` table. This module classifies each candidate
and stops at the gate — a PASS is left in the store for ops to promote, it is
never auto-published. This is the code-level enforcement of the foundational
"AI never auto-promotes" trust invariant (docs/WORLD_CLASS.md §5), not a comment.

Every step is written to the deterministic-replay log (worker.replay_log) so
any decision this loop makes is auditable and re-runnable later.

Failure semantics (project precedent, see worker/resolve_entities.py and
docs/OPERATING_RULES.md rule 3.1): configuration/structural errors (e.g. an
unwritable replay log directory) fail LOUD and abort the whole run — these
mean the harness itself is broken and continuing would produce a run that
looks fine but is not. Per-source *transient* errors (a flaky fetch, a
provider hiccup) are caught, logged as 'error' for that source alone, and the
loop CONTINUES: one bad source must never take down the run, and the failure
is always visible in the RunReport/replay log — never silently absorbed as
"nothing to do".

JS-shell render fallback (worker/fetch/render_fetch.py): the fetch step runs
`fetch_with_render` — plain fetch first, always; when the input-quality sensor
flags the plain result as a boilerplate-only JS shell ("enable javascript"
chrome with no content — the signature of Squarespace/Wix-style calendars),
the page is re-fetched once through headless Chromium and the RENDERED HTML
feeds the sensor/extract path instead of the shell. Two bounds keep this safe
and cheap:
- Budget: renders per run are capped by ONELIVE_MAX_RENDERS_PER_RUN
  (default 5; 0 disables rendering entirely). The value is validated
  fail-closed at run start: unset/empty uses the default, anything else must
  parse as a base-10 integer >= 0 or run_loop aborts loudly before touching
  any source — a typo must never silently mean "uncapped".
- Availability fail-open, trust fail-closed: a render failure (missing
  playwright package or browser binary, timeout, budget exhausted) NEVER
  kills the source or the run and NEVER fabricates content — it is logged
  loudly, recorded on the replay fetch entry (render_error), and the
  un-rendered plain result proceeds exactly as it did before the fallback
  existed. Rendered HTML earns no trust shortcut: it re-enters the same
  sensor gate as any other fetched text, and everything downstream (extract,
  gate3, never-promote) is unchanged.

Ratchet note (dev-time only, per red-team review): the iterate-on-green /
revert-on-regression ratchet governs how WE build and evolve this file across
commits. It must never leak into the runtime behaviour of the loop itself:
this module does not self-modify, and it must never auto-approve a promotion
to "keep the run going". Escalating an ambiguous candidate to a human is
the correct, intended outcome here — not a bug to route around.

This module deliberately does NOT import worker.promote: it can never publish,
so it cannot be the path an AI-extracted candidate reaches the canonical event
table through. Promotion lives behind the authenticated ops endpoint only.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ai.provider import AIProvider
from worker.ai_extract import extract_candidates
from worker.candidate_store import (
    list_candidate_source_classes,
    load_candidate_gate_signals,
    stamp_gate_verdict,
)
from worker.crawl_state import (
    BACKOFF_STATUSES,
    QUEUE_DISCOVER,
    QUEUE_EVENT,
    QUEUE_REFRESH,
    UNVERIFIED,
    SourceCrawlState,
    TickBudget,
    choose_primary_door,
    classify_recheck,
    host_of,
    load_door_fingerprint,
    resolve_int_env,
)
from worker.fetch.http_fetch import fetch_url
from worker.fetch.render_fetch import RenderError, fetch_with_render, render_html
from worker.replay_log import ReplayRecord, canonical_digest, log_step, new_run_id
from worker.sensors import assess_input
from worker.sourcing.catalog_posture import resolve_entry
from worker.sourcing.page_discovery import (
    DEFAULT_MAX_PAGES,
    discover_event_pages,
    same_site,
)
from worker.sourcing.source_class import (
    CLASS_B_PUBLIC_HTML,
    classify_entry,
    demote_on_response,
    wall_signals_from_exception,
)
from worker.trust_gate3 import GateDecision, evaluate_gate

logger = logging.getLogger(__name__)

# Renders are expensive (a full headless-Chromium process per page), so each
# run carries a hard budget. Env knob + default documented in the module
# docstring above; validation is fail-closed in _resolve_render_cap().
RENDER_CAP_ENV = "ONELIVE_MAX_RENDERS_PER_RUN"
DEFAULT_MAX_RENDERS_PER_RUN = 5

# Follow-pages budgets (see _resolve_follow_caps).
#
# FAIR CRAWL (founder, 2026-09-02: "many sources per wave, few pages each").
# The per-SOURCE ceiling used to be the walker's own cap of 15, and the run
# budget was spent in source order — so the first two link-heavy calendars
# consumed all 30 pages and every source behind them got zero. That is a
# Coverage Law defect in scheduler form, and no amount of budget fixes it:
# the ceiling has to bind per SOURCE, not per run. It is now ONE door.
#
# The knob is a NEW name, not the old one re-pointed: a stale
# ONELIVE_MAX_FOLLOW_PAGES_PER_SOURCE=15 left in some environment would
# silently restore the unfair walk, and a removed knob cannot do that. The run
# ceiling stays exactly what it was — the FinOps bound — and must be >= the
# wave size K, or the tail of a wave loses its door to a budget the head
# already spent.
FOLLOW_RUN_CAP_ENV = "ONELIVE_MAX_FOLLOW_PAGES_PER_RUN"
DOORS_PER_SOURCE_ENV = "ONELIVE_DOORS_PER_SOURCE"
DEFAULT_MAX_FOLLOW_PAGES_PER_RUN = 30
#: One door per source, per run. The start page is not counted here: a source
#: costs at most TWO fetches a wave (its primary door, plus one discovered
#: events/calendar/shows page, or one fallback to its registered start URL).
#: DEFAULT_MAX_PAGES (the walker's own 15) remains the discovery module's
#: ceiling for callers that genuinely want a deep walk — tools/class_b_multipage
#: .py — and is deliberately NOT what the armed loop uses.
DEFAULT_DOORS_PER_SOURCE = 1

# Greppable, structured marker logged when a source answers an unauthenticated
# read with a wall (401/402/403/407/429 or a sign-in redirect) and is therefore
# class D from that moment. Ops greps for it to build the claim queue: the
# scheduled loop cannot commit to docs/CLASS_D_CLAIM_QUEUE.md, so the log line
# and the replay entry ARE the routing (R-085). Do NOT rename without updating
# the runbook that matches on it.
CLASS_D_WALL_MARKER = "INGEST_WALL_OBSERVED_CLASS_D"

# Keys tracked in RunReport.counts. Declared up front so every run reports the
# full shape even when a count is zero (never omit a key because it's 0 —
# that would make "nothing happened" indistinguishable from "not tracked").
_COUNT_KEYS = (
    "fetched",
    "not_modified",
    "extracted",
    "passed",
    "escalated",
    "held",
    "sensor_rejected",
    "errors",
    # Follow-pages (class B multi-page walk). Counted separately from the
    # start-page buckets above so "what the homepage produced" and "what the
    # click produced" can never be read as one number.
    "pages_followed",
    "pages_extracted",
    "pages_missed",
    "pages_walled",
    "candidates",
    # Fair crawl. `skipped_unchanged` counts doors whose body the server or
    # the fingerprint proved identical to the last read — the whole point of
    # the pass: an unchanged page costs one conditional GET and ZERO AI calls.
    # `blocked` counts sources a wall (401/403) or a back-off status
    # (429/503) stopped before any extraction, so "we chose not to read it"
    # can never be read as "this venue has no events".
    "skipped_unchanged",
    "blocked",
    # Deferred: a source the tick did not reach because ITS host had had
    # enough, or discovery had spent its share. Not dropped — it leads a later
    # tick. Counted so "we did not get to it" can never read as "it had
    # nothing".
    "deferred",
    # The measured outcomes (founder: "report fetches/extracts/$"). `fetches`
    # is every HTTP request the loop made; `extract_calls` is every page sent
    # to the model, which — extraction being the only stage that may call
    # Anthropic — is the whole of the AI spend. Tokens are what the provider
    # itself reported.
    "fetches",
    "extract_calls",
    "input_tokens",
    "output_tokens",
)

# _run_one_source's "not_modified" outcome intentionally does NOT also set
# "fetched" (fetch_url reported nothing new arrived, so no bytes were newly
# fetched this run) — kept as its own explicit bucket here to document that
# choice as deliberate rather than an oversight.


@dataclass
class SourceResult:
    """One source's outcome, plus the columns the founder's run table prints.

    The report fields default so every existing construction site (including
    run_loop's error path) stays valid, and so a row always renders — an empty
    cell in the table means "this source never got that far", never "the
    number was not tracked".
    """

    source_id: Optional[str]
    source_name: str
    stage_reached: str
    decision: str
    detail: str
    urls_fetched: List[str] = field(default_factory=list)
    changed: Optional[bool] = None
    queue: str = ""
    #: The fail-closed verification verdict for this check (worker.crawl_state:
    #: verified_present / verified_absent / unverified). UNVERIFIED is the
    #: default because a result that never reached a check has, by definition,
    #: confirmed nothing — the default must never be the permissive one.
    verdict: str = UNVERIFIED
    verdict_reason: str = ""
    candidates: int = 0
    skipped_unchanged: int = 0
    blocked: str = ""


@dataclass
class RunReport:
    """What one tick did. `outcomes` is TickBudget.outcomes(): the measured
    fetches / extract calls / tokens / elapsed seconds, and the honest reason
    the tick ended (`stop_reason`) — "exhausted" when nothing due was left,
    otherwise the budget that bound. Sources reached is an outcome here, never
    an input."""

    run_id: str
    started: str
    finished: str
    results: List[SourceResult] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=lambda: {k: 0 for k in _COUNT_KEYS})
    outcomes: Dict[str, Any] = field(default_factory=dict)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_fetched_text(fetch_result: Dict[str, Any]) -> str:
    """Read the bytes fetch_url wrote to storage_ref and decode as text.

    fetch_url is the real http adapter (worker/fetch/http_fetch.py): on
    status 'ok' it always returns a storage_ref path to the bytes it wrote.
    Decoding is best-effort utf-8 with replacement so a stray non-utf8 byte
    degrades to a sensor-detectable "looks binary" signal rather than raising
    and killing the source (that's what per-source error isolation is for
    upstream, not this narrow decode step).
    """
    storage_ref = fetch_result["storage_ref"]
    with open(storage_ref, "rb") as f:
        raw = f.read()
    return raw.decode("utf-8", errors="replace")


def _resolve_budget(env_name: str, default: int, noun: str) -> int:
    """This module's budget knobs, parsed by the ONE fail-closed parser
    (worker.crawl_state.resolve_int_env) that every budget in the pipeline
    uses. Kept as a named local so the call sites below read as they always
    did, and so there is still exactly one place to look for "how a budget is
    parsed" — which must never become two, because the second copy always
    drifts in the direction that costs money."""
    return resolve_int_env(env_name, default, noun)


def _resolve_render_cap() -> int:
    """The per-run JS-shell render budget (see module docstring). 0 disables
    rendering entirely."""
    return _resolve_budget(RENDER_CAP_ENV, DEFAULT_MAX_RENDERS_PER_RUN, "render")


def _resolve_follow_caps() -> Dict[str, int]:
    """The follow-pages budgets: DOORS per source and pages per RUN, both
    fail-closed.

    Two ceilings, because they bound two different risks:

    * PER SOURCE (default 1 — the fair-crawl door) is the FAIRNESS bound. It
      is what stops one link-heavy venue from being walked while the rest of
      the wave gets nothing. This is the number the founder's rule turns into
      code: many sources per wave, few pages each.
    * PER RUN is the FinOps bound. Extraction cost is one model call per event
      block per page (R-043), so pages — not sources — are what a run spends.

    Why the fairness bound is per SOURCE and not a smarter share of the run
    budget: a share still has to be spent in some order, and whatever goes
    first wins. A hard per-source door needs no ordering to be fair, and it is
    one number a human can check against a run table.

    The run budget must be at least `wave size x doors` or the tail of a wave
    loses its door to a budget the head already spent — the cron sets both,
    and worker/run_once.py orders sources least-recently-attempted first, so
    a source that misses out leads the next wave rather than being dropped.

    0 on either knob disables following entirely (a ceiling of 0 means no
    walk, never "uncapped" — the project-wide budget rule).
    """
    return {
        "run_cap": _resolve_budget(
            FOLLOW_RUN_CAP_ENV, DEFAULT_MAX_FOLLOW_PAGES_PER_RUN, "follow-page"),
        "source_cap": _resolve_budget(
            DOORS_PER_SOURCE_ENV, DEFAULT_DOORS_PER_SOURCE,
            "per-source door"),
    }


class _RenderBudgetStop(RenderError):
    """Render refused by the per-run budget (cap reached, or cap=0 disabled).

    A RenderError subclass so the fetch step's single fail-open path handles
    it, but distinguishable so the log line says "budget" (expected, by
    design) rather than "failure" (a browser/timeout problem worth alerting
    on).
    """


def _make_budgeted_render(render_state: Dict[str, int]):
    """Wrap render_html with the per-run budget. `render_state` is the run's
    mutable {"cap": N, "remaining": N} counter — decremented ONLY when a real
    render is attempted, so refused renders never consume budget.
    """

    def _render(**kwargs: Any) -> str:
        if render_state["cap"] == 0:
            raise _RenderBudgetStop(
                f"JS-shell rendering is disabled ({RENDER_CAP_ENV}=0); "
                "proceeding with the un-rendered plain fetch"
            )
        if render_state["remaining"] <= 0:
            raise _RenderBudgetStop(
                f"render budget exhausted ({RENDER_CAP_ENV}={render_state['cap']} "
                "renders this run); proceeding with the un-rendered plain fetch"
            )
        render_state["remaining"] -= 1
        # Module-global lookup on purpose: tests monkeypatch
        # orchestrator.render_html exactly like orchestrator.fetch_url.
        return render_html(**kwargs)

    return _render


def _fetch_with_render_fallback(
    *,
    source_id: Optional[str],
    url: str,
    render_state: Dict[str, int],
    etag: Optional[str] = None,
    last_modified: Optional[str] = None,
) -> Dict[str, Any]:
    """The orchestrator's fetch step: plain fetch + budgeted JS-shell render.

    Delegates to worker.fetch.render_fetch.fetch_with_render (which is plain-
    first and only renders on the sensor's boilerplate-shell trigger), with
    one policy added HERE, at the loop level: render problems are fail-open.
    render_fetch's own contract stays loud (RenderError raises), but a
    scheduled ingestion run must not lose a source it already fetched just
    because the OPTIONAL enhancement path (extra package + browser binary)
    is absent or broke — so any RenderError is logged, stamped onto the
    returned result as `render_error` (the replay fetch entry records it),
    and the un-rendered plain result proceeds exactly as it did before the
    fallback existed. Nothing is fabricated: the fallback text is the real
    fetched bytes, and the sensor still judges them.

    All plain-fetch audit behavior (raw_fetch rows, attempt rows, replay
    semantics) is untouched — fetch_url runs unmodified either way, and
    plain-fetch exceptions propagate to run_loop's per-source isolation
    exactly as before.
    """
    plain_capture: Dict[str, Any] = {}

    def _remember_plain_text(fetch_result: Dict[str, Any]) -> str:
        # Capture the decoded plain text as fetch_with_render reads it, so a
        # later RenderError can fall back without re-fetching (a second fetch
        # would burn time and write a duplicate raw_fetch audit row).
        text = _read_fetched_text(fetch_result)
        plain_capture["result"] = fetch_result
        plain_capture["text"] = text
        return text

    try:
        return fetch_with_render(
            source_id=source_id,
            url=url,
            # The previous read's cache validators, so a well-behaved server
            # can answer 304 and send no body at all — the cheapest possible
            # "nothing changed here". Pass-through only; the decision about
            # what an unchanged page MEANS is made by _knock_door.
            etag=etag,
            last_modified=last_modified,
            # Late-bound module globals on purpose: tests monkeypatch
            # orchestrator.fetch_url / orchestrator.render_html.
            _fetch_fn=fetch_url,
            _render_fn=_make_budgeted_render(render_state),
            _read_text=_remember_plain_text,
        )
    except RenderError as exc:
        if "result" not in plain_capture:
            # Structurally unreachable today (fetch_with_render only renders
            # after reading the plain text) — if render_fetch's flow ever
            # changes, stay loud rather than invent an empty result.
            raise
        if isinstance(exc, _RenderBudgetStop):
            logger.warning("render skipped for %s: %s", url, exc)
        else:
            logger.error(
                "render FAILED for %s — falling back to the un-rendered plain "
                "fetch (source may be sensor-rejected as a JS shell): %s",
                url, exc,
            )
        return {
            **plain_capture["result"],
            "text": plain_capture["text"],
            "rendered": False,
            "render_error": f"{type(exc).__name__}: {exc}",
        }


@dataclass
class PageOutcome:
    """What ONE fetched page produced downstream of the fetch step.

    Shared by the start page and every followed page, because they are the
    same page as far as sensors, extraction and the trust gate are concerned —
    the only difference is which URL the loop was pointed at. `candidates` is
    the number of candidate rows the extract path actually wrote for the page
    (an N-event calendar writes N), so "pages followed" and "candidates" can
    never be conflated in a report.
    """

    stage: str
    decision: str
    detail: str
    candidates: int = 0
    model_calls: int = 0


def _process_fetched_page(
    *,
    run_id: str,
    ai: AIProvider,
    source_id: Optional[str],
    source_name: str,
    page_url: str,
    source_class: str,
    sxsw_mode: bool,
    text: str,
    content_type: Optional[str],
    budget: TickBudget,
) -> PageOutcome:
    """sensor -> extract -> gate3 -> stamp, for one already-fetched page.

    This is the single implementation of everything the loop does downstream
    of a fetch. The start page and every followed page run through it
    unchanged, so a class B source's calendar page is judged by exactly the
    same sensor, the same certified extractor and the same trust gate as its
    homepage — following a link buys reach, never a trust shortcut, and there
    is no second, laxer path for the pages the walk discovered.

    Exceptions propagate: run_loop's per-source isolation is still the ONE
    place that decides isolate-vs-abort (for a followed page the caller
    narrows that to the page, and says so there).
    """
    reading = assess_input(text=text, content_type=content_type)
    log_step(ReplayRecord(
        run_id=run_id, ts=_now_iso(), source_id=str(source_id), source_name=source_name,
        stage="sensor", inputs_digest=canonical_digest({"content_type": content_type, "length": len(text)}),
        outputs_digest=canonical_digest({"ok": reading.ok, "signals": reading.signals}),
        decision="sensor_rejected" if not reading.ok else "sensor_passed", detail=reading.reason,
    ))
    if not reading.ok:
        return PageOutcome("sensor", "sensor_rejected", reading.reason)

    if not budget.may_extract():
        # The model budget is the tick's real spend limit, so it is checked
        # HERE — immediately before the only stage that may call Anthropic —
        # and not merely between sources. The page was fetched and is fine; it
        # is simply not extracted this tick, and the source's next_due_at is
        # unchanged, so it comes back at the front of the next one.
        log_step(ReplayRecord(
            run_id=run_id, ts=_now_iso(), source_id=str(source_id), source_name=source_name,
            stage="extract", inputs_digest=canonical_digest({"length": len(text)}),
            outputs_digest=canonical_digest({"skipped": "model_budget"}),
            decision="deferred",
            detail="tick model budget spent — page fetched, extraction left for the next tick",
        ))
        return PageOutcome(
            "extract", "deferred",
            "tick model budget spent — extraction left for the next tick")

    # extract_candidates is the fan-out entrypoint: an N-event calendar page
    # produces N candidates. The FIRST id carries this page's gate3/replay
    # contract exactly as before (extract_candidate, the single-id wrapper this
    # call replaces, returned that same id); the rest are stamped by the
    # orchestrator's backlog sweep. Counting them here is what makes the run
    # report able to say how many rows a followed page was worth.
    outcome = extract_candidates(
        ai=ai,
        text=text,
        source_class=source_class,
        source_name=source_name,
        source_url=page_url,
        sxsw_mode=sxsw_mode,
        source_id=source_id,
    )
    # The AI spend of this tick, counted at the ONE place the pipeline calls a
    # model. CALLS only: that is what the model budget bounds, and it is
    # knowable in flight. The token totals are read back afterwards from what
    # the provider itself reported (worker/crawl_state.load_extraction_usage),
    # which keeps the cost report out of the extraction surface entirely.
    budget.record_extract()
    candidate_id = outcome.candidate_ids[0]
    n_candidates = len(outcome.candidate_ids)
    log_step(ReplayRecord(
        run_id=run_id, ts=_now_iso(), source_id=str(source_id), source_name=source_name,
        stage="extract", inputs_digest=canonical_digest({"length": len(text)}),
        outputs_digest=canonical_digest({"candidate_id": candidate_id}),
        decision="extracted", detail=f"candidate_id={candidate_id}",
    ))

    source_classes = list_candidate_source_classes(candidate_id)
    # Load the REAL stored extraction + evidence signals for THIS candidate (by
    # id, from the DB) so gate3 sees actual provenance / private-RSVP / start-time
    # facts recorded by ai_extract — never a per-source test shortcut.
    extracted, evidence_signals = load_candidate_gate_signals(candidate_id)
    verdict = evaluate_gate(
        source_classes=source_classes,
        sxsw_mode=sxsw_mode,
        extracted=extracted,
        evidence_signals=evidence_signals,
    )
    log_step(ReplayRecord(
        run_id=run_id, ts=_now_iso(), source_id=str(source_id), source_name=source_name,
        stage="gate3", inputs_digest=canonical_digest({"source_classes": source_classes, "extracted": extracted}),
        outputs_digest=canonical_digest({"decision": verdict.decision.value}),
        decision=verdict.decision.value, detail=verdict.reason,
    ))

    # Persist the verdict onto the candidate ROW (2026-08-05): before this,
    # the verdict lived only in the replay log — every candidate stayed at its
    # insert status 'needs_review', the autopromote pass selected an
    # eternally-empty 'ready_to_promote' population, and the only stamping
    # path was the per-item human ops action (the REJECTED approval loop in
    # disguise). Stamping classifies; it never publishes — the publish paths
    # re-gate independently. ESCALATE keeps 'needs_review' (the human queue)
    # with the reason recorded so the backlog sweep can tell "escalated by the
    # gate" from "never examined".
    if verdict.decision is GateDecision.ESCALATE:
        stamped = stamp_gate_verdict(
            candidate_id,
            status="needs_review",
            gate_reason=verdict.reason,
            required_next="human review — escalated by trust gate",
            expected_status="needs_review",
        )
    else:
        stamped = stamp_gate_verdict(
            candidate_id,
            status=verdict.base.status,
            gate_reason=verdict.base.reason,
            required_next=verdict.base.required_next,
            expected_status="needs_review",
        )
    if not stamped:
        # Compare-and-swap missed: something (ops action, dispute) moved this
        # row off 'needs_review' between creation and gate3 — the newer trust
        # state WINS and this run's verdict is recorded in the replay log
        # only. Loud, never silent, never an overwrite.
        logger.warning(
            "gate3 verdict for candidate %s NOT stamped — row left "
            "'needs_review' during the run; newer adjudicated state kept",
            candidate_id,
        )

    if verdict.decision is GateDecision.HOLD:
        return PageOutcome("gate3", "held", verdict.reason, n_candidates)

    if verdict.decision is GateDecision.ESCALATE:
        return PageOutcome("gate3", "escalated", verdict.reason, n_candidates)

    # PASS — but the orchestrator NEVER promotes. Promotion is the publish step
    # and must be an explicit, authenticated ops action (api/ops_candidates.py).
    # We leave the candidate in the store for a human/ops promote decision and
    # record the PASS in the replay log. There is deliberately no code path from
    # here to promote_candidate: "AI never auto-promotes" is enforced by the
    # absence of that call, not by a flag a future caller could flip.
    log_step(ReplayRecord(
        run_id=run_id, ts=_now_iso(), source_id=str(source_id), source_name=source_name,
        stage="gate3", inputs_digest=canonical_digest({"candidate_id": candidate_id}),
        outputs_digest=canonical_digest({"decision": "ready_to_promote"}),
        decision="ready_to_promote",
        detail="PASS (trust gate); left for authenticated ops promote — never auto-promoted",
    ))
    return PageOutcome(
        "gate3", "ready_to_promote",
        "PASS (trust gate); awaiting authenticated ops promote", n_candidates,
    )


def _class_verdict_for(source: Dict[str, Any]) -> Any:
    """The Coverage Law class letter for a DB source row, from the catalog's
    own declared access posture.

    The posture is resolved DB-first by worker.sourcing.catalog_posture: the
    row's own `config` when it declares one (a venue's claim must outrank a
    file), else the committed catalog's entry for that source. Measured live
    2026-09-02, 264 of 266 enabled rows declare nothing at all, so without the
    catalog fallback this walk would never fire on any real source. Either
    way the class is READ from a declaration — never inferred from the URL,
    never guessed — and a source neither the row nor the catalog speaks for
    classifies D on classify_entry's own unrecognized-posture rule, i.e. NOT
    followed. Fail-closed: the walk is an extra read of pages a source did not
    register, so it happens only where a declaration says the door is open.

    IMPORTANT: this decides FOLLOWING only. It must never gate the start-page
    fetch — every enabled source is still fetched exactly as before, so
    nothing here can shrink the catalog (Coverage Law: views are picky, the
    catalog is greedy).
    """
    return classify_entry(resolve_entry(
        name=source.get("name"), url=source.get("url"),
        config=source.get("config")))


#: Human-readable reasons a door was not knocked on. Each names the limit AND
#: what happens next, because "deferred" alone reads like a failure and it is
#: not one: the source leads a later tick.
_DEFER_REASONS = {
    "wall_clock": "tick wall-clock budget spent — deferred to the next tick",
    "fetch_budget": "tick fetch budget spent — deferred to the next tick",
    "model_budget": "tick model budget spent — deferred to the next tick",
    "host_politeness": (
        "this host has had its share of fetches this tick — deferred, so one "
        "busy host cannot be hammered and cannot stop everybody else"),
    "discover_share": (
        "discovery has spent its share of this tick's fetches — deferred, so "
        "an import backlog cannot starve the refresh of the live catalog"),
}


def _defer_reason(key: str) -> str:
    return _DEFER_REASONS.get(key, f"deferred ({key})")


@dataclass
class DoorOutcome:
    """What ONE knock on ONE url produced, before any policy is applied.

    A "door" is a URL we are willing to spend a fetch on: a source's best
    known door, its registered start URL, or the single events/calendar page
    its start page advertises. Every knock ends in exactly one `kind`, and the
    caller — not this function — decides what that means for the source:

      changed   the body is new; `text` is ready for sensor -> extract -> gate.
      unchanged the server said 304, or the body hashes to what we already
                read. Nothing to extract; the AI call is SAVED, not skipped
                by guesswork.
      wall      401/402/403/407 or a sign-in redirect: class D, we knock once.
      backoff   429/503: "slow down", not "you are not invited" (see
                crawl_state.BACKOFF_STATUSES for why these two differ).
      offsite   a 200 that arrived from another site; a different source.
      missed    404, 5xx, timeout, DNS — a broken page, not a closed door.
                `error` carries the original exception so a caller that has
                no fallback can re-raise it unchanged.
      deferred  a tick budget or host politeness said not now. NOT a failure
                and not a fact about the source: it leads a later tick.
    """

    url: str
    kind: str
    detail: str = ""
    text: str = ""
    content_type: Optional[str] = None
    final_url: str = ""
    verdict: Any = None
    error: Optional[BaseException] = None
    #: The HTTP status the response carried, when there was one. Used ONLY to
    #: tell a CLEAR 404 (the page is gone — confirmable) from every other
    #: failure (which confirms nothing). Never used to decide trust.
    http_status: Optional[int] = None


def _wall_observed(before: Any, after: Any) -> bool:
    """Did THIS RESPONSE reveal a wall — as opposed to the catalog already
    having declared the source closed?

    demote_on_response's documented contract is "returns `verdict` unchanged
    when nothing wall-like was seen", so a changed object IS the observation.
    Reading `after.is_closed_door` instead would be a coverage bug with teeth:
    264 of 266 enabled rows declare no access posture at all and therefore
    classify D before any fetch happens, so that test would refuse to read
    almost the entire catalog on the strength of a missing config field.
    Following is gated on the declared class (see _class_verdict_for); FETCHING
    never is.
    """
    return after is not before


def _knock_door(
    *,
    run_id: str,
    source_id: Optional[str],
    source_name: str,
    url: str,
    start_url: str,
    verdict: Any,
    render_state: Dict[str, int],
    follow: bool,
    budget: TickBudget,
    queue: str,
) -> DoorOutcome:
    """Fetch ONE url and classify the answer. The single knock in the loop.

    Every fetch the ingest path makes goes through here — start page, best
    door, followed page alike — so "what counts as a wall", "what counts as
    unchanged" and "did we land where we aimed" have exactly one definition
    each. Before this, the start page had no wall classification at all (a 403
    surfaced as a generic per-source error) and no change detection (every run
    re-extracted an identical page).

    Two facts make the unchanged path real, and they are complementary:
      * CONDITIONAL GET — the previous ETag/Last-Modified go out as
        If-None-Match / If-Modified-Since, so a well-behaved server answers
        304 and sends no body at all.
      * BODY FINGERPRINT — a server with no validators still sends bytes, and
        those bytes hash to the same sha256 the last successful raw_fetch row
        stored. Comparing them costs nothing and saves the extraction, which
        is where the money is (R-043: one model call per event block).

    The fingerprint read is fail-OPEN on availability and closed on trust: if
    the lookup itself errors, we treat the page as changed and extract it. A
    lost optimisation costs one extraction; a lost page costs a venue's whole
    calendar, and Coverage Law is explicit about which of those is the defect.
    """
    stage_fetch = "follow_fetch" if follow else "fetch"

    # THE BUDGET GATE, before any work. Every HTTP request the loop makes goes
    # through this one place, so the tick's stop conditions cannot be dodged by
    # a code path that forgot to ask — and the refusal reason is returned, not
    # swallowed, so the report can say which limit deferred which source.
    refusal = budget.may_fetch(host_of(url), queue=queue)
    if refusal is not None:
        return DoorOutcome(url=url, kind="deferred", detail=_defer_reason(refusal))
    budget.record_fetch(host_of(url), queue=queue)

    fingerprint = None
    try:
        fingerprint = load_door_fingerprint(source_id, url)
    except Exception as exc:  # noqa: BLE001 — an optimisation must never lose a page
        logger.warning(
            "fingerprint lookup failed for %s (%s) — treating the page as "
            "changed and extracting it; coverage beats the saved call.",
            url, exc,
        )

    try:
        fetch_result = _fetch_with_render_fallback(
            source_id=source_id, url=url, render_state=render_state,
            etag=fingerprint.etag if fingerprint else None,
            last_modified=fingerprint.last_modified if fingerprint else None,
        )
    except Exception as exc:  # noqa: BLE001 — classified here, never swallowed
        status, exc_final_url = wall_signals_from_exception(exc)
        if status in BACKOFF_STATUSES:
            # "Slow down" is not "you are not invited". The source keeps its
            # declared class; worker/crawl_state.py's fail-streak backoff is
            # what makes the next knock later instead of sooner.
            detail = f"HTTP {status} — backing off, class unchanged"
            log_step(ReplayRecord(
                run_id=run_id, ts=_now_iso(), source_id=str(source_id),
                source_name=source_name, stage=stage_fetch,
                inputs_digest=canonical_digest({"url": url}),
                outputs_digest=canonical_digest({"status": status}),
                decision="backoff", detail=detail,
            ))
            return DoorOutcome(url=url, kind="backoff", detail=detail, error=exc)
        walled = demote_on_response(
            verdict, status=status, final_url=exc_final_url, error=str(exc))
        if _wall_observed(verdict, walled):
            logger.warning(
                "%s source=%s url=%s reason=%s",
                CLASS_D_WALL_MARKER, source_name, url, walled.reason,
            )
            log_step(ReplayRecord(
                run_id=run_id, ts=_now_iso(), source_id=str(source_id),
                source_name=source_name,
                stage="follow_wall" if follow else "wall",
                inputs_digest=canonical_digest({"url": url}),
                outputs_digest=canonical_digest({"source_class": walled.source_class}),
                decision="class_d", detail=walled.reason,
            ))
            return DoorOutcome(url=url, kind="wall", detail=walled.reason,
                               verdict=walled, error=exc)
        log_step(ReplayRecord(
            run_id=run_id, ts=_now_iso(), source_id=str(source_id),
            source_name=source_name,
            stage="follow_fetch" if follow else "fetch",
            inputs_digest=canonical_digest({"url": url}),
            outputs_digest=canonical_digest({"error": str(exc)}),
            decision="missed", detail=f"{type(exc).__name__}: {exc}",
        ))
        return DoorOutcome(url=url, kind="missed",
                           detail=f"{type(exc).__name__}: {exc}", error=exc,
                           http_status=status)

    if not follow:
        # The start-page replay entry, with its original shape preserved (the
        # render fields are an extension of the same record, not a new one).
        fetch_outputs: Dict[str, Any] = {
            "status": fetch_result.get("status"),
            "rendered": bool(fetch_result.get("rendered")),
        }
        if fetch_result.get("rendered"):
            fetch_outputs["plain_shell_reason"] = fetch_result.get("plain_shell_reason")
        if fetch_result.get("render_error"):
            fetch_outputs["render_error"] = fetch_result.get("render_error")
        fetch_detail = str(fetch_result.get("status"))
        if fetch_result.get("rendered"):
            fetch_detail += (
                " (js-shell rendered via headless browser; plain fetch was: "
                f"{fetch_result.get('plain_shell_reason')})"
            )
        elif fetch_result.get("render_error"):
            fetch_detail += (
                " (render fallback unavailable, proceeding un-rendered: "
                f"{fetch_result.get('render_error')})"
            )
        log_step(ReplayRecord(
            run_id=run_id, ts=_now_iso(), source_id=str(source_id),
            source_name=source_name, stage="fetch",
            inputs_digest=canonical_digest({"url": url}),
            outputs_digest=canonical_digest(fetch_outputs),
            decision=fetch_result.get("status", "unknown"), detail=fetch_detail,
        ))

    if fetch_result.get("status") == "not_modified":
        return DoorOutcome(url=url, kind="unchanged",
                           detail="304 Not Modified — the server says the body is unchanged")

    # WHERE DID WE ACTUALLY LAND? (evaluator finding, PR #205 r1.) The caller
    # decided this URL was same-site and not a sign-in surface BEFORE the
    # fetch. requests follows redirects, so a 200 OK can come back from
    # somewhere else entirely — an off-origin ticketing host, or the venue's
    # login page. Re-checking the FINAL url is the difference between "we read
    # the venue's own calendar" and "we read a page we never classified and
    # attributed it to the venue".
    final_url = fetch_result.get("final_url") or url
    landed = demote_on_response(verdict, final_url=final_url)
    if _wall_observed(verdict, landed):
        logger.warning(
            "%s source=%s url=%s reason=%s",
            CLASS_D_WALL_MARKER, source_name, final_url, landed.reason,
        )
        log_step(ReplayRecord(
            run_id=run_id, ts=_now_iso(), source_id=str(source_id),
            source_name=source_name, stage="follow_wall" if follow else "wall",
            inputs_digest=canonical_digest({"url": url, "final_url": final_url}),
            outputs_digest=canonical_digest({"source_class": landed.source_class}),
            decision="class_d", detail=landed.reason,
        ))
        return DoorOutcome(url=url, kind="wall", detail=landed.reason,
                           final_url=final_url, verdict=landed)
    if url != start_url and not same_site(final_url, start_url):
        # NOT a wall — the site simply sent us somewhere else, and that
        # somewhere is a DIFFERENT source with its own catalog row, class and
        # access posture. Drop the page rather than extract it here.
        #
        # The `url != start_url` guard is load-bearing (Coverage Law: the
        # catalog is greedy). A source's REGISTERED start URL defines its
        # origin, so it cannot violate it — a catalog row that 301s to another
        # host is simply where that source lives, and refusing it would delete
        # rows we legally saw. The rule binds every door we CHOSE: a
        # remembered best_url and every followed page.
        logger.warning(
            "door %s redirected off-site to %s — not extracted "
            "(an off-site page is a different source, never this one's)",
            url, final_url,
        )
        log_step(ReplayRecord(
            run_id=run_id, ts=_now_iso(), source_id=str(source_id),
            source_name=source_name, stage="follow_offsite" if follow else "offsite",
            inputs_digest=canonical_digest({"url": url}),
            outputs_digest=canonical_digest({"final_url": final_url}),
            decision="offsite_redirect",
            detail=f"landed on {final_url}, which is not the start URL's site",
        ))
        return DoorOutcome(url=url, kind="offsite", final_url=final_url,
                           detail=f"landed off-site on {final_url}")

    if fingerprint is not None and fingerprint.unchanged(fetch_result.get("content_hash")):
        detail = (
            f"body fingerprint unchanged ({fingerprint.content_hash[:12]}...) — "
            "extraction skipped, nothing new to read"
        )
        log_step(ReplayRecord(
            run_id=run_id, ts=_now_iso(), source_id=str(source_id),
            source_name=source_name,
            stage="follow_fingerprint" if follow else "fingerprint",
            inputs_digest=canonical_digest({"url": url}),
            outputs_digest=canonical_digest({"content_hash": fetch_result.get("content_hash")}),
            decision="unchanged", detail=detail,
        ))
        return DoorOutcome(url=url, kind="unchanged", detail=detail, final_url=final_url)

    return DoorOutcome(
        url=url, kind="changed", final_url=final_url,
        text=fetch_result.get("text") or "",
        content_type=fetch_result.get("content_type"),
    )


def _discover_second_door(
    *,
    run_id: str,
    ai: AIProvider,
    source: Dict[str, Any],
    sxsw_mode: bool,
    start_url: str,
    start_html: str,
    follow_state: Dict[str, int],
    verdict: Any,
    budget: TickBudget,
) -> Dict[str, Any]:
    """The DISCOVER queue's second probe: the one best event page this start
    page advertises.

    A source is in the discover queue because we do not know its door yet. The
    start page is probe one; this is probe two, and there is no probe three.
    `discover_event_pages` already ranks its results by evidence — link text
    the site itself wrote, then event-shaped URL paths, then conventional
    guesses — so asking it for `limit=1` IS "the scored events/calendar/shows
    path". A second scorer here would be a second definition of what a schedule
    link looks like.

    Rules that cannot be relaxed, all enforced in _knock_door so there is one
    copy of each: on-origin only (checked before the fetch by discovery, and
    again on the FINAL url after redirects); a wall ends the source — we knock
    once; a 404 is a miss, not a wall; every fetch passes the tick budget.
    """
    source_id = source.get("source_id")
    source_name = source["name"]
    source_class = source["source_class"]
    summary: Dict[str, Any] = {
        "followed": 0, "extracted": 0, "missed": 0, "walled": False,
        "candidates": 0, "blocked_reason": "", "discovered": 0,
        "unchanged": 0, "deferred": 0, "urls": [],
    }

    if verdict.source_class != CLASS_B_PUBLIC_HTML:
        summary["blocked_reason"] = (
            f"not probed: catalog class {verdict.source_class} — {verdict.reason}")
        return summary

    budget_left = min(follow_state["source_cap"], follow_state["remaining"])
    if budget_left <= 0:
        summary["blocked_reason"] = (
            f"not probed: run probe budget spent "
            f"({FOLLOW_RUN_CAP_ENV}={follow_state['run_cap']}) — the pages this "
            "source advertises are left for a later tick, not dropped")
        return summary

    discovery = discover_event_pages(start_html, start_url, limit=budget_left)
    summary["discovered"] = len(discovery.pages)
    log_step(ReplayRecord(
        run_id=run_id, ts=_now_iso(), source_id=str(source_id), source_name=source_name,
        stage="follow_discovery", inputs_digest=canonical_digest({"start_url": start_url}),
        outputs_digest=canonical_digest({
            "pages": discovery.page_urls,
            "ics_links": discovery.ics_links,
            "jsonld_events": discovery.jsonld_events,
            "skipped": discovery.skipped_reason_counts(),
        }),
        decision="discovered",
        detail=(f"{len(discovery.pages)} same-site event page(s) advertised; "
                f"probe budget {budget_left}"),
    ))
    if not discovery.pages:
        summary["blocked_reason"] = "no same-site event page advertised by the start page"
        return summary

    for page in discovery.pages:
        if follow_state["remaining"] <= 0:
            summary["blocked_reason"] = (
                f"run probe budget spent after {summary['followed']} page(s) "
                f"({FOLLOW_RUN_CAP_ENV}={follow_state['run_cap']})")
            break
        follow_state["remaining"] -= 1
        summary["urls"].append(page.url)
        door = _knock_door(
            run_id=run_id, source_id=source_id, source_name=source_name,
            url=page.url, start_url=start_url, verdict=verdict,
            render_state=follow_state["render_state"], follow=True,
            budget=budget, queue=QUEUE_DISCOVER,
        )
        if door.kind == "deferred":
            summary["deferred"] += 1
            summary["blocked_reason"] = door.detail
            summary["urls"].pop()
            break
        if door.kind == "wall":
            # Narrowed isolation, deliberately: one broken sub-page must not
            # cost the rest of a venue's calendar, and a WALL must not be lost
            # as a generic error — that distinction is the whole class-D rule.
            summary["walled"] = True
            summary["blocked_reason"] = f"{door.detail} (at {page.url})"
            return summary
        if door.kind == "backoff":
            summary["blocked_reason"] = f"{door.detail} (at {page.url})"
            return summary
        if door.kind == "unchanged":
            summary["unchanged"] += 1
            continue
        if door.kind in ("missed", "offsite"):
            summary["missed"] += 1
            continue

        summary["followed"] += 1
        try:
            page_outcome = _process_fetched_page(
                run_id=run_id, ai=ai, source_id=source_id, source_name=source_name,
                page_url=page.url, source_class=source_class, sxsw_mode=sxsw_mode,
                text=door.text, content_type=door.content_type, budget=budget,
            )
        except Exception as exc:  # noqa: BLE001 — reported per page, never fatal
            summary["missed"] += 1
            logger.error("probe page %s failed after fetch: %s", page.url, exc)
            log_step(ReplayRecord(
                run_id=run_id, ts=_now_iso(), source_id=str(source_id),
                source_name=source_name, stage="follow_error",
                inputs_digest=canonical_digest({"url": page.url}),
                outputs_digest=canonical_digest({"error": str(exc)}),
                decision="error", detail=f"{type(exc).__name__}: {exc}",
            ))
            continue

        if page_outcome.decision == "deferred":
            summary["deferred"] += 1
            summary["blocked_reason"] = page_outcome.detail
            continue
        if page_outcome.decision != "sensor_rejected":
            summary["extracted"] += 1
            summary["candidates"] += page_outcome.candidates

    return summary


def _run_one_source(
    *,
    run_id: str,
    ai: AIProvider,
    source: Dict[str, Any],
    sxsw_mode: bool,
    render_state: Dict[str, int],
    follow_state: Dict[str, Any],
    budget: TickBudget,
) -> tuple[SourceResult, Dict[str, int]]:
    """Drive ONE source, from whichever queue it is in.

    REFRESH — we know this source's door (`best_url`, the page that produced
    the most candidates in the last 30 days). ONE fetch: go straight at it, and
    do not spend a second fetch guessing at conventional paths beside a page we
    know works. This is the steady state.

    DISCOVER — we do not know its door. ONE OR TWO probes: the registered start
    URL, then the single top-ranked events/calendar/shows page it advertises.

    Either way an UNCHANGED door ends the source for this tick: 304, or a body
    hashing to what we already read, means there is nothing new behind it, and
    re-proving that with a second fetch is the waste this pass removes. A dead
    best_url is the one case a refresh spends a second fetch: it falls back to
    the registered start URL, so a moved calendar re-discovers itself on the
    next tick instead of quietly costing the source its coverage.

    Returns (SourceResult, counts) where counts is this source's DELTA on the
    RunReport buckets — every stage it reached, not a single terminal bucket.
    A PASS stops at "ready_to_promote": the loop never publishes.

    Any exception from a start-page step is still treated as a per-source
    transient failure by the caller (run_loop) and is NOT caught here — the
    caller is the single place that decides isolation vs. abort. A door that
    misses (404/5xx/timeout) with no fallback left re-raises the ORIGINAL
    exception so that policy, and the error text ops reads, are unchanged.
    """
    source_id = source.get("source_id")
    source_name = source["name"]
    start_url = source["url"]
    source_class = source["source_class"]

    verdict = _class_verdict_for(source)
    state: Optional[SourceCrawlState] = source.get("crawl_state")
    # The scheduler may hand this source a specific door and queue — that is
    # how EVENT-PROXIMITY refresh reaches the loop: the item is a PAGE with a
    # near event on it, not a source taking its normal turn. Absent an
    # override the source's own crawl state decides, exactly as before.
    queue = source.get("queue") or (state.queue if state else QUEUE_DISCOVER)
    primary_url = choose_primary_door(
        start_url=start_url,
        # Routed through the same guard either way: a door read out of stored
        # data is only used when it is on the REGISTERED start URL's own site.
        best_url=source.get("door") or (state.best_url if state else None),
        same_site_fn=same_site,
    )
    urls: List[str] = [primary_url]

    door = _knock_door(
        run_id=run_id, source_id=source_id, source_name=source_name,
        url=primary_url, start_url=start_url, verdict=verdict,
        render_state=render_state, follow=False, budget=budget, queue=queue,
    )
    doors_spent = 0
    # THE DEFINING DOOR: the page this tick actually came to read. Kept
    # separate from `door` because the fallback below REPLACES `door`, and the
    # verdict must keep describing the page we came for (evaluator finding,
    # seat openai / lens absence-only). Without this, a best door that 404s
    # and then falls back to a healthy homepage reports `verified_present` —
    # a page that is gone displayed as re-verified, which is exactly the
    # misleading trust display the fail-closed rule exists to prevent.
    defining_door = door
    defining_url = primary_url
    if door.kind == "missed" and primary_url != start_url:
        # The remembered door is gone (moved calendar, retired path). Spend the
        # second fetch on the registered start URL rather than losing the
        # source for the tick — best_url is a shortcut, never a commitment.
        logger.warning(
            "best door %s missed (%s) — falling back to the registered start "
            "URL %s", primary_url, door.detail, start_url,
        )
        doors_spent = 1
        urls.append(start_url)
        primary_url = start_url
        door = _knock_door(
            run_id=run_id, source_id=source_id, source_name=source_name,
            url=start_url, start_url=start_url, verdict=verdict,
            render_state=render_state, follow=False, budget=budget, queue=queue,
        )

    def _verdict_kwargs(page_decision=None):
        """The fail-closed verdict for THE PAGE THIS TICK CAME TO READ.

        ONE call site, so no branch below can forget it and quietly default to
        something permissive. Recorded on the result AND in the replay log;
        nothing acts on it — the loop does not mutate published events (see
        worker.crawl_state's verification section for why that boundary is
        where it is).

        The verdict is computed from `defining_door`, NOT from whatever door
        the source ended up reading. When a remembered best door 404s and the
        loop falls back to the registered start URL, the fallback's success
        says the SOURCE still has a door — it says nothing about the page that
        vanished, and reporting `verified_present` for it would show a gone
        page as re-verified. The fallback outcome is still reported, as the
        separate fact it is: a re-found door, in the detail and the log.
        """
        fell_back = defining_door is not door
        v, why = classify_recheck(
            door_kind=defining_door.kind,
            # A page_decision belongs to the door that produced it. After a
            # fallback it describes the OTHER page, so it must not be allowed
            # to upgrade the defining page's verdict.
            page_decision=None if fell_back else page_decision,
            http_status=defining_door.http_status)
        if fell_back:
            why += (f"; the source's door was re-found at {primary_url} "
                    f"({door.kind}), which does not re-verify {defining_url}")
        log_step(ReplayRecord(
            run_id=run_id, ts=_now_iso(), source_id=str(source_id),
            source_name=source_name, stage="verify",
            inputs_digest=canonical_digest({
                "defining_url": defining_url, "read_url": primary_url,
                "queue": queue, "fell_back": fell_back}),
            outputs_digest=canonical_digest({"verdict": v}),
            decision=v, detail=why,
        ))
        return {"verdict": v, "verdict_reason": why}

    if door.kind == "deferred":
        return (
            SourceResult(
                source_id, source_name, "budget", "deferred", door.detail,
                urls_fetched=[], queue=queue, blocked=door.detail,
                **_verdict_kwargs(),
            ),
            {"deferred": 1},
        )

    if door.kind == "unchanged":
        return (
            SourceResult(
                source_id, source_name, "fetch", "not_modified", door.detail,
                urls_fetched=urls, changed=False, skipped_unchanged=1, queue=queue,
                **_verdict_kwargs(),
            ),
            # A 304 keeps its own historical bucket (no bytes were newly
            # fetched); an identical body DID cost a fetch, so it counts as
            # fetched. Both are skipped_unchanged — that is the money bucket.
            {"skipped_unchanged": 1,
             **({"not_modified": 1} if door.detail.startswith("304")
                else {"fetched": 1})},
        )

    if door.kind in ("wall", "backoff"):
        blocked = ("class D — closed door" if door.kind == "wall"
                   else "rate-limited — backing off")
        return (
            SourceResult(
                source_id, source_name, "fetch", door.kind, door.detail,
                urls_fetched=urls, blocked=f"{blocked}: {door.detail}", queue=queue,
                **_verdict_kwargs(),
            ),
            # `blocked` only. pages_walled counts PROBE pages that hit a wall;
            # a start-page wall is not a probe page, and merging the two would
            # make "the probe hit a wall" unreadable.
            {"blocked": 1},
        )

    if door.kind in ("missed", "offsite"):
        # No fallback left. Re-raise the ORIGINAL exception so run_loop's
        # per-source isolation records exactly what it always did; an off-site
        # landing has no exception, so it is reported as this source's error.
        if door.error is not None:
            raise door.error
        raise RuntimeError(door.detail)

    page = _process_fetched_page(
        run_id=run_id, ai=ai, source_id=source_id, source_name=source_name,
        page_url=primary_url, source_class=source_class, sxsw_mode=sxsw_mode,
        text=door.text, content_type=door.content_type, budget=budget,
    )

    if page.decision == "sensor_rejected":
        # The page told us nothing readable, so there is no markup to discover
        # a second door FROM. Unchanged behaviour, stated: the probe reads the
        # fetched page's own links, it never guesses without one.
        return (
            SourceResult(
                source_id, source_name, "sensor", "sensor_rejected", page.detail,
                urls_fetched=urls, changed=True, queue=queue,
                **_verdict_kwargs("sensor_rejected"),
            ),
            {"fetched": 1, "sensor_rejected": 1},
        )

    if page.decision == "deferred":
        # Fetched fine; the model budget stopped short of extracting it.
        return (
            SourceResult(
                source_id, source_name, "extract", "deferred", page.detail,
                urls_fetched=urls, changed=True, queue=queue, blocked=page.detail,
                **_verdict_kwargs("deferred"),
            ),
            {"fetched": 1, "deferred": 1},
        )

    # THE SECOND PROBE — discover queue only, and only if the first fetch has
    # not already been spent on the start-URL fallback. A refresh source's
    # door already answered; probing conventional paths beside a page we KNOW
    # produces candidates is precisely the fetch this pass exists to save, and
    # the guess is not lost — it is what a later tick tries if the best door
    # stops producing.
    if queue == QUEUE_DISCOVER and doors_spent == 0 and primary_url == start_url:
        probe = _discover_second_door(
            run_id=run_id, ai=ai, source=source, sxsw_mode=sxsw_mode,
            start_url=primary_url, start_html=door.text,
            follow_state=follow_state, verdict=verdict, budget=budget,
        )
    else:
        if queue == QUEUE_EVENT:
            why = ("event-proximity refresh: one page fetch covers every event "
                   "on that page, so no probe is spent")
        elif queue == QUEUE_REFRESH:
            why = "refresh queue: the known best door answered, so no probe was spent"
        else:
            why = ("second probe spent on the start-URL fallback after the best "
                   "door missed")
        probe = {
            "followed": 0, "extracted": 0, "missed": 0, "walled": False,
            "candidates": 0, "discovered": 0, "unchanged": 0, "deferred": 0,
            "urls": [], "blocked_reason": why,
        }
    urls.extend(probe["urls"])

    counts: Dict[str, int] = {
        "fetched": 1,
        "extracted": 1,
        "candidates": page.candidates + probe["candidates"],
        "pages_followed": probe["followed"],
        "pages_extracted": probe["extracted"],
        "pages_missed": probe["missed"],
        "pages_walled": 1 if probe["walled"] else 0,
        "skipped_unchanged": probe["unchanged"],
        "deferred": probe["deferred"],
    }
    detail = page.detail
    if probe["followed"] or probe["blocked_reason"] or probe["unchanged"]:
        detail += (
            f" | probe: {probe['followed']} page(s) fetched, "
            f"{probe['candidates']} candidate(s)"
            + (f", {probe['unchanged']} unchanged" if probe["unchanged"] else "")
            + (f"; {probe['blocked_reason']}" if probe["blocked_reason"] else "")
        )

    terminal = {"held": "held", "escalated": "escalated",
                "ready_to_promote": "passed"}[page.decision]
    counts[terminal] = counts.get(terminal, 0) + 1
    return (
        SourceResult(
            source_id, source_name, "gate3", page.decision, detail,
            urls_fetched=urls, changed=True, queue=queue,
            candidates=page.candidates + probe["candidates"],
            skipped_unchanged=probe["unchanged"],
            blocked=probe["blocked_reason"] if probe["walled"] else "",
            **_verdict_kwargs(page.decision),
        ),
        counts,
    )

def render_run_table(report: "RunReport") -> str:
    """The founder's run table, one row per source attempted.

        source | queue | url fetched | changed? | verified? | candidates |
        skipped-unchanged | blocked

    Printed by worker/run_once.py after every real run, and by the fixture
    tests, because the point of fair crawl is a claim about DISTRIBUTION —
    many sources, few pages each — and a counts dict cannot show distribution.
    A blank `blocked` cell means nothing stopped this source; "0" candidates
    with an empty blocked cell means we read the page and it advertised no
    events, which is a different fact from "we never got in" (Operating Law:
    a 403 is triage, not "this venue has no events"). `verified?` is the
    fail-closed verdict — "present", "absent", or "no" — and "no" means we
    learned nothing this tick, so the last good row stands.

    Pure formatting over the report the loop already built — it queries
    nothing and decides nothing, so printing it can never change a run.
    """
    header = ("source", "queue", "url fetched", "changed?", "verified?",
              "candidates", "skipped-unchanged", "blocked")
    rows = [header]
    for r in report.results:
        changed = "-" if r.changed is None else ("yes" if r.changed else "no")
        rows.append((
            r.source_name,
            r.queue or "-",
            " ".join(r.urls_fetched) if r.urls_fetched else "-",
            changed,
            r.verdict.replace("verified_", "").replace("unverified", "no"),
            str(r.candidates),
            str(r.skipped_unchanged),
            r.blocked or "",
        ))
    widths = [max(len(row[i]) for row in rows) for i in range(len(header))]
    out = [" | ".join(cell.ljust(widths[i]) for i, cell in enumerate(rows[0])).rstrip(),
           "-+-".join("-" * w for w in widths)]
    for row in rows[1:]:
        out.append(" | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
    return "\n".join(out)


def run_loop(
    *,
    ai: AIProvider,
    sources: List[Dict[str, Any]],
    sxsw_mode: bool = False,
    dsn: Optional[str] = None,
    budget: Optional[TickBudget] = None,
) -> RunReport:
    """Run one TICK of the pipeline over `sources`, in the order given.

    A tick is not "N sources". `sources` is the work the scheduler planned —
    already ordered most-overdue-first (worker/run_once.py) — and this loop
    works down it until a REAL budget stops it: wall clock, model spend, or the
    bug-safety fetch cap. Everything it did not reach is reported as DEFERRED
    and leads the next tick. How many sources a tick covered is an OUTCOME
    (report.outcomes), never an input.

    Each source dict is {source_id, name, url, source_class} plus, optionally,
    `crawl_state` (its derived history), `queue`, and `door` — the last two are
    how the event-proximity queue hands the loop a specific PAGE to re-read
    rather than a source taking its normal turn.

    The loop classifies candidates through the trust gate and STOPS there: a
    PASS candidate is left in the store ("ready_to_promote") for an
    authenticated ops action to publish. There is no `promote` flag and no
    promotion path from this module — "AI never auto-promotes" is enforced
    structurally, by the absence of any promote_candidate call.

    It also never MUTATES a published event. A re-check records a fail-closed
    verdict (worker.crawl_state.classify_recheck) and nothing else: no delete,
    no cancel, no date edit, whatever the page said. Only confirmed same-page
    evidence could license a change, and building that path is a
    trust-invariant decision, not this loop's.

    Per-candidate gate signals are loaded from the DB by candidate id via
    worker.candidate_store.load_candidate_gate_signals — never injected per
    source — so the gate always evaluates real stored data.

    `dsn` is accepted for interface symmetry with the rest of the pipeline
    (worker/candidate_store.py etc. read ONELIVE_DB_DSN from the environment)
    but is not passed further: none of the wired functions in this module
    accept a dsn parameter, so a caller wanting a non-default DSN must set
    ONELIVE_DB_DSN before calling run_loop.
    """
    # Resolve the per-run render budget BEFORE touching any source: a
    # malformed value is a config/structural failure and aborts the run
    # loudly (fail closed), per this module's failure semantics.
    render_cap = _resolve_render_cap()
    render_state = {"cap": render_cap, "remaining": render_cap}
    # Same fail-closed timing for the probe budgets: a malformed ceiling must
    # abort the run BEFORE the first fetch, never mid-walk.
    follow_caps = _resolve_follow_caps()
    follow_state: Dict[str, Any] = {
        "run_cap": follow_caps["run_cap"],
        "source_cap": follow_caps["source_cap"],
        "remaining": follow_caps["run_cap"],
        # Probes share the run's ONE render budget: a JS-shell calendar is
        # exactly the page worth rendering, and a second budget would double
        # the spend the render cap exists to bound.
        "render_state": render_state,
    }
    tick = budget if budget is not None else TickBudget()
    # Size the per-queue reservations against THIS tick's actual work, so a
    # share never strands budget it was only meant to protect.
    tick.reserve_for_plan([
        str(src.get("queue") or QUEUE_DISCOVER) for src in sources])

    run_id = new_run_id()
    started = _now_iso()
    report = RunReport(run_id=run_id, started=started, finished="")

    for index, source in enumerate(sources):
        source_id = source.get("source_id")
        source_name = source.get("name", "<unnamed>")

        stop = tick.tick_stop()
        if stop:
            # A REAL limit, so the tick ends here. Everything left is deferred,
            # counted, and named — a tick that quietly stopped early would look
            # exactly like a catalog that had nothing to say.
            tick.stop_reason = stop
            remaining = len(sources) - index
            tick.sources_deferred += remaining
            report.counts["deferred"] += remaining
            logger.warning(
                "tick stopped on %s after %d source(s); %d deferred to the next "
                "tick (nothing dropped — they lead the next one).",
                stop, tick.sources_touched, remaining,
            )
            log_step(ReplayRecord(
                run_id=run_id, ts=_now_iso(), source_id="", source_name="",
                stage="tick", inputs_digest=canonical_digest({"planned": len(sources)}),
                outputs_digest=canonical_digest(tick.outcomes()),
                decision="tick_stop", detail=f"{stop}; {remaining} source(s) deferred",
            ))
            break

        try:
            result, counts = _run_one_source(
                run_id=run_id, ai=ai, source=source, sxsw_mode=sxsw_mode,
                render_state=render_state, follow_state=follow_state, budget=tick,
            )
        except Exception as exc:  # noqa: BLE001 - deliberate, audited, isolated per spec
            # Per-source transient failure: caught, logged, and isolated so
            # one bad source cannot take down the tick. This is the ONLY place
            # a bare Exception is caught in this module, and it is always
            # logged to both the RunReport and the replay log — never
            # swallowed silently.
            log_step(ReplayRecord(
                run_id=run_id, ts=_now_iso(), source_id=str(source_id), source_name=source_name,
                stage="error", inputs_digest=canonical_digest({"source": source_name}),
                outputs_digest=canonical_digest({"error": str(exc)}), decision="error",
                detail=f"{type(exc).__name__}: {exc}",
            ))
            report.results.append(SourceResult(
                source_id, source_name, "error", "error", f"{type(exc).__name__}: {exc}",
                queue=str(source.get("queue") or ""),
            ))
            report.counts["errors"] += 1
            tick.sources_touched += 1
            continue

        if result.decision == "deferred":
            tick.sources_deferred += 1
        else:
            tick.sources_touched += 1
        report.results.append(result)
        for key, delta in counts.items():
            report.counts[key] += delta

    # The measured outcomes, written once at the end from the meter that did
    # the counting — never recomputed from the buckets, which would be a second
    # arithmetic to disagree with the first.
    report.counts["fetches"] = tick.fetches
    report.counts["extract_calls"] = tick.extract_calls
    report.counts["input_tokens"] = tick.input_tokens
    report.counts["output_tokens"] = tick.output_tokens
    report.outcomes = tick.outcomes()
    report.finished = _now_iso()
    return report
