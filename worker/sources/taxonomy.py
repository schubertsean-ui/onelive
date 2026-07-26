"""Every CLASS of event/venue data source, independent of any one metro.

Founder directive, 2026-07-26: "a list of every potential data source for
ingestion that has been identified throughout the entire build process... It
should be a consistent source for any locale."

The two halves of that ask are different things, and conflating them is what
makes source lists rot:

  * a source CLASS is portable — "the city's official civic calendar" exists in
    Austin, Nashville and Cleveland alike, with the same access pattern, the
    same trust weight and the same failure modes;
  * a source INSTANCE is local — `austintexas.gov/events` is Austin's answer to
    that class.

This module is the CLASSES. `tools/build_source_registry.py` binds instances to
them. Launching a new metro therefore means walking this list and answering
"what is this city's X?" — not inventing a source list from scratch, and not
copying Austin's URLs and hoping.

Each class declares what it actually PROVIDES, because they are not
interchangeable and treating them as one list is how a venue-enumeration source
gets mistaken for an event feed:

  EVENTS    listings with a date — the product's payload
  VENUES    an enumeration of places — the DENOMINATOR (how much market exists)
  IDENTITY  artist/entity resolution — the spine that links listings together
  SIGNAL    demand/interest, never a listing

TRUST_WEIGHT is the class's default position in the confidence model: FIRST_PARTY
(the venue/institution stating its own schedule — 'confirmed' by construction),
LICENSED (a commercial feed under terms), AGGREGATE (someone else's collection —
corroboration, never an anchor), USER (submitted; needs verification).
"""
from __future__ import annotations

# provides · trust · typical access · what it costs · why it can fail
SOURCE_CLASSES: dict = {
    # ---- EVENT sources: the product's payload ------------------------------
    "ticketing_api": {
        "provides": "EVENTS", "trust": "LICENSED",
        "access": "API key",
        "portable_prompt": "Which national ticketing platforms sell in this metro?",
        "examples": "Ticketmaster/Discovery, SeatGeek, Eventbrite, AXS, DICE, Bandsintown",
        "typical_yield": "high volume, big rooms; misses the long tail entirely",
        "known_failure_modes": ["credential missing", "geo scoping too coarse",
                                "rate limit", "payload shape drift"],
        "cost": "free tier to paid",
    },
    "venue_calendar": {
        "provides": "EVENTS", "trust": "FIRST_PARTY",
        "access": "public web / ICS / JSON-LD",
        "portable_prompt": "List every room that books live events, then find each one's own calendar.",
        "examples": "a club, theatre, brewery or listening room's own events page",
        "typical_yield": "the moat — the long tail nobody else has",
        "known_failure_modes": ["no machine-readable feed (newsletter only)",
                                "JS-rendered calendar", "bot protection / 403",
                                "TLS chain broken", "feed at an unguessed path"],
        "cost": "free",
    },
    "university_calendar": {
        "provides": "EVENTS", "trust": "FIRST_PARTY",
        "access": "Localist / ICS / JSON-LD",
        "portable_prompt": "Which universities and colleges are in the service area?",
        "examples": "a university's performing-arts series and master calendar",
        "typical_yield": "steady, well-structured, non-music culture",
        "known_failure_modes": ["Localist API path differs", "term-time gaps"],
        "cost": "free",
    },
    "library_calendar": {
        "provides": "EVENTS", "trust": "FIRST_PARTY",
        "access": "ICS / LibCal / civic CMS",
        "portable_prompt": "What is the public library system, and does it publish a feed?",
        "examples": "a city library system's programs calendar",
        "typical_yield": "family/all-ages and literary — categories ticketing never sees",
        "known_failure_modes": ["LibCal requires a key", "per-branch fragmentation"],
        "cost": "free",
    },
    "city_civic_calendar": {
        "provides": "EVENTS", "trust": "FIRST_PARTY",
        "access": "civic CMS / open-data portal",
        "portable_prompt": "What is the city's official events calendar and open-data portal?",
        "examples": "parks events, city-sponsored festivals, public meetings",
        "typical_yield": "civic and free/outdoor events",
        "known_failure_modes": ["CMS change", "no feed, HTML only"],
        "cost": "free",
    },
    "museum_gallery": {
        "provides": "EVENTS", "trust": "FIRST_PARTY",
        "access": "public web / JSON-LD",
        "portable_prompt": "Which museums and galleries program public events?",
        "examples": "museum late-nights, exhibition openings, talks",
        "typical_yield": "visual-arts and ideas categories",
        "known_failure_modes": ["exhibition dates modelled as ranges, not events"],
        "cost": "free",
    },
    "performing_arts": {
        "provides": "EVENTS", "trust": "FIRST_PARTY",
        "access": "public web / ICS / ticketing embed",
        "portable_prompt": "Which theatre, dance, opera and symphony organisations perform here?",
        "examples": "a resident theatre company, a symphony season",
        "typical_yield": "season-based; sparse but high-value",
        "known_failure_modes": ["calendar lives inside a ticketing iframe"],
        "cost": "free",
    },
    "festival_feed": {
        "provides": "EVENTS", "trust": "FIRST_PARTY",
        "access": "public web / bespoke schedule app",
        "portable_prompt": "Which annual festivals run in the service area?",
        "examples": "a city's flagship music/film/food festivals",
        "typical_yield": "enormous, bursty, concentrated in a few weeks",
        "known_failure_modes": ["schedule only published weeks before",
                                "bespoke app with no feed", "Sched/Whova 403"],
        "cost": "free",
    },
    "local_media": {
        "provides": "EVENTS", "trust": "AGGREGATE",
        "access": "public web",
        "portable_prompt": "What is the alt-weekly, the city magazine, the local news site?",
        "examples": "an alt-weekly's listings section",
        "typical_yield": "good editorial curation; duplicates first-party rows",
        "known_failure_modes": ["commercial ToS limits automated access",
                                "listings behind a widget"],
        "cost": "free",
    },
    "broadcast_calendar": {
        "provides": "EVENTS", "trust": "USER",
        "access": "public web",
        "portable_prompt": "Which radio and TV stations run a community calendar?",
        "examples": "public radio events, a TV station's submitted-events page",
        "typical_yield": "wide but unverified — user-submitted",
        "known_failure_modes": ["submission spam", "no dedup", "stale entries"],
        "cost": "free",
    },
    "email_newsletter": {
        "provides": "EVENTS", "trust": "FIRST_PARTY",
        "access": "opt-in subscription to a dedicated mailbox",
        "portable_prompt": "Which venues announce ONLY by newsletter?",
        "examples": "a small room whose entire schedule ships as a weekly email",
        "typical_yield": "THE long tail. In Austin, 55 of 64 curated sources have "
                         "no machine-readable feed at all — newsletter is the "
                         "only route to them.",
        "known_failure_modes": ["needs a dedicated address", "parsing prose",
                                "no stable ids"],
        "cost": "free, but needs a mailbox and a parser",
    },
    "claimed_upload": {
        "provides": "EVENTS", "trust": "FIRST_PARTY",
        "access": "venue self-serve after ownership verification",
        "portable_prompt": "Can the venue claim its page and post directly?",
        "examples": "a claimed venue uploading its own schedule",
        "typical_yield": "small now, the strategic endgame later",
        "known_failure_modes": ["needs the claim flow to exist", "abuse without verification"],
        "cost": "free",
    },
    "social": {
        "provides": "EVENTS", "trust": "USER",
        "access": "platform API / public page",
        "portable_prompt": "Where do venues here actually announce — IG, FB, elsewhere?",
        "examples": "a venue's Instagram posts announcing a show",
        "typical_yield": "where the smallest rooms really live",
        "known_failure_modes": ["API access restricted", "no structured date",
                                "ToS forbids scraping"],
        "cost": "credentialed",
    },
    "link_hub": {
        "provides": "EVENTS", "trust": "USER",
        "access": "public web",
        "portable_prompt": "Do venues route their audience through a link aggregator?",
        "examples": "Linktree pointing at the real calendar",
        "typical_yield": "indirect — a pointer to the real source",
        "known_failure_modes": ["indirection only; no dates of its own"],
        "cost": "free",
    },
    "community_board": {
        "provides": "EVENTS", "trust": "USER",
        "access": "public web",
        "portable_prompt": "Is there a neighbourhood or scene-specific board?",
        "examples": "a DIY/punk scene calendar, a neighbourhood association",
        "typical_yield": "otherwise-invisible grassroots events",
        "known_failure_modes": ["irregular maintenance", "no schema"],
        "cost": "free",
    },

    # ---- VENUE sources: the DENOMINATOR ------------------------------------
    "alcohol_licensing": {
        "provides": "VENUES", "trust": "FIRST_PARTY",
        "access": "state open data",
        "portable_prompt": "What is this state's liquor-licence open dataset?",
        "examples": "TABC (Texas). Every state has an equivalent ABC body.",
        "typical_yield": "authoritative venue ENUMERATION, county-tagged — the "
                         "denominator, not events",
        "known_failure_modes": ["proxy only: misses all-ages/no-alcohol rooms, "
                                "includes bars that never host shows",
                                "schema drift on the portal"],
        "cost": "free",
    },
    "places_api": {
        "provides": "VENUES", "trust": "AGGREGATE",
        "access": "API key, usage-priced",
        "portable_prompt": "Which places API covers this metro?",
        "examples": "Google Places, Foursquare",
        "typical_yield": "the broadest venue enumeration, incl. non-alcohol rooms",
        "known_failure_modes": ["cost per call", "category noise",
                                "no event data at all"],
        "cost": "PAID — founder-crucial spend",
    },
    "open_data_portal": {
        "provides": "VENUES", "trust": "FIRST_PARTY",
        "access": "Socrata/CKAN open data",
        "portable_prompt": "Does the city/county publish permits, licences or venue registries?",
        "examples": "special-event permits, food/beverage licences",
        "typical_yield": "venue enumeration + sometimes one-off event permits",
        "known_failure_modes": ["dataset ids change", "coverage varies wildly by city"],
        "cost": "free",
    },
    "directory": {
        "provides": "VENUES", "trust": "AGGREGATE",
        "access": "public web",
        "portable_prompt": "Is there a local venue directory or music-office listing?",
        "examples": "a city music office's venue list, a chamber directory",
        "typical_yield": "curated venue enumeration",
        "known_failure_modes": ["stale", "no addresses"],
        "cost": "free",
    },

    # ---- IDENTITY + SIGNAL --------------------------------------------------
    "artist_identity": {
        "provides": "IDENTITY", "trust": "AGGREGATE",
        "access": "open API",
        "portable_prompt": "Same everywhere — one global spine.",
        "examples": "MusicBrainz",
        "typical_yield": "artist disambiguation; NOT a calendar",
        "known_failure_modes": ["mistaken for an event source"],
        "cost": "free",
    },
    "artist_aggregator": {
        "provides": "EVENTS", "trust": "AGGREGATE",
        "access": "API / public web",
        "portable_prompt": "Which tour-date aggregators cover artists playing here?",
        "examples": "Bandsintown, Songkick",
        "typical_yield": "touring acts; corroboration for first-party rows",
        "known_failure_modes": ["API access restricted", "duplicates ticketing"],
        "cost": "free to paid",
    },
    "music_platform": {
        "provides": "SIGNAL", "trust": "AGGREGATE",
        "access": "API",
        "portable_prompt": "Where do local artists publish releases?",
        "examples": "Bandcamp, Spotify",
        "typical_yield": "local-artist signal, occasional show announcements",
        "known_failure_modes": ["not a calendar", "API limits"],
        "cost": "free to paid",
    },
    "search_benchmark": {
        "provides": "SIGNAL", "trust": "AGGREGATE",
        "access": "manual",
        "portable_prompt": "What do we measure ourselves against?",
        "examples": "a competitor's listings page used as a recall benchmark",
        "typical_yield": "QA only — NEVER ingested",
        "known_failure_modes": ["mistaken for an ingestion source"],
        "cost": "free",
    },
}

# Classes whose rows may enter the event pipeline at all. `search_benchmark` is
# measurement, `artist_identity` is a spine, and the VENUES classes build the
# denominator — none of them are listings, and counting them as event sources is
# how a coverage number gets inflated by things that carry no dates.
EVENT_CLASSES = frozenset(
    k for k, v in SOURCE_CLASSES.items() if v["provides"] == "EVENTS")
VENUE_CLASSES = frozenset(
    k for k, v in SOURCE_CLASSES.items() if v["provides"] == "VENUES")


def portability_checklist() -> list:
    """The questions to answer when standing up a new metro, in priority order:
    events first (the payload), then venues (the denominator), then the rest."""
    order = {"EVENTS": 0, "VENUES": 1, "IDENTITY": 2, "SIGNAL": 3}
    return [
        {"class": name, "provides": meta["provides"],
         "question": meta["portable_prompt"], "cost": meta["cost"]}
        for name, meta in sorted(
            SOURCE_CLASSES.items(),
            key=lambda kv: (order[kv[1]["provides"]], kv[0]))
    ]
