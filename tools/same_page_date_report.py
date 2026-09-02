#!/usr/bin/env python3
"""R-030 measurement: how many dateless listings a SAME-PAGE date can date.

Run 33579093995 stored 92 of its 198 candidates with `start_time = NULL`,
every one refused `no-full-date-evidence`. This script measures what
worker/datetime_normalize.py's same-page resolution does about that, and
prints the table as markdown.

The 92 rows themselves are NOT in this sandbox (no DSN, and the fetched
page text was never persisted), so nothing here claims to re-run them.
What IS measured, on real inputs:

  Table 1 — every class-B fixture page in tests/fixtures/class_b, split
    into listing blocks by the PIPELINE's own segmenter (worker/segment.py)
    and resolved with the pipeline's own resolver. The simulated claim is
    the bare clock in each block, which is exactly the claim shape the 92
    carry in the run log.
  Table 2 — the 92's own refused strings, quoted from the run, against
    each page shape a venue calendar actually uses.
  Table 3 — the 92 by source, with the resolvable/NULL split marked
    UNVERIFIED and the reason it cannot be measured here.

Usage: python tools/same_page_date_report.py [--markdown]
"""
from __future__ import annotations

import pathlib
import re
import sys
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from worker.same_page_dates import resolve_same_page_datetime  # noqa: E402
from worker.segment import segment_events  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "tests/fixtures/class_b"

# The page fetch time. Class-B fixtures advertise September 2026 dates, so
# the anchor is the run's own date; weekday pinning is meaningless without one.
AS_OF = date(2026, 9, 2)

# Verbatim from run 33579093995's log, via
# docs/evidence/2026-09-02_run-33579093995-wave.md and the candidate
# forensics arc — the raw values whose claims were refused.
WAVE_CLAIMS = ["9:00PM", "6:00PM", "7:30 PM", "10 am", "10 pm", "19:00:00"]

# Per-source refusal counts, verbatim from the same forensics table.
WAVE_BY_SOURCE = [
    ("Blanton Museum of Art", 42),
    ("Elephant Room", 19),
    ("Kingdom Nightclub", 13),
    ("Emo's Austin", 10),
    ("Stubb's Austin", 5),
    ("The Contemporary Austin", 3),
]

PAGE_SHAPES = [
    ("JSON-LD startDate",
     '<script type="application/ld+json">'
     '{{"@type":"Event","startDate":"2026-09-04T{h}:00"}}</script>'
     "<li>{claim} — The Deer</li>"),
    ("<time datetime>",
     '<li><time datetime="2026-09-04T{h}:00">{claim}</time> The Deer</li>'),
    ("ICS DTSTART",
     "BEGIN:VEVENT\nDTSTART;TZID=America/Chicago:20260904T{h}0000\n"
     "SUMMARY:The Deer — {claim}\nEND:VEVENT"),
    ("visible date + year",
     "<li>September 4, 2026 — {claim} The Deer</li>"),
    ("visible weekday + month/day (no year)",
     "<li>Fri Sep 4 &bull; {claim} The Deer</li>"),
    ("time only — no date anywhere", "<li>{claim} The Deer</li>"),
]

_CLOCK = re.compile(
    r"\b\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\b|\b(?:[01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d)?\b",
    re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")


def _first_clock(block: str):
    """The bare clock a listing block states — the claim shape the 92 carry."""
    hits = _CLOCK.findall(_TAGS.sub(" ", block))
    return hits[0].strip() if hits else None


def table_1():
    rows = []
    totals = [0, 0]
    reasons = {}
    for path in sorted(FIXTURES.glob("*.html")):
        page = path.read_text(errors="replace")
        blocks = segment_events(page)
        listings = resolved = 0
        kinds = set()
        for block in blocks:
            claim = _first_clock(block)
            if claim is None:
                continue
            listings += 1
            iso, refusal, evidence = resolve_same_page_datetime(
                claim, page_text=page, block_text=block, as_of=AS_OF)
            if iso is not None:
                resolved += 1
                kinds.add(evidence["kind"])
            else:
                reasons[refusal["reason"]] = reasons.get(
                    refusal["reason"], 0) + 1
        if listings:
            rows.append((path.name, listings, resolved, listings - resolved,
                         ", ".join(sorted(kinds)) or "—"))
            totals[0] += listings
            totals[1] += resolved
    return rows, totals, reasons


def table_2():
    rows = []
    for shape_name, template in PAGE_SHAPES:
        cells = []
        for claim in WAVE_CLAIMS:
            # The page's own clock is irrelevant: only its DATE is read,
            # and the stored time always comes from the claim itself.
            page = template.format(claim=claim, h="20")
            iso, _refusal, _evidence = resolve_same_page_datetime(
                claim, page_text=page, as_of=AS_OF)
            cells.append("dated" if iso else "NULL")
        rows.append((shape_name, cells))
    return rows


def main() -> int:
    out = []
    rows, totals, reasons = table_1()
    out.append("### Table 1 — real fixture pages, pipeline segmenter, "
               "pipeline resolver (MEASURED)\n")
    out.append("| fixture page | listing blocks with a clock | dated by "
               "same-page evidence | still NULL | carrier used |")
    out.append("|---|---:|---:|---:|---|")
    for name, listings, resolved, still, kinds in rows:
        out.append(f"| `{name}` | {listings} | {resolved} | "
                   f"{listings - resolved} | {kinds} |")
    pct = (100.0 * totals[1] / totals[0]) if totals[0] else 0.0
    out.append(f"| **total** | **{totals[0]}** | **{totals[1]}** | "
               f"**{totals[0] - totals[1]}** | {pct:.0f}% dated |")
    out.append("\nWhy the rest stay NULL — every refusal, by reason:\n")
    out.append("| reason | blocks |")
    out.append("|---|---:|")
    for reason, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
        out.append(f"| `{reason}` | {count} |")
    out.append(
        "\nTwo things this table shows that a percentage would hide. First, "
        "these fixtures are SYNTHETIC and two of the four listings on each "
        "page carry a weekday that contradicts their own `<time datetime>` "
        "(they say \"Thu Sep 11\" and \"Fri Sep 19\"; in 2026 those dates "
        "are a Friday and a Saturday). The resolver refuses them, which is "
        "the rule working: a page that disagrees with itself does not get a "
        "stored date. Second, `worker/segment.py` STRIPS TAGS on the "
        "anchor-split path, so the listing block handed to extraction no "
        "longer contains the `<time datetime>` or JSON-LD the page "
        "published. That is why the resolver takes the page text as well as "
        "the block: block first for \"nearby\", page as the carrier of the "
        "machine-readable date the segmenter dropped.")

    out.append("\n### Table 2 — the 92's own refused strings × page shape "
               "(MEASURED)\n")
    out.append("| page states the date as… | " + " | ".join(
        f"`{c}`" for c in WAVE_CLAIMS) + " |")
    out.append("|---" * (len(WAVE_CLAIMS) + 1) + "|")
    for shape_name, cells in table_2():
        out.append(f"| {shape_name} | " + " | ".join(cells) + " |")

    out.append("\n### Table 3 — the 92 by source (UNVERIFIED split)\n")
    out.append("| source | candidates with `start_time` refused | resolvable "
               "on same-page evidence | still NULL |")
    out.append("|---|---:|---|---|")
    for name, count in WAVE_BY_SOURCE:
        out.append(f"| {name} | {count} | UNVERIFIED | UNVERIFIED |")
    out.append(f"| **total** | **{sum(c for _, c in WAVE_BY_SOURCE)}** | "
               "UNVERIFIED | UNVERIFIED |")
    out.append("\nThe split is UNVERIFIED for one reason, stated plainly: "
               "deciding whether a given row resolves needs the text of the "
               "page it came from, and this sandbox has neither the database "
               "(no `ONELIVE_DB_DSN`) nor the fetched page text (never "
               "persisted — `raw_text` lives in the candidate row). Table 2 "
               "is what CAN be said about them without guessing: every one "
               "of the 92 carries a bare clock, so each resolves if and only "
               "if its own page states a date in one of the four carriers, "
               "and stays NULL otherwise.")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
