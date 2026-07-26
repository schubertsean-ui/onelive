#!/usr/bin/env python3
"""Name the environment faults that make the gate red for reasons that are not code.

v1 done-criterion 3 / BAR G5 / R-058. The gate used to fail four rows in a default
environment because three interpreter packages were missing and the clone was
shallow — and it reported those in the same red column as a real regression, which
teaches people to scan past red.

**This tool loosens nothing.** It is informational and always exits 0. A check that
fails still FAILS and `tools/validate` still exits non-zero; the only thing that
changes is that the reader can tell *why* a row is red without guessing. Making a
genuine failure report as an environment fault would be a gate relaxation, which is
founder-crucial — so this deliberately reports alongside the gate rather than
deciding anything for it.

Two classes, because they have different fixes:

- **MISSING-TOOL** — a package in `requirements-dev.txt` is not importable. Fix:
  `bash tools/bootstrap_dev.sh`.
- **UNPROVABLE-HERE** — the clone is shallow, so `tests/test_arming_smoke_binding.py`
  cannot reach the history it must bind evidence to. It fails CLOSED by design
  (R-036), which is correct and is not a defect. Fix: `git fetch --unshallow`.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# import name -> what installs it. Import names differ from distribution names often
# enough that guessing is wrong (PyYAML/yaml, PyJWT/jwt, psycopg2-binary/psycopg2).
DEV_IMPORTS: dict[str, str] = {
    "pytest": "pytest",
    "xdist": "pytest-xdist",
    "yaml": "PyYAML",
    "fastapi": "fastapi",
    "httpx": "httpx",
    # The SUBMODULE, not the top-level package, and the difference is the whole
    # lesson of 2026-07-26: on the broken image `import cryptography` succeeded
    # while `import cryptography.hazmat.primitives.asymmetric.ec` — the exact
    # import PyJWT performs — panicked in the Rust bindings. Probing the shallow
    # name is how this tool certified a sound environment three gate rows after
    # it had already failed. Probe what the code actually imports.
    "cryptography.hazmat.primitives.asymmetric.ec": "cryptography",
    "jwt": "PyJWT[crypto]",
    "psycopg2": "psycopg2-binary",
    "pydantic": "pydantic",
    "dateutil": "python-dateutil",
    "requests": "requests",
    "uvicorn": "uvicorn[standard]",
    "sentry_sdk": "sentry-sdk",
    "anthropic": "anthropic",
}


def _imports_cleanly(name: str) -> bool:
    """Whether `import <name>` actually SUCCEEDS in a fresh interpreter.

    Deliberately not `importlib.util.find_spec`, and deliberately a subprocess.

    `find_spec` answers "can this module be LOCATED", which is a strictly weaker
    question than "does it work", and the gap is not theoretical: this tool
    printed "every dev dependency importable — any red row below is about the
    CODE" on 2026-07-26 while three gate rows were red because `import jwt`
    raised. A broken distro `cryptography` was locatable, so `find_spec` said
    yes; importing it panicked in its Rust extension for a missing
    `_cffi_backend`. A check that reports an environment as sound while the
    environment is unsound is the false-confidence defect this file exists to
    prevent, aimed at itself.

    The subprocess is load-bearing for the same reason. That failure surfaced as
    a `pyo3_runtime.PanicException` from a Rust panic — a class of import
    failure that can abort the interpreter outright rather than raise something
    catchable. Importing in-process would risk taking the preflight down with
    it, so each import is isolated and judged only by its exit status.
    """
    try:
        proc = subprocess.run(
            [sys.executable, "-c", f"import {name}"],
            capture_output=True, text=True, timeout=120, cwd=str(_REPO_ROOT))
    except (OSError, subprocess.SubprocessError):
        # Could not even run the probe: report missing rather than assume good.
        return False
    return proc.returncode == 0


def missing_imports() -> list[tuple[str, str]]:
    """(import name, installs-with) for every dev dependency not importable here."""
    return [(name, dist) for name, dist in DEV_IMPORTS.items()
            if not _imports_cleanly(name)]


def is_shallow() -> bool | None:
    """True/False, or None when git itself could not answer."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT), timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() == "true"


def report() -> tuple[list[str], list[str]]:
    """Return (missing-tool lines, unprovable-here lines)."""
    tools = [f"MISSING-TOOL     {name} (install: {dist})"
             for name, dist in missing_imports()]
    unprovable: list[str] = []
    shallow = is_shallow()
    if shallow is True:
        unprovable.append(
            "UNPROVABLE-HERE  shallow clone — tests/test_arming_smoke_binding.py "
            "cannot reach the history it binds evidence to, so it fails CLOSED by "
            "design (R-036). That is correct behaviour, not a defect.")
    elif shallow is None:
        unprovable.append(
            "UNPROVABLE-HERE  could not ask git whether the clone is shallow — "
            "reported rather than assumed either way.")
    return tools, unprovable


def main() -> int:
    tools, unprovable = report()
    if not tools and not unprovable:
        print("env_preflight: OK — every dev dependency importable, full history "
              "present. Any red row below is about the CODE.")
        return 0

    print("env_preflight: this environment is incomplete. The rows below are NOT "
          "code defects, and they do NOT change the gate's verdict — a failing "
          "check still fails. They exist so you can tell the difference.")
    for line in tools + unprovable:
        print(f"  {line}")
    if tools:
        print("  FIX ALL MISSING-TOOL ROWS WITH: bash tools/bootstrap_dev.sh")
    if any("shallow clone" in u for u in unprovable):
        print("  FIX THE SHALLOW CLONE WITH:      git fetch --unshallow")
    # Always 0: this is a lens on the gate, never a gate. Exiting non-zero here
    # would make an incomplete environment block, which is not what it means.
    return 0


if __name__ == "__main__":
    sys.exit(main())
