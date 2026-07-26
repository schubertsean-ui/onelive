#!/usr/bin/env python3
"""Every open founder ask must carry the full structure — no bare requests.

Founder directive 2026-07-26, verbatim: *"codify this action by you for all future
similar needs. never ask me to do something without the specific structure
defined."* It followed a real failure: the founder was told to click through
"Vercel → Settings → Deployment Protection" with no URL, no field values, and no
statement of what it unblocked.

An ask without its structure pushes the work of figuring out the work back onto
the founder, which is the opposite of the job. So every ``### Ask N`` section in
``docs/V1.md`` that is not RESOLVED must carry six labelled fields. RESOLVED asks
are skipped — they are history, and rewriting them would be churn.

Exit codes (``tools/README.md`` convention): 0 clean, 1 findings, 2 tool error.
"""
from __future__ import annotations

import pathlib
import re
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_V1 = _REPO_ROOT / "docs" / "V1.md"

_ASK_HEADING = re.compile(r"^###\s+Ask\s+(\d+)\s*(?:—|-)?\s*(.*)$", re.MULTILINE)

# Each field must appear as a BOLD LABEL at the start of a line. A fact buried in
# prose is not a field the founder can scan on a phone, which is the whole point.
REQUIRED_FIELDS: dict[str, str] = {
    "What": "one plain sentence naming the action",
    "Where": "the full URL — a click-path is not a link (docs/DEPLOY.md §console links)",
    "Exactly what to enter": "literal field names and values, or 'nothing to type'",
    "Time": "an honest estimate",
    "Unblocks": "what becomes possible the moment it is done",
    "If you decline": "the cost and the alternative — never present a choice as free",
}
_RECOMMENDATION = "Recommendation"

_RESOLVED = re.compile(r"\bRESOLVED\b|\bDONE\b")


def _field_present(section: str, label: str) -> bool:
    # `**Label:**` or `**Label —**` at line start, allowing list-item bullets.
    pattern = re.compile(
        rf"^\s*(?:[-*]\s+)?\*\*{re.escape(label)}\s*(?::|—|-)", re.MULTILINE)
    return bool(pattern.search(section))


def _sections(text: str) -> list[tuple[str, str, str]]:
    """Return (ask number, heading text, section body) for each ask."""
    matches = list(_ASK_HEADING.finditer(text))
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((m.group(1), m.group(2), text[m.start():end]))
    return out


def audit(text: str) -> list[str]:
    """Return one finding per structural omission in an OPEN ask."""
    findings: list[str] = []
    for number, heading, section in _sections(text):
        if _RESOLVED.search(heading):
            continue  # history, not a live request
        missing = [label for label in REQUIRED_FIELDS
                   if not _field_present(section, label)]
        if not _field_present(section, _RECOMMENDATION):
            missing.append(_RECOMMENDATION)
        for label in missing:
            why = REQUIRED_FIELDS.get(label, "what you would do, named — not 'your call'")
            findings.append(
                f"Ask {number}: missing '**{label}:**' as a line-leading bold label "
                f"— {why}. CLAUDE.md prime directive 6.")
    return findings


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    path = pathlib.Path(argv[0]) if argv else DEFAULT_V1
    if not path.is_file():
        print(f"founder_ask_lint: ERROR — {path} is not a file", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8")
    asks = _sections(text)
    if not asks:
        # A checker that passes because it matched nothing proves nothing.
        print(f"founder_ask_lint: ERROR — no '### Ask N' sections found in {path}; "
              f"refusing to report a clean pass over an empty set", file=sys.stderr)
        return 2
    findings = audit(text)
    for finding in findings:
        print(finding)
    open_count = sum(1 for _, h, _ in asks if not _RESOLVED.search(h))
    if findings:
        print(f"founder_ask_lint: {len(findings)} violation(s) across {open_count} "
              f"open ask(s) — never ask the founder for something without the "
              f"structure defined.")
        return 1
    print(f"founder_ask_lint: OK — {open_count} open ask(s) of {len(asks)} total, "
          f"every one fully structured.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
