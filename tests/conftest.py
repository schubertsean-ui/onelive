"""Shared pytest fixtures for OneLive.

Most tests here are pure-logic and need no database. Tests that DO need a live
Postgres are marked with `@pytest.mark.dbintegration` and use the `db_conn`
fixture, which skips automatically unless ONELIVE_TEST_DB_DSN is set.

    export ONELIVE_TEST_DB_DSN="postgresql://user:pass@localhost:5432/onelive_test"
    pytest -m dbintegration        # run only DB integration tests
    pytest -m "not dbintegration"  # run only pure-logic tests (default in CI)
"""
import os
import sys

import pytest

# Ensure the repo root is importable (so `import worker.*` / `import api.*` work
# regardless of where pytest is invoked from).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "dbintegration: test requires a live Postgres (set ONELIVE_TEST_DB_DSN)",
    )


@pytest.fixture
def db_conn():
    dsn = os.getenv("ONELIVE_TEST_DB_DSN")
    if not dsn:
        pytest.skip("ONELIVE_TEST_DB_DSN not set; skipping DB integration test")
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(dsn)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()
