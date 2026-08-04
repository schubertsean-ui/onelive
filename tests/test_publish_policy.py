"""Proof of the earned-confidence auto-publish policy (worker/publish_policy.py):
AI posts at earned confidence WITHOUT a human click, except the founder's two
exceptions (conflict/escalate; often-unreliable source) and the never-moving
line (fabrication risk). Pure: no DB, no network. `ratified` is passed explicitly
so the tests don't depend on the environment flag."""
from worker.publish_policy import decide_publish


# ── The two founder exceptions + the never-moving line ────────────────────────

def test_fabrication_risk_never_auto_publishes_even_when_ratified():
    d = decide_publish(gate_decision="pass", source_classes=["ticketing"],
                       fabrication_risk=True, ratified=True)
    assert d.action == "human_review" and not d.publishes


def test_escalate_goes_to_human_review():
    d = decide_publish(gate_decision="escalate", source_classes=["venue_calendar"],
                       ratified=True)
    assert d.action == "human_review"


def test_unreliable_source_goes_to_human_review():
    d = decide_publish(gate_decision="pass", source_classes=["venue_calendar"],
                       reliability_score=0.20, ratified=True)
    assert d.action == "human_review" and "unreliable" in d.reason


def test_reliable_source_publishes():
    d = decide_publish(gate_decision="pass", source_classes=["venue_calendar"],
                       reliability_score=0.9, ratified=True)
    assert d.publishes


# ── Fail-closed: not ratified → behaves exactly as before (human review) ──────

def test_not_ratified_is_fail_closed_human_review():
    d = decide_publish(gate_decision="pass", source_classes=["ticketing"], ratified=False)
    assert d.action == "human_review" and "not ratified" in d.reason


# ── Earned confidence when it DOES publish ────────────────────────────────────

def test_pass_anchor_publishes_confirmed():
    d = decide_publish(gate_decision="pass", source_classes=["ticketing"], ratified=True)
    assert d.publishes and d.confidence == "confirmed"


def test_pass_two_non_anchor_publishes_likely():
    d = decide_publish(gate_decision="pass", source_classes=["local_media", "social"],
                       ratified=True)
    assert d.publishes and d.confidence == "likely"


def test_single_trusted_source_is_USED_at_likely_displayed_clean():
    # The founder's point: a single radio/TV/press source is great data — publish
    # it at 'likely', displayed clean (founder ruling 2026-08-04) — never queued.
    d = decide_publish(gate_decision="hold", source_classes=["local_media"], ratified=True)
    assert d.publishes and d.confidence == "likely"


def test_unknown_decision_fails_closed():
    d = decide_publish(gate_decision="banana", source_classes=["x"], ratified=True)
    assert d.action == "human_review"
