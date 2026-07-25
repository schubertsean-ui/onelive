"""Category resolver — assign a cultural DOMAIN (+ best-effort genre) to an event
from the STRONGEST available real signal, with provenance on every decision.

The founder's objection (2026-07-25), taken literally and correctly: category is
NOT guessable from a title keyword table alone when you can READ what the source
and the venue actually are. A comedy club's show is comedy; a museum's event is
visual-arts; a brewery's is food-drink; a schema.org `MusicEvent` is live-music —
regardless of what the title says. So this resolver reads signals in descending
authority and records WHICH signal decided (the graph-engineering "every claim
has a source" invariant):

  1. schema.org @type            (the event's OWN declared machine type — best)
  2. provider taxonomy domain    (Ticketmaster/SeatGeek/Eventbrite already mapped)
  3. venue business type / hint  (what KIND of business hosts it — Google Places
                                  primaryType, or the curated source cultural_domain:
                                  "you know what kind of business it is")
  4. title keywords              (deterministic last-resort read of the literal name)

Returns UNMAPPED (honest "Other") only when EVERY signal is silent — never a
fabricated domain. Pure + deterministic ⇒ unit-tested without a network or DB.

This is the machine mapping's classifier layer; the domain ids and the genre
sub-taxonomy are owned by docs/strategy/ONE_LIVE_CATEGORY_TAXONOMY_v1.md and
worker/importers/domain_map.py (kept in sync).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from worker.importers.domain_map import (
    DOMAINS,
    UNMAPPED,
    classify_from_title,
)

_DOMAIN_SET = set(DOMAINS)

# ── Signal 1: schema.org Event subtypes → domain ─────────────────────────────
# The schema.org Event type hierarchy is a real, widely-emitted taxonomy (venues
# on WordPress "The Events Calendar", Squarespace, universities on Localist emit
# it as JSON-LD). The event's own declared @type is the most authoritative signal.
_SCHEMA_TYPE_DOMAIN = {
    "musicevent": "live-music",
    "theaterevent": "theater",
    "comedyevent": "comedy",
    "danceevent": "dance",
    "screeningevent": "film",
    "literaryevent": "literary",
    "visualartsevent": "visual-arts",
    "exhibitionevent": "visual-arts",
    "educationevent": "ideas",
    "businessevent": "ideas",
    "hackathon": "ideas",
    "courseinstance": "ideas",
    "foodevent": "food-drink",
    "socialevent": "community",
    "childrensevent": "family",
    "sportsevent": "sports",
    "festival": "festivals",
    "publicationevent": "literary",
}

# ── Signal 3: venue business type → domain ───────────────────────────────────
# What KIND of venue hosts the event — a strong prior when the event itself
# declared no type. Keys are Google Places primaryType tokens (the standard
# venue-classification vocabulary) PLUS common curated tokens; the curated source
# `cultural_domain` (already a domain id) is accepted directly as a hint.
_VENUE_TYPE_DOMAIN = {
    "comedy_club": "comedy",
    "night_club": "nightlife",
    "bar": "nightlife",
    "wine_bar": "food-drink",
    "brewery": "food-drink",
    "brewpub": "food-drink",
    "winery": "food-drink",
    "distillery": "food-drink",
    "restaurant": "food-drink",
    "cafe": "food-drink",
    "performing_arts_theater": "performing-arts",
    "concert_hall": "live-music",
    "amphitheater": "live-music",
    "opera_house": "performing-arts",
    "dance_hall": "dance",
    "movie_theater": "film",
    "art_gallery": "visual-arts",
    "museum": "visual-arts",
    "library": "library",
    "book_store": "literary",
    "stadium": "sports",
    "arena": "sports",
    "university": "ideas",
    "school": "ideas",
    "community_center": "community",
    "church": "community",
    "park": "community",
}


@dataclass(frozen=True)
class CategoryResult:
    """The classifier's verdict + its provenance (which signal decided, and the
    literal evidence). `domain` is UNMAPPED when no signal fired."""

    domain: str
    genre: Optional[str]
    signal: str   # 'schema.org @type' | 'provider taxonomy' | 'venue business type' | 'title keywords' | 'none'
    evidence: Optional[str]

    @property
    def mapped(self) -> bool:
        return self.domain != UNMAPPED


def _norm_type(t: Optional[str]) -> str:
    """Normalize a schema.org @type ('http://schema.org/MusicEvent', 'MusicEvent',
    'schema:MusicEvent') to a bare lowercase token."""
    if not t:
        return ""
    return t.strip().rstrip("/").split("/")[-1].split(":")[-1].strip().lower()


def _genre_from_title(domain: str, title: Optional[str]) -> Optional[str]:
    """Best-effort genre WITHIN a resolved domain, from the title's own words.
    classify_from_title already returns a sub-label for a few domains (Ballet,
    Drag, Cabaret); reuse it only when it agrees with the resolved domain so we
    never attach a genre from a different field."""
    dom2, subseg = classify_from_title(title)
    if subseg and dom2 == domain:
        return subseg
    return None


def resolve_category(
    *,
    schema_type: Optional[str] = None,
    provider_domain: Optional[str] = None,
    venue_domain_hint: Optional[str] = None,
    venue_business_type: Optional[str] = None,
    title: Optional[str] = None,
) -> CategoryResult:
    """Resolve an event's cultural domain from the strongest available signal.

    Args (all optional — pass what you have; more signal = better result):
      schema_type:        the event's schema.org @type (JSON-LD), e.g. 'MusicEvent'.
      provider_domain:    a domain id already mapped from a provider taxonomy
                          (Ticketmaster/SeatGeek/Eventbrite) — pass UNMAPPED/None
                          if the provider gave no usable classification.
      venue_domain_hint:  a curated OneLive domain id for the host venue/source
                          (e.g. the source catalog's `cultural_domain`).
      venue_business_type: a raw venue-type token (Google Places primaryType).
      title:              the event's literal name — the last-resort signal.
    """
    # 1. The event's OWN declared machine type — most authoritative.
    st = _norm_type(schema_type)
    if st in _SCHEMA_TYPE_DOMAIN:
        dom = _SCHEMA_TYPE_DOMAIN[st]
        return CategoryResult(dom, _genre_from_title(dom, title),
                              "schema.org @type", st)

    # 2. Provider taxonomy (the licensed APIs' own classification, already mapped).
    if provider_domain and provider_domain in _DOMAIN_SET and provider_domain != UNMAPPED:
        return CategoryResult(provider_domain, _genre_from_title(provider_domain, title),
                              "provider taxonomy", provider_domain)

    # 3. What KIND of business hosts it. Prefer the CURATED source domain hint
    #    (human-vetted) over a raw Places type (machine-inferred).
    if venue_domain_hint and venue_domain_hint in _DOMAIN_SET and venue_domain_hint != UNMAPPED:
        return CategoryResult(venue_domain_hint, _genre_from_title(venue_domain_hint, title),
                              "venue business type", f"source domain={venue_domain_hint}")
    vt = (venue_business_type or "").strip().lower()
    if vt in _VENUE_TYPE_DOMAIN:
        dom = _VENUE_TYPE_DOMAIN[vt]
        return CategoryResult(dom, _genre_from_title(dom, title),
                              "venue business type", f"venue type={vt}")

    # 4. Deterministic last-resort read of the event's literal title.
    dom, subseg = classify_from_title(title)
    if dom != UNMAPPED:
        return CategoryResult(dom, subseg, "title keywords", (title or "").strip() or None)

    # Every signal silent → honest "Other", never a fabricated domain.
    return CategoryResult(UNMAPPED, None, "none", None)
