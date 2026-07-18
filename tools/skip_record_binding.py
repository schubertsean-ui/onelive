#!/usr/bin/env python3
"""skip_record_binding — bind a validate SKIP to its OPEN docs/RECORD.md row.

SUMMARY: the mechanical half of the no-silent-deferrals rule for the validate
gate (Kaizen 2026-07-18, classes skip-report-missing-record-citation +
unverifiable-ci-claim — the 3-PR repeat class #20/#27/#35). A check that
SKIPs in `tools/validate` for environmental reasons must correspond to an
OPEN row in docs/RECORD.md (the deferral register: deviation + cited bar +
objective trigger). This tool answers exactly one question, mechanically:
"does an OPEN Record row name this check?" — printing the row id (e.g.
R-002) on success, exiting non-zero on failure so the gate can go RED on an
unrecorded skip. It never edits anything and has no side effects.

Usage:
    python tools/skip_record_binding.py <check_name> [--record docs/RECORD.md]

Exit codes: 0 = an OPEN row names the check (row id printed to stdout);
            1 = no OPEN row names the check (message on stderr);
            2 = usage / record file unreadable (fail loud, never fail open).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_ROW_RE = re.compile(r"^\|\s*(R-\d+)\s*\|")


def parse_record_rows(record_text: str) -> list[tuple[str, str, str]]:
    """Return (row_id, full_row_text, status) for every R-### table row.

    Status is the last non-empty cell of the row (the register's Status
    column), e.g. "OPEN" or "RESOLVED (founder 2026-07-15: ...)".
    """
    rows: list[tuple[str, str, str]] = []
    for line in record_text.splitlines():
        m = _ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        status = cells[-1] if cells else ""
        rows.append((m.group(1), line, status))
    return rows


def find_open_record_row(check_name: str, record_text: str) -> str | None:
    """Return the id of an OPEN Record row whose text names check_name.

    Matching is deliberately simple and conservative: literal substring of
    the check name in the row, and a status cell that starts with OPEN.
    RESOLVED/closed rows never satisfy the binding — resolved debt cannot
    excuse a live skip.
    """
    if not check_name.strip():
        return None
    for row_id, row_text, status in parse_record_rows(record_text):
        if check_name in row_text and status.upper().startswith("OPEN"):
            return row_id
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("check_name", help="validate check name, e.g. visual_regression")
    ap.add_argument(
        "--record",
        default="docs/RECORD.md",
        help="path to the deferral register (default: docs/RECORD.md)",
    )
    args = ap.parse_args(argv)

    record_path = Path(args.record)
    try:
        record_text = record_path.read_text(encoding="utf-8")
    except OSError as exc:
        # Unreadable register = fail LOUD, never fail open (a missing
        # register must not look like "no binding required").
        print(f"skip_record_binding: cannot read {record_path}: {exc}", file=sys.stderr)
        return 2

    row_id = find_open_record_row(args.check_name, record_text)
    if row_id is None:
        print(
            f"skip_record_binding: no OPEN {record_path} row names "
            f"'{args.check_name}' — an unrecorded skip is a violation: open the "
            f"row (deviation + cited bar + objective trigger) or fix the check.",
            file=sys.stderr,
        )
        return 1
    print(row_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
