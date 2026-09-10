#!/usr/bin/env python3
"""Parse the printed time line. Safe to re-run."""
from pathlib import Path

p = Path("worker/locale_pack/desk_read.py")
t = p.read_text()

old = '''card_text = _ws(" ".join(text_parts))
occs_here = house_occurrences(card_text, page_html, as_of)
if not when and len(occs_here) == 1:
    when = occs_here[0]["when"]
'''
new = '''card_text = _ws(" ".join(text_parts))
parse_blob = _ws(" ".join(x for x in (card_text, when_text) if x))
occs_here = house_occurrences(parse_blob or card_text, page_html, as_of)
if not occs_here and node.parent is not None:
    parent_bits = []
    def _pt(n):
        for c in n.children:
            if isinstance(c, str):
                parent_bits.append(c)
            elif getattr(c, "tag", None) not in ("script", "style", None):
                _pt(c)
    _pt(node.parent)
    occs_here = house_occurrences(_ws(" ".join(parent_bits)), page_html, as_of)
if not when and occs_here:
    when = occs_here[0]["when"]
'''

if old in t:
    t = t.replace(old, new, 1)
    print("joined time line + parent text")
elif "parse_blob = _ws" in t:
    print("already joined")
else:
    print("marker missing")
    p.write_text(t)
    raise SystemExit(0)

old2 = '''        occs = list(fields.get("when_occs") or [])
        if not occs:
            occs = house_occurrences(fields.get("card_text") or fields.get("when_text") or "", html, as_of)
'''
new2 = '''        occs = list(fields.get("when_occs") or [])
        if not occs:
            blob = " ".join(x for x in (
                fields.get("card_text") or "",
                fields.get("when_text") or "",
            ) if x)
            occs = house_occurrences(blob, html, as_of)
'''
if old2 in t:
    t = t.replace(old2, new2, 1)
    print("fan-out uses card+when text")
elif "blob = \" \".join(x for x in" in t:
    print("fan-out already uses blob")

p.write_text(t)
print("desk_read date parse patched")
