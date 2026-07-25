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
release refuses everything). Release-time "now" is the GATE'S OWN clock
(r11: _utcnow(), never a parameter), and the autonomy grant's
max_releases_per_day is counted against a module-registered release
journal (configure_release_journal, once-only; none registered = the
autonomy path refuses). The human-identity check runs at BOTH
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
from datetime import date, datetime, timezone
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
    renderer_fingerprint,
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


def _utcnow() -> datetime:
    """The gate's OWN clock (r11): release-time "now" is never a caller
    argument — the subject of a release must not choose the clock that
    decides whether the release is lawful. A caller passing an earlier
    timestamp could release carousels of already-started events; this
    module attribute is process infrastructure (tests monkeypatch it the
    same way they patch env), not an API surface."""
    return datetime.now(timezone.utc)


def _release_moment() -> datetime:
    now = _utcnow()
    if now.tzinfo is None:
        raise ValueError(
            "release refused: the gate clock returned a naive datetime — "
            "a custody moment must be timezone-aware"
        )
    return now


class InMemoryReleaseJournal:
    """Reference release journal for tests and single-process dev runs.
    Production wires a DURABLE journal (the ops-console store, R-026's
    trigger) through configure_release_journal — the interface is
    count_on(date) -> int and record(release, moment)."""

    def __init__(self) -> None:
        self._by_day: dict[date, list[PublishRelease]] = {}

    def count_on(self, day: date) -> int:
        return len(self._by_day.get(day, []))

    def record(self, release: "PublishRelease", moment: datetime) -> None:
        self._by_day.setdefault(moment.date(), []).append(release)


# The release journal: deployment wiring, registered ONCE like the state
# reader. The autonomy path REQUIRES it (r11): a signed grant's
# max_releases_per_day is enforced HERE, mechanically — no journal means
# the ceiling cannot be counted, so nothing auto-releases (fail closed).
_RELEASE_JOURNAL = None


def configure_release_journal(journal) -> None:
    """Register the durable release journal. Once-only, same physics as
    configure_state_reader: a second registration is a misconfiguration
    or an attempt to reset the cadence count."""
    global _RELEASE_JOURNAL
    if _RELEASE_JOURNAL is not None:
        raise ValueError("release journal already configured — refusing to replace it")
    if not callable(getattr(journal, "count_on", None)) or not callable(
        getattr(journal, "record", None)
    ):
        raise ValueError("release journal must expose count_on(date) and record(release, moment)")
    _RELEASE_JOURNAL = journal


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


def _assert_iso_moment(value: str, context: str) -> None:
    """A custody timestamp is a timezone-aware full moment (r9 nit):
    date-only or naive values fail closed."""
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} {value!r} is not a valid ISO 8601 moment") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{context} {value!r} is not timezone-aware — not a moment")


def _approval_message(draft_hash: str, approved_by: str, approved_at: str) -> bytes:
    return "|".join((draft_hash, approved_by, approved_at)).encode("utf-8")


def approve(draft: CarouselDraft, approved_by: str, approved_at: str) -> Approval:
    """Record an authenticated human approval: signs the draft hash under
    the environment-held founder key. Refuses empty or AI-marked
    identities and refuses without the key — a name string alone approves
    nothing, and there is no way to hand this function a key."""
    identity = _assert_human_identity(approved_by)
    _assert_iso_moment(approved_at, "approval timestamp")
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
    asserted fact are verified against canonical rows, fail closed).
    reference_time comes ONLY from the gate's own clock (r11) — the sole
    caller is release_for_publish, which derives it from _utcnow()."""
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
        domain_ids=tuple(draft.domain_ids),
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
) -> PublishRelease:
    """The publish decision. Exactly two lawful paths:

    1. a human Approval whose signature verifies under the ENVIRONMENT-held
       founder key, whose hash matches this exact draft, AND whose approver
       identity passes the human check again HERE, or
    2. the founder's signed autonomy record, read from its canonical
       committed path only, signature-verified under the same env key.

    Everything else refuses. There are deliberately NO parameters for key
    material, record paths, trust state (r3), or the clock (r11): the key
    is deployment env, the record location is fixed, current state comes
    from the registered canonical reader, and release-time "now" is the
    gate's own clock — absent any of them, nothing releases. A PRESENT
    autonomy record that fails authentication refuses BOTH paths (r12):
    a corrupt trust-path artifact halts releases entirely rather than
    being quietly ignored while human approvals continue.
    """
    now = _release_moment()
    # The autonomy record is validated BEFORE either path (r12 blocker): a
    # malformed, unsigned, or wrong-signature ratification artifact is a
    # corrupted TRUST-PATH file, and the shipped contract is
    # refuse-everything — releases must not continue silently (even
    # human-approved) over a forged or tampered record. Absent file = L0,
    # which is the ordinary human-in-the-loop state, not a defect.
    active_policy = load_policy()
    _recheck_trust(draft, now.isoformat())
    draft_hash = content_hash(draft)

    if approval is not None:
        _assert_human_identity(approval.approved_by)
        _assert_iso_moment(approval.approved_at, "release refused: approval timestamp")
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
        release = PublishRelease(
            draft_hash=draft_hash,
            surface=draft.surface,
            series_key=draft.series_key,
            released_by=approval.approved_by,
        )
        # Human-approved releases are journaled too when a journal exists
        # (complete record), but per-post human custody never depends on
        # the autonomy grant's counting machinery.
        if _RELEASE_JOURNAL is not None:
            _RELEASE_JOURNAL.record(release, now)
        return release

    if active_policy.level != "L0":
        # Content binding (r10): the grant covers exactly the frozen render
        # surface and the enumerated series — anything else refuses.
        live = renderer_fingerprint()
        if active_policy.renderer_version != live:
            raise ValueError(
                "release refused: the autonomy grant froze renderer "
                f"{active_policy.renderer_version[:12]}… but the live renderer is "
                f"{live[:12]}… — code changed since ratification, re-sign or "
                "approve per post"
            )
        if active_policy.series_keys and draft.series_key not in active_policy.series_keys:
            raise ValueError(
                f"release refused: series {draft.series_key!r} is not in the "
                "autonomy grant's enumerated series"
            )
    if active_policy.allows_auto_release(draft.surface, draft.tier):
        # The grant's cadence ceiling, enforced MECHANICALLY here (r11):
        # no journal = the count cannot be proven = nothing auto-releases,
        # and a spent ceiling refuses until the (gate-clock) day turns.
        if _RELEASE_JOURNAL is None:
            raise ValueError(
                "release refused: no release journal configured — the autonomy "
                "grant's max_releases_per_day cannot be counted, so nothing "
                "auto-releases (register the journal at deployment)"
            )
        released_today = _RELEASE_JOURNAL.count_on(now.date())
        if released_today >= active_policy.max_releases_per_day:
            raise ValueError(
                f"release refused: the autonomy grant's cadence ceiling "
                f"({active_policy.max_releases_per_day}/day) is already spent "
                f"for {now.date()} ({released_today} released)"
            )
        release = PublishRelease(
            draft_hash=draft_hash,
            surface=draft.surface,
            series_key=draft.series_key,
            released_by=f"autonomy:{active_policy.level}",
        )
        _RELEASE_JOURNAL.record(release, now)
        return release
    raise ValueError(
        "release refused: no human approval and the autonomy record does not "
        f"cover ({draft.surface}, {draft.tier}) — default is L0, human in the loop"
    )
