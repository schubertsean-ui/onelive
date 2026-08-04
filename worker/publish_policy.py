"""Earned-confidence auto-publish policy — the decision layer for "AI posts
without a human click, except for exceptions."

Founder ratification (2026-07-25, verbatim): "I told you to prep to enable AI to
post without human approval except for exceptions or sources we have graded as
often unreliable." This module is that decision, made mechanically and testably.
See docs/memory/decisions/2026-07-25_auto-publish-earned-confidence-ratification.md.

THE MODEL. Every fetched, extracted, non-fabricated candidate is PUBLISHED at its
EARNED confidence with honest uncertainty display — no human click — EXCEPT the
two founder-named exceptions plus the one line that never moves:
  * ESCALATE (a real conflict: contradictory times, private-RSVP, dedupe
    ambiguity, or a validation error) → HUMAN REVIEW. Never auto-published.
  * a source graded OFTEN-UNRELIABLE (reliability below threshold) → HUMAN REVIEW.
  * fabrication risk (schema-invalid extraction / sensor-rejected shell) →
    HUMAN REVIEW. The "never invent an event that isn't real" invariant is
    preserved — auto-publish only ever publishes real extracted candidates.
Everything else publishes at earned confidence:
  * PASS (anchor, or corroborated by ≥2 independent sources) → confirmed.
    (Founder ruling 2026-08-04, verbatim: "Just 'confirmed' - remove 'likely'"
    — the corroborated tier earns the anchor's label.)
  * HOLD (a single trustworthy non-anchor source — radio/TV/press/one venue) →
    PUBLISHED at 'likely', displayed CLEAN (founder ruling 2026-08-04:
    "Trustworthy is trustworthy … publish without the uncertainty marker").
    A single good source is USED; corroboration or an anchor raises it to
    confirmed via the PASS path.
`disputed` is a separate moderation state and is ALWAYS shown as disputed.

This module is PURE (no DB, no network) so the policy is unit-tested exhaustively.
The wiring that acts on it (worker/autopromote.py) is the only new promoter and is
added to the promote-import allowlist in the same change. Auto-publish is gated by
a single mechanical flag (fail-closed OFF by default) so it is auditable and
reversible in one line — the founder's ratification flips it once the safeguards
(reliability grading + uncertainty display) are live.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from worker.confidence import derive_confidence

# Sources at or below this evolving reliability score (worker/source_reliability.py,
# 0..1, starts at 0.5) are "often unreliable" → their candidates go to human
# review instead of auto-publishing. Founder-tunable; conservative default.
DEFAULT_RELIABILITY_THRESHOLD = 0.35


def auto_publish_ratified() -> bool:
    """The single mechanical switch. Fail-closed: OFF unless explicitly enabled,
    so the deepest trust change can never be live by accident and is reversible in
    one line. The founder's ratification flips AUTO_PUBLISH_RATIFIED to a truthy
    value once the safeguards (reliability grading + honest uncertainty display)
    are proven live."""
    return os.environ.get("AUTO_PUBLISH_RATIFIED", "").strip().lower() in (
        "1", "true", "yes", "on")


@dataclass(frozen=True)
class PublishDecision:
    action: str                     # 'publish' | 'human_review'
    confidence: Optional[str]       # the earned 4-state confidence when publishing
    reason: str

    @property
    def publishes(self) -> bool:
        return self.action == "publish"


def decide_publish(
    *,
    gate_decision: str,             # 'pass' | 'hold' | 'escalate'
    source_classes: List[str],
    sxsw_mode: bool = False,
    reliability_score: Optional[float] = None,
    fabrication_risk: bool = False,
    ratified: Optional[bool] = None,
    reliability_threshold: float = DEFAULT_RELIABILITY_THRESHOLD,
) -> PublishDecision:
    """Decide whether a candidate auto-publishes (and at what earned confidence)
    or goes to human review. Pure — all inputs passed in, no DB/network.

    Order matters: the never-auto-publish guards are checked FIRST (fail-closed),
    then the ratification switch, then the earned-confidence publish.
    """
    gd = (gate_decision or "").strip().lower()

    # 1. Fabrication risk is NEVER auto-published — the one line that never moves.
    if fabrication_risk:
        return PublishDecision("human_review", None,
                               "fabrication risk (schema-invalid / sensor-rejected) — human review")

    # 2. Fail-closed: unless the founder-ratification switch is on, everything
    #    goes to human review exactly as before (no silent behavior change).
    is_ratified = auto_publish_ratified() if ratified is None else ratified
    if not is_ratified:
        return PublishDecision("human_review", None,
                               "auto-publish not ratified (fail-closed) — human review")

    # 3. A real conflict is a human's call, never auto-published.
    if gd == "escalate":
        return PublishDecision("human_review", None,
                               "gate ESCALATE (conflict/private/dedupe) — human review")

    # 4. The founder's second exception: an often-unreliable source.
    if reliability_score is not None and reliability_score < reliability_threshold:
        return PublishDecision("human_review", None,
                               f"source graded unreliable ({reliability_score:.2f} < "
                               f"{reliability_threshold:.2f}) — human review")

    # 5. Publish at EARNED confidence.
    if gd == "pass":
        conf = derive_confidence(source_classes, sxsw_mode=sxsw_mode)  # confirmed (anchor OR corroborated — founder ruling 2026-08-04)
        return PublishDecision("publish", conf, f"PASS → auto-published as {conf}")
    if gd == "hold":
        # A single TRUSTWORTHY non-anchor source publishes at 'likely' — founder
        # ruling 2026-08-04, verbatim: "Trustworthy is trustworthy … If it is,
        # publish without the uncertainty marker." (The earlier 'unverified'+
        # marker treatment was a mis-carry from the social-media discussion.)
        # Reliability is enforced ABOVE (step 4): an often-unreliable source
        # never reaches this line. 'likely' fits its own definition — one
        # credible source, not yet corroborated — and displays clean
        # (web/lib/trust.ts, same founder ruling).
        return PublishDecision("publish", "likely",
                               "single trustworthy source → auto-published as likely (founder ruling 2026-08-04)")

    # Unknown decision → fail closed.
    return PublishDecision("human_review", None,
                           f"unrecognized gate decision {gate_decision!r} — human review")
