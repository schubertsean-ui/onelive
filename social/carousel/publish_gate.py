"""Publish custody: the ONLY path from a carousel draft to Meta (spec §1, §10).

Greppable summary: same physics as worker/promote.py's assert_promotable —
release_for_publish is the last authoritative guard before anything
outward-facing. approve() binds a HUMAN reviewer to the draft's SHA-256
content hash (AI identities refused, fail-closed); release re-computes the
hash, re-checks every featured event's CURRENT trust state, re-scans
banned claim language, and consults the founder's autonomy record for
approval-less release (L0 default = never; malformed record = refuse
everything). The autonomous loop (agent_loop.py) is forbidden to import
this module — enforced by tests/test_social_carousel.py's import guard.
Live posting itself is stubbed pending founder-minted Meta credentials
[R-026].
"""
from __future__ import annotations

from dataclasses import dataclass

from social.carousel.autonomy import AutonomyPolicy, load_policy
from social.carousel.config import BANNED_CLAIM_PHRASES, FEATURABLE_CONFIDENCE
from social.carousel.generator import CarouselDraft, content_hash

# Identity markers that can never approve: the generator must not grade —
# or greenlight — its own homework. Matched as substrings of the lowered
# approver identity, fail-closed.
AI_IDENTITY_MARKERS = ("agent", "claude", "gpt", "gemini", "bot", "onelive-carousel")


@dataclass(frozen=True)
class Approval:
    """A human's sign-off on one exact draft (bound by content hash)."""

    draft_hash: str
    approved_by: str
    approved_at: str  # ISO 8601, supplied by the approving surface


@dataclass(frozen=True)
class PublishRelease:
    """Proof that the gate released this exact draft for posting."""

    draft_hash: str
    surface: str
    series_key: str
    released_by: str  # approver identity, or "autonomy:<level>"


def approve(draft: CarouselDraft, approved_by: str, approved_at: str) -> Approval:
    """Record a human approval. Refuses empty or AI-marked identities."""
    identity = (approved_by or "").strip()
    if not identity:
        raise ValueError("approval requires a named human approver")
    lowered = identity.lower()
    for marker in AI_IDENTITY_MARKERS:
        if marker in lowered:
            raise ValueError(
                f"approver {approved_by!r} matches AI identity marker {marker!r} — "
                "AI never publishes, so AI never approves"
            )
    if not approved_at:
        raise ValueError("approval requires a timestamp from the approving surface")
    return Approval(
        draft_hash=content_hash(draft),
        approved_by=identity,
        approved_at=approved_at,
    )


def _recheck_trust(draft: CarouselDraft, current_confidence: dict[str, str]) -> None:
    """The state that was true at generation must STILL be true at release:
    an event that went disputed since the draft was built blocks the post."""
    for slide in draft.slides:
        if slide.kind != "event":
            continue
        current = current_confidence.get(slide.event_id)
        if current is None:
            raise ValueError(
                f"release refused: no current confidence for {slide.event_id} — "
                "cannot verify the event is still featurable"
            )
        if current not in FEATURABLE_CONFIDENCE:
            raise ValueError(
                f"release refused: {slide.event_id} is now {current!r} — "
                "marketing never amplifies what the gate has not settled"
            )
        if current == "likely" and not slide.uncertainty_marker:
            raise ValueError(
                f"release refused: {slide.event_id} is 'likely' but its slide "
                "lacks the uncertainty affordance"
            )
        for text in (slide.headline, *slide.overlay_lines):
            lowered = text.lower()
            for phrase in BANNED_CLAIM_PHRASES:
                if phrase in lowered:
                    raise ValueError(
                        f"release refused: banned claim phrase {phrase!r} on "
                        f"slide for {slide.event_id}"
                    )


def release_for_publish(
    draft: CarouselDraft,
    current_confidence: dict[str, str],
    approval: Approval | None = None,
    policy: AutonomyPolicy | None = None,
) -> PublishRelease:
    """The publish decision. Exactly two lawful paths:

    1. A human Approval whose hash matches this exact draft, or
    2. the founder's ratified autonomy record covering (surface, tier).

    Everything else refuses. A caller passing policy=None gets the record
    loaded fresh from disk; a record that raises AutonomyRecordError
    propagates — a broken ratification refuses everything, loudly.
    """
    _recheck_trust(draft, current_confidence)
    draft_hash = content_hash(draft)

    if approval is not None:
        if approval.draft_hash != draft_hash:
            raise ValueError(
                "release refused: approval hash does not match this draft — "
                "the draft changed after approval, so the approval is void"
            )
        return PublishRelease(
            draft_hash=draft_hash,
            surface=draft.surface,
            series_key=draft.series_key,
            released_by=approval.approved_by,
        )

    active_policy = policy if policy is not None else load_policy()
    if active_policy.allows_auto_release(draft.surface, draft.tier):
        return PublishRelease(
            draft_hash=draft_hash,
            surface=draft.surface,
            series_key=draft.series_key,
            released_by=f"autonomy:{active_policy.level}",
        )
    raise ValueError(
        "release refused: no human approval and the autonomy record does not "
        f"cover ({draft.surface}, {draft.tier}) — default is L0, human in the loop"
    )


class MetaPublisher:
    """The Graph API boundary. Deliberately unimplemented: posting requires
    founder-minted Meta credentials and the ratified posting posture
    (credential minting + go-live are founder-crucial) [R-026]."""

    def post(self, release: PublishRelease) -> str:
        raise NotImplementedError(
            "Meta posting requires founder-minted Graph API credentials and "
            "the ratified posting posture — see spec §9 and RECORD.md R-026"
        )
