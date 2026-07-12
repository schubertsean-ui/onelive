"""Eval / Kaizen learning loop (Layer 4) — the regression-blocking harness.

WHAT THIS IS. A rotating, adversarial eval set (`ai/eval_corpus/cases.jsonl`) plus
a deterministic runner that replays each case against the CURRENT gate
(`worker.trust_gate3.evaluate_gate`), sensor (`worker.sensors.assess_input`), and
— when an AI provider is supplied — the extractor (scored by the ONE existing
scorer, `ai.eval_harness.score_extraction`). No second scorer is written here
(Sunset Law): scoring/aggregation is REUSED wholesale.

WHAT THIS IS NOT. This corpus's job is REGRESSION-BLOCKING, not novel-failure
prediction. The public eval literature (Wu 2026) finds curated eval sets predict
~0% of novel production failures ex-ante yet catch ~87% of known regressions
ex-post. So we make no claim to foresee new failure modes; we assert only that
the adversarial behaviors we have ALREADY understood do not silently regress.
`regressed` is therefore defined against known-good behavior, and we track no
history we cannot substantiate (there is deliberately no fake history file yet).

FIRST-CLASS METRIC: over_suppression. Precision alone rewards a paranoid gate
that rejects everything. We measure the opposite error explicitly — truth wrongly
suppressed: among gate cases whose expected decision is `pass`, the fraction the
gate wrongly sent to hold/escalate; among sensor cases expected to pass, the
fraction wrongly rejected. Control cases (one clean case per kind) exist so this
number is meaningful.

HERMETIC: gate and sensor evaluation need NO network, NO DB, NO AI. Extraction
cases need an ai provider; with `ai=None` they are reported SKIPPED — never
rendered as passed. A malformed corpus case fails LOUD on load (schema
validation), it is never silently skipped.

Deliberately does NOT import worker.promote — this module only evaluates.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai.eval_harness import ExtractionScore, aggregate, score_extraction
from worker.sensors import assess_input
from worker.trust_gate3 import evaluate_gate

DEFAULT_CORPUS = Path(__file__).resolve().parent / "eval_corpus" / "cases.jsonl"

VALID_KINDS = ("extraction", "gate", "sensor")
VALID_DECISIONS = ("pass", "hold", "escalate")


class CorpusError(ValueError):
    """Raised when a corpus case is malformed. Fails LOUD (never skipped)."""


@dataclass
class CaseResult:
    id: str
    kind: str
    passed: bool
    detail: str
    skipped: bool = False  # extraction cases with no ai provider; NEVER == passed


@dataclass
class EvalReport:
    results: List[CaseResult]
    extraction_metrics: Dict[str, Any]
    gate_accuracy: float
    sensor_accuracy: float
    over_suppression: Dict[str, float]  # {"gate": float, "sensor": float}
    regressed: bool = False


# --- corpus loading + schema validation (fail loud) --------------------------
def _validate_case(case: Any, where: str) -> None:
    if not isinstance(case, dict):
        raise CorpusError(f"{where}: case is not a JSON object")
    for key in ("id", "kind", "risk_note", "added"):
        if key not in case or case[key] in (None, ""):
            raise CorpusError(f"{where}: missing required key {key!r}")
    kind = case["kind"]
    if kind not in VALID_KINDS:
        raise CorpusError(f"{where} ({case['id']}): kind {kind!r} not in {VALID_KINDS}")

    if kind == "gate":
        gi = case.get("gate_input")
        if not isinstance(gi, dict) or not isinstance(gi.get("source_classes"), list):
            raise CorpusError(
                f"{where} ({case['id']}): gate case needs gate_input.source_classes (list)")
        if case.get("expected_decision") not in VALID_DECISIONS:
            raise CorpusError(
                f"{where} ({case['id']}): expected_decision must be one of {VALID_DECISIONS}")
    elif kind == "sensor":
        if not isinstance(case.get("source_text"), str):
            raise CorpusError(f"{where} ({case['id']}): sensor case needs source_text (str)")
        if not isinstance(case.get("expected_sensor_ok"), bool):
            raise CorpusError(
                f"{where} ({case['id']}): sensor case needs expected_sensor_ok (bool)")
    else:  # extraction
        if not isinstance(case.get("source_text"), str):
            raise CorpusError(f"{where} ({case['id']}): extraction case needs source_text (str)")
        if "expected" not in case:
            raise CorpusError(f"{where} ({case['id']}): extraction case needs expected")
        if not (case["expected"] is None or isinstance(case["expected"], dict)):
            raise CorpusError(f"{where} ({case['id']}): expected must be object or null")


def load_corpus(path: Path = DEFAULT_CORPUS) -> List[dict]:
    """Load + schema-validate the JSONL corpus. A malformed line or case raises
    CorpusError (loud) — it is never silently skipped."""
    path = Path(path)
    if not path.exists():
        raise CorpusError(f"corpus file not found: {path}")
    cases: List[dict] = []
    seen_ids: set = set()
    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            where = f"{path.name}:{lineno}"
            try:
                case = json.loads(line)
            except json.JSONDecodeError as e:
                raise CorpusError(f"{where}: invalid JSON ({e})") from e
            _validate_case(case, where)
            if case["id"] in seen_ids:
                raise CorpusError(f"{where}: duplicate case id {case['id']!r}")
            seen_ids.add(case["id"])
            cases.append(case)
    if not cases:
        raise CorpusError(f"corpus is empty: {path}")
    return cases


# --- per-kind evaluation -----------------------------------------------------
def _eval_gate(case: dict) -> CaseResult:
    gi = case["gate_input"]
    verdict = evaluate_gate(
        source_classes=gi["source_classes"],
        sxsw_mode=gi.get("sxsw_mode", False),
        extracted=gi.get("extracted"),
        evidence_signals=gi.get("evidence_signals"),
    )
    actual = verdict.decision.value
    expected = case["expected_decision"]
    passed = actual == expected
    detail = f"expected {expected}, got {actual} ({verdict.reason})"
    return CaseResult(case["id"], "gate", passed, detail)


def _eval_sensor(case: dict) -> CaseResult:
    reading = assess_input(text=case["source_text"], content_type=case.get("content_type"))
    expected = case["expected_sensor_ok"]
    passed = reading.ok == expected
    detail = f"expected ok={expected}, got ok={reading.ok} ({reading.reason})"
    return CaseResult(case["id"], "sensor", passed, detail)


def _eval_extraction(case: dict, ai: Optional[Any],
                     scores: List[ExtractionScore]) -> CaseResult:
    if ai is None:
        return CaseResult(case["id"], "extraction", passed=False, skipped=True,
                          detail="skipped: no ai provider supplied (extraction needs one)")
    expected = case["expected"] or {}
    schema = {"fields": sorted(expected.keys())}
    predicted = ai.extract_event_json(case["source_text"], schema)
    score = score_extraction(predicted, expected)
    scores.append(score)
    passed = score.hallucination_rate == 0.0 and score.recall == 1.0
    detail = (f"f1={score.f1:.3f} recall={score.recall:.3f} "
              f"hallucination_rate={score.hallucination_rate:.3f}")
    return CaseResult(case["id"], "extraction", passed, detail)


def run_eval(corpus: List[dict], *, ai: Optional[Any] = None) -> EvalReport:
    """Replay every case against the CURRENT gate/sensor/extractor. Gate & sensor
    need no ai; extraction cases are SKIPPED (not passed) when ai is None."""
    results: List[CaseResult] = []
    extraction_scores: List[ExtractionScore] = []

    for case in corpus:
        kind = case["kind"]
        if kind == "gate":
            results.append(_eval_gate(case))
        elif kind == "sensor":
            results.append(_eval_sensor(case))
        else:
            results.append(_eval_extraction(case, ai, extraction_scores))

    gate_results = [r for r in results if r.kind == "gate"]
    sensor_results = [r for r in results if r.kind == "sensor"]
    gate_accuracy = _accuracy(gate_results)
    sensor_accuracy = _accuracy(sensor_results)

    over_suppression = {
        "gate": _gate_over_suppression(corpus),
        "sensor": _sensor_over_suppression(corpus),
    }

    extraction_metrics: Dict[str, Any] = (
        aggregate(extraction_scores) if extraction_scores else {}
    )

    # Regression-blocking definition (see module docstring): any gate/sensor case
    # failing is a regression. Skipped extraction cases are NOT failures.
    regressed = any(
        (not r.passed) and (not r.skipped) and r.kind in ("gate", "sensor")
        for r in results
    )

    return EvalReport(
        results=results,
        extraction_metrics=extraction_metrics,
        gate_accuracy=gate_accuracy,
        sensor_accuracy=sensor_accuracy,
        over_suppression=over_suppression,
        regressed=regressed,
    )


def _accuracy(results: List[CaseResult]) -> float:
    scored = [r for r in results if not r.skipped]
    if not scored:
        return 1.0
    return sum(1 for r in scored if r.passed) / len(scored)


def _gate_over_suppression(corpus: List[dict]) -> float:
    """Among gate cases whose expected_decision is 'pass', the fraction the gate
    wrongly sent to hold/escalate (truth suppressed)."""
    pass_cases = [c for c in corpus if c["kind"] == "gate" and c["expected_decision"] == "pass"]
    if not pass_cases:
        return 0.0
    wrong = 0
    for c in pass_cases:
        gi = c["gate_input"]
        v = evaluate_gate(
            source_classes=gi["source_classes"],
            sxsw_mode=gi.get("sxsw_mode", False),
            extracted=gi.get("extracted"),
            evidence_signals=gi.get("evidence_signals"),
        )
        if v.decision.value != "pass":
            wrong += 1
    return wrong / len(pass_cases)


def _sensor_over_suppression(corpus: List[dict]) -> float:
    """Among sensor cases expected to pass, the fraction wrongly rejected."""
    pass_cases = [c for c in corpus if c["kind"] == "sensor" and c["expected_sensor_ok"] is True]
    if not pass_cases:
        return 0.0
    wrong = 0
    for c in pass_cases:
        r = assess_input(text=c["source_text"], content_type=c.get("content_type"))
        if not r.ok:
            wrong += 1
    return wrong / len(pass_cases)


# --- reporting ---------------------------------------------------------------
def format_report(report: EvalReport) -> str:
    lines: List[str] = []
    lines.append("=== OneLive Eval / Kaizen Loop ===")
    n = len(report.results)
    passed = sum(1 for r in report.results if r.passed and not r.skipped)
    failed = sum(1 for r in report.results if not r.passed and not r.skipped)
    skipped = sum(1 for r in report.results if r.skipped)
    lines.append(f"cases: {n}  passed: {passed}  failed: {failed}  skipped: {skipped}")
    lines.append(f"gate_accuracy:   {report.gate_accuracy:.3f}")
    lines.append(f"sensor_accuracy: {report.sensor_accuracy:.3f}")
    lines.append(f"over_suppression: gate={report.over_suppression['gate']:.3f} "
                 f"sensor={report.over_suppression['sensor']:.3f}")
    if report.extraction_metrics:
        m = report.extraction_metrics
        lines.append(f"extraction: f1={m.get('f1')} "
                     f"hallucination_rate={m.get('hallucination_rate')} "
                     f"n={m.get('n_examples')}")
    else:
        lines.append("extraction: SKIPPED (no ai provider)")
    lines.append("")
    for r in report.results:
        status = "SKIP" if r.skipped else ("PASS" if r.passed else "FAIL")
        lines.append(f"  [{status}] {r.kind:10s} {r.id}")
        if not r.passed and not r.skipped:
            lines.append(f"         -> {r.detail}")
    lines.append("")
    lines.append("REGRESSED" if report.regressed else "no regression")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    corpus = load_corpus()
    report = run_eval(corpus, ai=None)
    print(format_report(report))
    return 1 if report.regressed else 0


if __name__ == "__main__":
    sys.exit(main())
