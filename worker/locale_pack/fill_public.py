"""FL-010 public write. Read docs/fix-library/FL-010.md first.

Tonight prints venue.name through event.venue_id. One happening is
title + local date (+ listing URL when we have it). Place and clock
are fields. This module is the only writer that fills those fields
on already-public rows.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from worker.locale_pack.desk_fill import FAKE_PLACE, venue_label

PACK_TZ = "America/Chicago"
PLACEHOLDER_VENUE = (
    "unknown venue",
    "venue",
    "unknown",
    "tbd",
    "n/a",
    "na",
    "place to be confirmed",
)


def public_fill_patch(fresh: Dict[str, Any]) -> Dict[str, Any]:
    """Every printed field the public row may take. Never invent."""
    from worker.locale_pack.desk_fill import fill_patch
    fields = []
    if fresh.get("place"):
        fields.append("place")
    if fresh.get("clocks"):
        fields.append("clocks")
    if fresh.get("title"):
        fields.append("title")
    return fill_patch(fresh, fields)


def fill_public_rows(event_id: str, patch: Dict[str, Any]) -> str:
    """Write printed Place/clock onto every public twin of this happening."""
    if not event_id or not patch:
        return "nothing to fill"
    from worker.candidate_store import db  # noqa: PLC0415
    from worker.resolve_entities import resolve_venue_id  # noqa: PLC0415

    raw = str(event_id)
    if raw.startswith("promoted:"):
        raw = raw.split(":", 1)[1]
    label = venue_label(patch.get("venue_name") or "")
    if label.lower() in FAKE_PLACE:
        label = ""
    start = patch.get("start_time")
    title = patch.get("title")
    with db() as conn:
        with conn.cursor() as cur:
            if not title:
                cur.execute("select title from event where event_id = %s::uuid", (raw,))
                row = cur.fetchone()
                title = row[0] if row else None
            venue_id: Optional[str] = None
            if label:
                venue_id = resolve_venue_id(cur, label, "")
            cur.execute(
                """
                update event e
                   set venue_id = case
                         when %s::uuid is null then e.venue_id
                         when e.venue_id is null then %s::uuid
                         when exists (
                           select 1 from venue v
                            where v.venue_id = e.venue_id
                              and (
                                v.name is null
                                or btrim(v.name) = ''
                                or lower(v.name) = any(%s)
                              )
                         ) then %s::uuid
                         else e.venue_id
                       end,
                       start_time = coalesce(%s::timestamptz, e.start_time),
                       title = coalesce(%s, e.title)
                 where e.override_lock = false
                   and e.status in ('scheduled','moved')
                   and (
                        e.event_id = %s::uuid
                     or (
                          %s is not null
                      and lower(btrim(e.title)) = lower(btrim(%s))
                      and timezone(%s, coalesce(%s::timestamptz, e.start_time))::date
                        = timezone(%s, e.start_time)::date
                     )
                   )
                """,
                (venue_id, venue_id, list(PLACEHOLDER_VENUE), venue_id,
                 start, title, raw, title, title, PACK_TZ, start, PACK_TZ),
            )
            filled = cur.rowcount
            ghosts = 0
            if title and start:
                cur.execute(
                    """
                    update event
                       set status = 'cancelled'
                     where override_lock = false
                       and status in ('scheduled','moved')
                       and event_id <> %s::uuid
                       and lower(btrim(title)) = lower(btrim(%s))
                       and timezone(%s, start_time)::date
                         = timezone(%s, %s::timestamptz)::date
                       and (
                         venue_id is null
                         or abs(extract(epoch from (start_time - %s::timestamptz)))
                            between 14400 and 21600
                       )
                    """,
                    (raw, title, PACK_TZ, PACK_TZ, start, start),
                )
                ghosts = cur.rowcount
    return f"filled public twins of {raw} ({filled} row, ghosts={ghosts})"
