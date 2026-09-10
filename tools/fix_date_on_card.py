#!/usr/bin/env python3
"""Printed date stays on the public row. No invented venue. Safe to re-run."""
from pathlib import Path

p = Path("worker/locale_pack/desk_publish.py")
t = p.read_text()
old = '''        clock_hole = (f"one desk states {len(clocks)} different times for this "
                      f"row: {', '.join(clocks)}")
        clock_disputed = True
'''
new = '''        clock_hole = (f"one desk states {len(clocks)} different times for this "
                      f"row: {', '.join(clocks)}")
        clock_disputed = True
        start_time = row.night
'''
if old in t and "start_time = row.night\n    elif len(clocks) > 1:" not in t:
    t = t.replace(old, new, 1)
    p.write_text(t)
    print("write_for keeps night when two clocks")
elif "start_time = row.night" in t.split("len(clocks) > 1 and len(clock_desks)")[1][:400]:
    print("write_for already keeps night when two clocks")
else:
    print("write_for two-clock marker missing")

p = Path("worker/promote.py")
t = p.read_text()
old = 'venue_id = resolve_venue_id(cur, venue_name or "Unknown Venue", city or "Austin")'
new = 'venue_id = resolve_venue_id(cur, venue_name, city or "Austin") if venue_name else None'
if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t)
    print("promote no longer invents Unknown Venue")
elif "if venue_name else None" in t:
    print("promote already skips Unknown Venue")
else:
    print("Unknown Venue marker missing")
