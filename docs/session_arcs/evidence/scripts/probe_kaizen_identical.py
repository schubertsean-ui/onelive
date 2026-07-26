#!/usr/bin/env python3
"""Prove the kaizen_trends memoization changed SPEED only, not OUTPUT.

Loads the pre-memoization copy (from the commit before the change) and the
current working copy into one process, runs both over the real ledger, and
asserts the full report string and findings list are equal.

Run from the repo root:
    git show 077dfd0:tools/kaizen_trends.py > /tmp/kt_pre.py
    python docs/session_arcs/evidence/scripts/probe_kaizen_identical.py

077dfd0 is the commit immediately BEFORE 80b5ed1, which introduced the
lru_cache. `HEAD` would be the post-change copy — naming HEAD as the
"pre-change copy" was an error in the first version of this evidence file.
"""
import importlib.util
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


root = pathlib.Path(__file__).resolve().parents[4]
text = (root / "docs/metrics/KAIZEN_LEDGER.md").read_text(encoding="utf-8")
pre = load("kt_pre", "/tmp/kt_pre.py")
cur = load("kt_cur", str(root / "tools/kaizen_trends.py"))

t = time.perf_counter(); r_pre, f_pre = pre.build_report(text); dt_pre = time.perf_counter() - t
t = time.perf_counter(); r_cur, f_cur = cur.build_report(text); dt_cur = time.perf_counter() - t

print("report identical:", r_pre == r_cur)
print("findings identical:", f_pre == f_cur)
print(f"pre {dt_pre:.3f}s -> current {dt_cur:.3f}s")
