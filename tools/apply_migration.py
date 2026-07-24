#!/usr/bin/env python3
"""Apply a single SQL migration file to the database (ONELIVE_DB_DSN).

For IDEMPOTENT migrations only (`create ... if not exists`, `add column if not
exists`, `drop policy if exists` + create) so a re-run is safe. The whole file
is executed in one transaction; any error rolls back and fails LOUD (never a
partial apply). The SQL comes from a committed migration file (not external
input); it is passed to .execute() as a plain string variable, which is the
migration-runner path, not dynamic SQL constructed from user data.

Usage: python3 tools/apply_migration.py supabase/migrations/0010_xxx.sql
"""
from __future__ import annotations

import argparse
import pathlib
import sys


def apply_sql(conn, sql: str) -> None:
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Apply one idempotent SQL migration.")
    ap.add_argument("path", help="path to the .sql migration file")
    args = ap.parse_args(argv)

    p = pathlib.Path(args.path)
    if not p.is_file():
        print(f"migration file not found: {p}", file=sys.stderr)
        return 2
    sql = p.read_text()

    import psycopg2

    from worker.db_config import resolve_dsn

    conn = psycopg2.connect(resolve_dsn())
    try:
        apply_sql(conn, sql)
    finally:
        conn.close()
    print(f"applied migration: {p.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
