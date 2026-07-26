#!/usr/bin/env python3
"""Every decision record must name what carries it in the repo.

Founder directive 2026-07-26: *"confirm once a decision is made it has been
codified in the code and not left in the session."* A decision that lives only
in a chat reply did not happen — the next session starts from disk and will not
know it exists. Prose in a decision record is better than chat, but prose alone
still does not change behaviour (`docs/HOW_WE_WORK.md` §10, "a prose-only lesson
is an open defect").

So each file in ``docs/memory/decisions/`` must carry a line beginning
``**Codified by:**`` naming the commit, file, gate or RECORD row that implements
it. Staged work is a legitimate answer — cite the ``R-###`` row and its trigger.
"Nothing yet" is also legitimate, stated explicitly, because an honest gap is
findable and a silent one is not.

Exit codes (``tools/README.md`` convention): 0 clean, 1 findings, 2 tool error.
"""
from __future__ import annotations

import pathlib
import re
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DECISIONS_DIR = _REPO_ROOT / "docs" / "memory" / "decisions"

# Must START the line: a mention buried mid-paragraph is prose, not a field a
# reader or a machine can find.
_CODIFIED_RE = re.compile(r"^\*\*Codified by:\*\*\s*(\S.*)$", re.MULTILINE)

# Accepted as naming something real. Deliberately broad — the point is to force
# an explicit answer, not to police its wording.
_SUBSTANTIVE_RE = re.compile(
    r"(R-\d{3}"                      # a Record row (staged, with a trigger)
    r"|[0-9a-f]{7,40}"               # a commit sha
    r"|\.(py|ts|tsx|yml|yaml|sql|md|sh)\b"   # a file
    r"|NOTHING YET\b"                # the honest, explicit gap
    r")"
)


def _display(path: pathlib.Path) -> str:
    """Repo-relative when possible, absolute otherwise.

    `relative_to` RAISES for anything outside the repo root, which would crash
    the tool on a path it was merely asked to check rather than reporting a
    finding about it. A checker that dies on unexpected input is worse than one
    that prints an ugly path.
    """
    try:
        return str(path.relative_to(_REPO_ROOT))
    except ValueError:
        return str(path)


def audit(paths: list[pathlib.Path]) -> list[str]:
    """Return one finding per decision record that fails the rule."""
    findings: list[str] = []
    for path in sorted(paths):
        rel = _display(path)
        text = path.read_text(encoding="utf-8")
        match = _CODIFIED_RE.search(text)
        if match is None:
            findings.append(
                f"{rel}: no '**Codified by:**' line — name the commit, file, gate "
                f"or R-### row that carries this decision in the repo, or write "
                f"'**Codified by:** NOTHING YET — <why, and the trigger>'. "
                f"CLAUDE.md prime directive 6.")
            continue
        value = match.group(1).strip()
        if not _SUBSTANTIVE_RE.search(value):
            findings.append(
                f"{rel}: '**Codified by:**' names nothing findable ({value!r}) — "
                f"cite a commit sha, a file path, an R-### row, or the literal "
                f"'NOTHING YET' with a reason.")
    return findings


def main() -> int:
    if not DECISIONS_DIR.is_dir():
        print(f"decision_codified_lint: ERROR — {DECISIONS_DIR} is not a directory",
              file=sys.stderr)
        return 2
    records = [p for p in DECISIONS_DIR.glob("*.md") if p.name != "README.md"]
    if not records:
        # A checker that passes by finding nothing proves nothing.
        print("decision_codified_lint: ERROR — no decision records found; refusing "
              "to report a clean pass over an empty set", file=sys.stderr)
        return 2
    findings = audit(records)
    for finding in findings:
        print(finding)
    if findings:
        print(f"decision_codified_lint: {len(findings)} violation(s) of "
              f"{len(records)} record(s) — a decision only in chat did not happen.")
        return 1
    print(f"decision_codified_lint: OK — {len(records)} decision record(s), "
          f"every one names what carries it in the repo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
