"""Single source of truth for the service-role DB DSN.

No silent production default. `ONELIVE_DB_DSN` must be set in every real
deployment. A localhost dev DSN (which carries the well-known `password=postgres`
credential) is returned ONLY when the operator explicitly opts in with
`ONELIVE_DEV_DB=1`, so a missing/misconfigured DSN can never silently point a
production process at a throwaway local database. This mirrors
docs/OPERATING_RULES.md §3.1: fail loud on misconfiguration, never degrade
silently.

Resolution is lazy (call `resolve_dsn()` at connection time, not at import) so
importing a DB-backed module never requires the env to be set — only actually
opening a connection does.
"""
from __future__ import annotations

import os

# Dev-only convenience DSN. Not a production credential: only reachable behind
# the explicit ONELIVE_DEV_DB=1 opt-in below.
_DEV_DSN = "dbname=onelive user=postgres password=postgres host=localhost"


def resolve_dsn() -> str:
    dsn = os.getenv("ONELIVE_DB_DSN")
    if dsn:
        return dsn
    if os.getenv("ONELIVE_DEV_DB") == "1":
        return _DEV_DSN
    raise RuntimeError(
        "ONELIVE_DB_DSN is not set. Set it to the database DSN, or set "
        "ONELIVE_DEV_DB=1 to use the localhost dev database. Refusing to fall "
        "back to a hardcoded local default in an unknown environment."
    )
