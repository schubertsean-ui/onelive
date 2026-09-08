#!/usr/bin/env python3
"""Wire master desk_read.py: current-year house dates + sibling absorb."""
from pathlib import Path

P = Path("worker/locale_pack/desk_read.py")

NEW_FN = '''def _house_when(card_text: str, page_html: str,
                as_of: Optional[_date]) -> Optional[str]:
    """Yearless house date uses current year. Year never blocks."""
    text = (card_text or "").strip()
    if not text:
        return None
    wd_hits = list(_HOUSE_WD_MD_RE.finditer(text))
    weekday = None
    if wd_hits:
        wd, mon, day_s = wd_hits[0].groups()
        month = _HOUSE_MONTHS[mon.lower()]
        day = int(day_s)
        weekday = _HOUSE_WEEKDAYS.get(wd[:3].lower())
    else:
        md_hits = list(_HOUSE_MD_RE.finditer(text))
        if not md_hits:
            return None
        mon, day_s = md_hits[0].groups()
        month = _HOUSE_MONTHS[mon.lower()]
        day = int(day_s)
    years = _years_in_date_context(text, page_html)
    return complete_house_year(
        month, day, as_of=as_of, printed_years=years, weekday=weekday,
    )

'''

SIBLING = '''
def _is_happening_href(href: str) -> bool:
    if not href or _is_location_href(href):
        return False
    from urllib.parse import urlsplit
    return bool(re.search(r"(?:^|/)(?:event|events|e)/", urlsplit(href).path or href, re.I))


def _following_sibling_fields(node: "_Node"):
    parent = node.parent
    if parent is None:
        return "", None
    start = node
    while start.parent is not None and start.parent is not parent:
        start = start.parent
    started = False
    texts = []
    place = None
    for child in parent.children:
        if child is start:
            started = True
            continue
        if not started:
            continue
        if isinstance(child, str):
            texts.append(child)
            continue
        if not isinstance(child, _Node):
            continue
        hrefs = []
        if child.tag == "a":
            hrefs.append(_ws(child.attrs.get("href") or ""))
        for desc in child.descendants():
            if desc.tag == "a":
                hrefs.append(_ws(desc.attrs.get("href") or ""))
        if any(_is_happening_href(h) for h in hrefs):
            break
        texts.append(_node_plain_text(child))
        if place is None:
            place = _location_anchor_text(child)
    return _ws(" ".join(texts)), place

'''


def main() -> None:
    t = P.read_text()
    if "from worker.locale_pack._desk_read" in t:
        raise SystemExit("loader still present; copy master first")
    if "from worker.locale_pack.house_year import complete_house_year" not in t:
        t = t.replace(
            "from worker.locale_pack.kind_map import KindMap",
            "from worker.locale_pack.house_year import complete_house_year\n"
            "from worker.locale_pack.kind_map import KindMap",
        )
    if "_HOUSE_MD_RE" not in t:
        t = t.replace(
            "_HOUSE_MONTHS = {",
            "_HOUSE_MD_RE = re.compile(\n"
            "    r\"\\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|\"\n"
            "    r\"Jul(?:y)?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|\"\n"
            "    r\"Dec(?:ember)?)\\.?\\s+(\\d{1,2})\\b\",\n"
            "    re.I,\n)\n_HOUSE_MONTHS = {",
            1,
        )
    start = t.find("def _house_when")
    end = t.find("_VOID_TAGS")
    if start < 0 or end < 0:
        raise SystemExit("cannot find _house_when")
    t = t[:start] + NEW_FN + SIBLING + t[end:]
    old = '_house_when(_ws(" ".join(text_parts)), page_html, as_of)'
    new = (
        "_house_when(_ws(' '.join(text_parts) + ' ' + (_following_sibling_fields(node)[0] if node.tag == 'a' else '')), page_html, as_of)"
    )
    t = t.replace(old, new, 1)
    P.write_text(t)
    print("wired", P.stat().st_size)


if __name__ == "__main__":
    main()
