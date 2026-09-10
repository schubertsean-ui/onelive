#!/usr/bin/env python3
"""Restore desk_read.py from git history 665ce213 and wire FL-009.

Never write a stub. The 57KB reader already lives in this repo.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REAL = "665ce213c8eef4c4b3e652d5c6c2a871176d6ce7"
PATH = Path("worker/locale_pack/desk_read.py")


def main() -> None:
    blob = subprocess.check_output(
        ["git", "show", f"{REAL}:{PATH.as_posix()}"],
        text=True,
    )
    if len(blob.encode()) < 10000:
        raise SystemExit(f"{REAL} is not the real reader ({len(blob.encode())} bytes)")
    if "SEE_LOCAL" in blob or "PLACEHOLDER" in blob:
        raise SystemExit(f"{REAL} has a stub marker")
    if "def read(" not in blob or "def _house_when(" not in blob:
        raise SystemExit(f"{REAL} is not the real reader")

    text = blob
    if "from worker.locale_pack.card_place import place_from_card_text" not in text:
        needle = "from worker.locale_pack.house_dates import house_occurrences\n"
        if needle not in text:
            raise SystemExit("import site missing")
        text = text.replace(
            needle,
            needle + "from worker.locale_pack.card_place import place_from_card_text\n",
            1,
        )

    text = text.replace(
        "    if not occs_here and node.parent is not None:\n",
        "    sibling_text = \"\"\n    if node.parent is not None:\n",
        1,
    )
    text = text.replace(
        (
            "            href = \"\"\n"
            "            if getattr(child, \"tag\", None) == \"a\":\n"
            "                href = child.attrs.get(\"href\") or \"\"\n"
            "            if \"/event/\" in href:\n"
        ),
        (
            "            sib_href = \"\"\n"
            "            if getattr(child, \"tag\", None) == \"a\":\n"
            "                sib_href = child.attrs.get(\"href\") or \"\"\n"
            "            if \"/event/\" in sib_href:\n"
        ),
        1,
    )
    text = text.replace(
        (
            "        occs_here = house_occurrences(_ws(\" \".join(extra)), page_html, as_of)\n"
            "    if not when and occs_here:\n"
            "        when = occs_here[0][\"when\"]\n"
        ),
        (
            "        sibling_text = _ws(\" \".join(extra))\n"
            "        if not occs_here and sibling_text:\n"
            "            occs_here = house_occurrences(sibling_text, page_html, as_of)\n"
            "    if occs_here:\n"
            "        stated = occs_here[0][\"when\"]\n"
            "        if not when or (\"T\" in str(when) and str(when)[-1].isdigit()"
            " and \"-\" not in str(when)[10:]):\n"
            "            when = stated\n"
            "    card_blob = _ws(\" \".join(x for x in (card_text, sibling_text) if x))\n"
        ),
        1,
    )
    text = text.replace(
        '        "place_text": _ws(" ".join(place_parts)) or None,\n',
        (
            '        "place_text": _ws(" ".join(place_parts)) or '
            "place_from_card_text(card_blob or card_text)[0],\n"
        ),
        1,
    )
    if "place_from_card_text" not in text:
        raise SystemExit("wire failed")
    if "SEE_LOCAL" in text or "PLACEHOLDER" in text:
        raise SystemExit("refused to write a stub")
    if len(text.encode()) < 10000:
        raise SystemExit("refused to write a stub (too small)")
    PATH.write_text(text, encoding="utf-8")
    print("restored", PATH.stat().st_size)


if __name__ == "__main__":
    main()
