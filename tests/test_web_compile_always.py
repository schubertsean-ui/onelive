"""The compile gate must run on every PR, not only when web/ changes.

#260 merged an unclosed fetch(). visual-regression is path-filtered to
web/**. adversarial tsc only runs when the diff lists web/. A later
docs PR still compiled that file on Vercel and production went red.
This workflow is the lock so that cannot happen again.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "web-compile.yml"


def test_web_compile_workflow_has_no_path_filter():
    text = WF.read_text()
    header, _, _jobs = text.partition("jobs:")
    assert "paths:" not in header, (
        "A path filter is how a broken promoted.ts shipped. "
        "This job compiles the app on every PR."
    )
    assert "npx tsc --noEmit" in text
    assert "npm run build" in text
    assert "pull_request" in header
    assert "master" in header
