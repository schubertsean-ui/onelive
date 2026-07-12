# Orchestrator-as-Harness — Build Spec (Option A, world-class loop)

The orchestrator IS the Loop/Harness. It is not a plain pipeline runner that we
decorate later. Build it as the three-layer Sensors -> Harness -> Loop structure
we defined, with a three-way pass/fail/ESCALATE gate and deterministic-replay
logging from the first line. Everything below wires REAL existing functions; do
not stub or re-implement them.

## Existing building blocks (wire these, do not rewrite)
- `worker/fetch/http_fetch.py::fetch_url(*, source_id, url, ...)` -> dict with
  status ('ok'|'not_modified'), raw_fetch_id, content_hash, storage_ref, bytes.
- `ai/provider.py::AIProvider` protocol; real impl `ai/claude_provider.py`,
  stub `ai/bedrock_provider.py::BedrockProvider(client=None, model_id="stub")`.
- `worker/ai_extract.py::extract_candidate(*, ai, text, source_class, source_name,
  source_url, sxsw_mode=False, source_id=None) -> candidate_id`.
- `worker/gating.py::multi_confirm_gate(source_classes, sxsw_mode) -> GateResult`
  (fields: ok_to_promote, status, reason, required_next; ANCHOR_CLASSES set).
- `worker/promote.py::promote_candidate(candidate_id) -> event_id` (re-checks the
  gate internally; raises ValueError if not ok_to_promote or on duplicate).
- `worker/candidate_store.py::list_candidate_source_classes(candidate_id)`.
- DB DSN via env `ONELIVE_DB_DSN`. Sources live in table `source` (43 rows).

## What to BUILD (new files)

### 1. `worker/trust_gate3.py` — the three-way gate (Harness core)
Wrap, do NOT replace, `multi_confirm_gate`. The existing gate is 2-way
(ok_to_promote true/false). Trust requires a THIRD outcome: ESCALATE to a human.
```
class GateDecision(enum): PASS, HOLD, ESCALATE
@dataclass GateVerdict: decision: GateDecision; reason: str;
           base: GateResult; signals: dict
def evaluate_gate(*, source_classes, sxsw_mode, extracted, evidence_signals) -> GateVerdict
```
Rules (deterministic, documented inline, each tied to trust):
- PASS: base gate ok_to_promote AND no conflict signals -> safe to promote.
- ESCALATE (the trust-critical branch Karpathy's "never ask a human" rule would
  WRONGLY skip): promotable-by-count BUT conflicting/ambiguous evidence, e.g.
  * conflicting start_time across evidence, or
  * anchor present but extraction flagged validation_error in provenance, or
  * private/RSVP event (needs human judgement on publishing), or
  * dedupe-ambiguity hint.
  ESCALATE means: create/keep candidate in 'needs_review', write an audit_log
  'gate_escalated' row with the reason, and DO NOT auto-promote.
- HOLD: base gate not ok_to_promote (insufficient corroboration) -> wait for more
  evidence; not an error, not an escalation.
This gate NEVER promotes by itself. Promotion stays in promote.py behind its own
gate re-check (defense in depth).

### 2. `worker/replay_log.py` — deterministic-replay logging (NON-deferrable)
Append-only JSONL structured record of every loop step so any promotion decision
is auditable and re-runnable. One record per (run_id, source, stage).
```
@dataclass ReplayRecord: run_id, ts, source_id, source_name, stage, inputs_digest,
    outputs_digest, decision, detail
def new_run_id() -> str            # uuid4
def log_step(record: ReplayRecord) -> None   # append to ONELIVE_REPLAY_LOG
                                             # (default var/replay/<run_id>.jsonl)
```
inputs_digest/outputs_digest = sha256 of the canonical json of the relevant
payload (so a replay can verify determinism without storing PII-heavy raw text).
Must be import-safe with no DB and no network. Fail LOUDLY if the log dir is
unwritable (never silently drop audit records).

### 3. `worker/sensors.py` — input-quality / context-hygiene sensor
Gate fetch->extract: reject obviously junk input before spending an AI call.
```
@dataclass SensorReading: ok: bool; reason: str; signals: dict
def assess_input(*, text: str, content_type: str | None) -> SensorReading
```
Checks (deterministic): non-empty after strip; min length (e.g. >= 40 chars);
looks like text not binary; not a known error/placeholder page. ok=False short-
circuits the loop for that source with a logged 'sensor_rejected' replay step
(this is a normal outcome, not a failure).

### 4. `worker/orchestrator.py` — the Loop
```
@dataclass SourceResult: source_id, source_name, stage_reached, decision, detail
@dataclass RunReport: run_id, started, finished, results: list[SourceResult],
    counts: dict   # {'fetched':.., 'extracted':.., 'passed':.., 'escalated':..,
                   #  'held':.., 'sensor_rejected':.., 'errors':..}
def run_loop(*, ai: AIProvider, sources: list[dict], sxsw_mode=False,
             promote: bool=False, dsn: str|None=None) -> RunReport
```
For each source dict {source_id, name, url, source_class}:
  1. fetch (fetch_url) -> log_step. not_modified -> skip w/ logged step.
  2. read stored bytes -> text; sensors.assess_input -> if not ok, log
     'sensor_rejected' and continue.
  3. extract_candidate(...) -> candidate_id -> log_step 'extracted'.
  4. evidence_signals = gather (source_classes via list_candidate_source_classes,
     plus extracted fields) -> evaluate_gate -> log_step with decision.
  5. on PASS and promote=True: promote_candidate(candidate_id); on ValueError
     (e.g. duplicate) DOWNGRADE to ESCALATE (never crash the loop, never silently
     swallow) and log it. on PASS and promote=False: leave for ops, log 'would_promote'.
  6. ESCALATE/HOLD: log, leave candidate in needs_review.
Failure semantics (project precedent): config/structural errors fail LOUD and
abort the run with a clear message; per-source transient errors are caught,
logged as 'error' in that source's result + replay, and the loop CONTINUES (one
bad source must not take down the run). Never let "we failed" look like "nothing
there".
Ratchet (dev-time only, per red-team): the orchestrator does NOT self-modify;
the Karpathy ratchet governs how WE build/iterate it (commit on green, revert on
regression), and must never leak into the product gate — do NOT add any
"auto-approve to keep going" behaviour. Escalation to humans is correct here.

### 5. `worker/run_once.py` — replace the stub main
Keep a stub-provider path for offline smoke, but drive it THROUGH run_loop with a
single in-memory source so the orchestrator itself is exercised. Add a `--real`
flag that would use ClaudeProvider + real sources when env is configured (guarded;
must not require network/DB to import).

## TESTS (must be hermetic; no network, no DB) — tests/test_orchestrator.py + others
- gate3: PASS on anchor+clean; ESCALATE on conflicting start_time; ESCALATE on
  validation_error provenance; ESCALATE on private_rsvp; HOLD on single non-anchor.
- replay_log: writes JSONL, digests stable for same input, fails loud on unwritable dir.
- sensors: rejects empty/too-short/binary; accepts a real listing blurb.
- orchestrator: with a FAKE ai provider + monkeypatched fetch/extract/promote/store
  (no real IO), a 3-source run produces correct counts; a transient error in one
  source does not abort the others; promote=True path calls promote and downgrades
  a duplicate ValueError to ESCALATE.
- Must pass `python tools/trust_gate.py` (no dynamic SQL; orchestrator/sensors/gate3
  must NOT import worker.promote except orchestrator.py which is added to the
  promote allowlist in tools/trust_gate.py in THIS change).

## Non-negotiables (user quality bar)
No "ok" code, no TODO-for-later, no swallowed errors, no dead code, no red tests.
Every new module has a docstring tying it to the trust vision. Full suite green
locally (python -m pytest -q) AND trust gate green before you report done.
