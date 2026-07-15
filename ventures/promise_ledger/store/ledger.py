"""Point-in-time ledger store v0 — append-only event log over stdlib sqlite3.

Implements docs/LEDGER_STORAGE_DESIGN.md's one invariant structurally:
**as-of-known-when correctness**. Three record types, INSERT-only (no UPDATE,
no DELETE — there are no such statements in this module); every record carries
`retrieved_at` (the knowledge horizon) and reads filter on it. Corrections are
superseding events that reference the superseded record — the mistake stays
visible with its correction attached.

sqlite3 keeps this dependency-free and file-based: no service, no spend,
reversible — build-phase-1 appropriate. The engine choice for production is a
gated decision (design doc §NOT-decided); this store is the reference
implementation of the invariant, and its tests are the spec.
"""

from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path

from ventures.promise_ledger.schema.claim import Claim, LifecycleEvent, validate


class LedgerIntegrityError(RuntimeError):
    """Raised when a write would violate the append-only/validity invariants."""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL CHECK (event_type IN
        ('claim_recorded', 'lifecycle_event', 'source_retrieved')),
    claim_id TEXT,
    entity_key TEXT,
    retrieved_at TEXT NOT NULL,           -- knowledge horizon (ISO 8601, UTC)
    payload TEXT NOT NULL,                -- full record, JSON
    supersedes_seq INTEGER REFERENCES events(seq)
);
CREATE INDEX IF NOT EXISTS idx_events_claim ON events(claim_id, retrieved_at);
CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_key, retrieved_at);
"""


def _iso(dt: datetime.datetime) -> str:
    if dt.tzinfo is None:
        raise LedgerIntegrityError("ledger timestamps must be timezone-aware")
    return dt.astimezone(datetime.timezone.utc).isoformat()


def _claim_payload(claim: Claim) -> str:
    def default(o):
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        if hasattr(o, "value"):
            return o.value
        if hasattr(o, "__dict__") or hasattr(o, "__dataclass_fields__"):
            import dataclasses
            return dataclasses.asdict(o)
        raise TypeError(type(o))
    import dataclasses
    return json.dumps(dataclasses.asdict(claim), default=default)


class Ledger:
    """Append-only claim ledger. Open with a file path (or ':memory:')."""

    def __init__(self, path: str | Path = ":memory:"):
        self._conn = sqlite3.connect(str(path))
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------- writes

    def record_claim(self, claim: Claim, supersedes_seq: int | None = None) -> int:
        """Append a claim_recorded event. The claim must pass schema
        validation — an invalid record never enters the ledger."""
        errors = validate(claim)
        if errors:
            raise LedgerIntegrityError(f"invalid claim rejected: {errors}")
        return self._append(
            "claim_recorded", claim.claim_id,
            self._entity_key(claim), claim.provenance.retrieved_at,
            _claim_payload(claim), supersedes_seq)

    def record_lifecycle(self, event: LifecycleEvent, supersedes_seq: int | None = None) -> int:
        errors = validate(event)
        if errors:
            raise LedgerIntegrityError(f"invalid lifecycle event rejected: {errors}")
        known_claims = {r[0] for r in self._conn.execute(
            "SELECT DISTINCT claim_id FROM events WHERE event_type='claim_recorded'")}
        if event.claim_id not in known_claims:
            raise LedgerIntegrityError(
                f"lifecycle event references unknown claim_id {event.claim_id!r} — "
                "a lifecycle assertion needs a recorded claim")
        import dataclasses
        payload = json.dumps(dataclasses.asdict(event), default=lambda o: (
            o.isoformat() if isinstance(o, (datetime.datetime, datetime.date))
            else o.value if hasattr(o, "value") else str(o)))
        return self._append("lifecycle_event", event.claim_id, None,
                            event.observed_at, payload, supersedes_seq)

    def _append(self, event_type, claim_id, entity_key, retrieved_at, payload,
                supersedes_seq) -> int:
        if supersedes_seq is not None:
            row = self._conn.execute("SELECT seq FROM events WHERE seq=?",
                                     (supersedes_seq,)).fetchone()
            if row is None:
                raise LedgerIntegrityError(
                    f"supersedes_seq {supersedes_seq} does not exist — a correction "
                    "must reference the record it corrects")
        cur = self._conn.execute(
            "INSERT INTO events (event_type, claim_id, entity_key, retrieved_at, "
            "payload, supersedes_seq) VALUES (?,?,?,?,?,?)",
            (event_type, claim_id, entity_key, _iso(retrieved_at), payload, supersedes_seq))
        self._conn.commit()
        return cur.lastrowid

    @staticmethod
    def _entity_key(claim: Claim) -> str:
        return claim.entity.lei or f"CIK:{claim.entity.cik}"

    # -------------------------------------------------------------- reads

    def events_as_of(self, as_of: datetime.datetime, claim_id: str | None = None) -> list[dict]:
        """Everything knowable at `as_of` — the point-in-time read. Records
        retrieved after `as_of` do not exist for this query, ever."""
        q = ("SELECT seq, event_type, claim_id, retrieved_at, payload, supersedes_seq "
             "FROM events WHERE retrieved_at <= ?")
        args: list = [_iso(as_of)]
        if claim_id is not None:
            q += " AND claim_id = ?"
            args.append(claim_id)
        q += " ORDER BY seq"
        out = []
        for seq, etype, cid, ret, payload, sup in self._conn.execute(q, args):
            out.append({"seq": seq, "event_type": etype, "claim_id": cid,
                        "retrieved_at": ret, "payload": json.loads(payload),
                        "supersedes_seq": sup})
        return out

    def current_state(self, claim_id: str, as_of: datetime.datetime) -> dict | None:
        """Latest non-superseded state of a claim as knowable at `as_of`.
        Superseded records remain in every listing (shown, never hidden);
        this projection just tells you which record is operative."""
        events = self.events_as_of(as_of, claim_id=claim_id)
        if not events:
            return None
        superseded = {e["supersedes_seq"] for e in events if e["supersedes_seq"] is not None}
        operative = [e for e in events if e["seq"] not in superseded]
        lifecycle = [e for e in operative if e["event_type"] == "lifecycle_event"]
        claims = [e for e in operative if e["event_type"] == "claim_recorded"]
        return {
            "claim": claims[-1]["payload"] if claims else None,
            "state": (lifecycle[-1]["payload"]["state"] if lifecycle else "made"),
            "confidence": (lifecycle[-1]["payload"]["confidence"] if lifecycle else "unverified"),
            "history_events": len(events),
            "superseded_events": len(superseded),
        }

    def close(self):
        self._conn.close()
