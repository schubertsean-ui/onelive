"""Ticket A glue. Does not replace desk_read.py or desk_publish.py.

After plan(): date/place holds become holes. Yearless printed dates get a year.
Start is enough. End is optional. Never invent 17:00.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional, Sequence

from worker.locale_pack.existence import hold_reason as existence_hold
from worker.locale_pack.house_year import complete_year

_MD_RE = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\.?\s+(\d{1,2})\b",
    re.I,
)
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_DATE_HOLD = ("date", "place", "unplaced", "night and no time", "no desk stated")


def fill_printed_date(when_text: Optional[str], as_of: Optional[date] = None) -> Optional[str]:
    text = (when_text or "").strip()
    if not text:
        return None
    hit = _MD_RE.search(text)
    if not hit:
        return None
    mon, day_s = hit.groups()
    return complete_year(_MONTHS[mon.lower()], int(day_s), as_of=as_of)


def apply_to_write(write: Any) -> Any:
    """Keep titled rows. Date and place cannot hold. Fill printed start date."""
    extracted = dict(getattr(write, "extracted", None) or {})
    title = getattr(write, "title", None) or extracted.get("title")
    listing_url = extracted.get("listing_url")
    old = getattr(write, "hold_reason", None) or ""
    if old and not any(tok in str(old).lower() for tok in _DATE_HOLD):
        if old in {"no_title", "fixture", "class_d"}:
            return write
    write.hold_reason = existence_hold(
        door_readable=True,
        title=title,
        listing_url=listing_url,
    )
    when = extracted.get("when") or getattr(write, "when", None)
    when_text = (
        extracted.get("when_text")
        or getattr(write, "when_text", None)
        or extracted.get("when")
        or ""
    )
    if not when:
        filled = fill_printed_date(str(when_text) if when_text else None)
        if filled:
            extracted["when"] = filled
            extracted["when_precision"] = "date"
            desk = dict(extracted.get("_desk") or {})
            stmt = dict(desk.get("statement") or {})
            if stmt:
                stmt["when"] = filled
                desk["statement"] = stmt
                extracted["_desk"] = desk
            write.extracted = extracted
            if hasattr(write, "when"):
                write.when = filled
    return write


fill_house_date = fill_printed_date


def apply_to_writes(writes: Sequence[Any]) -> list:
    return [apply_to_write(w) for w in writes]
