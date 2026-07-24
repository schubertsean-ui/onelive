"""Carousel draft assembly — verbatim facts only, provenance on every slide.

Greppable summary: selects featurable events under the trust rules (spec
§1: confirmed freely; likely only with the quiet uncertainty affordance;
unverified/disputed never; CANONICAL PUBLISHED rows only — origin marker
required; event_status must be `scheduled`; unknown states fail loud),
excludes anything outside the series' truthful time window (no unverified
"tonight" claims — evaluator r1), assembles the hook -> events -> CTA
anatomy under the format physics in config.py, and stamps a canonical
SHA-256 content hash the publish gate binds approvals to. Error boundary
(evaluator r1): NoFeaturableEvents is the ONE expected skip condition;
every trust/misconfiguration defect raises CarouselTrustError and must
propagate loud — the agent loop never swallows it. No LLM call exists in
this path: overlay copy is template-framed verbatim event facts, and the
only descriptor slot requires Descriptor Foundry provenance.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from social.carousel.config import (
    BANNED_CLAIM_PHRASES,
    CarouselConfig,
    FEATURABLE_CONFIDENCE,
    FEATURABLE_EVENT_STATUS,
    HOOK_HEADLINE_MAX_WORDS,
    KNOWN_CONFIDENCE,
    KNOWN_EVENT_STATUS,
    SLIDE_COUNT_BANDS,
    SLIDE_OVERLAY_MAX_WORDS,
    SURFACE_CONSTRAINTS,
    TIMEFRAMES,
    validate_assignment,
)
from social.carousel.geo import hashtags_for

AGENT_AUTHOR = "onelive-carousel-agent"

# The structural "published canonical events only" check (evaluator r1): the
# canonical-event read path stamps this marker; candidate-store rows never
# carry it, so a candidate cannot be amplified even if handed in by mistake.
CANONICAL_ORIGIN = "canonical_event"

REQUIRED_EVENT_FIELDS = (
    "event_id",
    "name",
    "venue_name",
    "start_time",
    "confidence",
    "event_status",
    "origin",
    "domain_id",
    "source",
)


class CarouselTrustError(ValueError):
    """A trust or configuration violation — must always propagate loud."""


class NoFeaturableEvents(ValueError):
    """Expected volume weather: nothing featurable for this series/window.
    The ONE condition the agent loop may record as a skip."""


@dataclass(frozen=True)
class Slide:
    """One carousel card. kind: hook | event | cta."""

    kind: str
    headline: str
    overlay_lines: tuple[str, ...] = field(default_factory=tuple)
    image_ref: str = ""
    alt_text: str = ""
    # Trust plumbing: which event this slide asserts, from which source,
    # and whether the quiet uncertainty affordance must render (likely).
    event_id: str = ""
    source: str = ""
    confidence: str = ""
    uncertainty_marker: bool = False


@dataclass(frozen=True)
class CarouselDraft:
    """A complete, renderable carousel proposal awaiting human custody."""

    series_key: str
    surface: str
    tier: str
    timeframe: str
    author: str
    assignment: dict[str, str]
    slides: tuple[Slide, ...]
    caption: str
    hashtags: tuple[str, ...]
    short_link: str
    post_slot: str


def content_hash(draft: CarouselDraft) -> str:
    """Canonical SHA-256 over the draft's full content. Approvals bind to
    this; any post-approval edit changes the hash and voids the approval."""
    payload = json.dumps(asdict(draft), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def all_draft_text(draft: CarouselDraft) -> list[str]:
    """Every human- or machine-facing text the draft would publish — the
    surface the release gate must rescan in full (evaluator r1)."""
    texts: list[str] = []
    for slide in draft.slides:
        texts.append(slide.headline)
        texts.extend(slide.overlay_lines)
        texts.append(slide.alt_text)
    texts.append(draft.caption)
    texts.extend(draft.hashtags)
    texts.append(draft.short_link)
    return texts


def _check_event(event: dict) -> None:
    missing = [k for k in REQUIRED_EVENT_FIELDS if not event.get(k)]
    if missing:
        raise CarouselTrustError(
            f"event missing required fields {missing}: {event.get('event_id', '<no id>')}"
        )
    if event["origin"] != CANONICAL_ORIGIN:
        raise CarouselTrustError(
            f"event {event['event_id']} origin {event['origin']!r} is not the "
            f"canonical published read path ({CANONICAL_ORIGIN!r}) — candidate/"
            "pipeline rows are never amplified"
        )
    if event["confidence"] not in KNOWN_CONFIDENCE:
        raise CarouselTrustError(
            f"unknown confidence state {event['confidence']!r} on "
            f"{event['event_id']} — refusing to classify it as featurable"
        )
    if event["event_status"] not in KNOWN_EVENT_STATUS:
        raise CarouselTrustError(
            f"unknown event_status {event['event_status']!r} on {event['event_id']}"
        )
    descriptor = event.get("foundry_descriptor")
    if descriptor is not None:
        if not isinstance(descriptor, dict) or not descriptor.get("text") or not descriptor.get("provenance"):
            raise CarouselTrustError(
                f"foundry_descriptor on {event['event_id']} lacks text/provenance — "
                "descriptor copy must carry Descriptor Foundry provenance"
            )


def within_timeframe(start_time: str, reference_date: str, timeframe: str) -> bool:
    """Truthful-window check: does this event's date fall inside the window
    the carousel's copy will claim? Past events never qualify."""
    window = TIMEFRAMES[timeframe]["window_days"]
    event_date = date.fromisoformat(start_time[:10])
    ref = date.fromisoformat(reference_date[:10])
    return ref <= event_date <= ref + timedelta(days=int(window))


def select_featurable(events: list[dict]) -> list[dict]:
    """Trust selection (spec §1): confirmed first, then likely; scheduled
    only; the rest are never featured. Unknown states fail loud — a new
    state must be classified deliberately, never defaulted into marketing."""
    for event in events:
        _check_event(event)
    featurable = [
        e
        for e in events
        if e["confidence"] in FEATURABLE_CONFIDENCE
        and e["event_status"] in FEATURABLE_EVENT_STATUS
    ]
    # Order: trust state (confirmed first), then data completeness (image +
    # price present), then earliest start. No paid-placement input exists
    # here; adding one is a trust-invariant change (spec §1).
    def sort_key(e: dict):
        completeness = int(bool(e.get("image_url"))) + int(e.get("price_min") is not None)
        return (
            0 if e["confidence"] == "confirmed" else 1,
            -completeness,
            e["start_time"],
            e["event_id"],
        )

    return sorted(featurable, key=sort_key)


def _cap_words(text: str, max_words: int, label: str) -> str:
    if len(text.split()) > max_words:
        raise CarouselTrustError(f"{label} exceeds {max_words} words: {text!r}")
    return text


def _scan_banned(text: str, context: str) -> None:
    lowered = text.lower()
    for phrase in BANNED_CLAIM_PHRASES:
        if phrase in lowered:
            raise CarouselTrustError(f"banned claim phrase {phrase!r} in {context}: {text!r}")


def _hook_headline(hook_type: str, events: list[dict], config: CarouselConfig) -> str:
    """Deterministic hook templates over REAL aggregates only — a number
    promise is computed from the actual lineup, and the time phrase is the
    verified window, never an asserted 'tonight'."""
    n = len(events)
    phrase = str(TIMEFRAMES[config.timeframe]["phrase"])
    priced = [e["price_min"] for e in events if e.get("price_min") is not None]
    if hook_type == "number_promise":
        if priced:
            return f"{n} nights out under ${int(max(priced))}"
        return f"{n} real events, {config.city} {phrase.lower()}"
    if hook_type == "curiosity_gap":
        return f"{phrase} in {config.city} hits different"
    if hook_type == "awe":
        return f"{config.city} is loud {phrase.lower()}"
    if hook_type == "humor":
        return f"Your couch can wait, {config.city}"
    if hook_type == "social_proof":
        return f"Where {config.city} actually goes"
    if hook_type == "edition_anchor":
        return f"{phrase} in {config.city}"
    raise CarouselTrustError(f"unknown hook_type {hook_type!r}")


def _cta_lines(cta_type: str) -> tuple[str, ...]:
    ctas = {
        "save_this": ("Save this for the plan",),
        "send_to_friend": ("Send this to the friend who's always down",),
        "tag_who": ("Tag who you're taking",),
        "follow_for_daily": ("New edition every day. Follow along",),
        "link_in_bio": ("Every detail, one tap. Link in bio",),
    }
    if cta_type not in ctas:
        raise CarouselTrustError(f"unknown cta_type {cta_type!r}")
    return ctas[cta_type]


def _event_overlay(event: dict, timeframe: str) -> tuple[str, ...]:
    """Verbatim facts, one idea per slide: name / venue / when / price.
    Beyond tonight, the date is part of the fact — time alone would imply
    tonight (the r1 truthful-framing rule)."""
    clock = event["start_time"][11:16] if len(event["start_time"]) >= 16 else ""
    if timeframe == "tonight":
        when = clock
    else:
        event_date = date.fromisoformat(event["start_time"][:10])
        when = f"{event_date.strftime('%b %d')} · {clock}" if clock else event_date.strftime("%b %d")
    lines = [event["name"], f"{event['venue_name']} · {when}"]
    if event.get("price_min") is not None:
        price = event["price_min"]
        lines.append("Free" if price == 0 else f"From ${int(price)}")
    descriptor = event.get("foundry_descriptor")
    if descriptor:
        lines.append(descriptor["text"])
    return tuple(lines)


def _alt_text(event: dict, config: CarouselConfig) -> str:
    when = event["start_time"][:16].replace("T", " at ")
    return (
        f"{event['name']} at {event['venue_name']}, {config.city}, {when}. "
        f"Listing via {event['source']}."
    )


def _caption(config: CarouselConfig, style: str, events: list[dict], short_link: str) -> str:
    n = len(events)
    phrase = str(TIMEFRAMES[config.timeframe]["phrase"])
    lead = {
        "short_punch": f"{phrase} in {config.city}. {n} real ones.",
        "mini_story": (
            f"Somewhere in {config.city} {phrase.lower()} there's a room "
            f"that's about to go off. {n} candidates inside."
        ),
        "list": f"{n} events. {phrase}, {config.city}:",
    }
    if style not in lead:
        raise CarouselTrustError(f"unknown caption_style {style!r}")
    body = lead[style]
    if style == "list":
        body += "".join(f"\n• {e['name']} — {e['venue_name']}" for e in events[:5])
    # No badge language here (design brief trust display rules) — the
    # caption points at the product, where provenance is shown properly.
    return f"{body}\nReal listings, real sources. {short_link}"


def build_carousel(
    events: list[dict],
    config: CarouselConfig,
    assignment: dict[str, str],
    *,
    reference_date: str,
) -> CarouselDraft:
    """Assemble one draft: hook slide, one event per slide, CTA close —
    under the surface's hard slide bounds, the word caps, and the series'
    truthful time window (reference_date anchors it; passed in explicitly
    so cycles are reproducible). Raises CarouselTrustError on any trust or
    format violation, NoFeaturableEvents when the window is honestly empty
    — a draft that cannot be built honestly is not built at all."""
    config.validate()
    validate_assignment(assignment)
    featurable = [
        e
        for e in select_featurable(events)
        if within_timeframe(e["start_time"], reference_date, config.timeframe)
    ]
    if not featurable:
        raise NoFeaturableEvents(
            f"no featurable events inside the {config.timeframe} window from "
            f"{reference_date} — a carousel never posts thin or empty"
        )

    constraints = SURFACE_CONSTRAINTS[config.surface]
    band_lo, band_hi = SLIDE_COUNT_BANDS[assignment["slide_count_band"]]
    max_event_slides = min(band_hi, constraints.max_slides) - 2  # hook + CTA
    featured = featurable[:max_event_slides]

    hook_text = _cap_words(
        _hook_headline(assignment["hook_type"], featured, config),
        HOOK_HEADLINE_MAX_WORDS,
        "hook headline",
    )
    slides = [
        Slide(
            kind="hook",
            headline=hook_text,
            alt_text=f"Cover: {hook_text}. OneLive {config.city} carousel.",
            image_ref=featured[0].get("image_url", ""),
        )
    ]
    for event in featured:
        overlay = _event_overlay(event, config.timeframe)
        for line in overlay:
            _cap_words(line, SLIDE_OVERLAY_MAX_WORDS, f"slide overlay ({event['event_id']})")
        slides.append(
            Slide(
                kind="event",
                headline=event["name"],
                overlay_lines=overlay,
                image_ref=event.get("image_url", ""),
                alt_text=_alt_text(event, config),
                event_id=event["event_id"],
                source=event["source"],
                confidence=event["confidence"],
                uncertainty_marker=event["confidence"] == "likely",
            )
        )
    slides.append(
        Slide(
            kind="cta",
            headline=_cta_lines(assignment["cta_type"])[0],
            overlay_lines=_cta_lines(assignment["cta_type"]),
            alt_text="Closing card: share or save this OneLive carousel.",
        )
    )

    if not (constraints.min_slides <= len(slides) <= constraints.max_slides):
        raise CarouselTrustError(
            f"slide count {len(slides)} outside {config.surface} bounds "
            f"[{constraints.min_slides}, {constraints.max_slides}]"
        )

    short_link = f"{config.short_link_base}?utm_source={config.surface}&utm_campaign={config.series_key}"
    caption = _caption(config, assignment["caption_style"], featured, short_link)
    draft = CarouselDraft(
        series_key=config.series_key,
        surface=config.surface,
        tier=config.tier,
        timeframe=config.timeframe,
        author=AGENT_AUTHOR,
        assignment=dict(assignment),
        slides=tuple(slides),
        caption=caption,
        hashtags=hashtags_for(config.city, featured),
        short_link=short_link,
        post_slot=assignment["post_slot"],
    )
    for text in all_draft_text(draft):
        _scan_banned(text, "draft content")
    return draft
