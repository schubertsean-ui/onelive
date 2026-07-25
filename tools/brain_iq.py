#!/usr/bin/env python3
"""brain_iq — CLI for the continuous, multi-dimensional Brain IQ score.

SUMMARY: computes the brain's THREE kinds of smartness (KNOWLEDGE, EFFICIENCY,
LEARNING — brain/iq.py), shows the scorecard + trend, appends a timestamped row
to the continuous trend ledger (docs/metrics/BRAIN_IQ_LEDGER.md), and guards a
ONE-WAY RATCHET on the two GATED dimensions (KNOWLEDGE accuracy and
EFFICIENCY-work). No LLM, no network, no spend — every number is a measured,
reproducible fact, which is the whole point: "the brain gets quantifiably
smarter" becomes something we MEASURE and TREND, not assert.

The measurement instant is ALWAYS passed by the caller/CI (``--append TIMESTAMP``)
and never read from the wall clock in code — the scoring library is deterministic
and clock-free (latency is the one observed-but-never-gated exception, recorded
for the trend only).

Modes:
  --print              compute + show the 3-kind scorecard + trend (no write)
  --append TIMESTAMP   append one ledger row stamped TIMESTAMP (caller-supplied)
  --check              one-way ratchet GUARD: each GATED dimension must be >= its
                       best recorded value minus a small epsilon; exit non-zero
                       on regression. Fail loud.

Exit codes (tools/README.md convention):
  0 = ok (printed / appended / ratchet held);
  1 = a GATED dimension REGRESSED below its best recorded value (ratchet fired);
  2 = could not run (ledger missing/unreadable/unparseable, or bad args) — fail loud.

Usage:
  python tools/brain_iq.py --print
  python tools/brain_iq.py --append 2026-07-25T12:00:00Z
  python tools/brain_iq.py --check
"""
from __future__ import annotations

import argparse
import pathlib
import sys

# Running as a script puts tools/ on sys.path[0], not the repo root; add the
# root so `brain.*` imports exactly as it does under pytest.
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from brain.iq import (  # noqa: E402  (path bootstrap must precede import)
    GATED_DIMENSIONS,
    MEASURED,
    NOT_YET_MEASURED,
    BrainIQ,
    check_ratchet,
    compute_brain_iq,
    trend_symbol,
)

DEFAULT_LEDGER = _REPO_ROOT / "docs" / "metrics" / "BRAIN_IQ_LEDGER.md"

# The machine-readable table marker: rows between these fences are parsed. Prose
# above/below (including the measurement-coverage section) is free text.
_TABLE_HEADER_CELLS = ("timestamp", "knowledge", "efficiency", "learning",
                       "composite", "trend")


class LedgerError(Exception):
    """Raised when the trend ledger cannot be read or parsed — fail loud."""


# --- ledger parsing (a markdown table is the store; disk is truth) -----------
def _parse_row(cells: list) -> dict:
    """Parse a data row's cells into a dict, or raise if the numbers are bad."""
    return {
        "timestamp": cells[0],
        "knowledge": float(cells[1]),
        "efficiency": float(cells[2]),
        "learning": float(cells[3]),
        "composite": float(cells[4]),
        "trend": cells[5] if len(cells) > 5 else "",
    }


def load_ledger_rows(path: pathlib.Path) -> list:
    """Return the parsed data rows of the trend ledger (oldest-first).

    A row is a table line whose first four numeric columns parse as floats; the
    header row and separator row (dashes) are skipped. Fail loud if the file is
    absent or has NO parseable rows — a ratchet with no history proves nothing.
    """
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise LedgerError(f"cannot read Brain IQ ledger at {path}: {exc}")
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 5:
            continue
        low = [c.lower() for c in cells]
        if low[:6] == list(_TABLE_HEADER_CELLS) or low[:5] == list(_TABLE_HEADER_CELLS[:5]):
            continue  # header
        if set(cells[1]) <= set("-: "):
            continue  # separator row
        try:
            rows.append(_parse_row(cells))
        except (ValueError, IndexError):
            # A table line whose numeric columns do not parse is not a data row.
            continue
    if not rows:
        raise LedgerError(
            f"Brain IQ ledger at {path} has no parseable data rows — a one-way "
            f"ratchet needs at least one recorded measurement to guard against.")
    return rows


def best_gated(rows: list) -> dict:
    """The best (max) recorded value of each GATED dimension across all rows."""
    return {name: max(r[name] for r in rows) for name in GATED_DIMENSIONS}


def _format_row(iq: BrainIQ, previous_composite) -> str:
    trend = trend_symbol(iq.composite, previous_composite)
    return (f"| {iq.now_iso} | {iq.knowledge.score:.4f} | "
            f"{iq.efficiency.score:.4f} | {iq.learning.score:.4f} | "
            f"{iq.composite:.4f} | {trend} |")


def _is_data_row(stripped: str) -> bool:
    """True iff a stripped line is a parseable data row (not header/separator)."""
    if not stripped.startswith("|"):
        return False
    cells = [c.strip() for c in stripped.strip("|").split("|")]
    if len(cells) < 5:
        return False
    if cells[0].lower() == _TABLE_HEADER_CELLS[0]:
        return False
    if set(cells[1]) <= set("-: "):
        return False
    try:
        _parse_row(cells)
    except (ValueError, IndexError):
        return False
    return True


def append_row(path: pathlib.Path, iq: BrainIQ) -> str:
    """Insert one ledger row for ``iq`` INTO the trend table (not at file end).

    The row lands after the last existing data row (or after the table's
    separator line when the table is empty), so the ledger stays a real table
    with the measurement-coverage prose beneath it. Trend is computed vs the last
    existing row's composite.
    """
    try:
        rows = load_ledger_rows(path)
        previous_composite = rows[-1]["composite"]
    except LedgerError:
        previous_composite = None  # first-ever row: no predecessor, trend "-"
    line = _format_row(iq, previous_composite)

    lines = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
    insert_at = None
    separator_at = None
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped.startswith("|") and set(stripped.strip("|")) <= set("-: |"):
            separator_at = i
        if _is_data_row(stripped):
            insert_at = i
    if insert_at is None:
        if separator_at is None:
            raise LedgerError(
                f"Brain IQ ledger at {path} has no trend table to append into.")
        insert_at = separator_at
    lines.insert(insert_at + 1, line)
    pathlib.Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return line


# --- scorecard rendering ------------------------------------------------------
def _print_scorecard(iq: BrainIQ, previous_composite) -> None:
    print("=" * 78)
    print(" OneLive · Brain IQ · 3 kinds of smartness · deterministic, no spend")
    print(" 'it gets quantifiably smarter' — measured & trended, never asserted")
    print("=" * 78)
    print(f"  measured_at (passed in): {iq.now_iso}")
    print("-" * 78)
    for dim in (iq.knowledge, iq.efficiency, iq.learning):
        gated = "GATED " if dim.name in GATED_DIMENSIONS else "trend "
        print(f"  [{gated}] {dim.name.upper():<11} score = {dim.score:.4f}")
        for key in sorted(dim.sub_metrics):
            print(f"            · {key:<22} {dim.sub_metrics[key]:.6f}")
    print("-" * 78)
    trend = trend_symbol(iq.composite, previous_composite)
    prev = "n/a" if previous_composite is None else f"{previous_composite:.4f}"
    print(f"  COMPOSITE = {iq.composite:.4f}   trend vs previous ({prev}): {trend}")
    print("  (composite HIDES detail — the per-dimension scores govern.)")
    print("-" * 78)
    print("  latency note: efficiency records an OBSERVED wall latency "
          f"({iq.efficiency.sub_metrics.get('observed_latency_s', 0.0):.6f}s) for")
    print("  the trend only — it is machine-dependent/flaky and is NEVER gated.")
    print("-" * 78)
    print("  MEASUREMENT COVERAGE (Goodhart honesty — measured vs NOT-yet):")
    for item in MEASURED:
        print(f"    [measured]     {item.name}")
    for item in NOT_YET_MEASURED:
        print(f"    [NOT yet]      {item.name}")
        print(f"                   trigger: {item.trigger}")
    print("=" * 78)


# --- modes --------------------------------------------------------------------
def _do_print(ledger: pathlib.Path) -> int:
    iq = compute_brain_iq(now_iso="(unrecorded --print run)")
    previous_composite = None
    try:
        rows = load_ledger_rows(ledger)
        previous_composite = rows[-1]["composite"]
    except LedgerError:
        previous_composite = None
    _print_scorecard(iq, previous_composite)
    return 0


def _do_append(ledger: pathlib.Path, timestamp: str) -> int:
    if not timestamp:
        print("brain_iq: INVALID — --append requires a TIMESTAMP (the caller/CI "
              "supplies it; code never reads the wall clock).", file=sys.stderr)
        return 2
    iq = compute_brain_iq(now_iso=timestamp)
    line = append_row(ledger, iq)
    print(f"brain_iq: APPENDED row to {ledger}:")
    print(f"  {line}")
    return 0


def _do_check(ledger: pathlib.Path) -> int:
    try:
        rows = load_ledger_rows(ledger)
    except LedgerError as exc:
        print(f"brain_iq: INVALID — {exc}", file=sys.stderr)
        return 2
    best = best_gated(rows)
    iq = compute_brain_iq(now_iso="(ratchet --check run)")
    regressions = check_ratchet(iq, best=best)
    scores = iq.gated_scores()
    for name in GATED_DIMENSIONS:
        print(f"  {name:<11} now={scores[name]:.4f}  best={best[name]:.4f}")
    if regressions:
        for reg in regressions:
            print(f"brain_iq: REGRESSION — {reg.dimension} score {reg.current:.4f} "
                  f"dropped below its best recorded value {reg.best:.4f}. The brain "
                  f"got WORSE at this kind of smartness. Do not merge on red.",
                  file=sys.stderr)
        return 1
    print("brain_iq: PASS — every gated dimension met or beat its best recorded "
          "value (one-way ratchet held).")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", type=pathlib.Path, default=DEFAULT_LEDGER,
                        help="trend ledger (default: docs/metrics/BRAIN_IQ_LEDGER.md)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--print", dest="do_print", action="store_true",
                      help="compute + show the 3-kind scorecard + trend (no write)")
    mode.add_argument("--append", metavar="TIMESTAMP", default=None,
                      help="append one ledger row stamped TIMESTAMP (caller-supplied)")
    mode.add_argument("--check", action="store_true",
                      help="one-way ratchet guard on the gated dimensions")
    args = parser.parse_args(argv)

    if args.do_print:
        return _do_print(args.ledger)
    if args.append is not None:
        return _do_append(args.ledger, args.append)
    if args.check:
        return _do_check(args.ledger)
    parser.error("no mode selected")  # unreachable (group is required)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
