#!/usr/bin/env python3
"""One-shot: wire house_occurrences into desk_read.py. Safe to re-run."""
from pathlib import Path

p = Path("worker/locale_pack/desk_read.py")
t = p.read_text()
changed = False

old_imp = "from worker.locale_pack.kind_map import KindMap\n"
new_imp = old_imp + "from worker.locale_pack.house_dates import house_occurrences\n"
if "from worker.locale_pack.house_dates import house_occurrences" not in t:
    if old_imp not in t:
        raise SystemExit("import marker missing")
    t = t.replace(old_imp, new_imp, 1)
    changed = True

old_key = '        return ("url", listing_url.strip(), "")\n'
new_key = '        return ("url", listing_url.strip(), (when or "").strip())\n'
if old_key in t:
    t = t.replace(old_key, new_key, 1)
    changed = True

old_when = """    when_text = _ws(" ".join(time_text_parts)) or None
    when = time_iso or itemprop_date
    if not when:
        when = _house_when(_ws(" ".join(text_parts)), page_html, as_of)
"""
new_when = """    when_text = _ws(" ".join(time_text_parts)) or None
    when = time_iso or itemprop_date
    card_text = _ws(" ".join(text_parts))
    occs = house_occurrences(card_text, page_html, as_of)
    if not when and len(occs) == 1:
        when = occs[0]["when"]
        if not when_text:
            when_text = card_text or None
"""
if old_when in t:
    t = t.replace(old_when, new_when, 1)
    changed = True

old_ret = """        \"when\": when,
        \"when_text\": when_text,
"""
# fix - use real quotes in file
old_ret = '        "when": when,\n        "when_text": when_text,\n'
print('placeholder')
