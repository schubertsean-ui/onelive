#!/usr/bin/env python3
"""Save key is listing URL plus that night. Safe to re-run."""
from pathlib import Path

p = Path("worker/locale_pack/desk_publish.py")
t = p.read_text()
if 'return f"url:{url}|{when}"' in t:
    print("ingest_key already includes when")
    raise SystemExit(0)
old = '''    if row.basis != BASIS_LOCAL:
        return row.key
    url = _listing_url(row)
    if url:
        return f"url:{url}"
    member = row.members[0]
    return f"desk:{member.via}~{member.place}~{member.title_key}"
'''
new = '''    when = (getattr(row, "night", None) or "")
    if not when:
        for member in row.members:
            if getattr(member.row, "when", None):
                when = member.row.when
                break
    if row.basis != BASIS_LOCAL:
        return f"{row.key}|{when}" if when else row.key
    url = _listing_url(row)
    if url:
        return f"url:{url}|{when}"
    member = row.members[0]
    return f"desk:{member.via}~{member.place}~{member.title_key}~{when}"
'''
if old not in t:
    raise SystemExit("ingest_key block not found")
p.write_text(t.replace(old, new, 1))
print("ingest_key now url+when")
