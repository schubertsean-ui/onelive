#!/usr/bin/env python3
"""Base-owned structural + contamination lint over SUBJECT exam data.

Greppable summary: `python tools/golden_lint.py <golden.jsonl> <prompt.txt>`
runs the golden-set structural checks and the prompt-contamination checks
as TRUSTED code over untrusted data files (evaluator r14: lint that runs
from the subject checkout can be deleted by the PR it judges — these
checks must be base-owned to be binding). Mirrors the invariants of the
exam test module's lint section; the pytest versions remain for
development, this CLI is what the release gate executes. Exit codes:
0 all checks hold / 1 any violation (fail closed, each printed).
"""
from __future__ import annotations

import json
import re
import sys

# Entry-point script: put the repo root on the path so package imports
# work under direct invocation (python3 tools/<name>.py — how CI calls it).
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from ai.exam_thresholds import SAMPLE_FLOOR

COMPARABLE_FIELDS = (
    "title", "start_time", "end_time", "venue_name",
    "city", "artist_names", "ticket_link", "rsvp_link",
)
ROW_SHAPE = {"id", "source_class", "tags", "text", "expected", "forbidden"}
VALID_EXPECTED = set(COMPARABLE_FIELDS) | {"is_private_rsvp", "private_access", "notes"}


def lint(rows: list[dict], prompt_text: str) -> list[str]:
    problems: list[str] = []
    ids = [r.get("id") for r in rows]
    if len(ids) != len(set(ids)):
        problems.append("duplicate example ids")
    if len(rows) < 40:
        problems.append(f"only {len(rows)} examples (need >= 40)")
    for r in rows:
        rid = r.get("id", "<no id>")
        if not ROW_SHAPE <= set(r):
            problems.append(f"{rid}: missing documented row keys {ROW_SHAPE - set(r)}")
            continue
        if not isinstance(r["expected"], dict):
            problems.append(f"{rid}: expected is not an object")
            continue
        if not isinstance(r["tags"], list) or not all(isinstance(t, str) for t in r["tags"]):
            problems.append(f"{rid}: tags is not a list of strings")
            continue
        if not isinstance(r["text"], str) or not r["text"].strip():
            problems.append(f"{rid}: text missing or not a string")
        if not set(r["expected"]) <= VALID_EXPECTED:
            problems.append(f"{rid}: unknown expected keys")
    facts = sum(1 for r in rows for k in COMPARABLE_FIELDS
                if isinstance(r.get("expected"), dict)
                and r["expected"].get(k) not in (None, [], ""))
    if facts < SAMPLE_FLOOR:
        problems.append(f"golden set carries only {facts} expected facts "
                        f"(floor {SAMPLE_FLOOR})")
    tags = [t for r in rows for t in (r.get("tags") or [])]
    if tags.count("injection") < 5:
        problems.append("fewer than 5 injection cases")
    if tags.count("non-event") < 3:
        problems.append("fewer than 3 non-event cases")
    if sum(1 for r in rows if r.get("forbidden")) < 3:
        problems.append("fewer than 3 forbidden-marked injection cases")
    if not any("absence" in t for t in tags):
        problems.append("no absence traps")

    # Contamination: no golden surface form (answer strings) and no 5-word
    # text shingle may appear in the prompt ('Austin' exempt — the platform's
    # real city, present in both null and non-null keys).
    prompt_l = prompt_text.lower()
    names: set[str] = set()
    for r in rows:
        e = r.get("expected") or {}
        for k in ("title", "venue_name", "city"):
            if e.get(k):
                names.add(str(e[k]))
        names.update(str(a) for a in (e.get("artist_names") or []))
    for n in sorted(names):
        if len(n) > 3 and n.lower() != "austin" and n.lower() in prompt_l:
            problems.append(f"golden surface form leaked into the prompt: {n!r}")

    def words(s: str) -> list[str]:
        return re.findall(r"[a-z0-9']+", s.lower())
    prompt_words = " ".join(words(prompt_text))
    for r in rows:
        w = words(str(r.get("text", "")))
        for i in range(len(w) - 4):
            if " ".join(w[i:i + 5]) in prompt_words:
                problems.append(f"{r.get('id')}: golden text phrase leaked "
                                f"into the prompt: {' '.join(w[i:i + 5])!r}")
                break
    return problems


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: golden_lint.py <golden.jsonl> <prompt.txt>", file=sys.stderr)
        return 1
    try:
        rows = [json.loads(line) for line in
                open(argv[0], encoding="utf-8").read().splitlines() if line.strip()]
        prompt_text = open(argv[1], encoding="utf-8").read()
    except (OSError, ValueError) as exc:
        print(f"golden_lint: cannot read inputs ({exc}) — fail closed.",
              file=sys.stderr)
        return 1
    if not rows or not prompt_text.strip():
        print("golden_lint: empty golden set or prompt — fail closed.",
              file=sys.stderr)
        return 1
    problems = lint(rows, prompt_text)
    if problems:
        for p in problems:
            print(f"::error::golden_lint: {p}", file=sys.stderr)
        return 1
    print(f"golden_lint: OK — {len(rows)} examples, structural + "
          "contamination checks hold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
