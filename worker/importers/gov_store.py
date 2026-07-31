"""Deterministic upsert of normalized government-open-data records into
`venue_truth`.

No AI. Idempotent via ON CONFLICT (source_provider, external_id) — a re-run
UPDATES in place, never duplicates. Trust-gate compliant: the statement passed to
.execute() is a module-level static string built ONCE from a fixed constant
column list (no external input is ever formatted into SQL); values are always
bound as %s parameters and the raw payload is adapted to jsonb via psycopg2's
Json, never string-built. This writes ONLY the separate venue_truth store — it
never touches `event` or `licensed_event`, and never imports worker.promote (the
guarded promote path stays untouched). Mirrors worker.importers.licensed_store.
"""
from __future__ import annotations

from typing import Iterable

from psycopg2.extras import Json  # hard dep (worker/requirements.txt) — fail loud if broken

# Fixed column order — a constant, not external input; used only to assemble the
# static statement below once at import. Values are always bound as %s.
_COLS = [
    "source_provider", "external_id", "name", "address", "city", "state",
    "postal_code", "latitude", "longitude", "capacity", "license_type",
    "license_status", "service_type", "source_name", "raw",
]
_KEY = ("source_provider", "external_id")
_UPDATABLE = [c for c in _COLS if c not in _KEY]

# Static once, from constants only (no runtime/external data) → not dynamic SQL.
# last_seen_at bumps on every re-import; first_seen_at is preserved (set on insert
# by the column default, never in the UPDATE set).
UPSERT_SQL = (
    "insert into venue_truth (" + ", ".join(_COLS) + ") values ("
    + ", ".join(["%s"] * len(_COLS)) + ") "
    "on conflict (source_provider, external_id) do update set "
    + ", ".join(f"{c} = excluded.{c}" for c in _UPDATABLE)
    + ", last_seen_at = now()"
)


def _params(n: dict) -> list:
    # psycopg2 adapts the raw payload dict to jsonb via Json. No fallback: a
    # broken adapter must fail loud, not silently change insert semantics.
    raw = Json(n.get("raw") or {})
    return [
        n["source_provider"], n["external_id"], n.get("name"), n.get("address"),
        n.get("city"), n.get("state"), n.get("postal_code"), n.get("latitude"),
        n.get("longitude"), n.get("capacity"), n.get("license_type"),
        n.get("license_status"), n.get("service_type"), n.get("source_name"),
        raw,
    ]


def upsert_venue_truth(conn, records: Iterable[dict]) -> int:
    """Upsert normalized venue-truth records; return the count written. Commits
    once. A record must carry source_provider + external_id (the key); the
    normalizer guarantees a stable external_id, so a keyless record is a
    programming error and raises (KeyError) rather than silently dropping."""
    count = 0
    with conn.cursor() as cur:
        for r in records:
            cur.execute(UPSERT_SQL, _params(r))
            count += 1
    conn.commit()
    return count
