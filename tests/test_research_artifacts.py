"""Committed research artifacts must be machine-parseable.

Gate-gap fix from PR #18 evaluator round 3: a committed .jsonl verification
artifact carried '#' comment lines, which strict JSONL parsers reject — and
the suite stayed green. Research artifacts exist to be an audit trail; an
unparseable audit trail is a silent verification failure. This test parses
every .json and .jsonl file under docs/research/ so the suite goes red the
moment a research artifact is committed broken.
"""

import json
from pathlib import Path

import pytest

RESEARCH_DIR = Path(__file__).resolve().parent.parent / "docs" / "research"

_json_files = sorted(RESEARCH_DIR.glob("**/*.json")) if RESEARCH_DIR.exists() else []
_jsonl_files = sorted(RESEARCH_DIR.glob("**/*.jsonl")) if RESEARCH_DIR.exists() else []


@pytest.mark.parametrize("path", _json_files, ids=lambda p: p.name)
def test_research_json_parses(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, (dict, list)), f"{path.name}: top-level JSON must be an object or array"


@pytest.mark.parametrize("path", _jsonl_files, ids=lambda p: p.name)
def test_research_jsonl_every_line_parses(path):
    errors = []
    parsed = 0
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}:{lineno}: {exc}")
                continue
            if not isinstance(rec, dict):
                errors.append(f"{path.name}:{lineno}: line is {type(rec).__name__}, not an object — bare values cannot carry audit fields")
                continue
            parsed += 1
    assert not errors, f"invalid JSONL lines: {errors}"
    assert parsed > 0, f"{path.name}: no parseable records — an empty audit trail proves nothing"


def test_every_artifact_referenced_by_research_docs_is_committed():
    # Dynamic, not a hard-coded filename list: any docs/research/*.md that
    # mentions a .json/.jsonl artifact must have that artifact committed.
    import re

    # Top-level research docs only: the raw-source appendices in subdirectories
    # quote external API endpoints (e.g. EDGAR's submissions.json) that are not
    # repo artifacts.
    md_files = sorted(RESEARCH_DIR.glob("*.md"))
    if not md_files:
        pytest.skip("no research docs present")
    referenced = set()
    for md in md_files:
        text = md.read_text(encoding="utf-8")
        referenced.update(re.findall(r"[\w./-]+\.jsonl?\b", text))
    artifact_refs = {r.split("/")[-1] for r in referenced if not r.startswith("http")}
    assert artifact_refs, "no artifact references found in any research doc — update this test if artifacts moved"
    committed = {p.name for p in list(_json_files) + list(_jsonl_files)}
    missing = sorted(a for a in artifact_refs if a not in committed and (RESEARCH_DIR / a).suffix in (".json", ".jsonl"))
    assert not missing, f"research docs reference uncommitted artifacts: {missing}"
