"""Tests for the deployed-site verifier (tools/verify_deployed_site.py).

NO network: verify_page takes TEXT, so the whole judgment is testable here.

Per the test-codifies-the-bad-contract class (docs/memory/RED_CLASSES.md), every
bad-input test below asserts the REFUSAL, and uses the input that would actually
EVADE the check — a 200 with a loading skeleton, a page whose only JSON-LD is
non-event, an event card with no start time — not a convenient variant.
"""
import pytest

from tools.verify_deployed_site import (
    SiteVerificationError,
    extract_events,
    verify_page,
)

_GOOD = """<!doctype html><html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
 {"@type":"MusicEvent","name":"Spoon at the Mohawk","startDate":"2026-07-26T01:00:00Z"},
 {"@type":"TheaterEvent","name":"Late Night Improv","startDate":"2026-07-26T03:00:00Z"}
]}
</script></head><body>feed</body></html>"""


def test_a_real_feed_page_passes():
    r = verify_page(_GOOD, url="https://x/tonight")
    assert r["events"] == 2
    assert "Spoon at the Mohawk" in r["sample_titles"]


def test_a_200_with_NO_events_is_a_FAILURE_not_a_pass():
    """The case this tool exists for. A successful deploy that renders an empty
    feed answers 200 and looks healthy to every other check — reporting it as
    fine is the failure-reads-as-empty class applied to a web page."""
    skeleton = "<!doctype html><html><body><div class='feed' aria-busy='true'></div></body></html>"
    with pytest.raises(SiteVerificationError) as exc:
        verify_page(skeleton, url="https://x/tonight")
    assert "0 event(s)" in str(exc.value)


def test_non_event_jsonld_does_not_count_as_events():
    """An Organization/WebSite block is what almost every site ships. Counting it
    would make the check pass on a page with no events at all."""
    page = """<html><head><script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Organization","name":"OneLive"}
    </script></head><body></body></html>"""
    assert extract_events(page) == []
    with pytest.raises(SiteVerificationError):
        verify_page(page, url="https://x/tonight")


def test_an_event_missing_a_start_time_is_refused():
    """It renders as an empty card, which is worse than an absent one."""
    page = """<html><head><script type="application/ld+json">
    {"@type":"Event","name":"Mystery Show"}
    </script></head><body></body></html>"""
    with pytest.raises(SiteVerificationError) as exc:
        verify_page(page, url="https://x/tonight")
    assert "missing a name or startDate" in str(exc.value)


def test_an_event_missing_a_title_is_refused():
    page = """<html><head><script type="application/ld+json">
    {"@type":"Event","name":"   ","startDate":"2026-07-26T01:00:00Z"}
    </script></head><body></body></html>"""
    with pytest.raises(SiteVerificationError):
        verify_page(page, url="https://x/tonight")


def test_an_empty_body_is_refused():
    with pytest.raises(SiteVerificationError) as exc:
        verify_page("", url="https://x/tonight")
    assert "empty response" in str(exc.value)


def test_one_malformed_block_does_not_lose_the_good_ones():
    page = ("<html><head>"
            "<script type=\"application/ld+json\">{not json</script>"
            "<script type=\"application/ld+json\">"
            "{\"@type\":\"Event\",\"name\":\"Still Here\","
            "\"startDate\":\"2026-07-26T01:00:00Z\"}</script>"
            "</head><body></body></html>")
    assert verify_page(page, url="https://x/tonight")["events"] == 1


def test_min_events_threshold_is_enforced():
    """The threshold is a real gate: a one-event page is not a feed if we asked
    for more."""
    with pytest.raises(SiteVerificationError):
        verify_page(_GOOD, url="https://x/tonight", min_events=5)


def test_cli_refuses_a_min_events_that_cannot_fail():
    """A check that cannot fail proves nothing (repo bar §9.6)."""
    from tools.verify_deployed_site import main
    assert main(["https://x/tonight", "--min-events", "0"]) == 2


# ---- config-driven targets (founder: "make it all config-driven") -----------

def test_the_real_config_loads_and_every_target_is_valid():
    from tools.verify_deployed_site import load_targets
    targets = load_targets()
    assert targets, "no targets configured"
    assert {t["name"] for t in targets} >= {"production", "preview"}


def test_a_target_with_NO_url_FAILS_rather_than_skipping():
    """'production' ships with url=null until the founder fills it. It must FAIL,
    not skip: a check that quietly skips reads as green and proves nothing."""
    from tools.verify_deployed_site import main
    assert main(["--target", "production"]) == 1


def test_a_malformed_config_fails_loud(tmp_path, monkeypatch):
    import json
    import tools.verify_deployed_site as v
    bad = tmp_path / "site_targets.json"
    bad.write_text(json.dumps({"targets": [{"name": "x", "min_events": 0}]}))
    with pytest.raises(v.SiteVerificationError) as exc:
        v.load_targets(bad)
    assert "min_events >= 1" in str(exc.value)


def test_an_empty_target_list_fails_loud(tmp_path):
    import json
    import tools.verify_deployed_site as v
    bad = tmp_path / "site_targets.json"
    bad.write_text(json.dumps({"targets": []}))
    with pytest.raises(v.SiteVerificationError):
        v.load_targets(bad)


def test_cli_requires_exactly_one_of_url_or_target():
    from tools.verify_deployed_site import main
    assert main([]) == 2
    assert main(["https://x/tonight", "--target", "preview"]) == 2
