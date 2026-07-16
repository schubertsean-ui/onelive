#!/usr/bin/env python3
"""Extract EXTRACTION_SYSTEM_PROMPT from a prompts.py file WITHOUT executing it.

Greppable summary: `python tools/extract_prompt_text.py <path-to-prompts.py>`
prints the string literal assigned to EXTRACTION_SYSTEM_PROMPT, found by AST
parsing only — the file is never imported or executed. This is how the
trusted-harness exam dispatch takes a SUBJECT commit's prompt as inert data
(evaluator r9 doctrine, PR #28: untrusted code must never run with the exam
key; the prompt is a plain string constant, so it can be lifted as text).
Exit codes: 0 printed / 1 not found or not a plain literal (fail closed —
a prompt that needs code execution to produce is not examinable as data).
"""
from __future__ import annotations

import ast
import sys


def extract(source: str) -> str | None:
    """Return the literal assigned to EXTRACTION_SYSTEM_PROMPT, else None."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "EXTRACTION_SYSTEM_PROMPT":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
                    return None  # assigned, but not a plain string literal
    return None


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: extract_prompt_text.py <prompts.py>", file=sys.stderr)
        return 1
    try:
        source = open(argv[0], encoding="utf-8").read()
        text = extract(source)
    except (OSError, SyntaxError) as exc:
        print(f"extract_prompt_text: cannot parse ({exc}) — fail closed.",
              file=sys.stderr)
        return 1
    if not text or not text.strip():
        print("extract_prompt_text: EXTRACTION_SYSTEM_PROMPT not found as a "
              "plain string literal — a prompt that requires executing the "
              "subject's code is not examinable as data (fail closed).",
              file=sys.stderr)
        return 1
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
