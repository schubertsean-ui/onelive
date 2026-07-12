"""Shared FastAPI dependencies: the service-role DB connection.

All API routers depend on `get_db` for a single, consistent connection path
(service-role psycopg2 — bypasses RLS by design; see docs/OPERATING_RULES.md
and STATE.md's RLS section for why that is safe today).
"""
from typing import Dict, Any
import os

import psycopg2


DB_DSN = os.getenv("ONELIVE_DB_DSN", "dbname=onelive user=postgres password=postgres host=localhost")


def get_db():
    return psycopg2.connect(DB_DSN)


def require_admin() -> Dict[str, Any]:
    # Replace with real auth + RBAC
    return {"user_id": None, "role": "admin"}
