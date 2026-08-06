#!/usr/bin/env python3
"""Re-derive every factual claim in the handoff from the actual source tree.

A written rule saying "never work from memory" prevents nothing. It is the
`rule-stronger-than-mechanism` defect class this repo already names. This file
is the mechanism: each claim the handoff makes about the codebase is expressed
as CODE THAT RE-DERIVES IT, and the claim is compared against what the tree
actually says.

`lab/assemble_handoff.py` calls this and REFUSES TO WRITE the document if any
claim fails. So a stale or invented fact cannot reach the founder or an
external engineer through that file — not because someone promised to check,
but because the build breaks.

Run standalone: python3 lab/verify_claims.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys


def _read(path: str) -> str:
    return open(path).read()


def _lines(path: str) -> list[str]:
    return _read(path).split("\n")


# ── the claims ───────────────────────────────────────────────────────────────
# Each entry: (claim id, the human-readable claim, a callable returning the
# value AS THE TREE HAS IT, the expected value). A claim with no re-derivation
# is not allowed in the document.

def c_extraction_field_count() -> int:
    """Fields on AIEventExtraction — the complete extraction schema."""
    body = _read("worker/ai_models.py")
    body = body[body.index("class AIEventExtraction"):]
    return len(re.findall(r"^\s{4}(\w+)\s*:", body, re.M))


def c_card_field_count() -> int:
    """Fields on LicensedEvent — the shape both lanes render into."""
    body = _read("web/lib/licensed.ts")
    body = body[body.index("export type LicensedEvent"):]
    body = body[:body.index("\n};")]
    return len(re.findall(r"^\s{2}(\w+)\??\s*:", body, re.M))


def c_gating_start_time_hits() -> int:
    """Occurrences of start_time in the trust gate. The date requirement."""
    return _read("worker/gating.py").count("start_time")


def c_query_pack_size() -> int:
    """Phrases in the ONLY automated source-discovery mechanism."""
    body = _read("tools/scan_new_sources.py")
    body = body[body.index("QUERY_PACK = ["):]
    body = body[:body.index("]")]
    return len(re.findall(r'^\s*"', body, re.M))


def c_promote_dedupe_line() -> str:
    """The duplicate check that only runs when a date exists."""
    return _lines("worker/promote.py")[131].strip()


def c_jsonld_flatten_fn() -> str:
    """The function that flattens structured data into a string."""
    return _lines("worker/segment.py")[251].strip()


def c_jsonld_fields_kept() -> list:
    """Which schema.org fields the flattener reads. Everything else is lost."""
    body = "\n".join(_lines("worker/segment.py")[251:281])
    return sorted(set(re.findall(r'"(\w+)"', body)))


def c_render_trigger() -> str:
    """The signal that decides whether a page gets a browser."""
    body = _read("worker/fetch/render_fetch.py")
    m = re.search(r'return reading\.signals\.get\("(\w+)"\)', body)
    return m.group(1) if m else "NOT FOUND"


def c_feed_date_filter() -> bool:
    """The feed filters start_time by range, so NULLs are excluded."""
    body = _read("web/lib/promoted.ts")
    return 'p.append("start_time", `gte.' in body and 'lte.' in body


def c_range_year_fabrication() -> str:
    """EXECUTABLE: what the normaliser does with a year-less range."""
    sys.path.insert(0, ".")
    from worker.datetime_normalize import normalize_datetime_claim
    value, _ = normalize_datetime_claim("SEPT 04-27")
    return str(value)


def c_qualified_range_refused() -> str:
    """EXECUTABLE: what it does with a fully-qualified range."""
    sys.path.insert(0, ".")
    from worker.datetime_normalize import normalize_datetime_claim
    value, refusal = normalize_datetime_claim("Fri, Sep 4, 2026 - Sun, Sep 27, 2026")
    return "REFUSED:" + refusal["reason"] if refusal else str(value)


def c_full_date_accepted() -> str:
    """EXECUTABLE: a full date IS accepted — the normaliser is not the bug."""
    sys.path.insert(0, ".")
    from worker.datetime_normalize import normalize_datetime_claim
    value, _ = normalize_datetime_claim("Fri, Sep 4, 2026")
    return str(value)


def c_catalog_size() -> int:
    rows = json.load(open("sources/master_sources_catalog_120.json"))
    rows = rows if isinstance(rows, list) else rows.get("sources", rows)
    return len(rows)


CLAIMS = [
    ("C1", "worker/ai_models.py defines 11 extraction fields",
     c_extraction_field_count, 11),
    ("C2", "web/lib/licensed.ts LicensedEvent defines 30 card fields",
     c_card_field_count, 30),
    ("C3", "worker/gating.py contains ZERO occurrences of start_time",
     c_gating_start_time_hits, 0),
    ("C4", "the source-discovery query pack is 20 phrases",
     c_query_pack_size, 20),
    ("C5", "promote.py:132 runs the dedupe check only when start_time exists",
     c_promote_dedupe_line,
     "dups = find_possible_duplicates(venue_id, start_time, cur=cur) if start_time else []"),
    ("C6", "segment.py:252 is the JSON-LD flattening function",
     c_jsonld_flatten_fn, "def _jsonld_event_text(obj: Dict) -> Optional[str]:"),
    ("C7", "the flattener reads only name/startDate/location/address/url — "
     "never offers, description, endDate, performer, image or eventStatus",
     c_jsonld_fields_kept,
     ["address", "addressLocality", "event", "location", "name", "startDate",
      "start_date", "streetAddress", "url"]),
    ("C8", "the render trigger fires only on boilerplate_only",
     c_render_trigger, "boilerplate_only"),
    ("C9", "the feed filters start_time with gte./lte., excluding NULLs",
     c_feed_date_filter, True),
    ("C10", "'SEPT 04-27' normalises to a FABRICATED 2027 date",
     c_range_year_fabrication, "2027-09-04T00:00:00"),
    ("C11", "a fully-qualified date range is refused as unparseable",
     c_qualified_range_refused, "REFUSED:unparseable"),
    ("C12", "a full date IS accepted — the normaliser itself is sound",
     c_full_date_accepted, "2026-09-04T00:00:00"),
    ("C13", "the committed catalog holds 180 sources",
     c_catalog_size, 180),
]


def main() -> int:
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    print(f"verify_claims: re-deriving {len(CLAIMS)} claims from the tree at {head}\n")
    failures = []
    for cid, claim, fn, expected in CLAIMS:
        try:
            actual = fn()
        except Exception as exc:                       # a claim that cannot be
            actual = f"ERROR {type(exc).__name__}: {exc}"   # re-derived is a failure
        ok = actual == expected
        print(f"  [{'PASS' if ok else 'FAIL'}] {cid}  {claim}")
        if not ok:
            print(f"         expected: {expected!r}")
            print(f"         tree says: {actual!r}")
            failures.append(cid)

    print()
    if failures:
        print(f"verify_claims: FAIL — {len(failures)} claim(s) no longer match the "
              f"source: {', '.join(failures)}")
        print("The document must not be published until each is corrected "
              "AGAINST THE TREE, not against memory.")
        return 1
    print(f"verify_claims: OK — all {len(CLAIMS)} claims re-derived and matched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
