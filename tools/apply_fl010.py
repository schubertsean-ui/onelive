#!/usr/bin/env python3
"""Wire FL-010 into tools/desk_ingest.py. Read the Fix Process first.

A first Place on a public row is a fill. Do not call that corroboration.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / "tools" / "desk_ingest.py"

IMPORT_OLD = """from worker.locale_pack.desk_publish import (  # noqa: E402
    DESK_KEY,
    CandidateWrite,
    DeskPublishError,
    DeskRegistration,
    contradicts,
    describe_drift,
    drift,
    plan,
    plan_digest,
    refuse_fixture_write,
    registration_for,
)"""

IMPORT_NEW = """from worker.locale_pack.desk_publish import (  # noqa: E402
    DESK_KEY,
    CandidateWrite,
    DeskPublishError,
    DeskRegistration,
    contradicts,
    describe_drift,
    drift,
    plan,
    plan_digest,
    refuse_fixture_write,
    registration_for,
)
from worker.locale_pack.desk_fill import fill_patch, fills  # noqa: E402"""

SIG_OLD = """def ingest(writes: Sequence[CandidateWrite], *, seen: Mapping[str, tuple],
           create, add_evidence, promote, dispute=dispute_superseded) -> Dict[str, list]:"""

SIG_NEW = """def fill_published_holes(event_id: str, patch: dict) -> str:
    \"\"\"FL-010. Write a first printed Place or clock onto the public row.\"\"\"
    if not event_id or not patch:
        return \"nothing to fill\"
    from worker.candidate_store import db  # noqa: PLC0415
    venue = patch.get(\"venue_name\")
    start = patch.get(\"start_time\")
    title = patch.get(\"title\")
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                \"\"\"\n                update event
                   set venue_name = case
                         when %s is not null and (
                              venue_name is null
                              or btrim(venue_name) = ''
                              or lower(venue_name) in
                                 ('unknown venue','venue','unknown','tbd','n/a'))
                         then %s else venue_name end,
                       start_time = coalesce(%s::timestamptz, start_time),
                       title = coalesce(%s, title),
                       updated_at = now()
                 where event_id = %s::uuid
                   and override_lock = false
                \"\"\",
                (venue, venue, start, title, event_id),
            )
            n = cur.rowcount
    return f\"filled public row {event_id} ({n} row, {sorted(patch)})\"


def ingest(writes: Sequence[CandidateWrite], *, seen: Mapping[str, tuple],
           create, add_evidence, promote, dispute=dispute_superseded,
           fill=fill_published_holes) -> Dict[str, list]:"""

LEAVE_OLD = """else:
                    verdict = (f\"published row {event_id} is left alone: this is \"
                               f\"corroboration, not a contradiction — nothing the \"
                               f\"desks say about it has changed\")"""

LEAVE_NEW = """else:
                    hole = fills(stored, fresh)
                    if hole:
                        patch = fill_patch(fresh, hole)
                        try:
                            verdict = fill(event_id, patch)
                        except Exception as exc:  # noqa: BLE001
                            verdict = (f\"COULD NOT FILL published row {event_id} \"
                                       f\"({type(exc).__name__}: {exc})\")
                            out[\"failed\"].append((w, verdict))
                            continue
                    else:
                        verdict = (f\"published row {event_id} is left alone: this is \"
                                   f\"corroboration, not a contradiction — nothing the \"
                                   f\"desks say about it has changed\")"""


def main() -> int:
    text = INGEST.read_text(encoding=\"utf-8\")
    if \"from worker.locale_pack.desk_fill import\" not in text:
        if IMPORT_OLD not in text:
            raise SystemExit(\"desk_ingest import block not found\")
        text = text.replace(IMPORT_OLD, IMPORT_NEW, 1)
    if \"def fill_published_holes\" not in text:
        if SIG_OLD not in text:
            raise SystemExit(\"ingest() signature not found\")
        text = text.replace(SIG_OLD, SIG_NEW, 1)
    if \"hole = fills(stored, fresh)\" not in text:
        if LEAVE_OLD not in text:
            raise SystemExit(\"leave-alone branch not found\")
        text = text.replace(LEAVE_OLD, LEAVE_NEW, 1)
    INGEST.write_text(text, encoding=\"utf-8\")
    print(\"FL-010 wired into\", INGEST)
    return 0


if __name__ == \"__main__\":
    raise SystemExit(main())
