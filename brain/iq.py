"""Brain IQ — a continuous, multi-dimensional score of how smart the brain is.

Greppable summary: the founder directive is that the brain's improvement be
QUANTIFIED and TRENDED over time — "it gets quantifiably smarter, one or even 3
kinds of smartness." This module computes a :class:`BrainIQ` with THREE kinds of
smartness, each a 0..1 score plus its raw sub-metrics, all DETERMINISTIC (no
network, no LLM, no spend, and NO wall clock in the scoring logic — the
measurement instant is passed IN as ``now_iso``):

  * KNOWLEDGE — is the brain RIGHT? Reuses the memory-eval report
    (``brain/eval/``): overall accuracy, provenance-citation rate,
    abstention-correctness, and the hard temporal (knowledge-update) competency,
    folded into one 0..1 with a documented weighting.
  * EFFICIENCY — does the brain reach the same answers with LESS WORK? A
    DETERMINISTIC retrieval-work metric (graph nodes+edges materialised per
    benchmark query, lower = better) is the GATED number. A wall-latency figure
    is ALSO recorded for the trend, but it is machine-dependent and flaky, so it
    is NEVER gated — "smarter" = same knowledge at less graph work, not a faster
    CPU.
  * LEARNING — does the shared acquisition toolkit COMPOUND across runs? From a
    fixed, seeded+simulated history (fixed dates passed in, never a clock):
    adoption (recipes engaged by >=2 distinct runs), durability (learned recipes
    still valid, not flagged needs_rediscovery), and the count of shared
    findings (reusable techniques the whole org reads).

The composite is a documented weighted blend, but a single number HIDES detail,
so the per-dimension scores govern and the ledger trends every dimension
separately (docs/metrics/BRAIN_IQ_LEDGER.md). Goodhart honesty: this module also
carries the EXPLICIT list of what is NOT yet measured
(:data:`NOT_YET_MEASURED`), so "we measure some, not all" is visible and
shrinking, never hidden (docs/metrics/BRAIN_MEASUREMENT_COVERAGE.md).

Like the rest of ``brain/``, this is MEASUREMENT only: it never publishes and
never imports ``worker.promote``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from brain import acquisition as _acq
from brain.acquisition import AcquisitionRecipe, AcquisitionToolkit
from brain.eval.benchmark import BENCHMARK, KNOWLEDGE_UPDATE
from brain.eval.harness import BrainAnswerer, MemoryEvalReport, run_benchmark
from brain.schema import EdgeType, NodeType
from brain.seed_acquisition import technique_library


# ============================================================================
# KNOWLEDGE — is the brain RIGHT? (folds the memory-eval report into one 0..1)
# ============================================================================
# Documented weighting (sums to 1.0). Overall accuracy is the backbone;
# abstention-correctness is weighted heavily because fabricating an answer to an
# unanswerable question is the worst failure (never-fabricate is a trust
# invariant); provenance-citation keeps answers sourced; the temporal
# (knowledge_update) competency is emphasised on TOP of its share of overall
# accuracy because point-in-time recall is the hard, historically-open capability
# (R-010/R-031/R-041) we most want to keep measuring as it improves.
KNOWLEDGE_WEIGHTS = {
    "overall_accuracy": 0.40,
    "abstention_correctness": 0.25,
    "provenance_citation_rate": 0.20,
    "knowledge_update": 0.15,
}


def compute_knowledge(report: Optional[MemoryEvalReport] = None) -> "DimensionScore":
    """Fold the deterministic memory-eval report into one 0..1 KNOWLEDGE score.

    ``report`` defaults to a fresh ``run_benchmark()``; a caller/test may pass a
    DEGRADED report (e.g. from a fabricating answerer) to plant a regression.
    """
    report = report if report is not None else run_benchmark()
    subs = {
        "overall_accuracy": report.overall_accuracy,
        "abstention_correctness": report.abstention_correctness,
        "provenance_citation_rate": report.provenance_citation_rate,
        "knowledge_update": report.per_category[KNOWLEDGE_UPDATE].accuracy,
    }
    score = sum(KNOWLEDGE_WEIGHTS[k] * subs[k] for k in KNOWLEDGE_WEIGHTS)
    subs["n_questions"] = float(report.n_total)
    return DimensionScore(name="knowledge", score=score, sub_metrics=subs)


# ============================================================================
# EFFICIENCY — same answers at LESS WORK (deterministic; latency observed only)
# ============================================================================
class _WorkCountingGraph:
    """A transparent proxy over a brain ``Graph`` that COUNTS retrieval work.

    The eval harness answers every question by querying the brain — bounded
    ``subgraph()`` neighbourhoods and point-in-time ``claims_valid_at()`` reads.
    This proxy forwards every attribute to the real graph but tallies the volume
    of graph elements each read materialises (nodes+edges of a subgraph, claims
    of a point-in-time read). That tally is the DETERMINISTIC "work" a query
    costs: a brain that reaches the same answer touching fewer graph elements is
    doing less work, i.e. is more efficient. No wall clock is involved here.
    """

    def __init__(self, graph) -> None:
        self._g = graph
        self.work = 0

    def reset(self) -> None:
        self.work = 0

    def subgraph(self, *args, **kwargs):
        sg = self._g.subgraph(*args, **kwargs)
        self.work += len(sg.nodes) + len(sg.edges)
        return sg

    def claims_valid_at(self, *args, **kwargs):
        result = self._g.claims_valid_at(*args, **kwargs)
        self.work += len(result)
        return result

    def __getattr__(self, name):
        # Only reached for attributes not defined above (get, nodes_of_type,
        # has, the edges dict, ...): forward them untouched to the real graph.
        return getattr(self._g, name)


def compute_efficiency(*, answerer: Optional[BrainAnswerer] = None,
                       measure_latency: bool = True) -> "DimensionScore":
    """Measure the brain's average retrieval WORK per benchmark query.

    The GATED number is ``efficiency_score`` = ref / (ref + avg_work), where
    ``avg_work`` is the mean graph elements materialised per query and ``ref`` is
    the average FULL-GRAPH size (a naive "scan everything" brain's reference).
    Lower work => higher score, always in (0, 1], and improvement is always
    visible (no cap hides it). ``ref`` is derived from the fixed benchmark, so
    the score is reproducible byte-for-byte and comparable across ledger rows.

    A wall-latency figure is ALSO measured (``observed_latency_s``) and returned
    in the sub-metrics FOR THE TREND ONLY — it is machine-dependent and flaky and
    is never part of the score or the ratchet. ``measure_latency=False`` skips it
    for a fully clock-free run.
    """
    answerer = answerer if answerer is not None else BrainAnswerer()
    total_work = 0
    n_questions = 0
    total_graph_size = 0
    n_scenarios = 0

    start = time.perf_counter() if measure_latency else None
    for scenario in BENCHMARK:
        g, keymap = scenario.build()
        total_graph_size += len(g.nodes) + len(g.edges)
        n_scenarios += 1
        proxy = _WorkCountingGraph(g)
        for q in scenario.questions:
            proxy.reset()
            answerer.answer(proxy, keymap, q.query)
            total_work += proxy.work
            n_questions += 1
    latency = (time.perf_counter() - start) if start is not None else 0.0

    avg_work = total_work / n_questions if n_questions else 0.0
    ref = total_graph_size / n_scenarios if n_scenarios else 1.0
    score = ref / (ref + avg_work) if (ref + avg_work) else 0.0
    subs = {
        "avg_work_per_query": avg_work,
        "total_work": float(total_work),
        "n_questions": float(n_questions),
        "full_scan_reference": ref,
        # OBSERVED wall latency of one full benchmark sweep — recorded for the
        # trend, NEVER gated (machine-dependent, flaky). Do not fold into score.
        "observed_latency_s": latency,
    }
    return DimensionScore(name="efficiency", score=score, sub_metrics=subs)


# ============================================================================
# LEARNING — does the shared toolkit COMPOUND across runs? (seeded scenario)
# ============================================================================
# A mature shared toolkit target for normalising the raw shared-findings count
# into a 0..1 term. Documented constant, not a magic number: it is the count of
# reusable techniques a world-class acquisition toolkit maintains as common
# know-how; the seeded library ships fewer, so this term has visible headroom.
FINDINGS_TARGET = 10

# LEARNING sub-weights (sum 1.0): adoption and durability are the compounding
# signals (know-how reused across runs, and staying valid); shared-findings
# breadth is the smaller third.
LEARNING_WEIGHTS = {"adoption_rate": 0.40, "durability": 0.40,
                    "findings_shared_norm": 0.20}

# Fixed, deterministic simulated history (NO wall clock — integer stamps passed
# in). Five recipes over three distinct learning runs plus the seed run.
_SEED_RUN = "iq-seed"
_LEARNING_SOURCES = ("iq-src-a", "iq-src-b", "iq-src-c", "iq-src-d", "iq-src-e")
_T = (1_700_000_000.0, 1_700_003_600.0, 1_700_007_200.0, 1_700_010_800.0)


def _seeded_learning_toolkit() -> AcquisitionToolkit:
    """Build a toolkit with a FIXED seeded+simulated acquisition history.

    Deterministic by construction: fixed source ids, fixed run ids, fixed yields,
    and fixed integer timestamps passed as ``at=`` (never ``time.time()``). Models
    the compounding loop — different runs read-before-acquire and record outcomes
    back into the ONE shared toolkit, so adoption/durability/shared-findings are
    reproducible facts.
    """
    toolkit = AcquisitionToolkit()
    # Shared findings: the real reusable technique library (cross-source
    # know-how every agent reads). No catalog file needed — this list is
    # self-contained in brain/seed_acquisition.py.
    for tech in technique_library():
        toolkit.register_technique(tech, run_id=_SEED_RUN)
    a_tech = technique_library()[0].name  # a real technique to attribute uses to

    for source_id in _LEARNING_SOURCES:
        toolkit.register_recipe(
            AcquisitionRecipe(source_id=source_id, source_name=source_id,
                              calendar_url=f"https://{source_id}.test/events",
                              access_method="plain_http"),
            run_id=_SEED_RUN)

    def outcome(source_id, run_id, yield_count, at):
        toolkit.record_outcome(source_id, run_id=run_id, method="plain_http",
                               technique=a_tech, yield_count=yield_count,
                               success=True, at=at)

    # src-a: engaged by run-1 then run-2, both effective -> adopted, durable.
    outcome("iq-src-a", "run-1", 10, _T[1])
    outcome("iq-src-a", "run-2", 8, _T[2])
    # src-b: engaged by run-1 then run-3, both effective -> adopted, durable.
    outcome("iq-src-b", "run-1", 5, _T[1])
    outcome("iq-src-b", "run-3", 6, _T[3])
    # src-c: run-1 twice, both ZERO-yield -> consecutive_empty hits the
    # rediscovery threshold -> needs_rediscovery=True (NOT durable).
    outcome("iq-src-c", "run-1", 0, _T[1])
    outcome("iq-src-c", "run-1", 0, _T[2])
    # src-d: engaged once by run-2 -> adopted (seed+run-2), durable.
    outcome("iq-src-d", "run-2", 7, _T[2])
    # src-e: seed only -> engaged by one run, not adopted.
    return toolkit


def _distinct_run_objectives(graph, entity_id: str) -> set:
    """Distinct AgentRun objectives that WROTE a state claim on ``entity_id``.

    Reads only: for every claim MENTIONING the entity, follow its DERIVED_FROM
    edge to the AgentRun that learned it (acquisition binds every write to its
    run). A recipe touched by >=2 distinct runs is one the shared toolkit engaged
    across runs (a write is always preceded by a read-before-acquire).
    """
    runs: set = set()
    for edge in graph.edges.values():
        if edge.edge_type is EdgeType.MENTIONS and edge.dst == entity_id:
            claim_id = edge.src
            for derived in graph.edges.values():
                if derived.src == claim_id and derived.edge_type is EdgeType.DERIVED_FROM:
                    node = graph.nodes.get(derived.dst)
                    if node is not None and node.node_type == NodeType.AGENT_RUN:
                        runs.add(node.objective)
    return runs


def compute_learning(toolkit: Optional[AcquisitionToolkit] = None) -> "DimensionScore":
    """Compounding LEARNING metrics from the shared acquisition toolkit.

    ``toolkit`` defaults to the fixed seeded scenario; a test may pass its own.
    """
    toolkit = toolkit if toolkit is not None else _seeded_learning_toolkit()
    graph = toolkit.g
    recipes = toolkit.all_recipes()
    n_recipes = len(recipes)

    adopted = 0
    durable = 0
    for recipe in recipes:
        entity = None
        for node in graph.nodes_of_type(NodeType.ENTITY):
            if (getattr(node, "entity_type", "") == _acq._RECIPE_ENTITY_TYPE
                    and node.name == recipe.source_id):
                entity = node
                break
        if entity is not None and len(_distinct_run_objectives(graph, entity.id)) >= 2:
            adopted += 1
        if not recipe.needs_rediscovery:
            durable += 1

    findings_shared = len(toolkit.all_techniques())
    adoption_rate = adopted / n_recipes if n_recipes else 0.0
    durability = durable / n_recipes if n_recipes else 0.0
    findings_norm = min(1.0, findings_shared / FINDINGS_TARGET)

    score = (LEARNING_WEIGHTS["adoption_rate"] * adoption_rate
             + LEARNING_WEIGHTS["durability"] * durability
             + LEARNING_WEIGHTS["findings_shared_norm"] * findings_norm)
    subs = {
        "adoption_rate": adoption_rate,
        "durability": durability,
        "findings_shared": float(findings_shared),
        "findings_shared_norm": findings_norm,
        "n_recipes": float(n_recipes),
    }
    return DimensionScore(name="learning", score=score, sub_metrics=subs)


# ============================================================================
# The composite report
# ============================================================================
# Composite weighting (sums to 1.0): knowledge is primary (being RIGHT dominates
# being fast or well-read); efficiency is a real second axis; learning is the
# compounding third but the least mature (seeded, not live). A composite HIDES
# detail — the per-dimension scores govern, and the ledger trends each alone.
COMPOSITE_WEIGHTS = {"knowledge": 0.50, "efficiency": 0.30, "learning": 0.20}

# The GATED dimensions of the one-way ratchet: KNOWLEDGE (accuracy must not
# regress) and EFFICIENCY (retrieval work must not rise). LEARNING is trended but
# NOT gated (the seeded scenario is illustrative, not a live workload), and
# latency is NEVER gated (machine-dependent).
GATED_DIMENSIONS = ("knowledge", "efficiency")


@dataclass
class DimensionScore:
    """One kind of smartness: a 0..1 score plus the raw sub-metrics behind it."""

    name: str
    score: float
    sub_metrics: dict = field(default_factory=dict)


@dataclass
class BrainIQ:
    """The brain's multi-dimensional IQ at ``now_iso`` (a passed-in instant)."""

    now_iso: str
    knowledge: DimensionScore
    efficiency: DimensionScore
    learning: DimensionScore

    @property
    def composite(self) -> float:
        return (COMPOSITE_WEIGHTS["knowledge"] * self.knowledge.score
                + COMPOSITE_WEIGHTS["efficiency"] * self.efficiency.score
                + COMPOSITE_WEIGHTS["learning"] * self.learning.score)

    def dimension(self, name: str) -> DimensionScore:
        return getattr(self, name)

    def gated_scores(self) -> dict:
        return {name: self.dimension(name).score for name in GATED_DIMENSIONS}

    def score_signature(self) -> tuple:
        """The deterministic (latency-free) signature, for equality in tests.

        Excludes ``observed_latency_s`` deliberately — latency is observational
        and varies run-to-run; the SCORES do not.
        """
        return (round(self.knowledge.score, 12),
                round(self.efficiency.score, 12),
                round(self.learning.score, 12),
                round(self.composite, 12))


def compute_brain_iq(*, now_iso: str,
                     knowledge_report: Optional[MemoryEvalReport] = None,
                     efficiency_answerer: Optional[BrainAnswerer] = None,
                     learning_toolkit: Optional[AcquisitionToolkit] = None,
                     measure_latency: bool = True) -> BrainIQ:
    """Compute the 3-kind BrainIQ at ``now_iso`` (the instant is passed IN).

    All overrides default to the real deterministic computation; they exist so
    the tests can plant a regression in a single dimension (a degraded knowledge
    report, a wasteful efficiency answerer) and prove the ratchet fires.
    """
    if not now_iso:
        raise ValueError("compute_brain_iq requires now_iso (the measurement "
                         "instant is passed IN — library code never reads a clock).")
    return BrainIQ(
        now_iso=now_iso,
        knowledge=compute_knowledge(knowledge_report),
        efficiency=compute_efficiency(answerer=efficiency_answerer,
                                      measure_latency=measure_latency),
        learning=compute_learning(learning_toolkit),
    )


# ============================================================================
# Trend + one-way ratchet
# ============================================================================
def trend_symbol(current: float, previous: Optional[float], eps: float = 1e-4) -> str:
    """Direction of ``current`` vs the ``previous`` row: up / flat / down.

    ``previous is None`` (the first ledger row) has no predecessor, shown "-".
    """
    if previous is None:
        return "-"
    if current > previous + eps:
        return "↑"  # up
    if current < previous - eps:
        return "↓"  # down
    return "→"  # flat


# The ratchet epsilon: a float-safe slack so an identical recomputation is never
# read as a regression. A real regression is far larger than this.
RATCHET_EPS = 1e-6


@dataclass
class Regression:
    dimension: str
    current: float
    best: float


def check_ratchet(iq: BrainIQ, *, best: dict, eps: float = RATCHET_EPS) -> list:
    """Return the GATED dimensions that regressed below their best-recorded value.

    ``best`` maps a gated dimension name to its best recorded score. Each gated
    dimension must be >= its best minus ``eps``; anything lower is a regression
    (the brain got WORSE at that kind of smartness). LEARNING and latency are not
    gated and are never checked here.
    """
    regressions = []
    scores = iq.gated_scores()
    for name in GATED_DIMENSIONS:
        floor = best.get(name)
        if floor is None:
            continue
        if scores[name] + eps < floor:
            regressions.append(Regression(dimension=name, current=scores[name],
                                          best=float(floor)))
    return regressions


# ============================================================================
# Measurement coverage — the Goodhart-honesty control (measured vs NOT measured)
# ============================================================================
@dataclass(frozen=True)
class CoverageItem:
    name: str
    why: str
    trigger: str


# What IS measured today (the three dimensions and their sub-metrics).
MEASURED = (
    CoverageItem(
        "KNOWLEDGE — accuracy on the 6 agent-memory competencies",
        "The deterministic memory benchmark (brain/eval/) scores single-fact, "
        "multi-hop, knowledge-update (bi-temporal), contradiction, entity "
        "resolution, and abstention by exact match — free, reproducible.",
        "Live per tools/validate; ratchet in brain/eval/baselines.json + this IQ."),
    CoverageItem(
        "EFFICIENCY — graph retrieval work per query",
        "Deterministic count of graph nodes+edges materialised per benchmark "
        "query; 'smarter' = same knowledge at less work.",
        "Live and GATED here; the one-way ratchet forbids work rising."),
    CoverageItem(
        "LEARNING — adoption, durability, shared findings",
        "Compounding metrics from the shared acquisition toolkit over a fixed "
        "seeded+simulated history (deterministic).",
        "Live and trended (not gated — seeded scenario, not a live workload)."),
)

# What is KNOWN but NOT yet measured — named on purpose so the gap is visible and
# shrinking, never hidden. Each carries WHY it is unmeasured and an objective
# TRIGGER to close it. This is the Goodhart-honesty control: the score measures
# some kinds of smartness, and here is exactly which kinds it does not.
NOT_YET_MEASURED = (
    CoverageItem(
        "Reasoning depth beyond ~3 hops",
        "The benchmark's deepest chain is 3 hops; deeper multi-step reasoning "
        "(4+ hops, joins across many relations) is not exercised, so 'reasoning "
        "IQ' is only partially covered.",
        "Add >=4-hop labeled questions to brain/eval/benchmark.py and a "
        "reasoning-depth sub-metric when a real query needs that depth."),
    CoverageItem(
        "Real production extraction yield",
        "LEARNING uses a SEEDED toolkit history, not live ingestion — no live "
        "code yet reads recipe_for/record_outcome (R-040), so real adoption and "
        "yield-per-source are unmeasured.",
        "When the live orchestrator is toolkit-guided (R-040), fold real "
        "per-source yield and adoption into LEARNING."),
    CoverageItem(
        "Real wall-latency under load",
        "Only a single-run observational latency is recorded, and it is never "
        "gated (machine-dependent, flaky). Throughput and tail latency under "
        "concurrent load are unmeasured.",
        "Add a load/throughput harness when the brain serves live query traffic; "
        "gate on p50/p95 work-per-query, never raw wall time."),
    CoverageItem(
        "External LongMemEval (public leaderboard)",
        "KNOWLEDGE is OUR OWN benchmark scored by exact match (R-041); it is NOT "
        "comparable to the public LongMemEval figures (which need the public "
        "dataset + an LLM judge + real spend).",
        "Founder-crucial spend decision (G-BRAIN-1D): run real LongMemEval via "
        "the budgeted model router; the brain/eval read surface is the adapter."),
)
