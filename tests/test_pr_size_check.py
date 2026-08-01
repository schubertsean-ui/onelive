"""Tests for tools/pr_size_check.py — the early warning that keeps a branch
reviewable by the mandatory independent evaluator.

Founder directive (2026-07-25): PR #59 reached 1.26 MB against the reviewer's
800 KB cap, so the review REFUSED to run and the charter-mandatory evaluator pass
could not happen. Splitting after the fact is high-risk churn; this sees it
coming while splitting is still cheap.
"""
import importlib.util
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location(
        "pr_size_check", _ROOT / "tools" / "pr_size_check.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


psc = _mod()


def test_cap_is_read_from_the_workflow_not_hardcoded():
    # The cap must track whatever adversarial-review.yml actually passes, so the
    # warning can never drift away from the real limit.
    cap = psc.evaluator_cap_bytes()
    assert isinstance(cap, int) and cap > 0
    wf = (_ROOT / ".github" / "workflows" / "adversarial-review.yml").read_text()
    assert f"--max-diff-bytes {cap}" in wf


def test_excludes_mirror_the_workflows_review_diff():
    # Same exclusions the workflow applies, so the measured size is the size the
    # reviewer actually sees (package-lock.json is generated, never reviewed).
    ex = psc.workflow_excludes()
    assert any("package-lock.json" in e for e in ex)


def test_over_cap_exits_nonzero_and_says_the_review_cannot_happen(monkeypatch, capsys):
    monkeypatch.setattr(psc, "evaluator_cap_bytes", lambda: 800_000)
    monkeypatch.setattr(psc, "diff_bytes", lambda base: 1_260_000)
    rc = psc.main([])
    assert rc == 1
    err = capsys.readouterr().err
    assert "OVER CAP" in err and "REFUSE" in err


def test_warning_band_is_advisory_exit_zero(monkeypatch, capsys):
    monkeypatch.setattr(psc, "evaluator_cap_bytes", lambda: 800_000)
    monkeypatch.setattr(psc, "diff_bytes", lambda base: 600_000)  # 75%
    rc = psc.main(["--warn-pct", "70"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "WARNING" in out and "while splitting is still cheap" in out


def test_comfortably_under_is_quiet_ok(monkeypatch, capsys):
    monkeypatch.setattr(psc, "evaluator_cap_bytes", lambda: 800_000)
    monkeypatch.setattr(psc, "diff_bytes", lambda base: 100_000)
    assert psc.main([]) == 0
    assert "OK" in capsys.readouterr().out


def test_unmeasurable_skips_rather_than_failing_the_session(monkeypatch, capsys):
    # A shallow clone without the base ref must not fail the run — say so plainly.
    monkeypatch.setattr(psc, "diff_bytes", lambda base: None)
    assert psc.main([]) == 0
    assert "SKIPPED" in capsys.readouterr().out


def test_it_is_wired_into_validate():
    assert "pr_size_check" in (_ROOT / "tools" / "validate").read_text()
