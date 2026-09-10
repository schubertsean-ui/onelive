#!/usr/bin/env python3
from pathlib import Path
p = Path("worker/locale_pack/desk_publish.py")
t = p.read_text()
old = """    if not stored:
        return []
"""
new = """    if not stored:
        return [field for field in WATCHED if fresh.get(field)]
"""
if old not in t:
    if "WATCHED if fresh.get(field)" in t:
        print("already applied")
        raise SystemExit(0)
    raise SystemExit("drift absent block missing")
p.write_text(t.replace(old, new, 1))
print("drift treats missing statement as change when fields arrive")
