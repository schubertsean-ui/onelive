"""Tests for tools/lint.py — the pure-stdlib OneLive style/trust linter.

Proves each rule fires on a positive case and stays quiet on the matching
negative case, using temp files so real repo code is never mutated by a test.
Also proves the real repo is currently clean and that --fix actually rewrites
files on disk (not just flags).
"""
import importlib.util
import pathlib
import sys
import textwrap

_LINT_PATH = pathlib.Path(__file__).resolve().parent.parent / "tools" / "lint.py"
_spec = importlib.util.spec_from_file_location("lint", _LINT_PATH)
lint = importlib.util.module_from_spec(_spec)
sys.modules["lint"] = lint
_spec.loader.exec_module(lint)


def _write(root: pathlib.Path, rel: str, body: str) -> pathlib.Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(body))
    return p


def test_real_repo_is_clean():
    """Regression guard: the linter must be green on the real repo right now."""
    assert lint.main([]) == 0


# --- Rule 1: swallowed errors --------------------------------------------------
def test_catches_bare_except_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(lint, "REPO", tmp_path)
    monkeypatch.setattr(lint, "LINT_DIRS", ["worker"])
    _write(tmp_path, "worker/bad.py", '''
        """A module."""
        def f():
            try:
                risky()
            except:
                pass
    ''')
    f = lint.Findings()
    lint.check_swallowed_errors(f)
    assert not f.ok()
    assert any("bare except" in v for v in f.violations)


def test_catches_except_exception_blank(tmp_path, monkeypatch):
    monkeypatch.setattr(lint, "REPO", tmp_path)
    monkeypatch.setattr(lint, "LINT_DIRS", ["worker"])
    _write(tmp_path, "worker/bad2.py", '''
        """A module."""
        def f():
            try:
                risky()
            except Exception:
                pass
    ''')
    f = lint.Findings()
    lint.check_swallowed_errors(f)
    assert not f.ok()
    assert any("except Exception:" in v for v in f.violations)


def test_allows_logged_except(tmp_path, monkeypatch):
    monkeypatch.setattr(lint, "REPO", tmp_path)
    monkeypatch.setattr(lint, "LINT_DIRS", ["worker"])
    _write(tmp_path, "worker/good.py", '''
        """A module."""
        import logging
        log = logging.getLogger(__name__)

        def f():
            try:
                risky()
            except Exception:
                log.exception("risky() failed, degrading")
    ''')
    f = lint.Findings()
    lint.check_swallowed_errors(f)
    assert f.ok(), f.violations


# --- Rule 2: print() for error handling ---------------------------------------
def test_catches_print_in_except(tmp_path, monkeypatch):
    monkeypatch.setattr(lint, "REPO", tmp_path)
    _write(tmp_path, "worker/bad3.py", '''
        """A module."""
        def f():
            try:
                risky()
            except Exception as exc:
                print(exc)
    ''')
    f = lint.Findings()
    lint.check_print_for_errors(f)
    assert not f.ok()
    assert any("print()" in v for v in f.violations)


def test_allows_print_for_non_error_output(tmp_path, monkeypatch):
    monkeypatch.setattr(lint, "REPO", tmp_path)
    _write(tmp_path, "worker/good2.py", '''
        """A module."""
        def report(n):
            print(f"processed {n} rows")
    ''')
    f = lint.Findings()
    lint.check_print_for_errors(f)
    assert f.ok(), f.violations


# --- Rule 3: missing module docstring -----------------------------------------
def test_catches_missing_docstring(tmp_path, monkeypatch):
    monkeypatch.setattr(lint, "REPO", tmp_path)
    monkeypatch.setattr(lint, "LINT_DIRS", ["worker"])
    _write(tmp_path, "worker/nodoc.py", '''
        import os
        X = 1
    ''')
    f = lint.Findings()
    lint.check_module_docstrings(f)
    assert not f.ok()
    assert any("missing module docstring" in v for v in f.violations)


def test_allows_present_docstring(tmp_path, monkeypatch):
    monkeypatch.setattr(lint, "REPO", tmp_path)
    monkeypatch.setattr(lint, "LINT_DIRS", ["worker"])
    _write(tmp_path, "worker/hasdoc.py", '''
        """Has a docstring."""
        X = 1
    ''')
    f = lint.Findings()
    lint.check_module_docstrings(f)
    assert f.ok(), f.violations


def test_init_py_exempt_from_docstring_rule(tmp_path, monkeypatch):
    monkeypatch.setattr(lint, "REPO", tmp_path)
    monkeypatch.setattr(lint, "LINT_DIRS", ["api"])
    _write(tmp_path, "api/__init__.py", "")
    f = lint.Findings()
    lint.check_module_docstrings(f)
    assert f.ok(), f.violations


# --- Rule 4: leftover broken-window markers -----------------------------------
def test_catches_todo_marker(tmp_path, monkeypatch):
    monkeypatch.setattr(lint, "REPO", tmp_path)
    monkeypatch.setattr(lint, "LINT_DIRS", ["worker"])
    marker = "TO" + "DO"  # built at runtime so this test file itself stays clean
    _write(tmp_path, "worker/hastodo.py", f'''
        """A module."""
        # {marker}: revisit this later
        X = 1
    ''')
    f = lint.Findings()
    lint.check_no_todos(f)
    assert not f.ok()
    assert any("broken-window" in v for v in f.violations)


def test_no_todo_marker_is_clean(tmp_path, monkeypatch):
    monkeypatch.setattr(lint, "REPO", tmp_path)
    monkeypatch.setattr(lint, "LINT_DIRS", ["worker"])
    _write(tmp_path, "worker/clean.py", '''
        """A module."""
        # this comment is fine
        X = 1
    ''')
    f = lint.Findings()
    lint.check_no_todos(f)
    assert f.ok(), f.violations


# --- --fix: proves it actually rewrites files on disk -------------------------
def test_fix_strips_trailing_whitespace_and_adds_newline(tmp_path):
    p = tmp_path / "demo.py"
    p.write_text('x = 1   \ny = 2')  # trailing spaces, no final newline
    changed = lint.apply_fixes(p)
    assert changed is True
    text = p.read_text()
    assert text == "x = 1\ny = 2\n"


def test_fix_sorts_leading_imports_stdlib_before_thirdparty(tmp_path):
    p = tmp_path / "demo2.py"
    p.write_text(
        "import sys\n"
        "import os\n"
        "from collections import OrderedDict\n"
        "import requests\n"
        "\n"
        "print(1)\n"
    )
    changed = lint.apply_fixes(p)
    assert changed is True
    lines = p.read_text().splitlines()
    stdlib_block = [l for l in lines if l.startswith(("import os", "import sys", "from collections"))]
    requests_idx = next(i for i, l in enumerate(lines) if "requests" in l)
    os_idx = next(i for i, l in enumerate(lines) if l == "import os")
    assert os_idx < requests_idx, "stdlib imports must sort before third-party"


def test_fix_is_noop_on_already_clean_file(tmp_path):
    p = tmp_path / "clean.py"
    p.write_text('"""doc."""\nx = 1\n')
    changed = lint.apply_fixes(p)
    assert changed is False


# --- exit codes -----------------------------------------------------------------
def test_main_returns_1_on_violation(tmp_path, monkeypatch):
    monkeypatch.setattr(lint, "REPO", tmp_path)
    monkeypatch.setattr(lint, "LINT_DIRS", ["worker"])
    _write(tmp_path, "worker/nodoc.py", "X = 1\n")
    assert lint.main([]) == 1
