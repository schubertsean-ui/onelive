"""Shared FastAPI dependencies: the service-role DB connection.

All API routers depend on `get_db` for a single, consistent connection path
(service-role psycopg2 -- bypasses RLS by design; see docs/OPERATING_RULES.md
and STATE.md's RLS section for why that is safe today).
"""
from typing import Dict, Any

import psycopg2
from fastapi import Depends

from api.clerk_auth import require_allowlisted_user
from worker.db_config import resolve_dsn


def get_db():
    return psycopg2.connect(resolve_dsn())


def require_admin(user: Dict[str, Any] = Depends(require_allowlisted_user)) -> Dict[str, Any]:
    """Real auth for ops actions: a valid, allowlisted Clerk token (layer 2).

    In stealth every allowlisted user is an operator, so allowlisted == admin.
    Backed by api.clerk_auth (independent JWKS/RS256 + azp + email-allowlist
    verification); replaces the fail-open stub.
    """
    return user
