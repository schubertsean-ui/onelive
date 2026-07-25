"""Disk persistence for the knowledge-graph brain — the "does not forget" proof.

Greppable summary: save()/load() serialise a Graph to an append-only JSONL
file and rebuild it in a fresh process. The graph is written as a stream of
typed records — one `meta` line, one line per node, one line per edge, one
line per resolution — so the file is greppable and diff-able (disk is
truth), and reloading it reconstructs the FULL graph: superseded nodes stay
superseded, aliases and source_docs come back intact, and the resolution
history survives so a merge is still reversible after a reload.

Chosen format: JSONL over a single JSON blob because it is append-friendly
(the paper frames the world model as an append-only event log the graph is
rebuilt from) and because one-record-per-line survives partial reads and
greps cleanly. dumps()/loads() expose the same round-trip in memory, which
is what the persistence test asserts identity against.

This module reads and writes local files only; it never reaches the network
and never publishes.
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
from typing import Union

from brain.graph import Graph
from brain.schema import NODE_CLASSES, Edge, EdgeType, Node, NodeType


def _node_to_row(node: Node) -> dict:
    """Serialise a node dataclass to a JSON-safe dict (enums -> their value)."""
    row: dict = {"kind": "node"}
    for f in dataclasses.fields(node):
        val = getattr(node, f.name)
        if isinstance(val, NodeType):
            val = val.value
        row[f.name] = val
    return row


def _row_to_node(row: dict) -> Node:
    """Reconstruct a node dataclass from its serialised row."""
    node_type = NodeType(row["node_type"])
    cls = NODE_CLASSES[node_type]
    # node_type is set by each dataclass __post_init__, so drop it from kwargs
    # and let the class re-assert the correct enum.
    kwargs = {k: v for k, v in row.items() if k not in ("kind", "node_type")}
    valid = {f.name for f in dataclasses.fields(cls)}
    unknown = set(kwargs) - valid
    if unknown:
        raise ValueError(
            f"unknown field(s) {sorted(unknown)} for node type {node_type.value} "
            f"— refusing to silently drop data on load."
        )
    return cls(**kwargs)


def dumps(graph: Graph) -> str:
    """Serialise a Graph to a JSONL string (one record per line)."""
    lines = [json.dumps({"kind": "meta", "counter": graph._counter},
                        sort_keys=True)]
    for node in graph.nodes.values():
        lines.append(json.dumps(_node_to_row(node), sort_keys=True))
    for edge in graph.edges.values():
        lines.append(json.dumps({
            "kind": "edge",
            "src": edge.src,
            "dst": edge.dst,
            "edge_type": edge.edge_type.value,
        }, sort_keys=True))
    for rec in graph.resolutions:
        lines.append(json.dumps({"kind": "resolution", "record": rec},
                                sort_keys=True))
    return "\n".join(lines) + "\n"


def loads(text: str) -> Graph:
    """Rebuild a Graph from a JSONL string produced by dumps()."""
    graph = Graph()
    for lineno, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"brain/store: corrupt JSONL at line {lineno}: {exc}")
        kind = row.get("kind")
        if kind == "meta":
            graph._counter = int(row["counter"])
        elif kind == "node":
            node = _row_to_node(row)
            # Insert directly (bypass the typed adders): the graph was already
            # valid when it was saved, and the adders would re-derive edges that
            # are themselves persisted, producing duplicates. Round-trip fidelity
            # requires replaying the stored state exactly, not re-deriving it.
            if node.id in graph.nodes:
                raise ValueError(
                    f"brain/store: duplicate node id {node.id!r} at line {lineno}."
                )
            graph.nodes[node.id] = node
        elif kind == "edge":
            edge = Edge(src=row["src"], dst=row["dst"],
                        edge_type=EdgeType(row["edge_type"]))
            graph.edges[edge.key()] = edge
        elif kind == "resolution":
            graph.resolutions.append(row["record"])
        else:
            raise ValueError(
                f"brain/store: unknown record kind {kind!r} at line {lineno}."
            )
    return graph


def save(graph: Graph, path: Union[str, pathlib.Path]) -> None:
    """Persist a Graph to `path` as JSONL. Overwrites any existing file."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(graph), encoding="utf-8")


def load(path: Union[str, pathlib.Path]) -> Graph:
    """Load a Graph previously written by save()."""
    path = pathlib.Path(path)
    return loads(path.read_text(encoding="utf-8"))
