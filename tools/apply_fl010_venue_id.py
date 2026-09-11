#!/usr/bin/env python3
"""Rewrite fill_published_holes to write event.venue_id.

Tonight prints venue.name via event.venue_id (web/lib/promoted.ts).
Writing event.venue_name does not move the card. event has no venue_name column.
"""
from pathlib import Path

INGEST = Path(__file__).resolve().parents[1] / "tools" / "desk_ingest.py"
START = "def fill_published_holes(event_id: str, patch: dict) -> str:"
END = "def ingest("
NEW = '''def fill_published_holes(event_id: str, patch: dict) -> str:
    """FL-010. Write a first printed Place onto event.venue_id."""
    if not event_id or not patch:
        return "nothing to fill"
    from worker.candidate_store import db  # noqa: PLC0415
    from worker.resolve_entities import resolve_venue_id  # noqa: PLC0415
    raw = str(event_id)
    if raw.startswith("promoted:"):
        raw = raw.split(":", 1)[1]
    venue = (patch.get("venue_name") or "").strip() or None
    start = patch.get("start_time")
    title = patch.get("title")
    with db() as conn:
        with conn.cursor() as cur:
            venue_id = resolve_venue_id(cur, venue, "Austin") if venue else None
            cur.execute(
                """
                update event
                   set venue_id = case
                         when venue_id is null and %s is not null
                         then %s::uuid else venue_id end,
                       start_time = coalesce(%s::timestamptz, start_time),
                       title = coalesce(%s, title)
                 where event_id = %s::uuid
                   and override_lock = false
                """,
                (venue_id, venue_id, start, title, raw),
            )
            n = cur.rowcount
    return f"filled public row {raw} ({n} row, {sorted(patch)})"


'''
SKIP_OLD = (
    "            elif not moved:\n"
    "                out[\"skipped\"].append((\n"
    "                    w, f\"already PUBLIC as event {event_id} (candidate {cid}, \"\n"
    "                       f\"{status}), and the desk still says the same thing \"\n"
    "                       f\"about it\"))\n"
    "                continue\n"
)
SKIP_NEW = (
    "            elif not moved:\n"
    "                if (fresh or {}).get(\"place\"):\n"
    "                    try:\n"
    "                        fill(event_id, fill_patch(fresh, [\"place\"]))\n"
    "                    except Exception as exc:  # noqa: BLE001\n"
    "                        out[\"failed\"].append((\n"
    "                            w, f\"COULD NOT FILL published row {event_id} \"\n"
    "                               f\"({type(exc).__name__}: {exc})\"))\n"
    "                        continue\n"
    "                out[\"skipped\"].append((\n"
    "                    w, f\"already PUBLIC as event {event_id} (candidate {cid}, \"\n"
    "                       f\"{status}), and the desk still says the same thing \"\n"
    "                       f\"about it\"))\n"
    "                continue\n"
)

def main() -> int:
    text = INGEST.read_text(encoding="utf-8")
    start = text.find(START)
    end = text.find(END)
    if start < 0 or end < 0 or end <= start:
        raise SystemExit("fill_published_holes block not found")
    text = text[:start] + NEW + text[end:]
    if "fill(event_id, fill_patch(fresh, [\"place\"]))" not in text:
        if SKIP_OLD not in text:
            raise SystemExit("skip branch not found")
        text = text.replace(SKIP_OLD, SKIP_NEW, 1)
    INGEST.write_text(text, encoding="utf-8")
    print("FL-010 venue_id fill wired")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
