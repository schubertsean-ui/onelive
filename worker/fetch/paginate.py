"""Next-page discovery for paginated calendars — founder-directed 2026-08-05.

Founder, verbatim: "build multi-page ingestion next. It's the single biggest
lever left". The proving case is the Austin Chronicle calendar: 2,362 events
across 60 pages, of which a single-page fetch reads roughly forty.

What this module does: given a fetched calendar page, find the SOURCE'S OWN
"next page" link. It reads the page's own navigation — it never constructs,
guesses, or increments a URL the source did not publish (the same
source-authoritative doctrine the date callback follows: decision record
docs/memory/decisions/2026-08-05_source-site-authoritative.md).

Bounds that make this safe to run against every source:
  - SAME ORIGIN only: a "next" link pointing off-site is not this calendar's
    next page and is refused.
  - Loop-proof: the caller tracks visited URLs; this module also refuses a
    next-link equal to the page it came from.
  - No query-guessing: `?page=N+1` is only used when the page itself
    published that link.

Why following pages from the FRONT is the right depth policy: calendar pages
are date-ordered, so page 1 carries the soonest events — exactly what a
"tonight" product needs. Events deeper in the calendar rise toward page 1 as
their date approaches, so a bounded front-following crawl reaches everything
eventually without ever fetching sixty pages in one run.
"""
from __future__ import annotations

import logging
import re
from typing import Optional, Set
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

# <link rel="next"> / <a rel="next"> — the explicit, standards-blessed signal.
_REL_NEXT_RE = re.compile(
    r"""<(?:a|link)\b[^>]*\brel\s*=\s*["']?[^"'>]*\bnext\b[^"'>]*["']?[^>]*>""",
    re.I)
_HREF_RE = re.compile(r"""\bhref\s*=\s*["']([^"']+)["']""", re.I)

# An anchor whose visible text is a next-page affordance. Deliberately narrow:
# "next", "next page", "next ›", "older" (common on event calendars). Matching
# is on the anchor's TEXT, so a link merely containing the word elsewhere on
# the page is not mistaken for pagination.
_NEXT_ANCHOR_RE = re.compile(
    r"""<a\b([^>]*)>(?P<text>(?:(?!</a>).){0,120})</a>""", re.I | re.S)
_NEXT_TEXT_RE = re.compile(
    r"^\s*(?:next(?:\s+page)?|older(?:\s+events)?)\s*[›»→>]*\s*$", re.I)
_TAGS_RE = re.compile(r"<[^>]+>")


def _same_origin(a: str, b: str) -> bool:
    """True when two URLs share scheme+host+port (a calendar's own pages)."""
    try:
        pa, pb = urlparse(a), urlparse(b)
    except ValueError:
        return False
    return (pa.scheme, pa.hostname, pa.port) == (pb.scheme, pb.hostname, pb.port)


def canonical(url: str) -> str:
    """The comparison key for "have we already read this page?".

    Adversarial pre-review catch (2026-08-05): the visited check compared raw
    strings, so two spellings of ONE page counted as two pages and the walk
    ping-ponged between them. Two spellings occur constantly in the wild:

      - `<a href="#page-2">Next</a>` — an ordinary client-side pagination
        control. urljoin turns it into "<current page>#page-2", which is not
        string-equal to the current URL, so page 1 was fetched a second time.
        (A bare `href="#"` was already refused, because urljoin drops an empty
        fragment — a near-miss, which is why this went unnoticed.)
      - A next-link written with a different host case, which passes the
        origin check (urlparse lowercases .hostname) and then re-enters.

    The cost was not cosmetic: the duplicated page text segments into
    duplicate blocks, which consume the per-run extraction budget (pushing
    real events out of the run) and land as duplicate candidates, which the
    gate reads as a same-venue/same-time conflict and ESCALATEs — events that
    would have published instead stall in review.

    The fragment is dropped because it never identifies a different DOCUMENT,
    only a position within one. Host and scheme are lowercased because they
    are case-insensitive by RFC 3986. Everything else — path, query, port — is
    left exactly as published, since those DO distinguish pages.
    """
    try:
        p = urlparse(url)
    except ValueError:
        return url
    netloc = p.netloc.lower()
    path = p.path or "/"
    q = f"?{p.query}" if p.query else ""
    return f"{p.scheme.lower()}://{netloc}{path}{q}"


def _admissible(candidate: str, current_url: str, seen: Set[str]) -> bool:
    """A usable next page: http(s), same origin, not already visited.

    `seen` is compared on canonical() keys, so an alternate spelling of a page
    we have already read is refused. The caller fetches the URL as published.
    """
    if not candidate:
        return False
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if not _same_origin(candidate, current_url):
        return False
    key = canonical(candidate)
    return key not in {canonical(s) for s in seen} and key != canonical(current_url)


def discover_next_page(html: str, current_url: str,
                       seen: Optional[Set[str]] = None) -> Optional[str]:
    """The source's OWN next-page URL, or None.

    Order of trust: an explicit rel="next" first (the source stating it
    outright), then an anchor whose visible text is a next-page affordance.
    Returns an absolute URL, resolved against ``current_url``.
    """
    if not html:
        return None
    visited = seen or set()

    for m in _REL_NEXT_RE.finditer(html):
        href = _HREF_RE.search(m.group(0))
        if not href:
            continue
        candidate = urljoin(current_url, href.group(1).strip())
        if _admissible(candidate, current_url, visited):
            return candidate

    for m in _NEXT_ANCHOR_RE.finditer(html):
        text = _TAGS_RE.sub("", m.group("text") or "")
        text = text.replace("&nbsp;", " ").replace("&gt;", ">").replace("&rsaquo;", "›")
        if not _NEXT_TEXT_RE.match(text):
            continue
        href = _HREF_RE.search(m.group(1) or "")
        if not href:
            continue
        candidate = urljoin(current_url, href.group(1).strip())
        if _admissible(candidate, current_url, visited):
            return candidate

    return None
