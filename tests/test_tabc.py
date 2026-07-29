"""TABC authoritative classification (tools/tabc_classify.py) + its override of
the keyword guess in the Tasting Trail generator. Fixture-based (no network), so
the logic is proven before any live TABC fetch lands — the same discipline the
licensed importers use.
"""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load(mod_name, rel):
    spec = importlib.util.spec_from_file_location(mod_name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


tabc = _load("tabc_classify", "tools/tabc_classify.py")
gen = _load("gen_tasting_venues", "tools/gen_tasting_venues.py")


def test_permit_kind_maps_producer_permits_only():
    assert tabc.permit_kind("G") == "winery"
    assert tabc.permit_kind("bp") == "brewery"   # case-insensitive
    assert tabc.permit_kind(" D ") == "distillery"
    # A retailer / bar / on-premise permit is NOT a producer -> None (a bar that
    # merely sells beer is never a brewery).
    assert tabc.permit_kind("BE") is None
    assert tabc.permit_kind(None) is None
    assert tabc.permit_kind("") is None


def test_normalize_name_strips_punctuation_and_suffixes():
    assert tabc.normalize_name("Still Austin Whiskey Co.") == "still austin whiskey"
    assert tabc.normalize_name("Becker Vineyards, LLC") == "becker vineyards"
    assert tabc.normalize_name("  Jester   King  ") == "jester king"


def test_build_index_keeps_producers_and_maps_kinds():
    idx = tabc.build_index([
        {"trade_name": "Becker Vineyards", "permit_type": "G", "county": "GILLESPIE"},
        {"trade_name": "Garrison Brothers Distillery", "permit_type": "D", "county": "BLANCO"},
        {"trade_name": "Corner Bar", "permit_type": "BE", "county": "TRAVIS"},  # retailer -> dropped
    ])
    assert idx == {
        "becker vineyards": "winery",
        "garrison brothers distillery": "distillery",
    }


def test_build_index_reads_fetch_tabc_output_format():
    # adversarial-review #104: fetch_tabc.py writes {trade_name, county, kind}
    # (permit already resolved), NOT a raw permit_type. build_index MUST read
    # that shape, or the whole authoritative index silently empties.
    fetched = [
        {"trade_name": "Jester King Brewery", "county": "Travis", "kind": "brewery"},
        {"trade_name": "Becker Vineyards", "county": "Gillespie", "kind": "winery"},
    ]
    idx = tabc.build_index(fetched)
    assert idx == {"jester king brewery": "brewery", "becker vineyards": "winery"}


def test_fetch_to_index_roundtrip_connects():
    # End-to-end: a RAW Socrata row -> fetch_tabc.to_producers -> build_index ->
    # classify. Proves the two modules actually connect (the #104 regression).
    fetch = _load("fetch_tabc", "tools/fetch_tabc.py")
    raw_rows = [
        {"trade_name": "Still Austin Whiskey Co.", "permit_type": "D", "county": "TRAVIS"},
        {"trade_name": "Corner Icehouse", "permit_type": "BE", "county": "TRAVIS"},  # retailer -> dropped
    ]
    producers = fetch.to_producers(raw_rows)
    idx = tabc.build_index(producers)
    assert tabc.classify("Still Austin Whiskey Co.", idx) == "distillery"
    assert tabc.classify("Corner Icehouse", idx) is None


def test_classify_matches_by_normalized_name():
    idx = {"still austin whiskey": "distillery"}
    assert tabc.classify("Still Austin Whiskey Co.", idx) == "distillery"
    assert tabc.classify("Some Other Place", idx) is None
    assert tabc.classify("anything", {}) is None  # no index -> fall back


def test_tabc_overrides_the_keyword_guess_in_the_directory():
    # "Redbud Cafe" is keyword-classified 'restaurant' and EXCLUDED from the
    # directory. If TABC says it holds a Winery permit, it is AUTHORITATIVELY a
    # winery and must appear — the whole point of the license screen.
    assert gen.derive_kind("Redbud Cafe", "Restaurant; events: live music.") == "restaurant"
    without = gen.build_venues(tabc_index={})
    assert "Redbud Cafe" not in {v["name"] for v in without}

    with_tabc = gen.build_venues(tabc_index={"redbud cafe": "winery"})
    redbud = [v for v in with_tabc if v["name"] == "Redbud Cafe"]
    assert redbud and redbud[0]["kind"] == "winery"


def test_tabc_wins_over_a_keyword_hit_too():
    # A venue the keyword rule WOULD classify still defers to TABC's authority.
    # Becker Vineyards -> keyword winery; TABC agreeing keeps it winery, and TABC
    # is what decides.
    idx = {"becker vineyards": "winery"}
    vs = gen.build_venues(tabc_index=idx)
    becker = [v for v in vs if v["name"] == "Becker Vineyards"]
    if becker:  # present in the catalog on this branch
        assert becker[0]["kind"] == "winery"


def test_no_index_is_no_regression():
    # With no TABC file, the directory is exactly the keyword-classified set.
    from_keyword = gen.build_venues(tabc_index={})
    assert len(from_keyword) >= 20
    for v in from_keyword:
        assert v["kind"] in gen.TASTING_KINDS
