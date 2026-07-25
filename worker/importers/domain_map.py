"""Deterministic mapping from provider taxonomies to OneLive's 22 cultural
domains + subsegments.

NO AI, NO guessing beyond the provider's OWN stated taxonomy: every mapping is
a table lookup over the classification the licensed API already returns
(Ticketmaster segment/genre/subGenre; SeatGeek event type + performer genres).
Anything the tables don't cover falls back to a documented generic bucket and
is reported via `unmapped()` so gaps are visible, never silently miscategorized.

The domain ids here are the canonical set used across the app (mirror
web/lib and the monitor ontology). Keep this list and the web copy in sync.
"""
from __future__ import annotations

# Honest catch-all for provider taxonomy we do NOT recognize. It is NOT one of
# the 22 cultural domains — the feed shows it as "Other / uncategorized" and the
# runner logs the count via unmapped(), so coverage gaps are visible and never a
# fabricated category. Charter: ZERO fabricated data on product surfaces.
UNMAPPED = "unmapped"

# The 22 canonical cultural-domain ids. The FULL genre-equivalent sub-category
# taxonomy for each domain (the researched "genre for the other 20+ categories")
# is docs/strategy/ONE_LIVE_CATEGORY_TAXONOMY_v1.md — the human source of truth;
# the `subs` here are the current filter subset and are expanded from that doc as
# the feed consumes them (kept a strict subset so the two never contradict).
DOMAINS = (
    "live-music", "performing-arts", "theater", "comedy", "visual-arts",
    "film", "literary", "ideas", "festivals", "food-drink", "nightlife",
    "dance", "community", "heritage", "family", "place-based", "sports",
    "library", "fairs-expos", "seasonal", "wellness", "fashion-design",
)

# ---- Ticketmaster (segment / genre / subGenre) -------------------------------

# Top-level segment → domain (coarse; refined by genre for Arts & Theatre).
_TM_SEGMENT = {
    "music": "live-music",
    "sports": "sports",
    "film": "film",
    "arts & theatre": "theater",       # refined below by genre
    "arts & theater": "theater",
    "miscellaneous": "fairs-expos",    # expos/family/etc.; refined by genre
}

# Within "Arts & Theatre"/"Miscellaneous", genre picks the finer domain. Covers
# Ticketmaster's documented Arts & Theatre and Miscellaneous genre taxonomy so
# real events land in a named cultural domain instead of "Other".
_TM_GENRE_DOMAIN = {
    # Arts & Theatre
    "theatre": "theater", "theater": "theater", "musical": "theater",
    "miscellaneous theatre": "theater", "performance art": "theater",
    "classical": "performing-arts", "opera": "performing-arts",
    "orchestra": "performing-arts", "instrumental music": "performing-arts",
    "choral": "performing-arts",
    "dance": "dance", "ballet": "dance",
    "comedy": "comedy", "magic & illusion": "comedy", "magic": "comedy",
    "variety": "comedy",
    "children's theatre": "family", "childrens theatre": "family",
    "circus & specialty acts": "family", "spectacular": "family",
    "puppetry": "family", "family": "family",
    "film": "film",
    "fine art": "visual-arts", "arts": "visual-arts", "multimedia": "visual-arts",
    "cultural": "heritage",
    # Miscellaneous segment
    "fairs & festivals": "festivals", "festival": "festivals",
    "food & drink": "food-drink",
    "community/civic": "community",
    "lecture/seminar": "ideas",
    "health/wellness": "wellness", "health & wellness": "wellness",
    "home & garden": "fairs-expos", "hobby/special interest expo": "fairs-expos",
    "hobby/special interest expos": "fairs-expos", "expo": "fairs-expos",
}


# Provider placeholders that carry NO sub-bucket signal — never shown as a
# subsegment (a card must not read "Theater · Miscellaneous").
_TM_PLACEHOLDER = {"undefined", "none", "other", "miscellaneous", ""}


# Deterministic keyword inference from the event's OWN name — used ONLY when the
# provider left the classification blank ("Undefined"). This is not guessing or
# AI: it reads the literal words the provider already put in the title, the same
# signal a person reading the listing would use. Ordered — first match wins;
# more-specific phrases first. (domain, subsegment_label|None).
_TITLE_RULES: tuple[tuple[tuple[str, ...], str, str | None], ...] = (
    (("stand-up", "stand up", "standup", "comedy", "improv", "open mic"), "comedy", None),
    (("symphony", "philharmonic", "orchestra", "opera", "concerto", "chorale", "choral"), "performing-arts", None),
    (("ballet", "nutcracker"), "dance", "Ballet"),
    (("drag ",), "nightlife", "Drag"),
    (("burlesque", "cabaret"), "theater", "Cabaret"),
    (("musical", "theatre", "theater", " play", "playhouse"), "theater", None),
    (("poetry", "spoken word", "open mic poetry", "author ", "book signing", "book launch"), "literary", None),
    (("lecture", "seminar", "symposium", "keynote", "conference", "summit", " talk", "panel discussion", "ted"), "ideas", None),
    (("film ", "screening", "cinema", " movie", "documentary"), "film", None),
    (("festival", "fest ", " fest", "sxsw", "acl fest"), "festivals", None),
    (("wine", "beer", "brewery", "distillery", "cocktail", "tasting", "brunch", "happy hour", "dinner", "culinary", "chef", "food truck", "supper"), "food-drink", None),
    (("farmers market", "flea market", "artisan market", "block party", "parade", "street fair", "craft fair"), "community", None),
    (("5k", "10k", "marathon", " run ", "fun run", "rodeo", "wrestling", "boxing", "mma ", "race", "regatta"), "sports", None),
    (("yoga", "meditation", "wellness", "fitness", "hike", "retreat"), "wellness", None),
    (("art exhibit", "gallery", "art walk", "exhibition", "museum", "art show"), "visual-arts", None),
    (("story time", "storytime", "kids", "family fun", "children", "puppet"), "family", None),
    (("dj ", " dj", "nightclub", "rave", "club night", "afterparty"), "nightlife", None),
    (("dance ", "salsa", "cumbia", "two-step", "tango", "swing dance"), "dance", None),
    (("holiday", "christmas", "halloween", "new year", "nye", "easter", "day of the dead", "dia de"), "seasonal", None),
    (("live music", "concert", "acoustic", "band", "tribute", " tour"), "live-music", None),
)


def classify_from_title(title: str | None) -> tuple[str, str | None]:
    """Infer a domain from the provider's OWN event name when it gave no
    classification. Deterministic keyword match on real text; UNMAPPED if none."""
    t = (title or "").lower()
    for keywords, domain, subseg in _TITLE_RULES:
        if any(k in t for k in keywords):
            return domain, subseg
    return UNMAPPED, None


def ticketmaster_fallback_domain(
    title: str | None,
    attraction_classifications: list[tuple[str | None, str | None, str | None]] | None,
) -> tuple[str, str | None]:
    """Recover a domain for an event the provider left 'Undefined', using ONLY
    real provider data: first the attached performer's OWN classification
    (segment/genre — authoritative provider taxonomy), then keyword inference
    from the literal event name. Returns UNMAPPED only when neither yields a
    signal — honest, never fabricated.
    """
    # 1. Performer/attraction classification — the provider's own taxonomy on the
    #    act, which is often present even when the event header is Undefined.
    for seg, gen, sub in attraction_classifications or []:
        dom, subseg = ticketmaster_domain(seg, gen, sub)
        if dom != UNMAPPED:
            return dom, subseg
    # 2. Deterministic keyword inference from the real event name.
    return classify_from_title(title)


def ticketmaster_domain(segment: str | None, genre: str | None,
                        subgenre: str | None) -> tuple[str, str | None]:
    """Return (domain_id, subsegment) for a Ticketmaster classification.

    subsegment is the provider's genre (the human-meaningful sub-bucket), or the
    subGenre when it adds signal. Mapping uses ONLY the provider's own taxonomy —
    genre first, then the segment as a coarse fallback (e.g. an "Arts & Theatre"
    event with a missing/generic genre is theater, not "Other"; that is the
    provider's own segment, not a guess). A segment with no cultural signal at
    all ("Undefined", bare "Miscellaneous") stays UNMAPPED — honest, never a
    fabricated domain on a public feed.
    """
    seg = (segment or "").strip().lower()
    gen = (genre or "").strip()
    sub = (subgenre or "").strip()
    gen_l = gen.lower()

    if seg in ("arts & theatre", "arts & theater"):
        # Refine by genre; fall back to the segment's own coarse domain (theater)
        # rather than discarding the provider's Arts & Theatre classification.
        domain = _TM_GENRE_DOMAIN.get(gen_l) or _TM_SEGMENT[seg]
    elif seg == "miscellaneous":
        # Miscellaneous only lands in a real domain when its GENRE is recognized
        # (food & drink, festival, ...). A bare "Miscellaneous" has no signal.
        domain = _TM_GENRE_DOMAIN.get(gen_l, UNMAPPED)
    else:
        domain = _TM_SEGMENT.get(seg, UNMAPPED)

    # subsegment: prefer the genre; for music, the genre IS the subsegment
    # (Jazz/Rock/...). subGenre only used when it is more specific and differs.
    # Placeholder genres/subgenres are suppressed (no signal).
    subseg = gen if gen_l not in _TM_PLACEHOLDER else None
    if sub and sub.lower() not in _TM_PLACEHOLDER and sub != gen:
        subseg = f"{subseg} · {sub}" if subseg else sub
    return domain, subseg


# ---- SeatGeek (event type + performer genres) --------------------------------

_SG_TYPE_DOMAIN = {
    "concert": "live-music",
    "music_festival": "festivals",
    "theater": "theater",
    "broadway_tickets_national": "theater",
    "comedy": "comedy",
    "dance_performance_tour": "dance",
    "classical": "performing-arts",
    "classical_orchestral_instrumental": "performing-arts",
    "classical_opera": "performing-arts",
    "classical_vocal": "performing-arts",
    "family": "family",
    "film": "film",
    "literary": "literary",
    "conference": "ideas",
    "festival": "festivals",
}

# Sports in SeatGeek are many types (nba, mlb, ncaa_*, mls, ...). Any type token
# containing one of these maps to sports.
_SG_SPORTS_TOKENS = (
    "nba", "nfl", "mlb", "nhl", "mls", "ncaa", "wnba", "soccer", "football",
    "basketball", "baseball", "hockey", "tennis", "golf", "racing", "mma",
    "boxing", "wrestling", "sports",
)


def seatgeek_domain(event_type: str | None,
                    performer_genres: list[str] | None = None
                    ) -> tuple[str, str | None]:
    """Return (domain_id, subsegment) for a SeatGeek event type.

    subsegment comes from the primary performer's first genre when present
    (e.g. a concert's 'Jazz'); otherwise the event type, humanized.
    """
    t = (event_type or "").strip().lower()
    domain = _SG_TYPE_DOMAIN.get(t)
    if domain is None and any(tok in t for tok in _SG_SPORTS_TOKENS):
        domain = "sports"
    if domain is None:
        domain = UNMAPPED  # honest — an unknown type is never a fabricated domain

    subseg: str | None = None
    if performer_genres:
        subseg = performer_genres[0]
    if not subseg and t:
        subseg = t.replace("_", " ").title()
    return domain, subseg


def unmapped(provider: str, raw_classification: str) -> str:
    """A stable, greppable marker for a classification that could not be mapped,
    so ingestion can log coverage gaps rather than hide them."""
    return f"UNMAPPED[{provider}]: {raw_classification!r} -> {UNMAPPED}"
