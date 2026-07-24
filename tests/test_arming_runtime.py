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
    ):
        assert expected in rt, f"{expected} missing from armed-cron runtime closure"


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
