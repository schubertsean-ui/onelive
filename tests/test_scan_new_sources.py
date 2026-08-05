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
