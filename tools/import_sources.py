"""Bulk-import the master source catalog JSON into the `source` table.
Source: extracted from Entertainment-App-Code-v1-4 reference build (tools/import_sources.py)
"""
import argparse
import json
import os
import sys

import psycopg2

# Make the repo root importable when run directly as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from worker.db_config import resolve_dsn


# The gate treats source_class as EVIDENCE STRENGTH: worker/gating.py promotes
# on a single source when its class is an anchor (festival_feed, ticketing,
# venue_calendar, claimed_upload, email_opt_in) and otherwise demands 2-source
# corroboration. So the value written here decides whether a source's events
# can ever reach /tonight.
#
# FAIL LOUD (2026-07-26): this used to default to the string "unknown" when a
# catalog row had no category. "unknown" is not an anchor class and never
# corroborates with itself, so such a source produced events that were held
# forever with `Insufficient corroboration (have 1; need 2)` — a silent,
# permanent dead end created by a missing field. A source whose evidence class
# was never decided is a config defect, and this refuses it at import instead
# of writing a row that can never promote.
#
# It deliberately does NOT guess: inferring `venue_calendar` from a name would
# manufacture anchor evidence and let unverified single-source events promote,
# which is the gate's whole reason to exist. Classification comes from the
# catalog or not at all.
KNOWN_SOURCE_CLASSES = frozenset({
    # anchors — one is enough to promote (worker/gating.py ANCHOR_CLASSES)
    "festival_feed", "ticketing", "venue_calendar", "claimed_upload",
    "email_opt_in",
    # non-anchors — real classes, but they need corroboration
    "local_media", "city_calendar", "social", "university_calendar",
    "artist_aggregator", "music_platform", "search_benchmark", "link_hub",
    "calendar_feed", "community", "directory", "library_calendar",
    "artist_directory",
})


def _require_source_class(s: dict) -> str:
    """The source's evidence class, or a loud failure. Never a silent default."""
    value = s.get("category") or s.get("source_type")
    if not value:
        raise SystemExit(
            f"import_sources: source {s.get('name')!r} has no `category` — "
            "refusing to import. source_class decides whether this source's "
            "events can promote at all; an unset one becomes a permanent "
            "dead end (held forever on 'Insufficient corroboration'). Set a "
            "category in the catalog. Known values: "
            f"{', '.join(sorted(KNOWN_SOURCE_CLASSES))}")
    if value not in KNOWN_SOURCE_CLASSES:
        raise SystemExit(
            f"import_sources: source {s.get('name')!r} has category "
            f"{value!r}, which the gate does not recognise — refusing to "
            "import. An unrecognised class silently behaves as a non-anchor. "
            "Add it to KNOWN_SOURCE_CLASSES here (and to ANCHOR_CLASSES in "
            "worker/gating.py ONLY if it is genuinely first-party evidence), "
            "or correct the catalog.")
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True, help="Path to sources JSON")
    # No hardcoded DSN default: use --dsn, else resolve from env
    # (ONELIVE_DB_DSN, or the explicit ONELIVE_DEV_DB=1 dev opt-in).
    ap.add_argument("--dsn", default=None)
    args = ap.parse_args()
    dsn = args.dsn or resolve_dsn()

    with open(args.json, "r", encoding="utf-8") as f:
        sources = json.load(f)

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            for s in sources:
                # ON CONFLICT (name) requires the source_name_key unique
                # constraint (migration 0009). On conflict we refresh the
                # mutable columns so re-importing an updated catalog is a true
                # upsert, not a silent no-op.
                cur.execute("""
                  insert into source (name, source_type, base_url, enabled, credibility_weight, config)
                  values (%s,%s,%s,%s,%s,%s::jsonb)
                  on conflict (name) do update set
                    source_type = excluded.source_type,
                    base_url = excluded.base_url,
                    enabled = excluded.enabled,
                    credibility_weight = excluded.credibility_weight,
                    config = excluded.config
                """, (
                    s["name"],
                    _require_source_class(s),
                    s.get("base_url"),
                    True,
                    float(s.get("credibility_weight", 0.5)),
                    json.dumps(s),
                ))
        conn.commit()
    print(f"Imported {len(sources)} sources from {args.json}")


if __name__ == "__main__":
    main()
