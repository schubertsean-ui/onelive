#!/usr/bin/env python3
"""Compute the ARMED CRON's runtime file set — everything a change to which can
alter what `.github/workflows/ingest.yml` runs after a smoke run.

WHY: the arming-evidence binding (tests/test_arming_smoke_binding.py) guarantees
the code the ARMED ingestion cron runs is byte-identical to the code a paid smoke
run exercised. Its original classifier was a coarse denylist (everything except
docs/tests/design is "runtime"), which mis-classified code the cron never runs —
the consumer web app, SQL migrations, the deterministic licensed-feed importer —
as cron runtime and demanded a paid re-smoke for changes that cannot affect it.

The runtime set here is the union of THREE precisely-computed parts, so it is
neither over-broad (the false-positive money-burn) nor fail-open:
  1. the transitive first-party import CLOSURE of the scripts ingest.yml runs
     (run_once.py, assemble_dsn.py, assert_deadman_period.py) — including
     `from pkg import submodule` submodule forms and relative imports;
  2. every repo file the workflow itself REFERENCES (e.g. `pip install -r
     worker/requirements.txt`, CLI data args, invoked scripts) — the workflow is
     the authoritative declaration of the cron's inputs, so a dependency-manifest
     or data-arg change re-fires the binding;
  3. any DATA/CONFIG file (json/yaml/csv/lock/txt/ini/toml/sql) referenced by
     literal path inside a closure source file — a data input the code reads.
Plus ingest.yml itself (so any change to how it invokes/install steps re-fires).

Not fail-open: anything the cron imports/installs/reads-by-literal-path is
included automatically; the one static blind spot — dynamic imports
(`importlib`/`__import__`) in the closure — fails LOUD (DynamicImportError)
rather than silently under-including. Over-inclusion (a data path mentioned in
source) is fail-closed and harmless.

Exit 0 and print the sorted runtime set when run directly; exit 2 (fail closed)
if the closure hits a dynamic import.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
INGEST = ROOT / ".github" / "workflows" / "ingest.yml"

# Data/config extensions whose literal references in cron source are runtime
# inputs (code deps are handled by the import graph; .md/.py excluded to avoid
# docstring/comment noise).
_DATA_EXT = (".json", ".yaml", ".yml", ".csv", ".lock", ".txt", ".ini", ".toml", ".sql")
_PATH_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.[A-Za-z0-9]+")


class DynamicImportError(RuntimeError):
    """A runtime-closure file uses a dynamic import; the static closure cannot be
    trusted complete, so the binding must not proceed (fail closed)."""


def _strip_yaml_comments(text: str) -> str:
    """Drop YAML line comments (`#` at line start or after whitespace) so file
    paths mentioned only in comments are not mistaken for cron inputs."""
    return re.sub(r"(?m)(?:^|\s)#.*$", "", text)


def _invoked_scripts(workflow_text: str) -> list[str]:
    return sorted(set(re.findall(r"python3?\s+(\S+\.py)\b", workflow_text)))


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


def _imported_modules(pyfile: pathlib.Path) -> list[str]:
    src = pyfile.read_text()
    if re.search(r"\bimportlib\b|\b__import__\s*\(", src):
        try:
            disp = pyfile.relative_to(ROOT).as_posix()
        except ValueError:
            disp = pyfile.name
        raise DynamicImportError(
            f"{disp} uses a dynamic import (importlib/__import__); the arming "
            "runtime closure cannot be proven complete. Resolve by making the "
            "cron path's imports static, or extend tools/arming_runtime.py to "
            "enumerate the dynamic target."
        )
    tree = ast.parse(src)
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                base = _resolve_relative(pyfile, node.module, node.level)
            else:
                base = node.module
            if base:
                mods.append(base)
                # `from pkg import submod` — submod may be a first-party module
                # FILE, not just an attribute; record both so a submodule the
                # cron imports is never omitted from the closure.
                for alias in node.names:
                    mods.append(f"{base}.{alias.name}")
    return mods


def _referenced_files(text: str, data_only: bool = False) -> set[pathlib.Path]:
    """Repo files whose relative path appears verbatim in `text`. When
    data_only, keep only data/config extensions (used for scanning source, where
    code deps are already covered by the import graph)."""
    out: set[pathlib.Path] = set()
    for m in _PATH_RE.findall(text):
        if data_only and not m.lower().endswith(_DATA_EXT):
            continue
        p = ROOT / m
        if p.is_file():
            out.add(p)
    return out


def runtime_files() -> set[str]:
    """The set of repo-relative posix paths a change to which can alter the
    armed cron's behavior."""
    text = _strip_yaml_comments(INGEST.read_text())
    seen: set[pathlib.Path] = set()

    # (1) import closure of the invoked scripts
    stack = [ROOT / s for s in _invoked_scripts(text) if (ROOT / s).exists()]
    while stack:
        f = stack.pop()
        if f in seen:
            continue
        seen.add(f)
        for mod in _imported_modules(f):
            mp = _module_to_path(mod)
            if mp is not None and mp not in seen:
                stack.append(mp)

    # (3) data/config files referenced by literal path inside closure sources
    data_refs: set[pathlib.Path] = set()
    for f in list(seen):
        data_refs |= _referenced_files(f.read_text(), data_only=True)

    # (2) dependency manifests the workflow installs (`pip install -r <file>`)
    # — the concrete non-code runtime input. (Invoked scripts are already in the
    # closure; any other invocation change is a change to ingest.yml, which is in
    # the set below, so it re-fires regardless.)
    rels = {p.relative_to(ROOT).as_posix() for p in (seen | data_refs)}
    for reqf in re.findall(r"-r\s+(\S+)", text):
        p = ROOT / reqf
        if p.is_file():
            rels.add(p.relative_to(ROOT).as_posix())
    rels.add(".github/workflows/ingest.yml")
    return rels


def main(argv=None) -> int:
    try:
        paths = sorted(runtime_files())
    except DynamicImportError as exc:
        print(f"arming_runtime: FAIL CLOSED — {exc}", file=sys.stderr)
        return 2
    for p in paths:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
