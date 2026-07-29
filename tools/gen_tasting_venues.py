#!/usr/bin/env python3
"""Generate web/lib/tasting_venues.generated.ts from the source catalog.

The Tasting Trail section (docs/design/TASTING_TRAIL_SECTION_v1.md) shows
breweries / wineries / distilleries as an ALWAYS-ON venue directory — visible
even when a venue has no scheduled event. Those venues live in the curated,
first-party source catalog (cultural_domain=food-drink, entity_type=venue,
policy-railed). This generator extracts them into a typed, web-bundled data
file so the Next.js section renders the directory WITHOUT a DB migration; a
venue's live events still join from the pipeline when present (never fabricated).

Truth-first: this file carries ONLY venue-identity fields the catalog already
records (name, kind, county, first-party url) — no event claims.

Run:
  python tools/gen_tasting_venues.py           # (re)write the generated file
  python tools/gen_tasting_venues.py --check    # exit 1 if the file is stale

A sync test (tests/test_gen_tasting_venues.py) keeps the generated file from
drifting from the catalog.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Run as a script (`python tools/gen_tasting_venues.py`), so self-insert the repo
# root on sys.path — otherwise `from tools.tabc_classify import ...` fails (tools/
# is not on the path when the file is the entrypoint).
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CATALOG = ROOT / "sources" / "master_sources_catalog_120.json"
OUT = ROOT / "web" / "lib" / "tasting_venues.generated.ts"
# Optional AUTHORITATIVE kind source: TABC licensed-producer index (written by
# tools/fetch_tabc.py where egress reaches data.texas.gov). When present it
# overrides the keyword guess — a licensed winery is a winery no matter its name.
TABC_INDEX = ROOT / "sources" / "tabc_producers.json"

# Valid kinds derive_kind can return — kept in sync with web/lib/venues.ts.
VALID_KINDS = ("winery", "brewery", "distillery", "beer-garden", "restaurant", "tasting-room")

# The kinds the Tasting Trail DIRECTORY admits: genuine tasting venues only
# (breweries / wineries / distilleries / beer gardens / tasting rooms), the
# section's founder-stated scope. A plain restaurant or a dance hall that merely
# has music is NOT a tasting venue — it is excluded from this always-on
# directory (adversarial-review #96: Redbud Cafe / Uptown Blanco Arts &
# Entertainment). Such a venue still appears in the EVENTS feed when it has an
# event — the two surfaces are complementary, and nothing here hides an event.
TASTING_KINDS = frozenset({"winery", "brewery", "distillery", "beer-garden", "tasting-room"})


# Kind → its keyword vocabulary. A combined estate names its kinds in order of
# primary identity ("Westcave Cellars Winery & Brewery" is a winery that also
# brews; "Yegua Creek Brewery & Restaurant" is a brewery with a kitchen), so the
# EARLIEST keyword in the text wins — see _match_kind. "beer garden"/"biergarten"
# is its own kind ahead of the broader "beer"/brewery vocabulary, and the
# whiskey/spirits words carry distillery even when no "distill" appears.
_KIND_KEYWORDS: "list[tuple[str, tuple[str, ...]]]" = [
    ("distillery", ("distill", "whiskey", "whisky", "bourbon", "spirits", "speakeasy")),
    ("beer-garden", ("beer garden", "biergarten")),
    ("brewery", ("brewery", "brewing", "beerworks", "brewpub")),
    ("winery", ("winery", "vineyard", "cellars", "wine")),
    # Tasting rooms proper — taprooms, cideries, meaderies. Positive signals so a
    # genuine tasting room classifies WITHOUT relying on a catch-all default
    # (which would sweep in non-tasting food-drink venues, #96).
    ("tasting-room", ("tasting room", "taproom", "tap room", "cellar door", "cidery", "cider", "meadery", "kombucha")),
    ("restaurant", ("restaurant", "grille", "steakhouse", "saloon", "kitchen", "grill", "cafe")),
]


def _match_kind(text: str) -> "str | None":
    """Classify by the kind whose keyword appears EARLIEST in the string —
    "leading word wins", because a venue's primary identity is the first kind it
    names ('Cellars Winery & Brewery' → winery, 'Brewery & Restaurant' →
    brewery). Ties are impossible (distinct keywords sit at distinct offsets);
    on a tie of START offset the earlier-listed kind in _KIND_KEYWORDS wins, so
    'beer garden' still beats the 'beer'-free brewery set. Returns None on no
    match."""
    t = text.lower()
    best_pos: "int | None" = None
    best_kind: "str | None" = None
    for kind, kws in _KIND_KEYWORDS:
        for kw in kws:
            i = t.find(kw)
            if i != -1 and (best_pos is None or i < best_pos):
                best_pos = i
                best_kind = kind
    return best_kind


def derive_kind(name: str, notes: str = "") -> "str | None":
    """Classify a venue by kind, or None when nothing positively matches. The
    venue's OWN NAME is authoritative — a '<X> Winery' whose notes mention a
    co-located brewery ('Old 290 Brewery on site', 'winery+brewery') is still a
    WINERY, not a brewery (adversarial-review #96: matching name+notes together
    mislabeled Carter Creek and Bell Springs). Only when the name carries no kind
    keyword do we fall back to the notes' OWN leading kind label (we format notes
    as '<Kind>; events: …'), using just the segment before the first ';' so a
    downstream mention of some other kind can't override it.

    Returns None (NOT a 'tasting-room' default) when neither name nor notes carry
    a kind keyword: a food-drink venue with no positive tasting/kind signal — a
    dance hall, an arts venue — must not be ASSUMED a tasting room and swept into
    the directory (#96: Uptown Blanco Arts & Entertainment). build_venues drops
    the Nones."""
    from_name = _match_kind(name)
    if from_name is not None:
        return from_name
    from_notes = _match_kind(notes.split(";", 1)[0])
    if from_notes is not None:
        return from_notes
    return None


def load_tabc_index() -> "dict[str, str]":
    """The authoritative TABC producer index ({normalized_name: kind}), or empty
    when the file has not been fetched yet — in which case classification falls
    back entirely to the keyword guess (no regression)."""
    if not TABC_INDEX.exists():
        return {}
    from tools.tabc_classify import build_index
    return build_index(json.loads(TABC_INDEX.read_text(encoding="utf-8")))


def build_venues(tabc_index: "dict[str, str] | None" = None) -> list[dict]:
    """The TASTING venues from the catalog, mapped to directory records and
    sorted deterministically (county, then name) so the generated file is
    stable across runs. Kind is AUTHORITATIVE from TABC when the venue holds a
    producer permit under its name (a licensed winery is a winery regardless of
    its name), else the keyword guess. Only genuine tasting kinds are admitted
    (TASTING_KINDS); a restaurant or an unclassifiable food-drink venue is
    excluded from this always-on directory — it still reaches users through the
    events feed when it has an event (#96)."""
    from tools.tabc_classify import classify as tabc_classify
    idx = load_tabc_index() if tabc_index is None else tabc_index
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    out = []
    for e in cat:
        if e.get("cultural_domain") != "food-drink" or e.get("entity_type") != "venue":
            continue
        name = e.get("name") or ""
        notes = e.get("notes") or ""
        # TABC (authoritative) first; keyword guess only when TABC has no match.
        kind = tabc_classify(name, idx) or derive_kind(name, notes)
        if kind not in TASTING_KINDS:
            continue  # restaurant, or no positive tasting signal — not this section
        out.append({
            "id": str(e.get("id")),
            "name": name,
            "kind": kind,
            "county": str(e.get("county") or "").lower(),
            "url": e.get("base_url") or "",
        })
    out.sort(key=lambda v: (v["county"], v["name"].lower()))
    return out


def render(venues: list[dict]) -> str:
    lines = [
        "// GENERATED by tools/gen_tasting_venues.py — DO NOT EDIT BY HAND.",
        "// Source: sources/master_sources_catalog_120.json"
        " (cultural_domain=food-drink, entity_type=venue).",
        "// Regenerate: python tools/gen_tasting_venues.py"
        " (a sync test enforces this stays current).",
        'import type { TastingVenue } from "./venues";',
        "",
        "export const TASTING_VENUES: TastingVenue[] = [",
    ]
    for v in venues:
        lines.append(
            "  { "
            f'id: {json.dumps(v["id"])}, '
            f'name: {json.dumps(v["name"], ensure_ascii=False)}, '
            f'kind: {json.dumps(v["kind"])}, '
            f'county: {json.dumps(v["county"])}, '
            f'url: {json.dumps(v["url"])} '
            "},"
        )
    lines.append("];")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate the Tasting Trail venue directory.")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the generated file is out of date (CI/sync guard)")
    args = ap.parse_args(argv)

    venues = build_venues()
    content = render(venues)

    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != content:
            print("tasting_venues.generated.ts is OUT OF DATE — run: "
                  "python tools/gen_tasting_venues.py", file=sys.stderr)
            return 1
        print(f"tasting_venues.generated.ts is in sync ({len(venues)} venues)")
        return 0

    OUT.write_text(content, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} with {len(venues)} tasting venues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
