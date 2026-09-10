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
_TIME = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)".?", re.I)
