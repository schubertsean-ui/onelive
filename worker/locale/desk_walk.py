"""walk(public_desk) — a desk's WHOLE public list, page by page, holes and all.

Founder, this session's ticket: "Paginate until the public list is exhausted (or
write blocked_reason per page). No login."

`read()` (worker/locale/desk_read.py) turns ONE page into happening rows. A
desk's list is many pages, and page 2 onward is simply absent from the store
until something follows it — an unpaginated read looks green while capping
coverage at whatever the first page happened to hold, which the Coverage Law
calls a defect, not a limitation.

Four rules hold this to what the desk itself published:

  * THE NEXT PAGE IS THE DESK'S OWN LINK. A next URL comes from markup the page
    states — `<link rel="next">`, an anchor carrying `rel="next"`, or an anchor
    whose own text or aria-label says it is the next page. We never SYNTHESISE
    a page address by incrementing somebody's query parameter: a made-up URL is
    a guess about a stranger's routing, and the 404 (or the wrong page) it
    returns would be recorded as their coverage.
  * A WALL ENDS THE WALK. 401/402/403/407/429 or a redirect onto a sign-in page
    is class D through the SAME authority the ingest loop uses
    (`worker.sourcing.source_class.demote_on_response`). We knock once. There is
    no login, no retry, no work-around — the page gets a `blocked_reason` and
    the walk stops there with everything read so far intact.
  * SAME HOST, NO CYCLES, HARD CAP. A next link that leaves the desk's host is
    not that desk's next page; a link back to a page already visited is a
    carousel, not a list; and a list that never ends is bounded by `max_pages`.
    Every one of those is REPORTED (`stopped_because`) so it can never be
    mistaken for an exhausted desk — including the refusal, which stops on
    `next_link_not_followed`: the page stated a next page, WE declined it, and
    saying "no next link" there would put our refusal on the desk's account.
  * NOTHING FAILS SILENTLY. Every page visited becomes a `PageVisit` row with
    its status, its row count and its `blocked_reason` — the founder's per-page
    column. A page that yields nothing is a page that yielded nothing, never an
    absent row in the table. And a list that continues behind a control we
    cannot follow (a "Load more" button, an `href="#"` anchor) stops on
    `next_control_not_a_link`, never on `no_next_link`: the one is a floor, the
    other claims a whole desk.

Cross-page duplicates are collapsed on the row's OWN identity when it stated one
(its listing URL), else on title + the date the page stated. Both numbers are
kept: `count` (unique happenings) and `rows_seen` (before de-duplication), so
pagination can neither inflate coverage with repeats nor hide a shrinking list.

Pure: stdlib only plus this repo's own readers. No network, no DB, no clock, no
model. The caller injects `fetch`; this module decides only what to ask for next
and what the answer means.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Callable, List, Optional, Sequence, Tuple
from urllib.parse import urldefrag, urljoin, urlsplit

from worker.locale.desk_read import DeskReadError, Happening, fill_holes, read, row_key
from worker.locale.identity_patterns import IdentityPattern
from worker.locale.kind_map import KindMap
from worker.locale.pack import Door
from worker.sourcing.source_class import ClassVerdict, demote_on_response

log = logging.getLogger(__name__)

#: How many pages one walk may open. A desk with more says so
#: (`stopped_because="max_pages"`) instead of being silently truncated.
DEFAULT_MAX_PAGES = 40

#: The class a pack-declared public door starts from, before the desk answers.
#: Stated here rather than assumed downstream, so the demotion below has
#: something explicit to demote FROM.
DECLARED_PUBLIC = ClassVerdict("B", "declared public in the locale pack", fetchable=True)

#: Link text (normalised) that means "the next page of this list". Matched on
#: the whole normalised text, never on a substring, so "Next Wednesday" in a
#: listing title is not a pagination control.
NEXT_TEXTS = frozenset({
    "next", "next page", "next »", "next >", "next ›", "next 〉",
    "»", "›", ">", "older", "older posts", "more", "more results", "show more",
    "next results", "load more",
})

#: Substrings that make an aria-label a next-page control. An aria-label is
#: written for a screen reader — it says what the control does.
NEXT_ARIA = ("next page", "next results", "go to next", "next set")

_WS_RE = re.compile(r"\s+")
_REL_SPLIT_RE = re.compile(r"[\s,]+")
#: Status codes that mean a wall, read out of a blocked page's REASON text for
#: the case where there is no HTTP status to read: a proxy CONNECT denial
#: ("Tunnel connection failed: 403 Forbidden") is a wall between us and the
#: desk, and counting it as an ordinary error would print `403_n = 0` for a
#: desk nobody could reach.
_WALL_CODE_RE = re.compile(r"\b(?:401|402|403|407|429)\b")


class DeskWalkError(ValueError):
    """The walk cannot start: a door that may not be read, or a fetcher that
    does not answer with something this module can classify. Raised, never
    downgraded to an empty walk that would read as an empty desk.
    """


@dataclass(frozen=True)
class PageFetch:
    """One page as the caller's fetcher saw it.

    `status` is the HTTP status when there was one; `error` carries a transport
    failure text when there was not. `final_url` is where the fetch LANDED after
    redirects — the value the wall test reads, since a redirect onto a sign-in
    page is how a login wall usually announces itself.
    """

    url: str
    status: Optional[int] = None
    body: Optional[str] = None
    final_url: Optional[str] = None
    error: Optional[str] = None
    #: The fetcher's own answer to "was this a wall?", for the case its `error`
    #: text cannot carry it: a transport failure is truncated for display, and
    #: whether "403" survives that truncation depends on how long the URL was.
    #: The walk still classifies the error text itself, so a fetcher that never
    #: sets this loses nothing; it can only ever ADD a wall, never hide one.
    walled: bool = False

    @property
    def landed_url(self) -> str:
        return self.final_url or self.url


@dataclass
class PageVisit:
    """One page of the desk's list, and what it gave us."""

    n: int
    url: str
    status: Optional[int] = None
    rows_seen: int = 0            # rows this page printed
    new_rows: int = 0             # rows not already seen on an earlier page
    blocked_reason: Optional[str] = None
    next_url: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    #: Which rung of the split ladder read this page (`DeskRead.identity_tier`).
    #: None when the page was never read at all — a wall, an error, an empty
    #: body — which is a different silence from `unsplit` and is kept apart.
    identity_tier: Optional[str] = None
    #: Rows on this page whose stated address was the LIST's own URL and were
    #: dropped to a hole (ONE-LIVE-ENTITY-SPLIT-LAW.md §2 Forbidden).
    mash_blocked: int = 0
    #: This page hit a WALL — the desk's own 401/402/403/407/429 or 4xx/5xx, a
    #: login redirect, or a proxy CONNECT denial between us and it. Set where
    #: the block is decided, from the FULL error text, because `blocked_reason`
    #: is truncated for display and a counter must never depend on how long a
    #: URL happened to be.
    walled: bool = False

    @property
    def blocked(self) -> bool:
        return self.blocked_reason is not None

    @property
    def unsplit(self) -> bool:
        """The page was read and declared no identity we hold: zero rows, and a
        coverage defect on this door. Never 'the desk had nothing on'."""
        return self.identity_tier == "unsplit"


@dataclass
class DeskWalk:
    """A whole walk: every page visited, every happening, and why it stopped."""

    door_id: str
    door_type: str
    via: Optional[str]
    start_url: str
    pages: List[PageVisit] = field(default_factory=list)
    rows: List[Happening] = field(default_factory=list)
    duplicates_across_pages: int = 0
    #: Second readings of one card merged into the first, summed over pages.
    merged_readings: int = 0
    skipped_untitled: int = 0
    #: Categories the desk stated that the committed mapping does not cover.
    unmapped_categories: List[str] = field(default_factory=list)
    stopped_because: str = "not started"
    notes: List[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Unique happenings across the whole walk."""
        return len(self.rows)

    @property
    def rows_seen(self) -> int:
        """Rows the desk printed, before cross-page de-duplication."""
        return sum(p.rows_seen for p in self.pages)

    @property
    def dated(self) -> int:
        return sum(1 for r in self.rows if r.when)

    @property
    def pages_read(self) -> int:
        return sum(1 for p in self.pages if not p.blocked)

    @property
    def pages_blocked(self) -> int:
        return sum(1 for p in self.pages if p.blocked)

    @property
    def unsplit_n(self) -> int:
        """Pages read that declared no identity. A coverage defect on this door
        (ONE-LIVE-ENTITY-SPLIT-LAW.md §4), answered by a pattern or a claim —
        never by a mashed row, and never printed as an empty desk."""
        return sum(1 for p in self.pages if p.unsplit)

    @property
    def walled_n(self) -> int:
        """Pages that hit a WALL: class D on contact (401/402/403/407/429 or a
        login redirect), any 4xx/5xx the desk answered with, or a proxy CONNECT
        denial between us and it.

        Ours or theirs, the consequence is identical and is the whole point of
        counting it: that page's list is UNKNOWN, never empty (Operating Law,
        effectiveness rule 4 — "403/404 on a start URL is triage, not 'this
        venue has no events'"). Reading the transport error too is deliberate:
        the sandbox's own 403 arrives as a ProxyError with no HTTP status, and a
        wall that shows up as `0` in the 403 column is exactly the number that
        would let a walled desk be reported as an empty calendar.
        """
        return sum(1 for p in self.pages if p.walled)

    @property
    def unread_n(self) -> int:
        """Pages we opened and could not read, for ANY reason — walls included.
        `403_n` is a subset of it, and the gap between them is the pages that
        failed some other way."""
        return sum(1 for p in self.pages if p.blocked)

    @property
    def mash_n(self) -> int:
        """Rows in THIS walk's output whose address is a list URL rather than
        their own. Derived from the rows themselves, never from the guard's
        counter, because "mash_n = 0" is the claim this ticket has to prove.
        """
        starts = {_normalize(p.url) for p in self.pages}
        starts.add(_normalize(self.start_url))
        return sum(1 for r in self.rows
                   if r.listing_url and _normalize(r.listing_url) in starts)

    @property
    def mash_blocked(self) -> int:
        """How many times the reader dropped a list URL off a row. Reported
        beside `mash_n` so a zero there is visibly a REFUSAL, not an absence."""
        return sum(p.mash_blocked for p in self.pages)

    @property
    def identity_tiers(self) -> List[str]:
        """Which rungs split this desk's pages, in first-seen order."""
        out: List[str] = []
        for page in self.pages:
            if page.identity_tier and page.identity_tier not in out:
                out.append(page.identity_tier)
        return out

    @property
    def exhausted(self) -> bool:
        """True only when the desk itself ran out of next links.

        Any other stop — a cap, a wall, a cycle, a next link we refused, a
        continuation control we cannot follow — means the list may go on, and no
        table may call this walk the desk's whole output.
        """
        return self.stopped_because == "no_next_link"


# --------------------------------------------------------------------------
# Next-page discovery — the desk's own links, never a synthesised address
# --------------------------------------------------------------------------

class _LinkScanner(HTMLParser):
    """Collect the page's candidate next-page links, in document order.

    Two tiers, kept apart so the caller can prefer the declared one:
      `rel_next`  — `rel="next"` on a `<link>` or `<a>` (the machine statement)
      `text_next` — an `<a>` whose own text or aria-label says "next"

    Plus a third list that is NOT a tier, because nothing in it can be
    followed: `controls`, the continuation controls a page states as script
    rather than as a link — a `<button>` saying "Load more", an `<a>` with no
    href or with `href="#"`. They are collected precisely so the walk can say
    the list goes on. See `continuation_control`.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rel_next: List[str] = []
        self.text_next: List[str] = []
        self.controls: List[str] = []
        self._open_anchor: Optional[str] = None
        self._open_control: Optional[str] = None
        self._open_control_tag: Optional[str] = None
        self._anchor_text: List[str] = []

    @staticmethod
    def _attrs(attrs) -> dict:
        return {k.lower(): (v or "") for k, v in attrs}

    @staticmethod
    def _is_rel_next(value: str) -> bool:
        return "next" in {t.lower() for t in _REL_SPLIT_RE.split(value or "") if t}

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        a = self._attrs(attrs)
        href = a.get("href", "").strip()
        if tag == "link" and href and self._is_rel_next(a.get("rel", "")):
            self.rel_next.append(href)
            return
        aria = _WS_RE.sub(" ", a.get("aria-label", "").strip().lower())
        says_next = bool(aria) and any(needle in aria for needle in NEXT_ARIA)
        if tag == "button" or (tag == "a" and not _followable(href)):
            if tag == "button" and self._open_anchor is not None:
                # A button inside a link: the LINK is what we could follow, and
                # its text is still being collected. Leave it alone.
                return
            # A control, not a link. Whatever it does, it does in script we do
            # not run — so it can only ever be REPORTED.
            what = f"<{tag}>" + (f' aria-label="{aria}"' if aria else "")
            if says_next:
                self.controls.append(what)
                return
            self._open_control = what
            self._open_control_tag = tag
            self._anchor_text = []
            return
        if tag != "a":
            return
        if self._is_rel_next(a.get("rel", "")):
            self.rel_next.append(href)
            return
        if says_next:
            self.text_next.append(href)
            return
        # Otherwise the anchor's own text decides — collected until </a>.
        self._open_anchor = href
        self._open_control = None
        self._open_control_tag = None
        self._anchor_text = []

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        if self._open_anchor is not None or self._open_control is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag not in ("a", "button"):
            return
        text = _WS_RE.sub(" ", "".join(self._anchor_text)).strip().lower()
        if self._open_control is not None and self._open_control_tag == tag:
            if text in NEXT_TEXTS:
                self.controls.append(f'{self._open_control} "{text}"')
            self._open_control = None
            self._open_control_tag = None
            self._anchor_text = []
            return
        if tag == "a" and self._open_anchor is not None:
            if text in NEXT_TEXTS:
                self.text_next.append(self._open_anchor)
            self._open_anchor = None
            self._anchor_text = []


def _followable(href: str) -> bool:
    """True when this href is something we could actually open.

    An empty href, `href="#"` or `href="javascript:..."` is a hook for script,
    not an address. The distinction matters because such an anchor labelled
    "Load more" is a list that CONTINUES — see `continuation_control`.
    """
    href = (href or "").strip()
    return bool(href) and not href.lower().startswith(("#", "javascript:"))


def continuation_control(html: str) -> Optional[str]:
    """The page's own "there is more" control, when it is not a link — else None.

    Modern list pages often continue behind script: a `<button>Load more</button>`,
    or an `<a href="#">Show more</a>` wired up in JavaScript we do not run. To a
    link-following walker those pages look IDENTICAL to the last page of a list,
    and that is the dangerous part: the walk would stop with `no_next_link`,
    `exhausted` would be True, and a fraction of the desk would be reported as
    the whole desk with no caveat anywhere.

    We still do not follow it — synthesising whatever URL that script would call
    is the guess about a stranger's routing this module refuses everywhere else.
    We REPORT it, which is what makes the stop honest: the walk ends on
    `next_control_not_a_link`, `exhausted` stays False, and every table prints
    its "this is a floor" caveat.
    """
    if not html:
        return None
    scanner = _LinkScanner()
    try:
        scanner.feed(html)
        scanner.close()
    except Exception:  # noqa: BLE001 — a pathological page reports nothing extra
        return None
    return scanner.controls[0] if scanner.controls else None


def _normalize(url: str) -> str:
    """Compare form for the visited set: fragment dropped, nothing else.

    Deliberately conservative — two URLs that differ only in a query parameter
    ORDER are different pages as far as we are concerned, because guessing that
    a desk treats them alike is exactly the kind of assumption that silently
    drops a page.
    """
    return urldefrag(url or "")[0]


def _same_host(candidate: str, current: str) -> bool:
    a, b = urlsplit(candidate), urlsplit(current)
    if not a.netloc:
        return True  # relative link — resolves onto the current host
    return a.netloc.lower() == b.netloc.lower()


def next_page_url(html: str, current_url: str) -> Tuple[Optional[str], Optional[str]]:
    """The desk's own next-page link, absolutised. Returns `(url, note)`.

    `note` explains a REFUSAL — an off-host next link — so a stopped walk can
    say why rather than looking like an exhausted list.
    """
    if not html:
        return None, None
    scanner = _LinkScanner()
    try:
        scanner.feed(html)
        scanner.close()
    except Exception as exc:  # noqa: BLE001 — a pathological page ends the walk, it never crashes it
        return None, f"next-link scan raised ({exc}); walk stops here"
    off_host = None
    for href in list(scanner.rel_next) + list(scanner.text_next):
        href = href.strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute = urljoin(current_url, href)
        if urlsplit(absolute).scheme not in ("http", "https"):
            continue
        if not _same_host(absolute, current_url):
            off_host = (f"next link leaves the desk's host "
                        f"({urlsplit(absolute).netloc}) — not followed")
            continue
        return absolute, None
    return None, off_host


# --------------------------------------------------------------------------
# The walk
# --------------------------------------------------------------------------

def _row_identity(row: Happening) -> Tuple[str, str, str]:
    """Cross-page identity — the SAME rule one page already uses for its two
    readings (`worker.locale.desk_read.row_key`), so a listing repeated on
    page 2 is the same listing by the same test, with its URL defragmented.

    Identity is used here ONLY to avoid counting one listing twice. It is never
    a condition of existing: a row with no URL and no date still exists, keyed
    by its title (ONE-LIVE-TRUST.md — existence must not use an identity test).
    """
    return row_key(row.title, row.when, row.when_text,
                   _normalize(row.listing_url) if row.listing_url else None)


def walk(door: Door, fetch: Callable[[str], PageFetch], *,
         max_pages: int = DEFAULT_MAX_PAGES,
         start_url: Optional[str] = None,
         kind_map: Optional[KindMap] = None,
         patterns: Optional[Sequence[IdentityPattern]] = None) -> DeskWalk:
    """Follow one public desk's list to its end (or to the first honest stop).

    `fetch` is injected: this module never opens a socket, so the whole walk is
    testable against committed pages and a live run differs only in the fetcher
    it is handed. `patterns` is passed straight through to `read()` and defaults
    to the committed identity table, so a test states the shapes of ITS pages
    without any host reaching this module.
    """
    if not isinstance(door, Door):
        raise DeskWalkError(f"walk() takes a Door, got {type(door).__name__}")
    if not door.readable:
        raise DeskWalkError(
            f"door {door.door_id!r} is not a readable public desk "
            f"(type={door.door_type}, public={door.public}, intake={door.intake})"
            + (f" — {door.blocked_reason}" if door.blocked_reason else ""))
    if not callable(fetch):
        raise DeskWalkError("walk() needs a callable fetch(url) -> PageFetch")
    if not isinstance(max_pages, int) or max_pages < 1:
        raise DeskWalkError(f"max_pages must be a positive int, got {max_pages!r}")

    begin = start_url or door.url
    result = DeskWalk(door_id=door.door_id, door_type=door.door_type,
                      via=door.via, start_url=begin)
    seen_identities: dict = {}
    visited: set = set()
    url: Optional[str] = begin

    while url is not None:
        if len(result.pages) >= max_pages:
            result.stopped_because = "max_pages"
            result.notes.append(
                f"stopped at the {max_pages}-page cap with a next link still "
                f"outstanding ({url}) — this is OUR limit, not the end of the desk")
            break
        key = _normalize(url)
        if key in visited:
            result.stopped_because = "cycle"
            result.notes.append(
                f"next link returns to a page already read ({url}) — "
                f"pagination cycle, stopped")
            break
        visited.add(key)

        page = PageVisit(n=len(result.pages) + 1, url=url)
        result.pages.append(page)

        try:
            fetched = fetch(url)
        except Exception as exc:  # noqa: BLE001 — a fetcher blowing up is one page's news
            page.blocked_reason = f"fetch raised: {type(exc).__name__}: {exc}"[:300]
            page.walled = bool(_WALL_CODE_RE.search(f"{exc}"))
            result.stopped_because = "fetch_error"
            break
        if not isinstance(fetched, PageFetch):
            raise DeskWalkError(
                f"fetch({url!r}) returned {type(fetched).__name__}; walk() needs a "
                f"PageFetch so status, body and the landing URL are all classifiable")

        page.status = fetched.status

        # A wall, decided by the ingest loop's own authority. We knock once.
        verdict = demote_on_response(
            DECLARED_PUBLIC, status=fetched.status,
            final_url=fetched.final_url, error=fetched.error)
        if verdict.is_closed_door:
            page.blocked_reason = f"class D on contact — {verdict.reason}"
            page.walled = True
            result.stopped_because = "wall"
            break
        if fetched.error:
            page.blocked_reason = f"fetch failed: {fetched.error}"[:300]
            page.walled = bool(fetched.walled) or bool(_WALL_CODE_RE.search(fetched.error))
            result.stopped_because = "fetch_error"
            break
        if fetched.status is not None and fetched.status >= 400:
            # Triage, never "this desk has nothing on" (ONE-LIVE-OPERATING-LAW,
            # effectiveness rule 4).
            page.blocked_reason = (
                f"HTTP {fetched.status} — triage, not 'no events here'")
            page.walled = True
            result.stopped_because = "http_error"
            break
        if not fetched.body or not fetched.body.strip():
            page.blocked_reason = "empty body — nothing read (not 'nothing on')"
            result.stopped_because = "empty_page"
            break

        landed = fetched.landed_url
        try:
            page_read = read(door, fetched.body, base_url=landed, kind_map=kind_map,
                             patterns=patterns)
        except DeskReadError as exc:
            page.blocked_reason = f"unreadable: {exc}"[:300]
            result.stopped_because = "unreadable"
            break

        page.rows_seen = page_read.count
        page.identity_tier = page_read.identity_tier
        page.mash_blocked = page_read.mash_blocked
        page.notes.extend(page_read.notes)
        result.skipped_untitled += page_read.skipped_untitled
        result.merged_readings += page_read.merged_readings
        for unmapped in page_read.unmapped_categories:
            if unmapped not in result.unmapped_categories:
                result.unmapped_categories.append(unmapped)
        for row in page_read.rows:
            identity = _row_identity(row)
            if identity in seen_identities:
                # A later page may state something the first one left as a hole
                # (a category, a venue). Fill holes, never overwrite, and count
                # the repeat so pagination cannot inflate coverage.
                index = seen_identities[identity]
                result.rows[index] = fill_holes(result.rows[index], row)
                result.duplicates_across_pages += 1
                continue
            seen_identities[identity] = len(result.rows)
            result.rows.append(row)
            page.new_rows += 1

        following, note = next_page_url(fetched.body, landed)
        if note:
            page.notes.append(note)
        page.next_url = following
        if following is None:
            # THREE different silences, and only one of them is an exhausted
            # desk. `no_next_link` is the strongest claim this module makes, so
            # the two weaker cases get their own reason and keep `exhausted`
            # false.
            if note:
                # The page stated a next page and we did not follow it (it left
                # the desk's host, or the page could not be scanned). Reporting
                # that as `no_next_link` would say the DESK ran out of list.
                result.stopped_because = "next_link_not_followed"
                result.notes.append(f"page {page.n}: {note}")
            elif control := continuation_control(fetched.body):
                result.stopped_because = "next_control_not_a_link"
                said = (f"page {page.n} states a continuation control we cannot "
                        f"follow ({control}) — the desk's list goes on behind "
                        f"script; this walk is a FLOOR, not the whole desk")
                page.notes.append(said)
                result.notes.append(said)
            else:
                result.stopped_because = "no_next_link"
            break
        url = following

    if result.stopped_because == "not started":  # pragma: no cover - loop always sets it
        result.stopped_because = "no_pages"
    return result


def walk_table(walks: Sequence[DeskWalk]) -> str:
    """The founder's per-page column, as a markdown table over one or more walks."""
    lines = ["| door | page | url | status | rows | new | blocked_reason |",
             "|---|---|---|---|---|---|---|"]
    for one in walks:
        for page in one.pages:
            reason = (page.blocked_reason or "—").replace("|", "\\|")
            lines.append(
                f"| `{one.door_id}` | {page.n} | {page.url.replace('|', '%7C')} | "
                f"{page.status if page.status is not None else '—'} | "
                f"{page.rows_seen} | {page.new_rows} | {reason} |")
    return "\n".join(lines)
