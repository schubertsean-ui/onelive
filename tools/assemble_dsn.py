#!/usr/bin/env python3
"""Assemble the runtime DB DSN from as-pasted Supabase secrets (fail closed).

Greppable summary: founder-ergonomics support (PR #19) — the Supabase
Connect panel emits a URI containing a literal `[YOUR-PASSWORD]`
placeholder, and hand-editing a credential string is error-prone (and
silently corrupts URIs when passwords contain reserved characters). This
script reads env `ONELIVE_DB_DSN_RAW` (the URI exactly as pasted) and
`ONELIVE_DB_PASSWORD` (optional separate secret), splices the URL-ENCODED
password into the placeholder, and prints the final DSN to stdout —
NOTHING else is ever printed to stdout, and no secret material is ever
written to stderr, so callers can capture stdout silently and error
output stays log-safe. Scope discipline: the caller (ingest.yml) invokes
this INSIDE the single step that needs the DSN and exports it only there;
the assembled credential must never enter GITHUB_ENV, step outputs, or
workflow-command logs (evaluator findings, PR #19 round 1).

Exit codes per tools/README.md: 0 printed / 2 misconfiguration (empty
DSN, placeholder without password, line breaks).
"""
from __future__ import annotations

import os
import sys
import urllib.parse

PLACEHOLDER = "[YOUR-PASSWORD]"


def assemble(raw: str, password: str) -> str:
    """Return the final DSN. Raises ValueError on misconfiguration.

    Error messages deliberately contain NO secret material — they may end
    up in CI logs.
    """
    if not raw.strip():
        raise ValueError(
            "ONELIVE_DB_DSN_RAW is empty — paste the Supabase Session-pooler "
            "URI (as-is) into the ONELIVE_DB_DSN secret."
        )
    if PLACEHOLDER in raw:
        if not password.strip():
            raise ValueError(
                "the DSN still contains the [YOUR-PASSWORD] placeholder and "
                "ONELIVE_DB_PASSWORD is not set. Recommended: keep the DSN "
                "exactly as Supabase shows it and add the database password "
                "as its own secret named ONELIVE_DB_PASSWORD."
            )
        # URL-encode so reserved characters in the password (@ : / % …)
        # cannot corrupt the URI — safer than any hand edit.
        final = raw.replace(PLACEHOLDER, urllib.parse.quote(password, safe=""))
    else:
        final = raw
    if "\n" in final or "\r" in final:
        raise ValueError(
            "assembled DSN contains a line break (copy-paste artifact) — "
            "re-paste the secret as a single line."
        )
    return final


def main() -> int:
    try:
        final = assemble(
            os.environ.get("ONELIVE_DB_DSN_RAW", ""),
            os.environ.get("ONELIVE_DB_PASSWORD", ""),
        )
    except ValueError as exc:
        print(f"assemble_dsn: FAIL — {exc}", file=sys.stderr)
        return 2
    print(final)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
