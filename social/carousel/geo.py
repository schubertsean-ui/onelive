"""GEO/SEO discovery bundle — machine legibility for every carousel (spec §8).

Greppable summary: schema.org Event + SocialMediaPosting JSON-LD, Open
Graph tags, per-slide alt text, a small-specific hashtag set (research
consensus: 3-5 focused tags beat tag walls), and an llms.txt block so the
linked landing page answers AI crawlers with gate-verified, attributed
facts. One generator feeds both the carousel captions and the /tonight
pages so structured data can never drift between surfaces. Attribution is
always present and never cloaked — being the verifiable source IS the GEO
strategy.
"""
from __future__ import annotations

import json

MAX_HASHTAGS = 5

# Domain id -> the community tag that field actually uses (Austin-first;
# per-metro tables extend this as markets open).
DOMAIN_TAGS = {
    "live_music": "livemusic",
    "comedy": "comedy",
    "theater": "theater",
    "nightlife": "nightlife",
    "food_drink": "foodie",
    "visual_arts": "artopening",
    "film": "filmscreening",
    "dance": "dance",
    "festivals": "festival",
}


def hashtags_for(city: str, events: list[dict]) -> tuple[str, ...]:
    """3-5 specific tags: city, city+scene, then the featured domains'
    community tags in lineup order. Deterministic, deduplicated, capped."""
    if not city:
        raise ValueError("city required for hashtag frame")
    slug = city.lower().replace(" ", "")
    tags = [f"#{slug}", f"#{slug}events"]
    for event in events:
        domain_tag = DOMAIN_TAGS.get(event.get("domain_id", ""))
        if domain_tag:
            candidate = f"#{slug}{domain_tag}"
            if candidate not in tags:
                tags.append(candidate)
        if len(tags) >= MAX_HASHTAGS:
            break
    return tuple(tags[:MAX_HASHTAGS])


def event_jsonld(event: dict, city: str) -> dict:
    """schema.org Event markup for one canonical event. Only asserts fields
    that exist — absent data is omitted, never invented."""
    for key in ("event_id", "name", "venue_name", "start_time", "source"):
        if not event.get(key):
            raise ValueError(f"event_jsonld missing required field {key!r}")
    doc: dict = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": event["name"],
        "startDate": event["start_time"],
        "eventStatus": "https://schema.org/EventScheduled",
        "location": {
            "@type": "Place",
            "name": event["venue_name"],
            "address": {"@type": "PostalAddress", "addressLocality": city},
        },
        "identifier": event["event_id"],
        # Attribution rides the markup: the source is part of the fact.
        "isBasedOn": event["source"],
    }
    if event.get("venue_address"):
        doc["location"]["address"]["streetAddress"] = event["venue_address"]
    if event.get("artist_name"):
        doc["performer"] = {"@type": "PerformingGroup", "name": event["artist_name"]}
    if event.get("price_min") is not None:
        doc["offers"] = {
            "@type": "Offer",
            "price": str(event["price_min"]),
            "priceCurrency": "USD",
        }
    if event.get("image_url"):
        doc["image"] = event["image_url"]
    return doc


def carousel_jsonld(draft, events: list[dict], city: str) -> dict:
    """SocialMediaPosting markup wrapping the featured events' Event nodes.
    `draft` is any object with caption/short_link/hashtags attributes."""
    return {
        "@context": "https://schema.org",
        "@type": "SocialMediaPosting",
        "headline": draft.slides[0].headline,
        "articleBody": draft.caption,
        "url": draft.short_link,
        "keywords": ", ".join(tag.lstrip("#") for tag in draft.hashtags),
        "about": [event_jsonld(e, city) for e in events],
    }


def og_tags(draft, city: str) -> dict[str, str]:
    """Open Graph tags for the landing page the carousel links to."""
    return {
        "og:title": draft.slides[0].headline,
        "og:description": draft.caption.split("\n")[0],
        "og:url": draft.short_link,
        "og:type": "website",
        "og:site_name": "OneLive",
        "og:locale": "en_US",
        "og:image:alt": draft.slides[0].alt_text,
        "article:section": f"Events in {city}",
    }


def llms_txt_block(events: list[dict], city: str) -> str:
    """Markdown block for the site's llms.txt: gate-settled facts with
    per-line source attribution, so answer engines can cite us precisely."""
    lines = [f"## Tonight in {city} — event listings with confidence + source", ""]
    for event in events:
        when = event["start_time"][:16].replace("T", " ")
        lines.append(
            f"- {event['name']} — {event['venue_name']}, {when} "
            f"(confidence: {event['confidence']}; source: {event['source']})"
        )
    return "\n".join(lines)


def discovery_bundle(draft, events: list[dict], city: str) -> dict:
    """Everything machine-facing for one carousel, in one artifact:
    regenerated on every post and every event change (freshness is a
    pipeline property, not a campaign)."""
    return {
        "carousel_jsonld": carousel_jsonld(draft, events, city),
        "event_jsonld": [event_jsonld(e, city) for e in events],
        "og_tags": og_tags(draft, city),
        "llms_txt_block": llms_txt_block(events, city),
        "alt_texts": [slide.alt_text for slide in draft.slides],
        "canonical_json": json.dumps(
            [e["event_id"] for e in events], sort_keys=True
        ),
    }
