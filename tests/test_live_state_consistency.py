"""STATE.md's live handoff must not contradict docs/RECORD.md.

Recurrence surface of the stale-live-incident-state class (third catch,
PR #49 r1, which fired the ledger's threshold-3 repeat-class alarm):
STATE.md's NEXT queue kept instructing "observe the FIRST schedule-event
run -> flip R-008 with its id" after RECORD.md had already resolved
R-008 — the live handoff document directing work at a finished row can
mislead the next operator during an active incident.

The gate is TWO LAYERS (r2 refused the r1 verb-adjacency regex as a
false-confidence gate; r3 refused the r2 tag as a blanket bypass that
could launder a directive — "flip R-008 (RESOLVED ...)" passed while
still directing live work at a resolved row):

1. DEFAULT-DENY tag layer: inside the LIVE NEXT block, ANY mention of a
   Record row that RECORD.md marks RESOLVED fails unless immediately
   tagged "(RESOLVED" — no verb list to evade, and every surviving
   mention displays its resolved status to the reader on its face.
2. DIRECTIVE layer: a directive verb immediately preceding the row id
   fails REGARDLESS of the tag — the tag cannot launder a directive.

Honest limit, stated so the gate never overclaims (the r2/r3 lesson):
layer 2 is a deny-list and deny-lists are incomplete by nature — a novel
directive verb with a tagged id can pass layer 2. What the gate
guarantees is exactly: no untagged stale mention, and no known-directive
laundering; a surviving mention is always visibly "(RESOLVED"-flagged
text whose staleness a reader can see. Intent understanding stays with
the evaluator review, not this gate.

Scope: the FIRST "NEXT (" block only — that is the live imperative
handoff. Preserved historical sections lower in STATE.md legitimately
narrate resolved rows and are out of scope, as is narration outside
NEXT. Ids absent from RECORD.md are out of scope (unknown status). A
STATE.md with NO live NEXT block fails loud (r3 nit) — silent pass on a
missing handoff would itself be a false-confidence gate.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATE = REPO / "STATE.md"
RECORD = REPO / "docs" / "RECORD.md"

_ROW = re.compile(r"^\|\s*(R-\d{3})\s*\|")
_ID = re.compile(r"R-\d{3}")
_RESOLVED_TAG = re.compile(r"\s*\(RESOLVED\b")
# Directive verbs that may not immediately precede a RESOLVED row id,
# tagged or not (optionally through "row"/"the"/"on"). Deny-list —
# incomplete by nature; see the module docstring's honest limit.
_DIRECTIVE_BEFORE = re.compile(
    r"(?:flip|resolve|close|finish|work|observe|re-?run|re-?open|complete|"
    r"do|address|action|handle|fix|deliver|drive|escalate)\s+"
    r"(?:row\s+|the\s+|on\s+)?$",
    re.IGNORECASE,
)


def record_statuses(record_text: str) -> dict[str, str]:
    """Map R-### -> its status cell's leading keyword (OPEN/RESOLVED/...)."""
    statuses: dict[str, str] = {}
    for line in record_text.splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        statuses[m.group(1)] = cells[-1].split("(")[0].strip().upper()
    return statuses


def live_next_block(state_text: str) -> str:
    """The first NEXT block: from its opening line to a blank/heading line.

    Paragraph-aware so a wrapped continuation line cannot evade the gate
    (r2 finding).
    """
    lines = state_text.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("NEXT ("):
            block = [line]
            for cont in lines[i + 1 :]:
                if not cont.strip() or cont.lstrip().startswith("#"):
                    break
                block.append(cont)
            return "\n".join(block)
    raise AssertionError(
        "STATE.md has no live 'NEXT (' block — the live handoff is missing, "
        "which this gate must fail loud on rather than silently pass (PR #49 "
        "r3 nit)."
    )


def stale_resolved_mentions(state_text: str, record_text: str) -> list[str]:
    """RESOLVED rows the live NEXT block mishandles.

    A mention is stale when it is untagged (layer 1) OR when a directive
    verb immediately precedes the id, tag or no tag (layer 2).
    """
    statuses = record_statuses(record_text)
    block = live_next_block(state_text)
    stale: list[str] = []
    for m in _ID.finditer(block):
        rid = m.group(0)
        if not statuses.get(rid, "").startswith("RESOLVED"):
            continue
        tagged = bool(_RESOLVED_TAG.match(block[m.end() :]))
        directed = bool(_DIRECTIVE_BEFORE.search(block[: m.start()]))
        if tagged and not directed:
            continue
        if rid not in stale:
            stale.append(rid)
    return stale


def test_live_next_block_tags_every_resolved_row_mention():
    stale = stale_resolved_mentions(
        STATE.read_text(encoding="utf-8"), RECORD.read_text(encoding="utf-8")
    )
    assert stale == [], (
        f"STATE.md's live NEXT block mishandles already-RESOLVED Record "
        f"row(s) {stale} — either an untagged mention or a directive verb "
        f"aimed at a resolved row (the stale-live-incident-state class, "
        f"PR #49 r1/r2/r3). Rewrite the item to the current truth, point it "
        f"at the OPEN successor row, or tag a legitimate non-directive "
        f"reference 'R-### (RESOLVED ...)'."
    )


_RECORD_RESOLVED = (
    "| R-008 | 2026-07-13 | cron unarmed | Sentinel rule | arming PR "
    "| RESOLVED (2026-07-22, citations) |\n"
)


def test_gate_goes_red_on_the_r1_defect_shape():
    state = (
        "NEXT (top of queue): (1) observe the FIRST schedule-event "
        "ingestion run → flip R-008 with its id.\n"
    )
    assert stale_resolved_mentions(state, _RECORD_RESOLVED) == ["R-008"]


def test_gate_goes_red_on_every_r2_evasion_shape():
    evasions = [
        "NEXT (top of queue): (1) R-008 → RESOLVED this commit.",
        "NEXT (top of queue): (1) close row R-008.",
        "NEXT (top of queue): (1) finish R-008.",
        "NEXT (top of queue): (1) work R-008 next.",
        # wrapped continuation line
        "NEXT (top of queue): (1) first item;\n(2) then flip R-008 now.",
    ]
    for state in evasions:
        assert stale_resolved_mentions(state, _RECORD_RESOLVED) == [
            "R-008"
        ], f"evasion shape slipped past the gate: {state!r}"


def test_gate_goes_red_on_every_r3_tag_laundering_shape():
    launderings = [
        "NEXT (top of queue): (1) close row R-008 (RESOLVED ...).",
        "NEXT (top of queue): (1) finish R-008 (RESOLVED ...).",
        "NEXT (top of queue): (1) flip R-008 (RESOLVED ...) with its id.",
    ]
    for state in launderings:
        assert stale_resolved_mentions(state, _RECORD_RESOLVED) == [
            "R-008"
        ], f"tag laundered a directive past the gate: {state!r}"


def test_missing_live_next_block_fails_loud():
    import pytest

    with pytest.raises(AssertionError, match="no live 'NEXT"):
        stale_resolved_mentions("# STATE\nno queue here\n", _RECORD_RESOLVED)


def test_tagged_reference_to_a_resolved_row_is_allowed():
    state = (
        "NEXT (top of queue): (1) density work — R-008 (RESOLVED — arming "
        "proven, do not re-litigate); the open half is R-023.\n"
    )
    record = _RECORD_RESOLVED + (
        "| R-023 | 2026-07-22 | sparse delivery | cadence directive "
        "| 24h measurement | OPEN |\n"
    )
    assert stale_resolved_mentions(state, record) == []


def test_open_row_mentions_are_unrestricted():
    record = (
        "| R-023 | 2026-07-22 | sparse delivery | cadence directive "
        "| 24h measurement | OPEN |\n"
    )
    state = "NEXT (top of queue): (1) measure density, then resolve R-023 per its trigger.\n"
    assert stale_resolved_mentions(state, record) == []


def test_historical_sections_below_the_live_block_are_out_of_scope():
    state = (
        "NEXT (top of queue): (1) current work only.\n"
        "\n"
        "## Where we were (2026-07-18)\n"
        "NEXT (top of queue, historical): then: R-008 cron arming.\n"
    )
    assert stale_resolved_mentions(state, _RECORD_RESOLVED) == []
