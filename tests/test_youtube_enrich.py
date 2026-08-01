"""Tests for the YouTube resolver (worker/enrich/youtube.py).

Covers the trust-critical behaviors: authoritative-only resolution (channel from
sameAs, never name search), the cheap 3-call path, public+embeddable selection,
provenance, and honest-gap-by-construction. No network — a fake Fetcher records
the endpoints hit and returns canned API payloads, so the quota discipline
(channels → playlistItems → videos, never `search`) is itself asserted.
"""
from __future__ import annotations

import pytest

from worker.enrich import youtube as yt


# --- pure: parse_channel_ref --------------------------------------------------

@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.youtube.com/channel/UCabc123", ("id", "UCabc123")),
        ("https://youtube.com/@thehandle", ("handle", "@thehandle")),
        ("https://www.youtube.com/user/LegacyName", ("username", "LegacyName")),
        ("https://m.youtube.com/channel/UCxyz", ("id", "UCxyz")),
    ],
)
def test_parse_channel_ref_forms(url, expected):
    assert yt.parse_channel_ref(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=abc",          # a video, not a channel
        "https://www.youtube.com/c/CustomName",         # custom URL — no cheap API param
        "https://open.spotify.com/artist/abc",          # not youtube
        "javascript:alert(1)",                          # non-http
        "https://youtube.com/",                         # no channel segment
        "https://www.youtube.com/channel/XXnotuc",      # not a UC… id
    ],
)
def test_parse_channel_ref_rejects(url):
    assert yt.parse_channel_ref(url) is None


def test_channel_ref_prefers_canonical_id():
    # A handle appears first, a canonical id later — the id must win (needs no
    # extra resolution and can't be reassigned).
    same_as = [
        "https://instagram.com/band",
        "https://youtube.com/@band",
        "https://www.youtube.com/channel/UCcanon",
    ]
    kind, value, src = yt.channel_ref_from_sameas(same_as)
    assert (kind, value) == ("id", "UCcanon")
    assert src == "https://www.youtube.com/channel/UCcanon"


def test_channel_ref_none_when_no_youtube():
    assert yt.channel_ref_from_sameas(["https://instagram.com/x", "https://x.com/y"]) is None


# --- pure: pick_embeddable ----------------------------------------------------

def _vid(id_, privacy="public", embeddable=True, title="T"):
    return {"id": id_, "status": {"privacyStatus": privacy, "embeddable": embeddable},
            "snippet": {"title": title}}


def test_pick_embeddable_skips_private_and_nonembeddable():
    items = [
        _vid("a", privacy="private"),
        _vid("b", embeddable=False),
        _vid("c"),                      # first public + embeddable
        _vid("d"),
    ]
    assert yt.pick_embeddable(items)["id"] == "c"


def test_pick_embeddable_none_when_all_blocked():
    items = [_vid("a", privacy="unlisted"), _vid("b", embeddable=False)]
    assert yt.pick_embeddable(items) is None


# --- orchestration with a fake Fetcher ----------------------------------------

class FakeAPI:
    """Records endpoints hit; returns canned payloads keyed by endpoint."""
    def __init__(self, responses):
        self.responses = responses
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, endpoint, params):
        self.calls.append((endpoint, dict(params)))
        return self.responses.get(endpoint, {})


_HAPPY = {
    "channels": {"items": [{"id": "UCcanon", "contentDetails": {"relatedPlaylists": {"uploads": "UUcanon"}}}]},
    "playlistItems": {"items": [
        {"contentDetails": {"videoId": "vid1"}},
        {"contentDetails": {"videoId": "vid2"}},
    ]},
    "videos": {"items": [
        {"id": "vid1", "status": {"privacyStatus": "private", "embeddable": True}, "snippet": {"title": "hidden"}},
        {"id": "vid2", "status": {"privacyStatus": "public", "embeddable": True}, "snippet": {"title": "The Set"}},
    ]},
}


def test_resolve_happy_path_authoritative():
    api = FakeAPI(_HAPPY)
    out = yt.resolve_channel_video(["https://www.youtube.com/channel/UCcanon"], api)
    assert out is not None
    assert out.video_id == "vid2"                          # skipped the private vid1
    assert out.embed_url == "https://www.youtube.com/embed/vid2"
    assert out.watch_url == "https://www.youtube.com/watch?v=vid2"
    assert out.title == "The Set"
    assert out.channel_id == "UCcanon"
    assert out.resolved_via == yt.RESOLVED_VIA_CHANNEL_ID
    assert out.confidence == yt.CONFIDENCE_AUTHORITATIVE
    assert out.authoritative_link == "https://www.youtube.com/channel/UCcanon"
    prov = out.provenance()
    assert prov["resolved_via"] == yt.RESOLVED_VIA_CHANNEL_ID
    assert prov["video_id"] == "vid2"


def test_resolve_never_calls_search_endpoint():
    # Quota discipline is a trust property here: search.list is 100 units and,
    # worse, would be a name guess. Assert it is NEVER hit.
    api = FakeAPI(_HAPPY)
    yt.resolve_channel_video(["https://www.youtube.com/channel/UCcanon"], api)
    endpoints = [c[0] for c in api.calls]
    assert endpoints == ["channels", "playlistItems", "videos"]
    assert "search" not in endpoints


def test_resolve_handle_uses_forHandle_param():
    api = FakeAPI(_HAPPY)
    out = yt.resolve_channel_video(["https://youtube.com/@band"], api)
    assert out.resolved_via == yt.RESOLVED_VIA_HANDLE
    # the channels call carried forHandle, not id/search
    ch_params = next(p for e, p in api.calls if e == "channels")
    assert ch_params.get("forHandle") == "@band"


def test_resolve_honest_gap_no_channel():
    api = FakeAPI(_HAPPY)
    assert yt.resolve_channel_video(["https://instagram.com/x"], api) is None
    assert api.calls == []                                 # nothing hit — no channel to resolve


def test_resolve_honest_gap_no_embeddable_video():
    responses = dict(_HAPPY)
    responses["videos"] = {"items": [
        {"id": "v", "status": {"privacyStatus": "private", "embeddable": True}, "snippet": {"title": "x"}},
    ]}
    api = FakeAPI(responses)
    assert yt.resolve_channel_video(["https://www.youtube.com/channel/UCcanon"], api) is None


def test_resolve_honest_gap_channel_unresolved():
    api = FakeAPI({"channels": {"items": []}})
    assert yt.resolve_channel_video(["https://www.youtube.com/channel/UCcanon"], api) is None


def test_resolve_never_raises_on_fetcher_error():
    def boom(endpoint, params):
        raise RuntimeError("network down")
    # Degrades to None (honest gap), never crashes the enrichment pass.
    assert yt.resolve_channel_video(["https://www.youtube.com/channel/UCcanon"], boom) is None


# --- env gating ---------------------------------------------------------------

def test_client_from_env_disabled_without_key():
    assert yt.client_from_env({}) is None
    assert yt.client_from_env({"YOUTUBE_API_KEY": "   "}) is None


def test_client_from_env_returns_fetcher_with_key():
    f = yt.client_from_env({"YOUTUBE_API_KEY": "abc"})
    assert callable(f)
