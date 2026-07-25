"""Root-cause analysis engine — get to the ROOT of a failure, systemically, and
make recurrence a mechanical signal instead of a vibe.

Founder directive (2026-07-25): "build in a root cause analysis — the world
leading, after researching it — to get at the root of your failures."

The synthesis (researched, cited in docs/strategy/ONE_LIVE_CONSTRUCTION_AND_RCA_v1.md):

  * 5 WHYS as the causal spine — chain "why did this happen?" until a ROOT
    (a cause with no deeper *controllable* cause) is reached. (fivewhys.ai;
    Kepner-Tregoe.)
  * ISHIKAWA / blameless SRE for the CATEGORY — the root is classified into a
    SYSTEMIC class (missing test, ambiguous spec, tooling gap, unbounded cost,
    …), never "the agent was careless." Google SRE: dig past human error to
    tooling gaps, missing tests, unclear ownership; a standard template enables
    TREND analysis over root-cause TYPES. (sre.google/sre-book/postmortem-culture.)
  * KEPNER-TREGOE "what changed" for regressions — a `what_changed` field for the
    "it worked, then it didn't" case.
  * RECURRENCE TRENDING — every root is committed to the brain, so the count of a
    CLASS is queryable. This is OPERATING_RULES §1 ("a repeated error is a
    finding, not a rhythm") made mechanical: >2 of a class raises an escalation
    flag automatically.

Each analysis is COMMITTED to the knowledge-graph brain (an inference Claim for
the root + an Evaluation carrying the category + chain), linked to the failing
artifact/run, so future construction planning can RETRIEVE it and avoid the red
path. Pure/deterministic given its inputs — it structures, persists, and trends
the analyst's causal chain; it does not invent causes.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import List, Optional

from brain.graph import Graph
from brain.schema import Claim, Evaluation, NodeType

# The recurrence threshold from OPERATING_RULES §1: an error appearing MORE THAN
# TWICE is a finding requiring a recorded determination. The 3rd occurrence trips it.
RECURRENCE_FINDING_THRESHOLD = 2

_RCA_RUBRIC_PREFIX = "rca"


class CauseCategory(enum.Enum):
    """Systemic root-cause classes (Ishikawa-for-software + our own documented
    recurring classes from docs/memory/gotchas). Blameless by construction: every
    value names a SYSTEM property, never a person/agent. Extend deliberately —
    a new class is a new trend line."""

    OVERSTATEMENT_BUILT_AS_LIVE = "overstatement-built-as-live"
    GREENFIELD_ASSUMPTION = "greenfield-assumption"      # didn't read prior work
    COST_UNBOUNDED = "cost-unbounded"
    MISSING_TEST = "missing-test"
    AMBIGUOUS_SPEC = "ambiguous-spec"
    TOOLING_GAP = "tooling-gap"
    UNCLEAR_OWNERSHIP = "unclear-ownership"
    PROCESS_GAP = "process-gap"
    REGRESSION_WHAT_CHANGED = "regression-what-changed"  # Kepner-Tregoe
    ROUTINIZED_RECURRING = "routinized-recurring-error"  # the §1 meta-class
    DEPENDENCY_OR_UPSTREAM = "dependency-or-upstream"
    OTHER = "other"


@dataclass
class RootCause:
    """The verdict of an analysis: the symptom, the 5-whys chain to the root, the
    systemic category, the corrective (fix this instance) + preventive (stop the
    class) actions, and the recurrence signal."""

    symptom: str
    why_chain: List[str]
    root: str
    category: CauseCategory
    corrective_action: str
    preventive_action: str
    what_changed: Optional[str] = None
    recurrence_count: int = 0          # prior roots of this class before this one
    is_recurring_finding: bool = False  # count crossed the §1 threshold
    claim_id: str = ""
    evaluation_id: str = ""


def _rca_rubric(category: CauseCategory) -> str:
    return f"{_RCA_RUBRIC_PREFIX}:{category.value}"


def class_frequency(graph: Graph, category: CauseCategory) -> int:
    """How many roots of this systemic class the brain already holds. The trend
    line Google SRE's template exists to produce — here, queryable in O(evals)."""
    rubric = _rca_rubric(category)
    return sum(
        1 for n in graph.nodes_of_type(NodeType.EVALUATION)
        if getattr(n, "rubric", "") == rubric and not n.superseded
    )


def analyze(
    graph: Graph,
    *,
    symptom: str,
    why_chain: List[str],
    category: CauseCategory,
    corrective_action: str,
    preventive_action: str,
    what_changed: Optional[str] = None,
    failing_artifact_id: Optional[str] = None,
    analysis_run_id: Optional[str] = None,
) -> RootCause:
    """Run one blameless RCA and COMMIT it to the brain.

    Enforces the discipline (fail closed, so a shallow analysis cannot be
    recorded as a real one):
      * the 5-whys chain must have >= 2 links and terminate at `root` (the last
        link) — a one-step "why" is a symptom, not a root;
      * `category` must be a systemic CauseCategory (the type system guarantees
        blamelessness — there is no "human error" value);
      * `preventive_action` (stop the CLASS) is required, not just a corrective
        (fix the instance) — the SRE lesson that fixing the token without the
        systemic gap guarantees recurrence.

    Persists an inference Claim (the root) + an Evaluation (category + chain) and,
    when given, links them to the failing artifact and the analysis run. Computes
    the recurrence count BEFORE committing this one, and flags the §1 finding when
    the class crosses the threshold.
    """
    if len([w for w in why_chain if w and w.strip()]) < 2:
        raise ValueError(
            "RCA needs a 5-whys chain of at least 2 links — a single 'why' finds a "
            "symptom, not a root. Chain 'why did that happen?' until a controllable "
            "root remains."
        )
    if not corrective_action.strip():
        raise ValueError("RCA requires a corrective action (fix this instance).")
    if not preventive_action.strip():
        raise ValueError(
            "RCA requires a PREVENTIVE action (stop the whole class) — a corrective "
            "fix without a preventive control guarantees recurrence (SRE)."
        )
    if not isinstance(category, CauseCategory):
        raise TypeError("category must be a systemic CauseCategory (blameless).")

    root = root_of(why_chain)
    prior = class_frequency(graph, category)
    is_finding = prior >= RECURRENCE_FINDING_THRESHOLD

    # Commit the root as an INFERENCE claim (it is reasoned from evidence, not a
    # sourced fact) — satisfies invariant 1 without a Source node.
    claim = graph.add_claim(Claim(
        text=f"ROOT[{category.value}]: {root}",
        inference=True,
    ))
    # The Evaluation carries the category (in its rubric, for O(evals) trending),
    # the whole chain, and the preventive control. target = the failing artifact
    # when known, so the trace links defect -> its root.
    notes = _format_notes(symptom, why_chain, corrective_action,
                          preventive_action, what_changed, prior, is_finding)
    evaluation = graph.add_evaluation(Evaluation(
        rubric=_rca_rubric(category),
        verdict="root-cause",
        target_id=failing_artifact_id if (failing_artifact_id and graph.has(failing_artifact_id)) else None,
        notes=notes,
    ))
    # Tie the root claim to the analysis run when provided (provenance).
    if analysis_run_id and graph.has(analysis_run_id):
        from brain.schema import EdgeType
        graph.add_edge(claim.id, analysis_run_id, EdgeType.DERIVED_FROM)

    return RootCause(
        symptom=symptom,
        why_chain=list(why_chain),
        root=root,
        category=category,
        corrective_action=corrective_action,
        preventive_action=preventive_action,
        what_changed=what_changed,
        recurrence_count=prior,
        is_recurring_finding=is_finding,
        claim_id=claim.id,
        evaluation_id=evaluation.id,
    )


def root_of(why_chain: List[str]) -> str:
    """The root is the terminal link of the causal chain (the deepest controllable
    cause the analyst reached)."""
    live = [w.strip() for w in why_chain if w and w.strip()]
    return live[-1] if live else ""


def _format_notes(symptom, why_chain, corrective, preventive, what_changed,
                  prior, is_finding) -> str:
    lines = [f"SYMPTOM: {symptom}"]
    for i, w in enumerate(why_chain, 1):
        lines.append(f"  WHY{i}: {w}")
    lines.append(f"CORRECTIVE (this instance): {corrective}")
    lines.append(f"PREVENTIVE (the class): {preventive}")
    if what_changed:
        lines.append(f"WHAT CHANGED (Kepner-Tregoe): {what_changed}")
    lines.append(f"PRIOR OCCURRENCES OF CLASS: {prior}"
                 + ("  ⚠ §1 RECURRING FINDING — escalate" if is_finding else ""))
    return "\n".join(lines)
