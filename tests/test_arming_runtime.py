"""Tests for tools/arming_runtime.py — the armed-cron runtime closure computer
that scopes the arming-evidence binding (tests/test_arming_smoke_binding.py).
"""
import importlib.util
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location(
        "arming_runtime", _ROOT / "tools" / "arming_runtime.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_closure_includes_the_cron_path():
    rt = _mod().runtime_files()
    # entrypoints + key transitive imports the armed cron actually runs
    for expected in (
        ".github/workflows/ingest.yml",
        "worker/run_once.py",
        "worker/orchestrator.py",
        "worker/sentinel.py",
        "ai/bedrock_provider.py",
        "tools/assemble_dsn.py",
        "tools/assert_deadman_period.py",
        "worker/requirements.txt",  # a non-Python runtime input the workflow installs
    ):
        assert expected in rt, f"{expected} missing from armed-cron runtime closure"


def test_workflow_comment_paths_do_not_leak():
    # File paths mentioned only in ingest.yml comments must NOT enter the set
    # (that would reintroduce false positives). docs/ is comment-only there.
    rt = _mod().runtime_files()
    assert not any(p.startswith("docs/") for p in rt), sorted(p for p in rt if p.startswith("docs/"))


def test_closure_excludes_non_cron_code():
    rt = _mod().runtime_files()
    # None of these run in the armed ingest cron; they must NOT trip the binding.
    for path in rt:
        assert not path.startswith("web/"), f"consumer app leaked in: {path}"
        assert not path.startswith("supabase/"), f"migration leaked in: {path}"
        assert not path.startswith("worker/importers/"), f"importer leaked in: {path}"
        assert not path.startswith("tests/"), f"test leaked in: {path}"
        assert not path.startswith("docs/"), f"doc leaked in: {path}"


def test_dynamic_import_fails_loud(tmp_path):
    m = _mod()
    dyn = tmp_path / "dyn.py"
    dyn.write_text("import importlib\nx = importlib.import_module('os')\n")
    with pytest.raises(m.DynamicImportError):
        m._imported_modules(dyn)


def test_static_imports_parse_cleanly(tmp_path):
    m = _mod()
    f = tmp_path / "ok.py"
    f.write_text("import os\nfrom worker.orchestrator import run_loop\n")
    mods = m._imported_modules(f)
    assert "os" in mods and "worker.orchestrator" in mods
    # `from pkg import submod` records the submodule too (fail-open fix)
    assert "worker.orchestrator.run_loop" in mods


def test_importlib_in_comment_does_not_trip(tmp_path):
    # AST-based detection: 'importlib' in a comment/docstring is NOT a dynamic import.
    m = _mod()
    f = tmp_path / "c.py"
    f.write_text('"""mentions importlib in a docstring"""\n# and a comment: importlib\nimport os\n')
    assert m._imported_modules(f) == ["os"]


def test_package_inits_included():
    rt = _mod().runtime_files()
    # parent-package __init__.py files Python runs on import are in the set
    assert any(p.endswith("__init__.py") for p in rt)


def test_missing_declared_script_fails_loud(tmp_path, monkeypatch):
    m = _mod()
    wf = tmp_path / "ingest.yml"
    wf.write_text("steps:\n  run: python worker/does_not_exist_xyz.py\n")
    monkeypatch.setattr(m, "INGEST", wf)
    with pytest.raises(m.MissingRuntimeInput):
        m.runtime_files()


def test_missing_requirements_fails_loud(tmp_path, monkeypatch):
    m = _mod()
    wf = tmp_path / "ingest.yml"
    wf.write_text("steps:\n  run: pip install -r worker/no_such_reqs.txt\n")
    monkeypatch.setattr(m, "INGEST", wf)
    with pytest.raises(m.MissingRuntimeInput):
        m.runtime_files()
