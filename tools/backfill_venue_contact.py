#!/usr/bin/env python3
"""Backfill venue_url + venue_phone onto existing licensed_event rows.

The two columns (migration 0014) are populated going forward by the importer,
but the ~1,300 rows imported BEFORE this feature already carry the provider's
full payload in their `raw` jsonb — so we can fill the columns WITHOUT re-fetching
from any API. We re-run the SAME per-provider normalizer on the stored raw and
copy just the two contact fields, so the backfill can never drift from what a
live import would write.

Only rows still missing BOTH fields are touched, and a row is written only when
the re-normalization actually yields a value — no row is cleared, nothing is
fabricated. Idempotent: a second run finds nothing to do.

Usage: python3 tools/backfill_venue_contact.py   # ONELIVE_DB_DSN in env
"""
from __future__ import annotations

import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from worker.importers.normalize import (  # noqa: E402
    normalize_eventbrite,
    normalize_seatgeek,
    normalize_ticketmaster,
)

_NORMALIZER = {
    "ticketmaster": normalize_ticketmaster,
    "seatgeek": normalize_seatgeek,
    "eventbrite": normalize_eventbrite,
}


def contact_from_raw(provider: str, raw: dict) -> tuple[str | None, str | None]:
    """(venue_url, venue_phone) as the live importer would derive them, or
    (None, None) when the provider is unknown or the payload yields nothing."""
    fn = _NORMALIZER.get(provider)
    if fn is None or not isinstance(raw, dict):
        return (None, None)
    try:
        n = fn(raw) or {}
    except Exception:
        # A malformed historical payload must not abort the whole backfill.
        return (None, None)
    return (n.get("venue_url"), n.get("venue_phone"))


def main() -> int:
    import psycopg2

    from worker.db_config import resolve_dsn

    conn = psycopg2.connect(resolve_dsn())
    scanned = filled = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                "select licensed_event_id, source_provider, raw from licensed_event "
                "where venue_url is null and venue_phone is null"
            )
            rows = cur.fetchall()
            for event_id, provider, raw in rows:
                scanned += 1
                url, phone = contact_from_raw(provider, raw or {})
                if url is None and phone is None:
                    continue
                cur.execute(
                    "update licensed_event set venue_url = %s, venue_phone = %s, "
                    "updated_at = now() where licensed_event_id = %s",
                    (url, phone, event_id),
                )
                filled += 1
        conn.commit()
    finally:
        conn.close()
    print(f"backfill_venue_contact: scanned {scanned} row(s) missing contact, "
          f"filled {filled}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
