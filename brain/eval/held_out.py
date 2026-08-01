"""The HELD-OUT (hidden) memory benchmark for the OneLive brain.

Greppable summary: the TEST split of a classic ML dev/test discipline, applied
to the brain. ``brain/eval/benchmark.py`` is the VISIBLE (dev) set — committed,
readable, and therefore game-able by an agent that optimizes the brain against
those exact questions. This module loads a SEPARATE, DISJOINT set of questions
(``brain/eval/held_out_pages.json``) that reuses the SAME deterministic scorer
(``brain/eval/harness.run_benchmark``), so passing the visible set does NOT
guarantee passing this one. There is no LLM, no network, no spend — the score is
a measured, reproducible fact.

WHY THIS FILE IS ONLY THE "DEV MIRROR"
--------------------------------------
The blindness that stops a self-optimizing PR from gaming the score does NOT
come from this file being secret in the repo (it isn't — nothing checked into
git is). It comes from BASE-OWNERSHIP, exactly like the golden-set extraction exam
(the ``ai/`` exam runner + ``.github/workflows/extraction-eval.yml``): the
authoritative run is ``.github/workflows/brain-held-out-eval.yml`` on
``pull_request_target``, which scores the PR HEAD's brain (``brain/graph.py`` /
``brain/schema.py``) using the BASE ref's copy of THIS file, this JSON, and the
scorer. A PR that edits the held-out questions, lowers the floor, or weakens the
scorer is judged by BASE's copy, not its own. The in-repo copy here is the DEV
MIRROR — it lets us run, test, and iterate the machinery locally; the BASE-run
copy is the judge. See ``docs/strategy/ONE_LIVE_HELDOUT_EVAL_v1.md``.

The corpus is DATA (the JSON), compiled here into the same :class:`Scenario`
objects the visible benchmark uses, and answered by the same brain-backed read
helpers — so a brain that loses an edge, a supersede flag, a validity interval,
or a resolution link scores strictly worse here too.
"""
from __future__ import annotations

import json
import pathlib
from typing import Callable, List, Optional, Tuple

from brain.eval.benchmark import (
    CATEGORIES,
    Gold,
    Query,
    Question,
    Scenario,
    _attr,
    _rel,
)
from brain.eval.harness import MemoryEvalReport, run_benchmark
from brain.graph import Graph
from brain.schema import EdgeType, Entity, Source

HELD_OUT_PATH = pathlib.Path(__file__).resolve().parent / "held_out_pages.json"


class HeldOutError(ValueError):
    """The hidden corpus is missing or malformed. A test set that cannot load
    proves nothing, so every caller fails LOUD on this rather than silently
    scoring an empty benchmark as a pass."""


# --- corpus compilation (JSON data -> Scenario objects) -----------------------
def _build_scenario(spec: dict) -> Scenario:
    """Compile one scenario spec (pure data) into a :class:`Scenario` whose
    ``build`` reconstructs a fresh brain and whose questions carry structured
    :class:`Query`/:class:`Gold` labels. Fail loud on any missing reference —
    an unresolvable key is a corpus bug, never a silent skip."""
    sid = spec["id"]

    def build() -> Tuple[Graph, dict]:
        g = Graph()
        k: dict = {}

        src_ids = {}
        for key, s in spec.get("sources", {}).items():
            src_ids[key] = g.add_source(
                Source(uri=s.get("uri", ""), title=s.get("title", ""))).id

        for key, e in spec.get("entities", {}).items():
            k[key] = g.add_entity(Entity(
                name=e["name"],
                entity_type=e.get("entity_type", ""),
                aliases=list(e.get("aliases", [])),
                source_docs=list(e.get("source_docs", [])),
            )).id

        def ent(key: str) -> str:
            if key not in k:
                raise HeldOutError(
                    f"scenario {sid!r}: unknown entity key {key!r}.")
            return k[key]

        def src(key: str) -> str:
            if key not in src_ids:
                raise HeldOutError(
                    f"scenario {sid!r}: unknown source key {key!r}.")
            return src_ids[key]

        claim_refs = {}
        for a in spec.get("attrs", []):
            claim = _attr(g, ent(a["subject"]), a["predicate"], a["value"],
                          src(a["source"]),
                          valid_from=a.get("valid_from"),
                          valid_to=a.get("valid_to"))
            if a.get("ref"):
                claim_refs[a["ref"]] = claim

        for r in spec.get("rels", []):
            _rel(g, ent(r["subject"]), r["predicate"], ent(r["object"]),
                 src(r["source"]))

        for c in spec.get("contradicts", []):
            if c["a"] not in claim_refs or c["b"] not in claim_refs:
                raise HeldOutError(
                    f"scenario {sid!r}: contradicts references unknown claim "
                    f"ref(s) {c['a']!r}/{c['b']!r}.")
            g.add_edge(claim_refs[c["a"]].id, claim_refs[c["b"]].id,
                       EdgeType.CONTRADICTS)

        for res in spec.get("resolutions", []):
            g.resolve_entities(
                canonical=ent(res["canonical"]),
                others=[ent(o) for o in res["others"]],
                rationale=res["rationale"],
                confidence=float(res["confidence"]),
            )

        return g, k

    questions = [_build_question(sid, q) for q in spec.get("questions", [])]
    return Scenario(sid, build, questions)


def _build_question(sid: str, q: dict) -> Question:
    if q["category"] not in CATEGORIES:
        raise HeldOutError(
            f"scenario {sid!r}: question {q.get('id')!r} has unknown category "
            f"{q['category']!r} (must be one of {CATEGORIES}).")
    query = Query(
        op=q["op"],
        subject=q.get("subject", ""),
        predicate=q.get("predicate", ""),
        path=tuple(q.get("path", ())),
        alias=q.get("alias", ""),
        as_of_date=q.get("as_of_date", ""),
    )
    g = q["gold"]
    gold = Gold(
        value=g.get("value"),
        values=tuple(g["values"]) if g.get("values") is not None else None,
        disputed=bool(g.get("disputed", False)),
        unknown=bool(g.get("unknown", False)),
        expect_source=bool(g.get("expect_source", True)),
    )
    return Question(id=q["id"], category=q["category"], text=q["text"],
                    query=query, gold=gold)


def _load_spec(path: pathlib.Path = HELD_OUT_PATH) -> dict:
    try:
        raw = pathlib.Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise HeldOutError(
            f"cannot read held-out corpus at {path} ({exc}); a hidden test set "
            f"that cannot load proves nothing.") from exc
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise HeldOutError(
            f"held-out corpus at {path} is not valid JSON ({exc}).") from exc
    if not isinstance(data, dict) or not data.get("scenarios"):
        raise HeldOutError(
            f"held-out corpus at {path} has no 'scenarios' — refusing to treat "
            f"an empty benchmark as a valid test set.")
    return data


def load_held_out_benchmark(path: pathlib.Path = HELD_OUT_PATH) -> List[Scenario]:
    """Compile the hidden corpus into scenarios (fail loud if absent/malformed)."""
    data = _load_spec(path)
    scenarios = [_build_scenario(s) for s in data["scenarios"]]
    if not scenarios:
        raise HeldOutError("held-out corpus compiled to zero scenarios.")
    return scenarios


def held_out_baselines(path: pathlib.Path = HELD_OUT_PATH) -> dict:
    """The recorded per-category FLOORS (a one-way ratchet). Fail loud if a
    floor is missing — a ratchet with no floor proves nothing (mirrors
    tools/brain_eval.py.load_baselines)."""
    data = _load_spec(path)
    baselines = data.get("baselines") or {}
    cats = baselines.get("categories")
    if not isinstance(cats, dict) or not cats:
        raise HeldOutError(
            f"held-out corpus at {path} has no 'baselines.categories' map — "
            f"refusing to treat that as a valid floor.")
    missing = [c for c in CATEGORIES if c not in cats]
    if missing:
        raise HeldOutError(
            f"held-out baselines at {path} are missing categories {missing} — "
            f"every category needs a floor.")
    return baselines


# --- the read surface used by disjointness tests + the CLI --------------------
# Compiled once at import (the corpus is fixed data); the CLI + tests reuse it.
HELD_OUT_BENCHMARK: List[Scenario] = load_held_out_benchmark()


def all_held_out_questions() -> list:
    """Flat list of every held-out question (for counts / disjointness proofs)."""
    return [q for s in HELD_OUT_BENCHMARK for q in s.questions]


def run_held_out(answerer=None,
                 mutate: Optional[Callable] = None) -> MemoryEvalReport:
    """Score the held-out set with the SAME deterministic scorer/runner as the
    visible benchmark (``harness.run_benchmark``). ``answerer``/``mutate`` are
    passthroughs so tests can plant regressions and prove the gate can go red."""
    return run_benchmark(scenarios=HELD_OUT_BENCHMARK,
                         answerer=answerer, mutate=mutate)
