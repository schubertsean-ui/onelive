"""Place printed on a list card after the title and the clock.

FL-009. Universal. If the desk printed a venue line next to the title,
that is Place. We do not invent. We do not use the city in the title.
Works on line-broken cards and on flattened HTML text.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

_DATE_LINE = re.compile(
    r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*\.?,?\s+"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\w*\.?,?\s+\d{1,2}"
    r"(?:st|nd|rd|th)?",
    re.I,
)
_TIME = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)\.?\b", re.I)
_KIND = re.compile(
    r"^(music|arts|food|film|comedy|theater|theatre|family|free|"
    r"lectures?|visual arts|literary|dance|sports|nightlife)\b",
    re.I,
)
_PHONE = re.compile(r"\b\d{3}[-/]\d{3}[-/]?\d{4}\b")
_CITY_ONLY = re.compile(
    r"^(austin|tx|texas|beyond austin|greater austin|east|south|north|"
    r"downtown|midtown|old west austin|driftwood)\.?$",
    re.I,
)
# FM/Hwy (8989 FM 150) OR a house number plus the rest of that street phrase.
_STREET = re.compile(
    r"(\d{3,6}\s+(?:f\.?m\.?|hwy|highway)\.?\s+\d+[A-Za-z]?"
    r"|\d{3,6}\s+[A-Za-z0-9.#][^|,]{0,60})",
    re.I,
)


def _clean(ln: str) -> str:
    return re.sub(r"\s+", " ", (ln or "")).strip(" ·|-|.,")


def _street_of(ln: str) -> Optional[str]:
    hit = _STREET.search(ln or "")
    if not hit:
        return None
    raw = hit.group(1).split("|")[0].strip().rstrip(",")
    raw = re.split(r"\s+\|\s+", raw)[0].strip()
    raw = re.sub(
        r",\s*(Austin|Driftwood|Texas|TX|Beyond Austin|Greater Austin|"
        r"Old West Austin|East|South|North|Downtown|Midtown)\b.*$",
        "",
        raw,
        flags=re.I,
    )
    return raw.strip(" ,") or None


def place_from_card_text(card_text: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (venue name, street line) printed after the clock on this card."""
    raw = card_text or ""
    lines = [_clean(ln) for ln in raw.splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines:
        return None, None
    if len(lines) == 1:
        return _from_flat(lines[0])
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
        found = _street_of(ln)
        if found:
            street = street or found
            before = _clean(ln[: ln.find(found)]).strip(" ,|")
            if name is None and before and not _CITY_ONLY.match(before) and 2 <= len(before) <= 80:
                name = before
            continue
        if name is None and 2 <= len(ln) <= 80:
            name = ln
    return name, street


def _from_flat(blob: str) -> Tuple[Optional[str], Optional[str]]:
    text = _clean(blob)
    cut = 0
    last = None
    for m in _DATE_LINE.finditer(text):
        last = m
    if last:
        cut = last.end()
    time_m = _TIME.search(text, cut)
    if time_m:
        cut = time_m.end()
    rest = text[cut:].strip(" ,;-|.")
    rest = _PHONE.sub("", rest)
    rest = re.sub(
        r"\b(?:MUSIC|ARTS|FOOD|FILM|COMEDY|THEATER|THEATRE|FREE)\b",
        "",
        rest,
        flags=re.I,
    )
    rest = _clean(rest)
    street = _street_of(rest)
    if street:
        idx = rest.find(street)
        rest = _clean(rest[:idx] if idx >= 0 else rest)
    rest = re.sub(
        r"\|\s*(Beyond Austin|Greater Austin|Old West Austin|East|South|North|Downtown|Midtown)\b",
        "",
        rest,
        flags=re.I,
    )
    rest = _clean(rest).strip(" ,|.")
    if rest and _CITY_ONLY.match(rest):
        rest = None
    if rest and (len(rest) < 2 or len(rest) > 80):
        rest = None
    return rest, street
