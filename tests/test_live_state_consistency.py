"""STATE.md's live handoff must not contradict docs/RECORD.md.

Recurrence surface of the stale-live-incident-state class (third catch,
PR #49 r1, which fired the ledger's threshold-3 repeat-class alarm):
STATE.md's NEXT queue kept instructing "observe the FIRST schedule-event
run -> flip R-008 with its id" after RECORD.md had already resolved
R-008 — the live handoff document directing work at a finished row can
mislead the next operator during an active incident.

The gate is DEFAULT-DENY (rebuilt at PR #49 r2, which correctly refused
the r1 version's verb-adjacency regex as a false-confidence gate —
"R-008 -> RESOLVED", "close row R-008", "finish R-008", or a wrapped
continuation line all slipped past it): inside the LIVE NEXT block, ANY
mention of a Record row that RECORD.md marks RESOLVED fails the suite
unless the mention is immediately tagged "(RESOLVED" — the tag both
satisfies the gate and keeps the handoff honest on its face. Mentions of
OPEN rows are unrestricted. There is no verb list to evade.

Scope: the FIRST "NEXT (" block only — that is the live imperative
handoff. Preserved historical sections lower in STATE.md legitimately
narrate resolved rows and are out of scope, as is narration outside
NEXT. Ids absent from RECORD.md are out of scope (unknown status).
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
    return ""


def untagged_resolved_mentions(state_text: str, record_text: str) -> list[str]:
    """RESOLVED rows the live NEXT block mentions without the (RESOLVED tag."""
    statuses = record_statuses(record_text)
    block = live_next_block(state_text)
    stale: list[str] = []
    for m in _ID.finditer(block):
        rid = m.group(0)
        if not statuses.get(rid, "").startswith("RESOLVED"):
            continue
        if _RESOLVED_TAG.match(block[m.end() :]):
            continue
        if rid not in stale:
            stale.append(rid)
    return stale


def test_live_next_block_tags_every_resolved_row_mention():
    stale = untagged_resolved_mentions(
        STATE.read_text(encoding="utf-8"), RECORD.read_text(encoding="utf-8")
    )
    assert stale == [], (
        f"STATE.md's live NEXT block mentions already-RESOLVED Record row(s) "
        f"{stale} without the explicit '(RESOLVED' tag — the "
        f"stale-live-incident-state class (PR #49 r1/r2). Either the mention "
        f"is stale work direction (rewrite the item to the current truth or "
        f"point it at the OPEN successor row) or it is a legitimate reference "
        f"that must be tagged 'R-### (RESOLVED ...)' so the handoff is honest "
        f"on its face."
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
    assert untagged_resolved_mentions(state, _RECORD_RESOLVED) == ["R-008"]


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
        assert untagged_resolved_mentions(state, _RECORD_RESOLVED) == [
            "R-008"
        ], f"evasion shape slipped past the gate: {state!r}"


def test_tagged_reference_to_a_resolved_row_is_allowed():
    state = (
        "NEXT (top of queue): (1) density work — R-008 (RESOLVED — arming "
        "proven, do not re-litigate); the open half is R-023.\n"
    )
    record = _RECORD_RESOLVED + (
        "| R-023 | 2026-07-22 | sparse delivery | cadence directive "
        "| 24h measurement | OPEN |\n"
    )
    assert untagged_resolved_mentions(state, record) == []


def test_open_row_mentions_are_unrestricted():
    record = (
        "| R-023 | 2026-07-22 | sparse delivery | cadence directive "
        "| 24h measurement | OPEN |\n"
    )
    state = "NEXT (top of queue): (1) measure density, then resolve R-023 per its trigger.\n"
    assert untagged_resolved_mentions(state, record) == []


def test_historical_sections_below_the_live_block_are_out_of_scope():
    state = (
        "NEXT (top of queue): (1) current work only.\n"
        "\n"
        "## Where we were (2026-07-18)\n"
        "NEXT (top of queue, historical): then: R-008 cron arming.\n"
    )
    assert untagged_resolved_mentions(state, _RECORD_RESOLVED) == []
