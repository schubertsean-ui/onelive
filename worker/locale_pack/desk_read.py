"""Read a public desk page into Happening rows. Holes stay None. No invented dates."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, replace
from html.parser import HTMLParser
from datetime import date as _date
from typing import Dict, List, Optional, Sequence, Tuple

from worker.importers.structured_feed import parse_jsonld
from worker.locale_pack.identity_patterns import (
    IdentityPattern,
    load_patterns,
    match as match_identity,
    patterns_for_url,
)
from worker.locale_pack.house_year import complete_house_year
from worker.locale_pack.kind_map import KindMap
from worker.locale_pack.pack import KIND_OTHER, Door, ListingSelector

log = logging.getLogger(__name__)
READABLE_INTAKES = frozenset({"html", "json_ld"})
MAX_ROWS = 500
_WS_RE = re.compile(r"\s+")
_EVENT_ITEMTYPE_RE = re.compile(r"schema\.org/[A-Za-z]*Event\b", re.I)
_PLACEISH_RE = re.compile(r"venue|location|place|where", re.I)
_LOCATION_HREF_RE = re.compile(r"(?:^|/)location(?:/|$)", re.I)
_PAGE_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_CATEGORYISH_CLASS_RE = re.compile(r"categor|section|genre|event-?type|tag\b", re.I)
_CATEGORY_ITEMPROPS = frozenset({"genre", "eventtype", "keywords"})
_ISO_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?$"
)
_HOUSE_WD_MD_RE = re.compile(
    r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.?,?\s+"
    r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\.?\s+(\d{1,2})\b",
    re.I,
)
_HOUSE_MD_RE = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\.?\s+(\d{1,2})\b",
    re.I,
)
_HAPPENING_HREF_RE = re.compile(r"(?:^|/)(?:event|events|e)/", re.I)
_HOUSE_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_HOUSE_WEEKDAYS = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
}
