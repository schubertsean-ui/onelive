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
                json.loads(line)
                parsed += 1
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}:{lineno}: {exc}")
    assert not errors, f"invalid JSONL lines: {errors}"
    assert parsed > 0, f"{path.name}: no parseable records — an empty audit trail proves nothing"


def test_artifacts_exist_when_report_references_them():
    report = RESEARCH_DIR / "PR_AGGREGATOR_RESEARCH.md"
    if not report.exists():
        pytest.skip("report not present")
    text = report.read_text(encoding="utf-8")
    referenced = [
        name
        for name in (
            "PR_AGGREGATOR_RESEARCH_verification.json",
            "PR_AGGREGATOR_RESEARCH_verification_votes.jsonl",
        )
        if name in text
    ]
    assert referenced, "report no longer references its verification artifacts — update this test's list"
    for name in referenced:
        assert (RESEARCH_DIR / name).exists(), f"report references {name} but it is not committed"
