#!/usr/bin/env python3
"""Wire one printed night to one row. Safe to re-run."""
from pathlib import Path


def must_replace(text: str, old: str, new: str, label: str) -> str:
    if new.strip() and new in text and old not in text:
        print(label, "already applied")
        return text
    if old not in text:
        raise SystemExit(f"missing: {label}")
    print(label, "patched")
    return text.replace(old, new, 1)


def wire_desk_read() -> None:
    path = Path("worker/locale_pack/desk_read.py")
    text = path.read_text()
    text = must_replace(
        text,
        "from worker.locale_pack.kind_map import KindMap\n",
        "from worker.locale_pack.kind_map import KindMap\n"
        "from worker.locale_pack.house_dates import house_occurrences\n",
        "import",
    )
    text = must_replace(
        text,
        '        return ("url", listing_url.strip(), "")\n',
        '        return ("url", listing_url.strip(), (when or "").strip())\n',
        "row_key",
    )
    text = must_replace(
        text,
        "        _add(fields[\"title\"], fields[\"when\"], fields[\"when_text\"],\n"
        "             fields[\"place_text\"], identity or fields[\"listing_url\"],\n"
        "             labels=tuple(fields.get(\"category_labels\") or ()),\n"
        "             hrefs=tuple(fields.get(\"hrefs\") or ()))\n",
        "        listing = identity or fields[\"listing_url\"]\n"
        "        occs = house_occurrences(\n"
        "            fields.get(\"when_text\") or \"\", html, as_of)\n"
        "        if not occs:\n"
        "            card = \" \".join(\n"
        "                part for part in (\n"
        "                    fields.get(\"title\"), fields.get(\"when_text\"),\n"
        "                    fields.get(\"place_text\"),\n"
        "                ) if part)\n"
        "            occs = house_occurrences(card, html, as_of)\n"
        "        if occs:\n"
        "            for night in occs:\n"
        "                _add(fields[\"title\"], night[\"when\"],\n"
        "                     fields[\"when_text\"], fields[\"place_text\"],\n"
        "                     listing,\n"
        "                     labels=tuple(fields.get(\"category_labels\") or ()),\n"
        "                     hrefs=tuple(fields.get(\"hrefs\") or ()))\n"
        "        else:\n"
        "            _add(fields[\"title\"], fields[\"when\"], fields[\"when_text\"],\n"
        "                 fields[\"place_text\"], listing,\n"
        "                 labels=tuple(fields.get(\"category_labels\") or ()),\n"
        "                 hrefs=tuple(fields.get(\"hrefs\") or ()))\n",
        "_add-loop",
    )
    path.write_text(text)


def wire_publish() -> None:
    path = Path("worker/locale_pack/desk_publish.py")
    text = path.read_text()
    text = must_replace(
        text,
        '    "ticket_link": None,\n',
        '    "ticket_link": getattr(row, "ticket_link", None),\n',
        "ticket_link",
    )
    old = "    return [f for f in drift(stored, fresh) if f in CONTRADICTING]\n"
    new = (
        "    out = []\n"
        "    for f in drift(stored, fresh):\n"
        "        if f not in CONTRADICTING:\n"
        "            continue\n"
        "        if not stored.get(f) and fresh.get(f):\n"
        "            continue\n"
        "        out.append(f)\n"
        "    return out\n"
    )
    if old in text:
        text = must_replace(text, old, new, "contradicts-fill")
    else:
        print("contradicts-fill marker missing; leave for ingest apply")
    path.write_text(text)


def main() -> int:
    wire_desk_read()
    wire_publish()
    print("wired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
