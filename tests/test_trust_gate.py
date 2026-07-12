"""Tests for tools/trust_gate.py — the deterministic trust-invariant CI gate.

A gate that cannot fail is theatre. These tests prove the gate (a) passes on the
real repo and (b) CATCHES each class of violation it claims to guard,
by running the individual checks against synthetic files written to a tmp repo.
"""
import importlib.util
import pathlib
import sys
import textwrap

import pytest

# Load trust_gate as a module from its path (tools/ is not a package). Register it
# in sys.modules BEFORE exec so that @dataclass (which looks the module up by name
# during class processing) can resolve it.
_GATE_PATH = pathlib.Path(__file__).resolve().parent.parent / "tools" / "trust_gate.py"
_spec = importlib.util.spec_from_file_location("trust_gate", _GATE_PATH)
trust_gate = importlib.util.module_from_spec(_spec)
sys.modules["trust_gate"] = trust_gate
_spec.loader.exec_module(trust_gate)


def test_real_repo_passes():
    """The gate must be green on the real repo right now (regression guard)."""
    assert trust_gate.main() == 0


def _write(root: pathlib.Path, rel: str, body: str) -> pathlib.Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(body))
    return p


def test_catches_fstring_sql(tmp_path, monkeypatch):
    monkeypatch.setattr(trust_gate, "REPO", tmp_path)
    monkeypatch.setattr(trust_gate, "SQL_DIRS", ["worker"])
    _write(tmp_path, "worker/bad.py", '''
        def q(cur, t):
            cur.execute(f"select * from {t}")
    ''')
    f = trust_gate.Findings()
    trust_gate.check_no_dynamic_sql(f)
    assert not f.ok()
    assert any("f-string" in v for v in f.violations)


def test_catches_percent_and_concat_and_format(tmp_path, monkeypatch):
    monkeypatch.setattr(trust_gate, "REPO", tmp_path)
    monkeypatch.setattr(trust_gate, "SQL_DIRS", ["worker"])
    _write(tmp_path, "worker/bad.py", '''
        def q(cur, name):
            cur.execute("select * from t where a = %s" % name)
            cur.execute("select * from t where a = " + name)
            cur.execute("select {}".format(name))
    ''')
    f = trust_gate.Findings()
    trust_gate.check_no_dynamic_sql(f)
    reasons = " ".join(f.violations)
    assert "%-format" in reasons
    assert "concatenation" in reasons
    assert ".format()" in reasons


def test_allows_static_and_psycopg_sql(tmp_path, monkeypatch):
    monkeypatch.setattr(trust_gate, "REPO", tmp_path)
    monkeypatch.setattr(trust_gate, "SQL_DIRS", ["worker"])
    _write(tmp_path, "worker/good.py", '''
        from psycopg2 import sql
        def q(cur, name, t):
            cur.execute("select * from venue where name = %s", (name,))
            cur.execute(sql.SQL("select count(*) from {}").format(sql.Identifier(t)))
    ''')
    f = trust_gate.Findings()
    trust_gate.check_no_dynamic_sql(f)
    assert f.ok(), f.violations


def test_catches_ads_touching_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(trust_gate, "REPO", tmp_path)
    monkeypatch.setattr(trust_gate, "SQL_DIRS", ["worker"])
    _write(tmp_path, "worker/ads_ranker.py", '''
        from worker.promote import promote_candidate
    ''')
    f = trust_gate.Findings()
    trust_gate.check_ads_tastemaker_isolation(f)
    assert not f.ok()
    assert any("ads/tastemaker" in v for v in f.violations)


def test_catches_ai_promoting(tmp_path, monkeypatch):
    monkeypatch.setattr(trust_gate, "REPO", tmp_path)
    _write(tmp_path, "ai/rogue.py", '''
        from worker.promote import promote_candidate
    ''')
    f = trust_gate.Findings()
    trust_gate.check_ai_never_promotes(f)
    assert not f.ok()
    assert any("never publishes directly" in v for v in f.violations)


def test_promote_allowlist_blocks_new_importer(tmp_path, monkeypatch):
    monkeypatch.setattr(trust_gate, "REPO", tmp_path)
    monkeypatch.setattr(trust_gate, "SQL_DIRS", ["worker"])
    monkeypatch.setattr(trust_gate, "PROMOTE_IMPORT_ALLOWLIST", set())
    _write(tmp_path, "worker/sneaky.py", '''
        from worker.promote import promote_candidate
    ''')
    f = trust_gate.Findings()
    trust_gate.check_promote_import_allowlist(f)
    assert not f.ok()
    assert any("allowlist" in v for v in f.violations)
