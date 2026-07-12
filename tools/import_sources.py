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
                    s.get("category", s.get("source_type", "unknown")),
                    s.get("base_url"),
                    True,
                    float(s.get("credibility_weight", 0.5)),
                    json.dumps(s),
                ))
        conn.commit()
    print(f"Imported {len(sources)} sources from {args.json}")


if __name__ == "__main__":
    main()
