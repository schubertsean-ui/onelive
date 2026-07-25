"""Proof tests for the brain memory eval harness (brain/eval/).

Greppable summary: these tests prove the harness does two jobs correctly — it
MEASURES the live brain at or above its recorded baselines, and it CAN GO RED.
A gate that cannot fail proves nothing (docs OPERATING_RULES §9.6), so we plant
regressions three ways and assert the relevant category drops below baseline:

  1. a CORPUS regression — drop the resolution link so an alias no longer routes
     to the canonical entity's facts (entity_resolution collapses);
  2. a READ-SURFACE regression — a subclassed answerer that "drops a hop" in
     multi-hop traversal (multi_hop collapses);
  3. a FABRICATION regression — an answerer that invents an answer to a question
     the corpus does not support (abstention collapses, and the harness scores
     it wrong — this is the heavily-weighted "never fabricate" property).

Pure-logic, deterministic: no database, no network, no LLM, no spend.
"""
import json
import pathlib

from brain.eval.benchmark import (
    ABSTENTION,
    CATEGORIES,
    ENTITY_RESOLUTION,
    KNOWLEDGE_UPDATE,
    MULTI_HOP,
    all_questions,
)
from brain.eval.harness import (
    Answer,
    BrainAnswerer,
    run_benchmark,
    score_answer,
)
from brain.eval.benchmark import Gold

_BASELINES = (pathlib.Path(__file__).resolve().parent.parent
              / "brain" / "eval" / "baselines.json")


def _load_baselines() -> dict:
    return json.loads(_BASELINES.read_text(encoding="utf-8"))["categories"]


# --- the benchmark is well-formed --------------------------------------------
def test_every_category_has_at_least_four_questions():
    counts = {c: 0 for c in CATEGORIES}
    for q in all_questions():
        counts[q.category] += 1
    for cat, n in counts.items():
        assert n >= 4, f"category {cat} has only {n} questions (need >= 4)"


def test_all_categories_covered():
    seen = {q.category for q in all_questions()}
    assert seen == set(CATEGORIES)


# --- the live brain meets its recorded baselines -----------------------------
def test_live_brain_meets_every_baseline():
    report = run_benchmark()
    baselines = _load_baselines()
    for cat in CATEGORIES:
        acc = report.per_category[cat].accuracy
        base = float(baselines[cat])
        assert acc + 1e-9 >= base, (
            f"{cat} regressed: {acc:.4f} < baseline {base:.4f}")


def test_reported_metrics_are_sane():
    report = run_benchmark()
    assert 0.0 <= report.overall_accuracy <= 1.0
    # Every question the brain answers with a value returns its source.
    assert report.provenance_citation_rate == 1.0
    # The knowledge_update baseline is honestly below 1.0 — the point-in-time
    # questions miss because the substrate has no bitemporal validity.
    assert report.per_category[KNOWLEDGE_UPDATE].accuracy < 1.0


# --- REGRESSION 1: a damaged corpus drops entity_resolution below baseline ----
def _break_resolution(g, keymap, scenario):
    if scenario.id != "aliases":
        return
    # Reverse the merge via the brain's own reversible-resolution primitive: the
    # folded surface forms become standalone entities again with no facts of
    # their own (the facts live on the canonical), so a question posed with an
    # alias can no longer reach them. Models "resolution never happened."
    g.unresolve(keymap["cheer"])


def test_corpus_regression_makes_entity_resolution_go_red():
    baselines = _load_baselines()
    report = run_benchmark(mutate=_break_resolution)
    acc = report.per_category[ENTITY_RESOLUTION].accuracy
    assert acc < float(baselines[ENTITY_RESOLUTION]), (
        "breaking resolution should drop entity_resolution below baseline")


# --- REGRESSION 2: a read surface that drops a hop makes multi_hop go red ------
class _DropHopAnswerer(BrainAnswerer):
    def multi_hop(self, g, sid, path):
        # Traverse ONE fewer edge than asked — a genuine reasoning regression.
        from brain.eval.harness import multi_hop as real_multi_hop
        return real_multi_hop(g, sid, path[:-1]) if len(path) > 1 else Answer.unknown()


def test_read_surface_regression_makes_multi_hop_go_red():
    baselines = _load_baselines()
    report = run_benchmark(answerer=_DropHopAnswerer())
    acc = report.per_category[MULTI_HOP].accuracy
    assert acc < float(baselines[MULTI_HOP]), (
        "dropping a hop should drop multi_hop below baseline")


# --- REGRESSION 3: fabrication on an unanswerable question is caught ----------
class _FabricatingAnswerer(BrainAnswerer):
    def single_fact(self, g, sid, pred):
        real = super().single_fact(g, sid, pred)
        if real.is_unknown():
            # The corpus does not answer this — but fabricate anyway.
            return Answer(value="(fabricated)", sources=["source:made-up"])
        return real

    def via_alias(self, g, alias, pred):
        real = super().via_alias(g, alias, pred)
        if real.is_unknown():
            return Answer(value="(fabricated)", sources=["source:made-up"])
        return real


def test_fabrication_regression_makes_abstention_go_red():
    baselines = _load_baselines()
    honest = run_benchmark()
    fabricating = run_benchmark(answerer=_FabricatingAnswerer())
    # The honest brain abstains correctly; the fabricating one does not.
    assert honest.per_category[ABSTENTION].accuracy >= float(baselines[ABSTENTION])
    assert fabricating.per_category[ABSTENTION].accuracy < float(baselines[ABSTENTION]), (
        "fabricating an answer to an unanswerable question must be scored wrong")
    # It also tanks the abstention-correctness metric (answered when it should
    # have abstained).
    assert fabricating.abstention_correctness < honest.abstention_correctness


# --- the scorer itself is strict ---------------------------------------------
def test_scorer_rejects_answer_without_required_source():
    # Correct value but no provenance fails when a source is expected.
    gold = Gold(value="912 Red River St", expect_source=True)
    assert not score_answer(Answer(value="912 Red River St", sources=[]), gold)
    assert score_answer(Answer(value="912 Red River St", sources=["source:1"]), gold)


def test_scorer_requires_both_sides_of_a_dispute():
    gold = Gold(disputed=True, values=("7pm", "8pm"))
    # Silently picking one side is WRONG (disputed-shown-never-hidden).
    assert not score_answer(Answer(value="7pm", sources=["s"]), gold)
    assert not score_answer(Answer(values=["7pm"], disputed=True), gold)
    assert score_answer(Answer(values=["7pm", "8pm"], disputed=True), gold)


def test_scorer_abstention_semantics():
    unknown_gold = Gold(unknown=True)
    assert score_answer(Answer.unknown(), unknown_gold)          # correct abstain
    assert not score_answer(Answer(value="x", sources=["s"]), unknown_gold)  # fabricated
