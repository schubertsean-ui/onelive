#!/usr/bin/env python3
"""Wire FL-010 into tools/desk_ingest.py. Read the Fix Process first.

A first Place on a public row is a fill. Do not call that corroboration.
The candidate statement can already hold Place while event.venue_name is empty.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / "tools" / "desk_ingest.py"

IMPORT_NEEDLE = "    registration_for,\n)"
IMPORT_ADD = "    registration_for,\n)\nfrom worker.locale_pack.desk_fill import fill_patch, fills  # noqa: E402"

SIG_NEEDLE = (
    "def ingest(writes: Sequence[CandidateWrite], *, seen: Mapping[str, tuple],\n"
    "           create, add_evidence, promote, dispute=dispute_superseded) -> Dict[str, list]:"
)

FILL_FN = '''def fill_published_holes(event_id: str, patch: dict) -> str:
    """FL-010. Write a first printed Place or clock onto the public row."""
    if not event_id or not patch:
        return "nothing to fill"
    from worker.candidate_store import db  # noqa: PLC0415
    raw = str(event_id)
    if raw.startswith("promoted:"):
        raw = raw.split(":", 1)[1]
    venue = patch.get("venue_name")
    start = patch.get("start_time")
    title = patch.get("title")
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update event
                   set venue_name = case
                         when %s is not null and (
                              venue_name is null
                              or btrim(venue_name) = ''
                              or lower(venue_name) in
                                 ('unknown venue','venue','unknown','tbd','n/a',
                                  'place to be confirmed'))
                         then %s else venue_name end,
                       start_time = coalesce(%s::timestamptz, start_time),
                       title = coalesce(%s, title),
                       updated_at = now()
                 where event_id = %s::uuid
                   and override_lock = false
                """,
                (venue, venue, start, title, raw),
            )
            n = cur.rowcount
    return f"filled public row {raw} ({n} row, {sorted(patch)})"


'''

SIG_NEW = (
    FILL_FN
    + "def ingest(writes: Sequence[CandidateWrite], *, seen: Mapping[str, tuple],\n"
    + "           create, add_evidence, promote, dispute=dispute_superseded,\n"
    + "           fill=fill_published_holes) -> Dict[str, list]:"
)

OLD_HOLE = (
    "                    hole = fills(stored, fresh)\n"
    "                    if hole:"
)

NEW_HOLE = (
    "                    hole = fills(stored, fresh)\n"
    "                    if not hole and fresh.get(\"place\"):\n"
    "                        hole = [\"place\"]\n"
    "                    if hole:"
)

LEAVE_NEEDLE = (
    "else:\n"
    "                    verdict = (f\"published row {event_id} is left alone: this is \"\n"
    "                               f\"corroboration, not a contradiction \u2014 nothing the \"\n"
    "                               f\"desks say about it has changed\")"
)

LEAVE_NEW = (
    "else:\n"
    "                    hole = fills(stored, fresh)\n"
    "                    if not hole and fresh.get(\"place\"):\n"
    "                        hole = [\"place\"]\n"
    "                    if hole:\n"
    "                        patch = fill_patch(fresh, hole)\n"
    "                        try:\n"
    "                            verdict = fill(event_id, patch)\n"
    "                        except Exception as exc:  # noqa: BLE001\n"
    "                            verdict = (f\"COULD NOT FILL published row {event_id} \"\n"
    "                                       f\"({type(exc).__name__}: {exc})\")\n"
    "                            out[\"failed\"].append((w, verdict))\n"
    "                            continue\n"
    "                    else:\n"
    "                        verdict = (f\"published row {event_id} is left alone: this is \"\n"
    "                                   f\"corroboration, not a contradiction \u2014 nothing the \"\n"
    "                                   f\"desks say about it has changed\")"
)


def main() -> int:
    text = INGEST.read_text(encoding="utf-8")
    if "from worker.locale_pack.desk_fill import" not in text:
        if IMPORT_NEEDLE not in text:
            raise SystemExit("desk_ingest import block not found")
        text = text.replace(IMPORT_NEEDLE, IMPORT_ADD, 1)
    if "def fill_published_holes" not in text:
        if SIG_NEEDLE not in text:
            raise SystemExit("ingest() signature not found")
        text = text.replace(SIG_NEEDLE, SIG_NEW, 1)
    if "if not hole and fresh.get(\"place\"):" not in text:
        if OLD_HOLE in text:
            text = text.replace(OLD_HOLE, NEW_HOLE, 1)
        elif LEAVE_NEEDLE in text:
            text = text.replace(LEAVE_NEEDLE, LEAVE_NEW, 1)
        else:
            raise SystemExit("leave-alone / hole branch not found")
    INGEST.write_text(text, encoding="utf-8")
    print("FL-010 wired into", INGEST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
