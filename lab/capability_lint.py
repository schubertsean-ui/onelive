#!/usr/bin/env python3
"""Mechanism for directive D2 — "Can does not mean do or must or will."

The failure this catches is specific: an agent writing "I can verify those
URLs" or "we could measure that" INSTEAD OF DOING IT, and treating the offer as
if it discharged the task. On 2026-08-06 that exact sentence — "I can verify
them from CI" — sat in a deliverable while fourteen unverified URLs stayed in
the document.

The rule: a first-person capability claim is only allowed when it is
immediately backed by evidence that the thing was DONE, or explicitly marked as
a deliberate deferral with a reason.

  ALLOWED   "I verified these from CI (run 31115936202)"
  ALLOWED   "We can render these — done in lab/verify_urls.py"
  ALLOWED   "I can measure the split [NOT DONE: needs founder GO first]"
  REJECTED  "I can verify those URLs from CI."

Evidence counts as any of:
  * a workflow run id            e.g. run 31115936202
  * a repository path that EXISTS on disk, in backticks
  * a `[NOT DONE: reason]` marker — an honest, recorded deferral

`lab/assemble_handoff.py` calls this and refuses to build the handoff if any
capability claim is unbacked. So the offer-instead-of-action failure cannot
reach the founder through that document.

Run standalone: python3 lab/capability_lint.py [paths...]
"""
from __future__ import annotations

import os
import re
import sys

DEFAULT_TARGETS = [
    "lab/EXTERNAL_AI_BRIEF.md",
    "lab/PLAN.md",
    "lab/PIPELINE_COMPONENTS.md",
    "lab/FIX_01_JSONLD.md",
    "lab/NEW_SESSION_PROMPT.md",
    "docs/ops/CODE_EVALUATION_2026-08-06.md",
    "docs/ops/CRAWLER_DEPTH_DIAGNOSIS_2026-08-06.md",
]

# First-person capability, followed by an AGENT action.
#
# Two exclusions, learned by running this and reading the hits:
#   * instructions written TO someone else ("you can render these") are
#     guidance, not an offer standing in for work;
#   * descriptions of what the SOFTWARE can do ("we can read pages 1-5 of a
#     calendar") are statements of system behaviour, not offers. The first
#     version of this file flagged four of those and zero real defects.
#
# The failure being caught is narrow and specific: the agent saying it COULD
# perform a verification action, instead of performing it.
_AGENT_ACTION = (
    r"verify|verified|check|measure|run|test|build|fix|find|probe|dispatch|"
    r"scan|audit|prove|confirm|validate|count|re-?derive|query|crawl|"
    r"extract|reproduce|replicate|benchmark|profile|sample")
_CAPABILITY = re.compile(
    rf"\b(?:I|we)\s+(?:can|could|would be able to|am able to|are able to)"
    rf"\s+(?:\w+\s+){{0,3}}?(?:{_AGENT_ACTION})\b",
    re.I)

_RUN_ID = re.compile(r"\brun\s+\d{8,}\b", re.I)
_PATH = re.compile(r"`([\w./\-]+\.(?:py|md|json|ts|tsx|yml|yaml|sql|jsonl))`")
_NOT_DONE = re.compile(r"\[NOT DONE:[^\]]+\]")
# Past tense adjacent to the claim means it was actually carried out.
_DID = re.compile(
    r"\b(?:did|done|ran|verified|measured|built|fixed|dispatched|committed|"
    r"pushed|executed|produced|counted|re-derived)\b", re.I)


def backed(line: str, context: str) -> bool:
    """Is this capability claim backed by evidence, or honestly deferred?"""
    if _NOT_DONE.search(context):
        return True
    if _RUN_ID.search(context):
        return True
    if _DID.search(context):
        return True
    for path in _PATH.findall(context):
        if os.path.exists(path):
            return True
    return False


def scan(path: str) -> list[tuple[int, str]]:
    if not os.path.exists(path):
        return []
    lines = open(path).read().split("\n")
    bad = []
    for i, line in enumerate(lines):
        if not _CAPABILITY.search(line):
            continue
        # Context = the claim plus the two lines after it, because prose wraps
        # and the evidence often lands on the next line.
        context = "\n".join(lines[i:i + 3])
        if not backed(line, context):
            bad.append((i + 1, line.strip()))
    return bad


# The detector must be PROVEN, not trusted. These run on every invocation: a
# linter that silently stopped matching would be worse than no linter.
_SELF_TEST_MUST_FLAG = [
    "I can verify those URLs from CI.",
    "We could measure the split if needed.",
    "I could probe the top candidates.",
]
_SELF_TEST_MUST_PASS = [
    "We can read pages 1-5 of a calendar.",          # system behaviour
    "You can render these with the headless browser.",  # instruction to others
    "I verified these from CI (run 31115936202).",   # actually done
    "I can measure the split [NOT DONE: awaiting founder GO].",  # deferred
]


def self_test() -> None:
    for text in _SELF_TEST_MUST_FLAG:
        if not (_CAPABILITY.search(text) and not backed(text, text)):
            raise SystemExit(f"capability_lint SELF-TEST FAILED — this should "
                             f"have been flagged and was not: {text!r}")
    for text in _SELF_TEST_MUST_PASS:
        if _CAPABILITY.search(text) and not backed(text, text):
            raise SystemExit(f"capability_lint SELF-TEST FAILED — this should "
                             f"have passed and was flagged: {text!r}")


def main(argv: list[str]) -> int:
    self_test()
    targets = argv[1:] or DEFAULT_TARGETS
    total = 0
    for path in targets:
        bad = scan(path)
        if bad:
            print(f"\n{path}")
            for lineno, text in bad:
                print(f"  line {lineno}: {text[:110]}")
            total += len(bad)

    print()
    if total:
        print(f"capability_lint: FAIL — {total} capability claim(s) with no "
              f"evidence of execution.")
        print("Directive D2: 'Can does not mean do or must or will.' Either DO "
              "the thing and cite the run id or the file, or mark it "
              "[NOT DONE: <reason>] so the deferral is on the record.")
        return 1
    print(f"capability_lint: OK — every first-person capability claim across "
          f"{len(targets)} file(s) is backed by execution or an explicit "
          f"[NOT DONE: ...] marker.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
