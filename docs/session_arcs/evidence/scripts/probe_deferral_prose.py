#!/usr/bin/env python3
"""Measure what extending deferral_scan over PROSE would fire on.

tools/deferral_scan.py deliberately scans code comments only. This counts what
it would flag in the session-facing prose docs, and prints each hit so the
true/false split can be judged rather than assumed.

Run from the repo root:
    python docs/session_arcs/evidence/scripts/probe_deferral_prose.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))
from tools.deferral_scan import PHRASES  # noqa: E402

for name in ("STATE.md", "TODOS.md"):
    text = pathlib.Path(name).read_text(encoding="utf-8")
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        for phrase in PHRASES:
            if phrase in low:
                hits.append((i, phrase, line.strip()[:110]))
                break
    print(f"{name}: {len(hits)} lines would fire, of {len(text.splitlines())}")
    for i, phrase, snippet in hits:
        print(f"   L{i} [{phrase}] {snippet}")
