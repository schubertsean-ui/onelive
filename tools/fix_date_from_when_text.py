#!/usr/bin/env python3
from pathlib import Path

READ = Path("worker/locale_pack/desk_read.py")

REPLACES = [
    (
        "    occs_here = house_occurrences(card_text, page_html, as_of)\n",
        "    blob = \" \".join(p for p in (card_text, when_text) if p)\n"
        "    occs_here = house_occurrences(blob, page_html, as_of)\n",
        "row-fields",
    ),
    (
        '        occs = house_occurrences(fields.get("card_text") or fields.get("when_text") or "", html, as_of)\n',
        '        blob = " ".join(p for p in (fields.get("card_text"), fields.get("when_text"), fields.get("title")) if p)\n'
        '        occs = house_occurrences(blob, html, as_of)\n',
        "jsonld",
    ),
    (
        '            occs = house_occurrences(\n                fields.get("card_text") or fields.get("when_text") or "", html, as_of)\n',
        '            blob = " ".join(p for p in (fields.get("card_text"), fields.get("when_text"), fields.get("title")) if p)\n'
        '            occs = house_occurrences(blob, html, as_of)\n',
        "html",
    ),
]


def main() -> int:
    t = READ.read_text()
    for old, new, label in REPLACES:
        if old not in t:
            print(label, "already or missing")
            continue
        t = t.replace(old, new, 1)
        print(label, "patched")
    READ.write_text(t)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
