"""Multi-confirm gating logic — the core trust mechanism.

Strict rules:
- If we have an anchor (a FIRST-PARTY source — see ANCHOR_CLASSES), allow
  promotion with >=1 anchor.
- Otherwise require multi-source corroboration (2 sources, or 3 in SXSW/chaos mode).
- Artist/venue claims always override (see promote.py / resolve_entities.py callers).

Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/gating.py)
"""
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

# FIRST-PARTY = AUTHORITATIVE (founder-ratified 2026-08-05, verbatim: "if
# something comes from the source site it's authoritative - no additional
# gating or checking needed. You have overengineered this and are strangling
# my display of valid events." — decision record
# docs/memory/decisions/2026-08-05_first-party-is-authoritative.md).
#
# The line this set draws, stated so it applies to any future class: an
# anchor is a source publishing an event IT ITSELF puts on or hosts — the
# venue's own calendar, the theater's/museum's/university's own site, the
# festival's own feed, the organizer's own claimed feed. A source REPORTING
# on someone else's event (a newspaper, a social post, an aggregator, a
# directory) is third-party and still needs corroboration: that is not
# "extra gating" on the source site, it is the difference between the horse's
# mouth and hearsay.
#
# WHY THIS SET GREW (2026-08-05): it held only the first five, while the LIVE
# catalog carries theater_arts (24 sources), gallery_museum (20),
# food_culinary (5), university (9), city_calendar (40) — classes no code in
# this repo even defines, seeded straight into the database. Result: 195 of
# 268 sources could never publish a single event alone, waiting forever on
# corroboration a venue's own site will never receive. Every one of those is
# a first-party site; holding them was the strangling the founder named.
ANCHOR_CLASSES = frozenset({
    # the original five
    "festival_feed", "ticketing", "venue_calendar", "claimed_upload",
    "email_opt_in",
    # institutional + venue-type calendars: the entity that runs the event
    # publishes it on its own surface
    "city_calendar", "university_calendar", "university", "library_calendar",
    "calendar_feed", "theater_arts", "gallery_museum", "food_culinary",
})

# Explicitly THIRD-PARTY: they report on or index OTHER people's events, so a
# single one of them is hearsay and still needs corroboration. Named here so
# each exclusion is a decision on the record, not an oversight.
THIRD_PARTY_CLASSES = frozenset({
    "local_media", "social", "blog",
    "artist_aggregator", "artist_directory", "music_platform", "directory",
    "link_hub", "search_benchmark",
    # community PLATFORMS (Meetup-style): the platform is not the host. The
    # live DB's 55 "community" rows were seeded outside this repo and their
    # real identity is unaudited; classified conservatively until it is
    # (R-081, objective trigger). Being wrong this way costs corroboration,
    # never a false authority claim.
    "community",
})


def is_first_party(source_class: str) -> bool:
    """True when the class is the horse's mouth. An UNKNOWN class is not
    assumed either way: it returns False (needs corroboration, the safe
    direction) and is LOGGED LOUDLY — the silent forever-hold that stranded
    195 sources is exactly what this warning exists to make impossible. An
    unclassified source is a config defect to fix in days, not a mystery."""
    if not source_class:
        return False
    if source_class in ANCHOR_CLASSES:
        return True
    if source_class not in THIRD_PARTY_CLASSES:
        logger.warning(
            "UNCLASSIFIED SOURCE CLASS %r — treated as third-party (needs "
            "corroboration) because authority was never decided for it. Its "
            "events will HOLD until it is added to ANCHOR_CLASSES (if the "
            "source hosts its own events) or THIRD_PARTY_CLASSES (if it "
            "reports on others) in worker/gating.py.", source_class)
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
            reason=f"First-party source: {anchors[0]}",
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
