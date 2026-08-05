#!/usr/bin/env python3
"""Read-only scope report: breadth and depth of the data engine, from the DB.

Founder ask (2026-08-04): "# of unique data sources · # of unique segments per
data source · # of unique venues, artists/people, etc per data source · # of
events per data source · plus whatever else helps me understand the scope
depth and breadth of the overall engine."

Every number is a live SELECT against production — nothing cached, nothing
estimated, nothing fabricated. READ-ONLY by construction: the connection is
opened with default_transaction_read_only=on, so any accidental write raises
instead of mutating. Output: one JSON document to stdout (artifact-friendly)
with a human summary on stderr.

Covers both publication lanes honestly:
  * licensed_event  — the licensed-API lane (Ticketmaster today), per provider;
  * event           — the pipeline lane (extraction → gate → promote), per
                      confidence state;
plus the intake funnel (source / raw_fetch / raw_event / event_candidate) so
breadth-in-progress is visible, not just what already reached the feed.

Usage: ONELIVE_DB_DSN=... python tools/db_scope_report.py
"""
from __future__ import annotations

import json
import os
import sys

import psycopg2


def q(cur, sql: str, params=None):
    """One read-only query -> list of tuples."""
    cur.execute(sql, params or ())
    return cur.fetchall()


def scalar(cur, sql: str, params=None):
    """One read-only query -> single value."""
    rows = q(cur, sql, params)
    return rows[0][0] if rows else None


def licensed_lane(cur) -> dict:
    """Per-provider breadth/depth of the licensed feed."""
    providers = []
    for (prov,) in q(cur, "select distinct source_provider from licensed_event order by 1"):
        row = q(cur, """
          select count(*),
                 count(*) filter (where start_time >= now()),
                 count(distinct category),
                 count(distinct subsegment),
                 count(distinct lower(venue_name)),
                 count(distinct lower(performer)) filter (where performer is not null),
                 min(start_time), max(start_time)
          from licensed_event where source_provider = %s
        """, (prov,))[0]
        segments = q(cur, """
          select coalesce(category, '(uncategorized)'), count(*)
          from licensed_event where source_provider = %s
          group by 1 order by 2 desc
        """, (prov,))
        providers.append({
            "provider": prov,
            "events_total": row[0],
            "events_upcoming": row[1],
            "unique_categories": row[2],
            "unique_subsegments": row[3],
            "unique_venues": row[4],
            "unique_performers": row[5],
            "earliest_event": str(row[6]),
            "latest_event": str(row[7]),
            "events_by_category": [{"category": c, "events": n} for c, n in segments],
        })
    return {"providers": providers}


def pipeline_lane(cur) -> dict:
    """The extraction→gate→promote lane: canonical events + the intake funnel."""
    by_conf = dict(q(cur, "select confidence, count(*) from event group by 1"))
    ev = q(cur, """
      select count(*),
             count(*) filter (where start_time >= now()),
             count(distinct venue_id),
             count(distinct category)
      from event
    """)[0]
    artists = scalar(cur, "select count(distinct a) from event, unnest(artist_ids) a")
    candidates = q(cur, """
      select coalesce(source_name, '(unknown source)'), count(*)
      from event_candidate group by 1 order by 2 desc
    """)
    return {
        "canonical_events_total": ev[0],
        "canonical_events_upcoming": ev[1],
        "canonical_unique_venues": ev[2],
        "canonical_unique_categories": ev[3],
        "canonical_unique_artists": artists,
        "events_by_confidence": by_conf,
        "candidates_total": sum(n for _, n in candidates),
        "candidates_by_source": [{"source": s, "candidates": n} for s, n in candidates],
    }


def date_distribution(cur) -> dict:
    """WHERE the events are in time — the founder's 'Today shows 11 events'
    diagnosis instrument (decision record 2026-08-05_today-density-and-
    duplicates.md). Buckets pipeline-published events AND the candidate pool
    by start_time so the supply bottleneck is read off evidence: NULL dates
    (extraction refused a datetime), past dates (stale backlog), or held
    future events (corroboration). Austin days (America/Chicago)."""
    events = {b: n for b, n in q(cur, """
      with b as (
        select case
          when start_time is null then 'null'
          when start_time < now() then 'past'
          when (start_time at time zone 'America/Chicago')::date =
               (now() at time zone 'America/Chicago')::date then 'today'
          when start_time < now() + interval '7 day' then 'next_7_days'
          else 'beyond_7_days'
        end as bucket
        from event
      )
      select bucket, count(*) from b group by 1 order by 1
    """)}
    cands = q(cur, """
      with b as (
        select status, case
          when start_time is null then 'null'
          when start_time < now() then 'past'
          when (start_time at time zone 'America/Chicago')::date =
               (now() at time zone 'America/Chicago')::date then 'today'
          when start_time < now() + interval '7 day' then 'next_7_days'
          else 'beyond_7_days'
        end as bucket
        from event_candidate
      )
      select status, bucket, count(*) from b group by 1, 2 order by 1, 2
    """)
    cand_by_status: dict = {}
    for status, bucket, n in cands:
        cand_by_status.setdefault(status, {})[bucket] = n
    return {
        "pipeline_events_by_start_time": events,
        "candidates_by_status_and_start_time": cand_by_status,
    }


def duplicate_report(cur) -> dict:
    """Cross-source duplicate detection (founder-caught 2026-08-05: the same
    show via two providers rendered twice). Groups upcoming rows by
    (normalized venue, start_time, normalized title) across BOTH publication
    lanes and reports groups with >1 member — the display layer collapses
    these; this section measures how much duplication the imports produce so
    the import-lane fix is sized from data."""
    rows = q(cur, """
      with all_rows as (
        select 'licensed:' || source_provider as src,
               lower(regexp_replace(regexp_replace(coalesce(venue_name,''), '[.'']', '', 'g'), '[^a-zA-Z0-9]+', ' ', 'g')) as v,
               start_time,
               lower(regexp_replace(regexp_replace(coalesce(performer, title, ''), '[.'']', '', 'g'), '[^a-zA-Z0-9]+', ' ', 'g')) as t
        from licensed_event where start_time >= now()
        union all
        select 'pipeline' as src,
               lower(regexp_replace(regexp_replace(coalesce(vn.name,''), '[.'']', '', 'g'), '[^a-zA-Z0-9]+', ' ', 'g')),
               e.start_time,
               lower(regexp_replace(regexp_replace(coalesce(e.title,''), '[.'']', '', 'g'), '[^a-zA-Z0-9]+', ' ', 'g'))
        from event e left join venue vn on vn.venue_id = e.venue_id
        where e.start_time >= now()
      )
      select v, start_time, t, count(*), array_agg(distinct src)
      from all_rows
      where v <> '' and t <> ''
      group by 1, 2, 3
      having count(*) > 1
      order by count(*) desc
    """)
    # Totals over EVERY group — the worst_groups listing below is a sample,
    # and a sampled listing must never stand in for the total (no silent
    # caps: a truncated count would read as "covered everything").
    return {
        "upcoming_duplicate_groups": len(rows),
        "upcoming_duplicate_rows_beyond_first": sum(r[3] - 1 for r in rows),
        "worst_groups": [
            {"venue": v, "start_time": str(st), "title": t, "count": n,
             "sources": srcs}
            for v, st, t, n, srcs in rows[:15]],
    }


def intake_funnel(cur) -> dict:
    """Cataloged sources and raw intake — breadth that hasn't reached the feed yet."""
    src = q(cur, """
      select source_type, count(*), count(*) filter (where enabled)
      from source group by 1 order by 2 desc
    """)
    return {
        "sources_total": scalar(cur, "select count(*) from source"),
        "sources_enabled": scalar(cur, "select count(*) from source where enabled"),
        "sources_by_type": [
            {"type": t, "total": n, "enabled": e} for t, n, e in src],
        "raw_fetches_total": scalar(cur, "select count(*) from raw_fetch"),
        "raw_events_total": scalar(cur, "select count(*) from raw_event"),
        "venues_known": scalar(cur, "select count(*) from venue"),
        "artists_known": scalar(cur, "select count(*) from artist"),
    }


def ratio_50_to_1(cur) -> dict:
    """The founder's 50:1 KPI, measured per window (2026-08-04, verbatim: "The
    50:1 is non-API ticketed events to API events on any given day weekend or
    weekly period.").

    Interpretation, stated so it can be corrected rather than assumed: non-API
    = pipeline-published canonical events (extraction → gate → promote — the
    DISCOVERED events — the events we find ourselves); API = licensed_event rows (ticketing
    APIs anyone can license). Windows are Austin days (America/Chicago):
    today, the containing-or-upcoming Fri→Sun weekend, and the next 7 days.
    """
    windows = q(cur, """
      with market as (
        select (now() at time zone 'America/Chicago')::date as today
      ), bounds as (
        -- days until Friday: isodow Fri=5, so (5 - isodow) mod 7 (Mon->4 ... Thu->1);
        -- the Fri/Sat/Sun case never reads this column (handled in the branch below).
        select today,
               today + ((5 - extract(isodow from today)::int + 7) %% 7) as fri
        from market
      ), w as (
        select 'today'::text as win,
               today::timestamp as lo, (today + 1)::timestamp as hi from bounds
        union all
        select 'weekend',
               (case when extract(isodow from today) in (5,6,7)
                     then today - (extract(isodow from today)::int - 5)
                     else fri end)::timestamp,
               (case when extract(isodow from today) in (5,6,7)
                     then today - (extract(isodow from today)::int - 5)
                     else fri end + 3)::timestamp
        from bounds
        union all
        select 'next_7_days', today::timestamp, (today + 7)::timestamp from bounds
      )
      select w.win,
             (select count(*) from licensed_event l
               where (l.start_time at time zone 'America/Chicago') >= w.lo
                 and (l.start_time at time zone 'America/Chicago') <  w.hi),
             (select count(*) from event e
               where (e.start_time at time zone 'America/Chicago') >= w.lo
                 and (e.start_time at time zone 'America/Chicago') <  w.hi)
      from w
    """)
    out = {}
    for win, api_n, non_api_n in windows:
        out[win] = {
            "api_events": api_n,
            "non_api_events": non_api_n,
            "ratio_non_api_to_api": (round(non_api_n / api_n, 2)
                                     if api_n else None),
            "target": 50.0,
            "target_met": (api_n > 0 and non_api_n / api_n >= 50.0),
        }
    return out


def main() -> int:
    """Connect read-only, assemble the full scope report, emit JSON."""
    dsn = os.environ.get("ONELIVE_DB_DSN", "").strip()
    if not dsn:
        print("ONELIVE_DB_DSN missing — this report reads production and "
              "needs the credential", file=sys.stderr)
        return 2
    conn = psycopg2.connect(dsn, options="-c default_transaction_read_only=on")
    try:
        with conn, conn.cursor() as cur:
            licensed = licensed_lane(cur)
            pipeline = pipeline_lane(cur)
            funnel = intake_funnel(cur)
            ratio = ratio_50_to_1(cur)
            dates = date_distribution(cur)
            dupes = duplicate_report(cur)
    finally:
        conn.close()

    lic_total = sum(p["events_total"] for p in licensed["providers"])
    published_total = lic_total + pipeline["canonical_events_total"]
    producing = len(licensed["providers"]) + len(
        [c for c in pipeline["candidates_by_source"]
         if c["source"] != "(unknown source)"])
    report = {
        "licensed_lane": licensed,
        "pipeline_lane": pipeline,
        "intake_funnel": funnel,
        "ratio_50_to_1": ratio,
        "date_distribution": dates,
        "duplicate_report": dupes,
        "totals": {
            "published_events_total": published_total,
            "published_upcoming": (
                sum(p["events_upcoming"] for p in licensed["providers"])
                + pipeline["canonical_events_upcoming"]),
            "sources_cataloged": funnel["sources_total"],
            "sources_producing_rows": producing,
            "events_per_producing_source": (
                round(published_total / producing, 1) if producing else None),
            "events_per_cataloged_source": (
                round(published_total / funnel["sources_total"], 1)
                if funnel["sources_total"] else None),
        },
    }
    json.dump(report, sys.stdout, indent=2, default=str)
    print()
    t = report["totals"]
    print(f"scope: {t['published_events_total']} published events "
          f"({t['published_upcoming']} upcoming) · "
          f"{t['sources_cataloged']} cataloged sources · "
          f"{t['sources_producing_rows']} producing · "
          f"{t['events_per_producing_source']} events/producing source",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
