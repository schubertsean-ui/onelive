"""Deterministic-replay logging — the audit trail behind every gate decision.

Every promotion (or escalation, or hold) this pipeline ever makes must be
reconstructable after the fact: which source, what stage, what decision, and
a digest of the inputs/outputs involved. This is what makes "why was this
event published" answerable months later instead of a shrug.

Design constraints (from the spec, non-negotiable):
- Import-safe with no DB and no network — this module must never be the
  reason an import fails offline.
- Append-only JSONL: one line per (run_id, source, stage) step, never
  rewritten or deleted.
- inputs_digest/outputs_digest are sha256 hashes of the *canonical* JSON of
  the relevant payload, not the raw payload itself — so a replay can verify
  determinism (same input digest => same decision) without the log itself
  becoming a second copy of potentially PII-heavy raw text.
- Fail LOUDLY if the log directory is unwritable. Silently dropping an audit
  record is exactly the "we failed looks like nothing happened" anti-pattern
  this project bans (see CLAUDE.md / OPERATING_RULES.md).
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass, asdict
from typing import Any


DEFAULT_REPLAY_DIR = "var/replay"


class ReplayLogWriteError(RuntimeError):
    """Raised when a replay step cannot be durably written. This is a
    structural failure (unwritable directory, permissions, disk full) and
    must abort the caller rather than be swallowed — losing the audit trail
    silently would defeat the entire point of deterministic replay."""


@dataclass
class ReplayRecord:
    run_id: str
    ts: str
    source_id: str
    source_name: str
    stage: str
    inputs_digest: str
    outputs_digest: str
    decision: str
    detail: str


def new_run_id() -> str:
    return str(uuid.uuid4())


def canonical_digest(payload: Any) -> str:
    """sha256 hex digest of the canonical (sorted-key, separator-normalized)
    JSON encoding of `payload`. Canonicalizing guarantees two logically
    identical payloads produce the same digest regardless of dict insertion
    order, which is what makes "same input digest -> same decision" a
    meaningful determinism check on replay.
    """
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _replay_path(run_id: str) -> str:
    log_dir = os.getenv("ONELIVE_REPLAY_LOG_DIR", DEFAULT_REPLAY_DIR)
    return os.path.join(log_dir, f"{run_id}.jsonl")


def log_step(record: ReplayRecord) -> None:
    """Append `record` as one JSON line to the run's replay log.

    Directory creation and the write itself are both wrapped: any OSError
    (unwritable dir, permissions, disk full) is re-raised as
    ReplayLogWriteError rather than swallowed, per the fail-loud-on-structural
    -error rule. This function performs no DB access and no network I/O.
    """
    path = _replay_path(record.run_id)
    log_dir = os.path.dirname(path) or "."
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as exc:
        raise ReplayLogWriteError(
            f"replay log directory {log_dir!r} is not writable: {exc}"
        ) from exc

    line = json.dumps(asdict(record), sort_keys=True, default=str)
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError as exc:
        raise ReplayLogWriteError(
            f"could not append replay step to {path!r}: {exc}"
        ) from exc
