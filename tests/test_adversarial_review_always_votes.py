"""Independent review is world-class only if it actually runs.

Two holes this file locks:

1. Web compile was skipped when the diff listed no web/ files. Production
   still compiles the full tree. That is how #260's unclosed fetch reached
   Vercel on a later docs merge, and how a red Vercel check was misread
   as noise.

2. tools/validate going red (including STATE.md staleness — ceremony)
   aborted the job BEFORE the independent evaluator voted. A review that
   does not run is not a review.

Validate still binds: the workflow fails after the verdict if validate
was red. Neither is a skip of the other.
"""
from __future__ import annotations

from pathlib import Path

WF = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "adversarial-review.yml"


def test_evaluator_packet_always_typechecks_and_builds_web():
    text = WF.read_text()
    assert "no web/ files in this diff — web checks not applicable" not in text
    assert "npx tsc --noEmit" in text
    assert "npm run build" in text
    # The compile is not inside a web/-only skip.
    skip_idx = text.find("Clerk-keyed rebuild skipped")
    tsc_idx = text.find("npx tsc --noEmit")
    assert tsc_idx != -1 and (skip_idx == -1 or tsc_idx < skip_idx)


def test_validate_red_does_not_skip_the_evaluator():
    text = WF.read_text()
    assert "id: validate" in text
    assert "Independent evaluator still runs" in text or "independent evaluator still runs" in text
    assert "Machine gates still bind" in text
    eval_idx = text.find("Independent evaluator (APPROVE required)")
    bind_idx = text.find("Machine gates still bind")
    assert eval_idx != -1 and bind_idx != -1 and eval_idx < bind_idx
