"""Place printed on a list card after the title and the clock.

FL-009. Universal. If the desk printed a venue line next to the title,
that is Place. We do not invent. We do not use the city in the title.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

_DATE_LINE = re.compile(
    r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*\.?,?\s+"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\w*\.?,?\s+\d{1,2}\b",
    re.I,
)
_TIME = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)\b", re.I)
_KIND = re.compile(
    r"^(music|arts|food|film|comedy|theater|theatre|family|free|"
    r"lectures?|visual arts|literary|dance|sports|nightlife)\b",
    re.I,
)
_PHONE = re.compile(r"^\d{3}[-/]\d{3}[-/]?\d{4}$")
_CITY_ONLY = re.compile(
    r"^(austin|tx|texas|beyond austin|greater austin|east|south|north|"
    r"downtown|midtown|old west austin)\.?$",
    re.I,
)
_STREET = re.compile(
    r"\d+\s+\S+.*(st|street|rd|road|ave|avenue|blvd|ln|lane|dr|drive|fm|hwy)\b",
    re.I,
)


def place_from_card_text(card_text: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (venue name, street line) printed after the clock on this card."""
    lines = [re.sub(r"\s+", " ", ln).strip(" ·|-|") for ln in (card_text or "").splitlines()]
    lines = [ln for ln in lines if ln]
    start = 0
    for i, ln in enumerate(lines):
        if _DATE_LINE.search(ln) or _TIME.search(ln):
            start = i + 1
    name = None
    street = None
    for ln in lines[start:]:
        low = ln.lower()
        if _KIND.match(ln) or _PHONE.match(ln.replace(" ", "")):
            continue
        if _CITY_ONLY.match(ln):
            continue
        if "looking for" in low or ln.startswith("via "):
            continue
        if _STREET.search(ln):
            street = ln.split("|")[0].strip()
            continue
        if name is None and 2 <= len(ln) <= 80:
            name = ln
    return name, street
