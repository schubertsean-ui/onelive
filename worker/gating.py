"""Multi-confirm gating logic — the core trust mechanism.

Rules (FOUNDER-RULED 2026-08-05, decision record
docs/memory/decisions/2026-08-05_first-party-promotes-on-one-source.md,
verbatim "only if it's a social media site first that is not the event
itself or the artist themselves or the venue itself … Then it gets a
secondary source" + "newspapers, periodicals, radio and tv stations, etc
are all first party authoritative"):

- A FIRST-PARTY / PUBLISHED source promotes on ONE source — the venue's own
  calendar, a ticketing system, a festival feed, a city/university/library
  calendar, a claimed upload, opt-in email, and PUBLISHED MEDIA (newspapers,
  periodicals, radio, TV). These are principals publishing their own
  events, or established outlets publishing under their own masthead.
- THIRD-PARTY SOCIAL chatter — a social post that is NOT the event, artist,
  or venue speaking for themselves — needs ONE corroborating source (two in
  SXSW/chaos mode). Aggregators, link hubs, and directories sit in the same
  needs-corroboration tier: they republish other people's claims.
- Artist/venue claims always override (see promote.py / resolve_entities.py).

Every source's class is recorded per candidate either way, so the credibility
of any single source can be measured over time (founder: "We are tracking
the sources internally so we can learn which may wind up having issues").

Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/gating.py)
"""
from dataclasses import dataclass
from typing import List

# Anchors = first-party / published sources: promote on ONE.
ANCHOR_CLASSES = {
    # principals publishing their own events
    "festival_feed", "ticketing", "venue_calendar", "claimed_upload",
    "email_opt_in", "calendar_feed",
    # public institutions publishing their own calendars
    "city_calendar", "university_calendar", "library_calendar", "community",
    # published media under their own masthead (founder ruling 2026-08-05)
    "local_media",
}


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
