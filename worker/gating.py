"""Multi-confirm gating logic — the core trust mechanism.

Strict rules:
- If we have an anchor (ticketing, venue calendar, festival feed, claimed upload,
  opt-in email), allow promotion with >=1 anchor.
- Otherwise require multi-source corroboration (2 sources, or 3 in SXSW/chaos mode).
- Artist/venue claims always override (see promote.py / resolve_entities.py callers).

Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/gating.py)
"""
from dataclasses import dataclass
from typing import List

ANCHOR_CLASSES = {"festival_feed", "ticketing", "venue_calendar", "claimed_upload", "email_opt_in"}


@dataclass
class GateResult:
    ok_to_promote: bool
    status: str
    reason: str
    required_next: str


def multi_confirm_gate(source_classes: List[str], sxsw_mode: bool = False) -> GateResult:
    classes = [c for c in source_classes if c]
    unique = set(classes)
    anchors = sorted(list(unique.intersection(ANCHOR_CLASSES)))
    if anchors:
        return GateResult(
            ok_to_promote=True,
            status="ready_to_promote",
            reason=f"Anchor evidence present: {anchors[0]}",
            required_next=""
        )
    # no anchors: require corroboration
    min_sources = 3 if sxsw_mode else 2
    if len(unique) >= min_sources:
        return GateResult(
            ok_to_promote=True,
            status="ready_to_promote",
            reason=f"Corroborated by {len(unique)} non-anchor sources",
            required_next=""
        )
    needed = min_sources - len(unique)
    return GateResult(
        ok_to_promote=False,
        status="needs_more_confirmation",
        reason=f"Insufficient corroboration (have {len(unique)}; need {min_sources})",
        required_next=f"Add {needed} more independent source(s) or obtain an anchor"
    )
