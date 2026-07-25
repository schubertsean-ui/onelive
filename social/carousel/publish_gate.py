"""Publish custody: the ONLY path from a carousel draft to Meta (spec §1, §10).

Greppable summary: same physics as worker/promote.py's assert_promotable —
release_for_publish is the last authoritative guard before anything
outward-facing. R3 CUSTODY SHAPE: the public API takes ONLY
(draft, current-state-free arguments) — no key material, no record paths,
no state dicts. The approval key comes EXCLUSIVELY from the deployment
environment (ONELIVE_APPROVAL_KEY — founder-minted, never in the repo,
never in agent-session env; absent = nothing signs or verifies, fail
closed). The autonomy record is read EXCLUSIVELY from its canonical
committed path and signature-verified. Current event trust state is read
EXCLUSIVELY through a module-registered canonical-store reader
(configure_state_reader — deployment wiring, once-only; none registered =
release refuses everything). The human-identity check runs at BOTH
approve() and release (a signed approval naming an AI identity still
refuses). The autonomous loop (agent_loop.py) is forbidden to import this
module — enforced by tests/test_social_carousel.py's import guard. There
is deliberately NO Graph API client in this codebase until R-026's
trigger fires. HMAC is symmetric — the asymmetric-signature upgrade is
recorded as R-028 for the same trigger.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from social.carousel.autonomy import load_policy
from social.carousel.config import (
    CarouselConfig,
    FEATURABLE_CONFIDENCE,
    FEATURABLE_EVENT_STATUS,
    LISTICLE_SIZES,
)
from social.carousel.generator import (
    BANNED_CLAIM_RE,
    CarouselDraft,
    CarouselTrustError,
    all_draft_text,
    content_hash,
    render_carousel,
    within_timeframe,
)
from social.carousel.scenarios import scenario_by_key, scenario_events

APPROVAL_KEY_ENV = "ONELIVE_APPROVAL_KEY"

# Identity markers that can never approve, enforced at approve() AND at
# release (r3: a caller-built Approval with a valid signature over an AI
# identity must still refuse). Matched as substrings of the lowered
# approver identity, fail-closed.
AI_IDENTITY_MARKERS = ("agent", "claude", "gpt", "gemini", "bot", "onelive-carousel")

# The canonical-store state reader: deployment wiring, registered ONCE at
# process startup by the surface that owns the DB read path (the ops
# console backend at R-026's trigger). event_ids -> {event_id: FULL canonical
# row (r4): confidence, event_status, name, venue_name, start_time, source,
# origin at minimum}. None = no reader = release refuses everything.
_STATE_READER: Callable[[list[str]], dict[str, dict]] | None = None


def configure_state_reader(reader: Callable[[list[str]], dict[str, dict]]) -> None:
    """Register the canonical-store reader. Once-only (fail-closed on
    re-registration): the reader is deployment configuration, not a
    per-call argument — a second registration in one process is a
    misconfiguration or an attempt to swap the truth source."""
    global _STATE_READER
    if _STATE_READER is not None:
        raise ValueError("state reader already configured — refusing to replace it")
    if not callable(reader):
        raise ValueError("state reader must be callable")
    _STATE_READER = reader


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


def _resolve_key() -> bytes:
    """The approval key comes from the deployment environment ONLY (r3:
    key material must never be a parameter of the custody API — the
    subject of authorization must not choose the key that verifies it)."""
    key = os.environ.get(APPROVAL_KEY_ENV)
    if not key:
        raise ValueError(
            f"no approval key available ({APPROVAL_KEY_ENV} unset) — approvals "
            "cannot be signed or verified, refusing (the key is founder-minted "
            "deployment config, never present in agent sessions)"
        )
    return key.encode("utf-8")


def _assert_human_identity(identity: str) -> str:
    identity = (identity or "").strip()
    if not identity:
        raise ValueError("approval requires a named human approver")
    lowered = identity.lower()
    for marker in AI_IDENTITY_MARKERS:
        if marker in lowered:
            raise ValueError(
                f"approver {identity!r} matches AI identity marker {marker!r} — "
                "AI never publishes, so AI never approves"
            )
    return identity


def _approval_message(draft_hash: str, approved_by: str, approved_at: str) -> bytes:
    return "|".join((draft_hash, approved_by, approved_at)).encode("utf-8")


def approve(draft: CarouselDraft, approved_by: str, approved_at: str) -> Approval:
    """Record an authenticated human approval: signs the draft hash under
    the environment-held founder key. Refuses empty or AI-marked
    identities and refuses without the key — a name string alone approves
    nothing, and there is no way to hand this function a key."""
    identity = _assert_human_identity(approved_by)
    try:
        datetime.fromisoformat(approved_at)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"approval timestamp {approved_at!r} is not a valid ISO 8601 moment"
        ) from exc
    key = _resolve_key()
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


def _recheck_trust(draft: CarouselDraft, reference_time: str) -> None:
    """The state AND FACTS that were true at generation must STILL be true
    at release, read from the CANONICAL STORE by the registered reader (r3:
    the final gate never trusts caller-supplied state; r4: nor does it
    trust that the generator was used at all — draft shape and every
    asserted fact are verified against canonical rows, fail closed)."""
    if _STATE_READER is None:
        raise ValueError(
            "release refused: no canonical state reader configured — the gate "
            "cannot verify current trust state, so nothing releases (register "
            "the reader at deployment; built at R-026's trigger)"
        )
    # Listicle shape (r4): exactly one hook first, one CTA last, and
    # exactly 5 or 7 event slides between them — a hand-built draft with
    # zero (or any other count of) event slides never releases.
    kinds = [s.kind for s in draft.slides]
    n_events = kinds.count("event")
    if (
        not kinds
        or kinds[0] != "hook"
        or kinds[-1] != "cta"
        or kinds.count("hook") != 1
        or kinds.count("cta") != 1
        or kinds[1:-1] != ["event"] * n_events
        or n_events not in LISTICLE_SIZES
    ):
        raise ValueError(
            f"release refused: draft shape {kinds} is not the listicle canon "
            f"(hook, {sorted(LISTICLE_SIZES)} event slides, cta)"
        )
    if not draft.slides[0].headline.startswith(f"{n_events} "):
        raise ValueError(
            "release refused: hook headline does not state the actual event "
            "count — the listicle promise must be exact"
        )
    event_ids = [s.event_id for s in draft.slides if s.kind == "event"]
    if len(set(event_ids)) != len(event_ids):
        raise ValueError(
            "release refused: duplicate event ids in the deck — the listicle "
            "promise counts distinct events, never repeats"
        )
    current_states = _STATE_READER(event_ids)
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
                f"release refused: canonical store returned no state for "
                f"{slide.event_id} — cannot verify the event is still featurable"
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
        if current.get("origin") != "canonical_event":
            raise ValueError(
                f"release refused: {slide.event_id} is not a canonical "
                "published row — candidate/pipeline rows are never amplified"
            )
    # TOTAL fact verification (r5): re-render the ENTIRE draft — every
    # slide line, alt text, caption, hashtag, link, and the complete
    # discovery bundle — from the CANONICAL rows through the same
    # deterministic renderer, and require hash identity. One check, no
    # per-field gaps: anything fabricated, truncated, dropped, or drifted
    # (including discovery={}) produces a different hash and refuses.
    rows_in_order = [current_states[eid] for eid in event_ids]
    # Scenario semantics re-applied at custody (r8): a draft carrying a
    # scenario series claim ("free nights", "date nights") releases only
    # if every canonical row still satisfies that scenario's predicate —
    # the meaning of the claim is re-derived, not trusted.
    if draft.series_key.startswith("scenario_"):
        try:
            scenario = scenario_by_key(draft.series_key.removeprefix("scenario_"))
        except ValueError as exc:
            raise ValueError(f"release refused: {exc}") from exc
        passing = {e["event_id"] for e in scenario_events(rows_in_order, scenario)}
        failing = [eid for eid in event_ids if eid not in passing]
        if failing:
            raise ValueError(
                f"release refused: events {failing} no longer satisfy the "
                f"{scenario.key!r} scenario predicate — the claim would be false"
            )
    config = CarouselConfig(
        surface=draft.surface,
        series_key=draft.series_key,
        city=draft.city,
        handle=draft.handle,
        short_link_base=draft.short_link_base,
        tier=draft.tier,
        timeframe=draft.timeframe,
        listicle_noun=draft.listicle_noun,
    )
    try:
        rebuilt = render_carousel(rows_in_order, config, dict(draft.assignment))
    except CarouselTrustError as exc:
        raise ValueError(
            f"release refused: canonical rows do not render a lawful carousel ({exc})"
        ) from exc
    if content_hash(rebuilt) != content_hash(draft):
        raise ValueError(
            "release refused: the draft does not re-derive byte-identically "
            "from the canonical store — no fabrication, no drift, no missing "
            "discovery artifacts"
        )
    # Belt on top of the hash (same regex as generation — r5 nit): scan the
    # copy surfaces for banned claim language.
    for text in all_draft_text(draft):
        match = BANNED_CLAIM_RE.search(text)
        if match:
            raise ValueError(
                f"release refused: banned claim phrase {match.group(0)!r} in draft content"
            )


def release_for_publish(
    draft: CarouselDraft,
    approval: Approval | None = None,
    *,
    reference_time: str,
) -> PublishRelease:
    """The publish decision. Exactly two lawful paths:

    1. a human Approval whose signature verifies under the ENVIRONMENT-held
       founder key, whose hash matches this exact draft, AND whose approver
       identity passes the human check again HERE, or
    2. the founder's signed autonomy record, read from its canonical
       committed path only, signature-verified under the same env key.

    Everything else refuses. There are deliberately NO parameters for key
    material, record paths, or trust state (r3): the key is deployment
    env, the record location is fixed, and current state comes from the
    registered canonical reader — absent any of them, nothing releases.
    """
    _recheck_trust(draft, reference_time)
    draft_hash = content_hash(draft)

    if approval is not None:
        _assert_human_identity(approval.approved_by)
        try:
            datetime.fromisoformat(approval.approved_at)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"release refused: approval timestamp {approval.approved_at!r} "
                "is not a valid ISO 8601 moment"
            ) from exc
        if approval.draft_hash != draft_hash:
            raise ValueError(
                "release refused: approval hash does not match this draft — "
                "the draft changed after approval, so the approval is void"
            )
        key = _resolve_key()
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

    active_policy = load_policy()
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
