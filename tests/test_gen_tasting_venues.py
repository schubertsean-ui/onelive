"""Tasting Trail venue-directory generator — sync + shape tests.

The web section reads a generated data file (web/lib/tasting_venues.generated.ts)
built from the source catalog. These tests keep it honest: it must stay IN SYNC
with the catalog (so it can't silently go stale), and every record must be a
well-formed venue with a real first-party URL and a valid kind.
"""
import importlib.util
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "gen_tasting_venues", ROOT / "tools" / "gen_tasting_venues.py"
)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def test_generated_file_is_in_sync_with_the_catalog():
    """The committed generated file must match a fresh generation — otherwise a
    catalog change (new tasting rooms) silently fails to reach the directory."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "gen_tasting_venues.py"), "--check"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        "web/lib/tasting_venues.generated.ts is stale — run "
        "`python tools/gen_tasting_venues.py`.\n" + result.stderr
    )


def test_every_venue_record_is_well_formed():
    venues = gen.build_venues()
    assert len(venues) >= 20, "expected the catalog's tasting-room venues"
    seen_ids = set()
    for v in venues:
        assert v["kind"] in gen.VALID_KINDS, f"bad kind {v['kind']!r}"
        assert v["url"].startswith("http"), f"non-http url for {v['name']!r}"
        assert v["id"] and v["name"], "id and name are required"
        assert v["id"] not in seen_ids, f"duplicate id {v['id']!r}"
        seen_ids.add(v["id"])


def test_kind_derivation_is_correct_for_known_shapes():
    assert gen.derive_kind("Still Austin Whiskey Co.") == "distillery"
    assert gen.derive_kind("Altdorf Biergarten") == "beer-garden"
    assert gen.derive_kind("Silver Creek Beer Garden & Grille") == "beer-garden"
    assert gen.derive_kind("Altstadt Brewery") == "brewery"
    assert gen.derive_kind("Becker Vineyards") == "winery"
    assert gen.derive_kind("Meanwhile Brewing Co.") == "brewery"
    assert gen.derive_kind("Garrison Brothers Distillery") == "distillery"


def test_name_wins_over_a_co_located_other_kind_in_notes():
    # adversarial-review #96: a winery whose NOTES mention a co-located brewery
    # must stay a winery — the venue's own name is authoritative.
    assert gen.derive_kind(
        "Carter Creek Winery Resort & Spa",
        "Winery; events: live music. Winery + Old 290 Brewery on site.",
    ) == "winery"
    assert gen.derive_kind(
        "Bell Springs Winery",
        "Winery; events: live music. Dripping Springs winery+brewery.",
    ) == "winery"
    # When the name carries no kind keyword, fall back to the notes' OWN leading
    # kind label (never a downstream mention of another kind).
    assert gen.derive_kind("Vinovium", "Winery; events: wine bar & restaurant.") == "winery"
    assert gen.derive_kind("Redbud Cafe", "Restaurant; events: live music.") == "restaurant"


def test_generated_file_has_no_winery_named_venue_mislabeled():
    # Guard the specific regression on the real data: any venue whose name ends
    # in a winery word must be classified winery.
    import re
    for v in gen.build_venues():
        if re.search(r"\b(winery|vineyards?|cellars)\b", v["name"], re.IGNORECASE):
            assert v["kind"] == "winery", f"{v['name']} mislabeled as {v['kind']}"
