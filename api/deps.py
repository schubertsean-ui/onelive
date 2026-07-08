import os
import psycopg2
from typing import Dict, Any

DB_DSN = os.getenv("ONELIVE_DB_DSN", "dbname=onelive user=postgres password=postgres host=localhost")


def get_db():
    return psycopg2.connect(DB_DSN)


def require_admin() -> Dict[str, Any]:
    # Replace with real auth + RBAC
    return {"user_id": None, "role": "admin"}
