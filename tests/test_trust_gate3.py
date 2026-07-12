"""Tests for the three-way trust gate (worker/trust_gate3.py).

Pure-logic, no DB, no network: evaluate_gate only wraps multi_confirm_gate
and inspects plain dicts.
"""
from worker.trust_gate3 import GateDecision, evaluate_gate


def test_pass_on_anchor_and_clean_evidence():
    verdict = evaluate_gate(
        source_classes=["ticketing"],
        extracted={"start_time": "2026-07-11T20:00:00", "is_private_rsvp": False},
        evidence_signals={"start_times": ["2026-07-11T20:00:00"]},
    )
    assert verdict.decision is GateDecision.PASS
    assert verdict.base.ok_to_promote is True


def test_escalate_on_conflicting_start_time():
    verdict = evaluate_gate(
        source_classes=["ticketing"],
        extracted={"start_time": "2026-07-11T20:00:00"},
        evidence_signals={"start_times": ["2026-07-11T20:00:00", "2026-07-11T21:30:00"]},
    )
    assert verdict.decision is GateDecision.ESCALATE
    assert "conflicting start_time" in verdict.reason


def test_escalate_on_validation_error_provenance():
    verdict = evaluate_gate(
        source_classes=["venue_calendar"],
        extracted={"_provenance": {"validation_error": True}},
        evidence_signals={},
    )
    assert verdict.decision is GateDecision.ESCALATE
    assert "validation_error" in verdict.reason


def test_escalate_on_private_rsvp():
    verdict = evaluate_gate(
        source_classes=["claimed_upload"],
        extracted={"is_private_rsvp": True},
        evidence_signals={},
    )
    assert verdict.decision is GateDecision.ESCALATE
    assert "private" in verdict.reason.lower()


def test_escalate_on_dedupe_ambiguity_hint():
    verdict = evaluate_gate(
        source_classes=["festival_feed"],
        extracted={},
        evidence_signals={"dedupe_ambiguous": True},
    )
    assert verdict.decision is GateDecision.ESCALATE
    assert "dedupe" in verdict.reason.lower()


def test_hold_on_single_non_anchor():
    verdict = evaluate_gate(
        source_classes=["social"],
        extracted={},
        evidence_signals={},
    )
    assert verdict.decision is GateDecision.HOLD
    assert verdict.base.ok_to_promote is False


def test_hold_never_escalates_even_with_conflict_signals():
    # If the base gate is not satisfied, we HOLD regardless of conflict
    # signals — ESCALATE is reserved for "promotable-by-count but ambiguous",
    # not for every candidate carrying a conflict signal.
    verdict = evaluate_gate(
        source_classes=["social"],
        extracted={"is_private_rsvp": True},
        evidence_signals={"start_times": ["a", "b"]},
    )
    assert verdict.decision is GateDecision.HOLD


def test_pass_requires_two_non_anchor_sources():
    verdict = evaluate_gate(
        source_classes=["social", "local_media"],
        extracted={},
        evidence_signals={},
    )
    assert verdict.decision is GateDecision.PASS


def test_sxsw_mode_forwarded_to_base_gate():
    # Two non-anchor sources is enough normally but not under sxsw_mode.
    verdict = evaluate_gate(
        source_classes=["social", "local_media"],
        sxsw_mode=True,
        extracted={},
        evidence_signals={},
    )
    assert verdict.decision is GateDecision.HOLD


def test_single_non_null_start_time_is_not_a_conflict():
    # One evidence row stating a start_time and others silent about it must
    # not be misread as a conflict.
    verdict = evaluate_gate(
        source_classes=["ticketing"],
        extracted={},
        evidence_signals={"start_times": ["2026-07-11T20:00:00", None, None]},
    )
    assert verdict.decision is GateDecision.PASS


def test_gate_never_imports_promote():
    import ast
    import worker.trust_gate3 as mod

    tree = ast.parse(open(mod.__file__).read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any(m.startswith("worker.promote") for m in imported)
