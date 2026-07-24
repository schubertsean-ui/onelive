"""Format physics + the creative factor space for Meta carousels.

Greppable summary: the perception-science constraints (spec §2 — hook slide
word cap, one idea per slide, per-surface slide bounds, story-reshare safe
margins) and the factored creative design space the bandit learns over
(spec §6). Everything here is a CONSTRAINT the generator enforces, not a
style suggestion. Trust rules: FEATURABLE_CONFIDENCE / NEVER_FEATURED and
the banned-claim phrase list are re-checked by the publish gate, so a
generator bug cannot relax them on the way out.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --- Trust selection (spec §1) -------------------------------------------------
# 4-state confidence canon: unverified | likely | confirmed | disputed.
# Marketing features only what the gate has settled; `likely` requires the
# quiet uncertainty affordance (design brief trust display rules).
FEATURABLE_CONFIDENCE = ("confirmed", "likely")
NEVER_FEATURED = ("unverified", "disputed")
KNOWN_CONFIDENCE = FEATURABLE_CONFIDENCE + NEVER_FEATURED

# Design brief: NO "confirmed"-style badge language anywhere, and no
# manufactured-scarcity claims without a sourced signal (spec §3 white-hat
# line). The generator never emits these; the gate refuses them if a
# template regression ever tries.
BANNED_CLAIM_PHRASES = (
    "confirmed",
    "verified",
    "guaranteed",
    "selling out",
    "sold out soon",
    "last chance",
    "almost gone",
)

# --- Per-surface format constraints (spec §2) ----------------------------------


@dataclass(frozen=True)
class SurfaceConstraints:
    """Hard mechanical limits for one Meta posting surface."""

    min_slides: int
    max_slides: int
    aspect_ratio: str
    canvas_px: tuple[int, int]
    # Story-reshare crops the feed canvas; content inside this margin
    # survives the crop, which is what makes resharing cheap (spec §7).
    reshare_safe_margin_px: int


SURFACE_CONSTRAINTS: dict[str, SurfaceConstraints] = {
    "instagram_feed": SurfaceConstraints(
        min_slides=2,
        max_slides=20,
        aspect_ratio="4:5",
        canvas_px=(1080, 1350),
        reshare_safe_margin_px=250,
    ),
    "facebook_page": SurfaceConstraints(
        min_slides=2,
        max_slides=10,
        aspect_ratio="1:1",
        canvas_px=(1080, 1080),
        reshare_safe_margin_px=120,
    ),
}

# Recognition-not-reading caps (spec §2: gist in ~13ms, headline <= 8 words).
HOOK_HEADLINE_MAX_WORDS = 8
SLIDE_OVERLAY_MAX_WORDS = 12

# --- The factored creative design space (spec §6) ------------------------------
# Each factor learns independently in the bandit; levels are closed sets so
# the whole space is enumerable and auditable. Negative-valence emotion
# registers deliberately do not exist (spec §3).
FACTORS: dict[str, tuple[str, ...]] = {
    "hook_type": (
        "curiosity_gap",
        "number_promise",
        "awe",
        "humor",
        "social_proof",
        "tonight_anchor",
    ),
    "emotion_register": (
        "excitement",
        "awe",
        "amusement",
        "belonging",
        "anticipation",
    ),
    "slide_count_band": ("5-7", "8-10", "11-14"),
    "caption_style": ("short_punch", "mini_story", "list"),
    "cta_type": (
        "save_this",
        "send_to_friend",
        "tag_who",
        "follow_for_daily",
        "link_in_bio",
    ),
    "post_slot": ("morning", "lunch", "late_afternoon", "evening"),
    # `video` is a live level so learning extends to Reels-style media the
    # moment asset supply exists (spec §2); the generator renders it as a
    # video-slot slide spec, it does not fabricate footage.
    "media_type": ("image", "collage", "video"),
}

SLIDE_COUNT_BANDS: dict[str, tuple[int, int]] = {
    "5-7": (5, 7),
    "8-10": (8, 10),
    "11-14": (11, 14),
}


@dataclass(frozen=True)
class CarouselConfig:
    """One carousel series' fixed identity (the learned parts live in the
    bandit assignment, not here)."""

    surface: str
    series_key: str
    city: str
    handle: str
    short_link_base: str
    domain_ids: tuple[str, ...] = field(default_factory=tuple)
    tier: str = "T1"

    def validate(self) -> None:
        if self.surface not in SURFACE_CONSTRAINTS:
            raise ValueError(
                f"unknown surface {self.surface!r}; known: "
                f"{sorted(SURFACE_CONSTRAINTS)}"
            )
        if self.tier not in ("T1", "T2", "T3"):
            raise ValueError(f"unknown tier {self.tier!r}")
        if not self.series_key:
            raise ValueError("series_key must be non-empty")
        if not self.city or not self.handle:
            raise ValueError("city and handle must be non-empty")
        if not self.short_link_base.startswith("https://"):
            raise ValueError("short_link_base must be an https URL")


def validate_assignment(assignment: dict[str, str]) -> None:
    """Fail loud on any factor/level outside the closed design space —
    a typo must never silently become an untracked creative arm."""
    for factor, level in assignment.items():
        if factor not in FACTORS:
            raise ValueError(f"unknown factor {factor!r}")
        if level not in FACTORS[factor]:
            raise ValueError(f"unknown level {level!r} for factor {factor!r}")
    missing = set(FACTORS) - set(assignment)
    if missing:
        raise ValueError(f"assignment missing factors: {sorted(missing)}")
