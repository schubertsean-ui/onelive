"""Point-in-time ledger store v0 — append-only event log over stdlib sqlite3.

Implements docs/LEDGER_STORAGE_DESIGN.md's one invariant structurally:
**as-of-known-when correctness**. Three record types with public writers
(`record_claim`, `record_lifecycle`, `record_source_retrieval`), INSERT-only
(no UPDATE, no DELETE — there are no such statements in this module); every
record's knowledge-horizon column holds WHEN THE SYSTEM LEARNED IT (claim:
provenance.retrieved_at; lifecycle: recorded_at — never observed_at; source:
retrieved_at) and reads filter on it. Corrections are superseding events that
reference the superseded record — the mistake stays visible with its
correction attached.

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
        # The claim must not merely exist — it must be KNOWABLE at the
        # event's own knowledge horizon (evaluator r23): otherwise
        # events_as_of() can surface a lifecycle verdict before the claim it
        # judges, yielding state="broken" with claim=None.
        row = self._conn.execute(
            "SELECT MIN(retrieved_at) FROM events "
            "WHERE event_type='claim_recorded' AND claim_id=?",
            (event.claim_id,)).fetchone()
        if row is None or row[0] is None:
            raise LedgerIntegrityError(
                f"lifecycle event references unknown claim_id {event.claim_id!r} — "
                "a lifecycle assertion needs a recorded claim")
        if _iso(event.recorded_at) < row[0]:
            raise LedgerIntegrityError(
                f"lifecycle recorded_at {_iso(event.recorded_at)} precedes the claim's "
                f"earliest knowledge horizon {row[0]} — a verdict cannot be knowable "
                "before the claim it judges")
        import dataclasses
        payload = json.dumps(dataclasses.asdict(event), default=lambda o: (
            o.isoformat() if isinstance(o, (datetime.datetime, datetime.date))
            else o.value if hasattr(o, "value") else str(o)))
        # Knowledge horizon = recorded_at (when WE learned it), NEVER
        # observed_at (when it happened): an outcome discovered late must not
        # be readable at times before its discovery (evaluator r22 — using
        # observed_at here time-travels and contaminates backtests).
        return self._append("lifecycle_event", event.claim_id, None,
                            event.recorded_at, payload, supersedes_seq)

    _SHA256_HEX = 64

    def record_source_retrieval(self, *, source_url: str, sha256: str,
                                size_bytes: int, retrieved_at: datetime.datetime,
                                entity_key: str | None = None,
                                note: str | None = None) -> int:
        """Append a source_retrieved event — the raw-source custody record
        (design doc record type 3). Payload contract mirrors the
        source_material MANIFEST entries: where the bytes came from, their
        hash, their size, and when we took custody. Validation at the door,
        like every other writer — an unverifiable custody record is worse
        than none."""
        errors = []
        if not source_url.startswith("https://"):
            errors.append("source_url must be an https URL naming the authority")
        if len(sha256) != self._SHA256_HEX or any(
                c not in "0123456789abcdef" for c in sha256.lower()) or \
                sha256 != sha256.lower():
            errors.append("sha256 must be 64 lowercase hex chars")
        if size_bytes <= 0:
            errors.append("size_bytes must be positive")
        if errors:
            raise LedgerIntegrityError(f"invalid source retrieval rejected: {errors}")
        payload = json.dumps({
            "source_url": source_url, "sha256": sha256, "size_bytes": size_bytes,
            "retrieved_at": _iso(retrieved_at), "note": note,
        })
        return self._append("source_retrieved", None, entity_key,
                            retrieved_at, payload, None)

    def _append(self, event_type, claim_id, entity_key, retrieved_at, payload,
                supersedes_seq) -> int:
        if supersedes_seq is not None:
            row = self._conn.execute(
                "SELECT event_type, claim_id, retrieved_at FROM events WHERE seq=?",
                (supersedes_seq,)).fetchone()
            if row is None:
                raise LedgerIntegrityError(
                    f"supersedes_seq {supersedes_seq} does not exist — a correction "
                    "must reference the record it corrects")
            # A correction corrects a specific prior assertion (evaluator r23):
            # same event type, same claim, and the superseded record must be
            # knowable no later than its correction — otherwise the audit
            # trail claims we corrected something we hadn't yet learned.
            sup_type, sup_claim, sup_retrieved = row
            if sup_type != event_type:
                raise LedgerIntegrityError(
                    f"a {event_type} record cannot supersede a {sup_type} record — "
                    "corrections stay within one event type")
            if sup_claim != claim_id:
                raise LedgerIntegrityError(
                    f"correction targets claim {sup_claim!r} but carries claim "
                    f"{claim_id!r} — corrections stay within one claim")
            if _iso(retrieved_at) < sup_retrieved:
                raise LedgerIntegrityError(
                    f"correction's knowledge horizon {_iso(retrieved_at)} precedes the "
                    f"superseded record's {sup_retrieved} — a correction cannot be "
                    "knowable before the record it corrects")
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
