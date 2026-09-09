#!/usr/bin/env python3
"""One-shot: year is not a gate in _house_when."""
from pathlib import Path

p = Path("worker/locale_pack/desk_read.py")
s = p.read_text()

old = '''def _house_when(card_text: str, page_html: str,
                as_of: Optional[_date]) -> Optional[str]:
    """The one calendar date THIS CARD printed, year completed from the page.

    Chronicle list cards print "Mon., Sept. 7" with no <time datetime>. That is
    the desk stating a night. Vague prose ("Every Sunday this fall") returns
    None. Two different dates on one card also return None — we do not pick.
    The weekday the card printed must match the completed date, or we refuse.
    `as_of` is accepted so callers can pass the walk clock; it is not a year.
    """
    del as_of
    text = (card_text or "").strip()
    if not text:
        return None
    hits = list(_HOUSE_WD_MD_RE.finditer(text))
    if len(hits) != 1:
        return None
    wd, mon, day_s = hits[0].groups()
    month = _HOUSE_MONTHS[mon.lower()]
    day = int(day_s)
    weekday = _HOUSE_WEEKDAYS[wd[:3].lower()]
    years = _years_in_date_context(text, page_html)
    if not years:
        return None
    found: List[_date] = []
    for year in years:
        try:
            candidate = _date(year, month, day)
        except ValueError:
            continue
        if candidate.weekday() != weekday:
            continue
        if candidate not in found:
            found.append(candidate)
    if len(found) == 1:
        return found[0].isoformat()
    return None
'''

new = '''def _house_when(card_text: str, page_html: str,
                as_of: Optional[_date]) -> Optional[str]:
    """Month+day the card printed. Year is not a gate.

    Printed 20xx wins. Yearless uses the walk date (as_of).
    """
    from worker.locale_pack.house_year import complete_year
    text = (card_text or "").strip()
    if not text:
        return None
    hits = list(_HOUSE_WD_MD_RE.finditer(text))
    if len(hits) != 1:
        return None
    _wd, mon, day_s = hits[0].groups()
    month = _HOUSE_MONTHS[mon.lower()]
    day = int(day_s)
    printed = _years_in_date_context(text, page_html)
    return complete_year(month, day, as_of=as_of, printed_years=printed)
'''

if old not in s:
    raise SystemExit("desk_read.py _house_when block not found as expected")
s = s.replace(old, new, 1)
p.write_text(s)
print("patched", p)
