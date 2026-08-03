"""Earned-confidence auto-publish policy for Spark Lines — "AI posts without a
human click, except exceptions", applied to the Descriptor Foundry.

WHY THIS EXISTS (founder-directed 2026-08-03): the #148 Spark Line take-live step
(`worker/descriptor/publish.py::approve_candidate`) required a HUMAN to approve
every line, one at a time. That is exactly the model the founder already REJECTED
for events (2026-07-25, verbatim: "Good lord I can't approve every one of thousands
of events! I told you to prep to enable AI to post without human approval except
for exceptions or sources we have graded as often unreliable.";
docs/memory/decisions/2026-07-25_auto-publish-earned-confidence-ratification.md).
A feature whose whole point is to enrich the feed for users, but which can only
reach a user via thousands of manual clicks, is a catch-22. This module fixes it
by mirroring the ratified events policy (`worker/publish_policy.py`) for Spark
Lines.

THE MODEL. The gate-custodied-publication invariant ("AI never publishes
unvalidated") is satisfied by the VALIDATION GATE,
not by a human click (2026-07-31 canon: reviewer-gate-means-validation). A Spark
Line's validation is the Descriptor Foundry: the mechanical faithfulness gate
(every proper noun/number grounded in the artist's OWN materials — facts never
invented) PLUS an INDEPENDENT judge (a different model than the generator, custody
enforced in `run_foundry`) scoring faithfulness+quality in [0,1]. A line that
clears that gate is validated, so it AUTO-PUBLISHES at its earned display — no
human click — EXCEPT the founder-named exceptions:
  * the independent judge scored BELOW the bar (the "graded unreliable" analog for
    generated copy) -> HUMAN REVIEW;
  * no/invalid judge evidence (a line that did not actually pass the gate) ->
    HUMAN REVIEW (fail-closed: never auto-publish an unvalidated line).
Everything else auto-approves. The founder controls the SWITCH and the bar, never
each line.

CUSTODY. This is NOT "an AI approving its own output": the promotion is driven by
the INDEPENDENT judge's score (a different model) + a founder flag, exactly as the
events policy promotes on the base-owned gate decision + `AUTO_PUBLISH_RATIFIED`.
The judge score must come from the FRESH FoundryResult at write time (never re-read
from a mutable row), so a later tamper cannot manufacture an approval. The manual
`approve_candidate`/`reject_candidate` path remains for spot-checks and overrides.

Auto-publish is gated by one mechanical, fail-closed flag (`AUTO_PUBLISH_SPARK`,
default OFF — reversible in one line). It flips ON only when the founder rules on
the still-held decisions this depends on (the free-lane grounding source + tier-C
generation spend); until then nothing auto-publishes and nothing reaches a user.

This module is PURE (no DB, no network) so the policy is unit-tested exhaustively.
"""
from __future__ import annotations

import numbers
import os
from dataclasses import dataclass
from typing import Optional

# The independent judge's faithfulness+quality score (0..1) a generated line must
# clear to auto-publish. Conservative default — a borderline line goes to a human,
# never silently live. Founder-tunable (spec §4; the events analog is the 0.35
# reliability floor). Below this bar => human review.
DEFAULT_JUDGE_THRESHOLD = 0.80


def auto_publish_spark() -> bool:
    """The single mechanical switch for Spark Line auto-publish. Fail-closed: OFF
    unless explicitly enabled, so a generated line can never go live by accident
    and the change is reversible in one line. Flips ON only when the founder rules
    on the free-lane grounding source + tier-C generation spend it depends on."""
    return os.environ.get("AUTO_PUBLISH_SPARK", "").strip().lower() in (
        "1", "true", "yes", "on")


@dataclass(frozen=True)
class SparkPublishDecision:
    action: str                 # 'auto_approve' | 'human_review'
    reason: str

    @property
    def auto_approves(self) -> bool:
        return self.action == "auto_approve"


def decide_spark_publish(
    *,
    judge_score: Optional[float],
    ratified: Optional[bool] = None,
    judge_threshold: float = DEFAULT_JUDGE_THRESHOLD,
) -> SparkPublishDecision:
    """Decide whether a Foundry-validated Spark Line candidate auto-publishes or
    goes to human review. Pure — all inputs passed in, no DB/network.

    Order matters (fail-closed): the never-auto guards are checked FIRST, then the
    switch, then the judge bar.
    """
    # 1. No/invalid validation evidence => never auto-publish (fail-closed). A
    #    line that did not pass the independent judge is not "validated". Reject a
    #    non-numeric score, a bool (bool is an int subclass — never a real score),
    #    or an out-of-range value, all as human review — never a type error.
    if (
        not isinstance(judge_score, numbers.Real)
        or isinstance(judge_score, bool)
        or not (0.0 <= float(judge_score) <= 1.0)
    ):
        return SparkPublishDecision(
            "human_review",
            f"no valid independent-judge score ({judge_score!r}) — not validated, human review")

    # 2. Fail-closed on the switch: unless the founder-ratification flag is on,
    #    everything goes to human review exactly as before (no silent change).
    is_ratified = auto_publish_spark() if ratified is None else ratified
    if not is_ratified:
        return SparkPublishDecision(
            "human_review", "auto-publish not ratified (fail-closed) — human review")

    # 3. The founder's exception: the independent judge scored below the bar.
    if judge_score < judge_threshold:
        return SparkPublishDecision(
            "human_review",
            f"independent judge below bar ({judge_score:.2f} < {judge_threshold:.2f}) — human review")

    # 4. Validated and above the bar => auto-publish, no human click.
    return SparkPublishDecision(
        "auto_approve",
        f"validated (independent judge {judge_score:.2f} >= {judge_threshold:.2f}) → auto-published")
