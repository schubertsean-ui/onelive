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
    "Options": "THREE named ways out, enumerated `1.`/`2.`/`3.` or `(a)`/`(b)`/`(c)` "
               "— never a problem or a limitation with no options",
    "What": "one plain sentence naming the action",
    "Where": "the full URL — a click-path is not a link (docs/DEPLOY.md §console links)",
    "Exactly what to enter": "literal field names and values, or 'nothing to type'",
    "What you will see": "the heading, button or screen state confirming the right "
                         "place, what changes after acting, and what to do if it "
                         "does NOT look like that — a URL plus a shape is not a "
                         "walkthrough",
    "Why this needs you": "what the agent tried and why this cannot be automated "
                          "— the founder's manual work is the scarcest resource, so "
                          "an ask with no such statement is an admission nobody looked",
    "Time": "an honest estimate",
    "Unblocks": "what becomes possible the moment it is done",
    "If you decline": "the cost and the alternative — never present a choice as free",
}
_RECOMMENDATION = "Recommendation"

# An ask that is finished, or folded into another one, is history — the structure
# rules govern LIVE requests. SUPERSEDED counts because merging two asks into one
# is the "an ask you can delete is worth more than an ask you can polish" rule
# working; demanding full fields on the tombstone would punish that.
_RESOLVED = re.compile(r"\bRESOLVED\b|\bDONE\b|\bSUPERSEDED\b")

MIN_OPTIONS = 3

# "Progress, not status" (CLAUDE.md prime directive 6 rule zero): an ask has to say
# how it gets us closer to a world-class go-live, and the only non-negotiable way to
# say that here is to cite a v1 done-criterion number or a BAR row. Prose intent is
# not a citation — `docs/V1.md` numbers the criteria and `docs/BAR.md` letters the
# rows precisely so this can be checked rather than felt.
_GOLIVE_CITATION = re.compile(
    r"(?:done-)?criteri(?:on|a)\s*#?\d"          # "criterion 6", "done-criteria 1"
    r"|\bv1\s+(?:done-)?criteri"                  # "v1 criterion ..."
    r"|\b[A-J]\d{1,2}\b"                          # a BAR row: C2, H7, P1, J11
    r"|\bBAR\b", re.IGNORECASE)


# An enumerated option: "1." / "(a)" / "a)" at the start of a line.
_OPTION_ITEM = re.compile(r"^\s*(?:\d+\.|\([a-z]\)|[a-z]\))\s+\S", re.MULTILINE)
# Where an Options block ENDS: the next line-leading bold label, or a heading.
_NEXT_LABEL = re.compile(r"^\s*(?:[-*]\s+)?\*\*[A-Z]|^#{1,6}\s", re.MULTILINE)


def _field_block(section: str, label: str) -> str | None:
    """Text from `**<label>:**` to the next line-leading bold label, or None."""
    found = re.search(rf"^\s*(?:[-*]\s+)?\*\*{re.escape(label)}\s*(?::|—|-)",
                      section, re.MULTILINE)
    if found is None:
        return None
    rest = section[found.end():]
    nxt = _NEXT_LABEL.search(rest)
    return rest[:nxt.start()] if nxt else rest


def _options_block(section: str) -> str | None:
    """Text from the `**Options:**` label to the next label/heading, or None."""
    return _field_block(section, "Options")


def cites_golive_progress(section: str) -> bool:
    """Does this ask's `Unblocks:` field name what it moves toward go-live?"""
    block = _field_block(section, "Unblocks")
    return block is not None and bool(_GOLIVE_CITATION.search(block))


def count_options(section: str) -> int:
    """How many enumerated options the ask offers (0 if the label is absent)."""
    block = _options_block(section)
    if block is None:
        return 0
    return len(_OPTION_ITEM.findall(block))


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
        # Rule zero: the ask must name what it moves toward go-live.
        if "Unblocks" not in missing and not cites_golive_progress(section):
            findings.append(
                f"Ask {number}: '**Unblocks:**' names no v1 done-criterion number "
                f"and no BAR row — an ask that cannot say which part of a "
                f"world-class go-live it moves is cost, not progress. Cite e.g. "
                f"'v1 done-criterion 1' or 'BAR C2'. CLAUDE.md prime directive 6 "
                f"rule zero.")
        # A present-but-thin Options block is the padding failure the directive
        # calls out: two choices dressed up as three.
        if "Options" not in missing:
            n = count_options(section)
            if n < MIN_OPTIONS:
                findings.append(
                    f"Ask {number}: '**Options:**' lists {n} enumerated option(s), "
                    f"needs {MIN_OPTIONS} — every problem carries three named ways "
                    f"out. If the third is a bad idea, name it AND say why it is "
                    f"bad; do not present two and call it three. CLAUDE.md prime "
                    f"directive 6.")
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
