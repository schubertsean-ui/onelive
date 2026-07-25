"""Proof tests for the shared, learning acquisition toolkit (brain/acquisition.py).

Greppable summary: each test PROVES one property the founder asked to see —
recipes and techniques round-trip through the brain store (durable + shared),
record_outcome improves a recipe's reliability + median_yield and a technique's
success stats, repeated empty yield flips needs_rediscovery, a login/paywall
bypass recipe is HARD-REJECTED, best_technique returns the higher-success
method, and the brain's four write invariants still hold (a recipe/technique
claim cannot enter the graph without a Source and a run).

Pure-logic tests: no database, no network.
"""
import pathlib

import pytest

from brain import store
from brain.graph import Graph, GraphInvariantError
from brain.schema import Claim, EdgeType, NodeType
from brain.acquisition import (
    AcquisitionError,
    AcquisitionRecipe,
    AcquisitionTechnique,
    AcquisitionToolkit,
    _assert_recipe_legal,
)
from brain.seed_acquisition import recipe_from_source, seed, technique_library


# --- helpers ------------------------------------------------------------------
def _kit_with_recipe(**over):
    kit = AcquisitionToolkit()
    base = dict(source_id="mohawk", source_name="Mohawk", calendar_url="https://m/cal",
                access_method="ics_feed", structured_format="ics", reliability=0.5,
                confidence=0.5)
    base.update(over)
    kit.register_recipe(AcquisitionRecipe(**base), run_id="run-1",
                        source_uri="catalog.json")
    return kit


def _seed_techniques(kit):
    for t in technique_library():
        kit.register_technique(t, run_id="run-1")


# --- recipe read/write round-trips through the brain store --------------------
def test_recipe_roundtrips_through_the_store(tmp_path: pathlib.Path):
    kit = _kit_with_recipe(access_method="jsonld", structured_format="jsonld",
                           median_yield=0.0)
    kit.record_outcome("mohawk", run_id="run-1", method="jsonld",
                       technique=None, yield_count=12, success=True, at=100.0)

    path = tmp_path / "acq.jsonl"
    kit.save(path)
    # A FRESH toolkit that never saw the original reads it back off disk.
    reloaded = AcquisitionToolkit.load(path)
    r = reloaded.recipe_for("mohawk")
    assert r is not None
    assert r.source_id == "mohawk"
    assert r.access_method == "jsonld"
    assert r.median_yield == 12.0
    assert r.last_yield == 12
    # Full-state identity: serialising both graphs yields identical bytes.
    assert store.dumps(reloaded.g) == store.dumps(kit.g)


def test_unknown_source_reads_as_none():
    kit = AcquisitionToolkit()
    assert kit.recipe_for("never_seen") is None
    assert kit.technique("never_seen") is None


# --- record_outcome improves reliability + median_yield + technique stats -----
def test_record_outcome_improves_reliability_and_median_yield():
    kit = _kit_with_recipe(reliability=0.5, median_yield=0.0)
    r0 = kit.recipe_for("mohawk")
    r1 = kit.record_outcome("mohawk", run_id="run-1", method="ics_feed",
                            technique=None, yield_count=10, success=True, at=1.0)
    assert r1.reliability > r0.reliability          # a success raised reliability
    assert r1.median_yield == 10.0                  # median of [10]
    assert r1.successes == 1 and r1.attempts == 1
    r2 = kit.record_outcome("mohawk", run_id="run-1", method="ics_feed",
                            technique=None, yield_count=20, success=True, at=2.0)
    assert r2.median_yield == 15.0                  # median of [10, 20]
    assert r2.reliability > r1.reliability
    # Each write superseded the prior state claim (invariant 4): exactly one
    # live recipe claim mentions the entity, and the history is retained.
    entity = kit._entity("acquisition_recipe", "mohawk")
    live = [e for e in kit.g.edges_of(entity.id)
            if e.edge_type is EdgeType.MENTIONS and e.dst == entity.id
            and not kit.g.get(e.src).superseded]
    assert len(live) == 1
    superseded = [e for e in kit.g.edges_of(entity.id)
                  if e.edge_type is EdgeType.MENTIONS and e.dst == entity.id
                  and kit.g.get(e.src).superseded]
    assert len(superseded) >= 2                     # seed + first outcome retained


def test_record_outcome_updates_technique_stats():
    kit = _kit_with_recipe()
    _seed_techniques(kit)
    t0 = kit.technique("parse-ics-feed")
    kit.record_outcome("mohawk", run_id="run-1", method="ics_feed",
                       technique="parse-ics-feed", yield_count=5, success=True, at=1.0)
    t1 = kit.technique("parse-ics-feed")
    assert t1.attempts == t0.attempts + 1
    assert t1.successes == t0.successes + 1
    assert t1.effective_success_rate() > t0.effective_success_rate()


def test_record_outcome_on_unknown_source_raises():
    kit = AcquisitionToolkit()
    with pytest.raises(AcquisitionError):
        kit.record_outcome("ghost", run_id="run-1", method="plain_http",
                           technique=None, yield_count=1, success=True)


def test_record_outcome_naming_unknown_technique_raises():
    kit = _kit_with_recipe()
    with pytest.raises(AcquisitionError):
        kit.record_outcome("mohawk", run_id="run-1", method="ics_feed",
                           technique="no-such-technique", yield_count=3, success=True)


# --- repeated empty -> needs_rediscovery flips (moved-page trigger) -----------
def test_repeated_empty_flips_needs_rediscovery():
    kit = _kit_with_recipe(confidence=0.9)
    kit.record_outcome("mohawk", run_id="run-1", method="ics_feed", technique=None,
                       yield_count=0, success=False, at=1.0)
    assert kit.recipe_for("mohawk").needs_rediscovery is False   # one empty: not yet
    r = kit.record_outcome("mohawk", run_id="run-1", method="ics_feed", technique=None,
                           yield_count=0, success=False, at=2.0)
    assert r.needs_rediscovery is True                            # two in a row: flip
    assert r.consecutive_empty == 2
    assert r.confidence < 0.9                                     # confidence dropped


def test_success_after_empties_clears_rediscovery():
    kit = _kit_with_recipe()
    for t in (1.0, 2.0):
        kit.record_outcome("mohawk", run_id="run-1", method="ics_feed", technique=None,
                           yield_count=0, success=False, at=t)
    assert kit.recipe_for("mohawk").needs_rediscovery is True
    r = kit.record_outcome("mohawk", run_id="run-1", method="ics_feed", technique=None,
                           yield_count=7, success=True, at=3.0)
    assert r.needs_rediscovery is False
    assert r.consecutive_empty == 0


def test_success_with_zero_yield_is_not_effective():
    # A mechanical "success" that returned zero events did NOT really succeed.
    kit = _kit_with_recipe()
    kit.record_outcome("mohawk", run_id="run-1", method="ics_feed", technique=None,
                       yield_count=0, success=True, at=1.0)
    r = kit.recipe_for("mohawk")
    assert r.successes == 0
    assert r.consecutive_empty == 1


# --- a recipe can NEVER encode a disallowed method ----------------------------
@pytest.mark.parametrize("bad", [
    dict(access_method="plain_http", plan_note="log in and scrape the member calendar"),
    dict(access_method="plain_http", plan_note="bypass the paywall to read events"),
    dict(access_method="plain_http", plan_note="use stored credentials to sign in"),
    dict(access_method="plain_http", segmentation_hint="solve the captcha then read"),
    dict(access_method="scrape_login"),          # unknown/forbidden method itself
    dict(access_method="plain_http", robots_ok=False),  # ignoring robots
])
def test_bypass_recipe_is_hard_rejected(bad):
    recipe = AcquisitionRecipe(source_id="evil", **bad)
    with pytest.raises(AcquisitionError):
        _assert_recipe_legal(recipe)
    # And it can never be stored through the toolkit either.
    kit = AcquisitionToolkit()
    with pytest.raises(AcquisitionError):
        kit.register_recipe(recipe, run_id="run-1")


def test_legal_rails_note_does_not_false_reject():
    # A recipe whose tos_note/explicitly_disallowed MENTION "login_scraping" as a
    # GUARDRAIL (what NOT to do) is fine — only ACTION fields are scanned.
    recipe = AcquisitionRecipe(
        source_id="mohawk", access_method="ics_feed", structured_format="ics",
        plan_note="read the offered ICS feed",
        tos_note="respect source policy; explicitly disallowed: login_scraping",
        explicitly_disallowed=["login_scraping"])
    _assert_recipe_legal(recipe)  # must NOT raise
    kit = AcquisitionToolkit()
    kit.register_recipe(recipe, run_id="run-1")
    assert kit.recipe_for("mohawk") is not None


def test_seed_maps_catalog_without_illegal_recipes():
    # Every catalog-derived recipe passes the legal rail and uses a safe method.
    kit = AcquisitionToolkit()
    summary = seed(kit)
    assert summary["recipes"] > 60
    for r in kit.all_recipes():
        _assert_recipe_legal(r)                 # raises if any is a bypass
        assert r.robots_ok is True
    # Re-seed is idempotent: no new recipes/techniques the second time.
    summary2 = seed(kit)
    assert summary2["recipes_new"] == 0
    assert summary2["techniques_new"] == 0


def test_seed_marks_benchmark_channels_not_automated():
    kit = AcquisitionToolkit()
    seed(kit)
    bing = kit.recipe_for("bing_search")        # a benchmark-only source
    assert bing is not None
    assert bing.automated_ok is False


# --- best_technique returns the higher-success technique ----------------------
def test_best_technique_prefers_higher_success():
    kit = AcquisitionToolkit()
    _seed_techniques(kit)
    # Both parse-jsonld-graph-event (prior .7) and detect-js-shell-then-render
    # (prior .6) apply to the 'squarespace' signal; jsonld wins initially.
    assert kit.best_technique("squarespace").name == "parse-jsonld-graph-event"
    # Record two render successes -> its observed rate overtakes jsonld's prior.
    kit.register_recipe(AcquisitionRecipe(source_id="sq", access_method="js_render",
                                          plan_note="render then parse"),
                        run_id="run-1")
    for t in (1.0, 2.0):
        kit.record_outcome("sq", run_id="run-1", method="js_render",
                           technique="detect-js-shell-then-render",
                           yield_count=9, success=True, at=t)
    assert kit.best_technique("squarespace").name == "detect-js-shell-then-render"


def test_best_technique_unknown_signal_is_none():
    kit = AcquisitionToolkit()
    _seed_techniques(kit)
    assert kit.best_technique("no_such_signal") is None


# --- the 4 brain write invariants still hold ----------------------------------
def test_recipe_claim_without_source_raises_brain_invariant():
    # A recipe/technique claim is a brain Claim: writing one with no Source and
    # no inference flag violates brain invariant 1 and raises loudly.
    g = Graph()
    with pytest.raises(GraphInvariantError):
        g.add_claim(Claim(text='{"kind": "acquisition_recipe"}',
                          source_id=None, inference=False))


def test_recipe_write_requires_a_run():
    # This module's own rule: every recipe write is bound to an AgentRun. A
    # blank run_id is refused (provenance cannot be dropped).
    kit = AcquisitionToolkit()
    with pytest.raises(AcquisitionError):
        kit.register_recipe(AcquisitionRecipe(source_id="x", access_method="plain_http"),
                            run_id="")


def test_stored_recipe_claim_cites_a_source_and_binds_the_run():
    # Structural proof: the stored recipe claim carries a DERIVED_FROM edge to a
    # Source (invariant 1) AND a DERIVED_FROM edge to the AgentRun that learned
    # it (this module's binding), so provenance is fully traversable.
    kit = _kit_with_recipe()
    entity = kit._entity("acquisition_recipe", "mohawk")
    claim = kit._current_claim(entity.id)
    assert claim is not None
    derived = [e for e in kit.g.edges_of(claim.id)
               if e.edge_type is EdgeType.DERIVED_FROM and e.src == claim.id]
    dst_types = {kit.g.get(e.dst).node_type for e in derived}
    assert NodeType.SOURCE in dst_types
    assert NodeType.AGENT_RUN in dst_types


def test_recipe_from_source_prefers_structured_feed():
    # A catalog row offering an ICS feed maps to the cheap structured method,
    # not a plain HTML scrape (cost discipline + authoritative anchor).
    row = {"id": "v1", "name": "Venue One", "base_url": "https://v1.example/calendar",
           "access_method": "public_web_or_ics", "access_reliability": 0.8,
           "credibility_weight": 0.85,
           "allowed": ["public_calendar_pages", "ics_feed_if_offered"],
           "explicitly_disallowed": ["login_scraping"]}
    r = recipe_from_source(row)
    assert r.access_method == "ics_feed"
    assert r.structured_format == "ics"
    assert r.calendar_url_is_homepage is False       # URL has a /calendar path
    _assert_recipe_legal(r)
