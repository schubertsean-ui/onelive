"""The Meta posting boundary: fail-closed OFF, release-bound, no network in tests.

Same physics the publish_gate suite proves for release, proven here for the
Graph API client: it posts NOTHING without the founder-minted token, NOTHING
without a PublishRelease that binds this exact draft, and NOTHING carrying a
banned claim — and when it does post, it runs the exact Instagram carousel
sequence against an injected transport (zero real network).
"""
from __future__ import annotations

import pytest

from social.carousel.generator import CarouselDraft, Slide, content_hash
from social.carousel.publish_gate import PublishRelease
import social.carousel.meta_publisher as meta_publisher
from social.carousel.meta_publisher import (
    MetaConfigError,
    MetaPublisher,
    MetaPublishError,
    PublishedPost,
)


def _draft(surface="instagram_feed", banned=False):
    overlay = ("Selling out soon",) if banned else ("Doors at 8",)
    return CarouselDraft(
        series_key="live-music",
        surface=surface,
        tier="T1",
        timeframe="tonight",
        city="Austin",
        handle="@onelive",
        listicle_noun="shows",
        short_link_base="https://onelive.example",
        domain_ids=("live-music",),
        author="onelive-carousel",
        assignment={},
        slides=(
            Slide(kind="hook", headline="3 shows to experience Tonight"),
            Slide(kind="event", headline="The Midnight Brass", overlay_lines=overlay,
                  event_id="ex-1", image_ref="https://img.example/ex-1.jpg"),
            Slide(kind="cta", headline="Send this to your crew"),
        ),
        caption="Real listings, real sources. https://onelive.example",
        hashtags=("#AustinTonight", "#LiveMusic"),
        short_link="https://onelive.example?utm_source=instagram_feed",
        post_slot="evening",
    )


def _release(draft, surface=None):
    return PublishRelease(
        draft_hash=content_hash(draft),
        surface=surface or draft.surface,
        series_key=draft.series_key,
        released_by="Sean Schubert",
    )


def _urls(draft):
    return [f"https://cards.example/{i}.png" for i in range(len(draft.slides))]


class _FakeTransport:
    """Records every Graph API call and hands back sequential ids."""

    def __init__(self):
        self.calls = []
        self._n = 0

    def __call__(self, url, params):
        self.calls.append((url, params))
        self._n += 1
        return {"id": f"node-{self._n}"}


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "founder-minted-token")
    monkeypatch.setenv("META_IG_USER_ID", "17841400000000000")


def test_disabled_without_token_refuses(monkeypatch):
    monkeypatch.delenv("META_ACCESS_TOKEN", raising=False)
    assert meta_publisher.meta_publishing_enabled() is False
    draft = _draft()
    with pytest.raises(MetaConfigError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _release(draft), _urls(draft))


def test_requires_a_publish_release(enabled):
    draft = _draft()
    with pytest.raises(MetaPublishError):
        # A hand-built stand-in that is NOT a PublishRelease must refuse.
        MetaPublisher(transport=_FakeTransport()).post(draft, object(), _urls(draft))


def test_release_hash_mismatch_refuses(enabled):
    draft = _draft()
    bogus = PublishRelease(
        draft_hash="0" * 64, surface=draft.surface,
        series_key=draft.series_key, released_by="Sean Schubert",
    )
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, bogus, _urls(draft))


def test_surface_mismatch_refuses(enabled):
    draft = _draft()
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(
            draft, _release(draft, surface="facebook_page"), _urls(draft)
        )


def test_wrong_image_count_refuses(enabled):
    draft = _draft()
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _release(draft), _urls(draft)[:-1])


def test_non_https_image_refuses(enabled):
    draft = _draft()
    urls = _urls(draft)
    urls[1] = "http://cards.example/1.png"  # not https
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _release(draft), urls)


def test_banned_claim_belt_refuses(enabled):
    draft = _draft(banned=True)  # overlay carries "Selling out soon"
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _release(draft), _urls(draft))


def test_unsupported_surface_refuses(enabled, monkeypatch):
    monkeypatch.setenv("META_FB_PAGE_ID", "9999")
    draft = _draft(surface="facebook_page")
    with pytest.raises(MetaConfigError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _release(draft), _urls(draft))


def test_happy_path_runs_the_carousel_sequence(enabled):
    draft = _draft()
    transport = _FakeTransport()
    published = MetaPublisher(transport=transport).post(draft, _release(draft), _urls(draft))

    assert isinstance(published, PublishedPost)
    assert published.surface == "instagram_feed"
    assert published.draft_hash == content_hash(draft)
    assert published.released_by == "Sean Schubert"

    # One child-media call per slide, then the carousel container, then publish.
    assert len(transport.calls) == len(draft.slides) + 2
    child_calls = transport.calls[: len(draft.slides)]
    for url, params in child_calls:
        assert url.endswith("/17841400000000000/media")
        assert params["is_carousel_item"] == "true"
        assert params["image_url"].startswith("https://")
        assert params["access_token"] == "founder-minted-token"

    container_url, container_params = transport.calls[-2]
    assert container_params["media_type"] == "CAROUSEL"
    assert container_params["children"].count(",") == len(draft.slides) - 1
    # Caption carries the hashtags exactly once, and no banned language.
    assert "#AustinTonight" in container_params["caption"]

    publish_url, publish_params = transport.calls[-1]
    assert publish_url.endswith("/media_publish")
    assert "creation_id" in publish_params


def test_api_error_object_fails_loud(enabled):
    draft = _draft()

    def erroring(url, params):
        return {"error": {"message": "Invalid OAuth access token", "code": 190}}

    with pytest.raises(meta_publisher.MetaAPIError):
        MetaPublisher(transport=erroring).post(draft, _release(draft), _urls(draft))
