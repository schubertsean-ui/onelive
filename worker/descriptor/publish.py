"""Gate-custodied take-live for Spark Lines — the publish step, as code.

"AI never publishes UNVALIDATED": the Foundry gate validates (candidate); this
module is the SEPARATE, gate-custodied step that takes a validated candidate
live, mirroring worker/promote.py and the Meta carousel publish physics
(Contract #23: structurally unable to self-publish; human approval bound to
content; fail-closed). The autonomous generator can NEVER call these to bless
its own output — an AI/agent approver is refused, exactly as the carousel gate
refuses an AI identity.

Fail-closed everywhere: a missing row, a non-candidate row, a text that no
longer matches what the approver saw, or a non-human approver all REFUSE with a
loud SparkLinePublishError. Nothing goes live by default.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

# The agent/author identities that may NEVER approve their own content (mirrors
# social/carousel: an AI identity cannot sign an approval).
AI_APPROVER_IDENTITIES = frozenset(
    {"descriptor_foundry", "onelive-carousel-agent", "ai", "agent", "system", ""}
)

STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_CANDIDATE = "candidate"


class SparkLinePublishError(Exception):
    """A trust/custody violation in the take-live step. Must propagate loud —
    a refusal to publish is never swallowed into a silent no-op."""


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_human_approver(approver: str) -> str:
    ident = (approver or "").strip()
    if ident.lower() in AI_APPROVER_IDENTITIES:
        raise SparkLinePublishError(
            f"approver {approver!r} is not a human identity — an AI/agent can "
            "never approve its own Spark Line (gate custody)"
        )
    return ident


def _load(cur, spark_line_id: str):
    cur.execute(
        "select spark_line_id, text, status, provenance from spark_line "
        "where spark_line_id = %s",
        (spark_line_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise SparkLinePublishError(f"no spark_line row {spark_line_id!r}")
    return row


def approve_candidate(
    spark_line_id: str,
    *,
    expected_text: str,
    approver: str,
    cur,
    now: datetime | None = None,
) -> None:
    """Take a validated CANDIDATE live. Gate-custodied and content-bound:

    - refuses a missing or non-candidate row (fail-closed);
    - refuses unless `expected_text` byte-matches the stored text — the approver
      approves the EXACT line they reviewed; a changed line must be re-approved
      (the Foundry validated THAT text, so binding live text == validated text);
    - refuses a non-human approver;
    - stamps the approval (who, when, the approved text's sha256) into
      provenance, then sets status = approved.
    """
    ident = _require_human_approver(approver)
    _, text, status, provenance = _load(cur, spark_line_id)
    if status != STATUS_CANDIDATE:
        raise SparkLinePublishError(
            f"spark_line {spark_line_id!r} is {status!r}, not {STATUS_CANDIDATE!r} "
            "— only a candidate can be taken live"
        )
    if text != expected_text:
        raise SparkLinePublishError(
            f"spark_line {spark_line_id!r} text has changed since review — "
            "refusing to publish a line the approver did not see (re-review)"
        )
    prov = dict(provenance or {})
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    prov["approval"] = {
        "approver": ident,
        "approved_at": stamp.isoformat(),
        "approved_text_sha256": _text_sha256(text),
    }
    cur.execute(
        "update spark_line set status = %s, provenance = %s::jsonb, "
        "updated_at = now() where spark_line_id = %s and status = %s",
        (STATUS_APPROVED, json.dumps(prov), spark_line_id, STATUS_CANDIDATE),
    )
    if cur.rowcount != 1:
        # A concurrent transition moved the row out from under us — fail closed
        # rather than report a publish that did not happen.
        raise SparkLinePublishError(
            f"spark_line {spark_line_id!r} was not in {STATUS_CANDIDATE!r} at "
            "update time — publish refused (concurrent change)"
        )


def reject_candidate(
    spark_line_id: str,
    *,
    approver: str,
    reason: str = "",
    cur,
    now: datetime | None = None,
) -> None:
    """Mark a candidate rejected (never shown). Same custody: a human decision,
    recorded. A rejected line is kept (audit), never silently deleted."""
    ident = _require_human_approver(approver)
    _, _text, status, provenance = _load(cur, spark_line_id)
    if status != STATUS_CANDIDATE:
        raise SparkLinePublishError(
            f"spark_line {spark_line_id!r} is {status!r}, not {STATUS_CANDIDATE!r}"
        )
    prov = dict(provenance or {})
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    prov["rejection"] = {
        "approver": ident,
        "rejected_at": stamp.isoformat(),
        "reason": reason,
    }
    cur.execute(
        "update spark_line set status = %s, provenance = %s::jsonb, "
        "updated_at = now() where spark_line_id = %s and status = %s",
        (STATUS_REJECTED, json.dumps(prov), spark_line_id, STATUS_CANDIDATE),
    )
    if cur.rowcount != 1:
        raise SparkLinePublishError(
            f"spark_line {spark_line_id!r} was not in {STATUS_CANDIDATE!r} at "
            "update time — reject refused (concurrent change)"
        )
