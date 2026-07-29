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


def permit_kind(code) -> "str | None":
    """The tasting kind for a TABC permit code, or None if it is not a producer
    permit we surface."""
    if not code:
        return None
    return PERMIT_KIND.get(str(code).strip().upper())


def build_index(records) -> "dict[str, str]":
    """Build {normalized_trade_name: kind} from TABC records, PRODUCER permits
    only. Accepts a few common field spellings so the fetch tool can pass rows
    through with minimal reshaping. First producer permit for a name wins (a
    winery+brewery estate is a winery under its own name — consistent with the
    keyword rule it replaces)."""
    idx: "dict[str, str]" = {}
    for r in records:
        kind = permit_kind(
            r.get("permit_type") or r.get("license_type") or r.get("type")
        )
        if not kind:
            continue
        raw = r.get("trade_name") or r.get("name") or r.get("location_name") or ""
        name = normalize_name(raw)
        if not name or name in idx:
            continue
        idx[name] = kind
    return idx


def classify(name: str, index: "dict[str, str]") -> "str | None":
    """Authoritative tasting kind for a venue NAME via the TABC index, or None
    when the venue holds no producer permit under that name (caller falls back to
    the keyword guess)."""
    if not index:
        return None
    return index.get(normalize_name(name))
