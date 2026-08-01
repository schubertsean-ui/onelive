"""Enrichment orchestration — the stage that CONNECTS the local-first cascade
(docs/strategy/ONE_LIVE_VERIFIED_PREVIEW_ENRICHMENT_v1.md).

The two lower modules already exist and are tested, but until now nothing called
them together (the "built-not-wired" gap): `first_party.extract_first_party`
(page → sameAs official channels + site-hosted embeds) and
`youtube.resolve_channel_video` (an entity's OWN sameAs channel → a verified,
embeddable video). This module runs them as ONE pass and picks the single
**best verified preview** to attach, with provenance.

AUTHORITY ORDER (strongest first) — every option is first-party, never a guess:
  1. a **site-hosted embed** the entity put on its OWN page (a YouTube/Spotify/
     Vimeo iframe the venue/artist chose to publish → they vouched for it), then
  2. a **resolved-channel video** reached through the entity's own `sameAs`
     YouTube channel (authoritative id/handle, not a name search).
If neither exists → an **honest gap** (no preview), never filler.

DISCIPLINE (mirrors first_party.py / youtube.py):
  * NETWORK-ISOLATED — the only network dependency (the YouTube Data API) is an
    injected `Fetcher`; page HTML is passed in already-fetched. So the whole
    orchestration is unit-testable with no key and no egress.
  * WRITES NOTHING, PUBLISHES NOTHING — returns a candidate enrichment with
    provenance that still flows through the normal gate. AI never publishes.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from .first_party import Embed, extract_first_party
from .youtube import Fetcher, VideoEnrichment, resolve_channel_video

_log = logging.getLogger(__name__)

# How a preview was obtained (provenance) + its confidence, both authoritative.
SOURCE_HOSTED_EMBED = "site_hosted_embed"        # the entity published it on its own page
SOURCE_RESOLVED_CHANNEL = "sameas_resolved_channel"  # via the entity's own sameAs channel
CONFIDENCE_AUTHORITATIVE = "authoritative"

# Embed providers we can render inline (a site-hosted iframe of one of these is a
# preview the entity vouched for). Kept in sync with first_party._EMBED_PROVIDERS.
_RENDERABLE_EMBED_PROVIDERS = ("youtube", "spotify", "vimeo")


@dataclass
class BestPreview:
    """The single preview to attach to an entity + its provenance record."""
    kind: str                 # "video" (resolved) | "embed" (site-hosted)
    provider: str             # youtube / spotify / vimeo
    url: str                  # embeddable/watch url
    source: str               # SOURCE_* — how we got it
    confidence: str = CONFIDENCE_AUTHORITATIVE

    def provenance(self) -> dict:
        return {"source": self.source, "provider": self.provider,
                "url": self.url, "confidence": self.confidence}


@dataclass
class EntityEnrichment:
    """Everything one enrichment pass surfaced for an entity (venue/artist)."""
    same_as: list[str] = field(default_factory=list)         # official channels
    hosted_embeds: list[Embed] = field(default_factory=list)  # embeds on its own page
    video: Optional[VideoEnrichment] = None                   # resolved-channel video

    def best_preview(self) -> Optional[BestPreview]:
        """Pick the strongest verified preview, or None (honest gap).

        A site-hosted renderable embed wins (the entity explicitly published it);
        otherwise the resolved-channel video; otherwise nothing."""
        for emb in self.hosted_embeds:
            if emb.provider in _RENDERABLE_EMBED_PROVIDERS:
                return BestPreview(kind="embed", provider=emb.provider, url=emb.url,
                                   source=SOURCE_HOSTED_EMBED)
        if self.video is not None:
            return BestPreview(kind="video", provider="youtube", url=self.video.embed_url,
                               source=SOURCE_RESOLVED_CHANNEL)
        return None

    def has_signal(self) -> bool:
        return bool(self.same_as or self.hosted_embeds or self.video)


def enrich_from_page(html: str, url: str, yt_fetch: Optional[Fetcher] = None) -> EntityEnrichment:
    """Run the local-first cascade over an already-fetched first-party page.

    `html`/`url` are the entity's own page (fetched upstream where egress works).
    `yt_fetch` is the injected YouTube Data API client (youtube.client_from_env());
    when None (no key / feature off) the channel-resolution step is skipped and we
    still return whatever first-party signals the page carried. Never raises: a
    resolution failure degrades to whatever was gathered, logged."""
    fp = extract_first_party(html or "", url)
    video: Optional[VideoEnrichment] = None
    if yt_fetch is not None and fp.same_as:
        try:
            video = resolve_channel_video(fp.same_as, yt_fetch)
        except Exception as exc:  # never crash the enrichment pass
            _log.warning("enrichment: youtube resolution degraded for %s: %s", url, exc)
            video = None
    return EntityEnrichment(same_as=fp.same_as, hosted_embeds=fp.hosted_embeds, video=video)
