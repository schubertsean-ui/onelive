#!/usr/bin/env python3
"""Compute the ARMED CRON's runtime file set — everything a change to which can
alter what `.github/workflows/ingest.yml` runs after a smoke run.

WHY: the arming-evidence binding (tests/test_arming_smoke_binding.py) guarantees
the code the ARMED ingestion cron runs is byte-identical to the code a paid smoke
run exercised. The original classifier was a coarse denylist (everything except
docs/tests/design is "runtime"), which mis-classified code the cron never runs —
the consumer web app, SQL migrations, the deterministic licensed-feed importer —
as cron runtime and demanded a paid re-smoke for changes that cannot affect it.

The runtime set here is computed precisely AND fail-closed:
  1. the transitive first-party import CLOSURE of the scripts ingest.yml runs
     (incl. `from pkg import submodule` submodule forms, relative imports, and
     every parent package `__init__.py` Python executes on the way in);
  2. an explicit registry of non-import cron inputs (_EXTRA_RUNTIME) — EMPTY
     today, because the cron reads no repo data/config file by path. Static
     analysis cannot exhaustively detect constructed paths (`ROOT / "x" / "y"`,
     assigned constants, joins), so rather than a FALSE completeness claim this
     is an explicit list; any future data input the cron reads MUST be added;
  3. the dependency manifests the workflow installs (`pip install -r <file>`);
  4. ingest.yml itself.

Fail-closed guarantees (the evidence gate must never silently under-include):
  * a workflow-DECLARED input (an invoked script or a `-r` requirements file)
    that is MISSING at head raises MissingRuntimeInput — a declared runtime input
    disappearing is a runtime change, not something to drop;
  * a dynamic import (`importlib`/`__import__`) anywhere in the closure raises
    DynamicImportError (detected via AST, so comments/docstrings never trip it).
Over-inclusion is fail-closed and harmless. The KNOWN scope limit is data files
the cron reads by a constructed (non-literal) path — covered by _EXTRA_RUNTIME,
not by guesswork.

Exit 0 and print the sorted set; exit 2 (fail closed) on a dynamic import or a
missing declared input.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
INGEST = ROOT / ".github" / "workflows" / "ingest.yml"

# Explicit registry of NON-import cron runtime inputs (data/config files the
# armed cron reads by a path static analysis cannot exhaustively resolve).
# EMPTY today — the cron reads no repo data file. Add a repo-relative posix path
# here the moment the cron path starts reading one, so its change/deletion
# re-fires the arming binding. Honest and explicit beats a false completeness
# claim over constructed paths.
_EXTRA_RUNTIME: tuple[str, ...] = ()


class DynamicImportError(RuntimeError):
    """A closure file uses a dynamic import; the static closure cannot be proven
    complete — fail closed."""


class MissingRuntimeInput(RuntimeError):
    """A workflow-declared runtime input (invoked script / requirements file) is
    absent at head — a runtime change, fail closed."""


def _strip_yaml_comments(text: str) -> str:
    return re.sub(r"(?m)(?:^|\s)#.*$", "", text)


def _invoked_scripts(workflow_text: str) -> list[str]:
    return sorted(set(re.findall(r"python3?\s+(\S+\.py)\b", workflow_text)))


def _with_package_inits(pyfile: pathlib.Path) -> list[pathlib.Path]:
    """The file plus every parent-package __init__.py Python runs to import it."""
    out = [pyfile]
    try:
        pyfile.relative_to(ROOT)
    except ValueError:
        return out
    d = pyfile.parent
    while d != ROOT and d.is_relative_to(ROOT):
        init = d / "__init__.py"
        if init.exists():
            out.append(init)
        d = d.parent
    return out


def _module_to_path(mod: str) -> pathlib.Path | None:
    rel = mod.replace(".", "/")
    for cand in (ROOT / f"{rel}.py", ROOT / rel / "__init__.py"):
        if cand.exists():
            return cand
    return None


def _resolve_relative(pyfile: pathlib.Path, module: str | None, level: int) -> str | None:
    pkg_parts = pyfile.relative_to(ROOT).parent.parts
    base = list(pkg_parts[: len(pkg_parts) - (level - 1)]) if level >= 1 else list(pkg_parts)
    if module:
        base += module.split(".")
    return ".".join(base) if base else None


def _is_dynamic_import(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name == "importlib" or a.name.startswith("importlib.") for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module == "importlib" or node.module.startswith("importlib")):
                return True
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id == "__import__":
                return True
            if isinstance(f, ast.Attribute) and f.attr == "import_module":
                return True
    return False


def _imported_modules(pyfile: pathlib.Path) -> list[str]:
    tree = ast.parse(pyfile.read_text())
    if _is_dynamic_import(tree):
        try:
            disp = pyfile.relative_to(ROOT).as_posix()
        except ValueError:
            disp = pyfile.name
        raise DynamicImportError(
            f"{disp} uses a dynamic import (importlib/__import__); the arming "
            "runtime closure cannot be proven complete. Make the cron path's "
            "imports static, or extend tools/arming_runtime.py."
        )
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = (_resolve_relative(pyfile, node.module, node.level)
                    if node.level and node.level > 0 else node.module)
            if base:
                mods.append(base)
                # `from pkg import submod` — submod may be a first-party module
                # FILE, not just an attribute; record both.
                for alias in node.names:
                    mods.append(f"{base}.{alias.name}")
    return mods


def runtime_files() -> set[str]:
    text = _strip_yaml_comments(INGEST.read_text())

    # (1) import closure of the invoked scripts — declared inputs MUST exist.
    stack: list[pathlib.Path] = []
    for s in _invoked_scripts(text):
        p = ROOT / s
        if not p.is_file():
            raise MissingRuntimeInput(
                f"ingest.yml invokes {s} but it is missing at head — the armed "
                "cron is broken/changed; fail closed."
            )
        stack.append(p)

    seen: set[pathlib.Path] = set()
    while stack:
        f = stack.pop()
        if f in seen:
            continue
        seen.add(f)
        for mod in _imported_modules(f):
            mp = _module_to_path(mod)
            if mp is not None:
                for inc in _with_package_inits(mp):
                    if inc not in seen:
                        stack.append(inc)

    rels = {p.relative_to(ROOT).as_posix() for p in seen}
    # (2) explicit non-import cron inputs (empty today; honest > guessed).
    rels |= set(_EXTRA_RUNTIME)

    # (3) dependency manifests the workflow installs — declared inputs MUST exist.
    for reqf in re.findall(r"-r\s+(\S+)", text):
        p = ROOT / reqf
        if not p.is_file():
            raise MissingRuntimeInput(
                f"ingest.yml installs -r {reqf} but it is missing at head; fail closed."
            )
        rels.add(p.relative_to(ROOT).as_posix())

    rels.add(".github/workflows/ingest.yml")
    return rels


def main(argv=None) -> int:
    try:
        paths = sorted(runtime_files())
    except (DynamicImportError, MissingRuntimeInput) as exc:
        print(f"arming_runtime: FAIL CLOSED — {exc}", file=sys.stderr)
        return 2
    for p in paths:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
