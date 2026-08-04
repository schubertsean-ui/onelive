"""Canonical 4-state confidence model for canonical events.

This is the single source of truth for confidence states in the pipeline.
Do NOT revert to a 3-state model (see CLAUDE.md / STATE.md — locked decision).

States:
- unverified : proposed/promoted with no corroboration yet.
- likely     : one CREDIBLE source, not yet corroborated (assigned by the
               publish policy's single-trusted-source path — founder rulings
               2026-08-04: "Trustworthy is trustworthy" + "Just 'confirmed' -
               remove 'likely'" for the corroborated tier; derive_confidence
               no longer returns it).
- confirmed  : backed by an anchor source (ticketing, venue calendar, etc.),
               an authoritative venue/artist claim, OR corroborated by 2+
               independent sources (3 in sxsw_mode).
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
    - enough non-anchor corroboration (2, or 3 in sxsw_mode) -> 'confirmed'
      (founder ruling 2026-08-04, verbatim: "Just 'confirmed' - remove 'likely'"
      on the corroborated tier — 2+ independent sources earn the same label an
      anchor does; decision record
      2026-08-04_corroborated-tier-publishes-confirmed.md)
    - otherwise                    -> 'unverified'

    Never returns 'likely': that state is reserved for the publish policy's
    single-trusted-source path (one credible source, not yet corroborated).
    Never returns 'disputed': disputed is a moderation decision applied
    explicitly via mark_disputed / ops action, not inferred from source counts.
    """
    unique = {c for c in source_classes if c}
    if unique.intersection(ANCHOR_CLASSES):
        return "confirmed"
    min_sources = 3 if sxsw_mode else 2
    if len(unique) >= min_sources:
        return "confirmed"
    return "unverified"
