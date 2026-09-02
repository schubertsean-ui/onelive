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
    SourceCrawlState,
    choose_primary_door,
    load_door_fingerprint,
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
    candidates: int = 0
    skipped_unchanged: int = 0
    blocked: str = ""


@dataclass
class RunReport:
    run_id: str
    started: str
    finished: str
    results: List[SourceResult] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=lambda: {k: 0 for k in _COUNT_KEYS})


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
    """Read + validate a per-run budget knob from the environment, fail-closed.

    Unset (or set to the empty string, which is how an absent CI variable
    arrives) means the default. Anything else MUST parse as a base-10 integer
    >= 0; a malformed value raises ValueError so run_loop aborts loudly at
    start — a budget knob that cannot be read is a structural/config failure
    (same policy as an unwritable replay dir), and silently substituting the
    default would turn a typo into an unnoticed spend change. 0 disables the
    budgeted behaviour entirely.

    One implementation for every knob: the render budget and the follow-page
    budgets are the same rule about the same kind of value, and two copies of
    "how a budget is parsed" would drift in the direction that costs money.
    """
    raw = os.getenv(env_name)
    if raw is None or raw.strip() == "":
        return default
    try:
        cap = int(raw.strip())
    except ValueError as exc:
        raise ValueError(
            f"{env_name} must be a base-10 integer >= 0 (got {raw!r}); "
            f"refusing to run with an unvalidated {noun} budget — fail closed"
        ) from exc
    if cap < 0:
        raise ValueError(
            f"{env_name} must be >= 0 (got {cap}); a negative {noun} "
            f"budget is meaningless — fail closed (use 0 to disable {noun}s)"
        )
    return cap


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
    """

    url: str
    kind: str
    detail: str = ""
    text: str = ""
    content_type: Optional[str] = None
    final_url: str = ""
    verdict: Any = None
    error: Optional[BaseException] = None


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
                           detail=f"{type(exc).__name__}: {exc}", error=exc)

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


def _follow_event_pages(
    *,
    run_id: str,
    ai: AIProvider,
    source: Dict[str, Any],
    sxsw_mode: bool,
    start_url: str,
    start_html: str,
    follow_state: Dict[str, int],
    verdict: Any,
) -> Dict[str, Any]:
    """Knock on the ONE best event page the start page advertises (#204's
    walker, inside the armed loop, now bounded to the fair-crawl door).

    Returns a summary dict: which door was tried, what it produced, and — if
    the source hit a wall — the class-D reason that stopped it.

    Rules that cannot be relaxed here (Coverage Law), all now enforced in
    _knock_door so there is one copy of each:
      * ON-ORIGIN ONLY, checked TWICE — page_discovery drops every off-site
        link before this function sees it, and the FINAL url of every
        successful fetch is re-checked before its text reaches the extractor.
      * A WALL ENDS THE SOURCE. We knock once. A 404 is a miss, not a wall.
      * BOUNDED. Per-source doors and a per-run page ceiling, both fail-closed.

    `discover_event_pages` returns its pages evidence-ranked (link text the
    site itself wrote, then event-shaped URL paths, then conventional
    guesses), so asking it for `limit=1` IS "the scored events/calendar/shows
    path" — the ranking already exists and a second scorer here would be a
    second definition of what a schedule link looks like.
    """
    source_id = source.get("source_id")
    source_name = source["name"]
    source_class = source["source_class"]
    summary: Dict[str, Any] = {
        "followed": 0, "extracted": 0, "missed": 0, "walled": False,
        "candidates": 0, "blocked_reason": "", "discovered": 0,
        "unchanged": 0, "urls": [],
    }

    if verdict.source_class != CLASS_B_PUBLIC_HTML:
        summary["blocked_reason"] = (
            f"not followed: catalog class {verdict.source_class} — {verdict.reason}")
        return summary

    budget = min(follow_state["source_cap"], follow_state["remaining"])
    if budget <= 0:
        summary["blocked_reason"] = (
            f"not followed: run follow-page budget spent "
            f"({FOLLOW_RUN_CAP_ENV}={follow_state['run_cap']}) — the pages this "
            "source advertises are left for a later run, not dropped")
        return summary

    discovery = discover_event_pages(start_html, start_url, limit=budget)
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
                f"door budget {budget}"),
    ))
    if not discovery.pages:
        summary["blocked_reason"] = "no same-site event page advertised by the start page"
        return summary

    for page in discovery.pages:
        if follow_state["remaining"] <= 0:
            summary["blocked_reason"] = (
                f"run follow-page budget spent after {summary['followed']} page(s) "
                f"({FOLLOW_RUN_CAP_ENV}={follow_state['run_cap']})")
            break
        follow_state["remaining"] -= 1
        summary["urls"].append(page.url)
        door = _knock_door(
            run_id=run_id, source_id=source_id, source_name=source_name,
            url=page.url, start_url=start_url, verdict=verdict,
            render_state=follow_state["render_state"], follow=True,
        )
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
                text=door.text, content_type=door.content_type,
            )
        except Exception as exc:  # noqa: BLE001 — reported per page, never fatal
            summary["missed"] += 1
            logger.error("follow page %s failed after fetch: %s", page.url, exc)
            log_step(ReplayRecord(
                run_id=run_id, ts=_now_iso(), source_id=str(source_id),
                source_name=source_name, stage="follow_error",
                inputs_digest=canonical_digest({"url": page.url}),
                outputs_digest=canonical_digest({"error": str(exc)}),
                decision="error", detail=f"{type(exc).__name__}: {exc}",
            ))
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
) -> tuple[SourceResult, Dict[str, int]]:
    """Drive ONE source through at most TWO doors: fetch -> sensor -> extract
    -> gate3 on each.

    Fair crawl (founder, 2026-09-02). The doors, in order:

      1. THE PRIMARY DOOR — the source's `best_url` (the page that produced
         the most candidates in the last 30 days), else its registered start
         URL. Going straight to the door that works is why a source costs one
         fetch in the steady state instead of a homepage plus a walk.
      2. AT MOST ONE MORE — either the single top-ranked events/calendar/shows
         page the start page advertises (class B only), or, when the best_url
         itself 404s/times out, a fallback to the registered start URL so a
         moved calendar re-discovers itself on the very next run instead of
         quietly costing the source its coverage.

    An unchanged primary door ENDS the source for this wave: 304 or an
    identical body hash means there is nothing new behind it, and spending the
    second door to prove that again is the waste this pass removes.

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
    primary_url = choose_primary_door(
        start_url=start_url,
        best_url=state.best_url if state else None,
        same_site_fn=same_site,
    )
    urls: List[str] = [primary_url]

    door = _knock_door(
        run_id=run_id, source_id=source_id, source_name=source_name,
        url=primary_url, start_url=start_url, verdict=verdict,
        render_state=render_state, follow=False,
    )
    doors_spent = 0
    if door.kind == "missed" and primary_url != start_url:
        # The remembered door is gone (moved calendar, retired path). Spend
        # the second door on the registered start URL rather than losing the
        # source for the wave — best_url is a shortcut, never a commitment.
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
            render_state=render_state, follow=False,
        )

    if door.kind == "unchanged":
        return (
            SourceResult(
                source_id, source_name, "fetch", "not_modified", door.detail,
                urls_fetched=urls, changed=False, skipped_unchanged=1,
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
                urls_fetched=urls, blocked=f"{blocked}: {door.detail}",
            ),
            # `blocked` only. pages_walled counts FOLLOWED pages that hit a
            # wall; a start-page wall is not a followed page, and merging the
            # two would make "the walk hit a wall" unreadable.
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
        text=door.text, content_type=door.content_type,
    )

    if page.decision == "sensor_rejected":
        # The page told us nothing readable, so there is no markup to discover
        # a second door FROM. Unchanged behaviour, stated: the walk reads the
        # fetched page's own links, it never guesses without one.
        return (
            SourceResult(
                source_id, source_name, "sensor", "sensor_rejected", page.detail,
                urls_fetched=urls, changed=True,
            ),
            {"fetched": 1, "sensor_rejected": 1},
        )

    # THE SECOND DOOR — spent only when there is something to discover it
    # from, and only if it has not already been spent. Two ways it is skipped:
    #
    #   * the best door already worked. Discovery would spend the fetch on a
    #     conventional-path GUESS (/calendar, /shows) beside a page we KNOW
    #     produces candidates. That is precisely the waste this pass removes,
    #     and the guess is not lost: it is what the next wave tries if the best
    #     door stops producing.
    #   * the fallback already used it, after the best door missed.
    #
    # Either way: <= 2 fetches per source per wave, always.
    if doors_spent == 0 and primary_url == start_url:
        follow = _follow_event_pages(
            run_id=run_id, ai=ai, source=source, sxsw_mode=sxsw_mode,
            start_url=primary_url, start_html=door.text,
            follow_state=follow_state, verdict=verdict,
        )
    else:
        follow = {
            "followed": 0, "extracted": 0, "missed": 0, "walled": False,
            "candidates": 0, "discovered": 0, "unchanged": 0, "urls": [],
            "blocked_reason": (
                "second door spent on the start-URL fallback after the best "
                "door missed — one door per source per wave"
                if doors_spent else
                "not discovered: the remembered best door answered, and a "
                "guessed path beside a working one is the fetch this pass "
                "exists to save"),
        }
    urls.extend(follow["urls"])

    counts: Dict[str, int] = {
        "fetched": 1,
        "extracted": 1,
        "candidates": page.candidates + follow["candidates"],
        "pages_followed": follow["followed"],
        "pages_extracted": follow["extracted"],
        "pages_missed": follow["missed"],
        "pages_walled": 1 if follow["walled"] else 0,
        "skipped_unchanged": follow["unchanged"],
    }
    detail = page.detail
    if follow["followed"] or follow["blocked_reason"] or follow["unchanged"]:
        detail += (
            f" | door: {follow['followed']} page(s) fetched, "
            f"{follow['candidates']} candidate(s)"
            + (f", {follow['unchanged']} unchanged" if follow["unchanged"] else "")
            + (f"; {follow['blocked_reason']}" if follow["blocked_reason"] else "")
        )

    terminal = {"held": "held", "escalated": "escalated",
                "ready_to_promote": "passed"}[page.decision]
    counts[terminal] = counts.get(terminal, 0) + 1
    return (
        SourceResult(
            source_id, source_name, "gate3", page.decision, detail,
            urls_fetched=urls, changed=True,
            candidates=page.candidates + follow["candidates"],
            skipped_unchanged=follow["unchanged"],
            blocked=follow["blocked_reason"] if follow["walled"] else "",
        ),
        counts,
    )



def render_run_table(report: "RunReport") -> str:
    """The founder's run table, one row per source attempted.

        source | url fetched | changed? | candidates | skipped-unchanged | blocked

    Printed by worker/run_once.py after every real run, and by the fixture
    tests, because the point of fair crawl is a claim about DISTRIBUTION —
    many sources, few pages each — and a counts dict cannot show distribution.
    A blank `blocked` cell means nothing stopped this source; "0" candidates
    with an empty blocked cell means we read the page and it advertised no
    events, which is a different fact from "we never got in" (Operating Law:
    a 403 is triage, not "this venue has no events").

    Pure formatting over the report the loop already built — it queries
    nothing and decides nothing, so printing it can never change a run.
    """
    header = ("source", "url fetched", "changed?", "candidates",
              "skipped-unchanged", "blocked")
    rows = [header]
    for r in report.results:
        changed = "-" if r.changed is None else ("yes" if r.changed else "no")
        rows.append((
            r.source_name,
            " ".join(r.urls_fetched) if r.urls_fetched else "-",
            changed,
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
) -> RunReport:
    """Run the full Sensors -> Harness -> Loop pipeline over `sources`.

    Each source dict is {source_id, name, url, source_class}. The loop classifies
    each candidate through the trust gate and STOPS at the gate: a PASS candidate
    is left in the store ("ready_to_promote") for an authenticated ops action to
    publish. There is no `promote` flag and no promotion path from this module —
    the "AI never auto-promotes" invariant is enforced structurally, by the
    absence of any promote_candidate call, not by a default a caller could flip.

    Per-candidate gate signals (stored extraction provenance, private-RSVP,
    start-time/dedupe facts) are loaded from the DB by candidate id via
    worker.candidate_store.load_candidate_gate_signals — never injected per
    source — so the gate always evaluates real stored data.

    `dsn` is accepted for interface symmetry with the rest of the pipeline
    (worker/candidate_store.py etc. read ONELIVE_DB_DSN from the environment)
    but is not passed further: none of the wired functions in this module
    accept a dsn parameter, so a caller wanting a non-default DSN must set
    ONELIVE_DB_DSN before calling run_loop. Accepting-but-not-silently-using a
    parameter would be dead code; we keep it in the signature (matching the
    spec) and document the constraint here instead of pretending it works.
    """
    # Resolve the per-run render budget BEFORE touching any source: a
    # malformed value is a config/structural failure and aborts the run
    # loudly (fail closed), per this module's failure semantics.
    render_cap = _resolve_render_cap()
    render_state = {"cap": render_cap, "remaining": render_cap}
    # Same fail-closed timing for the follow-pages budgets: a malformed
    # ceiling must abort the run BEFORE the first fetch, never mid-walk.
    follow_caps = _resolve_follow_caps()
    follow_state: Dict[str, Any] = {
        "run_cap": follow_caps["run_cap"],
        "source_cap": follow_caps["source_cap"],
        "remaining": follow_caps["run_cap"],
        # Followed pages share the run's ONE render budget: a JS-shell
        # calendar is exactly the page worth rendering, and a second budget
        # would double the spend the render cap exists to bound.
        "render_state": render_state,
    }

    run_id = new_run_id()
    started = _now_iso()
    report = RunReport(run_id=run_id, started=started, finished="")

    for source in sources:
        source_id = source.get("source_id")
        source_name = source.get("name", "<unnamed>")
        try:
            result, counts = _run_one_source(
                run_id=run_id, ai=ai, source=source, sxsw_mode=sxsw_mode,
                render_state=render_state, follow_state=follow_state,
            )
        except Exception as exc:  # noqa: BLE001 - deliberate, audited, isolated per spec
            # Per-source transient failure: caught, logged, and isolated so
            # one bad source cannot take down the run. This is the ONLY place
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
            ))
            report.counts["errors"] += 1
            continue

        report.results.append(result)
        for key, delta in counts.items():
            report.counts[key] += delta

    report.finished = _now_iso()
    return report
