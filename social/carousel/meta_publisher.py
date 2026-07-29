"""The Meta Graph API posting boundary — built at R-026's trigger (spec §9.1).

Greppable summary: this is the ONLY module that speaks to Meta's Graph API,
and it is FAIL-CLOSED OFF by default exactly like the vision extraction path
(ai/vision_provider.py) — with no META_ACCESS_TOKEN + surface node id in the
deployment environment it constructs nothing and posts nothing. It is the
outward-facing twin of worker/promote.py: the last mechanical step from an
approved draft to a live post, and it REFUSES unless handed a PublishRelease
whose signature the human-approval gate (publish_gate.release_for_publish)
already produced AND whose draft_hash binds this exact draft. So this client
cannot post anything the gate did not release — "AI never publishes" holds by
construction, not by policy.

Trust bindings enforced here, every one fail-closed:
  1. Credentials come from the deployment environment ONLY (never a parameter,
     never present in agent sessions). Absent = MetaConfigError, nothing posts.
  2. A PublishRelease is REQUIRED and its draft_hash must equal this draft's
     content_hash — a draft edited after release is a void release.
  3. release.surface must match draft.surface (a release for one surface never
     posts to another).
  4. Every slide needs a hosted https image URL supplied by the caller; a
     missing or non-https URL refuses the whole post (no partial/broken deck).
  5. A banned-claim rescan (same regex as generation and the gate) runs as a
     belt over the exact copy about to be posted.

The autonomous loop (agent_loop.py) is structurally forbidden to import this
module — enforced by tests/test_social_carousel.py's import guard, same physics
as the publish_gate/autonomy bar. The HTTP transport is injected so the trust
logic is unit-tested with zero network; the real urllib transport is built only
when it is actually used. The rendered-slide-image hosting surface that feeds
`slide_image_urls`, and the Facebook-Page carousel endpoint, are the remaining
go-live builds tracked as R-061 — this client fails loud rather than pretending
either exists.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass

from social.carousel.config import SURFACE_CONSTRAINTS
from social.carousel.generator import (
    BANNED_CLAIM_RE,
    CarouselDraft,
    all_draft_text,
    content_hash,
)
from social.carousel.publish_gate import PublishRelease

# Graph API version pinned so an upstream default bump never silently changes
# request shape; bump deliberately when Meta deprecates a version.
GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

ACCESS_TOKEN_ENV = "META_ACCESS_TOKEN"

# Which env var holds the posting node id for each supported surface. Only
# instagram_feed has a real Graph API carousel flow in this client; the
# facebook_page carousel endpoint is a separate build (R-061), and an
# unsupported surface refuses loudly rather than posting to the wrong place.
SURFACE_NODE_ENV = {
    "instagram_feed": "META_IG_USER_ID",
    "facebook_page": "META_FB_PAGE_ID",
}
SUPPORTED_SURFACES = ("instagram_feed",)


class MetaConfigError(RuntimeError):
    """Posting is not configured (missing credentials/surface node), or is
    disabled — fail closed OFF, never post."""


class MetaPublishError(RuntimeError):
    """A draft cannot be lawfully posted (release/hash/image/claim failure)."""


class MetaAPIError(RuntimeError):
    """The Graph API returned an error or an unusable response."""


@dataclass(frozen=True)
class PublishedPost:
    """Proof that Meta accepted and published one exact approved draft."""

    surface: str
    post_id: str
    container_id: str
    draft_hash: str
    released_by: str


def meta_publishing_enabled() -> bool:
    """True only when the access token is present in the environment. Like
    vision_extraction_enabled(): the capability is OFF unless the deployment
    explicitly holds the founder-minted credential."""
    return bool(os.environ.get(ACCESS_TOKEN_ENV, "").strip())


def _resolve_access_token() -> str:
    token = os.environ.get(ACCESS_TOKEN_ENV, "").strip()
    if not token:
        raise MetaConfigError(
            f"{ACCESS_TOKEN_ENV} unset — the Meta posting client is fail-closed "
            "OFF. The token is founder-minted deployment config (spec §9.1), "
            "never present in agent sessions, so nothing posts until it exists."
        )
    return token


def _resolve_surface_node(surface: str) -> str:
    if surface not in SUPPORTED_SURFACES:
        env = SURFACE_NODE_ENV.get(surface)
        detail = (
            f"the {surface!r} carousel endpoint is not built in this client (R-061)"
            if env
            else f"unknown surface {surface!r}"
        )
        raise MetaConfigError(f"refusing to post: {detail}")
    node = os.environ.get(SURFACE_NODE_ENV[surface], "").strip()
    if not node:
        raise MetaConfigError(
            f"{SURFACE_NODE_ENV[surface]} unset — cannot post to {surface!r} "
            "without its Graph API node id (founder-minted deployment config)."
        )
    return node


def _urllib_transport(url: str, params: dict) -> dict:
    """The real HTTP transport: form-encoded POST to the Graph API, JSON
    response, fail LOUD on transport error or a Graph `error` object. Built
    only when a post actually runs — tests inject a fake transport instead."""
    data = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:  # 4xx/5xx carry a JSON error body
        detail = exc.read().decode("utf-8", "replace")
        raise MetaAPIError(f"Graph API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise MetaAPIError(f"Graph API transport error: {exc.reason}") from exc
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise MetaAPIError(f"Graph API returned non-JSON: {body[:200]!r}") from exc


def _require_https(url: str, context: str) -> str:
    url = (url or "").strip()
    if not url.startswith("https://"):
        raise MetaPublishError(
            f"{context}: image url {url!r} is not an https URL — Meta requires a "
            "publicly reachable https image for every carousel slide"
        )
    return url


def _caption_with_tags(draft: CarouselDraft) -> str:
    """The exact caption text posted: the draft's caption (which already ends
    with the short link) followed by its hashtags — one assembled string, the
    same surfaces the banned-claim belt rescans."""
    tags = " ".join(draft.hashtags)
    return f"{draft.caption}\n\n{tags}".strip() if tags else draft.caption


class MetaPublisher:
    """Posts one approved carousel draft to Meta. Constructing it never touches
    the network; `post` does, and only after every trust binding passes."""

    def __init__(self, transport=None) -> None:
        # Injected transport(url, params) -> dict for hermetic tests; the real
        # urllib transport is the default used in deployment.
        self._transport = transport or _urllib_transport

    def _call(self, node: str, edge: str, params: dict, token: str) -> dict:
        url = f"{GRAPH_API_BASE}/{node}/{edge}"
        payload = self._transport(url, {**params, "access_token": token})
        if not isinstance(payload, dict):
            raise MetaAPIError(f"Graph API {edge} returned {type(payload).__name__}, expected object")
        if "error" in payload:
            raise MetaAPIError(f"Graph API {edge} error: {payload['error']}")
        node_id = payload.get("id")
        if not node_id:
            raise MetaAPIError(f"Graph API {edge} returned no id: {payload!r}")
        return payload

    def post(
        self,
        draft: CarouselDraft,
        release: PublishRelease,
        slide_image_urls,
    ) -> PublishedPost:
        """Publish `draft` to Meta. Refuses unless the capability is enabled,
        the release authenticates this exact draft/surface, every slide has a
        hosted https image, and the copy carries no banned claim.

        slide_image_urls: an ordered sequence, one https url per slide in
        deck order (hook, events…, cta). The rendered-card hosting surface
        (R-061) supplies these; event slides' cover urls are NOT assumed here
        because a Meta carousel is branded rendered cards, not raw photos.
        """
        if not meta_publishing_enabled():
            raise MetaConfigError(
                f"{ACCESS_TOKEN_ENV} unset — Meta posting is fail-closed OFF; "
                "nothing publishes until the founder mints the token."
            )
        if not isinstance(release, PublishRelease):
            raise MetaPublishError(
                "refusing to post: a PublishRelease from the human-approval gate "
                "is required — this client never posts an unreleased draft"
            )
        draft_hash = content_hash(draft)
        if release.draft_hash != draft_hash:
            raise MetaPublishError(
                "refusing to post: the release does not bind this exact draft "
                "(hash mismatch) — the draft changed after release, so it is void"
            )
        if release.surface != draft.surface:
            raise MetaPublishError(
                f"refusing to post: release surface {release.surface!r} does not "
                f"match draft surface {draft.surface!r}"
            )
        if draft.surface not in SURFACE_CONSTRAINTS:
            raise MetaPublishError(f"refusing to post: unknown surface {draft.surface!r}")

        token = _resolve_access_token()
        node = _resolve_surface_node(draft.surface)

        urls = list(slide_image_urls or [])
        if len(urls) != len(draft.slides):
            raise MetaPublishError(
                f"refusing to post: {len(urls)} image url(s) supplied for "
                f"{len(draft.slides)} slides — every slide needs a hosted image"
            )
        child_urls = [
            _require_https(url, f"slide {i}") for i, url in enumerate(urls)
        ]

        # Belt over the exact posted copy (same regex as generation + gate):
        # a banned claim never reaches Meta even if a caller hand-built a draft.
        for text in [*all_draft_text(draft), _caption_with_tags(draft)]:
            match = BANNED_CLAIM_RE.search(text)
            if match:
                raise MetaPublishError(
                    f"refusing to post: banned claim phrase {match.group(0)!r} in copy"
                )

        # Graph API Instagram carousel flow: a media container per slide, then
        # the carousel container, then publish (spec §9.1 / Meta docs).
        child_ids = [
            self._call(
                node,
                "media",
                {"image_url": url, "is_carousel_item": "true"},
                token,
            )["id"]
            for url in child_urls
        ]
        container = self._call(
            node,
            "media",
            {
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "caption": _caption_with_tags(draft),
            },
            token,
        )
        published = self._call(
            node,
            "media_publish",
            {"creation_id": container["id"]},
            token,
        )
        return PublishedPost(
            surface=draft.surface,
            post_id=published["id"],
            container_id=container["id"],
            draft_hash=draft_hash,
            released_by=release.released_by,
        )
