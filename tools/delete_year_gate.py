#!/usr/bin/env python3
from pathlib import Path

p = Path("worker/locale_pack/desk_read.py")
t = p.read_text()
if "    del as_of\n" not in t and "if not years:\n        return None" not in t:
    print("already deleted")
    raise SystemExit(0)
t = t.replace("    del as_of\n", "", 1)
old = "    years = _years_in_date_context(text, page_html)\n    if not years:\n        return None\n"
new = (
    "    years = _years_in_date_context(text, page_html)\n"
    "    if not years and as_of is not None:\n"
    "        years = {as_of.year}\n"
    "    if not years:\n"
    "        from datetime import date as _today\n"
    "        years = {_today.today().year}\n"
)
if old not in t:
    raise SystemExit("year block missing after del as_of strip")
t = t.replace(old, new, 1)
if "del as_of" in t:
    raise SystemExit("del as_of still present")
if "if not years:\n        return None" in t:
    raise SystemExit("return None year gate still present")
p.write_text(t)
print("deleted del as_of and year-missing return None")
