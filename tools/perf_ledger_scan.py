#!/usr/bin/env python3
"""M9 performance-prediction scanner — mechanical arm of KAIZEN §M9.

Greppable summary: founder rule (2026-07-23): any change that CLAIMS a
performance/cost/latency/quality improvement opens an M9 row in
docs/metrics/KAIZEN_LEDGER.md as a PREDICTION and MEASURES actual-vs-expected
at an objective trigger. This scanner parses the "## M9" table and enforces
structural completeness per row status, so a bare "this is faster/cheaper"
claim cannot ship unmeasured and a MEASURED row cannot lack its actual/delta/
verdict. It also prints the calibration summary (PENDING vs MEASURED counts,
MET-rate, and any UNDER/OVER misses to review) — the meta-metric.

This is NOT (yet) blocking inside tools/validate: it is a session-close and
CI-advisory review, exactly like the RECORD.md OPEN-row review it mirrors.
Wiring it into validate is a gate-custody change (evaluator-reviewed) and is
tracked in KAIZEN §M9, not silently deferred.

Exit codes (per tools/README.md): 0 clean / 1 structural violations found /
2 hard failure (ledger or the M9 section missing / unparseable — the
discipline requires the section to exist, so its absence fails loud).
"""
from __future__ import annotations

import argparse
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
LEDGER = REPO / "docs" / "metrics" / "KAIZEN_LEDGER.md"

# The columns the M9 table must carry, matched by a keyword in each header
# cell (so cosmetic header text like "Expected (%Δ)" still resolves).
COLUMN_KEYWORDS = (
    "id", "change", "metric", "baseline", "expected", "basis", "trigger",
    "actual", "delta", "verdict", "status",
)

# Cell values that count as "not filled in".
_EMPTY = {"", "—", "-", "–"}
# Sentinel meaning "not measured yet" — allowed ONLY on a PENDING row's
# actual/delta/verdict, never on a MEASURED row.
_PENDING = "PENDING"

VALID_STATUS = {"PENDING-MEASUREMENT", "MEASURED"}
VALID_VERDICT = {"MET", "UNDER", "OVER"}


class LedgerError(Exception):
    """Hard failure: the ledger or its M9 section cannot be read/parsed."""


def _is_empty(cell: str) -> bool:
    return cell.strip() in _EMPTY


def _split_row(line: str) -> list[str]:
    """Split a markdown table row on unescaped pipes, dropping the empty
    cells produced by the leading/trailing '|'."""
    parts = [c.strip() for c in line.strip().strip("|").split("|")]
    return parts


def _extract_m9_table(text: str) -> list[str]:
    """Return the raw '|...|' lines of the table under the '## M9' heading.

    Raises LedgerError if the section or a table under it is absent — the
    discipline requires the section to exist, so we fail loud rather than
    silently pass an empty scan.
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## M9"):
            start = i
            break
    if start is None:
        raise LedgerError(
            "no '## M9' section in docs/metrics/KAIZEN_LEDGER.md — the "
            "expected-vs-actual performance discipline (KAIZEN §M9) requires "
            "it. Restore the section rather than removing the check."
        )
    table: list[str] = []
    for line in lines[start + 1:]:
        if line.startswith("## "):  # next section ends the M9 block
            break
        if line.lstrip().startswith("|"):
            table.append(line)
    if len(table) < 3:  # header + separator + >=1 data row
        raise LedgerError(
            "the '## M9' section has no data table (need a header row, a "
            "'---' separator, and at least one prediction row)."
        )
    return table


def _map_columns(header_cells: list[str]) -> dict[str, int]:
    """Map each required keyword to its column index in the header."""
    col: dict[str, int] = {}
    lowered = [c.lower() for c in header_cells]
    for key in COLUMN_KEYWORDS:
        for idx, cell in enumerate(lowered):
            if key in cell:
                col[key] = idx
                break
        else:
            raise LedgerError(
                f"the M9 table header is missing a '{key}' column "
                f"(found columns: {header_cells!r})."
            )
    return col


def scan(text: str) -> list[str]:
    """Return a list of human-readable violation strings (empty == clean).

    Raises LedgerError (→ exit 2) on unparseable structure.
    """
    table = _extract_m9_table(text)
    header = _split_row(table[0])
    col = _map_columns(header)
    violations: list[str] = []

    def cell(row: list[str], key: str) -> str:
        idx = col[key]
        return row[idx] if idx < len(row) else ""

    for raw in table[2:]:  # skip header + separator
        row = _split_row(raw)
        rid = cell(row, "id") or "<no-id>"
        status = cell(row, "status").strip()

        if status not in VALID_STATUS:
            violations.append(
                f"{rid}: Status {status!r} is not one of {sorted(VALID_STATUS)}."
            )
            continue

        # Required on EVERY row: the prediction itself must be complete.
        for key in ("change", "metric", "baseline", "expected", "basis",
                    "trigger"):
            if _is_empty(cell(row, key)):
                violations.append(
                    f"{rid}: {key} is empty — a PENDING prediction needs "
                    f"Metric, Baseline, Expected, Basis, and Trigger before "
                    f"it can ship (KAIZEN §M9)."
                )

        if status == "MEASURED":
            # A result cannot rest on a phantom baseline or an unfilled actual.
            baseline = cell(row, "baseline")
            if baseline.strip().upper().startswith(_PENDING):
                violations.append(
                    f"{rid}: MEASURED but Baseline is still {_PENDING!r} — "
                    f"actual-vs-expected is meaningless without a real "
                    f"baseline; measure it before declaring the result."
                )
            for key in ("actual", "delta"):
                value = cell(row, key)
                if _is_empty(value) or value.strip().upper() == _PENDING:
                    violations.append(
                        f"{rid}: MEASURED but {key} is not filled in — the "
                        f"whole point of M9 is the measured actual and its "
                        f"delta from expected."
                    )
            verdict = cell(row, "verdict").strip().upper()
            if verdict not in VALID_VERDICT:
                violations.append(
                    f"{rid}: MEASURED Verdict {verdict!r} must be one of "
                    f"{sorted(VALID_VERDICT)} (a large miss either way is a "
                    f"defect to review, not a shrug)."
                )

    return violations


def _calibration_summary(text: str) -> str:
    """A short advisory report: the M9 meta-metric (prediction calibration)."""
    table = _extract_m9_table(text)
    header = _split_row(table[0])
    col = _map_columns(header)
    pending = measured = met = 0
    misses: list[str] = []
    for raw in table[2:]:
        row = _split_row(raw)
        status = (row[col["status"]] if col["status"] < len(row) else "").strip()
        if status == "PENDING-MEASUREMENT":
            pending += 1
        elif status == "MEASURED":
            measured += 1
            verdict = (row[col["verdict"]] if col["verdict"] < len(row)
                       else "").strip().upper()
            rid = (row[col["id"]] if col["id"] < len(row) else "?").strip()
            if verdict == "MET":
                met += 1
            elif verdict in ("UNDER", "OVER"):
                misses.append(f"{rid}={verdict}")
    rate = f"{met}/{measured}" if measured else "n/a (nothing measured yet)"
    out = [
        f"M9 calibration: {pending} PENDING, {measured} MEASURED, "
        f"MET-rate {rate}."
    ]
    if misses:
        out.append("  misses to review (should trend to zero): "
                   + ", ".join(misses))
    if pending:
        out.append(f"  {pending} open prediction(s) — review at session close: "
                   "a fired-but-unmeasured trigger is a defect, not a backlog "
                   "item.")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quiet", action="store_true",
        help="suppress the calibration summary; print only violations.",
    )
    args = parser.parse_args()

    if not LEDGER.exists():
        print(f"perf_ledger_scan: FAIL — {LEDGER} not found.", file=sys.stderr)
        return 2
    try:
        text = LEDGER.read_text(encoding="utf-8")
        violations = scan(text)
        summary = _calibration_summary(text)
    except LedgerError as exc:
        print(f"perf_ledger_scan: FAIL — {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        print(summary)
    if violations:
        print("perf_ledger_scan: M9 structural violations —", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1
    print("perf_ledger_scan: OK — every M9 prediction row is structurally "
          "complete for its status.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
