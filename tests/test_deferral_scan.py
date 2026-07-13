"""Tests for tools/deferral_scan.py — the Recording enforcement scanner.

Hermetic where possible (temp trees via monkeypatched REPO/RECORD), plus a
real-repo regression guard proving the codebase is currently clean. Proves:
untagged deferral comments fail; tagged ones pass only when the tag exists
in docs/RECORD.md (dangling tags fail); non-comment occurrences of the
phrases (string literals) do not fire for slash-comment files; a missing
register is a hard failure, never a silent pass.
"""
import importlib.util
import pathlib
import sys
import textwrap

_TOOL_PATH = pathlib.Path(__file__).resolve().parent.parent / "tools" / "deferral_scan.py"
_spec = importlib.util.spec_from_file_location("deferral_scan", _TOOL_PATH)
ds = importlib.util.module_from_spec(_spec)
sys.modules["deferral_scan"] = ds
_spec.loader.exec_module(ds)


def _setup(tmp_path, monkeypatch, record_text="R-001 exists"):
    monkeypatch.setattr(ds, "REPO", tmp_path)
    record = tmp_path / "docs" / "RECORD.md"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(record_text)
    monkeypatch.setattr(ds, "RECORD", record)
    (tmp_path / "worker").mkdir()


def _write(tmp_path, rel, body):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(body))
    return p


def test_untagged_deferral_comment_fails(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch)
    phrase = "good " + "enough"  # built at runtime so this file stays clean
    _write(tmp_path, "worker/x.py", f'''
        """Mod."""
        X = 1  # {phrase} until launch
    ''')
    assert ds.main([]) == 1
    assert "untagged deferral" in capsys.readouterr().err


def test_tagged_with_live_entry_passes(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, record_text="| R-001 | ... |")
    phrase = "for " + "now"          # runtime-built so this file stays clean
    _write(tmp_path, "worker/x.py", f'''
        """Mod."""
        X = 1  # error monitoring only {phrase} [R-001]
    ''')
    assert ds.main([]) == 0


def test_dangling_tag_fails(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, record_text="| R-001 | ... |")
    phrase = "for " + "now"          # runtime-built so this file stays clean
    tag = "[R-9" + "99]"
    _write(tmp_path, "worker/x.py", f'''
        """Mod."""
        X = 1  # parked {phrase} {tag}
    ''')
    assert ds.main([]) == 1
    assert "no entry" in capsys.readouterr().err


def test_string_literal_in_slash_comment_file_does_not_fire(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    (tmp_path / "web").mkdir()
    phrase = "for " + "now"          # runtime-built so this file stays clean
    _write(tmp_path, "web/x.ts", f'''
        const label = "see you later, {phrase}";
        export default label;
    ''')
    assert ds.main([]) == 0


def test_missing_register_is_hard_failure(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    (ds.RECORD).unlink()
    assert ds.main([]) == 2


def test_real_repo_is_clean():
    """Regression guard: the scanner must be green on the real repo now."""
    real_spec = importlib.util.spec_from_file_location("ds_real", _TOOL_PATH)
    real = importlib.util.module_from_spec(real_spec)
    real_spec.loader.exec_module(real)
    assert real.main([]) == 0
