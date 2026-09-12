#!/usr/bin/env python3
"""Identity key is listing URL or title + local date. Clock and Place stay out."""
from pathlib import Path

p = Path("worker/locale_pack/desk_publish.py")
t = p.read_text()
if "return identity_key(row)" in t:
    print("ingest_key already calls identity_key")
    raise SystemExit(0)
print("ingest_key does not call identity_key — refuse to put clock+place back")
raise SystemExit(1)
