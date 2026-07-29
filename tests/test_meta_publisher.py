"""The Meta posting boundary: fail-closed OFF, gate-signed-release-bound,
content-addressed images, at-post state recheck, no network in tests."""
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
EVENT_START = "2026-07-24T21:00:00-05:00"  # tonight, ahead of REF_NOW
SHA = {0: "a" * 64, 1: "b" * 64, 2: "c" * 64}  # per-slide image digests


def _img(i, *, sha=None, https=True):
    sha = SHA[i] if sha is None else sha
    scheme = "https" if https else "http"
    return f"{scheme}://cards.example/{sha}.png"


def _draft(surface="instagram_feed", banned=False, missing_sha=False, non_https=False,
           bad_addressing=False, bad_digest=False):
    overlay = ("Selling out soon",) if banned else ("Doors at 8",)
    ev_ref = _img(1, https=not non_https)
    ev_sha = "" if missing_sha else SHA[1]
    if bad_addressing:  # url does not contain the bound digest
        ev_ref = "https://cards.example/UNRELATED.png"
    if bad_digest:  # digest is not a real 64-hex sha, but appears in the url
        ev_sha = "promo"
        ev_ref = "https://cards.example/promo.png"
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
                  image_ref=_img(0), image_sha256=SHA[0]),
            Slide(kind="event", headline="The Midnight Brass", overlay_lines=overlay,
                  event_id="ex-1", start_time=EVENT_START,
                  image_ref=ev_ref, image_sha256=ev_sha),
            Slide(kind="cta", headline="Send this to your crew",
                  image_ref=_img(2), image_sha256=SHA[2]),
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


def _featurable(ids):
    return {
        i: {"confidence": "confirmed", "event_status": "scheduled",
            "origin": "canonical_event", "start_time": EVENT_START}
        for i in ids
    }


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
    monkeypatch.setenv("ONELIVE_APPROVAL_KEY", TEST_KEY)
    monkeypatch.setenv("ONELIVE_CARD_IMAGE_HOSTS", "https://cards.example/")
    monkeypatch.setattr(publish_gate, "_utcnow", lambda: datetime.fromisoformat(REF_NOW))
    monkeypatch.setattr(publish_gate, "_STATE_READER", _featurable)


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
        series_key=draft.series_key, released_by="Sean Schubert",
        released_at=REF_NOW, signature="",
    )
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, forged)


def test_wrong_signature_refuses(enabled):
    draft = _draft()
    forged = PublishRelease(
        draft_hash=content_hash(draft), surface=draft.surface,
        series_key=draft.series_key, released_by="Sean Schubert",
        released_at=REF_NOW, signature="de" * 32,
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


def test_stale_release_refuses(enabled):
    draft = _draft()
    old = _signed_release(draft, released_at="2026-07-24T09:00:00-05:00")
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, old)


def test_future_dated_release_refuses(enabled):
    draft = _draft()
    future = _signed_release(draft, released_at="2026-07-24T18:00:00-05:00")
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, future)


def test_image_without_bound_digest_refuses(enabled):
    draft = _draft(missing_sha=True)
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(draft))


def test_image_not_content_addressed_refuses(enabled):
    # url does not contain the approved digest → possible swap → refuse.
    draft = _draft(bad_addressing=True)
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(draft))


def test_non_https_image_refuses(enabled):
    draft = _draft(non_https=True)
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(draft))


def test_banned_claim_belt_refuses(enabled):
    draft = _draft(banned=True)
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(draft))


def test_event_now_disputed_refuses(enabled, monkeypatch):
    # State drifted after approval: the at-post recheck refuses.
    monkeypatch.setattr(
        publish_gate, "_STATE_READER",
        lambda ids: {i: {"confidence": "disputed", "event_status": "scheduled",
                         "origin": "canonical_event"} for i in ids},
    )
    draft = _draft()
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(draft))


def test_no_state_reader_refuses(enabled, monkeypatch):
    monkeypatch.setattr(publish_gate, "_STATE_READER", None)
    draft = _draft()
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(draft))


def test_event_retimed_since_approval_refuses(enabled, monkeypatch):
    # Canonical time drifted after approval (still confirmed/scheduled): the
    # slide's displayed time is stale, so the fresh-canonical recheck refuses.
    monkeypatch.setattr(
        publish_gate, "_STATE_READER",
        lambda ids: {i: {"confidence": "confirmed", "event_status": "scheduled",
                         "origin": "canonical_event",
                         "start_time": "2026-07-24T22:30:00-05:00"} for i in ids},
    )
    draft = _draft()
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(draft))


def test_untrusted_image_host_refuses(enabled, monkeypatch):
    monkeypatch.setenv("ONELIVE_CARD_IMAGE_HOSTS", "https://cdn.trusted.example/")
    draft = _draft()  # images are on cards.example — not the trusted host
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(draft))


def test_bare_origin_host_prefix_is_not_trusted(enabled, monkeypatch):
    # A prefix without the trailing '/' would also match cards.example.evil —
    # it is dropped, so nothing is trusted and the post fails closed.
    monkeypatch.setenv("ONELIVE_CARD_IMAGE_HOSTS", "https://cards.example")
    draft = _draft()
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(draft))


def test_non_hex_digest_refuses(enabled):
    # A non-digest string that happens to appear in the url must not pass as a
    # content address.
    draft = _draft(bad_digest=True)
    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, _signed_release(draft))


def test_no_trusted_host_allowlist_refuses(enabled, monkeypatch):
    monkeypatch.delenv("ONELIVE_CARD_IMAGE_HOSTS", raising=False)
    draft = _draft()
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
        assert "access_token" not in params
        assert headers["Authorization"] == "Bearer founder-minted-token"

    _, container_params, _ = transport.calls[-2]
    assert container_params["media_type"] == "CAROUSEL"
    assert container_params["children"].count(",") == len(draft.slides) - 1
    assert "#AustinTonight" in container_params["caption"]

    publish_url, publish_params, _ = transport.calls[-1]
    assert publish_url.endswith("/media_publish")
    assert "creation_id" in publish_params


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
    """The FULL gate (approve -> release_for_publish) on a real generated draft:
    its release passes verify_release (trusted because the gate signed it), and
    posting still refuses because the generator does not yet content-address
    slide images (the R-061 fail-closed boundary)."""
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

    verify_release(release, draft)  # does not raise — the gate signed it
    assert release.signature and release.released_at

    with pytest.raises(MetaPublishError):
        MetaPublisher(transport=_FakeTransport()).post(draft, release)
