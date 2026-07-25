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

import dataclasses
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from social.carousel.config import (
    BANNED_CLAIM_PHRASES,
    CarouselTrustError,
    CarouselConfig,
    FEATURABLE_CONFIDENCE,
    FEATURABLE_EVENT_STATUS,
    HOOK_HEADLINE_MAX_WORDS,
    KNOWN_CONFIDENCE,
    KNOWN_EVENT_STATUS,
    LISTICLE_SIZES,
    SLIDE_OVERLAY_MAX_WORDS,
    SURFACE_CONSTRAINTS,
    TIMEFRAMES,
    TONIGHT_EARLIEST_HOUR,
    validate_assignment,
)
from social.carousel.geo import discovery_bundle, hashtags_for

AGENT_AUTHOR = "onelive-carousel-agent"

# The render surface an autonomy grant freezes (r10): a grant covers
# EXACTLY this code; any change to these files voids it until re-signed.
_RENDER_SURFACE_FILES = ("config.py", "generator.py", "geo.py", "scenarios.py")


def renderer_fingerprint() -> str:
    """SHA-256 over the render-surface module bytes. Autonomy records bind
    to this value; release under autonomy requires equality."""
    import os as _os

    digest = hashlib.sha256()
    base = _os.path.dirname(__file__)
    for name in _RENDER_SURFACE_FILES:
        with open(_os.path.join(base, name), "rb") as fh:
            digest.update(name.encode())
            digest.update(fh.read())
    return digest.hexdigest()

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
    # when it starts (so the release gate can re-check future-ness with its
    # own clock), and whether the quiet uncertainty affordance must render.
    event_id: str = ""
    source: str = ""
    confidence: str = ""
    start_time: str = ""
    uncertainty_marker: bool = False


@dataclass(frozen=True)
class CarouselDraft:
    """A complete, renderable carousel proposal awaiting human custody."""

    series_key: str
    surface: str
    tier: str
    timeframe: str
    # Brand/render inputs carried ON the draft (r5) so the release gate can
    # RE-RENDER the whole draft from canonical rows and compare hashes.
    city: str
    handle: str
    listicle_noun: str
    short_link_base: str
    # The series' domain claim (r9): carried on the draft so the release
    # gate re-derives domain membership for tier series, not just scenarios.
    domain_ids: tuple[str, ...]
    author: str
    assignment: dict[str, str]
    slides: tuple[Slide, ...]
    caption: str
    hashtags: tuple[str, ...]
    short_link: str
    post_slot: str
    # The machine-facing GEO/SEO bundle (JSON-LD, OG, alt text, llms.txt
    # block) rides INSIDE the draft (r4): it is covered by content_hash, so
    # the approval binds it and the release gate re-checks it — discovery
    # artifacts can never drift from what the human approved.
    discovery: dict = field(default_factory=dict)


def content_hash(draft: CarouselDraft) -> str:
    """Canonical SHA-256 over the draft's full content. Approvals bind to
    this; any post-approval edit changes the hash and voids the approval."""
    payload = json.dumps(asdict(draft), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def all_draft_text(draft: CarouselDraft) -> list[str]:
    """Every COPY surface the draft would publish — the banned-claim rescan
    set (evaluator r1, extended r4 to the discovery bundle's copy surfaces:
    OG values and alt texts). The llms.txt block and JSON-LD are DATA
    surfaces excluded here by design — they legitimately state confidence
    labels ("confidence: confirmed") as trust display, and their facts are
    verified against the canonical store at release instead."""
    texts: list[str] = []
    for slide in draft.slides:
        texts.append(slide.headline)
        texts.extend(slide.overlay_lines)
        texts.append(slide.alt_text)
    texts.append(draft.caption)
    texts.extend(draft.hashtags)
    texts.append(draft.short_link)
    discovery = draft.discovery or {}
    texts.extend(str(v) for v in discovery.get("og_tags", {}).values())
    texts.extend(discovery.get("alt_texts", []))
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
    # One shared normalizer for every price surface (#67 r2/r3): "abc",
    # "NaN"/"Infinity", and negatives refuse with the trust-error shape,
    # never a raw float()/comparison exception.
    normalize_price(event.get("price_min"), "price_min", event["event_id"])
    descriptor = event.get("foundry_descriptor")
    if descriptor is not None:
        if not isinstance(descriptor, dict) or not descriptor.get("text") or not descriptor.get("provenance"):
            raise CarouselTrustError(
                f"foundry_descriptor on {event['event_id']} lacks text/provenance — "
                "descriptor copy must carry Descriptor Foundry provenance"
            )


def _parse_when(value: str, label: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise CarouselTrustError(f"unparseable {label} timestamp {value!r}") from exc


def within_timeframe(start_time: str, reference_time: str, timeframe: str) -> bool:
    """Truthful-window check at TIMESTAMP precision (founder directive
    2026-07-24): only events that have NOT yet started at reference_time
    qualify — a 6pm carousel never includes a 5:30pm start. On top of the
    future-only floor, the event must fall inside the claimed window:
    Today = rest of today; Tonight = rest of today from 5pm; This weekend
    = the current-or-next Fri-Sun block."""
    if timeframe not in TIMEFRAMES:
        raise CarouselTrustError(f"unknown timeframe {timeframe!r}")
    start = _parse_when(start_time, "event start")
    ref = _parse_when(reference_time, "reference")
    if (start.tzinfo is None) != (ref.tzinfo is None):
        raise CarouselTrustError(
            "timezone-aware/naive mismatch between event start and reference "
            f"({start_time!r} vs {reference_time!r}) — refusing to compare"
        )
    if start.tzinfo is not None:
        # Calendar windows are judged in the EVENT'S OWN timezone (r12
        # nit): the release gate's UTC clock is a different calendar date
        # after 19:00 CDT, which would falsely refuse an Austin "Tonight"
        # release. The instant comparison below is timezone-correct either
        # way; the .date()/.hour window checks need the market-local view.
        ref = ref.astimezone(start.tzinfo)
    if start <= ref:
        # Already started — including starting at this exact instant (r2:
        # "to happen" means strictly ahead): never shown, in any window.
        return False
    if timeframe == "today":
        return start.date() == ref.date()
    if timeframe == "tonight":
        return start.date() == ref.date() and start.hour >= TONIGHT_EARLIEST_HOUR
    # this_weekend: the Fri-Sun block containing ref (if ref is already in
    # one) or the next one ahead.
    days_to_friday = (4 - ref.weekday()) % 7 if ref.weekday() < 4 else 0
    weekend_start = (ref + timedelta(days=days_to_friday)).date()
    weekend_end = weekend_start + timedelta(days=6 - weekend_start.weekday())
    return weekend_start <= start.date() <= weekend_end


def select_featurable(events: list[dict]) -> list[dict]:
    """Trust selection (spec §1): confirmed first, then likely; scheduled
    only; the rest are never featured. Unknown states fail loud — a new
    state must be classified deliberately, never defaulted into marketing.
    Duplicate event ids fail loud too (r6): a listicle promise counts
    DISTINCT events, and a duplicated canonical row is an upstream defect."""
    seen: set[str] = set()
    for event in events:
        _check_event(event)
        if event["event_id"] in seen:
            raise CarouselTrustError(
                f"duplicate event id {event['event_id']!r} in the lineup — "
                "a listicle counts distinct events, never repeats"
            )
        seen.add(event["event_id"])
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


# Word-boundary matching (r4 nit): "Confirmedly Great" the band name passes;
# the claim word "confirmed" never does. Public: the release gate uses the
# SAME regex (r5 nit — generation and custody must agree).
BANNED_CLAIM_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in BANNED_CLAIM_PHRASES) + r")\b",
    re.IGNORECASE,
)


def _scan_banned(text: str, context: str) -> None:
    match = BANNED_CLAIM_RE.search(text)
    if match:
        raise CarouselTrustError(
            f"banned claim phrase {match.group(0)!r} in {context}: {text!r}"
        )


def normalize_price(raw, field: str, owner: str) -> Decimal | None:
    """THE price normalizer (#67 r3): every price surface — event
    checking, label rendering, the scenario filter — resolves raw price
    data through this ONE path, so the refusal contract cannot drift
    between surfaces. None passes through; unparseable, non-finite
    (Decimal happily parses "NaN"/"Infinity"), and negative values all
    refuse with the trust-error shape."""
    if raw is None:
        return None
    try:
        value = Decimal(str(raw))
    except InvalidOperation as exc:
        raise CarouselTrustError(f"unparseable {field} {raw!r} on {owner}") from exc
    if not value.is_finite():
        raise CarouselTrustError(f"non-finite {field} {raw!r} on {owner}")
    if value < 0:
        raise CarouselTrustError(
            f"negative {field} {raw!r} on {owner} — an impossible public "
            "price claim is a data defect, never copy"
        )
    return value


def _price_label(price) -> str:
    """Exact price display (r5, hardened r6 via Decimal): $19.99 is
    $19.99, never $19 — a public price claim is a fact, and facts are
    verbatim; Decimal avoids float representation surprises."""
    value = normalize_price(price, "price", "label render")
    if value is None:
        raise CarouselTrustError("price label requires a price, got None")
    if value != value.quantize(Decimal("0.01")):
        raise CarouselTrustError(
            f"price {price!r} has sub-cent precision — a public price claim "
            "is never rounded; fix the data"
        )
    if value == value.to_integral_value():
        return f"${int(value)}"
    return f"${value.quantize(Decimal('0.01'))}"


def _hook_headline(hook_type: str, events: list[dict], config: CarouselConfig) -> str:
    """The founder's listicle canon (2026-07-24): every hook reads
    '<N> <blank> to experience <Today | Tonight | This weekend>'. N is the
    ACTUAL number of event slides (the promise is kept exactly); the hook
    factor varies only the <blank>, and every blank is FACT-DERIVED (r11):
    the curated series noun (config, founder/scenario-ratified) or a price
    computed from the real lineup — never an AI-authored qualitative claim
    ("big rooms" for small venues is exactly the class this forbids)."""
    n = len(events)
    phrase = str(TIMEFRAMES[config.timeframe]["phrase"])
    priced = [e["price_min"] for e in events if e.get("price_min") is not None]
    if hook_type == "edition_anchor":
        blank = config.listicle_noun
    elif hook_type == "number_promise":
        if priced and len(priced) == n:
            # Honest by construction (r5): "from $X" claims the exact
            # MINIMUM, never an "under" ceiling a $X ticket would falsify,
            # and the label is exact — no cent truncation. The noun is the
            # series' own (r11): "family adventures" never becomes "nights".
            low = min(priced)
            if max(priced) == 0:
                # A noun that already says "free" (the free_tonight
                # scenario's "free nights") is not doubled.
                noun = config.listicle_noun
                blank = noun if noun.lower().startswith("free") else f"free {noun}"
            else:
                blank = f"{config.listicle_noun} from {_price_label(low)}"
        else:
            # An honest price promise needs every featured event priced;
            # otherwise fall back to the plain noun.
            blank = config.listicle_noun
    else:
        raise CarouselTrustError(f"unknown hook_type {hook_type!r}")
    headline = f"{n} {blank} to experience {phrase}"
    if len(headline.split()) > HOOK_HEADLINE_MAX_WORDS:
        # A two-word noun + "from $X" + "This weekend" can overflow the
        # 8-word recognition cap; the honest degrade is the plain noun
        # (always <= 7 words: N + <=2 noun + "to experience" + <=2 phrase),
        # never truncating the price fact.
        headline = f"{n} {config.listicle_noun} to experience {phrase}"
    return headline


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
    Beyond a same-day window, the date is part of the fact — time alone
    would imply today (the r1 truthful-framing rule)."""
    clock = event["start_time"][11:16] if len(event["start_time"]) >= 16 else ""
    if timeframe in ("today", "tonight"):
        when = clock
    else:
        event_date = _parse_when(event["start_time"], "event start").date()
        when = f"{event_date.strftime('%b %d')} · {clock}" if clock else event_date.strftime("%b %d")
    lines = [event["name"], f"{event['venue_name']} · {when}"]
    if event.get("price_min") is not None:
        price = Decimal(str(event["price_min"]))  # "0" the string is free too
        lines.append("Free" if price == 0 else f"From {_price_label(price)}")
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
    # Every caption style is assembled from canonical facts and the curated
    # series noun (r11): no venue/mood characterization the data does not
    # carry — "a room about to go off" was exactly the forbidden class.
    first = events[0]
    lead = {
        "short_punch": f"{phrase} in {config.city}: {n} {config.listicle_noun}.",
        "mini_story": (
            f"First up {phrase.lower()}: {first['name']} at "
            f"{first['venue_name']}. {n} {config.listicle_noun} in this edition."
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
    reference_time: str,
) -> CarouselDraft:
    """Assemble one draft: hook slide, EXACTLY 5 or 7 event slides (the
    founder's listicle canon — the sampled size falls back 7->5 when supply
    is short, and below 5 there is no post: a listicle promise is never
    padded), CTA close — under the surface's hard slide bounds, the word
    caps, and the series' truthful FUTURE-ONLY time window (reference_time,
    a full timestamp, anchors it; passed in explicitly so cycles are
    reproducible). Raises CarouselTrustError on any trust or format
    violation, NoFeaturableEvents when the window is honestly too thin —
    a draft that cannot be built honestly is not built at all."""
    config.validate()
    validate_assignment(assignment)
    featurable = [
        e
        for e in select_featurable(events)
        if within_timeframe(e["start_time"], reference_time, config.timeframe)
    ]
    sampled_size = int(assignment["listicle_size"])
    if sampled_size not in LISTICLE_SIZES:
        raise CarouselTrustError(f"listicle_size {sampled_size} not in {LISTICLE_SIZES}")
    if len(featurable) >= sampled_size:
        listicle_n = sampled_size
    elif len(featurable) >= min(LISTICLE_SIZES):
        listicle_n = min(LISTICLE_SIZES)
    else:
        raise NoFeaturableEvents(
            f"only {len(featurable)} featurable events inside the "
            f"{config.timeframe} window from {reference_time} — a listicle "
            f"promises at least {min(LISTICLE_SIZES)}, and the promise is never padded"
        )

    return render_carousel(featurable[:listicle_n], config, assignment)


def render_carousel(
    featured: list[dict],
    config: CarouselConfig,
    assignment: dict[str, str],
) -> CarouselDraft:
    """Pure deterministic render of an ALREADY-SELECTED lineup. Split out
    (r5) so the release gate can re-render the draft from canonical rows
    and compare content hashes — total fact verification in one check.
    Validates config + assignment ITSELF (r7) and runs the FULL event
    trust contract on every row it renders (r8; completed r13) — required
    fields, origin, known states, FEATURABILITY (confirmed/likely and
    scheduled ONLY — a disputed or cancelled row refuses here, not just at
    selection), descriptor provenance, non-negative prices, distinct ids,
    domain membership, and the exact 5/7 listicle canon — so this render
    path fails closed independently of whether build_carousel ever ran."""
    config.validate()
    validate_assignment(assignment)
    if len(featured) not in LISTICLE_SIZES:
        raise CarouselTrustError(
            f"render lineup of {len(featured)} events is not the listicle "
            f"canon {sorted(LISTICLE_SIZES)} — the promise is exact, and this "
            "renderer never builds a non-canonical deck"
        )
    seen: set[str] = set()
    for event in featured:
        _check_event(event)
        if event["confidence"] not in FEATURABLE_CONFIDENCE:
            raise CarouselTrustError(
                f"event {event['event_id']} confidence {event['confidence']!r} "
                "is not featurable — marketing never amplifies what the gate "
                "has not settled"
            )
        if event["event_status"] not in FEATURABLE_EVENT_STATUS:
            raise CarouselTrustError(
                f"event {event['event_id']} event_status "
                f"{event['event_status']!r} is not featurable — only scheduled "
                "events are ever rendered"
            )
        if event["event_id"] in seen:
            raise CarouselTrustError(
                f"duplicate event id {event['event_id']!r} in the render lineup"
            )
        seen.add(event["event_id"])
        if config.domain_ids and event["domain_id"] not in config.domain_ids:
            raise CarouselTrustError(
                f"event {event['event_id']} domain {event['domain_id']!r} is "
                f"outside this series' domains {config.domain_ids} — a series "
                "claim covers only its own domains"
            )
        if not event.get("image_url"):
            raise CarouselTrustError(
                f"event {event['event_id']} has no image — the spec's "
                "image-mandatory rule (perception physics) fails loud, and an "
                "imageless event rides the product feed instead"
            )
    constraints = SURFACE_CONSTRAINTS[config.surface]

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
                start_time=event["start_time"],
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
        city=config.city,
        handle=config.handle,
        listicle_noun=config.listicle_noun,
        short_link_base=config.short_link_base,
        domain_ids=tuple(config.domain_ids),
        author=AGENT_AUTHOR,
        assignment=dict(assignment),
        slides=tuple(slides),
        caption=caption,
        hashtags=hashtags_for(config.city, featured),
        short_link=short_link,
        post_slot=assignment["post_slot"],
    )
    # Attach the machine-discovery bundle INSIDE the draft so the content
    # hash (and therefore any approval) covers it (r4).
    draft = dataclasses.replace(
        draft, discovery=discovery_bundle(draft, featured, config.city)
    )
    for text in all_draft_text(draft):
        _scan_banned(text, "draft content")
    return draft
