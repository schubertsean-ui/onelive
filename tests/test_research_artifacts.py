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


def test_cited_source_appendices_exist_and_are_nonempty():
    """The market-analysis doc cites raw agent-report appendices as its
    provenance trail ([A]-[H] → market_analysis_sources/<Letter>_*.md).
    Every cited appendix file must be committed and non-trivially non-empty —
    a missing or gutted appendix would silently orphan the doc's citations."""
    import re

    analysis = RESEARCH_DIR / "PR_AGGREGATOR_MARKET_ANALYSIS.md"
    if not analysis.exists():
        pytest.skip("market analysis not present")
    text = analysis.read_text(encoding="utf-8")
    referenced_files = set(re.findall(r"market_analysis_sources/([\w-]+\.md)", text))
    assert referenced_files, "analysis doc no longer names its appendix files — update this test"
    srcdir = RESEARCH_DIR / "market_analysis_sources"
    for name in sorted(referenced_files):
        p = srcdir / name
        assert p.exists(), f"analysis cites {name} but it is not committed"
        assert len(p.read_text(encoding="utf-8").strip()) > 500, f"{name} is suspiciously small for a source appendix"
    # every bracketed appendix letter used in the analysis must map to a committed file
    cited_letters = set(re.findall(r"\[([A-H])\]", text))
    on_disk_letters = {p.name.split("_")[0] for p in srcdir.glob("*.md")} if srcdir.exists() else set()
    missing = sorted(cited_letters - on_disk_letters)
    assert not missing, f"analysis cites appendix letters with no committed file: {missing}"


def test_no_source_dated_after_compilation():
    """Evaluator catch (PR #18 round 8): an appendix cited a source whose
    publication date post-dated the compilation date — a time-incoherent
    (hallucinated or forward-dated) citation. Rule: no ISO date later than the
    file's compilation date may appear in a committed source appendix.
    (Forward-looking regulatory deadlines in these files are written as prose
    dates, so a strict ISO check does not false-positive on them.)"""
    import datetime
    import re

    srcdir = RESEARCH_DIR / "market_analysis_sources"
    if not srcdir.exists():
        pytest.skip("no source appendices present")
    violations = []
    for md in sorted(srcdir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        m = re.search(r"Compiled (\d{4}-\d{2}-\d{2})", text)
        assert m, f"{md.name}: missing 'Compiled YYYY-MM-DD' header — the date-sanity gate needs it"
        compiled = datetime.date.fromisoformat(m.group(1))
        for lineno, line in enumerate(text.splitlines(), start=1):
            future = []
            for iso in re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", line):
                try:
                    d = datetime.date.fromisoformat(iso)
                except ValueError:
                    continue
                if d > compiled:
                    future.append(iso)
            if not future:
                continue
            # A future-dated citation may remain ONLY as preserved disputed
            # evidence: the line must carry an explicit REFUTED verdict AND
            # must still contain the original source URL — a verdict without
            # the evidence is redaction, which the repo bar forbids.
            if "REFUTED" not in line:
                violations.append(f"{md.name}:{lineno}: cites {future} after compilation {compiled} with no REFUTED verdict")
            elif "http" not in line and "see row" not in line:
                violations.append(f"{md.name}:{lineno}: REFUTED line lost its original source URL — evidence must be preserved, not redacted")
    assert not violations, f"time-incoherent citations: {violations}"


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
    # keep any path component so same-basename artifacts in different
    # subdirectories cannot mask each other (evaluator r9 nit)
    artifact_refs = {r.removeprefix("docs/research/") for r in referenced if not r.startswith("http")}
    assert artifact_refs, "no artifact references found in any research doc — update this test if artifacts moved"
    committed = {str(p.relative_to(RESEARCH_DIR)) for p in list(_json_files) + list(_jsonl_files)}
    committed |= {p.name for p in list(_json_files) + list(_jsonl_files) if p.parent == RESEARCH_DIR}
    missing = sorted(a for a in artifact_refs if a not in committed and (RESEARCH_DIR / a).suffix in (".json", ".jsonl"))
    assert not missing, f"research docs reference uncommitted artifacts: {missing}"
