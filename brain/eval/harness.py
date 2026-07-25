"""The memory-eval runner + DETERMINISTIC scorer for the OneLive brain.

Greppable summary: builds a fresh brain from each benchmark scenario, answers
every question by QUERYING THE BRAIN (subgraph traversal, supersede-aware
retrieval, reversible-resolution routing), and scores each answer by exact /
structured match against its gold label. No LLM, no network, no spend — the
score is a measured fact, reproducible byte-for-byte.

The query helpers here are thin, brain-backed readers (this is the brain's
"read surface" for the benchmark). They do not modify ``brain/graph.py``; they
call its public API: ``subgraph``, ``get``, ``nodes_of_type``, and the
supersede / resolution state the graph already records. Because the helpers
traverse the real graph, a brain that loses an edge, a supersede flag, or a
resolution link answers WORSE — which is exactly what the planted-regression
tests in ``tests/test_brain_eval.py`` exploit to prove the gate can fail.

Metrics returned in :class:`MemoryEvalReport`:
  * per-category accuracy + overall accuracy,
  * provenance_citation_rate — of the questions the brain answered with a
    concrete value where a source was expected, the fraction that returned the
    supporting Source,
  * abstention_correctness — of ALL questions, the fraction where the
    abstain-or-answer decision was correct (abstains iff it should, answers iff
    it should). Fabricating an answer to an unanswerable question is the worst
    failure and is scored here and in the abstention category.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from brain.eval.benchmark import (
    BENCHMARK,
    CATEGORIES,
    Gold,
    Query,
    Question,
    Scenario,
)
from brain.graph import Graph
from brain.schema import EdgeType, NodeType


# --- the answer object --------------------------------------------------------
@dataclass
class Answer:
    """What a brain query returned. ``value is None and not disputed`` means the
    brain abstained (said unknown)."""

    value: Optional[str] = None
    values: List[str] = field(default_factory=list)  # both sides of a dispute
    disputed: bool = False
    sources: List[str] = field(default_factory=list)

    def is_unknown(self) -> bool:
        return self.value is None and not self.disputed and not self.values

    @classmethod
    def unknown(cls) -> "Answer":
        return cls()


# --- brain-backed query helpers (the read surface under test) -----------------
def _live_claims_mentioning(g: Graph, entity_id: str) -> List:
    """Every NON-superseded Claim one MENTIONS-hop from ``entity_id``.

    This is a real graph query: a 1-hop subgraph over MENTIONS edges, filtered
    to claim nodes that are still live. Superseded claims are excluded here —
    supersede-aware retrieval is what makes "current value" correct.
    """
    sg = g.subgraph(entity_id, hops=1, edge_types=[EdgeType.MENTIONS])
    return [n for n in sg.nodes
            if n.node_type == NodeType.CLAIM and not n.superseded]


def _all_claims_mentioning(g: Graph, entity_id: str) -> List:
    """Every Claim (incl. superseded) one MENTIONS-hop from ``entity_id``."""
    sg = g.subgraph(entity_id, hops=1, edge_types=[EdgeType.MENTIONS])
    return [n for n in sg.nodes if n.node_type == NodeType.CLAIM]


def _attr_value(claim, predicate: str) -> Optional[str]:
    """Parse ``"<predicate>=<value>"`` claim text; None if not this predicate."""
    prefix = f"{predicate}="
    if claim.text.startswith(prefix):
        return claim.text[len(prefix):]
    return None


def _attr_claims(g: Graph, entity_id: str, predicate: str) -> List:
    """Live attribute claims on ``entity_id`` for ``predicate``."""
    return [c for c in _live_claims_mentioning(g, entity_id)
            if _attr_value(c, predicate) is not None]


def single_fact(g: Graph, entity_id: str, predicate: str) -> Answer:
    """Retrieve one stored attribute fact + its source. Abstain if absent."""
    claims = _attr_claims(g, entity_id, predicate)
    if not claims:
        return Answer.unknown()
    values = {_attr_value(c, predicate) for c in claims}
    if len(values) > 1:
        # More than one live value for a single-fact predicate is itself a
        # dispute — surface it rather than pick one.
        return contradiction(g, entity_id, predicate)
    c = claims[0]
    return Answer(value=_attr_value(c, predicate),
                  sources=[c.source_id] if c.source_id else [])


def current_value(g: Graph, entity_id: str, predicate: str) -> Answer:
    """The CURRENT value of a fact that may have changed over time.

    Bi-temporal: the current fact is the live attribute claim whose VALID
    interval is still OPEN (``valid_to is None`` — unbounded future = still
    true). A closed-interval "before" claim (valid_to set) is a past era and is
    NOT returned. A timeless claim (both bounds None) is also open-ended, so a
    non-temporal fact behaves exactly as before. Abstain if nothing is currently
    valid; surface a dispute if two open claims disagree.
    """
    claims = [c for c in _attr_claims(g, entity_id, predicate)
              if getattr(c, "valid_to", None) is None]
    if not claims:
        return Answer.unknown()
    values = {_attr_value(c, predicate) for c in claims}
    if len(values) > 1:
        return contradiction(g, entity_id, predicate)
    c = claims[0]
    return Answer(value=_attr_value(c, predicate),
                  sources=[c.source_id] if c.source_id else [])


def as_of(g: Graph, entity_id: str, predicate: str, date: str) -> Answer:
    """Point-in-time recall — now SERVED by the bi-temporal substrate.

    Routes to ``Graph.claims_valid_at``: the fact whose VALID interval
    ``[valid_from, valid_to)`` contained ``date``, using only currently-believed
    (non-superseded) versions. Abstain if no fact was valid then (e.g. a date
    before any recorded era) — time-travel must not fabricate outside its
    intervals. If more than one value was valid at that instant (overlapping
    intervals), surface it as a dispute rather than pick one.
    """
    claims = [c for c in g.claims_valid_at(entity_id, date, predicate=predicate)
              if _attr_value(c, predicate) is not None]
    if not claims:
        return Answer.unknown()
    values = {_attr_value(c, predicate) for c in claims}
    if len(values) > 1:
        sources = sorted({c.source_id for c in claims if c.source_id})
        return Answer(values=sorted(values), disputed=True, sources=sources)
    c = claims[0]
    return Answer(value=_attr_value(c, predicate),
                  sources=[c.source_id] if c.source_id else [])


def contradiction(g: Graph, entity_id: str, predicate: str) -> Answer:
    """Surface BOTH sides when live sources disagree; never silently pick one."""
    claims = _attr_claims(g, entity_id, predicate)
    if not claims:
        return Answer.unknown()
    by_value = {}
    for c in claims:
        by_value.setdefault(_attr_value(c, predicate), []).append(c)
    values = sorted(by_value)
    # Corroborate with an explicit CONTRADICTS edge among these claims.
    ids = {c.id for c in claims}
    edge_disputed = any(
        e.edge_type == EdgeType.CONTRADICTS and e.src in ids and e.dst in ids
        for e in g.edges.values()
    )
    if len(values) >= 2 or edge_disputed:
        sources = sorted({c.source_id for c in claims if c.source_id})
        return Answer(values=values, disputed=True, sources=sources)
    c = claims[0]
    return Answer(value=values[0], sources=[c.source_id] if c.source_id else [])


def _relation_claim(g: Graph, entity_id: str, predicate: str):
    """A live relation claim for ``predicate`` where ``entity_id`` is the SUBJECT.

    The claim text stamps ``rel:<predicate>@<subject_id>`` (see benchmark._rel),
    so traversal only follows edges outward from the subject and never walks
    back into a shared intermediate node.
    """
    want = f"rel:{predicate}@{entity_id}"
    for c in _live_claims_mentioning(g, entity_id):
        if c.text == want:
            return c
    return None


def _other_entity(g: Graph, claim, not_id: str) -> Optional[str]:
    """The entity a relation claim mentions that is not ``not_id``."""
    sg = g.subgraph(claim.id, hops=1, edge_types=[EdgeType.MENTIONS])
    others = [n.id for n in sg.nodes
              if n.node_type == NodeType.ENTITY and n.id != not_id]
    return others[0] if len(others) == 1 else None


def multi_hop(g: Graph, start_id: str, path) -> Answer:
    """Traverse a chain of relation claims (>= 2 edges). Abstain if the chain
    breaks. The answer is the final entity's name; sources are the relation
    claims traversed (the provenance of the path)."""
    current = start_id
    sources: List[str] = []
    for predicate in path:
        rel = _relation_claim(g, current, predicate)
        if rel is None:
            return Answer.unknown()
        nxt = _other_entity(g, rel, current)
        if nxt is None:
            return Answer.unknown()
        if rel.source_id:
            sources.append(rel.source_id)
        current = nxt
    node = g.get(current)
    return Answer(value=node.name, sources=sources)


def _find_entity_for_alias(g: Graph, alias: str):
    """Resolve a surface form to the canonical entity that carries the facts.

    A folded surface form has ``canonical_id`` set (RESOLVED_TO); follow it. A
    match on the canonical's own name/aliases returns the canonical directly.
    """
    for e in g.nodes_of_type(NodeType.ENTITY):
        if e.name == alias or alias in getattr(e, "aliases", []):
            if e.canonical_id and g.has(e.canonical_id):
                return g.get(e.canonical_id)
            return e
    return None


def via_alias(g: Graph, alias: str, predicate: str) -> Answer:
    """Answer an attribute question posed with an ALIAS by routing through
    entity resolution to the canonical entity's facts."""
    ent = _find_entity_for_alias(g, alias)
    if ent is None:
        return Answer.unknown()
    return single_fact(g, ent.id, predicate)


# --- the pluggable answerer (so tests can plant regressions) ------------------
class BrainAnswerer:
    """Dispatches a :class:`Query` to the brain-backed helper for its ``op``.

    Subclass and override a method to PLANT a regression (e.g. drop a hop in
    ``multi_hop`` or fabricate on ``single_fact``) — the tests do exactly this
    to prove the gate detects a worse brain.
    """

    def answer(self, g: Graph, keymap: dict, q: Query) -> Answer:
        subject_id = keymap.get(q.subject) if q.subject else None
        if q.op in ("single_fact", "current_value", "contradiction") and subject_id is None:
            # Subject not in the corpus at all → nothing to retrieve → abstain.
            return Answer.unknown()
        if q.op == "single_fact":
            return self.single_fact(g, subject_id, q.predicate)
        if q.op == "current_value":
            return self.current_value(g, subject_id, q.predicate)
        if q.op == "contradiction":
            return self.contradiction(g, subject_id, q.predicate)
        if q.op == "as_of":
            return self.as_of(g, subject_id, q.predicate, q.as_of_date)
        if q.op == "multi_hop":
            if subject_id is None:
                return Answer.unknown()
            return self.multi_hop(g, subject_id, q.path)
        if q.op == "via_alias":
            return self.via_alias(g, q.alias, q.predicate)
        raise ValueError(f"unknown query op {q.op!r} — the benchmark is malformed.")

    # thin wrappers, overridable in tests
    def single_fact(self, g, sid, pred):
        return single_fact(g, sid, pred)

    def current_value(self, g, sid, pred):
        return current_value(g, sid, pred)

    def contradiction(self, g, sid, pred):
        return contradiction(g, sid, pred)

    def as_of(self, g, sid, pred, date):
        return as_of(g, sid, pred, date)

    def multi_hop(self, g, sid, path):
        return multi_hop(g, sid, path)

    def via_alias(self, g, alias, pred):
        return via_alias(g, alias, pred)


# --- scoring ------------------------------------------------------------------
def score_answer(answer: Answer, gold: Gold) -> bool:
    """Deterministic exact / structured match of an answer against its gold."""
    if gold.unknown:
        return answer.is_unknown()
    if gold.disputed:
        return (answer.disputed
                and set(answer.values) == set(gold.values or ()))
    # single expected value
    if answer.is_unknown() or answer.disputed:
        return False
    ok = answer.value == gold.value
    if gold.expect_source:
        ok = ok and bool(answer.sources)
    return ok


# --- report structures --------------------------------------------------------
@dataclass
class QuestionResult:
    id: str
    category: str
    text: str
    correct: bool
    abstained: bool
    should_abstain: bool
    cited_source: bool
    answered_value: bool  # produced a concrete value (not unknown, not disputed)


@dataclass
class CategoryScore:
    category: str
    n_correct: int
    n_total: int

    @property
    def accuracy(self) -> float:
        return self.n_correct / self.n_total if self.n_total else 0.0


@dataclass
class MemoryEvalReport:
    results: List[QuestionResult]
    per_category: dict  # category -> CategoryScore

    @property
    def overall_accuracy(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.correct) / len(self.results)

    @property
    def provenance_citation_rate(self) -> float:
        # Of questions the brain answered with a concrete value where a source
        # was expected, the fraction that returned one.
        eligible = [r for r in self.results if r.answered_value]
        if not eligible:
            return 0.0
        return sum(1 for r in eligible if r.cited_source) / len(eligible)

    @property
    def abstention_correctness(self) -> float:
        # Of ALL questions, the fraction where abstain-or-answer was correct.
        if not self.results:
            return 0.0
        good = sum(1 for r in self.results if r.abstained == r.should_abstain)
        return good / len(self.results)

    @property
    def n_total(self) -> int:
        return len(self.results)


# --- the runner ---------------------------------------------------------------
def run_benchmark(scenarios: Optional[List[Scenario]] = None,
                  answerer: Optional[BrainAnswerer] = None,
                  mutate: Optional[Callable[[Graph, dict, Scenario], None]] = None,
                  ) -> MemoryEvalReport:
    """Build each scenario's brain fresh, answer every question by querying it,
    and score deterministically.

    ``answerer`` lets a test inject a regressed read surface; ``mutate`` is an
    optional post-build hook (graph, keymap, scenario) a test can use to damage
    the corpus (drop an edge, clear a resolution) before questions are asked.
    """
    scenarios = scenarios if scenarios is not None else BENCHMARK
    answerer = answerer if answerer is not None else BrainAnswerer()

    results: List[QuestionResult] = []
    for scenario in scenarios:
        g, keymap = scenario.build()
        if mutate is not None:
            mutate(g, keymap, scenario)
        for q in scenario.questions:
            answer = answerer.answer(g, keymap, q.query)
            correct = score_answer(answer, q.gold)
            answered_value = (not answer.is_unknown()) and (not answer.disputed)
            results.append(QuestionResult(
                id=q.id,
                category=q.category,
                text=q.text,
                correct=correct,
                abstained=answer.is_unknown(),
                should_abstain=q.gold.unknown,
                cited_source=bool(answer.sources),
                answered_value=answered_value,
            ))

    per_category = {}
    for cat in CATEGORIES:
        rows = [r for r in results if r.category == cat]
        per_category[cat] = CategoryScore(
            category=cat,
            n_correct=sum(1 for r in rows if r.correct),
            n_total=len(rows),
        )
    return MemoryEvalReport(results=results, per_category=per_category)
