"""Committed research artifacts must be machine-parseable and trust-coherent.

Built up across PR #18 evaluator rounds 3-15. Gates, each with the failure it
mechanizes against and NEGATIVE fixtures proving it can fail:
- parseability: every docs/research .json/.jsonl parses; JSONL lines are objects
- cited artifacts exist and are non-empty (appendix letters resolve to files)
- evidence preservation: refuted citations are pinned in a registry
  (REFUTED_CITATIONS.json) by ORIGINAL url+date; the original must remain
  verbatim on a REFUTED-marked line — substitution (any other URL) or
  redaction fails
- date sanity: publication-style dates (ISO, URL-slug, and prose day-dates
  outside an explicit event-word context) must not post-date compilation
- sizing arithmetic: count x price = result claims recompute (range and point
  forms, M/B units). LIMITATION, stated not hidden: non-numeric counts
  ("S&P-500-class x $10-25k") are not mechanically checkable and remain the
  evaluator's/editor's job.
"""

import datetime
import json
import re
from pathlib import Path

import pytest

RESEARCH_DIR = Path(__file__).resolve().parent.parent / "docs" / "research"
SOURCES_DIR = RESEARCH_DIR / "market_analysis_sources"
REGISTRY_PATH = SOURCES_DIR / "REFUTED_CITATIONS.json"

_json_files = sorted(RESEARCH_DIR.glob("**/*.json")) if RESEARCH_DIR.exists() else []
_jsonl_files = sorted(RESEARCH_DIR.glob("**/*.jsonl")) if RESEARCH_DIR.exists() else []

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}

# Words that mark a future date as an EVENT/deadline (legitimate), not a
# publication date. Explicit and reviewable — extending this list is a
# reviewed change, not a silent loosening.
EVENT_CONTEXT = re.compile(
    r"appl(?:y|ies|ied)|effective|deadline|due|compliance|begins?|starts?|"
    r"until|by |from |live |in force|phase|portal|collected?|period|"
    r"expect|planned|target|mandate|wave|comment|postponed|delayed|"
    r"announced for|scheduled", re.IGNORECASE)


# ---------------------------------------------------------------- helpers

def _publication_style_dates(line: str):
    """ISO literals, URL-slug dates, and prose day-dates (e.g. 'Jul 28, 2026')."""
    out = []
    for iso in re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", line):
        out.append((iso, "iso"))
    for g in re.findall(r"https?://\S*?/(\d{4})/(\d{2})/(\d{2})", line):
        out.append(("-".join(g), "url"))
    for mon, day, year in re.findall(
            r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\b", line):
        out.append((f"{year}-{MONTHS[mon.lower()]:02d}-{int(day):02d}", "prose"))
    dated = []
    for iso, kind in out:
        try:
            dated.append((datetime.date.fromisoformat(iso), kind))
        except ValueError:
            continue
    return dated


def check_dates(text: str, compiled: datetime.date, registry_entries):
    """Return violations for time-incoherent publication dates in `text`.

    Registry semantics: every refuted future-dated citation must keep its
    ORIGINAL url and date together, verbatim, on a REFUTED-marked line.
    """
    violations = []
    lines = text.splitlines()
    # registry originals still present?
    for entry in registry_entries:
        if not any("REFUTED" in ln and entry["original_url"] in ln and entry["date"] in ln
                   for ln in lines):
            violations.append(
                f"registry citation {entry['date']} {entry['original_url']} is missing, "
                f"redacted, or substituted — original evidence must remain verbatim on a REFUTED line")
    registry_dates = {e["date"] for e in registry_entries}
    registry_urls = {e["original_url"] for e in registry_entries}
    for lineno, line in enumerate(lines, start=1):
        future = [(d, kind) for d, kind in _publication_style_dates(line) if d > compiled]
        # prose future dates in an explicit event context are legitimate
        future = [f for f in future if not (f[1] == "prose" and EVENT_CONTEXT.search(line))]
        if not future:
            continue
        if "REFUTED" not in line:
            violations.append(
                f"line {lineno}: cites future publication-style date(s) "
                f"{[d.isoformat() for d, _ in future]} (compiled {compiled}) with no REFUTED verdict")
            continue
        # REFUTED lines: every future date must be a registered refuted citation,
        # and evidence lines must carry the registered ORIGINAL url (any other
        # URL is substitution).
        for d, _kind in future:
            if d.isoformat() not in registry_dates:
                violations.append(
                    f"line {lineno}: REFUTED future date {d} is not in REFUTED_CITATIONS.json — "
                    f"register the original citation, never just annotate")
        if "http" in line and not any(u in line for u in registry_urls):
            violations.append(
                f"line {lineno}: REFUTED line carries a URL that is not the registered original — "
                f"evidence substitution")
    return violations


ARITH_RANGE = re.compile(
    r"~?([\d,]+k?)(?:–([\d,]+k?))?\s+(?:orgs|companies|issuers)[^×\n]*×\s*"
    r"\$([\d.]+)–([\d.]+)k[^=≈\n]*[=≈][^$\n]*\$([\d.]+)–([\d.]+)([MB])")
ARITH_POINT = re.compile(
    r"~?([\d,]+k?)\s*(?:orgs|companies|issuers)?\s*×\s*\$([\d.]+)k\s*(?:/\w+)?\s*"
    r"(?:is|=|≈)\s*(?:a\s*)?\$([\d.]+)([MB])\b")


def check_arithmetic(text: str):
    """Recompute count x price = result claims (range and point forms)."""
    def parse_count(tok):
        tok = tok.replace(",", "")
        return int(tok[:-1]) * 1000 if tok.endswith("k") else int(tok)

    def in_millions(val, unit):
        return val * (1000 if unit == "B" else 1)

    checked, errors = 0, []
    for m in ARITH_RANGE.finditer(text):
        lo_n = parse_count(m.group(1))
        hi_n = parse_count(m.group(2)) if m.group(2) else lo_n
        lo_p, hi_p = float(m.group(3)), float(m.group(4))
        lo_r = in_millions(float(m.group(5)), m.group(7))
        hi_r = in_millions(float(m.group(6)), m.group(7))
        want_lo, want_hi = lo_n * lo_p / 1000, hi_n * hi_p / 1000
        checked += 1
        if abs(want_lo - lo_r) > 1e-6 or abs(want_hi - hi_r) > 1e-6:
            errors.append(f"'{m.group(0)[:80]}': states {lo_r}-{hi_r}M, computes {want_lo:g}-{want_hi:g}M")
    for m in ARITH_POINT.finditer(text):
        n = parse_count(m.group(1))
        p = float(m.group(2))
        r = in_millions(float(m.group(3)), m.group(4))
        checked += 1
        if abs(n * p / 1000 - r) > 1e-6:
            errors.append(f"'{m.group(0)[:80]}': states {r}M, computes {n * p / 1000:g}M")
    return checked, errors


# ---------------------------------------------------------------- gates

@pytest.mark.parametrize("path", _json_files, ids=lambda p: p.name)
def test_research_json_parses(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, (dict, list)), f"{path.name}: top-level JSON must be an object or array"


@pytest.mark.parametrize("path", _jsonl_files, ids=lambda p: p.name)
def test_research_jsonl_every_line_parses(path):
    errors, parsed = [], 0
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
                errors.append(f"{path.name}:{lineno}: line is {type(rec).__name__}, not an object")
                continue
            parsed += 1
    assert not errors, f"invalid JSONL lines: {errors}"
    assert parsed > 0, f"{path.name}: no parseable records — an empty audit trail proves nothing"


def test_cited_source_appendices_exist_and_are_nonempty():
    analysis = RESEARCH_DIR / "PR_AGGREGATOR_MARKET_ANALYSIS.md"
    if not analysis.exists():
        pytest.skip("market analysis not present")
    text = analysis.read_text(encoding="utf-8")
    referenced_files = set(re.findall(r"market_analysis_sources/([\w-]+\.(?:md|txt))", text))
    assert referenced_files, "analysis doc no longer names its appendix files — update this test"
    for name in sorted(referenced_files):
        p = SOURCES_DIR / name
        assert p.exists(), f"analysis cites {name} but it is not committed"
        assert len(p.read_text(encoding="utf-8").strip()) > 500, f"{name} is suspiciously small"
    cited_letters = set(re.findall(r"\[([A-H])\]", text))
    on_disk = {p.name.split("_")[0] for p in SOURCES_DIR.glob("*.md")} if SOURCES_DIR.exists() else set()
    missing = sorted(cited_letters - on_disk)
    assert not missing, f"analysis cites appendix letters with no committed file: {missing}"


def test_refuted_registry_is_valid():
    if not REGISTRY_PATH.exists():
        pytest.skip("no refuted-citations registry")
    reg = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    for entry in reg["refuted"]:
        assert {"file", "date", "original_url"} <= set(entry), f"registry entry incomplete: {entry}"
        assert (SOURCES_DIR / entry["file"]).exists(), f"registry points at missing file {entry['file']}"


def test_no_publication_style_date_after_compilation():
    if not SOURCES_DIR.exists():
        pytest.skip("no source appendices present")
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))["refuted"] if REGISTRY_PATH.exists() else []
    violations = []
    for md in sorted(SOURCES_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        m = re.search(r"Compiled (\d{4}-\d{2}-\d{2})", text)
        assert m, f"{md.name}: missing 'Compiled YYYY-MM-DD' header"
        entries = [e for e in registry if e["file"] == md.name]
        violations += [f"{md.name}: {v}" for v in
                       check_dates(text, datetime.date.fromisoformat(m.group(1)), entries)]
    assert not violations, f"time-incoherent citations: {violations}"


def test_sizing_arithmetic_is_internally_consistent():
    md_files = sorted(RESEARCH_DIR.glob("*.md"))
    if not md_files:
        pytest.skip("no research docs present")
    total_checked, errors = 0, []
    for md in md_files:
        checked, errs = check_arithmetic(md.read_text(encoding="utf-8"))
        total_checked += checked
        errors += [f"{md.name}: {e}" for e in errs]
    assert not errors, f"sizing arithmetic errors: {errors}"
    assert total_checked >= 1, "no sizing claims matched — update patterns if phrasing changed"


def test_every_artifact_referenced_by_research_docs_is_committed():
    md_files = sorted(RESEARCH_DIR.glob("*.md"))
    if not md_files:
        pytest.skip("no research docs present")
    referenced = set()
    for md in md_files:
        referenced.update(re.findall(r"[\w./-]+\.jsonl?\b", md.read_text(encoding="utf-8")))
    artifact_refs = {r.removeprefix("docs/research/") for r in referenced if not r.startswith("http")}
    assert artifact_refs, "no artifact references found in any research doc"
    committed = {str(p.relative_to(RESEARCH_DIR)) for p in list(_json_files) + list(_jsonl_files)}
    committed |= {p.name for p in list(_json_files) + list(_jsonl_files) if p.parent == RESEARCH_DIR}
    missing = sorted(a for a in artifact_refs if a not in committed
                     and (RESEARCH_DIR / a).suffix in (".json", ".jsonl"))
    assert not missing, f"research docs reference uncommitted artifacts: {missing}"


# ------------------------------------------------ negative fixtures
# Each trust gate must demonstrably FAIL on the failure shape it claims to
# prevent (evaluator r15: happy-path-only tests are false confidence).

_COMPILED = datetime.date(2026, 7, 14)
_REG = [{"file": "X.md", "date": "2026-07-28",
         "original_url": "https://example.org/posts/2026-07-28-rc/"}]


def test_negative_unmarked_future_date_fails():
    vs = check_dates("| 6 | thing shipped | Jul 2026 | blog, https://x.io/posts/2026-07-28-rc/ | High |",
                     _COMPILED, [])
    assert vs, "gate missed an unmarked future URL-slug date"


def test_negative_prose_future_publication_date_fails():
    vs = check_dates("| 6 | spec released Jul 28, 2026 | Jul 2026 | someblog | High |", _COMPILED, [])
    assert vs, "gate missed a prose future publication date"


def test_negative_prose_future_event_date_allowed():
    vs = check_dates("obligations apply from Aug 2, 2026 across the EU", _COMPILED, [])
    assert not vs, f"gate false-positived on a legitimate future event date: {vs}"


def test_negative_redacted_original_url_fails():
    text = "| 6 | claim (2026-07-28) | — | — | REFUTED (editor) |"
    vs = check_dates(text, _COMPILED, _REG)
    assert any("missing, redacted, or substituted" in v for v in vs), "gate missed a redaction"


def test_negative_substituted_url_fails():
    text = ("| 6 | claim of 2026-07-28 | Jul 2026 | https://example.com/other | REFUTED (editor) |")
    vs = check_dates(text, _COMPILED, _REG)
    assert any("substitution" in v or "missing" in v for v in vs), "gate missed URL substitution"


def test_negative_preserved_original_passes():
    text = ("| 6 | claim of 2026-07-28 | Jul 2026 | https://example.org/posts/2026-07-28-rc/ "
            "| REFUTED (editor verdict) |")
    vs = check_dates(text, _COMPILED, _REG)
    assert not vs, f"gate rejected properly preserved refuted evidence: {vs}"


def test_negative_arithmetic_point_form_fails():
    checked, errs = check_arithmetic("we estimate 500 issuers × $25k = $100M of spend")
    assert checked == 1 and errs, "gate missed the historical point-form arithmetic error"


def test_negative_arithmetic_point_form_correct_passes():
    checked, errs = check_arithmetic("we estimate 500 issuers × $25k = $12.5M of spend")
    assert checked == 1 and not errs, f"gate false-positived on correct arithmetic: {errs}"


def test_negative_arithmetic_range_form_fails():
    checked, errs = check_arithmetic("~4,000–5,000 companies × $10–25k = **$50–125M** pool")
    assert checked == 1 and errs, "gate missed the historical range-form arithmetic error"
