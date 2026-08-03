"""First-party structured-data extractor — the parse layer of the local-first
enrichment cascade (docs/strategy/ONE_LIVE_VERIFIED_PREVIEW_ENRICHMENT_v1.md §1,
Layer 1) and the foundation of "get good at pulling data from websites / link
hubs" (founder directive 2026-08-01).

Given an already-fetched HTML document and its URL, it pulls the signals a first
party CHOSE to publish for machine consumption — schema.org/JSON-LD, `sameAs`
official-channel links, oEmbed/feed autodiscovery, the venue/artist's own
`og:image`, and the YouTube/Spotify/Vimeo embeds the page itself hosts — plus a
classifier that sorts a bio-hub's outbound links (Linktree/Beacons/etc.) into the
existing source pathway kinds.

DISCIPLINE (mirrors worker/importers/socrata.py):
  * PURE + stdlib-only (html.parser/json/urllib). NO network — fetching happens
    upstream in the pipeline (where egress works); this is the unit-testable
    parse step. Tests feed inline HTML.
  * NON-FABRICATING — an absent signal is empty/None, never invented.
  * OWN-DOMAIN GUARD on og:image — an image is only returned as the entity's own
    when it is served from the same registrable domain as the page (legal
    posture: a first party's own asset, not a hotlinked third-party image;
    ONE_LIVE_VERIFIED_PREVIEW_ENRICHMENT_v1.md §6.2).

This module WRITES nothing and makes no trust decision. Everything it surfaces is
a candidate signal that still flows through resolution + the corroboration gate
(publication is gate-custodied — AI output publishes only through the gate).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urljoin, urlparse

_log = logging.getLogger(__name__)

# Hosts that identify a link's PATHWAY KIND (research 2026-08-01: classify a bio
# hub's outbound links so we can resolve an entity to its OWN calendar/newsletter
# /socials/streaming). Matched on the registrable-ish host suffix, case-folded.
_LINK_KINDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("link_hub", ("linktr.ee", "beacons.ai", "linkin.bio", "lnk.bio", "bio.link", "hoo.be", "solo.to", "campsite.bio")),
    ("newsletter", ("substack.com", "mailchi.mp", "list-manage.com", "beehiiv.com", "buttondown.email", "ghost.io")),
    ("streaming", ("spotify.com", "music.apple.com", "youtube.com", "youtu.be", "bandcamp.com", "soundcloud.com", "tidal.com")),
    ("ticketing", ("bandsintown.com", "songkick.com", "dice.fm", "eventbrite.com", "seatgeek.com", "ticketmaster.com", "seated.com", "axs.com", "wl.seetickets.us")),
    ("social", ("instagram.com", "tiktok.com", "twitter.com", "x.com", "facebook.com", "threads.net", "youtube.com/@")),
)

_EMBED_PROVIDERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("youtube", ("youtube.com/embed", "youtube-nocookie.com/embed", "youtu.be")),
    ("spotify", ("open.spotify.com/embed", "spotify.com/embed")),
    ("vimeo", ("player.vimeo.com/video", "vimeo.com/video")),
)

_FEED_TYPES = {
    "application/rss+xml",
    "application/atom+xml",
    "application/feed+json",
    "application/json+feed",
}


@dataclass
class Embed:
    provider: str
    url: str


@dataclass
class FirstParty:
    """Everything a first-party page published for machine consumption."""
    jsonld: list = field(default_factory=list)          # parsed JSON-LD objects
    same_as: list[str] = field(default_factory=list)     # official-channel URLs
    og_image: Optional[str] = None                       # own-domain og:image only
    oembed: list[str] = field(default_factory=list)      # oEmbed discovery hrefs
    feeds: list[str] = field(default_factory=list)       # RSS/Atom/JSON feeds
    websub_hubs: list[str] = field(default_factory=list)  # <link rel="hub"> (push)
    hosted_embeds: list[Embed] = field(default_factory=list)  # yt/spotify/vimeo iframes
    outbound_links: list[str] = field(default_factory=list)   # external <a href> (bio hub)


def _reg_domain(host: str) -> str:
    """Registrable-ish domain = last two labels (e.g. mohawk.austin.com -> austin.com).
    A deliberate simplification: it does not consult the Public Suffix List, so a
    multi-part TLD (foo.co.uk) is approximated by its last two labels. Adequate for
    the .com/.org/.net US venue/artist domains this targets; a same-host match is
    always accepted first so subdomains of the exact page host never fail.
    """
    host = (host or "").lower().strip().lstrip(".")
    labels = [x for x in host.split(".") if x]
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def _same_site(url: str, base: str) -> bool:
    try:
        uh = urlparse(url).hostname or ""
        bh = urlparse(base).hostname or ""
    except ValueError:
        return False
    if not uh or not bh:
        return False
    uh, bh = uh.lower(), bh.lower()
    return uh == bh or _reg_domain(uh) == _reg_domain(bh)


def _http(url: str) -> Optional[str]:
    """Absolute http(s) URL or None — a `javascript:`/`data:`/relative-unresolved
    value never escapes as a link."""
    try:
        p = urlparse(url)
    except ValueError:
        return None
    return url if p.scheme in ("http", "https") and p.hostname else None


def classify_link(url: str) -> str:
    """Sort an outbound link into a source pathway kind (link_hub / newsletter /
    streaming / ticketing / social) or 'own_site' when it matches none — the
    entity's own domain is the highest-authority target. Non-http → 'other'."""
    safe = _http(url)
    if not safe:
        return "other"
    host = (urlparse(safe).hostname or "").lower().lstrip("www.")
    path = (urlparse(safe).path or "").lower()
    hp = host + path
    for kind, needles in _LINK_KINDS:
        if any(n in hp for n in needles):
            return kind
    return "own_site"


def _embed_for(src: str) -> Optional[Embed]:
    low = src.lower()
    for provider, needles in _EMBED_PROVIDERS:
        if any(n in low for n in needles):
            return Embed(provider=provider, url=src)
    return None


class _Parser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.out = FirstParty()
        self._in_ldjson = False
        self._ld_buf: list[str] = []

    # -- structured data + head links -------------------------------------------
    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "script" and a.get("type", "").strip().lower() == "application/ld+json":
            self._in_ldjson = True
            self._ld_buf = []
            return
        if tag == "meta":
            prop = (a.get("property") or a.get("name") or "").strip().lower()
            if prop in ("og:image", "og:image:url", "twitter:image"):
                img = _http(urljoin(self.base, a.get("content", "")))
                # OWN-DOMAIN guard (see module docstring / spec §6.2).
                if img and self.out.og_image is None and _same_site(img, self.base):
                    self.out.og_image = img
            return
        if tag == "link":
            rel = (a.get("rel") or "").strip().lower()
            typ = (a.get("type") or "").strip().lower()
            href = _http(urljoin(self.base, a.get("href", "")))
            if not href:
                return
            if typ in _FEED_TYPES:
                self.out.feeds.append(href)
            if typ in ("application/json+oembed", "text/xml+oembed"):
                self.out.oembed.append(href)
            if "hub" in rel.split():
                self.out.websub_hubs.append(href)
            # rel="me" is the IndieWeb "this is also me" official-channel signal.
            if "me" in rel.split():
                self.out.same_as.append(href)
            return
        if tag == "iframe":
            src = _http(urljoin(self.base, a.get("src", "")))
            if src:
                emb = _embed_for(src)
                if emb:
                    self.out.hosted_embeds.append(emb)
            return
        if tag == "a":
            href = _http(urljoin(self.base, a.get("href", "")))
            # Outbound = a different site than the page itself (bio-hub links).
            if href and not _same_site(href, self.base):
                self.out.outbound_links.append(href)

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ldjson:
            self._in_ldjson = False
            raw = "".join(self._ld_buf).strip()
            self._ld_buf = []
            if not raw:
                return
            try:
                data = json.loads(raw)
            except (ValueError, TypeError):
                return  # a malformed JSON-LD block is skipped, never guessed
            for obj in data if isinstance(data, list) else [data]:
                if isinstance(obj, dict):
                    self.out.jsonld.append(obj)
                    self._collect_same_as(obj)

    def handle_data(self, data):
        if self._in_ldjson:
            self._ld_buf.append(data)

    def _collect_same_as(self, obj: dict):
        sa = obj.get("sameAs")
        if isinstance(sa, str):
            h = _http(sa)
            if h:
                self.out.same_as.append(h)
        elif isinstance(sa, list):
            for item in sa:
                if isinstance(item, str):
                    h = _http(item)
                    if h:
                        self.out.same_as.append(h)


def _dedupe(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def extract_first_party(html: str, url: str) -> FirstParty:
    """Parse a first-party page into its published machine-readable signals.
    `url` is the page's own URL (used to resolve relative links and to enforce the
    own-domain og:image guard). Pure; never fetches; never raises on messy HTML."""
    p = _Parser(url)
    try:
        p.feed(html or "")
    except Exception as exc:
        # A pathological document must degrade to whatever parsed, never crash the
        # enrichment pass (loud failures belong to the fetch layer, not the parser).
        # Logged, not swallowed (OPERATING_RULES §1): the partial result is still
        # returned below, but the parse anomaly is recorded for observability.
        _log.warning("first_party: HTML parse degraded for %s: %s", url, exc)
    fp = p.out
    fp.same_as = _dedupe(fp.same_as)
    fp.feeds = _dedupe(fp.feeds)
    fp.oembed = _dedupe(fp.oembed)
    fp.websub_hubs = _dedupe(fp.websub_hubs)
    fp.outbound_links = _dedupe(fp.outbound_links)
    # De-dupe embeds by url while preserving order.
    seen: set[str] = set()
    fp.hosted_embeds = [e for e in fp.hosted_embeds if not (e.url in seen or seen.add(e.url))]
    return fp
