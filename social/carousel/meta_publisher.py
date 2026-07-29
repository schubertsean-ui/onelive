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
  2. The release must AUTHENTICATE via publish_gate.verify_release: it binds
     this exact draft (content-hash identity) AND its signature verifies under
     the founder key. A caller with the Meta token but not the founder key
     cannot hand-build an accepted release (evaluator PR #106, forgeable-release
     finding) — only a release the gate actually signed can publish.
  3. Slides are posted from the DRAFT's own hash-bound image refs, never from
     caller-supplied urls (evaluator PR #106, unbound-image finding): a caller
     cannot swap in unapproved imagery, because any change to a slide image
     changes content_hash and voids the release. Every image must be https;
     a slide with no bound image refuses the whole post (fail-closed until the
     R-061 renderer populates every slide's image ref).
  4. A banned-claim rescan (same regex as generation and the gate) runs as a
     belt over the exact copy about to be posted.

The autonomous loop (agent_loop.py) is structurally forbidden to import this
module — enforced by tests/test_social_carousel.py's import guard, same physics
as the publish_gate/autonomy bar. The HTTP transport is injected so the trust
logic is unit-tested with zero network; the real urllib transport is built only
when it is actually used. The rendered-slide-image hosting surface that must
populate every slide's bound image ref, and the Facebook-Page carousel
endpoint, are the remaining go-live builds tracked as R-061 — this client fails
loud rather than pretending either exists.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime

from social.carousel.config import SURFACE_CONSTRAINTS
from social.carousel.generator import (
    BANNED_CLAIM_RE,
    CarouselDraft,
    all_draft_text,
)
from social.carousel.publish_gate import (
    PublishRelease,
    assert_events_still_publishable,
    current_moment,
    verify_release,
)

# A signed release is fresh only briefly: the human (or autonomy grant) approves
# and the post follows within this window. Beyond it the release is stale — the
# event state it was checked against may have drifted (disputed/cancelled/
# started), so the boundary refuses and a new approval is required (evaluator
# PR #106: a release must not be an unbounded bearer token).
MAX_RELEASE_AGE_SECONDS = 3600

# Graph API version pinned so an upstream default bump never silently changes
# request shape; bump deliberately when Meta deprecates a version.
GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

ACCESS_TOKEN_ENV = "META_ACCESS_TOKEN"

# The trusted, IMMUTABLE, content-addressed image host(s) — deployment config
# (comma-separated https origin/prefixes). A content-addressed url only proves
# the bytes are the approved bytes when the host is trusted to serve that digest
# immutably (evaluator PR #106 r4: an arbitrary host can serve different pixels
# from /<approved-sha>.png). Empty = fail-closed, nothing posts. The R-061 card
# host must be an immutable, object-locked, content-addressed store.
CARD_IMAGE_HOSTS_ENV = "ONELIVE_CARD_IMAGE_HOSTS"

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


def _urllib_transport(url: str, params: dict, headers: dict) -> dict:
    """The real HTTP transport: form-encoded POST to the Graph API, JSON
    response, fail LOUD on transport error or a Graph `error` object. The access
    token rides an Authorization header (evaluator PR #106 nit), never the body
    or query. Built only when a post actually runs — tests inject a fake
    transport instead."""
    data = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers or {}, method="POST")
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


def _trusted_image_hosts() -> tuple:
    raw = os.environ.get(CARD_IMAGE_HOSTS_ENV, "")
    return tuple(h.strip() for h in raw.split(",") if h.strip())


def _require_content_addressed_image(slide, index: int) -> str:
    """The slide's image must be an https url that is BOTH content-addressed to
    the approved bytes AND served from a trusted immutable host:

      1. the bound image_sha256 (covered by content_hash, so the release binds
         it) must appear in the url — the url names the approved bytes; and
      2. the url must sit on a configured trusted-host prefix — a content-
         addressed url only proves the bytes on an immutable store we trust to
         serve that digest and never mutate it (evaluator PR #106 r4: an
         arbitrary host can serve different pixels from /<sha>.png).

    Empty digest OR no configured trusted host refuses (fail-closed until the
    R-061 renderer hosts the card at its content-addressed url on that store)."""
    context = f"slide {index} ({slide.kind})"
    url = _require_https(slide.image_ref, context)
    digest = (slide.image_sha256 or "").strip().lower()
    if not digest:
        raise MetaPublishError(
            f"{context}: no bound image_sha256 — the slide's image is not "
            "content-addressed, so it cannot be posted (fail-closed until the "
            "renderer hosts the rendered card; R-061)"
        )
    if digest not in url.lower():
        raise MetaPublishError(
            f"{context}: image url is not content-addressed to the approved "
            "bytes (bound sha256 not present in the url) — refusing to post "
            "possibly-swapped imagery"
        )
    hosts = _trusted_image_hosts()
    if not hosts:
        raise MetaPublishError(
            f"{context}: no trusted image-host allowlist configured "
            f"({CARD_IMAGE_HOSTS_ENV}) — a content-addressed url is only "
            "trustworthy on an immutable store we control, so nothing posts "
            "(fail-closed; the R-061 card host)"
        )
    if not any(url.startswith(prefix) for prefix in hosts):
        raise MetaPublishError(
            f"{context}: image host is not in the trusted immutable-host "
            "allowlist — refusing possibly-mutable imagery from an untrusted host"
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
        payload = self._transport(url, params, {"Authorization": f"Bearer {token}"})
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
    ) -> PublishedPost:
        """Publish `draft` to Meta. Refuses unless the capability is enabled,
        the release AUTHENTICATES this exact draft (gate signature verified),
        every slide carries a hash-bound https image ref, and the copy carries
        no banned claim.

        Images come from the draft's own slides (draft.slides[i].image_ref),
        which are covered by content_hash and therefore by the verified release
        — a caller cannot substitute unapproved imagery. The R-061 renderer is
        what populates every slide's image ref with its hosted rendered-card
        url; until it does, hook/cta slides have no image ref and this refuses.
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
        # The one authentication point: only a release the gate signed (binding
        # this exact draft) verifies. A hand-built matching-fields object fails.
        try:
            verify_release(release, draft)
        except ValueError as exc:
            raise MetaPublishError(f"refusing to post: {exc}") from exc
        # Freshness: a stale (or future-dated) release refuses. Age is measured
        # against the gate's OWN clock, the same one that stamped released_at,
        # so the release's subject cannot choose the clock that judges its age.
        age = (current_moment() - datetime.fromisoformat(release.released_at)).total_seconds()
        if age < 0 or age > MAX_RELEASE_AGE_SECONDS:
            raise MetaPublishError(
                f"refusing to post: release age {age:.0f}s is outside the "
                f"[0, {MAX_RELEASE_AGE_SECONDS}]s freshness window — re-approve "
                "against current event state"
            )
        if draft.surface not in SURFACE_CONSTRAINTS:
            raise MetaPublishError(f"refusing to post: unknown surface {draft.surface!r}")
        # Final trust check at the LAST moment before the outward post: re-read
        # the events from the canonical store and refuse if any drifted
        # (disputed/cancelled/started) since approval — a fresh signature is not
        # a fresh fact. Fail-closed if no reader is wired.
        try:
            assert_events_still_publishable(draft)
        except ValueError as exc:
            raise MetaPublishError(f"refusing to post: {exc}") from exc

        token = _resolve_access_token()
        node = _resolve_surface_node(draft.surface)

        # Post the draft's OWN images (hash-bound, so the verified release covers
        # them), and require each image_ref to be CONTENT-ADDRESSED to the
        # approved bytes: the slide's bound image_sha256 must appear in the url,
        # so the host cannot swap the bytes behind an unchanged url. Empty
        # image_sha256 (today's generator) refuses — fail-closed until R-061.
        child_urls = [
            _require_content_addressed_image(slide, i)
            for i, slide in enumerate(draft.slides)
        ]
        draft_hash = release.draft_hash

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
