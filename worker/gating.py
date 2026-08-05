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
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

# Anchors = first-party / published sources: promote on ONE.
#
# The institutional classes below (theater_arts, gallery_museum, food_culinary,
# university) were found by PR #191 in the LIVE database, seeded outside this
# repo: the committed catalog holds 180 sources while the ingest run reports
# 266 enabled, so classes this gate had never heard of were reaching it. Under
# the pre-ruling code every one of them fell through to the corroboration
# branch and waited forever — a museum's own calendar is never going to be
# corroborated by a second museum. That is the founder's "strangling my display
# of valid events" in its purest form, so they are named here explicitly.
ANCHOR_CLASSES = frozenset({
    # principals publishing their own events
    "festival_feed", "ticketing", "venue_calendar", "claimed_upload",
    "email_opt_in", "calendar_feed",
    # public institutions publishing their own calendars
    "city_calendar", "university_calendar", "university", "library_calendar",
    # venue-type institutions publishing their own programs (live-DB classes)
    "theater_arts", "gallery_museum", "food_culinary",
    # NOTE: local_media is deliberately NOT here — see THIRD_PARTY_CLASSES.
    # The founder's ruling covers mastheads; the CLASS as constituted does not.
})

# Explicitly THIRD-PARTY: they report on, index, or host OTHER people's events,
# so one of them alone is hearsay. Named so each exclusion is a decision on the
# record rather than an oversight.
#
# "community" sits here rather than in the anchor tier — a reversal of this
# branch's first pass, adopted from PR #191's better reading. A community
# PLATFORM (Meetup-style) is not the host of what it lists, so it is not the
# horse's mouth under the founder's own "comes from the source site" test. The
# live rows are also unaudited. Being wrong in this direction costs one
# corroborating source; being wrong the other way asserts an authority we
# cannot back.
THIRD_PARTY_CLASSES = frozenset({
    "social", "blog", "artist_aggregator", "artist_directory",
    "music_platform", "directory", "link_hub", "search_benchmark",
    "community",
    # local_media HELD here pending a class SPLIT (R-089), not in
    # disagreement with the founder's ruling but in faithful service of it.
    # The ruling names "newspapers, periodicals, radio and tv stations" —
    # publishers speaking under their own masthead. This CLASS is not that
    # set. Read from our OWN committed catalog
    # (sources/master_sources_catalog_120.json), four of its members are
    # submit-your-event widgets whose notes say so verbatim:
    #   kvue_community_calendar  "Community calendar is USER-SUBMITTED
    #                             (Trumba) -> low verification anchor;
    #                             content is third-party submissions,
    #                             treat unverified"
    #   kxan_calendar            "User-submitted community calendar ->
    #                             treat unverified"
    #   cbs_austin_community_calendar / fox7_community_calendar — same note
    # plus culturemap_austin_events ("listings partly user-submitted") and
    # kut_events ("KUT-hosted events + user-submitted community calendar").
    # Anchoring the class would let anyone who fills in a station's Trumba
    # form publish to the live site ALONE and render as `confirmed` — the
    # exact opposite of "it came from the source site". A submission widget
    # is the purest case of NOT the venue, artist, or event itself.
    # RESOLUTION: split local_media (masthead) from media_community_calendar
    # (UGC) and anchor only the former. Until that split exists the class
    # waits for corroboration; being wrong this way costs a second source,
    # never a false authority claim.
    "local_media",
})


# Unknown classes already warned about. The warning must reach an operator
# ONCE per class per process, not once per call: this predicate sits in the
# gate's hot path, and logging it on every call both floods the log (the
# name is the whole signal — the ten-thousandth copy adds nothing) and
# costs real time. The perf gate caught exactly that: emitting the warning
# per call blew multi_confirm_gate's 50us budget over 5,000 reps.
_WARNED_UNCLASSIFIED: set = set()


def is_first_party(source_class: str) -> bool:
    """True when the class is the horse's mouth.

    An UNKNOWN class is not assumed either way: it returns False (needs
    corroboration — the safe direction) and is LOGGED LOUDLY, once per class.
    The silent forever-hold is what stranded the DB-seeded institutional
    classes; an unclassified source is a config defect to fix in days, not a
    mystery to discover later from missing listings.
    """
    if not source_class:
        return False
    if source_class in ANCHOR_CLASSES:
        return True
    if source_class not in THIRD_PARTY_CLASSES:
        if source_class not in _WARNED_UNCLASSIFIED:
            _WARNED_UNCLASSIFIED.add(source_class)
            logger.warning(
                "UNCLASSIFIED SOURCE CLASS %r — treated as third-party (needs "
                "corroboration) because authority was never decided for it. Its "
                "events will HOLD until it is added to ANCHOR_CLASSES (if the "
                "source hosts or publishes its own events) or "
                "THIRD_PARTY_CLASSES (if it reports on others) in "
                "worker/gating.py.", source_class)
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
