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
        "unresolvable": 0, "events_dated": 0,
        "end_before_start_dropped": 0, "disputed_events_skipped": 0,
        "errors": 0,
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
                            # An end that is not strictly after the start is
                            # NOT stored (evaluator #191 r3, absence-only):
                            # "Aug 8 8pm" + a bare "1am" resolves the end onto
                            # the SAME calendar day, i.e. before the show
                            # starts. The midnight rollover is the obvious
                            # human reading and exactly the kind of obvious
                            # reading this module refuses to make — a guessed
                            # end is dropped, the start still lands.
                            if end_iso is not None and end_iso <= iso:
                                counts["end_before_start_dropped"] += 1
                                end_iso = None
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
                #
                # A DISPUTED public row is never mutated by this pass
                # (evaluator #191 r3, absence-only): disputed is
                # shown-never-hidden, and silently changing a disputed event's
                # time is precisely the adjudication this pass has no authority
                # to make. Counted OUTSIDE the `real` branch so a DRY RUN
                # reports the skip too — a dry run that showed 0 disputed
                # while disputed rows existed would under-report the very
                # thing an operator runs it to see.
                cur.execute(
                    """
                    select count(*) from event e
                    join event_candidate c on c.promoted_event_id = e.event_id
                    where e.start_time is null and c.start_time is not null
                      and e.confidence = 'disputed'
                    """)
                counts["disputed_events_skipped"] = cur.fetchone()[0]
                if real:
                    # The public row inherits ONLY from a candidate this pass
                    # actually resolved (the datetime_resolution provenance key
                    # it just wrote), never from any incidental non-null
                    # candidate time — and only when the inherited pair is
                    # internally consistent. Everything else stays NULL.
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
                          and e.confidence <> 'disputed'
                          and c.extracted->'_provenance'->'datetime_resolution'
                              is not null
                          and (c.end_time is null or c.end_time > c.start_time)
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
