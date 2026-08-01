"""Tests for the enrichment orchestration (worker/enrich/enrichment.py) — the
stage that connects first_party + youtube and picks the best verified preview.

No network: page HTML is inline and the YouTube Data API is a fake Fetcher.
Covers the authority order (site-hosted embed > resolved channel > honest gap),
the honest-gap-by-construction paths, and never-raises behavior.
"""
from __future__ import annotations

from worker.enrich import enrichment as en


# A page that publishes a sameAs YouTube channel (drives resolution) and NO
# site-hosted embed.
_HTML_SAMEAS_CHANNEL = """
<html><head>
<script type="application/ld+json">
{"@type":"MusicGroup","name":"The Band",
 "sameAs":["https://www.youtube.com/channel/UCband","https://instagram.com/band"]}
</script>
</head><body></body></html>
"""

# A page that hosts a YouTube embed itself (the entity vouched for it).
_HTML_HOSTED_EMBED = """
<html><body>
<iframe src="https://www.youtube.com/embed/vidHOSTED"></iframe>
</body></html>
"""

# A page with both: a hosted embed AND a sameAs channel — hosted must win.
_HTML_BOTH = """
<html><head>
<script type="application/ld+json">
{"@type":"MusicGroup","sameAs":["https://www.youtube.com/channel/UCband"]}
</script>
</head><body>
<iframe src="https://open.spotify.com/embed/track/abc"></iframe>
</body></html>
"""

_YT_HAPPY = {
    "channels": {"items": [{"id": "UCband", "contentDetails": {"relatedPlaylists": {"uploads": "UUband"}}}]},
    "playlistItems": {"items": [{"contentDetails": {"videoId": "vidRESOLVED"}}]},
    "videos": {"items": [
        {"id": "vidRESOLVED", "status": {"privacyStatus": "public", "embeddable": True},
         "snippet": {"title": "Live set"}},
    ]},
}


def _fake_yt(responses):
    def fetch(endpoint, params):
        return responses.get(endpoint, {})
    return fetch


def test_resolved_channel_video_when_only_sameas():
    out = en.enrich_from_page(_HTML_SAMEAS_CHANNEL, "https://band.example", _fake_yt(_YT_HAPPY))
    assert "https://www.youtube.com/channel/UCband" in out.same_as
    assert out.video is not None and out.video.video_id == "vidRESOLVED"
    bp = out.best_preview()
    assert bp is not None
    assert bp.kind == "video" and bp.source == en.SOURCE_RESOLVED_CHANNEL
    assert bp.url == "https://www.youtube.com/embed/vidRESOLVED"
    assert bp.provenance()["source"] == en.SOURCE_RESOLVED_CHANNEL


def test_hosted_embed_is_surfaced():
    out = en.enrich_from_page(_HTML_HOSTED_EMBED, "https://band.example", None)
    bp = out.best_preview()
    assert bp is not None
    assert bp.kind == "embed" and bp.provider == "youtube"
    assert bp.source == en.SOURCE_HOSTED_EMBED
    assert "vidHOSTED" in bp.url


def test_hosted_embed_wins_over_resolved_channel():
    # The entity published its own embed AND has a sameAs channel — the
    # explicitly-published embed is the stronger vouch and must win.
    out = en.enrich_from_page(_HTML_BOTH, "https://band.example", _fake_yt(_YT_HAPPY))
    bp = out.best_preview()
    assert bp is not None
    assert bp.source == en.SOURCE_HOSTED_EMBED
    assert bp.provider == "spotify"


def test_no_yt_fetch_skips_resolution_but_keeps_first_party():
    # No API key/fetcher: resolution is skipped, but sameAs is still gathered.
    out = en.enrich_from_page(_HTML_SAMEAS_CHANNEL, "https://band.example", None)
    assert out.video is None
    assert "https://www.youtube.com/channel/UCband" in out.same_as
    assert out.best_preview() is None          # honest gap — nothing to render
    assert out.has_signal() is True             # but we did learn its channels


def test_honest_gap_on_empty_page():
    out = en.enrich_from_page("<html><body>nothing</body></html>", "https://x.example",
                              _fake_yt(_YT_HAPPY))
    assert out.best_preview() is None
    assert out.has_signal() is False


def test_never_raises_on_yt_error():
    def boom(endpoint, params):
        raise RuntimeError("api down")
    out = en.enrich_from_page(_HTML_SAMEAS_CHANNEL, "https://band.example", boom)
    # Degrades to first-party-only, never crashes.
    assert out.video is None
    assert out.best_preview() is None
    assert "https://www.youtube.com/channel/UCband" in out.same_as
