#!/usr/bin/env python3
"""Deterministic language-audit gate for OneLive (OPERATING_RULES.md §1c).

Prose is a build artifact. A truth-first product's voice must not hedge: hedging
adverbs and vague qualifiers soften claims the text should either make or drop.
This gate enforces §1c the same way tools/trust_gate.py enforces trust
invariants — as a hermetic, in-repo static check that gives the same answer every
run, so the rule cannot quietly regress.

What it scans (the audited surfaces named in §1c):
  * Python  — comments and docstrings.
  * TS/TSX/JS/MJS — line and block comments, plus JSX text and string literals.
  * Markdown — prose (fenced code blocks and inline code are exempt: code is code).

What it flags: a fixed set of hedging/filler adverbs and qualifiers (see HEDGES).

What it does NOT flag (to stay precise, never a blunt instrument):
  * The technical-adverb allowlist (ALLOW_TECHNICAL): words that state a real
    engineering property (idempotently, atomically, explicitly, loudly, ...).
  * Legitimate multi-word constructions the bare word would false-positive on —
    e.g. "rather than" (contrastive), "just in time", "as such". See CONTEXT_OK.
  * Files outside the repo's own authored surface (vendored deps, build output,
    lockfiles, this repo's copied skills, session context).

Exit codes: 0 = clean; 1 = at least one finding (printed as file:line: word —
line text, so each is actionable). Fail loud, never a vague "audit failed".

Usage:
  python tools/language_audit.py                 # audit the whole repo
  python tools/language_audit.py path [path ...] # audit specific paths
"""
from __future__ import annotations

import io
import pathlib
import re
import sys
import tokenize
from dataclasses import dataclass, field

REPO = pathlib.Path(__file__).resolve().parent.parent

# --- What counts as a defect ------------------------------------------------
# Hedging / filler adverbs and qualifiers. Lower-cased; matched whole-word.
HEDGES: frozenset[str] = frozenset(
    {
        "just",
        "simply",
        "quickly",
        "basically",
        "honestly",
        "actually",
        "really",
        "very",
        "merely",
        "obviously",
        "clearly",
        "essentially",
        "literally",
        "truly",
        "totally",
        "completely",
        "extremely",
        "incredibly",
        "somewhat",
        "quite",
        "definitely",
        "certainly",
        "arguably",
        "fairly",
    }
)

# Adverbs kept when they state a genuine engineering property (§1c exception).
# Present here for documentation and so a future edit cannot add them to HEDGES
# without tripping the self-test in tests/test_language_audit.py.
ALLOW_TECHNICAL: frozenset[str] = frozenset(
    {
        "idempotently",
        "atomically",
        "explicitly",
        "loudly",
        "verbatim",
        "deterministically",
        "hermetically",
        "synchronously",
        "asynchronously",
        "statically",
    }
)

# A hedge word is exempt on a given line when it is part of one of these
# lower-cased multi-word constructions (checked as a substring of the line).
# These are legitimate grammar, not hedging.
CONTEXT_OK: tuple[str, ...] = (
    "rather than",
    "just in time",
    "just-in-time",
    "as such",
)

# Files/dirs never audited: not this repo's authored prose.
SKIP_DIR_PARTS = {
    ".git",
    "node_modules",
    ".next",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    ".venv",
    "venv",
    "skills",  # copied skill libraries are not our prose
    "current_session_context",
    "past_session_contexts",
    "qa",  # local QA harness/screenshots, not shipped prose
}
SKIP_FILE_NAMES = {"package-lock.json", "language_audit.py"}  # self-exempt: HEDGES list

PY_EXT = {".py"}
JS_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
MD_EXT = {".md"}
AUDITED_EXT = PY_EXT | JS_EXT | MD_EXT

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")


@dataclass
class Finding:
    path: str
    line: int
    word: str
    text: str


@dataclass
class Findings:
    items: list[Finding] = field(default_factory=list)

    def add(self, path: str, line: int, word: str, text: str) -> None:
        self.items.append(Finding(path, line, word, text.strip()))

    @property
    def ok(self) -> bool:
        return not self.items


def _rel(path: pathlib.Path) -> str:
    """Repo-relative path for display, or the absolute path when the file lives
    outside the repo (e.g. a tmp file under test). Never raises."""
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _iter_words(fragment: str):
    """Yield lower-cased whole words in a text fragment."""
    for m in _WORD_RE.finditer(fragment):
        yield m.group(0).lower()


def _line_is_context_ok(line_lower: str, word: str) -> bool:
    """True if `word` on this line is part of an allowed multi-word construction."""
    for phrase in CONTEXT_OK:
        if word in phrase.split() and phrase in line_lower:
            return True
    return False


def _flag_fragment(fragment: str, base_line: int, path: str, lines: list[str], f: Findings) -> None:
    """Flag hedges in a text fragment. `base_line` is the 1-based line of the
    fragment start; findings are attributed to the fragment's own line via the
    full-line lookup so the printed context is the real source line."""
    for offset, frag_line in enumerate(fragment.splitlines() or [fragment]):
        lineno = base_line + offset
        line_lower = frag_line.lower()
        for word in _iter_words(frag_line):
            if word in HEDGES and not _line_is_context_ok(line_lower, word):
                src = lines[lineno - 1] if 0 <= lineno - 1 < len(lines) else frag_line
                f.add(path, lineno, word, src)


def audit_python(path: pathlib.Path, f: Findings) -> None:
    """Flag hedges in Python comments and docstrings (not in executable code
    identifiers — those are covered by review; strings that are docstrings are)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    rel = _rel(path)
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Fall back to a comment-only scan if the file will not tokenize.
        for i, line in enumerate(lines, start=1):
            hash_at = line.find("#")
            if hash_at >= 0:
                _flag_fragment(line[hash_at:], i, rel, lines, f)
        return

    # Comments always. String literals only when they are docstrings (first
    # statement of module/class/def) — approximated as a standalone string
    # expression, which is how docstrings appear at the token level.
    prev_significant = tokenize.INDENT
    for tok in toks:
        if tok.type == tokenize.COMMENT:
            _flag_fragment(tok.string, tok.start[0], rel, lines, f)
        elif tok.type == tokenize.STRING:
            # Treat as docstring when the previous significant token opens a
            # suite or is the module start (NEWLINE/INDENT/DEDENT/colon-block).
            if prev_significant in (
                tokenize.INDENT,
                tokenize.NEWLINE,
                tokenize.NL,
                tokenize.DEDENT,
                tokenize.ENCODING,
            ):
                _flag_fragment(tok.string, tok.start[0], rel, lines, f)
        if tok.type not in (
            tokenize.NL,
            tokenize.COMMENT,
        ):
            prev_significant = tok.type


_JS_LINE_COMMENT = re.compile(r"//.*")
_JS_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def audit_js(path: pathlib.Path, f: Findings) -> None:
    """Flag hedges in JS/TS comments, string literals, and JSX text.

    We scan the whole file text for the hedge words but exempt nothing by syntax
    here beyond what CONTEXT_OK covers: in a UI file, hedging in visible copy is
    exactly what §1c targets, and hedging in a comment is also a defect. The only
    false-positive risk is a hedge word inside an identifier, which the
    whole-word regex avoids (identifiers like `justify` are not the word `just`).
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    rel = _rel(path)
    for i, line in enumerate(lines, start=1):
        line_lower = line.lower()
        for word in _iter_words(line):
            if word in HEDGES and not _line_is_context_ok(line_lower, word):
                f.add(rel, i, word, line)


_MD_FENCE = re.compile(r"^```")
_MD_INLINE_CODE = re.compile(r"`[^`]*`")


def audit_markdown(path: pathlib.Path, f: Findings) -> None:
    """Flag hedges in Markdown prose. Fenced code blocks and inline code spans
    are exempt (code is code, held to the code rule, not the prose rule)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    rel = _rel(path)
    in_fence = False
    for i, line in enumerate(lines, start=1):
        if _MD_FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        prose = _MD_INLINE_CODE.sub(" ", line)  # drop inline code spans
        line_lower = prose.lower()
        for word in _iter_words(prose):
            if word in HEDGES and not _line_is_context_ok(line_lower, word):
                f.add(rel, i, word, line)


def _should_skip(path: pathlib.Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIR_PARTS:
        return True
    if path.name in SKIP_FILE_NAMES:
        return True
    return False


def audit_path(path: pathlib.Path, f: Findings) -> None:
    ext = path.suffix.lower()
    if ext in PY_EXT:
        audit_python(path, f)
    elif ext in JS_EXT:
        audit_js(path, f)
    elif ext in MD_EXT:
        audit_markdown(path, f)


def collect_files(roots: list[pathlib.Path]) -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for root in roots:
        if root.is_file():
            if root.suffix.lower() in AUDITED_EXT and not _should_skip(root):
                out.append(root)
            continue
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.suffix.lower() in AUDITED_EXT and not _should_skip(p):
                out.append(p)
    return out


def run(roots: list[pathlib.Path]) -> Findings:
    f = Findings()
    for path in collect_files(roots):
        audit_path(path, f)
    return f


def main(argv: list[str]) -> int:
    roots = [pathlib.Path(a).resolve() for a in argv[1:]] or [REPO]
    f = run(roots)
    if f.ok:
        print("language_audit: OK — no hedging/filler adverbs in audited prose.")
        return 0
    for item in f.items:
        print(f"{item.path}:{item.line}: '{item.word}' — {item.text}")
    print(f"\nlanguage_audit: {len(f.items)} finding(s). "
          f"Remove the hedging word or, if it states a real engineering property, "
          f"use the precise term (see OPERATING_RULES.md §1c).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
