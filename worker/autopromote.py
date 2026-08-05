"""Auto-promote engine — the ONLY wiring between the ratified earned-confidence
publish policy (worker/publish_policy.py) and the promoter (worker/promote.py).

Founder ratification (2026-07-25, docs/memory/decisions/
2026-07-25_auto-publish-earned-confidence-ratification.md): every fetched,
extracted, non-fabricated candidate publishes at its EARNED confidence without
a human click — EXCEPT gate ESCALATE, often-unreliable sources, and fabrication
risk, which always go to human review. That decision record names this module
("the only new promoter WILL BE worker/autopromote.py") and requires it to be
added to tools/trust_gate.py's PROMOTE_IMPORT_ALLOWLIST in the same change —
the deliberate, reviewed pattern the promote-import guard exists to enforce.

WHY a separate module (and never the orchestrator):
  The "orchestrator cannot import the promote path" invariant is structural
  and tested (tests/test_orchestrator.py). The AI-extraction loop stops at
  the gate; this module is a SEPARATE entrypoint (worker/run_autopromote.py)
  that starts from the candidate STORE, so extraction and publication remain
  two independently auditable stages with the gate between them. AI still
  never publishes: this pass only acts on gate output, re-verified fresh.

Fail-closed properties, each load-bearing:
  * The single mechanical switch. auto_publish_ratified() (AUTO_PUBLISH_RATIFIED,
    default OFF) gates the WHOLE pass: off means a loud no-op that promotes
    nothing — identical behavior to before this module existed.
  * Never trust a stored verdict. Every candidate's gate verdict is recomputed
    here via the same worker.trust_gate3.evaluate_gate the orchestrator used,
    against the candidate's REAL stored extraction + evidence signals — a stale
    'ready_to_promote' status row cannot publish on yesterday's evidence.
  * The promoter re-asserts. promote_candidate() re-runs the full three-way
    gate inside its own transaction before writing a canonical event (belt and
    braces): even a bug in THIS module cannot publish a non-PASS candidate.
  * Publish only on a fresh PASS. decide_publish's HOLD-publishes-as-unverified
    branch is for the hold queue's future surface; THIS pass's population is
    gate-passed candidates, so a fresh non-PASS verdict means the evidence
    drifted since the status was written — the candidate is left for human
    review with the drift recorded, never force-published past the promoter's
    PASS-only guard.
  * Per-candidate isolation. Any exception is recorded (log + audit_log),
    rolled back, and the pass continues; a failed candidate is never marked
    promoted (only promote_candidate's own committed transaction can do that).

Every skip/decision is written to audit_log (parameterized SQL only) so an
auto-publish decision is exactly as auditable as a human ops click.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from worker.candidate_store import _load_gate_signals, load_candidate_gate_signals
from worker.promote import promote_candidate
from worker.publish_policy import auto_publish_ratified, decide_publish
# The fabrication predicate is imported from the gate module itself —
# mechanical identity with what ESCALATE checks, never a hand-mirrored copy
# that could drift (same discipline as the harness-manifest rule, CLAUDE.md).
from worker.trust_gate3 import GateDecision, _has_validation_error_provenance, evaluate_gate

logger = logging.getLogger(__name__)

# Reliability score a source implicitly starts at (worker/source_reliability.py
# inserts 0.5 on first adjustment). An ungraded source is NOT the founder's
# "graded often-unreliable" exception, so it carries the same start score the
# grading loop would give it — comfortably above the 0.35 review threshold.
_UNGRADED_START_SCORE = 0.5

# Buckets tracked in AutopromoteReport.counts. Declared up front so every run
# reports the full shape even when a count is zero (project precedent:
# worker/orchestrator.py _COUNT_KEYS — "nothing happened" must be
# distinguishable from "not tracked").
_COUNT_KEYS = ("examined", "promoted", "human_review", "errors")


@dataclass
class CandidateOutcome:
    """One candidate's terminal outcome for this pass.

    action is 'promoted' | 'human_review' | 'error'. 'human_review' means the
    candidate was deliberately LEFT in its current status with the reason
    recorded — this pass never demotes or reroutes a candidate, so the human
    ops inbox path (api/ops_candidates.py) keeps working unchanged.
    """

    candidate_id: str
    action: str
    detail: str
    event_id: Optional[str] = None


@dataclass
class AutopromoteReport:
    """Auditable summary of one pass. enabled=False documents that the
    ratification switch was off and the pass was a deliberate no-op."""

    enabled: bool = False
    counts: Dict[str, int] = field(default_factory=lambda: {k: 0 for k in _COUNT_KEYS})
    outcomes: List[CandidateOutcome] = field(default_factory=list)


def _reliability_score(cur, source_id) -> Optional[float]:
    """Read the candidate source's evolving reliability grade.

    No row means the grading loop has not touched this source yet: it gets the
    documented 0.5 start score, not None — so "ungraded" and "just graded to
    its starting value" behave identically. None is returned only when the
    candidate has no source identity at all (source_id is NULL): with nothing
    to grade, the founder's graded-often-unreliable exception cannot apply,
    and decide_publish's other guards (fresh gate, fabrication) still hold.
    """
    if source_id is None:
        return None
    cur.execute(
        "select reliability_score from source_reliability where source_id=%s",
        (source_id,),
    )
    row = cur.fetchone()
    if not row or row[0] is None:
        return _UNGRADED_START_SCORE
    return float(row[0])


def _audit(conn, candidate_id: str, action: str, payload: Dict) -> None:
    """Write one system-actor audit row for an autopromote decision.

    Mirrors worker/candidate_store.record_ai_degradation: actor_type 'system'
    so machine decisions are never disguised as admin clicks in the audit trail.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into audit_log(actor_type, action, entity_type, entity_id, payload)
            values ('system',%s,'candidate',%s,%s::jsonb)
            """,
            (action, candidate_id, json.dumps(payload)),
        )


def _process_one(conn, *, candidate_id: str, source_id, sxsw_mode: bool) -> CandidateOutcome:
    """Decide and act on a single ready_to_promote candidate.

    Recomputes the gate verdict from the candidate's REAL stored evidence on
    this connection (never a stored verdict), feeds the ratified policy, and
    either publishes via promote_candidate (which re-asserts the gate in its
    own transaction) or leaves the candidate for human review with the reason
    written to audit_log. Raises are handled by the caller's per-candidate
    isolation — this function stays honest and lets failures propagate.
    """
    with conn.cursor() as cur:
        cur.execute(
            "select source_class from candidate_evidence where candidate_id=%s",
            (candidate_id,),
        )
        classes = [r[0] for r in cur.fetchall()]
        extracted, evidence_signals = load_candidate_gate_signals(candidate_id, cur=cur)
        reliability = _reliability_score(cur, source_id)

    # Fresh three-way verdict — the same gate, the same real stored signals,
    # the same seam (load_candidate_gate_signals) the orchestrator gates on.
    verdict = evaluate_gate(
        source_classes=classes,
        sxsw_mode=sxsw_mode,
        extracted=extracted,
        evidence_signals=evidence_signals,
    )

    # `ratified` is left to default (None) so the policy re-reads the live
    # AUTO_PUBLISH_RATIFIED switch itself: even if a caller reaches this
    # function directly, the fail-closed flag still governs (belt and braces
    # with run_autopromote's own top-level check).
    decision = decide_publish(
        gate_decision=verdict.decision.value,
        source_classes=classes,
        sxsw_mode=sxsw_mode,
        reliability_score=reliability,
        fabrication_risk=_has_validation_error_provenance(extracted),
    )

    if decision.publishes and verdict.decision is GateDecision.PASS:
        # promote_candidate re-runs the full gate on its own connection and
        # transaction; on any refusal it raises and the caller records the
        # failure — this candidate is never marked promoted by us.
        event_id = promote_candidate(candidate_id)
        _audit(conn, candidate_id, "autopromote_publish", {
            "event_id": str(event_id),
            "confidence": decision.confidence,
            "reason": decision.reason,
            "gate": verdict.decision.value,
        })
        logger.info(
            "autopromote: published candidate %s as event %s (%s)",
            candidate_id, event_id, decision.reason,
        )
        return CandidateOutcome(candidate_id, "promoted", decision.reason, event_id=str(event_id))

    if decision.publishes:
        # Policy says publish but the FRESH gate verdict is not PASS: the
        # evidence drifted since this candidate was marked ready_to_promote
        # (the population this pass selects is gate-passed by definition).
        # promote_candidate publishes only PASS candidates, and that guard is
        # not ours to argue with — record the drift and leave it to a human.
        detail = (
            f"policy would publish ({decision.reason}) but the fresh gate "
            f"verdict is {verdict.decision.value!r} ({verdict.reason}) — the "
            f"promoter publishes only gate-PASS candidates; left for human review"
        )
    else:
        detail = decision.reason

    _audit(conn, candidate_id, "autopromote_skip", {
        "reason": detail,
        "gate": verdict.decision.value,
        "reliability_score": reliability,
    })
    logger.info("autopromote: left candidate %s for human review (%s)", candidate_id, detail)
    return CandidateOutcome(candidate_id, "human_review", detail)



@dataclass
class StampReport:
    """Auditable summary of one backlog gate-stamping pass. Stamping
    CLASSIFIES candidates (persists the trust-gate verdict onto the row);
    it never publishes — 'stamped_ready' rows merely become visible to the
    two custody-holding publish paths, both of which re-gate before acting."""

    counts: Dict[str, int] = field(default_factory=lambda: {
        "examined": 0, "stamped_ready": 0, "stamped_hold": 0,
        "escalated": 0, "skipped_stale": 0, "errors": 0,
    })


def stamp_backlog(conn, *, limit: int) -> StampReport:
    """Sweep up to `limit` NEVER-STAMPED candidates (status='needs_review'
    with gate_reason still NULL — the population the 2026-08-05 diagnosis
    found stranded: verdicts lived only in the replay log) through the SAME
    evaluate_gate the orchestrator runs, and persist each verdict with the
    same column contract the human ops action uses. ESCALATE keeps
    'needs_review' but records the reason, so an escalated candidate leaves
    the sweep population after one examination instead of being re-examined
    forever. Honest residual: a candidate stamped 'needs_more_confirmation'
    re-enters the gate only when new evidence arrives through a re-gating
    path (ops add_evidence, or a future orchestrator merge) — this sweep is
    for the never-examined backlog, not a standing re-adjudicator.
    Bounded, DB-only (no AI calls), per-candidate isolation like the
    promote pass.
    """
    if limit <= 0:
        raise ValueError(
            f"stamp_backlog limit must be positive, got {limit} — 0 never "
            "means uncapped; skip the call to skip the phase."
        )
    report = StampReport()
    with conn.cursor() as cur:
        cur.execute(
            """
            select candidate_id, sxsw_mode
            from event_candidate
            where status='needs_review' and gate_reason is null
            order by created_at asc
            limit %s
            """,
            (limit,),
        )
        rows = cur.fetchall()

    for candidate_id, sxsw_mode in rows:
        candidate_id = str(candidate_id)
        report.counts["examined"] += 1
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "select source_class from candidate_evidence where candidate_id=%s",
                    (candidate_id,),
                )
                source_classes = [r[0] for r in cur.fetchall()]
                extracted, evidence_signals = _load_gate_signals(cur, candidate_id)
                verdict = evaluate_gate(
                    source_classes=source_classes,
                    sxsw_mode=bool(sxsw_mode),
                    extracted=extracted,
                    evidence_signals=evidence_signals,
                )
                if verdict.decision is GateDecision.ESCALATE:
                    status = "needs_review"
                    gate_reason = verdict.reason
                    required_next = "human review — escalated by trust gate"
                    bucket = "escalated"
                else:
                    status = verdict.base.status
                    gate_reason = verdict.base.reason
                    required_next = verdict.base.required_next
                    bucket = ("stamped_ready" if status == "ready_to_promote"
                              else "stamped_hold")
                # Compare-and-swap (evaluator finding, PR #182 r2): re-assert
                # the SELECTION predicate in the write so a row that ops or a
                # dispute moved between the sweep's read and this update is
                # never overwritten — 0 rows matched = newer trust state wins.
                cur.execute(
                    """
                    update event_candidate
                    set status=%s, gate_reason=%s, required_next=%s, updated_at=now()
                    where candidate_id=%s
                      and status='needs_review' and gate_reason is null
                    """,
                    (status, gate_reason, required_next, candidate_id),
                )
                stamped = cur.rowcount == 1
            if not stamped:
                conn.rollback()
                logger.warning(
                    "gate-stamp sweep: candidate %s left the never-stamped "
                    "population mid-sweep — skipped, newer state kept",
                    candidate_id,
                )
                report.counts["skipped_stale"] += 1
                continue
            _audit(conn, candidate_id, "gate_stamp", {
                "decision": verdict.decision.value,
                "status": status,
                "reason": gate_reason,
            })
            conn.commit()
            report.counts[bucket] += 1
        except Exception:  # noqa: BLE001 — per-candidate isolation; logged, sweep continues
            logger.exception("stamp_backlog: candidate %s raised — skipped, sweep continues", candidate_id)
            try:
                conn.rollback()
            except Exception:  # noqa: BLE001 — rollback is best-effort; the log line above carries the failure
                logger.exception("stamp_backlog: rollback failed for candidate %s", candidate_id)
            report.counts["errors"] += 1

    logger.info(
        "gate-stamp sweep complete: examined=%d ready=%d hold=%d escalated=%d "
        "stale-skipped=%d errors=%d",
        report.counts["examined"], report.counts["stamped_ready"],
        report.counts["stamped_hold"], report.counts["escalated"],
        report.counts["skipped_stale"], report.counts["errors"],
    )
    return report


def run_autopromote(conn, *, limit: int) -> AutopromoteReport:
    """Run one auto-promote pass over up to `limit` ready_to_promote candidates.

    Selection is oldest-first (created_at) so a bounded recurring pass drains
    the queue instead of re-reading its head. `limit` must be a positive int:
    0/negative/non-int is a misconfiguration and FAILS CLOSED (raises) instead
    of silently meaning "uncapped" — same rule as run_once's budget ceiling.

    Flag off (auto_publish_ratified() False) → the whole pass is a loud no-op:
    nothing is read, nothing is promoted, the report says enabled=False.

    Per-candidate exceptions are recorded (log + best-effort audit row), rolled
    back on this connection, and the pass CONTINUES — one broken candidate
    never takes down the pass, and a failed candidate is never marked promoted
    (only promote_candidate's own committed transaction writes that status).
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError(
            f"limit={limit!r} is invalid — the autopromote batch ceiling must "
            "be a positive integer; 0/negative fails closed, it never means "
            "uncapped."
        )

    report = AutopromoteReport()
    if not auto_publish_ratified():
        logger.warning(
            "AUTO_PUBLISH_RATIFIED is OFF — autopromote pass is a NO-OP "
            "(fail-closed). No candidates were read and nothing was promoted; "
            "every candidate still routes through the human ops inbox. Flip "
            "the switch only per the 2026-07-25 ratification record."
        )
        return report

    report.enabled = True
    with conn.cursor() as cur:
        cur.execute(
            """
            select candidate_id, source_id, sxsw_mode
            from event_candidate
            where status='ready_to_promote'
            order by created_at asc
            limit %s
            """,
            (limit,),
        )
        rows = cur.fetchall()

    for candidate_id, source_id, sxsw_mode in rows:
        candidate_id = str(candidate_id)
        report.counts["examined"] += 1
        try:
            outcome = _process_one(
                conn, candidate_id=candidate_id, source_id=source_id,
                sxsw_mode=bool(sxsw_mode),
            )
            conn.commit()
        except Exception as exc:  # noqa: BLE001 — deliberate per-candidate isolation, logged + audited below
            logger.exception("autopromote: candidate %s raised — skipped, pass continues", candidate_id)
            try:
                conn.rollback()
                _audit(conn, candidate_id, "autopromote_error", {
                    "error": f"{type(exc).__name__}: {exc}",
                })
                conn.commit()
            except Exception:  # noqa: BLE001 — audit is best-effort; the log line above already carries the failure
                logger.exception(
                    "autopromote: could not write audit row for failed candidate %s",
                    candidate_id,
                )
            outcome = CandidateOutcome(candidate_id, "error", f"{type(exc).__name__}: {exc}")
        bucket = {"promoted": "promoted", "human_review": "human_review"}.get(outcome.action, "errors")
        report.counts[bucket] += 1
        report.outcomes.append(outcome)

    logger.info(
        "autopromote pass complete: examined=%d promoted=%d human_review=%d errors=%d",
        report.counts["examined"], report.counts["promoted"],
        report.counts["human_review"], report.counts["errors"],
    )
    return report
