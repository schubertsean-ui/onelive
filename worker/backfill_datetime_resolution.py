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
from worker.datetime_resolve import resolve_partial_date_claim

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
                        # The prose block-text reader is RETIRED (see
                        # worker/datetime_resolve.py): it resolved nothing in
                        # live traffic and review found five fabrication paths
                        # through it. Only the claim's OWN month+day evidence
                        # is used here now.
                        iso, rec = resolve_partial_date_claim(start_claim, created_at)
                        if iso is None:
                            counts["unresolvable"] += 1
                            continue
                        resolution = {"start_time": rec}
                        end_iso = None
                        end_claim = (claims or {}).get("end_time", {}).get("raw")
                        if end_claim:
                            end_iso, end_rec = resolve_partial_date_claim(
                                end_claim, created_at)
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


class BackfillPreconditionError(RuntimeError):
    """Raised when --real is requested before the one-way door is safe."""


# The founder-settled timezone storage contract (R-083, second constraint).
# Flipped to True ONLY by the PR that lands the ratified contract and its
# migration for already-written rows. A backfill run before that writes
# thousands of instants 5-6 hours early.
TIMEZONE_CONTRACT_SETTLED = False


def assert_safe_to_write() -> None:
    """Refuse --real until the one-way door is actually closed (R-083).

    R-083 records this as a HARD STOP, and the evaluator's finding on the
    consolidated head was exactly right: a hard stop that lives only in a
    markdown file is not a hard stop. This workflow holds production DB
    credentials and can be dispatched by hand, so the stop belongs HERE.

    The gate-fix precondition is checked BEHAVIOURALLY, not by a flag — the
    probe below asks the real gate whether one instant written two ways still
    reads as a conflict. A flag can drift from the code it claims to describe;
    a probe cannot. If R-084(a) is unfixed, the gate escalates, every row this
    pass dates acquires a gate_reason, and those rows leave every automated and
    human path permanently (R-085). So we refuse.
    """
    from worker.trust_gate3 import _has_conflicting_start_time

    same_instant_two_renderings = {
        "start_times": ["2026-08-08T19:30:00+00:00", "2026-08-08T19:30:00"]
    }
    if _has_conflicting_start_time(same_instant_two_renderings):
        raise BackfillPreconditionError(
            "REFUSING --real: the trust gate still reports a CONFLICT for one "
            "instant rendered two ways, so R-084(a) is not fixed on this "
            "checkout. Every row this pass dated would immediately escalate "
            "with a gate_reason written, which removes it from stamp_backlog, "
            "from run_autopromote, and from the human promote path — "
            "permanently (R-085). Land the canonical-instant gate fix first. "
            "See docs/ops/PATH_TO_THOUSANDS.md B0-B9 for the required order."
        )
    if not TIMEZONE_CONTRACT_SETTLED:
        raise BackfillPreconditionError(
            "REFUSING --real: the timezone storage contract is not settled "
            "(R-083). worker/datetime_normalize.py returns a NAIVE isoformat "
            "into a timestamptz column and nothing sets a session TimeZone, so "
            "8pm Central is stored as 3pm Central. Writing the backlog through "
            "that lands thousands of events 5-6 hours early. This is a founder "
            "decision; flip TIMEZONE_CONTRACT_SETTLED in the PR that lands the "
            "ratified contract and its migration."
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, required=True,
                    help="candidate ceiling for this pass (bounded, always)")
    ap.add_argument("--real", action="store_true",
                    help="write; without it the pass only reports")
    args = ap.parse_args()
    if args.real:
        # Fail BEFORE opening the connection: a refusal must cost nothing and
        # must not half-run.
        assert_safe_to_write()
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
