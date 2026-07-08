"""Bulk-import the master source catalog JSON into the `source` table.
Source: extracted from Entertainment-App-Code-v1-4 reference build (tools/import_sources.py)
"""
import argparse
import json
import os
import psycopg2

DEFAULT_DSN = os.getenv("ONELIVE_DB_DSN", "dbname=onelive user=postgres password=postgres host=localhost")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True, help="Path to sources JSON")
    ap.add_argument("--dsn", default=DEFAULT_DSN)
    args = ap.parse_args()

    with open(args.json, "r", encoding="utf-8") as f:
        sources = json.load(f)

    with psycopg2.connect(args.dsn) as conn:
        with conn.cursor() as cur:
            for s in sources:
                cur.execute("""
                  insert into source (name, source_type, base_url, enabled, credibility_weight, config)
                  values (%s,%s,%s,%s,%s,%s::jsonb)
                  on conflict do nothing
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
