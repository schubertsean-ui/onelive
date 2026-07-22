"""STATE.md's live handoff must not contradict docs/RECORD.md.

Recurrence surface of the stale-live-incident-state class (third catch,
PR #49 r1, which fired the ledger's threshold-3 repeat-class alarm):
STATE.md's NEXT queue kept instructing "observe the FIRST schedule-event
run -> flip R-008 with its id" after RECORD.md had already resolved
R-008 — the live handoff document directing work at a finished row can
mislead the next operator during an active incident. The class fix is
mechanical: the NEXT queue may not direct work (flip / resolve / close)
at a Record row the Record already marks RESOLVED. The exact PR #49
defect shape is pinned below as a red case.

Scope is deliberately narrow (the NEXT queue only, directive verbs
only): NEXT is the imperative surface — historical narration elsewhere
in STATE.md legitimately names resolved rows.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATE = REPO / "STATE.md"
RECORD = REPO / "docs" / "RECORD.md"

_ROW = re.compile(r"^\|\s*(R-\d{3})\s*\|")
_DIRECTIVE = re.compile(r"(?:flip|resolve|close)\s+(R-\d{3})", re.IGNORECASE)


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


def next_queue_lines(state_text: str) -> list[str]:
    return [
        line
        for line in state_text.splitlines()
        if line.lstrip().startswith("NEXT (")
    ]


def stale_directives(state_text: str, record_text: str) -> list[str]:
    """Record rows the NEXT queue directs work at although already RESOLVED."""
    statuses = record_statuses(record_text)
    stale: list[str] = []
    for line in next_queue_lines(state_text):
        for rid in _DIRECTIVE.findall(line):
            if statuses.get(rid, "").startswith("RESOLVED") and rid not in stale:
                stale.append(rid)
    return stale


def test_live_next_queue_directs_no_resolved_record_row():
    stale = stale_directives(
        STATE.read_text(encoding="utf-8"), RECORD.read_text(encoding="utf-8")
    )
    assert stale == [], (
        f"STATE.md's NEXT queue directs work at already-RESOLVED Record row(s) "
        f"{stale} — the stale-live-incident-state class (see PR #49 r1). "
        f"Rewrite the NEXT item to the current truth (or point it at the "
        f"OPEN successor row) in the same commit that resolves a row."
    )


def test_checker_goes_red_on_the_pr49_defect_shape():
    record = (
        "| R-008 | 2026-07-13 | cron unarmed | Sentinel rule | arming PR "
        "| RESOLVED (2026-07-22, citations) |\n"
    )
    state = (
        "NEXT (top of queue): (1) observe the FIRST schedule-event "
        "ingestion run → flip R-008 with its id.\n"
    )
    assert stale_directives(state, record) == ["R-008"]


def test_open_rows_may_be_directed():
    record = "| R-023 | 2026-07-22 | sparse delivery | cadence directive | 24h measurement | OPEN |\n"
    state = "NEXT (top of queue): (1) measure density, then resolve R-023 per its trigger.\n"
    assert stale_directives(state, record) == []


def test_narration_outside_next_is_ignored():
    record = (
        "| R-008 | 2026-07-13 | cron unarmed | Sentinel rule | arming PR "
        "| RESOLVED (2026-07-22) |\n"
    )
    state = (
        "## Where we are\n"
        "History: we planned to flip R-008 once the first run fired, and did.\n"
        "NEXT (top of queue): (1) unrelated work.\n"
    )
    assert stale_directives(state, record) == []
