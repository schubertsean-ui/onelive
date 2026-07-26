"""Tests for tools/decision_codified_lint.py.

The rule it enforces (CLAUDE.md prime directive 6, founder directive 2026-07-26):
a decision is not done until the repo carries it, so every file in
docs/memory/decisions/ must name the commit, file, gate or R-### row that
implements it — or say "NOTHING YET" with a reason.

Proves: the real decisions directory passes (a live integration check, not a
fixture); a record with no marker fails; a marker naming nothing findable fails;
each accepted form is accepted; and a checker that would pass by finding nothing
errors out instead (a gate that cannot fail proves nothing).
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "decision_codified_lint", _REPO_ROOT / "tools" / "decision_codified_lint.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


LINT = _load()

_BODY = "# Decision — something\n\nSome prose about the decision.\n"


def _record(tmp_path: pathlib.Path, name: str, tail: str) -> pathlib.Path:
    path = tmp_path / name
    path.write_text(_BODY + tail, encoding="utf-8")
    return path


def test_the_real_decisions_directory_passes():
    # Live check against the actual repo: every decision on disk names what
    # carries it. This is the assertion that would catch a new record landing
    # without its codification line.
    records = [p for p in LINT.DECISIONS_DIR.glob("*.md") if p.name != "README.md"]
    assert len(records) >= 20, "decision records vanished — check the glob"
    assert LINT.audit(records) == []


def test_a_record_with_no_marker_is_a_finding(tmp_path):
    path = _record(tmp_path, "2026-01-01_no-marker.md", "")
    findings = LINT.audit([path])
    assert len(findings) == 1
    assert "no '**Codified by:**' line" in findings[0]


def test_a_marker_naming_nothing_findable_is_a_finding(tmp_path):
    path = _record(tmp_path, "2026-01-01_vague.md",
                   "\n**Codified by:** it is handled\n")
    findings = LINT.audit([path])
    assert len(findings) == 1
    assert "names nothing that EXISTS" in findings[0]


@pytest.mark.parametrize("value", [
    "`tools/kpi_report.py` and its test",          # a file
    "docs/RECORD.md R-067 (staged, with a trigger)",  # a Record row
    "commit d29b8d9",                              # a sha
    "NOTHING YET — specified only; trigger: after v1 is live",  # the honest gap
])
def test_each_accepted_form_passes(tmp_path, value):
    path = _record(tmp_path, "2026-01-01_ok.md", f"\n**Codified by:** {value}\n")
    assert LINT.audit([path]) == []


def test_a_marker_buried_mid_paragraph_does_not_count(tmp_path):
    # Must START the line — a mention inside prose is not a field anyone can find.
    path = _record(tmp_path, "2026-01-01_buried.md",
                   "\nThis was **Codified by:** `tools/lint.py` eventually.\n")
    findings = LINT.audit([path])
    assert len(findings) == 1
    assert "no '**Codified by:**' line" in findings[0]


def test_an_empty_record_set_errors_rather_than_reporting_clean(monkeypatch, tmp_path):
    # A checker that passes because it found nothing is the fail-open this repo
    # keeps catching; exit 2 is "tool error", never 0.
    monkeypatch.setattr(LINT, "DECISIONS_DIR", tmp_path)
    assert LINT.main() == 2


def test_a_missing_directory_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(LINT, "DECISIONS_DIR", tmp_path / "does_not_exist")
    assert LINT.main() == 2


def test_main_returns_1_on_findings(monkeypatch, tmp_path):
    _record(tmp_path, "2026-01-01_bad.md", "")
    monkeypatch.setattr(LINT, "DECISIONS_DIR", tmp_path)
    assert LINT.main() == 1


def test_readme_is_not_audited_as_a_decision(monkeypatch, tmp_path):
    (tmp_path / "README.md").write_text("just an index\n", encoding="utf-8")
    _record(tmp_path, "2026-01-01_ok.md", "\n**Codified by:** `tools/lint.py`\n")
    monkeypatch.setattr(LINT, "DECISIONS_DIR", tmp_path)
    assert LINT.main() == 0


# ------------------------------------------- a plausible string is not evidence
def test_a_path_that_does_not_exist_is_a_finding(tmp_path):
    """`CLASS:codification-gate-nonbinding` (openai/absence-only, PR #76 r2).

    Matching a SHAPE was all this did, so any `.md`-looking string passed even when
    no such file existed — certifying a decision as codified when nothing in the
    repo carried it. The identical defect the escape-closure gate had.
    """
    path = _record(tmp_path, "2026-01-01_ghost.md",
                   "\n**Codified by:** docs/DEFINITELY_NOT_A_FILE.md\n")
    findings = LINT.audit([path])
    assert len(findings) == 1 and "names nothing that EXISTS" in findings[0]


def test_a_record_row_that_does_not_exist_is_a_finding(tmp_path):
    path = _record(tmp_path, "2026-01-01_ghostrow.md",
                   "\n**Codified by:** R-999\n")
    findings = LINT.audit([path])
    assert len(findings) == 1


def test_a_commit_git_cannot_resolve_is_a_finding(tmp_path):
    """Seven hex characters is a shape, not a commit."""
    path = _record(tmp_path, "2026-01-01_ghostsha.md",
                   "\n**Codified by:** commit deadbee\n")
    findings = LINT.audit([path])
    assert len(findings) == 1


def test_an_absolute_path_outside_the_repo_is_a_finding(tmp_path):
    """`Path(root) / "/etc/x.md"` discards the root, so an absolute path to any
    host file would otherwise count as a repo citation."""
    path = _record(tmp_path, "2026-01-01_outside.md",
                   "\n**Codified by:** /etc/hostname.md\n")
    findings = LINT.audit([path])
    assert len(findings) == 1


def test_a_bare_NOTHING_YET_is_a_finding_without_its_reason(tmp_path):
    """The token promises a reason AND a trigger. Bare, it is just a way to pass —
    the escape hatch that made this gate optional."""
    path = _record(tmp_path, "2026-01-01_bare.md",
                   "\n**Codified by:** NOTHING YET\n")
    findings = LINT.audit([path])
    assert len(findings) == 1


def test_NOTHING_YET_WITH_a_reason_and_trigger_passes(tmp_path):
    """So the honest gap is still expressible — otherwise the gate forces a lie."""
    path = _record(tmp_path, "2026-01-01_honest.md",
                   "\n**Codified by:** NOTHING YET — the flag stays OFF until "
                   "safeguard 1 ships; trigger is R-056 closing\n")
    assert LINT.audit([path]) == []


def test_citations_that_DO_resolve_pass(tmp_path):
    """The other half: real files, real rows and `tools/validate` (no extension,
    and the most likely citation in the repo) must all be accepted."""
    for value in ("docs/BAR.md", "R-002", "`tools/validate`"):
        path = _record(tmp_path, f"2026-01-01_ok_{abs(hash(value))}.md",
                       f"\n**Codified by:** {value}\n")
        assert LINT.audit([path]) == [], value
