"""Deterministic upsert of normalized licensed-feed events into `licensed_event`.

No AI. Idempotent via ON CONFLICT (source_provider, external_id) — a re-run
UPDATES in place, never duplicates. Trust-gate compliant: the statement passed to
.execute() is a module-level static string bound with %s parameters (the column
list is a fixed constant — no external input is ever formatted into SQL), and the
raw source payload is adapted to jsonb via psycopg2's Json, never string-built.
This writes ONLY the separate licensed store; it never touches `event` or imports
worker.promote (the guarded promote path stays untouched).
"""
from __future__ import annotations

from typing import Iterable

from psycopg2.extras import Json  # hard dep (worker/requirements.txt) — fail loud if broken

# Fixed column order. Not external input — used only to assemble the static
# statement below once at import; values are always bound as %s parameters.
_COLS = [
    "source_provider", "external_id", "title", "category", "subsegment",
    "performer", "start_time", "end_time", "status", "on_sale_status",
    "price_min", "price_max", "currency", "is_free", "ticket_url", "image_url",
    "venue_name", "venue_city", "venue_area", "venue_address", "venue_lat",
    "venue_lng", "venue_url", "venue_phone", "confidence", "raw",
]
_KEY = ("source_provider", "external_id")
_UPDATABLE = [c for c in _COLS if c not in _KEY]

# Static once, from constants only (no runtime/external data) → not dynamic SQL.
UPSERT_SQL = (
    "insert into licensed_event (" + ", ".join(_COLS) + ") values ("
    + ", ".join(["%s"] * len(_COLS)) + ") "
    "on conflict (source_provider, external_id) do update set "
    + ", ".join(f"{c} = excluded.{c}" for c in _UPDATABLE)
    + ", updated_at = now()"
)


def _params(n: dict) -> list:
    # psycopg2 adapts the raw payload dict to jsonb via Json. No fallback: a
    # broken adapter must fail loud, not silently change insert semantics.
    raw = Json(n.get("raw") or {})
    return [
        n["source_provider"], n["external_id"], n["title"], n.get("category"),
        n.get("subsegment"), n.get("performer"), n.get("start_time"),
        n.get("end_time"), n.get("status", "scheduled"), n.get("on_sale_status"),
        n.get("price_min"), n.get("price_max"), n.get("currency"), n.get("is_free"),
        n.get("ticket_url"), n.get("image_url"), n.get("venue_name"),
        n.get("venue_city"), n.get("venue_area"), n.get("venue_address"),
        n.get("venue_lat"), n.get("venue_lng"),
        n.get("venue_url"), n.get("venue_phone"),
        n.get("confidence", "confirmed"),
        raw,
    ]


def upsert_events(conn, events: Iterable[dict]) -> int:
    """Upsert normalized events; return the count written. Commits once."""
    count = 0
    with conn.cursor() as cur:
        for ev in events:
            cur.execute(UPSERT_SQL, _params(ev))
            count += 1
    conn.commit()
    return count
