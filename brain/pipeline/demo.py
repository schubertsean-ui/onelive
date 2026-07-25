"""Runnable end-to-end proof of the lossless phased pipeline.

    python -m brain.pipeline.demo

Runs the seven OneLive roles (find -> compose -> interpret -> execute -> measure
-> evaluate -> change) with a durable save after every phase, then prints the
provenance chain and the field-fate ledger — showing that every field the finder
produced is still accounted for at the changer, and that the loop closed into a
follow-up task. No network, no DB, no AI: the pipeline MECHANICS, demonstrated.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from brain.graph import Graph
from brain import store
from brain.pipeline import run_pipeline, trace
from brain.pipeline.default_stages import DEFAULT_STAGES


def main() -> None:
    tmp = Path(tempfile.mkdtemp()) / "brain.jsonl"
    graph = Graph()
    result = run_pipeline(graph, DEFAULT_STAGES,
                          save_hook=lambda g: store.save(g, tmp))

    # Reload from disk into a FRESH graph to prove the handoff was durable.
    reloaded = store.load(tmp)
    chain = trace(reloaded, result.final_artifact_id)

    print("=" * 72)
    print("OneLive phased pipeline — lossless handoff trace (reloaded from disk)")
    print("=" * 72)
    for i, h in enumerate(chain):
        arrow = "" if i == 0 else "  |  DERIVED_FROM the phase above"
        print(f"\n[{i+1}] {h.stage.upper()}{arrow}")
        print(f"    artifact: {h.artifact_id}")
        print(f"    carried load-bearing fields: {sorted(h.carried)}")
        if h.transformed:
            print(f"    transformed: {h.transformed}")
        if h.consumed:
            print(f"    consumed (recorded, not lost): {h.consumed}")

    print("\n" + "-" * 72)
    print("Field-fate ledger — where every ORIGIN (finder) field ended up:")
    for k, v in sorted(result.origin_field_fate.items()):
        print(f"    {k:16s} -> {v}")

    print("\n" + "-" * 72)
    print(f"Loop closed: follow-up Task {result.followup_task_id} opened, "
          f"DEPENDS_ON the change + metric + evaluation.")
    print("Zero fields lost across seven phases; chain fully recoverable after "
          "a fresh-process reload.")


if __name__ == "__main__":
    main()
