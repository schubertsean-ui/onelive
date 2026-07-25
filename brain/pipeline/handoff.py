"""Lossless handoff — the physics that make a phased agent pipeline lose ZERO
information between stages.

Founder requirement (2026-07-25): "ensure there is zero loss from a finder
identifying to a compositor packaging it and then an agent interpreting it and
executing and measuring and evaluating and changing and on and on."

The problem with chaining agents naively is that each stage re-summarizes the
last, and a summary drops fields. Over a 7-stage chain that silent attrition is
how "the finder found it" becomes "the executor never knew." This module makes
loss IMPOSSIBLE-BY-CONSTRUCTION rather than merely discouraged:

  * Every stage's output is a `HandoffArtifact` — a typed payload (a dict of
    named fields) PLUS a `carried` set: the keys that are load-bearing and must
    not vanish.
  * A field can leave the carried set ONLY through an EXPLICIT, RECORDED move:
      - it survives verbatim into the next payload (stays carried), or
      - it is `transformed` (old_key -> new_key, the new key must be present), or
      - it is `consumed` with a written reason (its information was folded into a
        named successor field).
    Any carried key that simply DISAPPEARS with no declaration raises
    `LossyHandoffError` — the handoff FAILS CLOSED. You cannot drop a fact by
    forgetting to mention it; you can only drop it by saying so, on the record.
  * Every handoff is PERSISTED to the knowledge-graph brain as an Artifact node
    (authored by the stage's AgentRun) with a DERIVED_FROM edge to its upstream
    artifact. So the whole chain is durable and traceable: `trace()` walks the
    provenance back to the origin finding, and `origin_fields_preserved()` proves
    the finder's original fields are still recoverable at the far end — after a
    save/reload in a fresh process, not just in memory.

This is the graph-engineering "every output traces to its source" invariant
applied to the AGENT pipeline itself: a lossless conveyor, with a paper trail for
every field's fate.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from brain.graph import Graph
from brain.schema import Artifact, EdgeType

# The content-key under which a handoff's manifest is stored inside the Artifact
# node's `content` string (canonical JSON). Kept as one blob so the whole chunk
# survives a save/load round-trip with the node.
_MANIFEST_VERSION = "handoff/1"


class LossyHandoffError(Exception):
    """Raised when a load-bearing field would vanish across a stage boundary
    without an explicit transform/consume declaration. Fail closed: a handoff
    that cannot account for every carried field does not happen."""


def _canonical(obj) -> str:
    """Deterministic JSON so the content hash is stable across processes."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(payload: Dict, carried: Set[str]) -> str:
    return hashlib.sha256(
        _canonical({"payload": payload, "carried": sorted(carried)}).encode("utf-8")
    ).hexdigest()


@dataclass
class HandoffArtifact:
    """One stage's output: the work chunk (`payload`) + the set of keys that must
    not be silently lost (`carried`) + where it lives in the graph (`artifact_id`)
    + the manifest of what moved (`transformed`/`consumed`) so a field's fate is
    always on the record."""

    stage: str
    payload: Dict
    carried: Set[str]
    artifact_id: str
    upstream_id: Optional[str] = None
    transformed: Dict[str, str] = field(default_factory=dict)
    consumed: Dict[str, str] = field(default_factory=dict)  # key -> reason
    content_hash: str = ""

    def to_manifest(self) -> Dict:
        return {
            "manifest_version": _MANIFEST_VERSION,
            "stage": self.stage,
            "payload": self.payload,
            "carried": sorted(self.carried),
            "upstream_id": self.upstream_id,
            "transformed": self.transformed,
            "consumed": self.consumed,
            "content_hash": self.content_hash,
        }

    @staticmethod
    def from_manifest(m: Dict, artifact_id: str) -> "HandoffArtifact":
        return HandoffArtifact(
            stage=m["stage"],
            payload=m["payload"],
            carried=set(m["carried"]),
            artifact_id=artifact_id,
            upstream_id=m.get("upstream_id"),
            transformed=dict(m.get("transformed", {})),
            consumed=dict(m.get("consumed", {})),
            content_hash=m.get("content_hash", ""),
        )


def _validate_zero_loss(
    upstream: Optional[HandoffArtifact],
    payload: Dict,
    transformed: Dict[str, str],
    consumed: Dict[str, str],
) -> Set[str]:
    """Return the carried set for the NEW artifact, or raise LossyHandoffError.

    The rule, applied to every key the upstream declared load-bearing:
      survives verbatim -> stays carried;
      transformed[key]=new -> new must be in payload, new is carried;
      consumed[key]=reason -> dropped on the record (reason required), not carried;
      otherwise -> LossyHandoffError (a fact cannot vanish unaccounted-for).
    New keys introduced by this stage join the carried set (they are now
    load-bearing for everything downstream).
    """
    new_keys = set(payload.keys())
    if upstream is None:
        # Origin stage (the finder): everything it emits becomes load-bearing.
        return new_keys

    carried_forward: Set[str] = set()
    missing: List[str] = []
    for key in upstream.carried:
        if key in payload:
            carried_forward.add(key)
        elif key in transformed:
            new_key = transformed[key]
            if new_key not in payload:
                missing.append(
                    f"{key!r} declared transformed->{new_key!r} but {new_key!r} "
                    f"is absent from the new payload"
                )
            else:
                carried_forward.add(new_key)
        elif key in consumed:
            if not str(consumed[key]).strip():
                missing.append(f"{key!r} declared consumed but with an empty reason")
            # consumed-with-reason: intentionally not carried, but recorded.
        else:
            missing.append(
                f"{key!r} was carried by the upstream stage and would vanish here "
                f"with no transform/consume declaration"
            )
    if missing:
        raise LossyHandoffError(
            "zero-loss handoff violated — a load-bearing field cannot silently "
            "disappear across a stage boundary. Offending field(s):\n  - "
            + "\n  - ".join(missing)
            + "\nDeclare each as transformed={old: new} or consumed={old: reason}."
        )
    # Everything the stage newly introduced is load-bearing downstream too.
    carried_forward |= (new_keys - carried_forward)
    return carried_forward


def emit_handoff(
    graph: Graph,
    *,
    stage: str,
    run_id: str,
    payload: Dict,
    upstream: Optional[HandoffArtifact] = None,
    transformed: Optional[Dict[str, str]] = None,
    consumed: Optional[Dict[str, str]] = None,
    version: Optional[str] = None,
) -> HandoffArtifact:
    """Validate zero-loss, then persist this stage's output as an Artifact node
    (authored by `run_id`) with a DERIVED_FROM edge to the upstream artifact.

    Returns the new HandoffArtifact. Raises LossyHandoffError before writing
    anything if a carried field would be lost — the graph never records a lossy
    handoff.
    """
    transformed = dict(transformed or {})
    consumed = dict(consumed or {})
    carried = _validate_zero_loss(upstream, payload, transformed, consumed)
    content_hash = _hash(payload, carried)

    art = HandoffArtifact(
        stage=stage,
        payload=payload,
        carried=carried,
        artifact_id="",  # assigned by the graph
        upstream_id=upstream.artifact_id if upstream else None,
        transformed=transformed,
        consumed=consumed,
        content_hash=content_hash,
    )
    node = graph.add_artifact(Artifact(
        name=f"handoff:{stage}",
        authoring_run=run_id,
        version=version or f"{stage}",
        content=_canonical(art.to_manifest()),
    ))
    art.artifact_id = node.id
    if upstream is not None:
        # Provenance: this artifact was DERIVED_FROM its upstream. The chain of
        # these edges is what trace()/origin_fields_preserved() walk.
        graph.add_edge(node.id, upstream.artifact_id, EdgeType.DERIVED_FROM)
    return art


def load_handoff(graph: Graph, artifact_id: str) -> HandoffArtifact:
    """Reconstruct a HandoffArtifact from its persisted Artifact node — the read
    side of the durable handoff (used across a save/reload boundary)."""
    node = graph.get(artifact_id)
    manifest = json.loads(node.content)
    return HandoffArtifact.from_manifest(manifest, artifact_id)


def trace(graph: Graph, artifact_id: str) -> List[HandoffArtifact]:
    """Walk DERIVED_FROM edges from `artifact_id` back to the origin finding,
    returning the chain oldest-first. Proves the whole pipeline is one connected
    provenance chain — nothing orphaned between stages."""
    chain: List[HandoffArtifact] = []
    seen: Set[str] = set()
    cur: Optional[str] = artifact_id
    while cur is not None and cur not in seen:
        seen.add(cur)
        h = load_handoff(graph, cur)
        chain.append(h)
        cur = h.upstream_id
    chain.reverse()
    return chain


def origin_fields_preserved(graph: Graph, artifact_id: str) -> Dict[str, str]:
    """For every load-bearing field the ORIGIN stage emitted, report where it is
    at `artifact_id`: its current key (verbatim or via a transform chain) or the
    stage+reason that consumed it. Never returns "lost" — if a field were lost,
    emit_handoff would have raised at that boundary. This is the zero-loss
    guarantee made queryable: given the far end of the chain, account for every
    original fact.
    """
    chain = trace(graph, artifact_id)
    if not chain:
        return {}
    origin = chain[0]
    # Track each origin key's current name as it flows forward.
    current_name: Dict[str, str] = {k: k for k in origin.carried}
    fate: Dict[str, str] = {}
    for h in chain[1:]:
        for origin_key, name in list(current_name.items()):
            if name in h.consumed:
                fate[origin_key] = f"consumed@{h.stage}: {h.consumed[name]}"
                del current_name[origin_key]
            elif name in h.transformed:
                current_name[origin_key] = h.transformed[name]
    for origin_key, name in current_name.items():
        fate[origin_key] = f"present@{chain[-1].stage}:{name}"
    return fate
