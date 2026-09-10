#!/usr/bin/env python3
"""Card text into night splitter. Safe to re-run."""
from pathlib import Path

def must(text, old, new, label):
    if old in text:
        print(label, "patched")
        return text.replace(old, new, 1)
    if "when_occs" in text and label.startswith("when"):
        print(label, "already")
        return text
    if "for night in nights" in text and label.startswith("add"):
        print(label, "already")
        return text
    if 'fields.get("card_text")' in text and label.startswith("occs"):
        print(label, "already")
        return text
    if '"card_text": card_text' in text and label.startswith("fields"):
        print(label, "already")
        return text
    raise SystemExit("missing " + label)

rd = Path("worker/locale_pack/desk_read.py")
t = rd.read_text()
t = must(
    t,
    "    when_text = _ws(\" \".join(time_text_parts)) or None\n"
    "    when = time_iso or itemprop_date\n"
    "    if not when:\n"
    "        when = _house_when(_ws(\" \".join(text_parts)), page_html, as_of)\n",
    "    when_text = _ws(\" \".join(time_text_parts)) or None\n"
    "    when = time_iso or itemprop_date\n"
    "    card_text = _ws(\" \".join(text_parts))\n"
    "    occs_here = house_occurrences(card_text, page_html, as_of)\n"
    "    if not when and len(occs_here) == 1:\n"
    "        when = occs_here[0][\"when\"]\n",
    "when-block",
)
t = must(
    t,
    "        \"when\": when,\n        \"when_text\": when_text,\n",
    "        \"when\": when,\n        \"when_text\": when_text,\n"
    "        \"card_text\": card_text,\n        \"when_occs\": occs_here,\n",
    "fields-return",
)
t = must(
    t,
    "        _add(fields[\"title\"], fields[\"when\"], fields[\"when_text\"],\n"
    "             fields[\"place_text\"], fields[\"listing_url\"],\n"
    "             labels=tuple(fields.get(\"category_labels\") or ()),\n"
    "             hrefs=tuple(fields.get(\"hrefs\") or ()))\n",
    "        occs = list(fields.get(\"when_occs\") or [])\n"
    "        if not occs:\n"
    "            occs = house_occurrences(fields.get(\"card_text\") or fields.get(\"when_text\") or \"\", html, as_of)\n"
    "        nights = [o[\"when\"] for o in occs] if occs else [fields[\"when\"]]\n"
    "        for night in nights:\n"
    "            _add(fields[\"title\"], night, fields[\"when_text\"],\n"
    "                 fields[\"place_text\"], fields[\"listing_url\"],\n"
    "                 labels=tuple(fields.get(\"category_labels\") or ()),\n"
    "                 hrefs=tuple(fields.get(\"hrefs\") or ()))\n",
    "add1-loop",
)
t = must(
    t,
    "        occs = house_occurrences(\n"
    "            fields.get(\"when_text\") or \"\", html, as_of)\n"
    "        if not occs:\n"
    "            card = \" \".join(\n"
    "                part for part in (\n"
    "                    fields.get(\"title\"), fields.get(\"when_text\"),\n"
    "                    fields.get(\"place_text\"),\n"
    "                ) if part)\n"
    "            occs = house_occurrences(card, html, as_of)\n",
    "        occs = list(fields.get(\"when_occs\") or [])\n"
    "        if not occs:\n"
    "            occs = house_occurrences(\n"
    "                fields.get(\"card_text\") or fields.get(\"when_text\") or \"\", html, as_of)\n",
    "occs-card-text",
)
t = t.replace(
    "    None. Two different dates on one card also return None \u2014 we do not pick.\n",
    "    None. Several printed nights are split by house_occurrences, not here.\n",
    1,
)
rd.write_text(t)
print("desk_read night split uses card text")
