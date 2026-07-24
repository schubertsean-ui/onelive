"""Publish custody: the ONLY path from a carousel draft to Meta (spec §1, §10).

Greppable summary: same physics as worker/promote.py's assert_promotable —
release_for_publish is the last authoritative guard before anything
outward-facing. Approvals are AUTHENTICATED (evaluator r1): approve()
requires the founder-held approval key (ONELIVE_APPROVAL_KEY —
founder-minted, never in the repo, never handed to agent sessions) and
signs the draft's SHA-256 content hash with HMAC-SHA256; release verifies
the signature, so an agent cannot forge an approval by typing a human
name. Release also re-checks every featured event's CURRENT confidence
AND event_status, and rescans the ENTIRE draft text surface (slides,
caption, hashtags, alt text, link) for banned claim language — the final
guard trusts nothing the generator did earlier. Approval-less release
exists only through the founder's authenticated autonomy record (L0
default = never; unverifiable record = refuse everything). The autonomous
loop (agent_loop.py) is forbidden to import this module — enforced by
tests/test_social_carousel.py's import guard. There is deliberately NO
Graph API client in this codebase: posting infrastructure is built only
when the founder mints Meta credentials and ratifies the posture [R-026]
— a PublishRelease is the complete, auditable hand-off record until then.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass

from social.carousel.autonomy import AutonomyPolicy, load_policy
from social.carousel.config import (
    BANNED_CLAIM_PHRASES,
    FEATURABLE_CONFIDENCE,
    FEATURABLE_EVENT_STATUS,
)
from social.carousel.generator import (
    CarouselDraft,
    all_draft_text,
    content_hash,
    within_timeframe,
)

APPROVAL_KEY_ENV = "ONELIVE_APPROVAL_KEY"

# Identity markers that can never approve, kept as defense-in-depth ON TOP
# of the signature requirement (the signature is the enforcement; this
# catches a mis-issued key being used under an agent identity). Matched as
# substrings of the lowered approver identity, fail-closed.
AI_IDENTITY_MARKERS = ("agent", "claude", "gpt", "gemini", "bot", "onelive-carousel")


@dataclass(frozen=True)
class Approval:
    """A human's signed sign-off on one exact draft (bound by content hash)."""

    draft_hash: str
    approved_by: str
    approved_at: str  # ISO 8601, supplied by the approving surface
    signature: str


@dataclass(frozen=True)
class PublishRelease:
    """Proof that the gate released this exact draft for posting."""

    draft_hash: str
    surface: str
    series_key: str
    released_by: str  # approver identity, or "autonomy:<level>"


def _resolve_key(explicit: str | bytes | None) -> bytes:
    key = explicit if explicit is not None else os.environ.get(APPROVAL_KEY_ENV)
    if not key:
        raise ValueError(
            f"no approval key available ({APPROVAL_KEY_ENV} unset) — approvals "
            "cannot be signed or verified, refusing (the key is founder-minted "
            "and never present in agent sessions)"
        )
    return key.encode("utf-8") if isinstance(key, str) else key


def _approval_message(draft_hash: str, approved_by: str, approved_at: str) -> bytes:
    return "|".join((draft_hash, approved_by, approved_at)).encode("utf-8")


def approve(
    draft: CarouselDraft,
    approved_by: str,
    approved_at: str,
    *,
    signing_key: str | bytes | None = None,
) -> Approval:
    """Record an authenticated human approval: the approving surface (which
    holds the founder-minted key — agent sessions do not) signs the draft
    hash. Refuses empty or AI-marked identities and refuses to proceed
    without a key — a name string alone approves nothing."""
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
    key = _resolve_key(signing_key)
    draft_hash = content_hash(draft)
    signature = hmac.new(
        key, _approval_message(draft_hash, identity, approved_at), hashlib.sha256
    ).hexdigest()
    return Approval(
        draft_hash=draft_hash,
        approved_by=identity,
        approved_at=approved_at,
        signature=signature,
    )


def _recheck_trust(
    draft: CarouselDraft, current_states: dict[str, dict], reference_time: str
) -> None:
    """The state that was true at generation must STILL be true at release:
    an event that went disputed OR got cancelled/moved OR has already
    started since the draft was built blocks the post (founder directive
    2026-07-24: only ever content that is yet to happen — the release gate
    re-checks with ITS clock, not the generator's). current_states:
    event_id -> {"confidence": ..., "event_status": ...}, freshly read from
    the canonical store; reference_time: the release moment, full ISO
    timestamp."""
    for slide in draft.slides:
        if slide.kind != "event":
            continue
        if not slide.start_time or not within_timeframe(
            slide.start_time, reference_time, draft.timeframe
        ):
            raise ValueError(
                f"release refused: {slide.event_id} (start {slide.start_time!r}) "
                f"is not strictly ahead within the {draft.timeframe} window at "
                f"{reference_time} — carousels never show what has already started"
            )
        current = current_states.get(slide.event_id)
        if current is None:
            raise ValueError(
                f"release refused: no current state for {slide.event_id} — "
                "cannot verify the event is still featurable"
            )
        confidence = current.get("confidence")
        status = current.get("event_status")
        if confidence not in FEATURABLE_CONFIDENCE:
            raise ValueError(
                f"release refused: {slide.event_id} is now {confidence!r} — "
                "marketing never amplifies what the gate has not settled"
            )
        if status not in FEATURABLE_EVENT_STATUS:
            raise ValueError(
                f"release refused: {slide.event_id} event_status is now {status!r} — "
                "only scheduled events may be featured"
            )
        if confidence == "likely" and not slide.uncertainty_marker:
            raise ValueError(
                f"release refused: {slide.event_id} is 'likely' but its slide "
                "lacks the uncertainty affordance"
            )
    # Full-content rescan (evaluator r1): the final guard scans EVERY text
    # surface of the draft itself — it never assumes the generator ran.
    for text in all_draft_text(draft):
        lowered = text.lower()
        for phrase in BANNED_CLAIM_PHRASES:
            if phrase in lowered:
                raise ValueError(
                    f"release refused: banned claim phrase {phrase!r} in draft content"
                )


def release_for_publish(
    draft: CarouselDraft,
    current_states: dict[str, dict],
    approval: Approval | None = None,
    policy: AutonomyPolicy | None = None,
    *,
    reference_time: str,
    verification_key: str | bytes | None = None,
) -> PublishRelease:
    """The publish decision. Exactly two lawful paths:

    1. an authenticated human Approval whose signature verifies under the
       founder-held key AND whose hash matches this exact draft, or
    2. the founder's authenticated autonomy record covering (surface, tier).

    Everything else refuses; either path first passes the trust re-check
    (current confidence + status, future-only at reference_time, full-text
    rescan). A caller passing policy=None gets the record loaded and
    signature-verified from disk; AutonomyRecordError propagates — a broken
    or bogus ratification refuses everything, loudly.
    """
    _recheck_trust(draft, current_states, reference_time)
    draft_hash = content_hash(draft)

    if approval is not None:
        if approval.draft_hash != draft_hash:
            raise ValueError(
                "release refused: approval hash does not match this draft — "
                "the draft changed after approval, so the approval is void"
            )
        key = _resolve_key(verification_key)
        expected = hmac.new(
            key,
            _approval_message(approval.draft_hash, approval.approved_by, approval.approved_at),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, approval.signature):
            raise ValueError(
                "release refused: approval signature does not verify under the "
                "approval key — a name string alone approves nothing"
            )
        return PublishRelease(
            draft_hash=draft_hash,
            surface=draft.surface,
            series_key=draft.series_key,
            released_by=approval.approved_by,
        )

    active_policy = (
        policy if policy is not None else load_policy(verification_key=verification_key)
    )
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
