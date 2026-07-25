"""Construction loop — plan from experience, run, score, learn, repeat.

Founder directive (2026-07-25), a loop they specified almost verbatim as the
canonical case-based-reasoning cycle: "confirm vision, goals and specific
objectives; assess all parameters for green and red probable paths; check brain
for existing green examples/successes; select the most likely success path(s); if
nothing exists use the probable paths analysis; run agents and gather feedback;
analyze, score, commit all to brain; measure improvement or slippage; commit;
inform next actions; repeat."

That maps onto three researched, cited frameworks (docs/strategy/
ONE_LIVE_CONSTRUCTION_AND_RCA_v1.md):

  * CASE-BASED REASONING — Retrieve, Reuse, Revise, Retain (Aamodt & Plaza; the
    LLM-agent CBR reviews arXiv:2504.06943). "check brain for green examples" =
    RETRIEVE; "select the most likely success path" = REUSE; running+adapting =
    REVISE; "commit all to brain" = RETAIN.
  * REFLEXION — after a failure, write a post-mortem and feed it to the next
    attempt (here: an RCA committed to the brain, retrieved as a red path to
    avoid). 91% vs 80% pass@1 on HumanEval with nothing but a text memory.
  * PDCA (Deming) — Plan → Do → Check → Act, the outer improvement wheel;
    "measure improvement or slippage" is the Check that gates the next Act.

The BRAIN is the memory that makes it compound: successes and root causes both
persist, so each pass plans from more experience than the last. This module is
the planner/recorder; the "run agents" step plugs in brain/pipeline.run_pipeline
(or any executor). Pure/deterministic given the graph — the learning lives in the
data, not in hidden state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from brain.graph import Graph
from brain.rca import RootCause
from brain.schema import AgentRun, EdgeType, Evaluation, Metric, NodeType

_OUTCOME_RUBRIC_PREFIX = "outcome"
_SCORE_METRIC_PREFIX = "score"
_CONSTRUCT_AGENT_PREFIX = "construct"


@dataclass
class Objective:
    """Step 1 — confirm vision, goals, specific objectives. `objective_class` is
    the retrieval key: runs sharing a class pool their experience."""

    vision: str
    goal: str
    objective_class: str
    success_criteria: str = ""


@dataclass
class CandidatePath:
    """A probable path with its green/red assessment. `est_success` is the
    analyst's/probable-paths prior in [0,1]; `risks` names the failure modes
    (matched against prior RCA classes to down-weight red paths)."""

    name: str
    description: str
    est_success: float
    risks: List[str] = field(default_factory=list)


@dataclass
class GreenExample:
    path_name: str
    score: float
    run_id: str


@dataclass
class Plan:
    """Step 4/5 output — the selected path, why, and the experience behind it."""

    objective: Objective
    selected: CandidatePath
    score: float                      # experience-adjusted success estimate
    alternatives: List[CandidatePath]
    green_precedents: List[GreenExample]
    red_classes_to_avoid: List[str]
    reused_precedent: bool            # True = Reuse of a prior success; False = fresh
    rationale: str


@dataclass
class Outcome:
    """Step 7-9 — what happened, committed, with the improvement/slippage verdict
    and the next actions it implies."""

    run_id: str
    success: bool
    score: float
    prior_score: Optional[float]
    delta: Optional[float]
    trend: str                        # 'improving' | 'slipping' | 'flat' | 'first'
    root_cause: Optional[RootCause]
    next_actions: List[str]


# ── Retrieve (CBR) ───────────────────────────────────────────────────────────

def retrieve_green_examples(graph: Graph, objective_class: str) -> List[GreenExample]:
    """RETRIEVE: prior SUCCESSFUL runs for this objective class, best score first.
    "check brain for existing green examples/successes." """
    agent = f"{_CONSTRUCT_AGENT_PREFIX}:{objective_class}"
    outcome_rubric = f"{_OUTCOME_RUBRIC_PREFIX}:{objective_class}"
    score_metric = f"{_SCORE_METRIC_PREFIX}:{objective_class}"

    # run_id -> path name (from the AgentRun.objective we stamped: "path=<name>")
    run_path = {}
    for run in graph.nodes_of_type(NodeType.AGENT_RUN):
        if getattr(run, "agent", "") == agent and not run.superseded:
            obj = getattr(run, "objective", "") or ""
            run_path[run.id] = obj.split("path=", 1)[-1] if "path=" in obj else obj
    # run_id -> score (latest metric per run via its DERIVED_FROM link)
    run_score = {}
    for m in graph.nodes_of_type(NodeType.METRIC):
        if getattr(m, "name", "") == score_metric and not m.superseded:
            for e in graph.edges_of(m.id):
                if e.edge_type == EdgeType.DERIVED_FROM and e.src == m.id and e.dst in run_path:
                    run_score[e.dst] = m.value
    greens: List[GreenExample] = []
    for ev in graph.nodes_of_type(NodeType.EVALUATION):
        if (getattr(ev, "rubric", "") == outcome_rubric
                and getattr(ev, "verdict", "") == "success"
                and not ev.superseded
                and ev.target_id in run_path):
            greens.append(GreenExample(
                path_name=run_path[ev.target_id],
                score=run_score.get(ev.target_id, 1.0),
                run_id=ev.target_id,
            ))
    greens.sort(key=lambda g: g.score, reverse=True)
    return greens


def retrieve_red_classes(graph: Graph, objective_class: str) -> List[str]:
    """RETRIEVE the red side: systemic root-cause CLASSES seen on this objective
    class before (from committed RCAs), so planning can steer around them
    (Reflexion: the prior post-mortem informs the next attempt)."""
    seen = []
    for ev in graph.nodes_of_type(NodeType.EVALUATION):
        rubric = getattr(ev, "rubric", "")
        if rubric.startswith("rca:") and not ev.superseded:
            # Only count RCAs recorded against a failing run of THIS class.
            cls = rubric.split("rca:", 1)[-1]
            if cls not in seen:
                seen.append(cls)
    return seen


# ── Reuse / select (CBR) ─────────────────────────────────────────────────────

def plan(graph: Graph, objective: Objective, candidates: List[CandidatePath]) -> Plan:
    """Steps 2-5: assess green/red paths, RETRIEVE prior successes, REUSE the best
    precedent, else fall back to the probable-paths analysis.

    Scoring: a candidate starts at its probable-paths `est_success`. If a prior
    GREEN example used the same path, its estimate is pulled toward that proven
    score (experience beats a prior). If any of its `risks` names a class that has
    a committed RCA, it is penalized (a known red path). The highest adjusted
    score wins; ties break toward a reused precedent (proven > speculative).
    """
    if not candidates:
        raise ValueError("plan needs at least one probable path to assess.")
    greens = retrieve_green_examples(graph, objective.objective_class)
    green_by_path = {g.path_name: g for g in greens}
    red_classes = set(retrieve_red_classes(graph, objective.objective_class))

    scored = []
    for c in candidates:
        score = max(0.0, min(1.0, c.est_success))
        reused = False
        if c.name in green_by_path:
            # Reuse: blend toward the proven score (weight experience 0.7).
            score = 0.3 * score + 0.7 * green_by_path[c.name].score
            reused = True
        # Penalize a path whose named risks are known red classes.
        if any(_risk_matches(r, red_classes) for r in c.risks):
            score *= 0.5
        scored.append((score, reused, c))

    # Highest score; tie -> reused precedent first, then higher raw est_success.
    scored.sort(key=lambda t: (t[0], t[1], t[2].est_success), reverse=True)
    best_score, best_reused, best = scored[0]

    if greens:
        rationale = (f"REUSE of prior success on path {best.name!r} "
                     f"(best precedent scored {green_by_path.get(best.name).score:.2f})"
                     if best_reused else
                     f"no prior success used this path; selected {best.name!r} on its "
                     f"probable-paths estimate, adjusted for known red classes")
    else:
        rationale = (f"no green precedent in the brain for class "
                     f"{objective.objective_class!r} — selected {best.name!r} from the "
                     f"probable-paths analysis (first pass; this run becomes the seed)")

    return Plan(
        objective=objective,
        selected=best,
        score=best_score,
        alternatives=[c for _, _, c in scored[1:]],
        green_precedents=greens,
        red_classes_to_avoid=sorted(red_classes),
        reused_precedent=best_reused,
        rationale=rationale,
    )


def _risk_matches(risk: str, red_classes: set) -> bool:
    r = (risk or "").strip().lower()
    return any(r == rc or r in rc or rc in r for rc in red_classes if rc)


# ── Retain + measure (CBR + PDCA Check) ──────────────────────────────────────

class BlockedGateError(Exception):
    """Raised when a run is being recorded as SUCCESS while a required CI gate is
    blocked. Founder catch (2026-07-25): a merge-blocking test failure was
    reported for hours as "pre-existing" — so the loop must not be able to write
    "success" over a red gate. See tools/blocking_failure_check.py."""


def blocked_gates() -> List[str]:
    """The required checks currently turned RED by a failing test, via
    tools/blocking_failure_check.py (which reads CI to find full-suite gates).

    Returns [] when nothing is blocked. Never raises: if the checker cannot run
    (missing interpreter/tool), it returns [] and the caller's own gates still
    apply — this is a guard on OVERSTATEMENT, not a second test runner.
    """
    import os
    import subprocess
    import sys
    # RECURSION GUARD: the checker runs the full pytest suite, and that suite
    # contains tests of this very function. Without this, a test that records a
    # success would spawn a suite that spawns another suite. The subprocess
    # inherits the flag, so any nested call short-circuits.
    if os.environ.get("ONELIVE_IN_GATE_CHECK") == "1":
        return []
    root = __import__("pathlib").Path(__file__).resolve().parent.parent
    tool = root / "tools" / "blocking_failure_check.py"
    if not tool.exists():
        return []
    env = dict(os.environ, ONELIVE_IN_GATE_CHECK="1")
    try:
        proc = subprocess.run([sys.executable, str(tool)], cwd=str(root),
                              capture_output=True, text=True, timeout=900, env=env)
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode == 0:
        return []
    # The checker prints the blocked gate list on the "These turn the following
    # REQUIRED check(s) RED:" line.
    for ln in (proc.stderr or "").splitlines():
        if "REQUIRED check(s) RED:" in ln:
            return [g.strip() for g in ln.split("RED:", 1)[1].split(",") if g.strip()]
    return ["<unnamed gate>"]


def record_outcome(
    graph: Graph,
    objective: Objective,
    plan_used: Plan,
    *,
    success: bool,
    score: float,
    notes: str = "",
    root_cause: Optional[RootCause] = None,
    check_gates: bool = True,
) -> Outcome:
    """Steps 7-10: RETAIN the run + its score to the brain, measure improvement or
    slippage vs the prior run of this class, and emit the next actions.

    Commits an AgentRun (stamped with the path so future RETRIEVE can match), an
    outcome Evaluation, and a score Metric linked to the run. On failure, a
    root_cause (from rca.analyze) should be attached — it is already in the brain
    and will surface via retrieve_red_classes next pass (Reflexion). `trend`
    compares this score to the immediately prior one for the class.
    """
    score = max(0.0, min(1.0, score))

    # PHYSICS, not a reminder: a run cannot be RETAINED as a success while a
    # required CI gate is red. This is the 2026-07-25 lesson made structural —
    # "pre-existing" and "recorded as R-###" cannot talk their way past it,
    # because the check is a subprocess reading CI, not a judgement.
    if success and check_gates:
        blocked = blocked_gates()
        if blocked:
            raise BlockedGateError(
                "refusing to record SUCCESS while required check(s) are RED: "
                f"{', '.join(blocked)}. A failing test reds every full-suite gate, "
                "so this work is BLOCKED, not done. Fix it (or record success=False "
                "with the root cause). Age ('pre-existing') and a RECORD.md "
                "R-### tag are NOT exemptions."
            )

    prior_scores = _class_scores(graph, objective.objective_class)
    prior = prior_scores[-1] if prior_scores else None

    run = graph.add_agent_run(AgentRun(
        agent=f"{_CONSTRUCT_AGENT_PREFIX}:{objective.objective_class}",
        objective=f"path={plan_used.selected.name}",
        status="succeeded" if success else "failed",
    ))
    graph.add_evaluation(Evaluation(
        rubric=f"{_OUTCOME_RUBRIC_PREFIX}:{objective.objective_class}",
        verdict="success" if success else "failure",
        target_id=run.id,
        notes=notes or plan_used.rationale,
    ))
    metric = graph.add_metric(Metric(
        name=f"{_SCORE_METRIC_PREFIX}:{objective.objective_class}",
        value=score, unit="0..1",
    ))
    graph.add_edge(metric.id, run.id, EdgeType.DERIVED_FROM)

    delta = None if prior is None else round(score - prior, 6)
    if prior is None:
        trend = "first"
    elif delta > 0:
        trend = "improving"
    elif delta < 0:
        trend = "slipping"
    else:
        trend = "flat"

    next_actions = _next_actions(success, trend, plan_used, root_cause, score)
    return Outcome(
        run_id=run.id, success=success, score=score, prior_score=prior,
        delta=delta, trend=trend, root_cause=root_cause, next_actions=next_actions,
    )


def _class_scores(graph: Graph, objective_class: str) -> List[float]:
    """Every recorded score for this class, in commit order (created_at) — the
    improvement/slippage series."""
    name = f"{_SCORE_METRIC_PREFIX}:{objective_class}"
    metrics = [m for m in graph.nodes_of_type(NodeType.METRIC)
               if getattr(m, "name", "") == name and not m.superseded]
    metrics.sort(key=lambda m: m.created_at)
    return [m.value for m in metrics]


def improvement(graph: Graph, objective_class: str) -> dict:
    """The measured trajectory for a class: the score series, the latest delta,
    and a direction. "measure improvement or slippage." """
    scores = _class_scores(graph, objective_class)
    if not scores:
        return {"series": [], "latest": None, "delta": None, "direction": "no-data"}
    delta = None if len(scores) < 2 else round(scores[-1] - scores[-2], 6)
    direction = ("first" if delta is None
                 else "improving" if delta > 0
                 else "slipping" if delta < 0 else "flat")
    return {"series": scores, "latest": scores[-1], "delta": delta, "direction": direction}


# A run can "succeed" (it completed, nothing broke) and still be a WEAK result.
# Below this score, do NOT tell the next pass to reinforce the path — a thin
# outcome reported as a win is the overstatement class this loop exists to catch.
# (Found 2026-07-25 by actually running the loop: the local-coverage pass scored
# 0.35 with 16 of 18 sources yielding zero, and the loop still said "worked".)
WEAK_SUCCESS_SCORE = 0.60


def _next_actions(success, trend, plan_used, root_cause, score=1.0) -> List[str]:
    actions: List[str] = []
    if success and score < WEAK_SUCCESS_SCORE:
        actions.append(
            f"WEAK RESULT ({score:.2f}): path {plan_used.selected.name!r} completed but "
            f"under-delivered — do NOT reinforce it. Treat the gap as the finding and "
            f"try a higher-ceiling path (or fix this one's bottleneck) next pass")
    elif success and trend in ("improving", "first", "flat"):
        actions.append(
            f"reinforce: path {plan_used.selected.name!r} worked — it is now a green "
            f"precedent future planning will Reuse for this class")
        if trend == "flat":
            actions.append("flat score: look for a higher-ceiling path next pass, "
                          "not just repetition")
    if not success:
        actions.append(f"path {plan_used.selected.name!r} failed — do NOT Reuse it "
                       f"until the root cause is addressed")
        if root_cause is not None:
            actions.append(f"apply preventive control: {root_cause.preventive_action}")
            if root_cause.is_recurring_finding:
                actions.append(
                    f"§1 ESCALATION: class {root_cause.category.value!r} has recurred "
                    f">{root_cause.recurrence_count} times — root-cause the PROCESS, "
                    f"not just this instance")
    if trend == "slipping" and success:
        actions.append("slippage despite success: score fell vs the prior run — "
                       "investigate what regressed before the next pass")
    return actions
