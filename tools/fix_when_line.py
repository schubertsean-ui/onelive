#!/usr/bin/env python3
"""Put the printed time line into date parse. Safe to re-run."""
from pathlib import Path

p = Path("worker/locale_pack/desk_read.py")
t = p.read_text()
if "parse_blob = _ws(" in t and "node.parent is not None" in t:
    print("already fixed")
    raise SystemExit(0)

needle = "    occs_here = house_occurrences(card_text, page_html, as_of)\n"
if needle not in t:
    print("NEEDLE MISSING")
    i = t.find("house_occurrences(")
    print(repr(t[i-80:i+120]) if i >= 0 else "no house_occurrences")
    raise SystemExit(1)

insert = (
    "    parse_blob = _ws(\" \".join(x for x in (card_text, when_text) if x))\n"
    "    occs_here = house_occurrences(parse_blob or card_text, page_html, as_of)\n"
    "    if not occs_here and node.parent is not None:\n"
    "        parent_bits = []\n"
    "        def _pt(n):\n"
    "            for c in n.children:\n"
    "                if isinstance(c, str):\n"
    "                    parent_bits.append(c)\n"
    "                elif getattr(c, \"tag\", None) not in (\"script\", \"style\", None):\n"
    "                    _pt(c)\n"
    "        _pt(node.parent)\n"
    "        occs_here = house_occurrences(_ws(\" \".join(parent_bits)), page_html, as_of)\n"
)
t = t.replace(needle, insert, 1)

old_if = "    if not when and len(occs_here) == 1:\n        when = occs_here[0][\"when\"]\n"
new_if = "    if not when and occs_here:\n        when = occs_here[0][\"when\"]\n"
if old_if in t:
    t = t.replace(old_if, new_if, 1)

old_fan = (
    "            occs = house_occurrences(fields.get(\"card_text\") or "
    "fields.get(\"when_text\") or \"\", html, as_of)\n"
)
new_fan = (
    "            blob = \" \".join(x for x in (\n"
    "                fields.get(\"card_text\") or \"\",\n"
    "                fields.get(\"when_text\") or \"\",\n"
    "            ) if x)\n"
    "            occs = house_occurrences(blob, html, as_of)\n"
)
if old_fan in t:
    t = t.replace(old_fan, new_fan, 1)

p.write_text(t)
if "parse_blob = _ws(" not in p.read_text():
    print("WRITE FAILED")
    raise SystemExit(1)
print("desk_read now parses the time line")
