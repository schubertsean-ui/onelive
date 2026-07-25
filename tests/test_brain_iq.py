"""Proof tests for the continuous Brain IQ score (brain/iq.py + tools/brain_iq.py).

Greppable summary: these tests prove the multi-dimensional smartness score does
its jobs — the THREE dimensions compute DETERMINISTICALLY, the one-way ratchet
PASSES at/above baseline and FAILS on a planted regression in EACH gated
dimension (knowledge DOWN => red; efficiency-work UP => red), the trend column
reads up/flat/down correctly, latency is recorded but NEVER gated (a slow run
does not fail --check), and the measurement-coverage list is non-empty and
honest. A gate that cannot fail proves nothing (docs OPERATING_RULES §9.6), so
each gate is proven able to fail.

Pure-logic, deterministic: no database, no network, no LLM, no spend. The
measurement instant is always passed IN — no wall clock in the test logic.
"""
import pathlib
import subprocess
import sys

import pytest

from brain.eval.harness import Answer, BrainAnswerer, run_benchmark
from brain.iq import (
    GATED_DIMENSIONS,
    MEASURED,
    NOT_YET_MEASURED,
    BrainIQ,
    DimensionScore,
    check_ratchet,
    compute_brain_iq,
    compute_efficiency,
    compute_knowledge,
    compute_learning,
    trend_symbol,
)
from brain.schema import NodeType

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_CLI = _REPO_ROOT / "tools" / "brain_iq.py"
_LEDGER = _REPO_ROOT / "docs" / "metrics" / "BRAIN_IQ_LEDGER.md"

_NOW = "2026-07-25T00:00:00Z"


# --- planted-regression answerers --------------------------------------------
class _WastefulAnswerer(BrainAnswerer):
    """Does redundant graph retrieval before every answer — genuinely inflates
    the work counter, so EFFICIENCY-work goes UP and its score DROPS."""

    def answer(self, g, keymap, q):
        for node in g.nodes_of_type(NodeType.ENTITY):
            g.subgraph(node.id, hops=2)
        return super().answer(g, keymap, q)


class _FabricatingAnswerer(BrainAnswerer):
    """Invents an answer to a question the corpus does not support, so KNOWLEDGE
    (abstention + overall accuracy) DROPS."""

    def single_fact(self, g, sid, pred):
        real = super().single_fact(g, sid, pred)
        return Answer(value="(fabricated)", sources=["s"]) if real.is_unknown() else real

    def via_alias(self, g, alias, pred):
        real = super().via_alias(g, alias, pred)
        return Answer(value="(fabricated)", sources=["s"]) if real.is_unknown() else real


# --- the three dimensions compute, and deterministically ---------------------
def test_three_dimensions_present_and_bounded():
    iq = compute_brain_iq(now_iso=_NOW)
    for dim in (iq.knowledge, iq.efficiency, iq.learning):
        assert isinstance(dim, DimensionScore)
        assert 0.0 <= dim.score <= 1.0
        assert dim.sub_metrics, f"{dim.name} carries no raw sub-metrics"
    assert 0.0 <= iq.composite <= 1.0


def test_scores_are_deterministic():
    a = compute_brain_iq(now_iso=_NOW)
    b = compute_brain_iq(now_iso="a-different-instant")
    # The SCORES (and composite) are identical run-to-run; only the passed-in
    # instant and the observational latency may differ.
    assert a.score_signature() == b.score_signature()


def test_each_dimension_reports_its_named_sub_metrics():
    iq = compute_brain_iq(now_iso=_NOW)
    assert {"overall_accuracy", "abstention_correctness",
            "provenance_citation_rate", "knowledge_update"} <= set(iq.knowledge.sub_metrics)
    assert {"avg_work_per_query", "full_scan_reference",
            "observed_latency_s"} <= set(iq.efficiency.sub_metrics)
    assert {"adoption_rate", "durability", "findings_shared"} <= set(iq.learning.sub_metrics)


# --- the ratchet PASSES at/above baseline ------------------------------------
def test_ratchet_passes_at_baseline():
    iq = compute_brain_iq(now_iso=_NOW)
    best = iq.gated_scores()
    assert check_ratchet(iq, best=best) == []


def test_ratchet_passes_when_a_gated_dimension_improves():
    iq = compute_brain_iq(now_iso=_NOW)
    # A recorded best BELOW the current scores (the brain improved since) holds.
    lower = {name: max(0.0, s - 0.1) for name, s in iq.gated_scores().items()}
    assert check_ratchet(iq, best=lower) == []


# --- the ratchet FAILS on a planted regression in EACH gated dimension -------
def test_planted_knowledge_regression_turns_ratchet_red():
    baseline = compute_brain_iq(now_iso=_NOW)
    best = baseline.gated_scores()
    degraded_report = run_benchmark(answerer=_FabricatingAnswerer())
    iq = compute_brain_iq(now_iso=_NOW, knowledge_report=degraded_report)
    assert iq.knowledge.score < best["knowledge"]
    regressions = check_ratchet(iq, best=best)
    assert [r.dimension for r in regressions] == ["knowledge"]


def test_planted_efficiency_regression_turns_ratchet_red():
    baseline = compute_brain_iq(now_iso=_NOW)
    best = baseline.gated_scores()
    iq = compute_brain_iq(now_iso=_NOW, efficiency_answerer=_WastefulAnswerer())
    # More work per query => lower efficiency score.
    assert iq.efficiency.sub_metrics["avg_work_per_query"] > \
        baseline.efficiency.sub_metrics["avg_work_per_query"]
    assert iq.efficiency.score < best["efficiency"]
    regressions = check_ratchet(iq, best=best)
    assert [r.dimension for r in regressions] == ["efficiency"]


# --- the trend column reads up / flat / down correctly -----------------------
def test_trend_symbol_reads_up_flat_down():
    assert trend_symbol(0.90, None) == "-"          # first row, no predecessor
    assert trend_symbol(0.95, 0.90) == "↑"          # up
    assert trend_symbol(0.90, 0.90) == "→"          # flat
    assert trend_symbol(0.85, 0.90) == "↓"          # down
    # A change smaller than epsilon reads flat (float-safe).
    assert trend_symbol(0.900001, 0.900000, eps=1e-3) == "→"


# --- latency is recorded but NEVER gated -------------------------------------
def test_latency_is_recorded():
    iq = compute_brain_iq(now_iso=_NOW)
    assert "observed_latency_s" in iq.efficiency.sub_metrics
    assert iq.efficiency.sub_metrics["observed_latency_s"] >= 0.0


def test_slow_run_does_not_fail_the_ratchet():
    # Construct an IQ whose scores meet the best but whose latency is enormous;
    # the ratchet must ignore latency entirely.
    good = compute_efficiency()
    slow_eff = DimensionScore(name="efficiency", score=good.score,
                              sub_metrics={**good.sub_metrics,
                                           "observed_latency_s": 999.0})
    iq = BrainIQ(now_iso=_NOW, knowledge=compute_knowledge(),
                 efficiency=slow_eff, learning=compute_learning())
    best = {"knowledge": iq.knowledge.score, "efficiency": iq.efficiency.score}
    assert check_ratchet(iq, best=best) == []
    assert "observed_latency_s" not in GATED_DIMENSIONS


# --- learning is NOT gated (trended only) ------------------------------------
def test_learning_is_not_a_gated_dimension():
    assert "learning" not in GATED_DIMENSIONS
    # Even a collapsed learning score never appears in the ratchet result.
    iq = compute_brain_iq(now_iso=_NOW)
    best = iq.gated_scores()
    zero_learning = BrainIQ(now_iso=_NOW, knowledge=iq.knowledge,
                            efficiency=iq.efficiency,
                            learning=DimensionScore("learning", 0.0, {"x": 0.0}))
    assert check_ratchet(zero_learning, best=best) == []


# --- the measurement-coverage list is non-empty and honest -------------------
def test_measurement_coverage_is_non_empty_and_honest():
    assert MEASURED, "the measured-dimensions list must not be empty"
    assert NOT_YET_MEASURED, "the NOT-yet-measured list must not be empty — a " \
        "score that claims to measure everything is a Goodhart trap"
    for item in NOT_YET_MEASURED:
        assert item.name and item.why and item.trigger, (
            f"coverage item {item.name!r} must carry a why AND a trigger")
    # The external public-benchmark gap is named on purpose (honesty about our
    # own-benchmark scope, R-041).
    names = " ".join(i.name.lower() for i in NOT_YET_MEASURED)
    assert "longmemeval" in names


# --- the CLI works end to end (print / append / check) -----------------------
def _run_cli(args, ledger):
    return subprocess.run(
        [sys.executable, str(_CLI), "--ledger", str(ledger), *args],
        capture_output=True, text=True, cwd=str(_REPO_ROOT))


def _seed_ledger(path):
    path.write_text(
        "# test ledger\n\n"
        "| timestamp | knowledge | efficiency | learning | composite | trend |\n"
        "|---|---|---|---|---|---|\n",
        encoding="utf-8")


def test_cli_print_runs_clean():
    proc = _run_cli(["--print"], _LEDGER)
    assert proc.returncode == 0, proc.stderr
    assert "Brain IQ" in proc.stdout
    assert "KNOWLEDGE" in proc.stdout and "EFFICIENCY" in proc.stdout \
        and "LEARNING" in proc.stdout


def test_cli_append_then_check_holds(tmp_path):
    ledger = tmp_path / "ledger.md"
    _seed_ledger(ledger)
    appended = _run_cli(["--append", _NOW], ledger)
    assert appended.returncode == 0, appended.stderr
    body = ledger.read_text(encoding="utf-8")
    assert _NOW in body
    # A freshly-appended real measurement is exactly current, so --check holds.
    checked = _run_cli(["--check"], ledger)
    assert checked.returncode == 0, checked.stderr


def test_cli_append_computes_trend_against_prior_row(tmp_path):
    ledger = tmp_path / "ledger.md"
    _seed_ledger(ledger)
    # Hand-seed a LOWER prior composite so the real append trends UP.
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write("| 2020-01-01T00:00:00Z | 0.5000 | 0.5000 | 0.5000 | 0.5000 | - |\n")
    _run_cli(["--append", _NOW], ledger)
    last = [ln for ln in ledger.read_text(encoding="utf-8").splitlines()
            if _NOW in ln][0]
    assert last.strip().endswith("↑ |"), last


def test_cli_check_fails_loud_without_a_ledger(tmp_path):
    empty = tmp_path / "no_rows.md"
    empty.write_text("# empty\n\nno table here\n", encoding="utf-8")
    proc = _run_cli(["--check"], empty)
    assert proc.returncode == 2, proc.stdout + proc.stderr
