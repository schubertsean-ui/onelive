"""PURE DATA: model routing values + the extraction ratification flag.

This module must stay a pure data module — optional docstring plus
constant-literal assignments ONLY (enforced by tools/pure_data.py; the
exam gate refuses to certify it otherwise). Logic lives in
tools/model_router.py, which imports these values. That split is what
lets the release gate treat routing VALUES as subject-certifiable data
(AST-extracted, never executed) while router LOGIC changes go through
the harness-merge path (evaluator r13).

Cheapest-capable defaults, ratified via docs/MODEL_ROUTING.md. Change
them THERE first — this table implements the doc, not the other way
around.

Extraction escalation history (cost-discipline rule 2, both logged):
  Cheap->Standard 2026-07-15: claude-haiku-4-5 failed the golden-set
  exam 3 consecutive cycles after full key/prompt calibration
  (instruction-following residual, not knowledge).
  Standard->Critical 2026-07-15: claude-sonnet-4-6 failed 4 consecutive
  cycles, the last two oscillating at 2.3-2.7% (bar: 1%) on a coherent,
  de-contaminated spec — an instruction-following ceiling. The tier is
  earned by passing the same gate and lost the same way: once the gate
  opens, BOTH cheaper tiers re-sit the exam via workflow_dispatch and
  extraction routes to the cheapest passer — a standing, tracked
  policy: the de-escalation exam procedure is queued in TODOS.md and the
  routing policy doc (docs/MODEL_ROUTING.md).

EXTRACTION_THRESHOLD_RATIFIED (R-013 status 2026-07-17): True is STAGED
in PR #31, which the release gate holds red until a verified attended
exam run EXISTS — corrected gate: rate bar AND both >=300 fact floors,
zero injections, evidence bound to the PR's exact head commit, prompt
hash, routed model, golden-set hash, harness-manifest hash, and
dependency lock. The passing run's id is recorded in the PR body and
merge commit, not here: evidence binds the head SHA, so writing the id
into the tree after the run would create a new head the evidence no
longer certifies. R-013 itself stays OPEN until a commit cites that
run + verifier output (records describe what exists). Historical
context: routed claude-opus-4-8 passed the RATE bar on exam cycle 11
(0.0068 <= 0.01, recall 0.9702, zero injections — run 29424147665) but
asserted 295 < 300 facts; only a corrected-gate attended run counts.
Once open, the gate remains in force on every extraction-surface PR,
and the flag returns to False if the routed model ever fails (KAIZEN
§M7 one-way ratchet governs the threshold).
"""

STAGE_MODELS = {
    "mechanical": "claude-haiku-4-5",
    "standard": "claude-sonnet-4-6",
    "critical": "claude-opus-4-8",
    "extraction": "claude-opus-4-8",
    # Non-Claude by charter (§0.2) — cost never downgrades the grader.
    "evaluator": "gpt-5.5",
}

# False as of the 2026-08-03 re-certification sitting (founder-directed:
# prompt caching + usage capture entered ai/claude_provider.py, a
# manifest-bound file, so per the charter's compensated exception this PR
# CLOSES extraction fail-closed at merge; the standing three-step re-opens
# it: founder's attended exam on the new harness -> authenticated record PR
# -> head-bound flag-flip PR back to True).
EXTRACTION_THRESHOLD_RATIFIED = False
