"""PURE DATA: model routing values + the extraction ratification flag.

This module must stay a pure data module — optional docstring plus
constant-literal assignments ONLY. Logic lives in tools/model_router.py,
which imports these values. That split is what lets a release gate treat
routing VALUES as certifiable data (AST-extracted, never executed) while
router LOGIC changes go through the harness-merge path (evaluator r13).

Cheapest-capable defaults. A project ratifies its own table in
docs/MODEL_ROUTING.md and changes the values THERE first — this table
implements the doc, not the other way around. Cost discipline: each stage
takes the cheapest tier that PASSES the same gates; a tier is earned by
passing them and lost the same way.

EXTRACTION_THRESHOLD_RATIFIED gates the `extraction` stage fail-closed.
The kernel ships it False DELIBERATELY: a template has never sat an
attended exam, so its extraction stage must route nowhere. A project flips
it to the literal True only as the RECORD of a passed exam — evidence bound
to the exact head commit, prompt hash, routed model, golden-set hash and
dependency lock — never to unblock a run. It returns to False the moment
the routed model fails, and the resolver checks the literal `True`, not
truthiness, so a misconfigured "False"/"yes"/1 keeps extraction CLOSED.
"""

STAGE_MODELS = {
    "mechanical": "claude-haiku-4-5",
    "standard": "claude-sonnet-4-6",
    "critical": "claude-opus-4-8",
    "extraction": "claude-opus-4-8",
    # Non-Claude by charter — cost never downgrades the grader.
    "evaluator": "gpt-5.5",
}

EXTRACTION_THRESHOLD_RATIFIED = False
