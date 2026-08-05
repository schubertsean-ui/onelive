"""Backfill: resolve preserved partial-date claims for existing candidates
and their already-published events (Contract #44, founder directive
2026-08-05 — the discovered lane's dates, NOW; no re-crawl, no AI spend).

WHAT IT DOES, in one bounded pass (dry-run by default; --real writes):
  1. Candidates with start_time NULL whose provenance preserves a refused
     start_time claim (reason no-full-date-evidence) get the claim resolved
     against the candidate's own created_at (the closest stored proxy for
     fetch time) via worker.datetime_resolve — the stated, deterministic,
     refuse-everything-else rule. Resolution lands in start_time AND in
     extracted._provenance.datetime_resolution (auditable forever). Same for
     end_time when its claim resolves.
  2. Already-published events whose start_time is NULL take their candidate's
     newly-resolved start_time/end_time via promoted_event_id — the same
     back-reference 0020's provenance backfill used.

CUSTODY UNCHANGED: this writes dates derived from each candidate's OWN
preserved claim + its own fetch context; it publishes nothing (events
touched are already published, gaining only the date their source page
evidenced) and no gate, threshold, or confidence moves. Per-row failures
are isolated and counted; the pass never dies on one bad row.
"""
from __future__ import annotations

import argparse
import json
import logging

import psycopg2

from worker.db_config import resolve_dsn
from worker.datetime_resolve import (
    resolve_partial_date_claim,
    resolve_time_only_from_block,
)

logger = logging.getLogger(__name__)


def run(limit: int, real: bool) -> dict:
    counts = {
        "examined": 0, "resolved_start": 0, "resolved_end": 0,
        "unresolvable": 0, "events_dated": 0, "errors": 0,
    }
    conn = psycopg2.connect(resolve_dsn())
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select candidate_id, created_at,
                           extracted->'_provenance'->'unstored_datetime_claims' as claims,
                           raw_text
                    from event_candidate
                    where start_time is null
                      and extracted->'_provenance'->'unstored_datetime_claims'
                          ->'start_time'->>'reason' = 'no-full-date-evidence'
                    order by created_at
                    limit %s
                    """, (limit,))
                rows = cur.fetchall()
                for cid, created_at, claims, raw_text in rows:
                    counts["examined"] += 1
                    try:
                        start_claim = (claims or {}).get("start_time", {}).get("raw")
                        # Same two evidence sources as live extraction: the
                        # claim's own month+day first, then the single date
                        # stated in the candidate's OWN stored block text —
                        # which is what a bare "8:00 pm" needs and what the
                        # whole backlog is made of.
                        iso, rec = resolve_partial_date_claim(start_claim, created_at)
                        if iso is None:
                            iso, rec = resolve_time_only_from_block(
                                start_claim, raw_text, created_at)
                        if iso is None:
                            counts["unresolvable"] += 1
                            continue
                        resolution = {"start_time": rec}
                        end_iso = None
                        end_claim = (claims or {}).get("end_time", {}).get("raw")
                        if end_claim:
                            end_iso, end_rec = resolve_partial_date_claim(
                                end_claim, created_at)
                            if end_iso is None:
                                end_iso, end_rec = resolve_time_only_from_block(
                                    end_claim, raw_text, created_at)
                            if end_iso is not None:
                                resolution["end_time"] = end_rec
                                counts["resolved_end"] += 1
                        counts["resolved_start"] += 1
                        if real:
                            cur.execute(
                                """
                                update event_candidate
                                set start_time = %s,
                                    end_time = coalesce(%s, end_time),
                                    updated_at = now(),
                                    extracted = jsonb_set(
                                      extracted, '{_provenance,datetime_resolution}',
                                      %s::jsonb, true)
                                where candidate_id = %s
                                """,
                                (iso, end_iso, json.dumps(resolution), cid))
                    except Exception:  # noqa: BLE001 — isolate per row
                        counts["errors"] += 1
                        logger.exception(
                            "backfill: candidate %s raised — skipped, pass "
                            "continues", cid)

                # Published-but-dateless events inherit their candidate's
                # freshly resolved dates (no new publish — the row exists).
                if real:
                    cur.execute(
                        """
                        update event e
                        set start_time = c.start_time,
                            end_time = coalesce(e.end_time, c.end_time),
                            updated_at = now()
                        from event_candidate c
                        where c.promoted_event_id = e.event_id
                          and e.start_time is null
                          and c.start_time is not null
                        """)
                    counts["events_dated"] = cur.rowcount
    finally:
        conn.close()
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, required=True,
                    help="candidate ceiling for this pass (bounded, always)")
    ap.add_argument("--real", action="store_true",
                    help="write; without it the pass only reports")
    args = ap.parse_args()
    counts = run(args.limit, args.real)
    print("BackfillDatetimeReport:")
    print(f"  real:   {args.real}")
    print(f"  counts: {counts}")
    # Loud zero: an all-unresolvable pass is a finding, not a success.
    if counts["examined"] and not counts["resolved_start"]:
        print("  NOTE: nothing resolved — the preserved claims may not carry "
              "month+day evidence; inspect samples before re-running.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
