"""Authority-based verification — the decision core of the Verification Cascade.

Design of record: docs/strategy/ONE_LIVE_VERIFICATION_ENGINE_v1.md. The founder's
principle (2026-07-31): an event is true only if it traces to a first-party
AUTHORITY — the venue's, artist's, or group's own source. Verification is
*provenance to an authority*, not counting sources.

This module is the PURE decision layer (no DB, no network, no side effects; every
input passed in — mirrors publish_policy.py / triangulate.py so it is exhaustively
unit-testable). It answers two questions:

  1. classify_source_authority(): is a signal's SOURCE a first-party authority
     (and for which kind of entity, on what basis) — or a weak signal?
  2. decide_verification(): given that provenance PLUS the outcome of the active
     resolution cascade (resolved-to-authority? how many independent second
     signals?), does the event VERIFY, VALIDATE, or HOLD — and if HOLD, WHY (a
     machine-readable reason the held-and-learn loop consumes).

It NEVER publishes and NEVER fabricates. The active network steps (fetching the
authority page, finding a second signal) and the registry are separate, later
components; their OUTCOMES are inputs here so the decision stays pure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional

# --- provenance classes -------------------------------------------------------

AUTHORITATIVE = "authoritative"
WEAK = "weak"

# The KIND of first-party authority a source category represents. A source in one
# of these categories is the entity's OWN schedule (or a licensed authority), so
# it is authoritative by construction — the "trust the venue/artist/group's own
# page, full stop" rule. Aggregators, press, and social are NOT here (they are
# weak signals unless the identity registry says a specific page/handle is the
# entity's own).
FIRST_PARTY_CATEGORIES: Mapping[str, str] = {
    "venue_calendar": "venue",
    "calendar_feed": "venue",
    "city_calendar": "organizer",
    "university_calendar": "organizer",
    "library_calendar": "organizer",
    "festival_feed": "organizer",
    "ticketing": "ticketing",
}

# How we KNOW a source is authoritative (recorded for audit/provenance).
BASIS_FIRST_PARTY_FEED = "first_party_feed"     # a first-party calendar we ingest
BASIS_REGISTERED_IDENTITY = "registered_identity"  # domain/handle verified as the entity's own
BASIS_RESOLVED = "resolved_to_authority"        # a weak signal resolved to an authority page
BASIS_SECOND_SIGNAL = "independent_second_signal"

# HOLD reason codes — the held-and-learn loop groups by these to decide what to
# wire next (add a venue page, fix a blocked fetch, build a social connector).
HOLD_SPOOF = "spoof_suspected"
HOLD_NO_AUTHORITY = "no_authority_reachable"
HOLD_NO_SECOND_SIGNAL = "no_second_signal"


@dataclass(frozen=True)
class Provenance:
    """Who said it, and whether that source is an authority."""
    authority: str                 # AUTHORITATIVE | WEAK
    kind: Optional[str] = None     # venue | organizer | ticketing | artist | None
    basis: Optional[str] = None    # a BASIS_* constant
    entity: Optional[str] = None   # the authority entity this ties to, if known
    spoof_suspected: bool = False

    @property
    def is_authoritative(self) -> bool:
        return self.authority == AUTHORITATIVE


def _source_identity(source: Mapping) -> Optional[str]:
    for key in ("source_id", "handle", "domain", "source_name", "source"):
        v = source.get(key)
        if v:
            return str(v).strip().lower()
    return None


def classify_source_authority(
    source: Mapping,
    registry: Optional[Mapping[str, Mapping]] = None,
) -> Provenance:
    """Classify a signal's SOURCE as a first-party authority or a weak signal.

    Order of authority (most authoritative first):
      1. The source's CATEGORY is a first-party authority category (its own
         calendar / a licensed ticketing feed) → authoritative by construction.
      2. The identity REGISTRY maps this source's id/handle/domain to a verified
         official page/account for an entity → authoritative (e.g. the artist's
         OWN verified social handle — "social media can verify alone").
      3. Otherwise → a weak signal (an individual/third-party/press/aggregator).

    `registry` (when provided) maps a lowercased source identity → a record like
    {"kind": "artist", "entity": "Spoon"}. A `spoof_suspected` truthy field on the
    source is carried through — the only extra check applied to an authority.
    """
    spoof = bool(source.get("spoof_suspected"))
    category = str(source.get("category") or "").lower()

    kind = FIRST_PARTY_CATEGORIES.get(category)
    if kind:
        return Provenance(AUTHORITATIVE, kind=kind, basis=BASIS_FIRST_PARTY_FEED,
                          entity=source.get("source_name") or source.get("source_id"),
                          spoof_suspected=spoof)

    if registry:
        ident = _source_identity(source)
        rec = registry.get(ident) if ident else None
        if rec:
            return Provenance(AUTHORITATIVE, kind=rec.get("kind"),
                              basis=BASIS_REGISTERED_IDENTITY, entity=rec.get("entity"),
                              spoof_suspected=spoof)

    return Provenance(WEAK, spoof_suspected=spoof)


# --- the cascade decision -----------------------------------------------------

@dataclass(frozen=True)
class ResolutionOutcome:
    """What the (separate, later) active cascade produced for a WEAK signal:
    whether it was resolved to an authority page, and how many INDEPENDENT second
    signals were found. Defaults describe 'nothing found' — the honest baseline."""
    resolved_to_authority: bool = False
    resolved_kind: Optional[str] = None
    resolved_entity: Optional[str] = None
    second_signals: int = 0        # independent corroborating signals beyond the original
    authority_unreachable: bool = False  # the active step tried an authority and it was blocked/absent


VERIFIED = "verified"
VALIDATED = "validated"
HOLD = "hold"

# How many INDEPENDENT second signals make a non-authority claim CONFIRMED
# rather than merely shown-with-uncertainty. Founder ruling 2026-08-04
# ("Just 'confirmed' - remove 'likely'", decision record
# 2026-08-04_corroborated-tier-publishes-confirmed.md): the corroborated
# tier publishes confirmed; 'likely' belongs EXCLUSIVELY to the publish
# policy's single-trusted-source tier and is never derived from
# corroboration counts. Tunable; documented single source.
CONFIRMED_SECOND_SIGNALS = 2


@dataclass(frozen=True)
class VerificationDecision:
    status: str                    # VERIFIED | VALIDATED | HOLD
    confidence: Optional[str]      # 'confirmed' | 'likely' | 'unverified' | None
    authority_kind: Optional[str]
    basis: Optional[str]
    reason: str
    hold_reason: Optional[str] = None  # a HOLD_* code when status == HOLD

    @property
    def publishable(self) -> bool:
        return self.status in (VERIFIED, VALIDATED)


def decide_verification(provenance: Provenance,
                        resolution: Optional[ResolutionOutcome] = None) -> VerificationDecision:
    """The Verification Cascade decision (pure). Order mirrors the design doc §2.

    1. spoof suspected → HOLD (odd/spoof is the only thing that stops an authority).
    2. authoritative source → VERIFIED (confirmed).
    3. weak + resolved to an authority page → VERIFIED (confirmed).
    4. weak + >=1 independent second signal → VALIDATED (confirmed if >=
       threshold per the 2026-08-04 corroborated-tier ruling, else
       unverified-with-marker — used and shown honestly).
    5. else → HOLD, with a machine-readable reason for the held-and-learn loop.
    """
    if provenance.spoof_suspected:
        return VerificationDecision(HOLD, None, provenance.kind, provenance.basis,
                                    "spoof/odd source suspected — human review",
                                    hold_reason=HOLD_SPOOF)

    if provenance.is_authoritative:
        return VerificationDecision(VERIFIED, "confirmed", provenance.kind,
                                    provenance.basis,
                                    f"first-party authority ({provenance.kind}) — verified")

    res = resolution or ResolutionOutcome()

    if res.resolved_to_authority:
        return VerificationDecision(VERIFIED, "confirmed", res.resolved_kind,
                                    BASIS_RESOLVED,
                                    "weak signal resolved to a first-party authority — verified")

    if res.second_signals >= 1:
        conf = ("confirmed" if res.second_signals >= CONFIRMED_SECOND_SIGNALS
                else "unverified")
        return VerificationDecision(VALIDATED, conf, None, BASIS_SECOND_SIGNAL,
                                    f"validated by {res.second_signals} independent "
                                    f"second signal(s), authority unreachable")

    # Weak signal, authority not reached, and no independent second signal → HOLD.
    # The reason distinguishes 'we tried the authority and it was unreachable'
    # (blocked / no page) from 'no second signal to fall back on' so the
    # held-and-learn loop knows what to wire next; when the active cascade set
    # neither flag it simply had no authority to reach.
    reason_code = HOLD_NO_SECOND_SIGNAL if res.authority_unreachable else HOLD_NO_AUTHORITY
    return VerificationDecision(
        HOLD, None, None, None,
        "weak signal, no authority reachable and no independent second signal — held",
        hold_reason=reason_code)
