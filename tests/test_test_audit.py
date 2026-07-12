"""Tests for tools/test_audit.py — the false-confidence test-suite audit.

Each detector is proven against a synthetic tests/ directory written to
tmp_path (never against the real tests/ dir, so a future real test file
can't accidentally break this suite by tripping a detector). Also includes
one smoke test that the real repo's tests/ directory currently audits
clean, since that's the whole point of shipping this tool.
"""
import importlib.util
import pathlib
import sys

_PATH = pathlib.Path(__file__).resolve().parent.parent / "tools" / "test_audit.py"
_spec = importlib.util.spec_from_file_location("test_audit", _PATH)
test_audit = importlib.util.module_from_spec(_spec)
sys.modules["test_audit"] = test_audit
_spec.loader.exec_module(test_audit)


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content)
    return p


def test_real_repo_tests_dir_audits_clean():
    findings = test_audit.Findings()
    for f in test_audit._test_files():
        test_audit.audit_file(f, findings)
    assert findings.ok(), f"real tests/ dir has false-confidence findings: {findings.items}"


def test_flags_empty_pass_only_test(tmp_path):
    _write(tmp_path, "test_empty.py", "def test_nothing():\n    pass\n")
    findings = test_audit.Findings()
    test_audit.audit_file(tmp_path / "test_empty.py", findings)
    assert any("just `pass`" in f for f in findings.items)


def test_flags_zero_assertions(tmp_path):
    _write(tmp_path, "test_noassert.py", "def test_runs_but_checks_nothing():\n    x = 1 + 1\n    y = x * 2\n")
    findings = test_audit.Findings()
    test_audit.audit_file(tmp_path / "test_noassert.py", findings)
    assert any("zero assert" in f for f in findings.items)


def test_flags_trivially_true_assertion(tmp_path):
    _write(tmp_path, "test_trivial.py", "def test_always_true():\n    assert True\n    assert 1 == 1\n")
    findings = test_audit.Findings()
    test_audit.audit_file(tmp_path / "test_trivial.py", findings)
    assert sum("trivially-true" in f for f in findings.items) == 2


def test_flags_overly_broad_raises(tmp_path):
    _write(tmp_path, "test_broad.py",
           "import pytest\n\n\ndef test_raises_anything():\n    with pytest.raises(Exception):\n        raise ValueError('boom')\n")
    findings = test_audit.Findings()
    test_audit.audit_file(tmp_path / "test_broad.py", findings)
    assert any("pytest.raises(Exception)" in f for f in findings.items)


def test_does_not_flag_narrowed_raises(tmp_path):
    _write(tmp_path, "test_narrow.py",
           "import pytest\n\n\ndef test_raises_specific():\n    with pytest.raises(ValueError, match='boom'):\n        raise ValueError('boom')\n")
    findings = test_audit.Findings()
    test_audit.audit_file(tmp_path / "test_narrow.py", findings)
    assert not any("pytest.raises" in f for f in findings.items)


def test_flags_mock_asserted_but_never_invoked(tmp_path):
    _write(tmp_path, "test_deadmock.py",
           "from unittest.mock import Mock\n\n\ndef test_checks_a_mock_that_was_never_called():\n"
           "    cb = Mock()\n    cb.assert_not_called()\n")
    findings = test_audit.Findings()
    test_audit.audit_file(tmp_path / "test_deadmock.py", findings)
    assert any("never invoked" in f for f in findings.items)


def test_does_not_flag_mock_that_is_invoked(tmp_path):
    _write(tmp_path, "test_livemock.py",
           "from unittest.mock import Mock\n\n\ndef test_checks_a_mock_that_was_called():\n"
           "    cb = Mock()\n    cb('hello')\n    cb.assert_called_once_with('hello')\n")
    findings = test_audit.Findings()
    test_audit.audit_file(tmp_path / "test_livemock.py", findings)
    assert not any("never invoked" in f for f in findings.items)


def test_healthy_test_produces_no_findings(tmp_path):
    _write(tmp_path, "test_healthy.py",
           "def test_addition_is_correct():\n    assert 2 + 2 == 4\n")
    findings = test_audit.Findings()
    test_audit.audit_file(tmp_path / "test_healthy.py", findings)
    assert findings.ok()


def test_main_advisory_mode_returns_0_despite_findings(tmp_path, monkeypatch, capsys):
    _write(tmp_path, "test_empty.py", "def test_nothing():\n    pass\n")
    rc = test_audit.main(["--tests-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "finding" in out
    assert "advisory only" in out


def test_main_strict_mode_returns_1_on_findings(tmp_path):
    _write(tmp_path, "test_empty.py", "def test_nothing():\n    pass\n")
    rc = test_audit.main(["--strict", "--tests-dir", str(tmp_path)])
    assert rc == 1


def test_main_returns_0_on_clean_dir(tmp_path):
    _write(tmp_path, "test_clean.py", "def test_ok():\n    assert 1 == 1 + 0\n    assert True is True or False\n")
    # note: the second assert here is a Compare/BoolOp, not the trivial-const
    # shape this audit flags, so this file should be reported clean.
    rc = test_audit.main(["--strict", "--tests-dir", str(tmp_path)])
    assert rc == 0


def test_main_returns_1_on_missing_tests_dir(tmp_path):
    missing = tmp_path / "does_not_exist"
    rc = test_audit.main(["--tests-dir", str(missing)])
    assert rc == 1
