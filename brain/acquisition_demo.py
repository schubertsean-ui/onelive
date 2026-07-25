"""Runnable proof of SHARED, DURABLE acquisition learning: `python -m brain.acquisition_demo`.

Greppable summary: seeds the toolkit from the catalog, has AGENT A read a
source's recipe BEFORE acquiring, "acquire" (simulated — no network), and
RECORD the outcome so the recipe and the technique improve; saves to disk;
then RELOADS into a FRESH toolkit that never saw the first and has AGENT B read
the IMPROVED recipe straight off disk. The point the founder can SEE: agent B
inherited agent A's learning without ever talking to it — the common toolkit
enlarged and persisted. Also shows the moved-page re-discovery trigger and the
legal rail rejecting a bypass recipe.

No network, deterministic (timestamps are fixed), stdlib + brain only.
"""
from __future__ import annotations

import pathlib
import tempfile

from brain.acquisition import AcquisitionError, AcquisitionRecipe, AcquisitionToolkit
from brain.seed_acquisition import seed

_BAR = "=" * 74
# A fixed "clock" so the demo is byte-deterministic across runs.
_T0 = 1_753_000_000.0


def _show_recipe(label: str, r: AcquisitionRecipe) -> None:
    print(f"  {label}")
    print(f"    source_id       : {r.source_id}  ({r.source_name})")
    print(f"    access_method   : {r.access_method}   structured_format: {r.structured_format}")
    print(f"    calendar_url    : {r.calendar_url or '(none)'}"
          f"{'  [homepage-only, real listing URL is a learning step]' if r.calendar_url_is_homepage else ''}")
    print(f"    reliability     : {r.reliability}   median_yield: {r.median_yield}"
          f"   attempts: {r.attempts}   confidence: {r.confidence}")
    print(f"    needs_rediscovery: {r.needs_rediscovery}   last_yield: {r.last_yield}"
          f"   learned_by_run: {r.learned_by_run or '(seed)'}")


def main() -> int:
    print(_BAR)
    print("ONE LIVE acquisition toolkit — the agent forgets, the toolkit does not.")
    print(_BAR)

    # --- seed the shared toolkit from the catalog + technique library ---------
    kit = AcquisitionToolkit()
    summary = seed(kit)
    print(f"\nSeeded from the master sources catalog:")
    print(f"  recipes:    {summary['recipes']}  (new this run: {summary['recipes_new']})")
    print(f"  techniques: {summary['techniques']}  (new this run: {summary['techniques_new']})")

    target = "cheer_up_charlies"  # a first-party venue calendar in the catalog

    # --- AGENT A: READ before acquiring --------------------------------------
    print(f"\n--- AGENT A reads the recipe BEFORE acquiring '{target}' ---")
    before = kit.recipe_for(target)
    assert before is not None, "seed should have produced this recipe"
    _show_recipe("recipe (as seeded):", before)

    # Which technique should agent A reach for on a Squarespace/JSON-LD page?
    sig = "squarespace"
    chosen = kit.best_technique(sig)
    print(f"\n  best_technique(signal={sig!r}) -> {chosen.name} "
          f"(rate={round(chosen.effective_success_rate(), 3)}, cost={chosen.cost_hint})")

    # --- AGENT A: "acquire" (simulated) and RECORD the outcome ---------------
    print("\n--- AGENT A acquires (simulated) and RECORDS the outcome ---")
    kit.record_outcome(
        target, run_id="agent-A-001", method=before.access_method,
        technique="parse-jsonld-graph-event", yield_count=23, success=True,
        cost="low", notes="found JSON-LD @graph with 23 MusicEvent nodes", at=_T0)
    improved = kit.recipe_for(target)
    _show_recipe("recipe (after AGENT A's successful acquire):", improved)
    print(f"    -> reliability {before.reliability} -> {improved.reliability}, "
          f"median_yield {before.median_yield} -> {improved.median_yield}, "
          f"version {before.version} -> {improved.version}")

    # --- persist, then reload into a FRESH toolkit (the process boundary) -----
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "acquisition_brain.jsonl"
        kit.save(path)
        print(f"\nSaved shared toolkit to disk: {path} ({path.stat().st_size} bytes)")
        print("--- process boundary: a DIFFERENT agent loads the toolkit from disk ---")
        kit2 = AcquisitionToolkit.load(path)

    # --- AGENT B: reads the IMPROVED recipe it never learned itself -----------
    print("\n--- AGENT B (fresh process) reads the recipe for the SAME source ---")
    inherited = kit2.recipe_for(target)
    _show_recipe("recipe AGENT B sees (inherited from AGENT A, off disk):", inherited)
    assert inherited.reliability == improved.reliability
    assert inherited.median_yield == improved.median_yield == 23.0
    assert inherited.attempts == 1
    print("  PROOF: agent B inherited agent A's yield + reliability without ever")
    print("         meeting agent A — the shared toolkit persisted and enlarged.")

    # Technique stats are shared too: agent A's success moved the JSON-LD rate.
    tj = kit2.technique("parse-jsonld-graph-event")
    print(f"\n  shared technique 'parse-jsonld-graph-event': attempts={tj.attempts}, "
          f"successes={tj.successes}, rate={round(tj.effective_success_rate(), 3)}")

    # --- AGENT B: the moved-page re-discovery trigger ------------------------
    print("\n--- AGENT B hits a moved/changed page: two empty acquires in a row ---")
    kit2.record_outcome(target, run_id="agent-B-001", method=inherited.access_method,
                        technique="parse-jsonld-graph-event", yield_count=0,
                        success=False, notes="AI_EXTRACT_ZERO_EVENTS_SOURCE_MAY_HAVE_MOVED",
                        at=_T0 + 86400)
    mid = kit2.recipe_for(target)
    print(f"  after 1 empty: needs_rediscovery={mid.needs_rediscovery}, "
          f"consecutive_empty={mid.consecutive_empty}, confidence={mid.confidence}")
    kit2.record_outcome(target, run_id="agent-B-001", method=inherited.access_method,
                        technique="parse-jsonld-graph-event", yield_count=0,
                        success=False, notes="AI_EXTRACT_ZERO_EVENTS_SOURCE_MAY_HAVE_MOVED",
                        at=_T0 + 172800)
    moved = kit2.recipe_for(target)
    print(f"  after 2 empty: needs_rediscovery={moved.needs_rediscovery}, "
          f"consecutive_empty={moved.consecutive_empty}, confidence={moved.confidence}")
    assert moved.needs_rediscovery is True
    print("  PROOF: repeated empty yield flipped the recipe to needs_rediscovery=True")
    print("         and lowered confidence — the moved-page trigger fired.")

    # --- the legal rail: a bypass recipe can never be stored -----------------
    print("\n--- the legal rail: a login/paywall-bypass recipe is HARD-REJECTED ---")
    try:
        kit2.register_recipe(
            AcquisitionRecipe(source_id="evil_source", access_method="plain_http",
                              plan_note="log in with a member account and scrape behind the paywall"),
            run_id="agent-B-001")
        print("  ERROR: a bypass recipe was accepted — this must never happen!")
        return 1
    except AcquisitionError as exc:
        print(f"  rejected loudly, as required: {exc}")

    print("\nThe toolkit learned, shared, and stayed honest. It did not forget.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
