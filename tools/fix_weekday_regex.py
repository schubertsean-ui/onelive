#!/usr/bin/env python3
from pathlib import Path
p = Path("worker/locale_pack/desk_read.py")
t = p.read_text()
old = r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.?,?\s+"
new = (
    r"\b(Mon(?:day)?|Tue(?:sday)?|Wed(?:nesday)?|"
    r"Thu(?:rsday)?|Fri(?:day)?|Sat(?:urday)?|Sun(?:day)?)\.?,?\s+"
)
if old not in t:
    if new in t:
        print("already applied")
        raise SystemExit(0)
    raise SystemExit("regex block missing")
p.write_text(t.replace(old, new, 1))
print("weekday regex expanded")
