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

Defense in depth (evaluator, PR #19 rounds 1–2): scope AND masking. The
URL-encoded DSN differs from both GitHub secrets, so GitHub's automatic
redaction does not cover it — `--mask-command` prints a properly ESCAPED
`::add-mask::` workflow command (`%`→`%25`, CR→`%0D`, LF→`%0A`, the
escaping whose absence was round 1's leak) so the runner redacts the
assembled value in all subsequent logs even if some future failure path
prints the environment. Outer whitespace on both inputs is normalized
away (the most common paste artifact — trailing newline/space); INTERIOR
line breaks still hard-fail.

Exit codes per tools/README.md: 0 printed / 2 misconfiguration (empty
DSN, placeholder without password, interior line breaks).
"""
from __future__ import annotations

import argparse
import os
import sys
import urllib.parse

PLACEHOLDER = "[YOUR-PASSWORD]"


def assemble(raw: str, password: str) -> str:
    """Return the final DSN. Raises ValueError on misconfiguration.

    Error messages deliberately contain NO secret material — they may end
    up in CI logs.
    """
    # Outer whitespace (trailing newline/space) is a paste artifact, not
    # information — normalize instead of punishing the founder for it.
    raw = raw.strip()
    password = password.strip()
    if not raw:
        raise ValueError(
            "ONELIVE_DB_DSN_RAW is empty — paste the Supabase Session-pooler "
            "URI (as-is) into the ONELIVE_DB_DSN secret."
        )
    if PLACEHOLDER in raw:
        if not password:
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
    if "\n" in final or "\r" in final or any(c.isspace() for c in final):
        raise ValueError(
            "assembled DSN contains interior whitespace or a line break "
            "(copy-paste artifact) — re-paste the secret as a single line."
        )
    return final


def escape_workflow_command_value(value: str) -> str:
    """Escape a value for use in a GitHub workflow command (::add-mask::).

    Order matters: '%' first, or the escapes themselves get re-escaped.
    Without this, a value containing %25/%0A/%0D sequences registers the
    WRONG mask and the real value leaks (evaluator, PR #19 round 1).
    """
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Assemble the DB DSN from as-pasted Supabase secrets."
    )
    parser.add_argument(
        "--mask-command", action="store_true",
        help="print an escaped ::add-mask:: workflow command for the "
             "assembled DSN (register redaction with the CI runner) instead "
             "of the DSN itself",
    )
    args = parser.parse_args(argv)
    try:
        final = assemble(
            os.environ.get("ONELIVE_DB_DSN_RAW", ""),
            os.environ.get("ONELIVE_DB_PASSWORD", ""),
        )
    except ValueError as exc:
        print(f"assemble_dsn: FAIL — {exc}", file=sys.stderr)
        return 2
    if args.mask_command:
        print(f"::add-mask::{escape_workflow_command_value(final)}")
    else:
        print(final)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
