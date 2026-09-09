"""Multi-confirm gating. Validated door publishes on ONE source.

Two sources only if the only evidence is unvalidated.
"""
import logging
from dataclasses import dataclass
import json
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

ANCHOR_CLASSES = frozenset({
    "festival_feed", "ticketing", "venue_calendar", "claimed_upload",
    "email_opt_in", "calendar_feed",
    "city_calendar", "university_calendar", "university", "library_calendar",
    "theater_arts", "gallery_museum", "food_culinary",
    "local_media",
    "community",
})

THIRD_PARTY_CLASSES = frozenset({
    "social", "blog", "artist_aggregator", "artist_directory",
    "music_platform", "directory", "link_hub", "search_benchmark",
})

_VALID_PATH = Path(__file__).resolve().parents[1] / "sources" / "valid_sources.json"


def validated_classes() -> frozenset:
    extra = set(ANCHOR_CLASSES)
    try:
        data = json.loads(_VALID_PATH.read_text())
        extra.update(data.get("validated_classes") or [])
    except OSError:
        pass
    return frozenset(extra)


_WARNED_UNCLASSIFIED: set = set()


def is_first_party(source_class: str) -> bool:
    if not source_class:
        return False
    if source_class in validated_classes():
        return True
    if source_class not in THIRD_PARTY_CLASSES:
        if source_class not in _WARNED_UNCLASSIFIED:
            _WARNED_UNCLASSIFIED.add(source_class)
            logger.warning(
                "UNCLASSIFIED SOURCE CLASS %r — list it in sources/valid_sources.json",
                source_class,
            )
    return False


@dataclass
class GateResult:
    ok_to_promote: bool
    status: str
    reason: str
    required_next: str


def multi_confirm_gate(source_classes: List[str], sxsw_mode: bool = False) -> GateResult:
    classes = [c for c in source_classes if c]
    unique = set(classes)
    anchors = sorted(c for c in unique if is_first_party(c))
    if anchors:
        return GateResult(
            ok_to_promote=True,
            status="ready_to_promote",
            reason=f"Validated source: {anchors[0]}",
            required_next="",
        )
    min_sources = 3 if sxsw_mode else 2
    if len(unique) >= min_sources:
        return GateResult(
            ok_to_promote=True,
            status="ready_to_promote",
            reason=f"Unvalidated corroborated by {len(unique)} sources",
            required_next="",
        )
    needed = min_sources - len(unique)
    return GateResult(
        ok_to_promote=False,
        status="needs_more_confirmation",
        reason=f"Unvalidated only (have {len(unique)}; need {min_sources})",
        required_next=f"Add a validated door or {needed} more independent source(s)",
    )
