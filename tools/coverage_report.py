"""Source coverage report — make source blindness MEASURABLE, not assumed.

WHY. A trust-first events feed can only be as good as its source coverage: an
event nobody's sources report on is invisible, and that blindness is silent
unless we measure it. This tool produces a county x category coverage grid plus
explicit "coverage debt" callouts (uncategorized sources, empty county/category
cells) so the gap the 43-source catalog hid becomes a number on a report.

TWO INPUT MODES (both first-class; neither is a fallback that hides truth):
  * --json PATH   : compute coverage from a catalog JSON file (the shape
                    tools/import_sources.py imports). Hermetic — no DB needed,
                    so it runs in CI/sandbox and is unit-tested.
  * --dsn / env   : ONELIVE_DB_DSN set -> read the live `source` table (the
                    ground truth after import). Table/column identifiers are
                    composed via psycopg2.sql — never f-strings.

If neither a JSON file nor a reachable DB is available, the tool says so LOUDLY
(prints the exact SQL to run via the Supabase connector) and exits non-zero. It
never prints an empty grid as if coverage were zero.

The 5-county Austin MSA and the canonical category vocabulary are defined here so
the grid always shows EVERY county and EVERY category — including the empty
cells, which are the entire point.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Canonical geography + vocabulary (mirrors migration 0010's CHECK domain).
COUNTIES: Tuple[str, ...] = ("travis", "williamson", "hays", "bastrop", "caldwell")
# NULL county = not county-specific (metro/state/national). Shown as its own row
# so metro-wide sources are visible, never conflated with a real county.
METRO_WIDE = "(metro-wide)"

CATEGORIES: Tuple[str, ...] = (
    "music", "theater", "visual_art", "film", "food",
    "literary", "community", "festival", "comedy", "dance", "museum", "university",
)

DEFAULT_DSN = os.getenv("ONELIVE_DB_DSN", "")


@dataclass
class CoverageResult:
    """A fully-computed coverage report. `verified` is False only when we could
    not read any source of truth (never to paper over an empty result)."""
    verified: bool
    source_count: int
    # grid[county_label][category] = number of sources covering that cell
    grid: Dict[str, Dict[str, int]]
    county_totals: Dict[str, int]
    category_totals: Dict[str, int]
    uncategorized: List[str] = field(default_factory=list)  # sources w/ no categories
    unknown_county: List[str] = field(default_factory=list)  # county not in domain
    empty_cells: List[Tuple[str, str]] = field(default_factory=list)
    reason: str = ""  # populated when not verified


def _blank_grid() -> Dict[str, Dict[str, int]]:
    labels = list(COUNTIES) + [METRO_WIDE]
    return {label: {cat: 0 for cat in CATEGORIES} for label in labels}


def _county_label(county: Optional[str]) -> Tuple[str, bool]:
    """Map a raw county value to a grid row label. Returns (label, is_unknown).
    None -> metro-wide row. An out-of-domain value is surfaced as unknown, never
    silently dropped."""
    if county is None or county == "":
        return METRO_WIDE, False
    if county in COUNTIES:
        return county, False
    return county, True  # out-of-domain; caller records it


def compute_coverage(sources: List[dict]) -> CoverageResult:
    """Pure function: fold a list of source dicts into a coverage grid. Shared by
    both the JSON and DB modes so they can never diverge."""
    grid = _blank_grid()
    county_totals = {label: 0 for label in list(COUNTIES) + [METRO_WIDE]}
    category_totals = {cat: 0 for cat in CATEGORIES}
    uncategorized: List[str] = []
    unknown_county: List[str] = []

    for s in sources:
        name = s.get("name", "<unnamed>")
        label, is_unknown = _county_label(s.get("county"))
        if is_unknown:
            unknown_county.append(f"{name} (county={s.get('county')!r})")
            # still count it under its raw label so the total is honest
            grid.setdefault(label, {cat: 0 for cat in CATEGORIES})
            county_totals.setdefault(label, 0)
        county_totals[label] += 1

        cats = s.get("coverage_categories") or []
        if not cats:
            uncategorized.append(name)
            continue
        for cat in cats:
            if cat in CATEGORIES:
                grid[label][cat] = grid[label].get(cat, 0) + 1
                category_totals[cat] += 1
            else:
                # Unknown category is coverage debt too — surface via uncategorized
                # style callout rather than inventing a column.
                uncategorized.append(f"{name} (category={cat!r})")

    empty_cells: List[Tuple[str, str]] = []
    for label in list(COUNTIES) + [METRO_WIDE]:
        for cat in CATEGORIES:
            if grid[label][cat] == 0:
                empty_cells.append((label, cat))

    return CoverageResult(
        verified=True,
        source_count=len(sources),
        grid=grid,
        county_totals=county_totals,
        category_totals=category_totals,
        uncategorized=uncategorized,
        unknown_county=unknown_county,
        empty_cells=empty_cells,
    )


def from_json(path: Path) -> CoverageResult:
    path = Path(path)
    if not path.exists():
        return CoverageResult(False, 0, {}, {}, {}, reason=f"catalog file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return CoverageResult(False, 0, {}, {}, {}, reason=f"invalid JSON in {path}: {exc}")
    if not isinstance(data, list):
        return CoverageResult(False, 0, {}, {}, {},
                              reason=f"catalog must be a JSON array, got {type(data).__name__}")
    return compute_coverage(data)


def from_db(dsn: str) -> CoverageResult:
    """Read the live `source` table. Identifiers composed via psycopg2.sql; any
    failure is reported loudly, never swallowed into an empty grid."""
    if not dsn:
        return CoverageResult(
            False, 0, {}, {}, {},
            reason=("ONELIVE_DB_DSN not set. Run this via the Supabase connector:\n"
                    "  select county, coverage_categories, name from source where enabled;"))
    try:
        import psycopg2
        from psycopg2 import sql
    except ImportError:
        return CoverageResult(False, 0, {}, {}, {}, reason="psycopg2 not installed")
    try:
        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL(
                    "select {name}, {county}, {cats} from {tbl} where {enabled}"
                ).format(
                    name=sql.Identifier("name"),
                    county=sql.Identifier("county"),
                    cats=sql.Identifier("coverage_categories"),
                    tbl=sql.Identifier("source"),
                    enabled=sql.Identifier("enabled"),
                ))
                rows = cur.fetchall()
    except Exception as exc:  # noqa: BLE001 — reported loudly, not swallowed
        return CoverageResult(False, 0, {}, {}, {}, reason=f"db query failed: {exc}")
    sources = [{"name": r[0], "county": r[1], "coverage_categories": r[2] or []}
               for r in rows]
    return compute_coverage(sources)


def format_report(res: CoverageResult) -> str:
    if not res.verified:
        return f"coverage report UNVERIFIED: {res.reason}"

    lines: List[str] = []
    lines.append("=== OneLive Source Coverage (county x category) ===")
    lines.append(f"total sources: {res.source_count}")
    lines.append("")

    labels = list(COUNTIES) + [METRO_WIDE]
    # extra unknown-county labels, if any, appended so nothing is hidden
    for extra in res.grid:
        if extra not in labels:
            labels.append(extra)

    col_w = 9
    header = "county".ljust(14) + "".join(c[:col_w].rjust(col_w + 1) for c in CATEGORIES) + "   total"
    lines.append(header)
    lines.append("-" * len(header))
    for label in labels:
        row_cells = "".join(str(res.grid.get(label, {}).get(cat, 0)).rjust(col_w + 1)
                            for cat in CATEGORIES)
        total = res.county_totals.get(label, 0)
        lines.append(label.ljust(14) + row_cells + str(total).rjust(8))
    lines.append("-" * len(header))
    total_row = "".join(str(res.category_totals.get(cat, 0)).rjust(col_w + 1) for cat in CATEGORIES)
    lines.append("TOTAL".ljust(14) + total_row + str(res.source_count).rjust(8))
    lines.append("")

    # Coverage debt — the whole point of the report.
    lines.append(f"empty cells (county x category with ZERO sources): {len(res.empty_cells)}")
    if res.empty_cells:
        preview = ", ".join(f"{c}/{cat}" for c, cat in res.empty_cells[:12])
        more = "" if len(res.empty_cells) <= 12 else f" (+{len(res.empty_cells) - 12} more)"
        lines.append(f"  {preview}{more}")
    if res.uncategorized:
        lines.append(f"uncategorized / unknown-category sources (debt): {len(res.uncategorized)}")
        lines.append("  " + ", ".join(res.uncategorized[:10])
                     + ("" if len(res.uncategorized) <= 10 else f" (+{len(res.uncategorized) - 10} more)"))
    if res.unknown_county:
        lines.append(f"OUT-OF-DOMAIN county values (should be impossible post-0010): {len(res.unknown_county)}")
        lines.append("  " + ", ".join(res.unknown_county[:10]))
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="OneLive source coverage report")
    ap.add_argument("--json", help="Compute coverage from a catalog JSON file (hermetic)")
    ap.add_argument("--dsn", default=DEFAULT_DSN, help="Postgres DSN (default: ONELIVE_DB_DSN)")
    args = ap.parse_args(argv)

    if args.json:
        res = from_json(Path(args.json))
    else:
        res = from_db(args.dsn)

    print(format_report(res))
    return 0 if res.verified else 2


if __name__ == "__main__":
    sys.exit(main())
