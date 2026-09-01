"""Claim intake API — the DB half of the class-D → class-E/F door.

Coverage Law: a closed door (login / paywall / bot wall) is never fetched; it
gets a claim/submit path instead. worker/claim/intake.py validates a
submission; this router is the only thing that WRITES one, and it writes
exactly two kinds of catalog row:

  * ONE `source` row — the claim itself. Registered `enabled=False`, so no
    scheduled fetch can ever pick up an unverified claimant's feed by
    accident, with `config` carrying the Coverage Law class, the confidence,
    and the claim record (who, how, when, verified=False).
  * ONE `event_candidate` per listing the claimant actually HANDED OVER (the
    CSV rows). Written through worker.candidate_store.create_candidate — the
    same insert the pipeline uses, so the claim path cannot drift from the
    column/cast contract the pipeline proved (an ICS URL or an email opt-in
    hands over no listings yet, so it writes none: we never invent an event
    from the promise of a calendar).

NOT one transaction, and said plainly rather than papered over: the source row
commits on this router's connection and each listing is inserted by
create_candidate on its own (founder decision 2026-09-01, PR #203 option (b) —
candidate_store.py sits in the armed cron's runtime closure and must not change
here). Two things keep that honest. The WHOLE submission is validated and
parsed before any write, so a malformed CSV can never get partway in; and if an
insert fails after the source row exists, the error names the source id and how
many listings landed, so an operator sees a partial state instead of a silent
one. The residual gap is docs/RECORD.md R-082.

Nothing here publishes, and nothing here fetches. The candidates enter at
`needs_review` in the classes worker/gating.py names THIRD-PARTY, so the
existing gate holds them exactly as it holds any uncorroborated stranger —
promotion stays with the two custody-holding paths it already belongs to.

Authenticated like the rest of /ops: an operator records the claim after the
organizer answers the outreach message (docs/ops/VENUE_CLAIM_OUTREACH.md).
There is deliberately NO anonymous public write path in this change — opening
one is a new outward-facing surface, and the human loop is the smaller thing
that makes a login-only organizer legal today.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_db, require_admin
from worker.candidate_store import create_candidate
from worker.claim.intake import (
    INTAKE_MODES,
    RECEIPT_STATES,
    SUBMITTER_ROLES,
    ClaimRefused,
    build_claim,
    hold_reason,
    resolve_forward_address,
)

router = APIRouter(prefix="/ops", tags=["ops"])


class ClaimIn(BaseModel):
    """What an operator types in. Note what is NOT here: confidence, source
    class, and `verified` are not accepted from the caller under any name —
    the submitter must never choose the terms on which it is trusted."""

    venue_name: str
    submitter_role: str = "organizer"   # organizer -> class E, third_party -> F
    intake_mode: str = "ics_url"        # ics_url | csv_upload | email_forward
    contact_name: str = ""
    contact_email: str = ""
    feed_url: str = ""
    csv_text: str = ""
    notes: str = ""


@router.get("/claims/intake")
def intake_options(admin=Depends(require_admin)) -> Dict[str, Any]:
    """The vocabulary + the forwarding address, so the form never hard-codes
    either and a changed intake mailbox needs no web redeploy."""
    import os

    return {
        "intake_modes": list(INTAKE_MODES),
        "submitter_roles": list(SUBMITTER_ROLES),
        "forward_to": resolve_forward_address(os.environ),
    }


@router.post("/claims")
def record_claim(payload: ClaimIn, admin=Depends(require_admin), conn=Depends(get_db)) -> Dict[str, Any]:
    """Record one claim as catalog rows. Returns the receipt, refuses loudly."""
    import os

    try:
        claim = build_claim(
            venue_name=payload.venue_name,
            submitter_role=payload.submitter_role,
            intake_mode=payload.intake_mode,
            contact_name=payload.contact_name,
            contact_email=payload.contact_email,
            feed_url=payload.feed_url,
            csv_text=payload.csv_text,
            notes=payload.notes,
            env=os.environ,
        )
    except ClaimRefused as refusal:
        # 422, not 400: the submission was understood and REFUSED on its
        # content, and the reason string is written for the venue owner to read.
        raise HTTPException(status_code=422, detail=str(refusal))

    received_at = datetime.now(timezone.utc).isoformat()
    recorded_by = str((admin or {}).get("email") or (admin or {}).get("sub") or "ops")
    config = claim.source_config(received_at=received_at, recorded_by=recorded_by)

    try:
        with conn.cursor() as cur:
            # One source row per claimed venue. A re-claim (a venue sending a
            # better feed, or a correction) UPDATES the row rather than
            # duplicating the venue — `source` has a unique index on
            # lower(name). enabled stays False on both paths: an update must
            # never be a way to switch a claim on.
            cur.execute(
                """
                insert into source (name, source_type, base_url, enabled, config)
                values (%s, %s, %s, false, %s::jsonb)
                on conflict (lower(name)) do update
                  set source_type = excluded.source_type,
                      base_url    = coalesce(excluded.base_url, source.base_url),
                      enabled     = false,
                      config      = excluded.config
                returning source_id
                """,
                (
                    claim.venue_name,
                    claim.source_type,
                    claim.feed_url or None,
                    json.dumps(config),
                ),
            )
            row = cur.fetchone()
            if row is None:
                # An upsert that matches nothing is a schema/constraint change,
                # not a normal outcome — fail loud rather than return a receipt
                # for a row that may not exist.
                raise HTTPException(
                    status_code=500,
                    detail="claim source upsert returned no row — nothing was recorded",
                )
            source_id = str(row[0])

        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise

    # The listings, each on create_candidate's own connection. The source row is
    # already committed, so a failure here is a PARTIAL write: report it with the
    # source id and the count that landed rather than a bare 500, because the
    # operator needs to know exactly what is in the catalog before retrying.
    candidate_ids: List[str] = []
    try:
        for listing in claim.listings:
            candidate_ids.append(create_candidate(
                source_id=source_id,
                source_name=claim.venue_name,
                source_url=listing.url or claim.feed_url or "",
                source_class=claim.pipeline_source_class,
                raw_text=(
                    f"claimed listing (row {listing.row_number}) submitted via "
                    f"{claim.intake_mode} by {claim.submitter_role}"
                ),
                extracted=listing.as_extracted(),
                sxsw_mode=False,
            ))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"PARTIAL: the claimed source {source_id} was recorded (disabled, "
                f"unverified) and {len(candidate_ids)} of {claim.listing_count} "
                f"listings were written before this failed: {exc}. Nothing is "
                "published either way; re-submitting will update the same source "
                "row and re-insert the listings."
            ),
        ) from exc

    return {
        # INTERNAL receipt only (founder rule 2026-09-01): received / held /
        # not live. Never "we have your calendar", never "live on 1Live".
        "status": list(RECEIPT_STATES),
        "source_id": source_id,
        "venue_name": claim.venue_name,
        "coverage_class": claim.coverage_class,
        "source_class": claim.pipeline_source_class,
        "confidence": claim.confidence,
        "intake_mode": claim.intake_mode,
        "forward_to": claim.forward_to,
        "feed_url": claim.feed_url,
        "enabled": False,
        "listings_recorded": len(candidate_ids),
        "candidate_ids": candidate_ids,
        "hold_reason": hold_reason(claim),
        "received_at": received_at,
    }
