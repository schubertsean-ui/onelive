"""Existence is a door question, not a field question.

Founder 2026-09-08: a trusted desk that printed a title publishes.
Missing year, minute, or place is a hole on the card. It is not a hold.
"""
from __future__ import annotations

from typing import Optional

HOLD_NONE = None
HOLD_NO_TITLE = "no_title"
HOLD_FIXTURE = "fixture"
HOLD_CLASS_D = "class_d"
ALLOWED_HOLDS = frozenset({HOLD_NO_TITLE, HOLD_FIXTURE, HOLD_CLASS_D})


def exists(door_readable: bool, title: Optional[str], listing_url: Optional[str] = None) -> bool:
    if not door_readable:
        return False
    titled = bool((title or "").strip())
    linked = bool((listing_url or "").strip())
    return titled or linked


def hold_reason(
    *,
    door_readable: bool,
    title: Optional[str],
    listing_url: Optional[str] = None,
    is_fixture: bool = False,
    is_class_d: bool = False,
    when: Optional[str] = None,
    place: Optional[str] = None,
) -> Optional[str]:
    """Date, time, place, and year are ignored. They cannot hold."""
    del when, place
    if is_fixture:
        return HOLD_FIXTURE
    if is_class_d:
        return HOLD_CLASS_D
    if exists(door_readable, title, listing_url):
        return HOLD_NONE
    return HOLD_NO_TITLE
