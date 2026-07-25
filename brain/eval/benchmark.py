"""A labeled, deterministic memory benchmark for the OneLive brain.

Greppable summary: the ground-truth corpus + questions that let us MEASURE the
brain (``brain/``) instead of asserting it is good. Each :class:`Scenario`
builds a FRESH knowledge graph from a fixed corpus (sources, entities, claims,
edges, supersessions, resolutions) and carries a list of :class:`Question`s,
each with a GOLD answer and a category. The runner+scorer live in
``brain/eval/harness.py``; the CLI in ``tools/brain_eval.py``.

Why these six categories: they are the standard agent-memory competencies the
literature benchmarks (single-fact recall, multi-hop reasoning, knowledge
update over time, contradiction handling, entity resolution, and abstention).
See ``docs/strategy/ONE_LIVE_BRAIN_BENCHMARK_v1.md`` for the honest write-up and
the positioning versus SOTA (LongMemEval / Zep / Graphiti).

HOW A QUESTION IS ANSWERED WITHOUT AN LLM
-----------------------------------------
This benchmark is deterministic and spends nothing — there is no NL parser and
no LLM judge. Every question carries a structured :class:`Query` that names a
graph operation and its arguments (by a stable per-scenario key), and the
harness answers it by QUERYING THE BRAIN (subgraph traversal, supersede-aware
retrieval, alias resolution). Facts are encoded in claim text with a fixed
machine convention so the answer can be read back structurally:

  * an ATTRIBUTE claim mentions ONE entity and reads ``"<predicate>=<value>"``
    (e.g. a claim mentioning the Mohawk entity, text ``"address=912 Red River St"``).
  * a RELATION claim mentions TWO entities and reads ``"rel:<predicate>"``
    (e.g. a claim mentioning {Ghost, Mohawk}, text ``"rel:plays_at"``); the
    object is the OTHER mentioned entity, reached by following MENTIONS edges.

The convention is the fact-encoding; the ANSWERING is real graph traversal, so
a graph that loses an edge, a resolution, or a supersede flag scores lower.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple

from brain.graph import Graph
from brain.schema import (
    Claim,
    EdgeType,
    Entity,
    Source,
)

# --- category names (single source of truth) ---------------------------------
SINGLE_FACT = "single_fact_recall"
MULTI_HOP = "multi_hop"
KNOWLEDGE_UPDATE = "knowledge_update"
CONTRADICTION = "contradiction"
ENTITY_RESOLUTION = "entity_resolution"
ABSTENTION = "abstention"

CATEGORIES: Tuple[str, ...] = (
    SINGLE_FACT,
    MULTI_HOP,
    KNOWLEDGE_UPDATE,
    CONTRADICTION,
    ENTITY_RESOLUTION,
    ABSTENTION,
)


# --- structured query + gold + question --------------------------------------
@dataclass(frozen=True)
class Query:
    """A brain operation to run for one question.

    ``op`` picks the harness helper; the other fields are its arguments.
    ``subject`` is a per-scenario key resolved against the scenario's keymap
    (never a hand-written node id). ``as_of_date`` probes point-in-time recall
    the current substrate cannot serve (no bitemporal validity) — it is here on
    purpose so the benchmark MEASURES that gap rather than hiding it.
    """

    op: str  # single_fact | multi_hop | current_value | as_of | contradiction | via_alias
    subject: str = ""            # keymap key of the subject entity
    predicate: str = ""          # attribute predicate for single_fact/current_value/contradiction
    path: Tuple[str, ...] = ()   # relation predicates to traverse for multi_hop
    alias: str = ""              # surface form to resolve for via_alias
    as_of_date: str = ""         # date string for a point-in-time (as_of) probe


@dataclass(frozen=True)
class Gold:
    """The labeled correct answer for a question.

    Exactly one shape applies:
      * ``unknown=True``            — the corpus does not answer it; the brain
                                      MUST abstain (return unknown), never fabricate.
      * ``disputed=True`` + ``values`` — two sources disagree; the brain MUST
                                      surface BOTH values and flag disputed.
      * else ``value``              — a single expected answer; ``expect_source``
                                      says whether a supporting Source must come back.
    """

    value: Optional[str] = None
    values: Optional[Tuple[str, ...]] = None
    disputed: bool = False
    unknown: bool = False
    expect_source: bool = True


@dataclass(frozen=True)
class Question:
    id: str
    category: str
    text: str          # the human-readable question (for the scorecard)
    query: Query
    gold: Gold


@dataclass
class Scenario:
    """A fresh-brain corpus plus the questions asked against it."""

    id: str
    build: Callable[[], Tuple[Graph, dict]]  # -> (graph, keymap)
    questions: list = field(default_factory=list)


# --- small corpus builders ----------------------------------------------------
def _attr(g: Graph, subject_id: str, predicate: str, value: str,
          source_id: str) -> Claim:
    """Add a sourced ATTRIBUTE claim (mentions the subject only)."""
    claim = g.add_claim(Claim(text=f"{predicate}={value}", source_id=source_id))
    g.add_edge(claim.id, subject_id, EdgeType.MENTIONS)
    return claim


def _rel(g: Graph, subject_id: str, predicate: str, object_id: str,
         source_id: str) -> Claim:
    """Add a sourced RELATION claim (mentions both endpoints).

    The text stamps the DIRECTION (``rel:<predicate>@<subject_id>``) so a chain
    that revisits an intermediate node (e.g. two venues both ``located_in`` the
    same district) is traversed subject->object, never backward: MENTIONS edges
    alone are undirected, so the direction lives in the claim it belongs to.
    """
    claim = g.add_claim(Claim(text=f"rel:{predicate}@{subject_id}",
                              source_id=source_id))
    g.add_edge(claim.id, subject_id, EdgeType.MENTIONS)
    g.add_edge(claim.id, object_id, EdgeType.MENTIONS)
    return claim


# --- scenario 1: venues_and_shows (single_fact, multi_hop, abstention) --------
def build_venues_and_shows() -> Tuple[Graph, dict]:
    g = Graph()
    k: dict = {}

    src_cal = g.add_source(Source(uri="https://mohawkaustin.com/cal",
                                  title="Mohawk official calendar")).id
    src_dir = g.add_source(Source(uri="https://austindir.test/venues",
                                  title="Austin venue directory")).id
    src_empire = g.add_source(Source(uri="https://empireatx.test",
                                     title="Empire ATX site")).id
    src_ghost = g.add_source(Source(uri="https://ghostband.test/tour",
                                    title="Ghost tour page")).id

    k["mohawk"] = g.add_entity(Entity(name="Mohawk", entity_type="venue")).id
    k["empire"] = g.add_entity(Entity(name="Empire", entity_type="venue")).id
    k["stubbs"] = g.add_entity(Entity(name="Stubb's", entity_type="venue")).id
    k["ghost"] = g.add_entity(Entity(name="Ghost", entity_type="artist")).id
    k["red_river"] = g.add_entity(
        Entity(name="Red River District", entity_type="district")).id
    k["austin"] = g.add_entity(Entity(name="Austin", entity_type="city")).id

    _attr(g, k["mohawk"], "address", "912 Red River St", src_cal)
    _attr(g, k["mohawk"], "capacity", "900", src_cal)
    _attr(g, k["empire"], "genre", "techno", src_empire)
    _attr(g, k["stubbs"], "address", "801 Red River St", src_dir)
    _attr(g, k["ghost"], "genre", "doom rock", src_ghost)

    _rel(g, k["ghost"], "plays_at", k["mohawk"], src_ghost)
    _rel(g, k["mohawk"], "located_in", k["red_river"], src_dir)
    _rel(g, k["empire"], "located_in", k["red_river"], src_dir)
    _rel(g, k["red_river"], "located_in", k["austin"], src_dir)

    return g, k


VENUES_QUESTIONS = [
    # single_fact_recall
    Question("vs-sf-1", SINGLE_FACT, "What is Mohawk's street address?",
             Query("single_fact", subject="mohawk", predicate="address"),
             Gold(value="912 Red River St")),
    Question("vs-sf-2", SINGLE_FACT, "What is Mohawk's capacity?",
             Query("single_fact", subject="mohawk", predicate="capacity"),
             Gold(value="900")),
    Question("vs-sf-3", SINGLE_FACT, "What genre does Empire play?",
             Query("single_fact", subject="empire", predicate="genre"),
             Gold(value="techno")),
    Question("vs-sf-4", SINGLE_FACT, "What is Stubb's street address?",
             Query("single_fact", subject="stubbs", predicate="address"),
             Gold(value="801 Red River St")),
    # multi_hop (>= 2 edges traversed)
    Question("vs-mh-1", MULTI_HOP, "What city is the Mohawk venue in?",
             Query("multi_hop", subject="mohawk", path=("located_in", "located_in")),
             Gold(value="Austin")),
    Question("vs-mh-2", MULTI_HOP, "What district does the band Ghost play in?",
             Query("multi_hop", subject="ghost", path=("plays_at", "located_in")),
             Gold(value="Red River District")),
    Question("vs-mh-3", MULTI_HOP, "What city does the band Ghost play in?",
             Query("multi_hop", subject="ghost",
                   path=("plays_at", "located_in", "located_in")),
             Gold(value="Austin")),
    Question("vs-mh-4", MULTI_HOP, "What city is Empire in?",
             Query("multi_hop", subject="empire", path=("located_in", "located_in")),
             Gold(value="Austin")),
    # abstention (corpus does NOT answer these)
    Question("vs-ab-1", ABSTENTION, "What is Mohawk's wifi password?",
             Query("single_fact", subject="mohawk", predicate="wifi_password"),
             Gold(unknown=True)),
    Question("vs-ab-2", ABSTENTION, "What year was Mohawk founded?",
             Query("single_fact", subject="mohawk", predicate="founded_year"),
             Gold(unknown=True)),
    Question("vs-ab-3", ABSTENTION, "What city does Empire's owner live in?",
             Query("multi_hop", subject="empire", path=("owned_by", "lives_in")),
             Gold(unknown=True)),
]


# --- scenario 2: changing_lineup (knowledge_update, contradiction) ------------
def build_changing_lineup() -> Tuple[Graph, dict]:
    g = Graph()
    k: dict = {}

    src_early = g.add_source(Source(uri="https://listing.test/early",
                                    title="Early week listing (2026-07-01)")).id
    src_late = g.add_source(Source(uri="https://mohawkaustin.com/cal",
                                   title="Day-of official calendar (2026-07-08)")).id
    src_flyer = g.add_source(Source(uri="https://flyer.test/fest",
                                    title="Street flyer")).id
    src_venue = g.add_source(Source(uri="https://venue.test/fest",
                                    title="Venue box office")).id

    k["mohawk"] = g.add_entity(Entity(name="Mohawk", entity_type="venue")).id
    k["fest"] = g.add_entity(Entity(name="Red River Fest", entity_type="event")).id

    # Knowledge update: an early claim, superseded by a later one. The old node
    # stays addressable (invariant 4); the CURRENT answer is the live claim.
    for pred, old_v, new_v in (
        ("headliner", "Band A", "Band B"),
        ("cover", "$15", "$20"),
        ("door_time", "8pm", "9pm"),
    ):
        old = _attr(g, k["mohawk"], pred, old_v, src_early)
        new = _attr(g, k["mohawk"], pred, new_v, src_late)
        g.supersede(old.id, by=new.id)

    # Contradiction: two live sources disagree, linked by a CONTRADICTS edge.
    for pred, va, vb in (("start_time", "7pm", "8pm"), ("at", "Mohawk", "Empire")):
        ca = _attr(g, k["fest"], pred, va, src_flyer)
        cb = _attr(g, k["fest"], pred, vb, src_venue)
        g.add_edge(ca.id, cb.id, EdgeType.CONTRADICTS)

    return g, k


LINEUP_QUESTIONS = [
    # knowledge_update — the CURRENT value must win over the superseded one.
    Question("cl-ku-1", KNOWLEDGE_UPDATE,
             "Who is tonight's headliner at Mohawk right now?",
             Query("current_value", subject="mohawk", predicate="headliner"),
             Gold(value="Band B")),
    Question("cl-ku-2", KNOWLEDGE_UPDATE, "What is the current cover charge at Mohawk?",
             Query("current_value", subject="mohawk", predicate="cover"),
             Gold(value="$20")),
    Question("cl-ku-3", KNOWLEDGE_UPDATE, "What is the current door time at Mohawk?",
             Query("current_value", subject="mohawk", predicate="door_time"),
             Gold(value="9pm")),
    # knowledge_update — POINT-IN-TIME recall. The substrate has no bitemporal
    # validity (R-010/R-031): supersede records THAT a fact changed, not WHEN it
    # was valid, so an "as of <date>" question cannot be served. Gold is the
    # historical value; the brain will miss it. This measures the honest gap.
    Question("cl-ku-4", KNOWLEDGE_UPDATE,
             "As of the early listing (2026-07-01), who was the headliner?",
             Query("as_of", subject="mohawk", predicate="headliner",
                   as_of_date="2026-07-01"),
             Gold(value="Band A")),
    Question("cl-ku-5", KNOWLEDGE_UPDATE,
             "As of the early listing (2026-07-01), what was the cover charge?",
             Query("as_of", subject="mohawk", predicate="cover",
                   as_of_date="2026-07-01"),
             Gold(value="$15")),
    # contradiction — surface BOTH, flag disputed; never silently pick one.
    Question("cl-co-1", CONTRADICTION, "What time does Red River Fest start?",
             Query("contradiction", subject="fest", predicate="start_time"),
             Gold(disputed=True, values=("7pm", "8pm"))),
    Question("cl-co-2", CONTRADICTION, "Where is Red River Fest held?",
             Query("contradiction", subject="fest", predicate="at"),
             Gold(disputed=True, values=("Mohawk", "Empire"))),
]


# --- scenario 3: aliases (entity_resolution, contradiction, abstention) -------
def build_aliases() -> Tuple[Graph, dict]:
    g = Graph()
    k: dict = {}

    src_cuc = g.add_source(Source(uri="https://cheerupcharlies.test",
                                  title="Cheer Up Charlies site")).id
    src_x = g.add_source(Source(uri="https://mag-x.test", title="Magazine X")).id
    src_y = g.add_source(Source(uri="https://mag-y.test", title="Magazine Y")).id
    src_other = g.add_source(Source(uri="https://fire-marshal.test",
                                    title="Fire-marshal record")).id

    # Canonical venue holds the facts; two surface forms get folded into it.
    k["cheer"] = g.add_entity(Entity(name="Cheer Up Charlies", entity_type="venue")).id
    surf_1 = g.add_entity(Entity(name="Cheer Ups", entity_type="venue",
                                 source_docs=["doc:cheerups"])).id
    surf_2 = g.add_entity(Entity(name="CUC", entity_type="venue",
                                 source_docs=["doc:cuc"])).id
    k["dj_nova"] = g.add_entity(Entity(name="DJ Nova", entity_type="artist")).id

    _attr(g, k["cheer"], "address", "900 Red River St", src_cuc)
    _attr(g, k["cheer"], "genre", "queer dance", src_cuc)

    # Reversible resolution: fold the two surface forms into the canonical.
    g.resolve_entities(canonical=k["cheer"], others=[surf_1, surf_2],
                       rationale="same venue: same address + same calendar",
                       confidence=0.95)

    # Contradiction on the artist and on the canonical venue's capacity.
    ga = _attr(g, k["dj_nova"], "genre", "house", src_x)
    gb = _attr(g, k["dj_nova"], "genre", "techno", src_y)
    g.add_edge(ga.id, gb.id, EdgeType.CONTRADICTS)
    ca = _attr(g, k["cheer"], "capacity", "200", src_cuc)
    cb = _attr(g, k["cheer"], "capacity", "300", src_other)
    g.add_edge(ca.id, cb.id, EdgeType.CONTRADICTS)

    return g, k


ALIAS_QUESTIONS = [
    # entity_resolution — a question using an ALIAS must reach the canonical
    # entity's facts (and their provenance).
    Question("al-er-1", ENTITY_RESOLUTION, "What is the address of 'Cheer Ups'?",
             Query("via_alias", alias="Cheer Ups", predicate="address"),
             Gold(value="900 Red River St")),
    Question("al-er-2", ENTITY_RESOLUTION, "What genre is 'CUC'?",
             Query("via_alias", alias="CUC", predicate="genre"),
             Gold(value="queer dance")),
    Question("al-er-3", ENTITY_RESOLUTION,
             "What is the address of 'Cheer Up Charlies'?",
             Query("via_alias", alias="Cheer Up Charlies", predicate="address"),
             Gold(value="900 Red River St")),
    Question("al-er-4", ENTITY_RESOLUTION, "What genre does 'Cheer Ups' play?",
             Query("via_alias", alias="Cheer Ups", predicate="genre"),
             Gold(value="queer dance")),
    # contradiction
    Question("al-co-1", CONTRADICTION, "What genre is DJ Nova?",
             Query("contradiction", subject="dj_nova", predicate="genre"),
             Gold(disputed=True, values=("house", "techno"))),
    Question("al-co-2", CONTRADICTION, "What is the capacity of Cheer Up Charlies?",
             Query("contradiction", subject="cheer", predicate="capacity"),
             Gold(disputed=True, values=("200", "300"))),
    # abstention
    Question("al-ab-1", ABSTENTION, "What is Cheer Up Charlies' phone number?",
             Query("single_fact", subject="cheer", predicate="phone"),
             Gold(unknown=True)),
    Question("al-ab-2", ABSTENTION, "What is the address of 'Barbarella'?",
             Query("via_alias", alias="Barbarella", predicate="address"),
             Gold(unknown=True)),
]


BENCHMARK = [
    Scenario("venues_and_shows", build_venues_and_shows, VENUES_QUESTIONS),
    Scenario("changing_lineup", build_changing_lineup, LINEUP_QUESTIONS),
    Scenario("aliases", build_aliases, ALIAS_QUESTIONS),
]


def all_questions() -> list:
    """Flat list of every question in the benchmark (for counts/inspection)."""
    return [q for s in BENCHMARK for q in s.questions]
