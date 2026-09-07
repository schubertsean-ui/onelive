"""`python worker/run_once.py` puts worker/ on sys.path[0].

A package named `locale` there shadows the stdlib. argparse → gettext
then crashes: AttributeError: module 'locale' has no attribute 'normalize'.
Ingest and autopromote die before any fetch. This test is the lock.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "worker"


def test_worker_top_level_does_not_use_stdlib_names():
    stdlib = sys.stdlib_module_names
    hits = []
    for p in WORKER.iterdir():
        if p.suffix in {".txt", ".lock"}:
            continue
        name = p.name if p.is_dir() else p.stem
        if name.startswith("_"):
            continue
        if name in stdlib:
            hits.append(name)
    assert hits == [], (
        f"worker/ shadows stdlib {hits}. `python worker/*.py` then "
        "imports the wrong module. Ingest/autopromote never start. "
        "Rename the package."
    )


def test_simulating_worker_script_still_gets_stdlib_locale():
    code = (
        "import sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "sys.modules.pop('locale', None)\n"
        "import locale\n"
        "assert hasattr(locale, 'normalize'), locale\n"
        "print(locale.__file__)\n"
    )
    r = subprocess.run(
        [sys.executable, "-c", code, str(WORKER)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "normalize" not in (r.stderr or "")
    # Must be CPython's locale, not a tree package.
    assert "lib" in r.stdout.replace("\\", "/")
