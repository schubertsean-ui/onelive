"""Fill the public cards Tonight shows.

Public identity is title + local date + listing URL.
Place and clock are fields. They do not open a second card.
Tonight prints venue.name through event.venue_id. Write that column.
Replace a placeholder venue. Rewrite a tz-only clock. Hide extra twins.
Never invent a Place. Never insert Unknown Venue.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

FAKE_PLACE = frozenset({
    "unknown venue", "venue", "unknown", "tbd", "n/a", "na",
    "place to be confirmed",
})


def venue_label(place: Optional[str]) -> str:
    raw = (place or "").strip()
    if not raw:
        return ""
    name = raw.split(",", 1)[0].strip()
    if name.lower() in FAKE_PLACE:
        return ""
    return name


def public_patch(fresh: Mapping[str, Any]) -> Dict[str, Any]:
    patch: Dict[str, Any] = {}
    place = venue_label(str(fresh.get("place") or ""))
    if place:
        patch["venue_name"] = place
    clocks = fresh.get("clocks") or []
    if clocks:
        patch["start_time"] = clocks[0]
    if fresh.get("title"):
        patch["title"] = str(fresh["title"]).strip()
    url = (fresh.get("listing_url") or fresh.get("source_url") or "").strip()
    if url:
        patch["listing_url"] = url
    return patch


def fill_public_rows(event_id: Optional[str], patch: Mapping[str, Any]) -> str:
    """Write printed Place and clock onto every Tonight card for this happening."""
    if not patch:
        return "nothing to fill"
    from worker.candidate_store import db  # noqa: PLC0415
    from worker.resolve_entities import resolve_venue_id  # noqa: PLC0415
    raw = str(event_id or "")
    if raw.startswith("promoted:"):
        raw = raw.split(":", 1)[1]
    venue = venue_label(str(patch.get("venue_name") or ""))
    start = patch.get("start_time")
    title = (patch.get("title") or "").strip() or None
    listing = (patch.get("listing_url") or "").strip() or None
    if not venue and not start:
        return "nothing to fill"
    fake = list(FAKE_PLACE)
    with db() as conn:
        with conn.cursor() as cur:
            venue_id = resolve_venue_id(cur, venue, "") if venue else None
            cur.execute(
                """
                update event e
                   set venue_id = case
                         when %s is not null and (
                              e.venue_id is null
                              or exists (
                                  select 1 from venue v
                                   where v.venue_id = e.venue_id
                                     and lower(btrim(coalesce(v.name,'')))
                                         = any(%s)
                              )
                         ) then %s::uuid else e.venue_id end,
                       start_time = coalesce(%s::timestamptz, e.start_time),
                       updated_at = now()
                 where e.override_lock = false
                   and e.status in ('scheduled', 'moved')
                   and (
                        (%s <> '' and e.event_id::text = %s)
                     or (%s is not null and e.source_url = %s)
                     or (%s is not null and lower(btrim(e.title)) = lower(%s)
                         and e.start_time is not null)
                   )
                """,
                (
                    venue_id, fake, venue_id, start,
                    raw, raw,
                    listing, listing,
                    title, title,
                ),
            )
            filled = cur.rowcount
            hidden = 0
            if title:
                cur.execute(
                    """
                    update event
                       set status = 'cancelled',
                           updated_at = now()
                     where override_lock = false
                       and event_id in (
                        select event_id from (
                            select event_id,
                                   row_number() over (
                                       partition by lower(btrim(title)),
                                         coalesce(
                                           (start_time at time zone
                                              'America/Chicago')::date,
                                           start_time::date)
                                       order by (venue_id is null),
                                                start_time desc nulls last,
                                                event_id
                                   ) as rn
                              from event
                             where status in ('scheduled', 'moved')
                               and lower(btrim(title)) = lower(%s)
                        ) ranked
                        where rn > 1
                     )
                    """,
                    (title,),
                )
                hidden = cur.rowcount
    return (
        f"filled public happening {title or raw} "
        f"({filled} row, hidden {hidden}, {venue or 'no place'})"
    )
