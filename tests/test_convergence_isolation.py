"""Shadow isolation for worker/convergence/, enforced BOTH directions.

The convergence package is shadow-only (spec §11: zero product-path
coupling until the founder's C5 ratification). The C1 suite's original
isolation test covered one file's outbound imports only; the pre-attack
review (PR #51) correctly called the package docstring's "imported by
nothing" claim prose-ahead-of-mechanism. This suite is the mechanism,
package-wide:

- INBOUND: no production module (worker/, api/, ai/, tools/) outside
  the package may import worker.convergence, by AST sweep.
- OUTBOUND: every file in the package may import only the Python
  standard library or package-internal modules, by AST sweep — new
  sibling files added later are covered automatically.
- DYNAMIC-IMPORT BAN: the tokens importlib/__import__ may not appear in
  package source at all — the AST sweeps read static import statements,
  and stdlib importlib would otherwise be a sanctioned evasion of them.

Honest limit: exec/eval of constructed strings could still evade an AST
sweep; those tokens are caught by ordinary review, and the package has
no business using them. The gate's guarantee is: no static import
coupling either direction, and no sanctioned dynamic-import machinery.
"""

from __future__ import annotations

import ast
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
PACKAGE = REPO / "worker" / "convergence"
PRODUCTION_DIRS = ("worker", "api", "ai", "tools")

_STDLIB = set(sys.stdlib_module_names)


def _imports_of(path: pathlib.Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import — package-internal
                continue
            if node.module:
                names.append(node.module)
    return names


def _production_py_outside_package() -> list[pathlib.Path]:
    out = []
    for d in PRODUCTION_DIRS:
        for p in (REPO / d).rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            if PACKAGE in p.parents or p.parent == PACKAGE:
                continue
            out.append(p)
    return out


def test_inbound_no_production_module_imports_convergence():
    offenders = {}
    for p in _production_py_outside_package():
        hits = [
            name
            for name in _imports_of(p)
            if name == "worker.convergence"
            or name.startswith("worker.convergence.")
        ]
        if hits:
            offenders[str(p.relative_to(REPO))] = hits
    assert offenders == {}, (
        f"shadow violation: production code imports worker.convergence "
        f"{offenders} — coupling the shadow engine into the pipeline is "
        f"the founder's C5 ratification decision, not a code change "
        f"(spec §11)"
    )


def test_outbound_every_package_file_is_stdlib_or_internal_only():
    assert PACKAGE.is_dir(), "worker/convergence vanished?"
    offenders = {}
    for p in sorted(PACKAGE.glob("*.py")):
        bad = [
            name
            for name in _imports_of(p)
            if name.split(".")[0] not in _STDLIB
            and not (
                name == "worker.convergence"
                or name.startswith("worker.convergence.")
            )
        ]
        if bad:
            offenders[p.name] = bad
    assert offenders == {}, (
        f"shadow violation: package file(s) import beyond stdlib/"
        f"package-internal {offenders} — the shadow engine may not touch "
        f"pipeline modules or third-party deps (spec §11 C1/C2 contract)"
    )


def test_dynamic_import_tokens_banned_in_package_source():
    offenders = {}
    for p in sorted(PACKAGE.glob("*.py")):
        text = p.read_text(encoding="utf-8")
        hits = [tok for tok in ("importlib", "__import__") if tok in text]
        if hits:
            offenders[p.name] = hits
    assert offenders == {}, (
        f"dynamic-import token(s) in shadow package source {offenders} — "
        f"the AST sweeps read static imports, so importlib/__import__ "
        f"would be a sanctioned evasion; the package has no business "
        f"using them"
    )


def test_sweeps_go_red_on_planted_offenders(tmp_path):
    inbound = tmp_path / "consumer.py"
    inbound.write_text("from worker.convergence import sl\n", encoding="utf-8")
    assert [
        n for n in _imports_of(inbound) if n.startswith("worker.convergence")
    ], "inbound sweep failed to see a direct import"
    outbound = tmp_path / "sneaky.py"
    outbound.write_text("import requests\n", encoding="utf-8")
    assert [
        n for n in _imports_of(outbound) if n.split(".")[0] not in _STDLIB
    ], "outbound sweep failed to see a third-party import"
