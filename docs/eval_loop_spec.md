# Eval / Kaizen Learning Loop — Build Spec (Layer 4)

Closes agent-loop research §9 remaining gaps: a rotating, adversarial,
contamination-resistant eval set that tracks precision, **recall/false-negatives
(over-suppression) as a first-class metric**, and frames the eval set's job as
**regression-blocking, not novel-failure-prediction**. REUSE the existing scorer
— do NOT write a second one (Sunset Law: one logical invariant, one physical
representation).

## REUSE (do not duplicate)
- `ai/eval_harness.py::score_extraction / aggregate / ExtractionScore` already
  compute precision, recall, f1, hallucination_rate. Call these. Do NOT
  reimplement scoring.
- `worker/trust_gate3.py::evaluate_gate` + `GateDecision` — the gate under test
  for the gate-eval half.
- `worker/sensors.py::assess_input` — for sensor-level adversarial cases.

## BUILD

### 1. `ai/eval_corpus/` — the rotating adversarial eval set (data, not code)
A directory of JSON case files. Each case is one adversarial scenario harvested
from a real or realistic failure mode. Schema (one JSON object per file, or a
JSON array in a single `cases.jsonl`; choose JSONL for easy rotation/appending):
```
{
  "id": "cancelled-event-still-listed-001",
  "kind": "extraction" | "gate" | "sensor",
  "risk_note": "why this case is adversarial / what silent failure it targets",
  "added": "2026-07-11",
  "source_text": "...the raw source blurb the pipeline would see...",
  "content_type": "text/html",
  # for kind=extraction: the ground-truth expected extraction
  "expected": { "title": ..., "start_time": ..., ... } | null,
  # for kind=gate: inputs to evaluate_gate + expected decision
  "gate_input": {"source_classes": [...], "sxsw_mode": false,
                 "extracted": {...}, "evidence_signals": {...}},
  "expected_decision": "pass" | "hold" | "escalate",
  # for kind=sensor: expected sensor outcome
  "expected_sensor_ok": true | false
}
```
Seed with at least 12 cases spanning the documented adversarial classes:
ambiguous/cancelled/rescheduled event, contradictory source pages (conflicting
start_time -> must ESCALATE), stale-but-plausible listing, private/RSVP event
(-> ESCALATE), truncated fetch (-> sensor reject), mojibake (-> sensor reject),
prompt-injection in source (-> sensor reject), boilerplate-only shell (-> sensor
reject), single non-anchor source (-> HOLD), clean anchor event (-> PASS,
control), a hallucination-bait case (source omits a field the model is tempted
to fill), and a near-duplicate/dedupe-ambiguity case (-> ESCALATE). Include at
least one clean "control" case per kind so a gate that rejects everything does
NOT score perfectly (guards the over-suppression blind spot).

### 2. `ai/eval_loop.py` — the runner
```
@dataclass CaseResult: id; kind; passed: bool; detail: str
@dataclass EvalReport: results: list[CaseResult]; extraction_metrics: dict;
    gate_accuracy: float; sensor_accuracy: float;
    over_suppression: dict  # see below
def load_corpus(path=DEFAULT_CORPUS) -> list[dict]
def run_eval(corpus, *, ai=None) -> EvalReport   # ai only needed for kind=extraction;
                                                 # gate/sensor cases need NO ai, NO network, NO DB
def format_report(report) -> str
```
- kind=gate: call evaluate_gate with gate_input, compare .decision.value to
  expected_decision.
- kind=sensor: call assess_input, compare .ok to expected_sensor_ok.
- kind=extraction: if `ai` is provided, extract and score with score_extraction;
  if `ai is None`, SKIP extraction cases (report them as skipped, not passed —
  never let "skipped" look like "passed").
- **over_suppression** (first-class, the §9 differentiator): among gate cases
  whose expected_decision is `pass`, the fraction the gate WRONGLY sent to
  hold/escalate; among sensor cases whose expected_sensor_ok is true, the
  fraction wrongly rejected. This is the false-negative / wrongly-suppressed-
  truth metric the public eval literature under-measures. Report it explicitly.
- **Regression-blocking framing:** `run_eval` returns a boolean `regressed` =
  any case that previously passed now fails. For now (no history store yet),
  define regressed = any control/clean case failing OR any gate/sensor case
  failing, and document in the module docstring that the corpus's job is
  regression-blocking, not predicting novel failures (Wu 2026: 0% ex-ante / 87%
  ex-post). Track nothing you can't yet substantiate — do not fake a history file.

### 3. `tests/test_eval_loop.py` (hermetic; gate/sensor cases need no ai)
- The seeded corpus loads and every case has required keys for its kind
  (schema-validate the corpus itself — a malformed case must fail LOUD, not be
  skipped silently).
- run_eval over the real seeded corpus with ai=None: all gate and sensor cases
  PASS (this proves the current gate+sensor satisfy the adversarial
  set — sabotage the corpus in a test by flipping one expected_decision and
  assert run_eval then reports a failure, proving the eval can fail).
- over_suppression is 0.0 on the seeded corpus (the control cases pass).
- extraction cases are reported as skipped (not passed) when ai=None.
- A CLI entrypoint `python -m ai.eval_loop` prints format_report and exits 0
  when no regression, 1 when regressed (mirror trust_gate.py's exit convention).

## Non-negotiables
No second scorer. No network/DB in gate/sensor eval paths. Malformed corpus
fails loud. "Skipped" never rendered as "passed". Every new case carries a
risk_note (why it's adversarial) so the corpus is self-documenting. Full suite +
`python tools/trust_gate.py` green before done. `ai/eval_loop.py` must NOT import
worker.promote.
