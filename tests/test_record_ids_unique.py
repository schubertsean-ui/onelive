"""RECORD.md id uniqueness — the deferral register's row ids must never collide.

Greppable summary: hermetic guard born from the 2026-08-03 R-068/R-069/R-070
collision, where two parallel sessions each allocated the same next-free ids
with different meanings and only a manual catch at merge time prevented the
register from corrupting. The [R-###] tag → row binding (deferral_scan,
skip_record_binding) is only sound while every id names exactly one row, so a
duplicate id is a register-integrity failure, not a style nit. This test makes
the collision mechanically impossible to merge: whichever branch lands second
goes red here until it renumbers (the precedent: later allocation renumbers,
earliest-merged keeps its ids).
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

RECORD = Path(__file__).resolve().parent.parent / "docs" / "RECORD.md"


def _row_ids() -> list[str]:
    ids = []
    for line in RECORD.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(R-\d{3})\s*\|", line)
        if m:
            ids.append(m.group(1))
    return ids


def test_record_file_exists_and_has_rows():
    ids = _row_ids()
    assert ids, "docs/RECORD.md has no R-### rows — the register moved or its format changed; update this guard with it"


def test_no_duplicate_record_ids():
    dupes = {rid: n for rid, n in Counter(_row_ids()).items() if n > 1}
    assert not dupes, (
        f"duplicate RECORD ids {sorted(dupes)} — two rows share an id, so every [R-###] tag pointing at it is "
        "ambiguous. Renumber the later-allocated row(s) to the next free id and update every cross-reference "
        "(the 2026-08-03 R-068/R-069/R-070 collision resolution is the precedent)."
    )
