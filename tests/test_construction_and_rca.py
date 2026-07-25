"""Proof that the construction loop LEARNS and the RCA gets to (and trends) roots.

Founder directive (2026-07-25): a researched construction method (confirm
objectives → assess green/red paths → check brain for green examples → select →
run → score → commit to brain → measure improvement/slippage → repeat) plus a
world-leading root-cause analysis. These tests prove the two properties that make
it more than a checklist: experience COMPOUNDS (a prior success is retrieved and
reused; a prior failure becomes a red class to avoid), and recurrence is a
MECHANICAL signal (OPERATING_RULES §1), durable across a reload.
"""
import pytest

from brain.graph import Graph
from brain import store
from brain.construction import (
    CandidatePath,
    Objective,
    improvement,
    plan,
    record_outcome,
    retrieve_green_examples,
    retrieve_red_classes,
)
from brain.rca import CauseCategory, RootCause, analyze, class_frequency


def _obj(cls="ship-importer"):
    return Objective(vision="every local event on /tonight", goal="ship an importer",
                     objective_class=cls, success_criteria="events land, categories right")


def _paths():
    return [
        CandidatePath("structured-feed", "deterministic ICS/JSON-LD import", 0.6,
                      risks=["cost-unbounded"]),
        CandidatePath("ai-extract", "AI extraction of free text", 0.5,
                      risks=["cost-unbounded", "overstatement-built-as-live"]),
    ]


# ── RCA ──────────────────────────────────────────────────────────────────────

def test_rca_requires_a_real_chain_and_a_preventive_action():
    g = Graph()
    with pytest.raises(ValueError):  # one-step "why" is a symptom, not a root
        analyze(g, symptom="x", why_chain=["only one"], category=CauseCategory.MISSING_TEST,
                corrective_action="fix", preventive_action="prevent")
    with pytest.raises(ValueError):  # no preventive control
        analyze(g, symptom="x", why_chain=["a", "b"], category=CauseCategory.MISSING_TEST,
                corrective_action="fix", preventive_action="   ")


def test_rca_commits_root_and_is_blameless_by_type():
    g = Graph()
    rc = analyze(
        g, symptom="promoted events showed 'Other'",
        why_chain=["promote passed no category signal",
                   "card_fields was called with only title",
                   "no test asserted the signal was threaded"],
        category=CauseCategory.MISSING_TEST,
        corrective_action="thread the venue/@type signal into card_fields",
        preventive_action="a wiring test that a config edit changes the output",
    )
    assert rc.root == "no test asserted the signal was threaded"
    assert rc.claim_id and rc.evaluation_id
    # Committed: a root claim + a categorized evaluation are in the graph.
    from brain.schema import NodeType
    assert any(n.id == rc.claim_id for n in g.nodes_of_type(NodeType.CLAIM))
    # Category is a systemic class (there is no "human error" value to pass).
    assert isinstance(rc.category, CauseCategory)


def test_recurrence_becomes_a_finding_at_the_section1_threshold():
    g = Graph()
    kw = dict(symptom="s", why_chain=["a", "b"], category=CauseCategory.OVERSTATEMENT_BUILT_AS_LIVE,
              corrective_action="c", preventive_action="p")
    r1 = analyze(g, **kw)
    r2 = analyze(g, **kw)
    r3 = analyze(g, **kw)
    assert r1.recurrence_count == 0 and not r1.is_recurring_finding
    assert r2.recurrence_count == 1 and not r2.is_recurring_finding
    # 3rd occurrence: prior count is 2 == threshold -> a §1 recurring finding.
    assert r3.recurrence_count == 2 and r3.is_recurring_finding
    assert class_frequency(g, CauseCategory.OVERSTATEMENT_BUILT_AS_LIVE) == 3


# ── Construction loop ────────────────────────────────────────────────────────

def test_first_pass_has_no_precedent_and_falls_back_to_probable_paths():
    g = Graph()
    p = plan(g, _obj(), _paths())
    assert not p.reused_precedent
    assert not p.green_precedents
    assert "probable-paths" in p.rationale
    # Highest est_success wins on a first pass (structured-feed 0.6 > ai-extract 0.5).
    assert p.selected.name == "structured-feed"


def test_a_prior_success_is_retrieved_and_reused_next_pass():
    g = Graph()
    obj = _obj()
    # Pass 1: plan + a SUCCESS on the 'ai-extract' path with a high score.
    p1 = plan(g, obj, _paths())
    out1 = record_outcome(g, obj, _plan_on(g, obj, "ai-extract"),
                          success=True, score=0.95)
    assert out1.trend == "first"
    greens = retrieve_green_examples(g, obj.objective_class)
    assert greens and greens[0].path_name == "ai-extract"
    # Pass 2: even though ai-extract's raw est_success (0.5) is LOWER than
    # structured-feed's (0.6), the proven 0.95 precedent pulls it above -> Reuse.
    p2 = plan(g, obj, _paths())
    assert p2.reused_precedent and p2.selected.name == "ai-extract"
    assert p2.score > 0.6


def test_a_committed_rca_makes_its_class_a_red_path_to_avoid():
    g = Graph()
    analyze(g, symptom="run blew the budget", why_chain=["fan-out uncapped", "no per-run ceiling"],
            category=CauseCategory.COST_UNBOUNDED, corrective_action="cap it",
            preventive_action="budget is a test")
    reds = retrieve_red_classes(g, _obj().objective_class)
    assert "cost-unbounded" in reds
    # Both candidate paths name cost-unbounded as a risk, so both are penalized;
    # planning still returns the least-bad, and surfaces the class to avoid.
    p = plan(g, _obj(), _paths())
    assert "cost-unbounded" in p.red_classes_to_avoid


def test_improvement_and_slippage_are_measured_across_passes():
    g = Graph()
    obj = _obj("measure-me")
    record_outcome(g, obj, _plan_on(g, obj, "structured-feed"), success=True, score=0.70)
    o2 = record_outcome(g, obj, _plan_on(g, obj, "structured-feed"), success=True, score=0.85)
    assert o2.trend == "improving" and o2.delta == pytest.approx(0.15)
    o3 = record_outcome(g, obj, _plan_on(g, obj, "structured-feed"), success=True, score=0.60)
    assert o3.trend == "slipping" and o3.delta == pytest.approx(-0.25)
    imp = improvement(g, "measure-me")
    assert imp["series"] == [0.70, 0.85, 0.60]
    assert imp["direction"] == "slipping"


def test_failure_outcome_carries_the_rca_and_section1_escalation_into_next_actions():
    g = Graph()
    obj = _obj("flaky")
    # Make the class recurring first (2 prior), then a 3rd failure with RCA.
    kw = dict(symptom="s", why_chain=["a", "b"], category=CauseCategory.PROCESS_GAP,
              corrective_action="c", preventive_action="p")
    analyze(g, **kw); analyze(g, **kw)
    rc = analyze(g, **kw)
    assert rc.is_recurring_finding
    out = record_outcome(g, obj, _plan_on(g, obj, "ai-extract"),
                         success=False, score=0.1, root_cause=rc)
    assert out.success is False
    joined = " ".join(out.next_actions)
    assert "preventive" in joined.lower()
    assert "§1 ESCALATION" in joined


def test_learning_is_durable_across_a_reload(tmp_path):
    g = Graph()
    obj = _obj("durable")
    record_outcome(g, obj, _plan_on(g, obj, "structured-feed"), success=True, score=0.9)
    path = tmp_path / "brain.jsonl"
    store.save(g, path)

    reloaded = store.load(path)
    greens = retrieve_green_examples(reloaded, "durable")
    assert greens and greens[0].path_name == "structured-feed"
    # And planning on the reloaded brain reuses the precedent.
    p = plan(reloaded, obj, _paths_named("structured-feed"))
    assert p.reused_precedent


# ── helpers ──────────────────────────────────────────────────────────────────

def _plan_on(g, obj, path_name):
    """A minimal Plan fixing the selected path (so record_outcome stamps it)."""
    from brain.construction import Plan
    sel = CandidatePath(path_name, "d", 0.5)
    return Plan(objective=obj, selected=sel, score=0.5, alternatives=[],
               green_precedents=[], red_classes_to_avoid=[], reused_precedent=False,
               rationale="test")


def _paths_named(name):
    return [CandidatePath(name, "d", 0.4), CandidatePath("other", "d", 0.6)]
