"""Same-site event-page discovery — the click a homepage-only ingest never makes.

Coverage Law puts class B ("public HTML, loads without login") in scope in any
locale, and the ingest path already fetches each source's registered start URL.
That start URL is almost always a HOMEPAGE, and a venue's homepage is marketing
copy: the schedule lives one click away, at the link the site itself labels
"Events", "Calendar", "Shows". Reading the homepage and stopping is reading the
door and calling it the building.

This module answers ONE question, offline and deterministically: given HTML we
have ALREADY fetched from a start URL, which SAME-SITE pages does this site
itself advertise as its events/calendar/shows pages? It returns URLs and the
evidence for each; it fetches nothing, writes nothing, and decides nothing about
trust. The caller (tools/class_b_multipage.py) does the fetching, under the
existing wall rules.

Three independent signals, all read off the page's own markup — never invented:

  1. LINK TEXT     an <a> whose visible text is the site's own word for its
                   schedule ("Events", "Upcoming Shows", "What's On").
  2. LINK PATH     an <a> whose URL path carries an event token (/events,
                   /calendar/2026-09, /shows/upcoming).
  3. COMMON PATHS  the handful of conventional locations (/events, /calendar,
                   /shows, …) offered as CANDIDATES when the page links to
                   none of them. These are guesses about a URL, never guesses
                   about an event: a 404 costs one HEAD-shaped GET and is
                   reported as a miss.

ICS and JSON-LD are read too, but NOT by a second implementation — the
authorities are worker/importers/structured_feed.py (discover_ics_links,
parse_jsonld), already used by the structured import. Two copies of "find the
calendar feed" would drift in exactly the direction that costs coverage.

WHAT THIS MODULE REFUSES TO DO, structurally:

  * Leave the site. Only same-site links survive (same host, or a host that
    differs from the start URL's only by a leading "www."). An off-site link is
    a DIFFERENT source with its own catalog row, its own class, and its own
    access posture — following it here would ingest a source nobody classified.
  * Walk into a wall. Any URL that looks like a sign-in surface is dropped here,
    before the caller can fetch it, using the SAME marker list the claim intake
    and the class-D demotion use (source_class.looks_like_login_url). Coverage
    Law: no login/paywall/bot-protection bypass, ever.
  * Grow without a bound. Every result set is capped; the cap is a parameter
    with a documented default, and the caller's per-run budget is separate.

Pure/deterministic, stdlib-only (no network, no DB, no AI) → unit-testable, and
the same input always yields the same ordered output.
"""
from __future__ import annotations

import logging
import re
import urllib.parse
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, List, Optional, Sequence, Tuple

from worker.sourcing.source_class import looks_like_login_url

log = logging.getLogger(__name__)

#: Default ceiling on pages discovered for ONE source. The founder's session
#: budget ("cap 15 extra pages per source per run") is the number; it lives here
#: as a default so a caller that forgets to pass one still gets a bound, and
#: fail-closed validation lives in the caller's CLI.
DEFAULT_MAX_PAGES = 15

#: Ceiling on how many COMMON-PATH guesses one start page may contribute. The
#: guesses are the weakest signal in the module — nothing on the page pointed at
#: them — so they get the smallest share of the budget, and a site that links its
#: own calendar never spends the budget on 404s. Politeness is the other half:
#: without this, a start page with no event links would send a dozen misses at
#: every venue on every run.
DEFAULT_MAX_COMMON_PATH_GUESSES = 6

# --- The site's own vocabulary for "here is our schedule" ---------------------
#
# Matched as whole words against link TEXT (lower-cased, punctuation folded to
# spaces) and against URL PATH segments. Deliberately broad: over-triggering
# costs one capped fetch of a page the site chose to label "Events"; UNDER-
# triggering costs the entire schedule of that venue, silently. Multi-word
# entries are matched as adjacent words so "live music" hits and "live" alone
# still hits on its own row.
_EVENT_WORDS: Tuple[str, ...] = (
    "event", "events",
    "calendar", "calendars",
    "show", "shows",
    "schedule", "schedules",
    "lineup", "lineups",
    "upcoming",
    "gig", "gigs",
    "concert", "concerts",
    "agenda",
    "performance", "performances",
    "programme", "programmes", "program", "programs",
    "listing", "listings",
    "tour", "tours",
    "whatson",
    "happening", "happenings",
    "exhibition", "exhibitions",
    "screening", "screenings",
)

#: Multi-word phrases a site uses for the same thing. Checked against the
#: normalized link text as a substring of the space-joined word sequence, so
#: "What's On" (apostrophe folded) and "Live Music" both hit.
_EVENT_PHRASES: Tuple[str, ...] = (
    "what s on", "whats on", "what is on",
    "live music", "on stage", "tour dates", "book tickets",
    "this week", "this month", "coming up", "now playing",
)

#: The conventional URL locations, tried ONLY as candidates when the page's own
#: markup offers nothing (or offers less than the cap). Ordered by how often a
#: real venue site uses them, so a truncated list keeps the likeliest first.
COMMON_EVENT_PATHS: Tuple[str, ...] = (
    "/events",
    "/calendar",
    "/shows",
    "/schedule",
    "/upcoming",
    "/whats-on",
    "/live",
    "/lineup",
    "/events/calendar",
    "/tour",
    "/concerts",
    "/programme",
)

#: Extensions that are files, not pages. A .ics is not excluded as "junk" — it
#: is routed to the ICS bucket by the authority in structured_feed, so it must
#: not also enter the page list and be fetched twice.
_NON_PAGE_SUFFIXES: Tuple[str, ...] = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".avif",
    ".zip", ".gz", ".tar", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".mp3", ".mp4", ".mov", ".avi", ".wav", ".m4a", ".css", ".js", ".ics",
    ".rss", ".xml", ".json", ".txt",
)

#: Non-page URL schemes an anchor may legitimately carry.
_NON_HTTP_SCHEMES = ("mailto:", "tel:", "sms:", "javascript:", "data:", "file:")

# Reasons a candidate was dropped, as constants so the caller's report and the
# tests name the same string (a reason typo must not read as a new reason).
SKIP_OFF_SITE = "off-site (different host — a separate source with its own class)"
SKIP_LOGIN = "sign-in surface (Coverage Law: never fetch a wall)"
SKIP_NOT_A_PAGE = "not an HTML page (file asset or feed)"
SKIP_BAD_SCHEME = "not an http(s) URL"
SKIP_SELF = "the start URL itself (already fetched)"

#: Why a page made the list. Reported per page so a human reading the run table
#: can see whether the site TOLD us (link/path) or we GUESSED the location.
VIA_LINK_TEXT = "link text"
VIA_LINK_PATH = "url path"
VIA_COMMON_PATH = "common path (guess)"


@dataclass(frozen=True)
class DiscoveredPage:
    """One same-site page worth fetching, plus the evidence that chose it."""

    url: str
    via: str
    evidence: str


@dataclass
class DiscoveryResult:
    """Everything one start page told us, and everything we refused."""

    start_url: str
    pages: List[DiscoveredPage] = field(default_factory=list)
    ics_links: List[str] = field(default_factory=list)
    jsonld_events: int = 0
    skipped: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def page_urls(self) -> List[str]:
        return [p.url for p in self.pages]

    def skipped_reason_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for _url, reason in self.skipped:
            counts[reason] = counts.get(reason, 0) + 1
        return counts


class _AnchorExtractor(HTMLParser):
    """Collect (href, visible text) for every <a href> in document order.

    Text is accumulated between <a> and </a>, including text inside nested
    inline elements (a <span> inside the link is still the link's label). An
    unclosed <a> at end of document still yields its accumulated text — a
    malformed page must not silently lose the one link we came for.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: List[Tuple[str, str]] = []
        self._depth = 0
        self._href: Optional[str] = None
        self._text: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        if self._depth:
            # Nested <a> is invalid HTML; close the outer one honestly rather
            # than merging two labels into one.
            self._flush()
        attr = {k.lower(): (v or "") for k, v in attrs}
        href = attr.get("href", "").strip()
        if not href:
            return
        # An aria-label/title is the accessible name when the visible text is an
        # icon — a real pattern on venue sites ("🎫" linking to /events).
        self._href = href
        self._text = []
        label = attr.get("aria-label") or attr.get("title")
        if label:
            self._text.append(label)
        self._depth = 1

    def handle_data(self, data: str) -> None:
        if self._depth:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._depth:
            self._flush()

    def close(self) -> None:  # pragma: no cover - exercised via feed/close
        super().close()
        self._flush()

    def _flush(self) -> None:
        if self._href is not None:
            self.anchors.append((self._href, " ".join(self._text)))
        self._href = None
        self._text = []
        self._depth = 0


_WORD_SPLIT = re.compile(r"[^a-z0-9]+")


def _normalize_words(value: str) -> List[str]:
    """Lower-case, punctuation-folded word list — the matching surface for both
    link text and URL paths, so "What's On", "whats-on" and "/whats_on" all
    reduce to the same tokens."""
    return [w for w in _WORD_SPLIT.split((value or "").lower()) if w]


def _site_host(host: str) -> str:
    """Host key for the same-site test: lower-cased, one leading "www." removed.

    Why "www." is folded and nothing else is: `example.com` and `www.example.com`
    are the same publisher serving the same calendar, and venue sites link
    between the two constantly. Any OTHER host — a subdomain, a ticketing
    vendor, a CDN — is a different source that needs its own catalog row and its
    own access classification, so it is refused here rather than followed.
    """
    host = (host or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _normalize_url(absolute: str) -> str:
    """Canonical form for de-duplication: fragment dropped, host lower-cased, a
    trailing slash removed from a non-root path. Query is PRESERVED — a
    calendar's ?month=2026-09 is a different page, not noise."""
    parts = urllib.parse.urlsplit(absolute)
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return urllib.parse.urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, parts.query, "")
    )


def _looks_like_page(path: str) -> bool:
    lowered = path.lower()
    return not lowered.endswith(_NON_PAGE_SUFFIXES)


def _text_match(text: str) -> Optional[str]:
    """Return the deciding token when link TEXT names a schedule, else None."""
    words = _normalize_words(text)
    if not words:
        return None
    joined = " ".join(words)
    for phrase in _EVENT_PHRASES:
        if phrase in joined:
            return phrase
    wordset = set(words)
    for word in _EVENT_WORDS:
        if word in wordset:
            return word
    return None


def _path_match(path: str) -> Optional[str]:
    """Return the deciding token when the URL PATH names a schedule, else None."""
    words = set(_normalize_words(path))
    if not words:
        return None
    for word in _EVENT_WORDS:
        if word in words:
            return word
    # "whats-on" splits to {"whats", "on"}; check the joined form too.
    joined = " ".join(_normalize_words(path))
    for phrase in _EVENT_PHRASES:
        if phrase in joined:
            return phrase
    return None


def _classify_href(href: str, start_url: str) -> Tuple[Optional[str], Optional[str]]:
    """Resolve one href against the start URL.

    Returns (normalized_absolute_url, skip_reason). Exactly one is non-None:
    a URL we may consider, or the reason we refused it. Refusals are RETURNED,
    never swallowed, so the caller's report can count them.
    """
    href = (href or "").strip()
    if not href or href.startswith("#"):
        return None, SKIP_BAD_SCHEME
    lowered = href.lower()
    if lowered.startswith(_NON_HTTP_SCHEMES):
        return None, SKIP_BAD_SCHEME

    absolute = urllib.parse.urljoin(start_url, href)
    parts = urllib.parse.urlsplit(absolute)
    if parts.scheme.lower() not in ("http", "https"):
        return None, SKIP_BAD_SCHEME
    if _site_host(parts.hostname or "") != _site_host(
        urllib.parse.urlsplit(start_url).hostname or ""
    ):
        return None, SKIP_OFF_SITE
    if looks_like_login_url(absolute):
        return None, SKIP_LOGIN
    if not _looks_like_page(parts.path or "/"):
        return None, SKIP_NOT_A_PAGE

    normalized = _normalize_url(absolute)
    if normalized == _normalize_url(start_url):
        return None, SKIP_SELF
    return normalized, None


def same_site(url: str, other: str) -> bool:
    """True when two URLs belong to the same site (host equal, ignoring a
    leading "www.").

    Public because the on-origin rule has to be enforced TWICE and by one
    definition: once here, dropping off-site links before the fetcher is
    offered them, and once by the caller on the fetch's FINAL url, because a
    same-origin link may answer 200 from somewhere else entirely. Two copies
    of "same site?" would drift in exactly the direction that lets an
    off-origin page be ingested as a venue's own.

    A URL with no host is never the same site as anything — fail closed.
    """
    a = urllib.parse.urlsplit(url or "")
    b = urllib.parse.urlsplit(other or "")
    if not a.netloc or not b.netloc:
        return False
    return _site_host(a.netloc) == _site_host(b.netloc)


def common_path_candidates(start_url: str, paths: Sequence[str] = COMMON_EVENT_PATHS) -> List[str]:
    """The conventional event-page URLs for a site, normalized and de-duplicated.

    Built against the start URL's ORIGIN (scheme + host), not its path: a source
    registered at https://venue.com/austin still keeps its calendar at
    https://venue.com/events far more often than at /austin/events, and the
    origin form is the one a site's own nav uses.
    """
    parts = urllib.parse.urlsplit(start_url)
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        return []
    origin = f"{parts.scheme.lower()}://{parts.netloc.lower()}"
    out: List[str] = []
    seen = set()
    for path in paths:
        candidate = _normalize_url(urllib.parse.urljoin(origin, path))
        if candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
    return out


def discover_event_pages(
    html: str,
    start_url: str,
    *,
    limit: int = DEFAULT_MAX_PAGES,
    include_common_paths: bool = True,
    max_common_path_guesses: int = DEFAULT_MAX_COMMON_PATH_GUESSES,
) -> DiscoveryResult:
    """Find the same-site event/calendar/shows pages this page advertises.

    Ordering is deterministic and evidence-ranked, because the cap will bite on
    a large site and WHICH pages survive the cap matters:

      1. links whose visible TEXT names a schedule (the site's own label — the
         strongest signal a human would follow),
      2. links whose URL PATH names one,
      3. conventional COMMON PATHS not already present (guesses, last).

    Within a tier, document order — stable, and it matches how a site orders its
    own nav (primary calendar first).

    `limit` <= 0 returns no pages (a ceiling of 0 means no run, never uncapped —
    the project-wide budget rule); ICS/JSON-LD signals are still reported, since
    reading them costs no fetch. `max_common_path_guesses` bounds tier 3
    separately, so a site that links nothing still costs a handful of 404s
    rather than the whole page budget.
    """
    result = DiscoveryResult(start_url=start_url)

    parser = _AnchorExtractor()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception as exc:  # noqa: BLE001 — a malformed page must not crash discovery
        # html.parser is lenient; if a pathological page still raises we keep the
        # anchors collected so far and say so LOUDLY. An empty result is the
        # honest outcome of an unparseable page — a crash would lose the source.
        log.warning(
            "event-page discovery: HTML parse raised for %s (%s); using the %d "
            "anchor(s) collected before the error.",
            start_url, exc, len(parser.anchors),
        )

    by_text: List[DiscoveredPage] = []
    by_path: List[DiscoveredPage] = []
    seen: set = set()

    for href, text in parser.anchors:
        normalized, skip_reason = _classify_href(href, start_url)
        if normalized is None:
            # SKIP_SELF and SKIP_BAD_SCHEME fire on ordinary nav noise (the home
            # link, "#main"); only the decision-bearing refusals are reported,
            # so the run table's blocked column stays readable.
            if skip_reason in (SKIP_OFF_SITE, SKIP_LOGIN, SKIP_NOT_A_PAGE):
                token = _text_match(text) or _path_match(
                    urllib.parse.urlsplit(urllib.parse.urljoin(start_url, href)).path
                )
                if token:
                    result.skipped.append((urllib.parse.urljoin(start_url, href), skip_reason))
            continue
        if normalized in seen:
            continue

        token = _text_match(text)
        if token:
            seen.add(normalized)
            by_text.append(DiscoveredPage(
                url=normalized, via=VIA_LINK_TEXT,
                evidence=f"link text {' '.join(_normalize_words(text))!r} matches {token!r}",
            ))
            continue

        path = urllib.parse.urlsplit(normalized).path
        token = _path_match(path)
        if token:
            seen.add(normalized)
            by_path.append(DiscoveredPage(
                url=normalized, via=VIA_LINK_PATH,
                evidence=f"url path {path!r} matches {token!r}",
            ))

    ranked: List[DiscoveredPage] = [*by_text, *by_path]

    if include_common_paths and max_common_path_guesses > 0:
        guesses = 0
        for candidate in common_path_candidates(start_url):
            if guesses >= max_common_path_guesses:
                break
            if candidate in seen or candidate == _normalize_url(start_url):
                continue
            seen.add(candidate)
            guesses += 1
            ranked.append(DiscoveredPage(
                url=candidate, via=VIA_COMMON_PATH,
                evidence="conventional event-page location; not linked from the "
                         "start page, so a miss here is a 404, not a lost event",
            ))

    result.pages = ranked[:limit] if limit > 0 else []

    # ICS + JSON-LD read through the EXISTING authorities, never a second copy.
    # Imported lazily so this module stays importable (and unit-testable) even
    # if the importer package grows a heavier dependency later.
    try:
        from worker.importers.structured_feed import discover_ics_links, parse_jsonld

        result.ics_links = discover_ics_links(html or "", start_url, limit=5)
        result.jsonld_events = len(parse_jsonld(html or ""))
    except Exception as exc:  # noqa: BLE001 — a structured-signal failure never kills page discovery
        log.warning(
            "event-page discovery: structured-signal read failed for %s (%s); "
            "page links are unaffected.", start_url, exc,
        )

    return result
