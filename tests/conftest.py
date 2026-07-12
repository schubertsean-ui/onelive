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
    config.addinivalue_line(
        "markers",
        "perf: performance/timing benchmark (skipped by default; run explicitly "
        "with `pytest -m perf`, see tools/profile_target.py and docs/TESTS.md)",
    )
    config.addinivalue_line(
        "markers",
        "visual: visual-regression check against tests/visual_baselines/ "
        "(skipped by default; requires a booted app, see tools/visual_regression.py)",
    )


def pytest_collection_modifyitems(config, items):
    """perf and visual tests are opt-in only: they require either a real
    timing budget (perf) or a booted app + baseline images (visual), neither
    of which belongs in the default fast/pure-logic suite that runs on every
    commit. Skip them UNLESS the run explicitly selected them via `-m perf`,
    `-m visual`, or a combination that mentions them (e.g. `-m "perf or visual"`)
    -- mirrors how `-m dbintegration` is used to opt IN to DB tests elsewhere
    in this file, just via auto-skip instead of a fixture, since there's no
    natural single fixture every perf/visual test shares.
    """
    markexpr = config.getoption("markexpr", default="") or ""
    for opt_in_marker in ("perf", "visual"):
        if opt_in_marker in markexpr:
            continue  # this run explicitly asked for these; don't skip them
        skip_marker = pytest.mark.skip(
            reason=f"'{opt_in_marker}' tests are opt-in only; run with `pytest -m {opt_in_marker}`"
        )
        for item in items:
            if opt_in_marker in item.keywords:
                item.add_marker(skip_marker)


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
