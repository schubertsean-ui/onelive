#!/usr/bin/env python3
"""Keep a printed night. Fill a hole. Do not erase. Safe to re-run."""
from pathlib import Path

# 1. event_page.apply — do not null the list date
p = Path("worker/locale_pack/event_page.py")
t = p.read_text()
old = '''        elif not _same_moment(row.when, statement.when):
            visit.when_conflict = True
            visit.listed_when = row.when
            visit.page_when = statement.when
            changes["when"] = None
            changes["when_precision"] = None
            changes["when_text"] = None
'''
new = '''        elif not _same_moment(row.when, statement.when):
            visit.when_conflict = True
            visit.listed_when = row.when
            visit.page_when = statement.when
'''
if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t)
    print("event_page.apply keeps printed night")
elif "changes[\"when\"] = None" not in t.split("def apply")[1][:1200]:
    print("event_page.apply already keeps printed night")
else:
    print("event_page.apply marker missing")

# 2. two-clock hold — do not hide the row
p = Path("worker/locale_pack/desk_publish.py")
t = p.read_text()
old = '''        hold_reason = (
            f"{clock_hole} — a conflict is a disagreement BETWEEN desks, and "
            f"this is one desk disagreeing with itself (or the de-dup key "
            f"merging two showings). Held rather than published with an empty "
            f"clock the desk did not leave empty")
'''
new = '''        clock_disputed = True
'''
if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t)
    print("write_for no longer holds two clocks")
elif "Held rather than published with an empty" not in t:
    print("two-clock hold already gone")
else:
    print("two-clock hold marker missing")
