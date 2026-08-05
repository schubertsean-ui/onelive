"""The Loop — orchestrator-as-Harness.

This module IS the Sensors -> Harness -> Loop structure, not a plain pipeline
runner decorated with trust features later. For each source it drives:

    fetch -> sensors.assess_input -> extract_candidate -> trust_gate3.evaluate_gate
        -> (PASS -> leave ready for ops promote | HOLD/ESCALATE -> needs_review)

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
from worker.ai_extract import extract_candidate
from worker.candidate_store import (
    list_candidate_source_classes,
    load_candidate_gate_signals,
    stamp_gate_verdict,
)
from worker.fetch.http_fetch import fetch_url
from worker.fetch.paginate import discover_next_page
from worker.fetch.render_fetch import RenderError, fetch_with_render, render_html
from worker.replay_log import ReplayRecord, canonical_digest, log_step, new_run_id
from worker.sensors import assess_input
from worker.trust_gate3 import GateDecision, evaluate_gate

logger = logging.getLogger(__name__)

# Renders are expensive (a full headless-Chromium process per page), so each
# run carries a hard budget. Env knob + default documented in the module
# docstring above; validation is fail-closed in _resolve_render_cap().
RENDER_CAP_ENV = "ONELIVE_MAX_RENDERS_PER_RUN"
DEFAULT_MAX_RENDERS_PER_RUN = 5

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
)

# _run_one_source's "not_modified" outcome intentionally does NOT also set
# "fetched" (fetch_url reported nothing new arrived, so no bytes were newly
# fetched this run) — kept as its own explicit bucket here to document that
# choice as deliberate rather than an oversight.


@dataclass
class SourceResult:
    source_id: Optional[str]
    source_name: str
    stage_reached: str
    decision: str
    detail: str


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


def _resolve_render_cap() -> int:
    """Read + validate ONELIVE_MAX_RENDERS_PER_RUN, fail-closed.

    Unset (or set to the empty string, which is how an absent CI variable
    arrives) means the default. Anything else MUST parse as a base-10 integer
    >= 0; a malformed value raises ValueError so run_loop aborts loudly at
    start — a budget knob that cannot be read is a structural/config failure
    (same policy as an unwritable replay dir), and silently substituting the
    default would turn a typo into an unnoticed spend change. 0 disables
    rendering entirely.
    """
    raw = os.getenv(RENDER_CAP_ENV)
    if raw is None or raw.strip() == "":
        return DEFAULT_MAX_RENDERS_PER_RUN
    try:
        cap = int(raw.strip())
    except ValueError as exc:
        raise ValueError(
            f"{RENDER_CAP_ENV} must be a base-10 integer >= 0 (got {raw!r}); "
            "refusing to run with an unvalidated render budget — fail closed"
        ) from exc
    if cap < 0:
        raise ValueError(
            f"{RENDER_CAP_ENV} must be >= 0 (got {cap}); a negative render "
            "budget is meaningless — fail closed (use 0 to disable rendering)"
        )
    return cap


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


# Founder-directed 2026-08-05 ("build multi-page ingestion next. It's the
# single biggest lever left"): a paginated calendar is read for up to this
# many pages per run. The proving case is the Austin Chronicle: 2,362 events
# across 60 pages, of which a single-page fetch reads ~40.
#
# Why a small number is the RIGHT number, not a timid one: calendar pages are
# date-ordered, so page 1 carries the soonest events — exactly what a tonight
# product needs — and deeper events rise toward page 1 as their date
# approaches. Front-following therefore reaches the whole calendar over time
# without ever pulling sixty pages in one run. The existing per-page AI-call
# cap (ai_extract._max_events_per_page) still bounds extraction cost: extra
# pages add fetch bytes, never an unbounded number of model calls.
_DEFAULT_MAX_PAGES_PER_SOURCE = 5


def _max_pages_per_source() -> int:
    raw = os.environ.get("INGEST_MAX_PAGES_PER_SOURCE", "").strip()
    if not raw:
        return _DEFAULT_MAX_PAGES_PER_SOURCE
    try:
        n = int(raw)
    except ValueError:
        logger.warning("INGEST_MAX_PAGES_PER_SOURCE=%r is not an int — using "
                       "default %d", raw, _DEFAULT_MAX_PAGES_PER_SOURCE)
        return _DEFAULT_MAX_PAGES_PER_SOURCE
    return n if n >= 1 else _DEFAULT_MAX_PAGES_PER_SOURCE


def _fetch_paginated(
    *,
    source_id: Optional[str],
    url: str,
    render_state: Dict[str, int],
) -> Dict[str, Any]:
    """Fetch page 1, then follow the SOURCE'S OWN next-page links (bounded).

    Page 1 keeps the full existing behavior — render fallback, 304 handling,
    audit rows — untouched, and its result is what this returns. Additional
    pages are PLAIN fetches (a render per page would multiply browser cost
    for pages that are the same template) whose text is appended, so the
    sensor, extractor, and gate see one longer document and every downstream
    contract is unchanged.

    Fail-soft by construction: any problem on page N>1 stops the walk and
    keeps everything already read. A calendar that publishes no next link is
    simply a one-page fetch, exactly as before.
    """
    first = _fetch_with_render_fallback(
        source_id=source_id, url=url, render_state=render_state,
    )
    if first.get("status") != "ok" or not first.get("text"):
        return first  # 304 / error: nothing to page through

    max_pages = _max_pages_per_source()
    if max_pages <= 1:
        return first

    texts = [first["text"]]
    seen = {url}
    current_url = url
    current_html = first["text"]
    pages = 1

    while pages < max_pages:
        try:
            next_url = discover_next_page(current_html, current_url, seen)
        except Exception as exc:  # noqa: BLE001 — discovery must never break ingestion
            logger.warning("next-page discovery failed for %s (%s) — keeping "
                           "%d page(s)", current_url, type(exc).__name__, pages)
            break
        if not next_url:
            break
        try:
            page_result = fetch_url(source_id=source_id, url=next_url)
            if page_result.get("status") != "ok":
                logger.info("page %d of %s returned %s — keeping %d page(s)",
                            pages + 1, url, page_result.get("status"), pages)
                break
            page_text = _read_fetched_text(page_result)
        except Exception as exc:  # noqa: BLE001 — a later page must never lose page 1
            logger.warning("page %d fetch failed for %s (%s) — keeping %d "
                           "page(s)", pages + 1, next_url, type(exc).__name__, pages)
            break
        if not page_text:
            break
        seen.add(next_url)
        texts.append(page_text)
        current_url, current_html = next_url, page_text
        pages += 1

    if pages > 1:
        logger.info("paginated fetch: %s read %d pages", url, pages)
    return {**first, "text": "\n".join(texts), "pages_fetched": pages}


def _fetch_with_render_fallback(
    *,
    source_id: Optional[str],
    url: str,
    render_state: Dict[str, int],
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


def _run_one_source(
    *,
    run_id: str,
    ai: AIProvider,
    source: Dict[str, Any],
    sxsw_mode: bool,
    render_state: Dict[str, int],
) -> tuple[SourceResult, List[str]]:
    """Drive a single source through fetch -> sensor -> extract -> gate3.
    Returns (SourceResult, count_keys) where count_keys is the ordered list of
    RunReport.counts buckets this source's run touched (e.g. a source that
    fetches, passes the sensor, extracts, then holds at the gate increments
    ["fetched", "extracted", "held"] — each stage it reached, not a single
    terminal bucket, so counts reflect real throughput at every stage rather
    than only the final outcome). A PASS stops at "ready_to_promote": the loop
    never publishes.

    Any exception raised by a step in here is treated as a per-source
    transient failure by the caller (run_loop) and is intentionally NOT
    caught inside this function — the caller is the single place that
    decides isolation vs. abort, so that policy lives in exactly one spot.
    """
    source_id = source.get("source_id")
    source_name = source["name"]
    url = source["url"]
    source_class = source["source_class"]

    fetch_result = _fetch_paginated(
        source_id=source_id, url=url, render_state=render_state,
    )
    # Replay fetch entry: the original fields are all preserved; the render
    # outcome EXTENDS the payload so the audit trail records whether the text
    # handed onward is the plain fetch or a headless re-render (and, on a
    # failed/refused render, why the plain text proceeded anyway).
    fetch_outputs: Dict[str, Any] = {
        "status": fetch_result.get("status"),
        "rendered": bool(fetch_result.get("rendered")),
        "pages_fetched": fetch_result.get("pages_fetched", 1),
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
        run_id=run_id, ts=_now_iso(), source_id=str(source_id), source_name=source_name,
        stage="fetch", inputs_digest=canonical_digest({"url": url}),
        outputs_digest=canonical_digest(fetch_outputs),
        decision=fetch_result.get("status", "unknown"), detail=fetch_detail,
    ))

    if fetch_result.get("status") == "not_modified":
        return (
            SourceResult(source_id, source_name, "fetch", "not_modified", "content unchanged since last fetch"),
            ["not_modified"],
        )

    # fetch_with_render already decoded (or rendered) the text; on any 'ok'
    # result the key is always present. Rendered or not, it faces the same
    # sensor below — a render buys readability, never trust.
    text = fetch_result["text"]
    content_type = fetch_result.get("content_type")
    reading = assess_input(text=text, content_type=content_type)
    log_step(ReplayRecord(
        run_id=run_id, ts=_now_iso(), source_id=str(source_id), source_name=source_name,
        stage="sensor", inputs_digest=canonical_digest({"content_type": content_type, "length": len(text)}),
        outputs_digest=canonical_digest({"ok": reading.ok, "signals": reading.signals}),
        decision="sensor_rejected" if not reading.ok else "sensor_passed", detail=reading.reason,
    ))
    if not reading.ok:
        return (
            SourceResult(source_id, source_name, "sensor", "sensor_rejected", reading.reason),
            ["fetched", "sensor_rejected"],
        )

    candidate_id = extract_candidate(
        ai=ai,
        text=text,
        source_class=source_class,
        source_name=source_name,
        source_url=url,
        sxsw_mode=sxsw_mode,
        source_id=source_id,
    )
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
        return (
            SourceResult(source_id, source_name, "gate3", "held", verdict.reason),
            ["fetched", "extracted", "held"],
        )

    if verdict.decision is GateDecision.ESCALATE:
        return (
            SourceResult(source_id, source_name, "gate3", "escalated", verdict.reason),
            ["fetched", "extracted", "escalated"],
        )

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
    return (
        SourceResult(source_id, source_name, "gate3", "ready_to_promote",
                     "PASS (trust gate); awaiting authenticated ops promote"),
        ["fetched", "extracted", "passed"],
    )


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

    run_id = new_run_id()
    started = _now_iso()
    report = RunReport(run_id=run_id, started=started, finished="")

    for source in sources:
        source_id = source.get("source_id")
        source_name = source.get("name", "<unnamed>")
        try:
            result, count_keys = _run_one_source(
                run_id=run_id, ai=ai, source=source, sxsw_mode=sxsw_mode,
                render_state=render_state,
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
        for key in count_keys:
            report.counts[key] += 1

    report.finished = _now_iso()
    return report
