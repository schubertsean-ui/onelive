#!/usr/bin/env python3
"""Compute the ARMED CRON's runtime file set — the transitive first-party import
closure of the scripts that `.github/workflows/ingest.yml` executes, plus the
ingest workflow file itself.

WHY: the arming-evidence binding (tests/test_arming_smoke_binding.py) exists to
guarantee the code the ARMED ingestion cron runs is byte-identical to the code a
paid smoke run exercised. Its original classifier was a coarse denylist
(everything except docs/tests/design is "runtime"), which mis-classified the
consumer web app, SQL migrations, and the deterministic licensed-feed importer —
none of which the cron runs — as cron runtime, and demanded a paid re-smoke for
changes that cannot affect the armed cron. This computes the TRUE runtime set so
the binding fires precisely on the code the cron actually executes.

NOT fail-open: the set is the real import closure, so anything the cron begins to
import is included automatically. The one static-analysis blind spot — dynamic
imports (`importlib`, `__import__`) inside the closure — is failed LOUD (a
DynamicImportError naming the file) rather than silently under-included, so the
binding degrades closed, never open.

Exit 0 and print the sorted runtime set when run directly (for inspection/CI).
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
INGEST = ROOT / ".github" / "workflows" / "ingest.yml"


class DynamicImportError(RuntimeError):
    """A runtime-closure file uses a dynamic import; the static closure cannot be
    trusted to be complete, so the binding must not proceed (fail closed)."""


def _invoked_scripts(workflow_text: str) -> list[str]:
    """Repo-relative .py paths invoked as `python[3] <path>` in the workflow."""
    return sorted(set(re.findall(r"python3?\s+(\S+\.py)\b", workflow_text)))


def _module_to_path(mod: str) -> pathlib.Path | None:
    """Resolve a first-party dotted module to a repo file, or None if it is not
    first-party (stdlib / site-packages resolve to nothing under ROOT)."""
    rel = mod.replace(".", "/")
    for cand in (ROOT / f"{rel}.py", ROOT / rel / "__init__.py"):
        if cand.exists():
            return cand
    return None


def _resolve_relative(pyfile: pathlib.Path, module: str | None, level: int) -> str | None:
    """Resolve a `from . import x` style module to an absolute dotted name."""
    pkg_parts = pyfile.relative_to(ROOT).parent.parts
    # level 1 = current package; level 2 = parent; ...
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
            f"{disp} uses a dynamic import "
            "(importlib/__import__); the arming runtime closure cannot be proven "
            "complete. Resolve by making the cron path's imports static, or "
            "extend tools/arming_runtime.py to enumerate the dynamic target."
        )
    tree = ast.parse(src)
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                resolved = _resolve_relative(pyfile, node.module, node.level)
                if resolved:
                    mods.append(resolved)
            elif node.module:
                mods.append(node.module)
    return mods


def runtime_files() -> set[str]:
    """The set of repo-relative posix paths the armed cron runs."""
    text = INGEST.read_text()
    stack = [ROOT / s for s in _invoked_scripts(text) if (ROOT / s).exists()]
    seen: set[pathlib.Path] = set()
    while stack:
        f = stack.pop()
        if f in seen:
            continue
        seen.add(f)
        for mod in _imported_modules(f):
            mp = _module_to_path(mod)
            if mp is not None and mp not in seen:
                stack.append(mp)
    rels = {p.relative_to(ROOT).as_posix() for p in seen}
    rels.add(".github/workflows/ingest.yml")
    return rels


def main(argv=None) -> int:
    for p in sorted(runtime_files()):
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
