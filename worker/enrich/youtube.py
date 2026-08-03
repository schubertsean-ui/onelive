"""YouTube resolution — Layer 3 (free-key platform lookup) of the local-first
enrichment cascade (docs/strategy/ONE_LIVE_VERIFIED_PREVIEW_ENRICHMENT_v1.md §2–§3).

This is the VERIFIED half of the preview ("Option B", founder directive
2026-07-31 "I'd like B" — the entity's *actual* video, not a search). It attaches
a video ONLY when the entity's OWN `sameAs` link points at a YouTube channel — the
channel the entity vouched for by publishing the link. It NEVER does a free-text
`search.list` guessing "this is them" (that is Option A's honest search, which
stays in web/lib/preview.ts). So every attachment here is authoritative by
construction, carrying a provenance record the gate consumes.

DISCIPLINE:
  * AUTHORITATIVE-ONLY — resolve by the channel id/handle the entity published in
    `sameAs`, never by name search. A name-only match is NOT verified and is not
    produced here (spec §3: "resolve by authoritative ID, never by free-text
    search alone").
  * CHEAP QUOTA — channels.list + playlistItems.list + videos.list = 3 units per
    entity; deliberately avoids search.list (100 units) (spec §4 discipline).
  * NETWORK ISOLATED — all HTTP goes through an injected `Fetcher`; the resolution
    and selection logic is pure and unit-tested with a fake. The default fetcher is
    stdlib-only (urllib), mirroring worker/enrich/first_party.py — no new dependency.
  * HONEST GAP — no channel in sameAs, no API key, or no public+embeddable video →
    None. Never a low-confidence guess auto-attached (spec §3, "honest gaps beat
    filler").
  * WRITES NOTHING, PUBLISHES NOTHING — the result is a candidate enrichment with
    provenance that still flows through the gate. Publication is gate-custodied —
    nothing publishes except through the gate.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Optional
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

_log = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3/"

# Provenance: how the entity was resolved to this channel (recorded for audit and
# to grade confidence). A canonical channel id is the strongest; a handle/username
# required one lookup but is still the entity's own published link.
RESOLVED_VIA_CHANNEL_ID = "sameas_youtube_channel_id"
RESOLVED_VIA_HANDLE = "sameas_youtube_handle"
RESOLVED_VIA_USERNAME = "sameas_youtube_username"

# Confidence rides the 4-state model conceptually (spec §3): an official-channel
# match is authoritative. Nothing weaker is produced by this module.
CONFIDENCE_AUTHORITATIVE = "authoritative"

# A Fetcher maps (endpoint, params) -> parsed JSON dict. Injected so orchestration
# is testable without network or a key; the default (real) implementation is below.
Fetcher = Callable[[str, Mapping[str, str]], dict]


@dataclass
class VideoEnrichment:
    """A verified video attachment + its provenance record (spec §3)."""
    video_id: str
    embed_url: str          # https://www.youtube.com/embed/<id> (uploader-permitted)
    watch_url: str          # https://www.youtube.com/watch?v=<id>
    title: Optional[str]
    channel_id: str
    resolved_via: str       # one of RESOLVED_VIA_*
    authoritative_link: str  # the sameAs URL that vouched for the channel
    confidence: str = CONFIDENCE_AUTHORITATIVE

    def provenance(self) -> dict:
        """The jsonb provenance the enrichment store records (spec §2 schema)."""
        return {
            "resolved_via": self.resolved_via,
            "authoritative_link": self.authoritative_link,
            "confidence": self.confidence,
            "channel_id": self.channel_id,
            "video_id": self.video_id,
        }


# --- pure parsing: sameAs URL -> channel reference ----------------------------

def _is_youtube_host(host: str) -> bool:
    host = (host or "").lower().lstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("m."):
        host = host[2:]
    return host in ("youtube.com", "youtu.be", "music.youtube.com")


def parse_channel_ref(url: str) -> Optional[tuple[str, str]]:
    """A YouTube channel URL -> (kind, value), or None if it names no channel.

    kind is 'id' (canonical UC… — strongest), 'handle' (@name), or 'username'
    (legacy /user/). A bare `/c/CustomName` custom URL is intentionally NOT
    resolved: the API has no cheap param for it (only the 100-unit search), so we
    treat it as an honest gap here rather than burn quota [R-062]. A /watch
    or /embed video link is not a channel and returns None.
    """
    try:
        p = urlparse(url)
    except ValueError:
        return None
    if p.scheme not in ("http", "https") or not _is_youtube_host(p.hostname or ""):
        return None
    segs = [s for s in (p.path or "").split("/") if s]
    if not segs:
        return None
    first = segs[0]
    if first == "channel" and len(segs) >= 2 and segs[1].startswith("UC"):
        return ("id", segs[1])
    if first == "user" and len(segs) >= 2:
        return ("username", segs[1])
    if first.startswith("@") and len(first) > 1:
        return ("handle", first)          # youtube.com/@handle
    return None


def channel_ref_from_sameas(same_as: Iterable[str]) -> Optional[tuple[str, str, str]]:
    """Pick the best channel reference from a list of sameAs URLs.

    Returns (kind, value, source_url) — the source_url is the vouching sameAs link,
    kept for provenance. A canonical channel id is preferred over a handle/username
    because it needs no extra resolution and cannot be reassigned.
    """
    best: Optional[tuple[str, str, str]] = None
    for url in same_as:
        ref = parse_channel_ref(url)
        if not ref:
            continue
        kind, value = ref
        if kind == "id":
            return (kind, value, url)      # strongest — take immediately
        if best is None:
            best = (kind, value, url)
    return best


# --- pure selection: API items -> the video to attach -------------------------

def _embed_url(video_id: str) -> str:
    return f"https://www.youtube.com/embed/{video_id}"


def _watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def pick_embeddable(video_items: list) -> Optional[dict]:
    """From videos.list items, the first PUBLIC + EMBEDDABLE one — order preserved
    (the caller passes recent-uploads-first). A private/unlisted or non-embeddable
    video is skipped, never attached (embedding it would 404 for the user)."""
    for item in video_items:
        if not isinstance(item, dict):
            continue
        status = item.get("status") or {}
        if status.get("privacyStatus") != "public":
            continue
        if status.get("embeddable") is not True:
            continue
        vid = item.get("id")
        if isinstance(vid, str) and vid:
            return item
    return None


# --- orchestration (uses the injected Fetcher; no network of its own) ----------

def _uploads_playlist(fetch: Fetcher, ref: tuple[str, str, str]) -> Optional[tuple[str, str]]:
    """Resolve a channel reference to (channel_id, uploads_playlist_id) with one
    channels.list call (1 unit). Returns None if the channel doesn't resolve."""
    kind, value, _ = ref
    params = {"part": "contentDetails"}
    if kind == "id":
        params["id"] = value
    elif kind == "handle":
        params["forHandle"] = value          # API accepts the @-handle
    elif kind == "username":
        params["forUsername"] = value
    else:
        return None
    data = fetch("channels", params)
    items = data.get("items") if isinstance(data, dict) else None
    if not items:
        return None
    ch = items[0]
    channel_id = ch.get("id")
    uploads = (
        ((ch.get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads")
    )
    if not (isinstance(channel_id, str) and isinstance(uploads, str) and uploads):
        return None
    return (channel_id, uploads)


def _recent_video_ids(fetch: Fetcher, uploads_playlist_id: str, limit: int = 5) -> list[str]:
    """Most-recent upload video ids via playlistItems.list (1 unit)."""
    data = fetch(
        "playlistItems",
        {"part": "contentDetails", "playlistId": uploads_playlist_id, "maxResults": str(limit)},
    )
    out: list[str] = []
    items = data.get("items") if isinstance(data, dict) else None
    for it in items or []:
        vid = ((it or {}).get("contentDetails") or {}).get("videoId")
        if isinstance(vid, str) and vid:
            out.append(vid)
    return out


def resolve_channel_video(same_as: Iterable[str], fetch: Fetcher) -> Optional[VideoEnrichment]:
    """The public entry point: given an entity's sameAs links, attach its most
    recent PUBLIC + EMBEDDABLE video from its OWN YouTube channel — or None (honest
    gap). Never raises: a transport/parse failure degrades to None, logged.

    `fetch` is the injected YouTube Data API client. Use client_from_env() for the
    real one (None when YOUTUBE_API_KEY is unset — the whole feature is then off).
    """
    ref = channel_ref_from_sameas(same_as)
    if not ref:
        return None
    _kind, _value, source_url = ref
    resolved_via = {
        "id": RESOLVED_VIA_CHANNEL_ID,
        "handle": RESOLVED_VIA_HANDLE,
        "username": RESOLVED_VIA_USERNAME,
    }[ref[0]]
    try:
        chan = _uploads_playlist(fetch, ref)
        if not chan:
            return None
        channel_id, uploads = chan
        video_ids = _recent_video_ids(fetch, uploads)
        if not video_ids:
            return None
        data = fetch("videos", {"part": "status,snippet", "id": ",".join(video_ids)})
        items = data.get("items") if isinstance(data, dict) else None
        chosen = pick_embeddable(items or [])
        if not chosen:
            return None
        vid = chosen["id"]
        title = ((chosen.get("snippet") or {}).get("title")) or None
        return VideoEnrichment(
            video_id=vid,
            embed_url=_embed_url(vid),
            watch_url=_watch_url(vid),
            title=title if isinstance(title, str) else None,
            channel_id=channel_id,
            resolved_via=resolved_via,
            authoritative_link=source_url,
        )
    except Exception as exc:  # never crash the enrichment pass
        _log.warning("youtube: resolution degraded for %s: %s", source_url, exc)
        return None


# --- default (real) fetcher: stdlib urllib, key-gated --------------------------

def make_fetcher(api_key: str, *, timeout: float = 8.0) -> Fetcher:
    """A real YouTube Data API fetcher bound to `api_key`. Stdlib-only."""
    def fetch(endpoint: str, params: Mapping[str, str]) -> dict:
        q = dict(params)
        q["key"] = api_key
        url = YOUTUBE_API_BASE + endpoint + "?" + urlencode(q)
        req = Request(url, headers={"User-Agent": "OneLive-enrichment (+https://1live.co)"})
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310 (https, fixed base)
            return json.loads(resp.read().decode("utf-8"))
    return fetch


def client_from_env(env: Optional[Mapping[str, str]] = None) -> Optional[Fetcher]:
    """The real fetcher from YOUTUBE_API_KEY, or None when it's unset (feature off).
    Key-gated exactly like the other optional integrations — absent key = disabled,
    never an error."""
    import os
    src = env if env is not None else os.environ
    key = (src.get("YOUTUBE_API_KEY") or "").strip()
    if not key:
        return None
    return make_fetcher(key)
