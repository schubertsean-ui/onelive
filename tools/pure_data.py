#!/usr/bin/env python3
"""Assert a Python file is a PURE DATA module — nothing executable in it.

Greppable summary: `is_pure_data_module(source)` returns True only when the
module's top level consists of an optional docstring plus constant-literal
assignments (strings, numbers, bools, None, and dict/list/tuple literals of
the same) to plain names. Imports, calls, functions, classes, subscript
targets (`globals()[...]`), augmented assignment, conditionals — anything
that could change a binding at import time — makes it impure.

This is the mechanical footing for the exam gate's subject-as-data rule
(evaluator r13): a file the gate certifies by AST extraction must be a file
that CANNOT mean something different when production imports it. The
extractors (extract_prompt_text / extract_routed_model) refuse impure
files, fail closed.
"""
from __future__ import annotations

import ast


def _is_const_literal(node: ast.expr) -> bool:
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.Dict):
        if not all(k is not None and _is_const_literal(k) and _is_const_literal(v)
                   for k, v in zip(node.keys, node.values)):
            return False
        # Duplicate keys are impure (r20 nit): Python import keeps the LAST
        # binding while a first-match reader would certify the first —
        # ambiguous evidence fails closed.
        consts = [k.value for k in node.keys if isinstance(k, ast.Constant)]
        return len(consts) == len(set(consts)) == len(node.keys)
    if isinstance(node, (ast.List, ast.Tuple)):
        # Sets deliberately excluded (r18 nit): the documented pure-data
        # surface is dict/list/tuple of constants, exactly.
        return all(_is_const_literal(e) for e in node.elts)
    return False


def is_pure_data_module(source: str) -> bool:
    """True only if the module top level is: optional docstring, then
    constant-literal assignments to plain names. Anything else — including
    an empty module — is not certifiable data."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    body = list(tree.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]  # module docstring
    if not body:
        return False
    for node in body:
        if isinstance(node, ast.Assign):
            if not all(isinstance(t, ast.Name) for t in node.targets):
                return False
            if not _is_const_literal(node.value):
                return False
        elif isinstance(node, ast.AnnAssign):
            # The ANNOTATION itself is evaluated at import time (r17
            # blocker: `X: __import__("os").system(...) = "safe"` executes
            # on import while the value literal looks innocent). Only a
            # bare-name annotation (str, int, ...) is inert enough.
            if not (isinstance(node.target, ast.Name)
                    and isinstance(node.annotation, ast.Name)
                    and node.value is not None
                    and _is_const_literal(node.value)):
                return False
        else:
            return False
    return True
