"""Canonical 4-state confidence model for canonical events.

This is the single source of truth for confidence states in the pipeline.
Do NOT revert to a 3-state model (see CLAUDE.md / STATE.md — locked decision).

States:
- unverified : proposed/promoted with no corroboration yet.
- likely     : corroborated by multiple independent non-anchor sources.
- confirmed  : backed by an anchor source (ticketing, venue calendar, etc.)
               or an authoritative venue/artist claim.
- disputed   : contradicted by evidence or flagged by moderation. A disputed
               event is ALWAYS still shown (marked disputed) and NEVER deleted
               or silently filtered from the public API.
"""
from typing import List

from worker.gating import ANCHOR_CLASSES  # anchor evidence classes (single source)



# Canonical, ordered by ascending trust (disputed is a moderation flag, kept last).
CONFIDENCE_STATES = ("unverified", "likely", "confirmed", "disputed")

# Public-feed display priority (lower = shown first). Disputed is shown last but
# is never dropped — it is a first-class rendered state.
FEED_PRIORITY = {
    "confirmed": 1,
    "likely": 2,
    "unverified": 3,
    "disputed": 4,
}


def is_valid_confidence(state: str) -> bool:
    return state in CONFIDENCE_STATES


def renders_in_public_feed(state: str) -> bool:
    """Every valid confidence state renders publicly — including 'disputed'.

    Disputed events are shown *as disputed*, never deleted or filtered out.
    This function exists so the never-drop rule is explicit and testable.
    """
    return is_valid_confidence(state)


def derive_confidence(source_classes: List[str], sxsw_mode: bool = False) -> str:
    """Map corroborating evidence to a 4-state confidence value at promotion time.

    - >=1 anchor source            -> 'confirmed'
    - enough non-anchor corroboration (2, or 3 in sxsw_mode) -> 'likely'
    - otherwise                    -> 'unverified'

    Never returns 'disputed': disputed is a moderation decision applied
    explicitly via mark_disputed / ops action, not inferred from source counts.
    """
    unique = {c for c in source_classes if c}
    if unique.intersection(ANCHOR_CLASSES):
        return "confirmed"
    min_sources = 3 if sxsw_mode else 2
    if len(unique) >= min_sources:
        return "likely"
    return "unverified"
