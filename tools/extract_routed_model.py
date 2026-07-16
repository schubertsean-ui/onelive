#!/usr/bin/env python3
"""Extract STAGE_MODELS["extraction"] from a model_router.py file as DATA.

Greppable summary: `python tools/extract_routed_model.py <model_router.py>`
prints the extraction model id from the file's top-level STAGE_MODELS dict
literal — found by AST parsing only, never by importing or executing the
subject's code (evaluator r12: the trust decision must run trusted BASE
code; subject expectations arrive as inert data). Fail-closed rules mirror
extract_prompt_text.py: exactly one top-level binding, a plain dict
literal with constant keys/values, and a present "extraction" entry.
Exit codes: 0 printed / 1 anything else.
"""
from __future__ import annotations

import ast
import sys


def extract(source: str) -> str | None:
    """Return STAGE_MODELS["extraction"] as a string, else None."""
    tree = ast.parse(source)

    def binds_name(node) -> bool:
        if isinstance(node, ast.Assign):
            return any(isinstance(t, ast.Name) and t.id == "STAGE_MODELS"
                       for t in node.targets)
        if isinstance(node, ast.AnnAssign):
            return (isinstance(node.target, ast.Name)
                    and node.target.id == "STAGE_MODELS")
        return False

    all_bindings = [n for n in ast.walk(tree) if binds_name(n)]
    top_level = [n for n in tree.body if binds_name(n)]
    if len(all_bindings) != 1 or len(top_level) != 1:
        return None
    value = top_level[0].value
    if not isinstance(value, ast.Dict):
        return None
    for k, v in zip(value.keys, value.values):
        if (isinstance(k, ast.Constant) and k.value == "extraction"
                and isinstance(v, ast.Constant) and isinstance(v.value, str)
                and v.value.strip()):
            return v.value
    return None


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: extract_routed_model.py <model_router.py>", file=sys.stderr)
        return 1
    try:
        text = extract(open(argv[0], encoding="utf-8").read())
    except (OSError, SyntaxError) as exc:
        print(f"extract_routed_model: cannot parse ({exc}) — fail closed.",
              file=sys.stderr)
        return 1
    if text is None:
        print("extract_routed_model: STAGE_MODELS['extraction'] not found as a "
              "single top-level plain dict literal entry (fail closed).",
              file=sys.stderr)
        return 1
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
