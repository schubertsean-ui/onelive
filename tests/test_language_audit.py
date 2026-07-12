"""Tests for tools/language_audit.py — the §1c language-audit gate.

A gate that cannot fire is theatre (same principle as test_trust_gate). These
tests prove the audit (a) passes on the real repo, (b) FIRES on each audited
surface (Python comment/docstring, JS/TS comment and UI copy, Markdown prose),
and (c) does NOT false-positive on the technical-adverb allowlist or on the
legitimate multi-word constructions in CONTEXT_OK. They also lock the invariant
that no allowlisted technical adverb is ever also a flagged hedge.
"""
import importlib.util
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
# Register in sys.modules BEFORE exec so @dataclass (which resolves the module by
# name during class processing on 3.12+) can find it. Same pattern as
# test_trust_gate.py.
_spec = importlib.util.spec_from_file_location(
    "language_audit", REPO / "tools" / "language_audit.py"
)
la = importlib.util.module_from_spec(_spec)
sys.modules["language_audit"] = la
_spec.loader.exec_module(la)


def _run(tmp_path, name: str, body: str):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    f = la.Findings()
    la.audit_path(p, f)
    return f


# --- passes on the real repo -------------------------------------------------
def test_real_repo_is_clean():
    f = la.run([REPO])
    assert f.ok, "hedging found in repo:\n" + "\n".join(
        f"{i.path}:{i.line}: {i.word} — {i.text}" for i in f.items
    )


# --- fires on each audited surface -------------------------------------------
def test_python_comment_flagged(tmp_path):
    f = _run(tmp_path, "a.py", "x = 1  # this basically just works\n")
    words = {i.word for i in f.items}
    assert "basically" in words and "just" in words


def test_python_docstring_flagged(tmp_path):
    f = _run(tmp_path, "b.py", '"""This is obviously correct."""\n')
    assert any(i.word == "obviously" for i in f.items)


def test_python_inline_code_not_docstring_ignored(tmp_path):
    # A string that is NOT a docstring (an assignment value) is code, not prose,
    # and must not be scanned — otherwise data/config strings false-positive.
    f = _run(tmp_path, "c.py", 'LABEL = "this is very important"\n')
    assert f.ok


def test_ts_comment_flagged(tmp_path):
    f = _run(tmp_path, "d.ts", "// this is really simple\nconst x = 1;\n")
    words = {i.word for i in f.items}
    assert "really" in words and "simple" not in words  # 'simple' is not a hedge


def test_tsx_ui_copy_flagged(tmp_path):
    f = _run(tmp_path, "e.tsx", "export const C = () => <p>Honestly the best</p>;\n")
    assert any(i.word == "honestly" for i in f.items)


def test_markdown_prose_flagged(tmp_path):
    f = _run(tmp_path, "f.md", "This is clearly the right approach.\n")
    assert any(i.word == "clearly" for i in f.items)


def test_markdown_fenced_code_exempt(tmp_path):
    body = "Prose line is clean.\n\n```\n# obviously a code comment\n```\n"
    f = _run(tmp_path, "g.md", body)
    assert f.ok


def test_markdown_inline_code_exempt(tmp_path):
    f = _run(tmp_path, "h.md", "Use the `--very-verbose` flag.\n")
    assert f.ok


# --- does NOT false-positive -------------------------------------------------
def test_context_ok_rather_than(tmp_path):
    f = _run(tmp_path, "i.py", "# fail loud rather than swallow the error\n")
    assert f.ok


def test_technical_adverb_allowlist_not_flagged(tmp_path):
    body = "# the importer upserts idempotently and writes atomically\n"
    f = _run(tmp_path, "j.py", body)
    assert f.ok


def test_word_inside_identifier_not_flagged(tmp_path):
    # 'justify' contains 'just' but the whole-word matcher must not flag it.
    f = _run(tmp_path, "k.ts", "const style = { justifyContent: 'center' };\n")
    assert f.ok


# --- invariant: allowlist and hedge sets are disjoint ------------------------
def test_allowlist_and_hedges_disjoint():
    assert not (la.HEDGES & la.ALLOW_TECHNICAL)


# --- sabotage: prove the audit can fail --------------------------------------
def test_sabotage_known_hedge_is_caught(tmp_path):
    f = _run(tmp_path, "sab.py", "# this is just simply basically actually wrong\n")
    # Four distinct hedges on one line must all be reported.
    words = {i.word for i in f.items}
    assert {"just", "simply", "basically", "actually"} <= words
