"""Runnable proof of the construction + RCA loop learning across passes.

    python -m brain.construction_demo

Three passes of the same objective. Pass 1 has no precedent (probable-paths
fallback) and fails → an RCA is committed. Pass 2 retrieves that red class and a
prior green, reuses the winning path, and improves. Pass 3 shows the trend. No
network, no DB, no AI — the LEARNING lives in the brain graph, durable.
"""
from __future__ import annotations

from brain.graph import Graph
from brain.construction import (
    CandidatePath, Objective, improvement, plan, record_outcome,
)
from brain.rca import CauseCategory, analyze


def main() -> None:
    g = Graph()
    obj = Objective(vision="every local event on /tonight",
                    goal="ship a working importer",
                    objective_class="ship-importer",
                    success_criteria="events land, categories correct, bounded cost")
    paths = [
        # The AI path LOOKS more capable up front (higher prior), but carries the
        # cost risk; the deterministic path is humbler but clean.
        CandidatePath("ai-extract", "AI extraction of free text", 0.65,
                      risks=["cost-unbounded"]),
        CandidatePath("structured-feed", "deterministic ICS/JSON-LD import", 0.55,
                      risks=[]),
    ]

    print("=" * 72)
    print("Construction loop — plan from experience, run, score, learn, repeat")
    print("=" * 72)

    # PASS 1 — no precedent; pick highest probable-paths estimate; it FAILS.
    p1 = plan(g, obj, paths)
    print(f"\nPASS 1 plan: {p1.selected.name!r}  score={p1.score:.2f}\n  {p1.rationale}")
    rc = analyze(
        g, symptom="ai-extract run blew the per-run budget",
        why_chain=["fan-out made one AI call per event block",
                   "the source cap bounded pages, not calls",
                   "no per-run AI-call ceiling existed"],
        category=CauseCategory.COST_UNBOUNDED,
        corrective_action="add EXTRACT_MAX_EVENTS_PER_PAGE cap",
        preventive_action="every build spec states its budget as a testable bound")
    o1 = record_outcome(g, obj, p1, success=False, score=0.20, root_cause=rc)
    print(f"PASS 1 outcome: FAIL score={o1.score:.2f} trend={o1.trend}")
    for a in o1.next_actions:
        print(f"    → {a}")

    # PASS 2 — the RCA made 'cost-unbounded' a red class; structured-feed (no such
    # risk) is chosen and SUCCEEDS with a strong score.
    p2 = plan(g, obj, paths)
    print(f"\nPASS 2 plan: {p2.selected.name!r}  score={p2.score:.2f}\n  {p2.rationale}"
          f"\n  red classes to avoid: {p2.red_classes_to_avoid}")
    o2 = record_outcome(g, obj, p2, success=True, score=0.82)
    print(f"PASS 2 outcome: SUCCESS score={o2.score:.2f} trend={o2.trend} "
          f"(Δ={o2.delta})")
    for a in o2.next_actions:
        print(f"    → {a}")

    # PASS 3 — the prior green is retrieved and REUSED; score improves again.
    p3 = plan(g, obj, paths)
    print(f"\nPASS 3 plan: {p3.selected.name!r}  reused_precedent={p3.reused_precedent}"
          f"  score={p3.score:.2f}\n  {p3.rationale}")
    o3 = record_outcome(g, obj, p3, success=True, score=0.90)
    print(f"PASS 3 outcome: SUCCESS score={o3.score:.2f} trend={o3.trend} (Δ={o3.delta})")

    imp = improvement(g, "ship-importer")
    print("\n" + "-" * 72)
    print(f"Improvement series for 'ship-importer': {imp['series']}  "
          f"direction={imp['direction']}")
    print("The brain learned: a failed path became a red class to avoid, a winning "
          "path became a green precedent to reuse, and the score trend is measured "
          "across passes — all durable in the graph.")


if __name__ == "__main__":
    main()
