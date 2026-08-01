"""Shared, learning acquisition toolkit — how OneLive reads each source, remembered.

Greppable summary: a DURABLE, SHARED store of (1) per-source acquisition
RECIPES and (2) reusable acquisition TECHNIQUES, persisted THROUGH the brain
knowledge-graph (brain/graph.py + brain/store.py) so every agent and every
session reads the same common toolkit off disk and writes its outcomes back
into it. The one-line thesis, inherited from the brain: **the agent forgets,
the toolkit does not.** An agent READS `recipe_for(source_id)` before it
acquires (so it never re-discovers how to read a page it has read before) and
calls `record_outcome(...)` after (so the recipe's yield/reliability and the
technique's success stats improve for whoever acquires next).

Why store it in the brain and not a fresh table: the brain already makes
provenance MECHANICAL. Recipes and techniques are stored as brain
Entities + Claims joined by typed edges, so they INHERIT the four write
invariants — most importantly, every recipe/technique state Claim must cite a
Source (invariant 1), and this module additionally binds every write to the
AgentRun that learned it. A state update SUPERSEDES the prior state Claim
(invariant 4) rather than overwriting it, so a recipe carries its full,
queryable version history and a bad update is reversible, never a catastrophe.

The legal rails are physics here, not politeness (CLAUDE.md Prime Directive,
§5 data-trust): a recipe can NEVER encode a method that bypasses a login, a
paywall, or robots. `_assert_recipe_legal` HARD-REJECTS any such recipe loudly
before it can be stored. Respecting a source's `explicitly_disallowed` list is
part of the recipe, never something the recipe defeats.

Cost discipline (CLAUDE.md "least costly method first"): each recipe and
technique carries a `cost_hint`, and `best_technique` prefers the
highest-success method and breaks ties toward the cheaper one — the cheapest
technique that meets the bar wins.

This module is MEMORY. Like the rest of `brain/`, it never publishes and must
not import `worker.promote` (trust invariant, enforced by tools/trust_gate.py):
knowing HOW to read a source is upstream of, and walled off from, the gate that
decides what reaches users.
"""
from __future__ import annotations

import dataclasses
import json
import statistics
import time
from dataclasses import dataclass, field
from typing import Optional

from brain.graph import Graph
from brain.schema import AgentRun, Claim, EdgeType, Entity, NodeType, Source


class AcquisitionError(Exception):
    """Raised when an acquisition write would be illegal or malformed.

    Deliberately loud and unignorable: the toolkit's whole value is that it
    cannot store a bypass recipe or a provenance-less outcome, so an attempt to
    do either stops the world rather than being silently accepted.
    """


# The five acquisition methods the toolkit knows, each policy-safe by
# construction (mirrors the deterministic importers + the render fallback):
#   plain_http  — a public GET of a public page (worker/fetch/http_fetch.py).
#   js_render   — headless render of a JS-shell page (worker/fetch/render_fetch.py).
#   ics_feed    — an offered iCalendar feed (worker/importers/structured_feed.py).
#   jsonld      — schema.org/Event JSON-LD embedded in a public page (same).
#   api         — an official/partner API or JSON feed (Localist, Ticketmaster, ...).
ACCESS_METHODS = frozenset({"plain_http", "js_render", "ics_feed", "jsonld", "api"})

# Structured payload shapes a recipe may declare.
STRUCTURED_FORMATS = frozenset({"ics", "jsonld", "none"})

# Tokens that mark an ACTIVE bypass in a recipe's action fields (access_method,
# plan_note, segmentation_hint). Their presence is a hard reject — we never
# encode a recipe that logs in, defeats a paywall, or evades a robot policy.
# NB: bare "scrape"/"scraping" is NOT here — scraping a PUBLIC page is allowed;
# only login/paywall/robots-defeating scraping is forbidden. The source's own
# `explicitly_disallowed` list (which legitimately contains words like
# "login_scraping") is a GUARDRAIL we store, not an action field we scan.
_FORBIDDEN_ACTION_TOKENS = frozenset({
    "login", "log in", "sign in", "signin", "log-in",
    "paywall", "credential", "password", "cookie steal", "session token",
    "auth_bypass", "authbypass", "bypass", "circumvent", "circumvention",
    "evasion", "evade", "captcha", "intercept", "scrape_login", "scrape-login",
})

# Bounded window of recent yields kept per recipe for a stable median.
_MAX_YIELD_HISTORY = 20
# Consecutive zero-yield acquisitions that flip a recipe to needs_rediscovery.
_REDISCOVERY_THRESHOLD = 2
# EWMA weight for the evolving reliability score (same idea as
# worker/source_reliability.py: outcomes move a bounded 0..1 score).
_RELIABILITY_ALPHA = 0.3
# Pseudo-count that lets a technique's prior_success_rate rule until real
# attempts accumulate (Beta-style smoothing), so ranking is stable from run 1.
_TECHNIQUE_PRIOR_WEIGHT = 2.0

# The two claim "kinds" this module stores in the brain, tagged inside the
# Claim text JSON so a recipe-state claim is never confused with a technique one.
_KIND_RECIPE = "acquisition_recipe"
_KIND_TECHNIQUE = "acquisition_technique"

_RECIPE_ENTITY_TYPE = "acquisition_recipe"
_TECHNIQUE_ENTITY_TYPE = "acquisition_technique"


# --- the two toolkit records (plain dataclasses, JSON-serialised into Claims) --

@dataclass
class AcquisitionRecipe:
    """How to acquire ONE source's events — the per-source, learned know-how.

    Static descriptor fields (calendar_url, access_method, structured_format,
    segmentation_hint) say HOW to read the page; legal fields (robots_ok,
    tos_note, explicitly_disallowed) say what is permitted; evolving telemetry
    (last_*, median_yield, reliability, needs_rediscovery) is updated by
    `record_outcome`; provenance fields (learned_by_run, confidence, version)
    tie the state to the run that produced it.
    """

    source_id: str
    source_name: str = ""
    # The REAL events/calendar page, not the homepage. `calendar_url_is_homepage`
    # is an honest flag when the seed only had a homepage to key on — discovering
    # the true listing URL is itself a per-source learning step.
    calendar_url: str = ""
    calendar_url_is_homepage: bool = False
    access_method: str = "plain_http"
    render_required: bool = False
    structured_format: str = "none"
    segmentation_hint: str = ""
    # How we acquire, in words — scanned by the legality gate. Kept SEPARATE
    # from tos_note (legal posture) so a rails note can safely say the word
    # "login" without tripping the action-token scan.
    plan_note: str = ""
    robots_ok: bool = True
    tos_note: str = ""
    explicitly_disallowed: list = field(default_factory=list)
    # False for opt-in / manual / benchmark channels (email-forward, claimed
    # upload, search-engine benchmark): legitimate sources, but not a "go fetch
    # the calendar" recipe — the toolkit knows not to auto-acquire them.
    automated_ok: bool = True
    last_attempt_at: Optional[float] = None
    last_success_at: Optional[float] = None
    last_yield: Optional[int] = None
    median_yield: float = 0.0
    yield_history: list = field(default_factory=list)
    attempts: int = 0
    successes: int = 0
    consecutive_empty: int = 0
    reliability: float = 0.5
    cost_hint: str = "low"
    needs_rediscovery: bool = False
    confidence: float = 0.5
    learned_by_run: str = ""
    version: int = 1

    def to_payload(self) -> dict:
        return {"kind": _KIND_RECIPE, "payload": dataclasses.asdict(self)}

    @classmethod
    def from_payload(cls, payload: dict) -> "AcquisitionRecipe":
        valid = {f.name for f in dataclasses.fields(cls)}
        unknown = set(payload) - valid
        if unknown:
            raise AcquisitionError(
                f"recipe payload has unknown field(s) {sorted(unknown)} — "
                "refusing to silently drop stored data on load."
            )
        return cls(**payload)


@dataclass
class AcquisitionTechnique:
    """A general, reusable acquisition METHOD — not tied to any one source.

    A named way of getting events out of a class of page, with the page
    `applies_to_signals` that trigger it and a running success record
    (`attempts`/`successes`) accumulated ACROSS every source it was used on.
    `prior_success_rate` seeds ranking before real attempts exist.
    """

    name: str
    description: str = ""
    when_to_use: str = ""
    applies_to_signals: list = field(default_factory=list)
    attempts: int = 0
    successes: int = 0
    prior_success_rate: float = 0.5
    cost_hint: str = "low"
    learned_by_run: str = ""
    version: int = 1

    def effective_success_rate(self) -> float:
        """Beta-smoothed success rate: the prior rules until attempts arrive,
        then observed successes take over. Deterministic, so ranking is stable."""
        num = self.successes + _TECHNIQUE_PRIOR_WEIGHT * self.prior_success_rate
        den = self.attempts + _TECHNIQUE_PRIOR_WEIGHT
        return num / den

    def to_payload(self) -> dict:
        return {"kind": _KIND_TECHNIQUE, "payload": dataclasses.asdict(self)}

    @classmethod
    def from_payload(cls, payload: dict) -> "AcquisitionTechnique":
        valid = {f.name for f in dataclasses.fields(cls)}
        unknown = set(payload) - valid
        if unknown:
            raise AcquisitionError(
                f"technique payload has unknown field(s) {sorted(unknown)} — "
                "refusing to silently drop stored data on load."
            )
        return cls(**payload)


# --- the legal rail: a bypass recipe can never be stored ----------------------

def _assert_recipe_legal(recipe: AcquisitionRecipe) -> None:
    """Hard-reject any recipe that is malformed or encodes a bypass. LOUD.

    A recipe must (a) use a known, policy-safe access method; (b) never claim
    to ignore robots; and (c) never describe an active login/paywall/robots
    bypass in any of its ACTION fields. This is the physics behind
    'never a recipe that bypasses login/paywall/robots'.
    """
    if recipe.access_method not in ACCESS_METHODS:
        raise AcquisitionError(
            f"recipe for {recipe.source_id!r} uses unknown access_method "
            f"{recipe.access_method!r}; must be one of {sorted(ACCESS_METHODS)}."
        )
    if recipe.structured_format not in STRUCTURED_FORMATS:
        raise AcquisitionError(
            f"recipe for {recipe.source_id!r} has unknown structured_format "
            f"{recipe.structured_format!r}; must be one of {sorted(STRUCTURED_FORMATS)}."
        )
    if not recipe.robots_ok:
        raise AcquisitionError(
            f"recipe for {recipe.source_id!r} sets robots_ok=False — the toolkit "
            "never stores a recipe that acquires against a robots policy. "
            "Acquire only what robots permits, or do not acquire."
        )
    haystack = " ".join([
        recipe.access_method, recipe.plan_note, recipe.segmentation_hint,
    ]).lower()
    for token in _FORBIDDEN_ACTION_TOKENS:
        if token in haystack:
            raise AcquisitionError(
                f"recipe for {recipe.source_id!r} encodes a forbidden action "
                f"({token!r}) — login/paywall/robots bypass is never a recipe. "
                "Rejected."
            )


# --- the toolkit --------------------------------------------------------------

class AcquisitionToolkit:
    """Read-before-acquire / record-after-acquire toolkit over a brain Graph.

    Wraps a `brain.Graph`. Recipes and techniques live in that graph as
    Entities + provenance-bearing Claims, so `brain.store.save/load` persist the
    whole toolkit to disk and any agent that loads the graph sees the shared,
    up-to-date common toolkit. All lookups are by stable name
    (source_id for recipes, technique name for techniques).
    """

    def __init__(self, graph: Optional[Graph] = None) -> None:
        self.g = graph if graph is not None else Graph()

    # --- persistence convenience (delegates to brain.store) -------------------
    @classmethod
    def load(cls, path) -> "AcquisitionToolkit":
        """Load a toolkit from a brain JSONL snapshot on disk."""
        from brain import store  # local import: keep the module import graph flat
        return cls(store.load(path))

    def save(self, path) -> None:
        """Persist the toolkit (its whole brain graph) to disk as JSONL."""
        from brain import store
        store.save(self.g, path)

    # --- provenance helpers ---------------------------------------------------
    def _run_node(self, run_id: str) -> AgentRun:
        """Get or create the AgentRun node for a caller-supplied run_id.

        The logical run_id is stamped into the node's objective so the same run
        reused across many outcomes maps to ONE node (provenance stays legible).
        """
        if not run_id:
            raise AcquisitionError(
                "an acquisition write requires a run_id — every recipe/technique "
                "claim must be bound to the AgentRun that learned it (provenance)."
            )
        marker = f"acq-run:{run_id}"
        for node in self.g.nodes_of_type(NodeType.AGENT_RUN):
            if getattr(node, "objective", "") == marker:
                return node  # type: ignore[return-value]
        return self.g.add_agent_run(AgentRun(
            agent="acquisition", objective=marker, status="active"))

    def _entity(self, entity_type: str, name: str) -> Optional[Entity]:
        for node in self.g.nodes_of_type(NodeType.ENTITY):
            if node.entity_type == entity_type and node.name == name:  # type: ignore[attr-defined]
                return node  # type: ignore[return-value]
        return None

    def _current_claim(self, entity_id: str) -> Optional[Claim]:
        """The single live (non-superseded) state Claim mentioning `entity_id`.

        Picks the highest-version live claim, so even if history is long the
        current state is unambiguous.
        """
        best: Optional[Claim] = None
        best_ver = -1
        for edge in self.g.edges_of(entity_id):
            if edge.edge_type is EdgeType.MENTIONS and edge.dst == entity_id:
                claim = self.g.get(edge.src)
                if getattr(claim, "superseded", False):
                    continue
                try:
                    ver = int(json.loads(claim.text)["payload"].get("version", 1))
                except (ValueError, KeyError, TypeError):
                    continue
                if ver > best_ver:
                    best, best_ver = claim, ver  # type: ignore[assignment]
        return best

    def _write_state_claim(self, *, entity: Entity, kind: str, payload: dict,
                           run: AgentRun, source_uri: str, source_title: str,
                           confidence: float) -> Claim:
        """Store a new state Claim (recipe or technique), superseding the prior.

        The Claim cites a fresh Source (invariant 1) and is bound to the run by
        a DERIVED_FROM edge (this module's run-binding rule). It MENTIONS the
        stable entity so lookups find it, and it SUPERSEDES the prior live claim
        (invariant 4) so the full version history stays queryable.
        """
        src = self.g.add_source(Source(
            uri=source_uri, title=source_title,
            description=f"acquisition state learned by {run.objective}"))
        claim = self.g.add_claim(Claim(
            text=json.dumps({"kind": kind, "payload": payload}, sort_keys=True),
            source_id=src.id, confidence=confidence))
        self.g.add_edge(claim.id, entity.id, EdgeType.MENTIONS)
        # Bind the learning run to the claim so provenance is traversable: this
        # state was DERIVED_FROM that run's work (in addition to its Source).
        self.g.add_edge(claim.id, run.id, EdgeType.DERIVED_FROM)
        prior = None
        for edge in self.g.edges_of(entity.id):
            if (edge.edge_type is EdgeType.MENTIONS and edge.dst == entity.id
                    and edge.src != claim.id):
                cand = self.g.get(edge.src)
                if not getattr(cand, "superseded", False):
                    prior = cand
        if prior is not None:
            self.g.supersede(prior.id, by=claim.id)
        return claim

    # --- recipes: register + READ ---------------------------------------------
    def register_recipe(self, recipe: AcquisitionRecipe, *, run_id: str,
                        source_uri: str = "", confidence: Optional[float] = None
                        ) -> AcquisitionRecipe:
        """Store a recipe (legality-checked) as an Entity + provenance Claim.

        Idempotent by source_id at the ENTITY level: re-registering a source
        that already has a recipe is a no-op that returns the existing recipe
        (seeding never duplicates). To change a stored recipe, use
        `record_outcome` (which supersedes) — registration only creates.
        """
        _assert_recipe_legal(recipe)
        existing = self.recipe_for(recipe.source_id)
        if existing is not None:
            return existing
        run = self._run_node(run_id)
        recipe.learned_by_run = run_id
        entity = self.g.add_entity(Entity(
            name=recipe.source_id, entity_type=_RECIPE_ENTITY_TYPE,
            source_docs=[source_uri] if source_uri else [],
            confidence=recipe.confidence))
        conf = confidence if confidence is not None else recipe.confidence
        self._write_state_claim(
            entity=entity, kind=_KIND_RECIPE, payload=recipe.to_payload()["payload"],
            run=run, source_uri=source_uri or f"recipe://{recipe.source_id}",
            source_title=f"recipe seed for {recipe.source_id}", confidence=conf)
        return recipe

    def recipe_for(self, source_id: str) -> Optional[AcquisitionRecipe]:
        """READ a source's recipe BEFORE acquiring. None if never learned.

        This is the read half of the loop: an agent calls it first so it does
        not re-discover how to read a page the toolkit already knows.
        """
        entity = self._entity(_RECIPE_ENTITY_TYPE, source_id)
        if entity is None:
            return None
        claim = self._current_claim(entity.id)
        if claim is None:
            return None
        return AcquisitionRecipe.from_payload(json.loads(claim.text)["payload"])

    def all_recipes(self) -> list:
        out = []
        for node in self.g.nodes_of_type(NodeType.ENTITY):
            if node.entity_type == _RECIPE_ENTITY_TYPE:  # type: ignore[attr-defined]
                r = self.recipe_for(node.name)  # type: ignore[attr-defined]
                if r is not None:
                    out.append(r)
        return out

    # --- techniques: register + READ ------------------------------------------
    def register_technique(self, technique: AcquisitionTechnique, *, run_id: str,
                          source_uri: str = "", confidence: float = 0.7
                          ) -> AcquisitionTechnique:
        """Store a reusable technique. Idempotent by name (no-op if present)."""
        existing = self.technique(technique.name)
        if existing is not None:
            return existing
        run = self._run_node(run_id)
        technique.learned_by_run = run_id
        entity = self.g.add_entity(Entity(
            name=technique.name, entity_type=_TECHNIQUE_ENTITY_TYPE,
            confidence=confidence))
        self._write_state_claim(
            entity=entity, kind=_KIND_TECHNIQUE,
            payload=technique.to_payload()["payload"], run=run,
            source_uri=source_uri or f"technique://{technique.name}",
            source_title=f"technique library seed: {technique.name}",
            confidence=confidence)
        return technique

    def technique(self, name: str) -> Optional[AcquisitionTechnique]:
        entity = self._entity(_TECHNIQUE_ENTITY_TYPE, name)
        if entity is None:
            return None
        claim = self._current_claim(entity.id)
        if claim is None:
            return None
        return AcquisitionTechnique.from_payload(json.loads(claim.text)["payload"])

    def all_techniques(self) -> list:
        out = []
        for node in self.g.nodes_of_type(NodeType.ENTITY):
            if node.entity_type == _TECHNIQUE_ENTITY_TYPE:  # type: ignore[attr-defined]
                t = self.technique(node.name)  # type: ignore[attr-defined]
                if t is not None:
                    out.append(t)
        return out

    def best_technique(self, signal: str) -> Optional[AcquisitionTechnique]:
        """Given a page SIGNAL (e.g. 'js_shell', 'has_jsonld', 'squarespace'),
        return the highest-success applicable technique.

        Applicability = the signal is in the technique's applies_to_signals.
        Ranking = effective (smoothed) success rate, descending; ties break
        toward the CHEAPER technique, then by name for determinism (cost
        discipline: the cheapest method that meets the bar wins).
        """
        _COST_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}
        candidates = [t for t in self.all_techniques()
                      if signal in t.applies_to_signals]
        if not candidates:
            return None
        candidates.sort(key=lambda t: (
            -t.effective_success_rate(),
            _COST_ORDER.get(t.cost_hint, 1),
            t.name,
        ))
        return candidates[0]

    # --- the WRITE half of the loop: record an outcome ------------------------
    def record_outcome(self, source_id: str, *, run_id: str, method: str,
                       technique: Optional[str], yield_count: int, success: bool,
                       cost: str = "low", notes: str = "",
                       at: Optional[float] = None) -> AcquisitionRecipe:
        """RECORD what happened after an acquisition, improving the toolkit.

        Updates the source's recipe (last_*, median_yield, reliability, the
        needs_rediscovery trigger) AND the named technique's success stats, all
        as provenance-bearing brain writes that SUPERSEDE the prior state. This
        is the write half of the loop: whoever acquires this source next reads
        the improved recipe, and whoever faces this technique's signal next
        reads its improved success rate.

        `success` is the caller's report that the acquisition mechanically
        worked; an "effective" success additionally requires yield_count > 0
        (a page that returns zero events did not really succeed). Two
        consecutive zero-yield acquisitions flip needs_rediscovery=True and
        lower confidence — the moved/changed-page trigger (e.g. the
        AI_EXTRACT_ZERO_EVENTS_SOURCE_MAY_HAVE_MOVED signal).
        """
        recipe = self.recipe_for(source_id)
        if recipe is None:
            raise AcquisitionError(
                f"no recipe for {source_id!r} to record an outcome against — "
                "register or seed it first (read-before-acquire)."
            )
        run = self._run_node(run_id)
        stamp = at if at is not None else time.time()
        effective = bool(success) and yield_count > 0

        recipe.attempts += 1
        recipe.last_attempt_at = stamp
        recipe.last_yield = int(yield_count)
        recipe.learned_by_run = run_id
        recipe.yield_history = (recipe.yield_history + [int(yield_count)]
                                )[-_MAX_YIELD_HISTORY:]
        recipe.median_yield = float(statistics.median(recipe.yield_history))
        # Evolving reliability, EWMA toward 1.0 on an effective success else 0.0.
        target = 1.0 if effective else 0.0
        recipe.reliability = round(
            (1 - _RELIABILITY_ALPHA) * recipe.reliability
            + _RELIABILITY_ALPHA * target, 6)
        if effective:
            recipe.successes += 1
            recipe.last_success_at = stamp
            recipe.consecutive_empty = 0
            recipe.needs_rediscovery = False
            recipe.confidence = round(min(1.0, recipe.confidence + 0.05), 6)
        else:
            recipe.consecutive_empty += 1
            recipe.confidence = round(max(0.0, recipe.confidence - 0.1), 6)
            if recipe.consecutive_empty >= _REDISCOVERY_THRESHOLD:
                recipe.needs_rediscovery = True
        if cost:
            recipe.cost_hint = cost
        recipe.version += 1

        entity = self._entity(_RECIPE_ENTITY_TYPE, source_id)
        assert entity is not None  # recipe_for succeeded, so the entity exists
        obs_uri = recipe.calendar_url or f"recipe://{source_id}"
        self._write_state_claim(
            entity=entity, kind=_KIND_RECIPE, payload=recipe.to_payload()["payload"],
            run=run, source_uri=obs_uri,
            source_title=(f"acquisition outcome {source_id} "
                          f"(method={method}, yield={yield_count}, ok={effective})"
                          + (f" — {notes}" if notes else "")),
            confidence=recipe.confidence)

        if technique:
            self._record_technique_use(technique, success=effective, run=run)
        return recipe

    def _record_technique_use(self, name: str, *, success: bool,
                              run: AgentRun) -> None:
        """Update a technique's running success stats and supersede its state."""
        tech = self.technique(name)
        if tech is None:
            raise AcquisitionError(
                f"outcome names technique {name!r} which is not in the library — "
                "seed or register it before recording it (no phantom techniques)."
            )
        tech.attempts += 1
        if success:
            tech.successes += 1
        tech.version += 1
        tech.learned_by_run = run.objective.replace("acq-run:", "")
        entity = self._entity(_TECHNIQUE_ENTITY_TYPE, name)
        assert entity is not None
        self._write_state_claim(
            entity=entity, kind=_KIND_TECHNIQUE,
            payload=tech.to_payload()["payload"], run=run,
            source_uri=f"technique://{name}",
            source_title=f"technique use: {name} (ok={success})",
            confidence=round(tech.effective_success_rate(), 6))
