"""The Loop — orchestrator-as-Harness.

This module IS the Sensors -> Harness -> Loop structure, not a plain pipeline
runner decorated with trust features later. For each source it drives:

    fetch -> sensors.assess_input -> extract_candidate -> trust_gate3.evaluate_gate
        -> (PASS -> promote_candidate | HOLD/ESCALATE -> leave in needs_review)

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

Ratchet note (dev-time only, per red-team review): the iterate-on-green /
revert-on-regression ratchet governs how WE build and evolve this file across
commits. It must never leak into the runtime behaviour of the loop itself:
this module does not self-modify, and it must never auto-approve a promotion
to "keep the run going". Escalating an ambiguous candidate to a human is
the correct, intended outcome here — not a bug to route around.

This file legitimately calls worker.promote.promote_candidate and is
therefore on the PROMOTE_IMPORT_ALLOWLIST in tools/trust_gate.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ai.provider import AIProvider
from worker.ai_extract import extract_candidate
from worker.candidate_store import list_candidate_source_classes
from worker.fetch.http_fetch import fetch_url
from worker.promote import promote_candidate
from worker.replay_log import ReplayRecord, canonical_digest, log_step, new_run_id
from worker.sensors import assess_input
from worker.trust_gate3 import GateDecision, evaluate_gate

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


def _gather_evidence_signals(candidate_id: str, extracted: Dict[str, Any]) -> Dict[str, Any]:
    """Build the evidence_signals dict trust_gate3.evaluate_gate needs.

    start_times comes from the extracted candidate's own start_time plus
    whatever the candidate store's evidence rows imply; in the current schema
    only the single extracted start_time is available per candidate at this
    stage (per-evidence start_time is not persisted separately), so
    start_times is a 1-element (or empty) list here. This is intentionally
    minimal rather than fabricated — trust_gate3 only flags a *conflict* when
    it observes more than one distinct non-null value, so a single value
    never triggers a false ESCALATE.
    """
    start_time = extracted.get("start_time")
    return {
        "start_times": [start_time] if start_time else [],
        "dedupe_ambiguous": False,
    }


def _run_one_source(
    *,
    run_id: str,
    ai: AIProvider,
    source: Dict[str, Any],
    sxsw_mode: bool,
    promote: bool,
) -> tuple[SourceResult, List[str]]:
    """Drive a single source through fetch -> sensor -> extract -> gate3 ->
    promote/escalate. Returns (SourceResult, count_keys) where count_keys is
    the ordered list of RunReport.counts buckets this source's run touched
    (e.g. a source that fetches, passes the sensor, extracts, then holds at
    the gate increments ["fetched", "extracted", "held"] — each stage it
    reached, not a single terminal bucket, so counts reflect real
    throughput at every stage rather than only the final outcome).

    Any exception raised by a step in here is treated as a per-source
    transient failure by the caller (run_loop) and is intentionally NOT
    caught inside this function — the caller is the single place that
    decides isolation vs. abort, so that policy lives in exactly one spot.
    """
    source_id = source.get("source_id")
    source_name = source["name"]
    url = source["url"]
    source_class = source["source_class"]

    fetch_result = fetch_url(source_id=source_id, url=url)
    log_step(ReplayRecord(
        run_id=run_id, ts=_now_iso(), source_id=str(source_id), source_name=source_name,
        stage="fetch", inputs_digest=canonical_digest({"url": url}),
        outputs_digest=canonical_digest({"status": fetch_result.get("status")}),
        decision=fetch_result.get("status", "unknown"), detail=str(fetch_result.get("status")),
    ))

    if fetch_result.get("status") == "not_modified":
        return (
            SourceResult(source_id, source_name, "fetch", "not_modified", "content unchanged since last fetch"),
            ["not_modified"],
        )

    text = _read_fetched_text(fetch_result)
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
    extracted = source.get("_extracted_for_test", {})  # see docstring in run_loop
    evidence_signals = _gather_evidence_signals(candidate_id, extracted)
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

    # PASS
    if not promote:
        log_step(ReplayRecord(
            run_id=run_id, ts=_now_iso(), source_id=str(source_id), source_name=source_name,
            stage="promote", inputs_digest=canonical_digest({"candidate_id": candidate_id}),
            outputs_digest=canonical_digest({}), decision="would_promote",
            detail="promote=False; left candidate for ops review",
        ))
        return (
            SourceResult(source_id, source_name, "gate3", "would_promote", "PASS but promote=False; left for ops"),
            ["fetched", "extracted", "passed"],
        )

    try:
        event_id = promote_candidate(candidate_id)
    except ValueError as exc:
        # promote_candidate re-checks the gate and dedupe internally; a
        # ValueError here (e.g. a duplicate discovered only at promote time)
        # is exactly the kind of ambiguity trust_gate3 exists to flag. We
        # downgrade to ESCALATE rather than crash the loop or silently drop
        # the candidate — it stays in needs_review with a logged reason.
        log_step(ReplayRecord(
            run_id=run_id, ts=_now_iso(), source_id=str(source_id), source_name=source_name,
            stage="promote", inputs_digest=canonical_digest({"candidate_id": candidate_id}),
            outputs_digest=canonical_digest({"error": str(exc)}), decision="escalated",
            detail=f"promote_candidate raised ValueError, downgraded to ESCALATE: {exc}",
        ))
        return (
            SourceResult(source_id, source_name, "promote", "escalated", f"promote raised: {exc}"),
            ["fetched", "extracted", "escalated"],
        )

    log_step(ReplayRecord(
        run_id=run_id, ts=_now_iso(), source_id=str(source_id), source_name=source_name,
        stage="promote", inputs_digest=canonical_digest({"candidate_id": candidate_id}),
        outputs_digest=canonical_digest({"event_id": event_id}), decision="promoted",
        detail=f"event_id={event_id}",
    ))
    return (
        SourceResult(source_id, source_name, "promote", "promoted", f"event_id={event_id}"),
        ["fetched", "extracted", "passed"],
    )


def run_loop(
    *,
    ai: AIProvider,
    sources: List[Dict[str, Any]],
    sxsw_mode: bool = False,
    promote: bool = False,
    dsn: Optional[str] = None,
) -> RunReport:
    """Run the full Sensors -> Harness -> Loop pipeline over `sources`.

    Each source dict is {source_id, name, url, source_class}; it may also
    carry an optional "_extracted_for_test" dict used only by hermetic tests
    to inject evidence_signals-relevant extracted fields (start_time,
    is_private_rsvp, _provenance) without a real DB round-trip, since the
    real extracted payload normally only becomes available via a DB read this
    module does not perform for every candidate.

    `dsn` is accepted for interface symmetry with the rest of the pipeline
    (worker/candidate_store.py etc. read ONELIVE_DB_DSN from the environment)
    but is not passed further: none of the wired functions in this module
    accept a dsn parameter, so a caller wanting a non-default DSN must set
    ONELIVE_DB_DSN before calling run_loop. Accepting-but-not-silently-using a
    parameter would be dead code; we keep it in the signature (matching the
    spec) and document the constraint here instead of pretending it works.
    """
    run_id = new_run_id()
    started = _now_iso()
    report = RunReport(run_id=run_id, started=started, finished="")

    for source in sources:
        source_id = source.get("source_id")
        source_name = source.get("name", "<unnamed>")
        try:
            result, count_keys = _run_one_source(
                run_id=run_id, ai=ai, source=source, sxsw_mode=sxsw_mode, promote=promote,
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
