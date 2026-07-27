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


def test_the_counted_preamble_equals_what_the_SHELL_actually_writes():
    """Refutes a r5 nit with an execution instead of an argument (R-089).

    The nit blamed trailing `>> pr.diff` redirection for an over-count. There is
    none — the echoes sit in a `{ … } > pr.diff` block with ONE redirect at the
    close, and the only `>` on any note line is a literal `>=20`. Running the real
    echo lines through bash found a genuine gap from a DIFFERENT cause: `$HEAD_SHA`
    interpolation. So this asserts the guard never UNDER-reports, which is the
    property it needs, rather than equality, which no static number can reach.
    """
    import pathlib
    import re
    import subprocess

    root = pathlib.Path(__file__).resolve().parent.parent
    wf = (root / ".github" / "workflows" / "adversarial-review.yml").read_text(
        encoding="utf-8")
    echoes = [ln.strip() for ln in wf.splitlines() if ln.strip().startswith('echo "#')]
    assert len(echoes) > 20, f"only {len(echoes)} note lines found — extractor is blind"
    assert not any(re.search(r'"\s*>>?\s*\S', ln) for ln in echoes), (
        "an echo line now carries its own redirection, so the block-level "
        "`{ … } > pr.diff` assumption no longer holds and the counter needs updating")

    proc = subprocess.run(["bash", "-c", "\n".join(echoes)],
                          capture_output=True, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode()
    actual = len(proc.stdout)          # with every $VAR unset, i.e. the MINIMUM
    counted = psc.notes_preamble_bytes()
    # NEVER UNDER-REPORT is the property, not exact equality — several note lines
    # interpolate `$HEAD_SHA`/`$MERGE_SHA`, so the real size varies per run and no
    # static number can equal it. Demanding equality would be a false requirement;
    # demanding "at least the minimum" is the property the guard needs.
    assert counted >= actual, (
        f"the tool counts {counted} preamble bytes but bash writes at least "
        f"{actual} — the guard under-reports again, which is R-089 reopening")
    # And not absurdly loose: a 3x over-estimate would make the guard cry wolf.
    assert counted < actual * 2, (
        f"counted {counted} vs a {actual}-byte floor — the widening is now so "
        f"generous the guard would block reviewable PRs")
