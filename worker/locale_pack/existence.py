"""Existence is a door question, not a field question.

A trusted readable door that printed a title (or listing URL) exists.
Missing year, minute, or place is a hole. It is not a hold.
"""
from __future__ import annotations

from typing import Optional

HOLD_NO_TITLE = "no_title"
HOLD_FIXTURE = "fixture"
HOLD_CLASS_D = "class_d"


def exists(door_readable: bool, title: Optional[str], listing_url: Optional[str] = None) -> bool:
    if not door_readable:
        return False
    return bool((title or "").strip()) or bool((listing_url or "").strip())


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
    del when, place
    if is_fixture:
        return HOLD_FIXTURE
    if is_class_d:
        return HOLD_CLASS_D
    if exists(door_readable, title, listing_url):
        return None
    return HOLD_NO_TITLE
