"""Authoritative brewery / winery / distillery classification from TABC permits.

The keyword classifier in tools/gen_tasting_venues.py (derive_kind) guesses a
venue's kind from its NAME, which is fragile: a "Cafe" that is actually a
licensed winery is missed, and a co-located name is ambiguous. TABC (the Texas
Alcoholic Beverage Commission) publishes every permit holder by TYPE, which is
GROUND TRUTH — a licensed winery holds a Winery permit no matter what its name
says. So a TABC match is AUTHORITATIVE and overrides the keyword guess.

This module is the pure, deterministic core (no network): it maps TABC permit
codes to our tasting kinds, normalizes trade names for matching, builds an index
from TABC records, and classifies a venue name against it. The LIVE fetch
(tools/fetch_tabc.py) runs where egress reaches data.texas.gov and writes
sources/tabc_producers.json; this logic is fixture-tested here so it is correct
before any live data lands (the same pattern the licensed importers use).
"""
from __future__ import annotations

import re

# TABC permit/license type code -> our tasting kind. PRODUCER permits only — a
# retailer/bar/restaurant permit is not a producer and is deliberately absent,
# so a bar that merely SELLS beer is never classified a brewery. Codes per TABC's
# published permit types; this map is the single, easily-corrected source once
# the first live fetch confirms the exact codes present in the dataset.
PERMIT_KIND = {
    "BP": "brewery",      # Brewer's Permit
    "BW": "brewery",      # Brewpub License
    "B": "brewery",       # Brewer's (legacy)
    "G": "winery",        # Winery Permit
    "GII": "winery",      # Winery Permit, Class II
    "D": "distillery",    # Distiller's and Rectifier's Permit
    "DW": "distillery",   # Distiller's variant
}

_PUNCT = re.compile(r"[^\w\s]")
_WS = re.compile(r"\s+")
# Common trailing business words dropped so "Still Austin Whiskey Co." matches
# "Still Austin Whiskey". Order-independent (applied repeatedly until stable).
_SUFFIXES = ("llc", "inc", "co", "company", "ltd", "lp", "the")


def normalize_name(s: str) -> str:
    """Lowercase, strip punctuation and trailing business suffixes, collapse
    whitespace — a conservative normalizer so trade-name spelling variants match
    without collapsing genuinely different venues."""
    if not s:
        return ""
    t = _WS.sub(" ", _PUNCT.sub(" ", s.lower())).strip()
    changed = True
    while changed and t:
        changed = False
        for suf in _SUFFIXES:
            if t.endswith(" " + suf):
                t = t[: -(len(suf) + 1)].strip()
                changed = True
    return t


def normalize_county(s) -> str:
    """Lowercase, strip whitespace and a trailing ' county' word — so the TABC
    'GILLESPIE' and the catalog 'gillespie' (or a stray 'Gillespie County')
    resolve to one key. Counties are NOT run through the business-suffix stripper
    (a county is not a trade name)."""
    if not s:
        return ""
    t = _WS.sub(" ", str(s).lower()).strip()
    if t.endswith(" county"):
        t = t[: -len(" county")].strip()
    return t


def permit_kind(code) -> "str | None":
    """The tasting kind for a TABC permit code, or None if it is not a producer
    permit we surface."""
    if not code:
        return None
    return PERMIT_KIND.get(str(code).strip().upper())


# The kinds a record may already carry (fetch_tabc.py resolves permit -> kind
# and writes {"kind": ...}, so its output must be readable directly).
KINDS = frozenset(PERMIT_KIND.values())


def build_index(records) -> "dict[tuple[str, str], str]":
    """Build {(normalized_trade_name, normalized_county): kind} from TABC records,
    PRODUCER permits only. Accepts BOTH shapes so the two halves can never
    silently drift apart (adversarial-review #104): (a) fetch_tabc.py's OUTPUT,
    which already resolved the permit to a `kind` field (this is what
    sources/tabc_producers.json holds); and (b) a RAW TABC record with a
    `permit_type`/`license_type`/`type` code.

    The key is (name, COUNTY), not name alone (adversarial-review #104 r3): a
    different producer with the same or similar trade name in another county must
    NOT be able to hand its permit's authority to an unrelated catalog venue. A
    record carrying no county is DROPPED — an unqualifiable identity is never
    admitted to the authoritative index (fail-closed; the caller then falls back
    to the keyword guess, never to a wrong authoritative kind). First producer
    for a (name, county) wins (a winery+brewery estate is a winery under its own
    name — consistent with the keyword rule it replaces)."""
    idx: "dict[tuple[str, str], str]" = {}
    for r in records:
        # Prefer an already-resolved, valid kind; else map a raw permit code.
        k = r.get("kind")
        kind = k if k in KINDS else permit_kind(
            r.get("permit_type") or r.get("license_type") or r.get("type")
        )
        if not kind:
            continue
        raw = r.get("trade_name") or r.get("name") or r.get("location_name") or ""
        name = normalize_name(raw)
        county = normalize_county(r.get("county") or r.get("location_county"))
        if not name or not county:
            continue  # fail-closed: an unqualifiable identity never enters
        key = (name, county)
        if key in idx:
            continue
        idx[key] = kind
    return idx


def classify(name: str, county, index: "dict[tuple[str, str], str]") -> "str | None":
    """Authoritative tasting kind for a venue via the TABC index, matched by
    (NAME, COUNTY) so a same-name producer in another county can never supply the
    kind (adversarial-review #104 r3). Returns None when the venue holds no
    producer permit under that name AND county — the caller falls back to the
    keyword guess. A venue with no county cannot be authoritatively matched
    (fail-closed) and likewise returns None."""
    if not index:
        return None
    c = normalize_county(county)
    if not c:
        return None
    return index.get((normalize_name(name), c))
