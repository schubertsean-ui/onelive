"""Pure-function tests for the source scanner v1 (tools/scan_new_sources.py).

No network: the domain normalization, catalog diff, and platform filter decide
WHAT counts as a new source candidate — pinned here.
"""
from tools.scan_new_sources import catalog_domains, is_platform, norm_domain


def test_norm_domain_strips_www_and_lowercases():
    assert norm_domain("https://WWW.TheSaxonPub.com/shows") == "thesaxonpub.com"
    assert norm_domain("http://mohawkaustin.com/") == "mohawkaustin.com"
    assert norm_domain("not a url") is None


def test_catalog_domains_reads_base_urls():
    cat = [{"base_url": "https://www.mohawkaustin.com/"},
           {"base_url": None}, {"name": "no url"}]
    assert catalog_domains(cat) == {"mohawkaustin.com"}


def test_platform_domains_are_never_candidates():
    assert is_platform("facebook.com")
    assert is_platform("m.facebook.com")
    assert is_platform("linktr.ee")
    # A venue named like a platform is NOT filtered.
    assert not is_platform("facebookbar.com")
    assert not is_platform("thesaxonpub.com")


def test_query_pack_covers_every_canonical_domain():
    # Sentinel (founder 2026-08-05, "it's at least 23 … where are you getting
    # all this?"): the v1 pack was an ad-hoc 20-phrase list with whole
    # canonical domains missing. The pack is now DERIVED from the canonical
    # taxonomy, and this test makes a new canonical domain FAIL the suite
    # until the scanner covers it — under-coverage cannot recur silently.
    from tools.scan_new_sources import DOMAIN_QUERY_PACK
    from worker.importers.domain_map import DOMAINS

    assert set(DOMAIN_QUERY_PACK) == set(DOMAINS)
    assert all(len(v) >= 2 for v in DOMAIN_QUERY_PACK.values()), \
        "every domain needs at least two plain search phrases"


def test_full_capcog_sweep_composition():
    # Launch directive (founder, verbatim): "all the data at launch: full
    # CAPCOG sweep". The sweep must be cities x phrases, Austin-first but
    # region-wide, and its size must stay within one dispatch's declared
    # bound so the launch run needs no silent truncation.
    from tools.scan_new_sources import CAPCOG_CITIES, QUERY_PACK

    assert CAPCOG_CITIES[0] == "Austin"
    assert len(CAPCOG_CITIES) >= 20  # the region, not the city
    sweep = len(CAPCOG_CITIES) * len(QUERY_PACK)
    assert 800 <= sweep <= 1000, sweep


def test_festival_windows_file_parses_and_is_dated():
    import json

    data = json.load(open("sources/festival_windows.json"))
    for w in data["windows"]:
        assert w["starts"] <= w["ends"]
        for key in ("slug", "name", "geo", "keyword_pack"):
            assert w.get(key)
