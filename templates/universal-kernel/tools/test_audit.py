#!/usr/bin/env python3
"""False-confidence test audit — AST scan of tests/ for tests that assert nothing.

Pure stdlib. A green suite only means something if every passing test can
actually fail. This scans tests/*.py for the shapes that let a test pass
without proving anything: zero assert/raises/approx calls, only trivially-
true assertions (assert True / assert 1==1), a body that's just `pass`,
overly-broad `pytest.raises(Exception)` (catches anything, proves little),
and Mock/MagicMock objects that are asserted on (assert_called*) but never
actually invoked in the test body. Reports per-file. `--strict` -> exit 1 on
any finding; otherwise advisory (exit 3). Never silently "fixes" a test it
flags — surfacing false confidence is the whole point.
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import sys
from dataclasses import dataclass, field

REPO = pathlib.Path(__file__).resolve().parent.parent
TESTS_DIR = REPO / "tests"

_ASSERT_LIKE_CALLS = {
    "raises", "approx", "warns", "deprecated_call", "approx_equal",
}
_MOCK_ASSERT_METHODS_PREFIX = "assert_"
_MOCK_CALL_METHODS = {"called", "call_count", "call_args", "call_args_list", "mock_calls"}


@dataclass
class Findings:
    items: list[str] = field(default_factory=list)

    def add(self, msg: str) -> None:
        self.items.append(msg)

    def ok(self) -> bool:
        return not self.items


# BOTH of pytest's default collection patterns (PR #75 r12, class
# self-weakenable-gate). Auditing only `test_*.py` meant an adopting project
# could add `foo_test.py` — which pytest DOES collect — and this gate against
# tests-that-cannot-fail would never look at it. A false-confidence audit
# bypassable by filename is worse than none, because it reads as coverage.
COLLECTION_PATTERNS = ("test_*.py", "*_test.py")


def _files_under(directory: pathlib.Path) -> list[pathlib.Path]:
    if not directory.exists():
        return []
    found = set()
    for pattern in COLLECTION_PATTERNS:
        found.update(p for p in directory.rglob(pattern)
                     if "__pycache__" not in p.parts)
    return sorted(found)


def _test_files() -> list[pathlib.Path]:
    return _files_under(TESTS_DIR)


def _is_test_func(node: ast.AST) -> bool:
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")


def _iter_test_funcs(tree: ast.Module):
    for node in ast.walk(tree):
        if _is_test_func(node):
            yield node


def _is_trivially_true(node: ast.Assert) -> bool:
    t = node.test
    if isinstance(t, ast.Constant) and t.value is True:
        return True
    if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq):
        left, right = t.left, t.comparators[0]
        if isinstance(left, ast.Constant) and isinstance(right, ast.Constant):
            return left.value == right.value  # e.g. 1 == 1, "x" == "x"
    return False


def _calls_pytest_raises_too_broadly(node: ast.AST) -> list[int]:
    """Return line numbers of `pytest.raises(Exception)` / `raises(Exception)`
    with no further narrowing (no match=...) — catches nearly everything."""
    lines = []
    for n in ast.walk(node):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        is_raises = (isinstance(f, ast.Attribute) and f.attr == "raises") or \
                    (isinstance(f, ast.Name) and f.id == "raises")
        if not is_raises or not n.args:
            continue
        arg0 = n.args[0]
        if isinstance(arg0, ast.Name) and arg0.id == "Exception":
            has_match = any(kw.arg == "match" for kw in n.keywords)
            if not has_match:
                lines.append(n.lineno)
    return lines


def _count_assert_like(node: ast.AST) -> int:
    count = 0
    for n in ast.walk(node):
        if isinstance(n, ast.Assert):
            count += 1
        elif isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
            if name in _ASSERT_LIKE_CALLS:
                count += 1
    return count


def _body_is_just_pass(node) -> bool:
    body = [b for b in node.body if not (isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant)
                                          and isinstance(b.value.value, str))]  # ignore docstring
    return len(body) == 1 and isinstance(body[0], ast.Pass)


def _mock_names_created(node: ast.AST) -> set[str]:
    """Variable names bound to a mock object. Covers both direct construction
    (`m = Mock()/MagicMock()/AsyncMock()`) and patch-based creation:
      - `m = patch(...).start()` / `m = mocker.patch(...)` / `m = mock.patch(...)`
      - `with patch(...) as m:` / `with mocker.patch(...) as m:`
    so a mock asserted-on-but-never-invoked is caught regardless of how it was
    created (the docstring and the detector are kept in lockstep on purpose)."""
    names = set()

    def _is_mock_ctor(call: ast.Call) -> bool:
        f = call.func
        fname = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
        if fname in ("Mock", "MagicMock", "AsyncMock", "patch"):
            return True
        # `patch(...).start()` — a Call whose func is an attribute `.start` on a
        # `patch(...)` / `mocker.patch(...)` / `mock.patch(...)` call.
        if isinstance(f, ast.Attribute) and f.attr == "start" and isinstance(f.value, ast.Call):
            inner = f.value.func
            iname = inner.attr if isinstance(inner, ast.Attribute) else (inner.id if isinstance(inner, ast.Name) else None)
            if iname == "patch":
                return True
        return False

    for n in ast.walk(node):
        # Plain assignment: name = <mock-producing call>
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            if isinstance(n.value, ast.Call) and _is_mock_ctor(n.value):
                names.add(n.targets[0].id)
        # Context manager: with patch(...) as name:  (and async with)
        if isinstance(n, (ast.With, ast.AsyncWith)):
            for item in n.items:
                if (isinstance(item.context_expr, ast.Call)
                        and _is_mock_ctor(item.context_expr)
                        and isinstance(item.optional_vars, ast.Name)):
                    names.add(item.optional_vars.id)
    return names


def _mock_asserted_but_never_invoked(node: ast.AST) -> list[str]:
    """Mock vars that have .assert_called*/.called checked, but the mock name
    itself is never called as a plain function anywhere else in the body."""
    mock_names = _mock_names_created(node)
    if not mock_names:
        return []
    asserted, invoked = set(), set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            base = n.func.value
            base_name = base.id if isinstance(base, ast.Name) else None
            if base_name in mock_names and n.func.attr.startswith(_MOCK_ASSERT_METHODS_PREFIX):
                asserted.add(base_name)
        if isinstance(n, ast.Attribute) and n.attr in _MOCK_CALL_METHODS:
            base = n.value
            if isinstance(base, ast.Name) and base.id in mock_names:
                asserted.add(base.id)
        # "invoked" = the mock name itself is the target of ANY call anywhere
        # (direct call, passed as a callback that's later invoked elsewhere is
        # out of static-analysis reach, so we accept the common direct-call
        # shape as the invocation signal, matching how these mocks are used
        # in this repo's test style).
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name) and f.id in mock_names:
                invoked.add(f.id)
            if isinstance(f, ast.Attribute):
                base = f.value
                if isinstance(base, ast.Name) and base.id in mock_names and not f.attr.startswith(_MOCK_ASSERT_METHODS_PREFIX) and f.attr not in _MOCK_CALL_METHODS:
                    invoked.add(base.id)  # mock_obj.some_method(...) counts as invoking it
    return sorted(asserted - invoked)


def audit_file(path: pathlib.Path, findings: Findings) -> None:
    try:
        rel = str(path.relative_to(REPO))
    except ValueError:
        rel = str(path)  # path lives outside REPO (e.g. a test fixture in tmp_path)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    except SyntaxError as exc:
        findings.add(f"{rel}: could not parse ({exc}); cannot audit.")
        return

    for func in _iter_test_funcs(tree):
        loc = f"{rel}:{func.lineno}:{func.name}"

        if _body_is_just_pass(func):
            findings.add(f"{loc}: body is just `pass` — asserts nothing, always \"passes\".")
            continue  # other checks are moot for an empty test

        n_asserts = _count_assert_like(func)
        if n_asserts == 0:
            findings.add(f"{loc}: zero assert/raises/approx calls — cannot fail, proves nothing.")

        for node in ast.walk(func):
            if isinstance(node, ast.Assert) and _is_trivially_true(node):
                findings.add(f"{rel}:{node.lineno}:{func.name}: trivially-true assertion "
                             f"(e.g. assert True / assert 1==1) — always passes regardless of code under test.")

        for lineno in _calls_pytest_raises_too_broadly(func):
            findings.add(f"{rel}:{lineno}:{func.name}: pytest.raises(Exception) with no match= "
                         f"narrowing — catches nearly any failure, so it can pass even when the "
                         f"WRONG exception (or wrong cause) is raised.")

        unused_mocks = _mock_asserted_but_never_invoked(func)
        for name in unused_mocks:
            findings.add(f"{loc}: mock '{name}' has assert_called*/.called checked but is never "
                         f"invoked in this test body — the assertion may be checking a mock that "
                         f"was never exercised (false confidence if the call site moved).")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="False-confidence test audit (AST scan of tests/).")
    ap.add_argument("--strict", action="store_true", help="Exit 1 if any finding is reported (default: advisory).")
    ap.add_argument("--tests-dir", default=None, help="Override tests/ directory (mainly for self-testing).")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])

    tests_dir = pathlib.Path(args.tests_dir) if args.tests_dir else TESTS_DIR
    files = _files_under(tests_dir)

    if not files:
        print(f"test_audit.py: no test files found under {tests_dir} — nothing to audit.", file=sys.stderr)
        return 1  # an empty/missing tests dir is itself a loud misconfig, not a clean pass

    findings = Findings()
    for f in files:
        audit_file(f, findings)

    print(f"test_audit.py: scanned {len(files)} test file(s) under {tests_dir}.")
    if findings.ok():
        print("test_audit.py: OK — no false-confidence patterns found.")
        return 0

    print(f"test_audit.py: {len(findings.items)} finding(s) "
          f"({'STRICT — will fail the run' if args.strict else 'advisory only'}):")
    for item in findings.items:
        print(f"  - {item}")

    # Exit 3 = findings, advisory (same contract as commit_sweep, evaluator
    # r13 on PR #35): validate records an honest ADVISORY row, never PASS,
    # without parsing stdout. --strict keeps exit 1.
    return 1 if args.strict else 3


if __name__ == "__main__":
    raise SystemExit(main())
