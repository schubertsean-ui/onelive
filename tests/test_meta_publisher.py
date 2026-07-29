"""The Meta posting boundary: fail-closed OFF, gate-SIGNED-release-bound, no network in tests.

Proven here: it posts NOTHING without the founder-minted token, NOTHING unless
the release's signature verifies under the founder key (a hand-built matching-
fields release is rejected), NOTHING whose images are not hash-bound in the
approved draft, and NOTHING carrying a banned claim — and when it does post, it
runs the exact Instagram carousel sequence against an injected transport.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from social.carousel.example_fixtures import EXAMPLE_EVENTS
from social.carousel.config import CarouselConfig
from social.carousel.generator import CarouselDraft, Slide, build_carousel, content_hash
import social.carousel.publish_gate as publish_gate
from social.carousel.publish_gate import (
    PublishRelease,
    _release_signature,
    approve,
    release_for_publish,
    verify_release,
)
import social.carousel.meta_publisher as meta_publisher
from social.carousel.meta_publisher import (
    MetaConfigError,
    MetaPublisher,
    MetaPublishError,
    PublishedPost,
)

TEST_KEY = "test-founder-approval-key-4f8a2c9d7e1b"  # >=32 bytes, >=8 distinct
REF_NOW = "2026-07-24T12:00:00-05:00"  # the gate clock in these tests


def _draft(surface="instagram_feed", banned=False, missing_image=False, non_https=False):
    overlay = ("Selling out soon",) if banned else ("Doors at 8",)
    event_image = ""
    if not missing_image:
        event_image = "http://cards.example/1.png" if non_https else "https://cards.example/1.png"
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
            Slide(kind="hook", headline="3 shows to experience Tonight",
                  image_ref="https://cards.example/0.png"),
            Slide(kind="event", headline="The Midnight Brass", overlay_lines=overlay,
                  event_id="ex-1", image_ref=event_image),
            Slide(kind="cta", headline="Send this to your crew",
                  image_ref="https://cards.example/2.png"),
        ),
        caption="Real listings, real sources. https://onelive.example",
        hashtags=("#AustinTonight", "#LiveMusic"),
        short_link="https://onelive.example?utm_source=instagram_feed",
        post_slot="evening",
    )


def _signed_release(draft, released_by="Sean Schubert", surface=None, released_at=REF_NOW):
    surface = surface or draft.surface
    dh = content_hash(draft)
    sig = _release_signature(
        dh, surface, draft.series_key, released_by, released_at, TEST_KEY.encode()
    )
    return PublishRelease(
        draft_hash=dh, surface=surface, series_key=draft.series_key,
        released_by=released_by, released_at=released_at, signature=sig,
    )


class _FakeTransport:
    def __init__(self):
        self.calls = []
        self._n = 0

    def __call__(self, url, params, headers):
        self.calls.append((url, params, headers))
        self._n += 1
        return {"id": f"node-{self._n}"}


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "founder-minted-token")
    monkeypatch.setenv("META_IG_USER_ID", "17841400000000000")
    monkeypatch.setenv("ONELIVE_APPROVAL_KEY", TEST_KEY)  # verify_release needs it
    monkeypatch.setattr(publish_gate, "_utcnow", lambda: datetime.fromisoformat(REF_NOW))


def test_disabled_without_token_refuses(monkeypatch):
    monkeypatch.delenv("META_ACCESS_TOKEN", raising=False)
    assert meta_publisher.meta_publishing_enabled() is False
    draft = _draft()
    with pytest.raises(MetaConfigError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(draft))


def test_requires_a_publish_release(enabled):
    draft = _draft()
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, object())


def test_unsigned_release_refuses(enabled):
    draft = _draft()
    forged = PublishRelease(
        draft_hash=content_hash(draft), surface=draft.surface,
        series_key=draft.series_key, released_by="Sean Schubert", signature="",
    )
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, forged)


def test_wrong_signature_refuses(enabled):
    # A caller with the Meta token but NOT the founder key cannot forge a
    # release the boundary accepts — this is the core "AI never publishes" bind.
    draft = _draft()
    forged = PublishRelease(
        draft_hash=content_hash(draft), surface=draft.surface,
        series_key=draft.series_key, released_by="Sean Schubert", signature="de" * 32,
    )
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, forged)


def test_release_for_a_different_draft_refuses(enabled):
    draft = _draft()
    other = _draft()
    object.__setattr__(other, "caption", "A different caption entirely.")
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(other))


def test_surface_mismatch_refuses(enabled):
    draft = _draft()
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(
            draft, _signed_release(draft, surface="facebook_page")
        )


def test_unbound_missing_image_refuses(enabled):
    # A slide with no hash-bound image ref cannot post (fail-closed until R-061).
    draft = _draft(missing_image=True)
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(draft))


def test_non_https_image_refuses(enabled):
    draft = _draft(non_https=True)
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(draft))


def test_banned_claim_belt_refuses(enabled):
    draft = _draft(banned=True)  # overlay carries "Selling out soon"
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(draft))


def test_unsupported_surface_refuses(enabled, monkeypatch):
    monkeypatch.setenv("META_FB_PAGE_ID", "9999")
    draft = _draft(surface="facebook_page")
    with pytest.raises(MetaConfigError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(draft))


def test_happy_path_runs_the_carousel_sequence(enabled):
    draft = _draft()
    transport = _FakeTransport()
    published = MetaPublisher(transport=transport).post(draft, _signed_release(draft))

    assert isinstance(published, PublishedPost)
    assert published.surface == "instagram_feed"
    assert published.draft_hash == content_hash(draft)
    assert published.released_by == "Sean Schubert"

    assert len(transport.calls) == len(draft.slides) + 2
    for url, params, headers in transport.calls[: len(draft.slides)]:
        assert url.endswith("/17841400000000000/media")
        assert params["is_carousel_item"] == "true"
        assert params["image_url"].startswith("https://")
        # Token rides the Authorization header, never the body/query.
        assert "access_token" not in params
        assert headers["Authorization"] == "Bearer founder-minted-token"

    _, container_params, _ = transport.calls[-2]
    assert container_params["media_type"] == "CAROUSEL"
    assert container_params["children"].count(",") == len(draft.slides) - 1
    assert "#AustinTonight" in container_params["caption"]

    publish_url, publish_params, _ = transport.calls[-1]
    assert publish_url.endswith("/media_publish")
    assert "creation_id" in publish_params


def test_stale_release_refuses(enabled):
    # A release stamped well outside the freshness window is stale — the event
    # state it was checked against may have drifted, so posting refuses.
    draft = _draft()
    old = _signed_release(draft, released_at="2026-07-24T09:00:00-05:00")  # 3h before REF_NOW
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, old)


def test_future_dated_release_refuses(enabled):
    draft = _draft()
    future = _signed_release(draft, released_at="2026-07-24T18:00:00-05:00")  # after REF_NOW
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, future)


def test_api_error_object_fails_loud(enabled):
    draft = _draft()

    def erroring(url, params, headers):
        return {"error": {"message": "Invalid OAuth access token", "code": 190}}

    with pytest.raises(meta_publisher.MetaAPIError):
        MetaPublisher(transport=erroring).post(draft, _signed_release(draft))


# --- The end-to-end proof: only a release the GATE issued authenticates -------

class _DurableJournal:
    durable = True

    def __init__(self):
        self._n = {}

    def count_on(self, day):
        return self._n.get(day, 0)

    def record(self, release, moment):
        self._n[moment.date()] = self._n.get(moment.date(), 0) + 1


def test_a_real_gate_issued_release_authenticates_and_posting_is_image_gated(monkeypatch):
    """Runs the FULL gate (approve -> release_for_publish) on a real generated
    draft and proves its release passes verify_release — the release is trusted
    because the gate signed it, not because its fields happen to match. Posting
    that real draft still refuses (its hook/cta slides have no bound image yet),
    which is the R-061 fail-closed boundary, not a bug."""
    ref = "2026-07-24T16:00:00-05:00"
    events = [e for e in EXAMPLE_EVENTS if e.get("domain_id") == "live-music"]
    by_id = {e["event_id"]: e for e in EXAMPLE_EVENTS}

    monkeypatch.setenv("META_ACCESS_TOKEN", "founder-minted-token")
    monkeypatch.setenv("META_IG_USER_ID", "17841400000000000")
    monkeypatch.setenv("ONELIVE_APPROVAL_KEY", TEST_KEY)
    monkeypatch.setattr(publish_gate, "_STATE_READER", lambda ids: {i: by_id[i] for i in ids})
    monkeypatch.setattr(publish_gate, "_utcnow", lambda: datetime.fromisoformat(ref))
    monkeypatch.setattr(publish_gate, "_RELEASE_JOURNAL", _DurableJournal())
    monkeypatch.setattr(publish_gate, "_APPROVER_REGISTRY", frozenset({"Sean Schubert"}))

    config = CarouselConfig(
        surface="instagram_feed", series_key="live-music", city="Austin",
        handle="@onelive", short_link_base="https://onelive.example",
        domain_ids=("live-music",), tier="T1", timeframe="tonight",
    )
    assignment = {
        "hook_type": "number_promise", "emotion_register": "excitement",
        "listicle_size": "5", "caption_style": "short_punch",
        "cta_type": "save_this", "post_slot": "evening", "media_type": "image",
    }
    draft = build_carousel(events, config, assignment, reference_time=ref)

    approval = approve(draft, "Sean Schubert", "2026-07-24T16:05:00-05:00")
    release = release_for_publish(draft, approval)

    # The gate's release authenticates against the draft it released.
    verify_release(release, draft)  # does not raise
    assert release.signature

    # And posting is correctly image-gated until the R-061 renderer binds images.
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, release)
