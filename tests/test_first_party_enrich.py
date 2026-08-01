"""Unit tests for the first-party structured-data extractor
(worker/enrich/first_party.py). NO network — inline HTML fixtures prove the parse
invariants: JSON-LD + sameAs collection, own-domain og:image guard, feed/oEmbed/
WebSub autodiscovery, site-hosted embed detection, outbound-link classification,
relative-URL resolution, and non-fabrication (malformed/absent → skipped, never
invented).
"""
from worker.enrich.first_party import (
    classify_link,
    extract_first_party,
)

_PAGE = "https://mohawkaustin.com/shows/velvet-casket"

_HTML = """
<html><head>
  <meta property="og:image" content="/img/poster.jpg">
  <meta property="og:title" content="Velvet Casket">
  <link rel="alternate" type="application/rss+xml" href="/feed">
  <link rel="alternate" type="application/json+oembed" href="https://mohawkaustin.com/oembed?u=x">
  <link rel="hub" href="https://pubsubhubbub.appspot.com/">
  <link rel="me" href="https://www.youtube.com/@velvetcasket">
  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"MusicGroup","name":"Velvet Casket",
   "sameAs":["https://open.spotify.com/artist/abc","https://instagram.com/velvetcasket"]}
  </script>
</head><body>
  <iframe src="https://open.spotify.com/embed/artist/abc"></iframe>
  <iframe src="https://www.youtube-nocookie.com/embed/xyz"></iframe>
  <iframe src="https://example-ads.com/banner"></iframe>
  <a href="/tickets">Tickets</a>
  <a href="https://dice.fm/event/velvet">Dice</a>
  <a href="https://linktr.ee/velvetcasket">All links</a>
</body></html>
"""


def test_extracts_jsonld_and_sameas():
    fp = extract_first_party(_HTML, _PAGE)
    assert len(fp.jsonld) == 1
    assert fp.jsonld[0]["name"] == "Velvet Casket"
    # sameAs from JSON-LD (list) + the rel="me" link, deduped.
    assert "https://open.spotify.com/artist/abc" in fp.same_as
    assert "https://instagram.com/velvetcasket" in fp.same_as
    assert "https://www.youtube.com/@velvetcasket" in fp.same_as


def test_og_image_own_domain_kept_and_resolved():
    fp = extract_first_party(_HTML, _PAGE)
    # Relative og:image resolved against the page URL; same registrable domain → kept.
    assert fp.og_image == "https://mohawkaustin.com/img/poster.jpg"


def test_og_image_cross_domain_dropped():
    html = '<meta property="og:image" content="https://cdn.thirdparty.net/x.jpg">'
    fp = extract_first_party(html, _PAGE)
    assert fp.og_image is None  # not the entity's own domain → not returned


def test_feeds_oembed_and_websub():
    fp = extract_first_party(_HTML, _PAGE)
    assert fp.feeds == ["https://mohawkaustin.com/feed"]
    assert fp.oembed == ["https://mohawkaustin.com/oembed?u=x"]
    assert fp.websub_hubs == ["https://pubsubhubbub.appspot.com/"]


def test_site_hosted_embeds_detected_thirdparty_ignored():
    fp = extract_first_party(_HTML, _PAGE)
    providers = {(e.provider, e.url) for e in fp.hosted_embeds}
    assert ("spotify", "https://open.spotify.com/embed/artist/abc") in providers
    assert ("youtube", "https://www.youtube-nocookie.com/embed/xyz") in providers
    # A non-embed iframe (ad banner) is not treated as media.
    assert all("example-ads.com" not in e.url for e in fp.hosted_embeds)


def test_outbound_links_are_external_only():
    fp = extract_first_party(_HTML, _PAGE)
    # /tickets is same-site → NOT outbound; dice + linktree are external.
    assert "https://dice.fm/event/velvet" in fp.outbound_links
    assert "https://linktr.ee/velvetcasket" in fp.outbound_links
    assert all("mohawkaustin.com" not in u for u in fp.outbound_links)


def test_classify_link_pathway_kinds():
    assert classify_link("https://linktr.ee/x") == "link_hub"
    assert classify_link("https://velvetcasket.substack.com") == "newsletter"
    assert classify_link("https://open.spotify.com/artist/abc") == "streaming"
    assert classify_link("https://dice.fm/event/x") == "ticketing"
    assert classify_link("https://instagram.com/x") == "social"
    assert classify_link("https://velvetcasket.com/shows") == "own_site"
    assert classify_link("javascript:alert(1)") == "other"


def test_malformed_jsonld_is_skipped_not_crashed():
    html = '<script type="application/ld+json">{not valid json,,,</script>'
    fp = extract_first_party(html, _PAGE)
    assert fp.jsonld == []  # skipped, never guessed


def test_non_http_links_never_escape():
    html = '<a href="javascript:alert(1)">x</a><a href="data:text/html,x">y</a>'
    fp = extract_first_party(html, _PAGE)
    assert fp.outbound_links == []


def test_absent_signals_are_empty_never_fabricated():
    fp = extract_first_party("<html><body><p>nothing here</p></body></html>", _PAGE)
    assert fp.jsonld == [] and fp.same_as == [] and fp.og_image is None
    assert fp.feeds == [] and fp.hosted_embeds == [] and fp.outbound_links == []


def test_jsonld_sameas_string_form():
    html = ('<script type="application/ld+json">'
            '{"@type":"Person","name":"A Speaker","sameAs":"https://youtube.com/@speaker"}'
            '</script>')
    fp = extract_first_party(html, _PAGE)
    assert fp.same_as == ["https://youtube.com/@speaker"]
