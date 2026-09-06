"""read_event_page(permalink) — ONE event page states its own night and place.

Founder, this session's ticket (Ticket C): "a [desk] (or [second desk]) /event/…
page becomes a Happening with when + place_text when THAT page states them. No
invented dates. No mash." — the two brands the founder named are elided in
brackets because a committed gate keeps brand literals out of this package
(`tests/test_locale_pack.py`): a locale stops being DATA the moment its modules
name a desk, and this reader has to work for a locale nobody has written yet.
The founder's text is quoted verbatim, brands included, in `tools/event_page_table.py`
and in the STATE contract, where the locale is chosen rather than processed.

Ticket B (`worker/locale/desk_read.py`) split a list page into rows and gave
each row its OWN address (`listing_url`). Most of those rows carry holes exactly
where the night and the place go, because a list card often prints neither. This
module follows that address — same host, one knock — and fills the two holes
from the words on THAT page.

Four rules, each a refusal to guess:

  * THE DATE COMES FROM THAT PAGE OR NOWHERE. Three statements count, and they
    are the three the ticket names: a `<time datetime="…">` carrying a real
    date, a schema.org `Event.startDate`, or a DTSTART in an iCalendar file the
    page itself advertises. Nothing else is a date. A page that states only a
    clock ("doors 8pm", `<time datetime="20:00">`) has stated a TIME, not a
    night: `when` stays NULL and `clock_only` says why. Prose ("this Friday")
    is carried verbatim in `when_text`, never parsed — a wrong night on a
    public row is worse than an honest hole (ONE-LIVE-TRUST.md: "A missing
    minute is not a missing night").

  * A DIFFERENT PAGE'S DATE MUST NOT ATTACH. This is the detail-page shape of
    the mash Ticket B killed, and it has two mouths. Outward: what the LIST
    page printed beside the card never becomes this page's statement —
    `PageStatement` is built from the fetched bytes alone and knows nothing
    about the row it will be applied to, so there is no code path along which a
    list date can arrive. Inward: an event page's "related events" rail is full
    of other listings' `<time>` and other listings' JSON-LD, so a candidate is
    dropped when it sits inside a card addressed to a DIFFERENT same-host
    permalink, and a JSON-LD Event whose own `url` names another page is never
    read as this one's.

  * THE PLACE IS THE PAGE'S OWN VENUE LINE. schema.org `location`, a microdata
    `itemprop="location"` subtree, or a printed line the page itself marks as
    the venue (`class="venue"`, `id="location"`, a `Where:` label). Absent means
    absent. We never fall back to the locale's city: "Austin, TX" written under
    a listing nobody stated a place for is a fabricated fact about where a
    stranger should drive tonight (ONE-LIVE-COVERAGE-LAW: single-source rows
    stay; ONE-LIVE-TRUST: null is correct).

  * A WALL IS A HOLE, NOT A WORKAROUND. 401/402/403/407/429 or a redirect onto
    a sign-in page is class D through the ingest loop's own authority
    (`worker.sourcing.source_class.demote_on_response`). We knock ONCE: the
    page becomes a hole with a `blocked_reason`, the door is queued for the
    human claim path (`tools/class_d_queue.py`), and neither that page nor any
    other page of that host is knocked on again in this run. No login, no
    retry, no work-around.

A CONTESTED NIGHT IS NO NIGHT (founder ruling, 2026-09-06). When the list card
and the event page both state a night and it is not the same moment, `apply()`
takes the night AWAY: `when` goes NULL, the disagreement is recorded, and
neither claim wins. Keeping the list's would publish a night that the desk's own
event page contradicts; taking the page's would be the mutation this ticket
excludes. Both statements are kept on the visit so the disagreement stays
auditable. Hole-filling is unchanged: a night the list never stated is taken
from the page.

Pure: stdlib plus this repo's own parsers. No network, no DB, no clock, no
model — the caller injects `fetch`, exactly as the walk does.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple
from urllib.parse import urldefrag, urlsplit

from worker.importers.structured_feed import (
    discover_ics_links, parse_ics, parse_jsonld,
)
from worker.locale.desk_read import (
    _FURNITURE_TAGS, _SCOPED_FURNITURE_TAGS, Happening, _TreeBuilder, _Node,
    _in_furniture, _inside_sectioning, _is_page_structure, _ws,
)
from worker.locale.desk_publish import _instant
from worker.locale.desk_walk import PageFetch, _same_host
from worker.sourcing.source_class import ClassVerdict, demote_on_response

log = logging.getLogger(__name__)

#: The class a permalink starts from — the desk it came from is already a
#: declared public door, and this is one of its own pages.
DECLARED_PUBLIC = ClassVerdict("B", "same-host page of a declared public desk",
                               fetchable=True)

#: Status codes that mean a wall when they reach us as text rather than as a
#: status (a proxy CONNECT failure carries no HTTP status). Same set the walk
#: uses, for the same reason: a wall printed as `0` in the blocked column is the
#: number that lets a walled desk read as an empty one.
_WALL_CODE_RE = re.compile(r"\b(?:401|402|403|407|429)\b")

#: A `datetime` attribute we accept as a real DATE: ISO date, optionally with a
#: time. Anything else is not a date this page stated.
_ISO_DATE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?"
    r"(?:Z|[+-]\d{2}:?\d{2})?))?$")
#: A `datetime` attribute that is a CLOCK and nothing else — "20:00", "8:00 PM".
#: The page stated a time; it has not stated a night.
_CLOCK_ONLY_RE = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?\s*(?:[AaPp]\.?[Mm]\.?)?$")

#: Where a page may print its own venue line. Matched on the element's OWN
#: class/id/itemprop tokens — a declaration by the page, never a guess from the
#: text's shape.
_PLACEISH_RE = re.compile(r"venue|location|place|where", re.I)
#: Labels a page prints in front of its venue line. Stripped from the value so
#: the place text is the place, not the label.
_PLACE_LABEL_RE = re.compile(r"^\s*(?:where|venue|location|place)\s*[:\-–—]\s*", re.I)

#: An element the page marks as the END of the event rather than its start.
#: Matched on whole tokens: the substring test spells an end time out of
#: `class="calendar"` ("cal-end-ar"), which would drop every start it labels.
_END_TOKEN_RE = re.compile(r"(?:^|[\s_\-])end(?:s|ed|time)?(?:$|[\s_\-])", re.I)

#: Cap on the text we will accept as a place line. A "venue" class wrapped
#: around half the page is not a venue line, and a paragraph published as a
#: place is a worse hole than no place.
MAX_PLACE_CHARS = 200

#: How many ICS files one page may cause us to fetch. The page advertises them;
#: we read the first same-host one that parses, and stop.
MAX_ICS_FETCHES = 1


class EventPageError(ValueError):
    """This page cannot be read as asked. Raised, never downgraded to an empty
    result that would read as "this page stated nothing"."""


@dataclass(frozen=True)
class PageStatement:
    """What ONE event page stated ABOUT ITSELF. Built from that page's bytes
    alone: it is handed no row, so nothing another page printed can enter here.
    """

    url: str                          # the page these words were read from
    when: Optional[str] = None        # ISO date or instant THAT page stated
    when_precision: Optional[str] = None   # "date" | "datetime"
    when_text: Optional[str] = None   # the date text the page printed, verbatim
    #: WHICH of the ticket's three statements produced `when`:
    #: "time_datetime" | "jsonld_startDate" | "ics". On the statement, so a
    #: table can never present one rung's reading as another's.
    when_source: Optional[str] = None
    place_text: Optional[str] = None
    #: "jsonld_location" | "microdata_location" | "printed_venue_line".
    place_source: Optional[str] = None
    #: The page stated a clock but no date. NOT a date, and named so a table can
    #: tell "no date printed" from "a time printed with no night".
    clock_only: bool = False
    #: Dates the page stated that we declined to choose between (a page printing
    #: two different nights has not told us which one this is). Counted, because
    #: declining is a decision and a silent decision looks like a bug.
    ambiguous_dates: Tuple[str, ...] = ()
    #: The page's structured data and its printed markup state DIFFERENT
    #: nights. The page argues with itself, so it has stated no night: `when`
    #: is None and `rung_claims` carries what each rung said.
    cross_rung_conflict: bool = False
    rung_claims: Tuple[str, ...] = ()
    #: Candidates dropped because they belonged to ANOTHER listing on this page
    #: (a related-events rail). The anti-mash count for the detail page.
    foreign_candidates: int = 0
    notes: Tuple[str, ...] = ()

    @property
    def dated(self) -> bool:
        return bool(self.when)

    @property
    def placed(self) -> bool:
        return bool(self.place_text)


@dataclass
class FollowVisit:
    """One permalink we tried to follow, whether or not it opened."""

    listing_url: str
    title: str = ""
    fetched_url: Optional[str] = None
    status: Optional[int] = None
    statement: Optional[PageStatement] = None
    blocked_reason: Optional[str] = None
    walled: bool = False
    #: This wall was written to the class-D claim queue's input (a human path),
    #: which is the only thing we ever do about a wall.
    queued: bool = False
    #: This row's address was already read earlier in this run. The page's
    #: answer is applied here too, but no second knock was spent and the page
    #: is not counted twice in any per-PAGE number.
    reused: bool = False
    #: We never knocked here: the host had already walled us `wall_streak_limit`
    #: times in a row. A hole made by OUR caution, and never counted as the
    #: desk's refusal — that number has to stay the number of walls we met.
    not_knocked: bool = False
    #: Not followed because the address leaves the desk's host. Same-host only
    #: is the ticket's first Must-do, and a refusal is reported, never silent.
    off_host: bool = False
    #: The page stated a night/place that DISAGREES with what the row already
    #: carried. Recorded, never silently reconciled (see the module docstring).
    when_conflict: bool = False
    place_conflict: bool = False
    #: On a contested night, what each side said. The row loses its night; the
    #: two claims are kept HERE so the disagreement stays auditable — a hole on
    #: the row must not also be a hole in the record of why.
    listed_when: Optional[str] = None
    page_when: Optional[str] = None
    #: What the ROW carries after `apply()`. Distinct from the page's own
    #: statement: a contested night leaves the page dated and the row NOT, and
    #: a table that prints only the page's number overstates what a friend
    #: would see.
    row_when_after: Optional[str] = None
    #: Filled by `apply()` — what this visit actually added to the row.
    filled_when: bool = False
    filled_place: bool = False

    @property
    def blocked(self) -> bool:
        return self.blocked_reason is not None

    @property
    def dated(self) -> bool:
        return bool(self.statement and self.statement.when)

    @property
    def placed(self) -> bool:
        return bool(self.statement and self.statement.place_text)


@dataclass
class FollowRun:
    """What following a batch of permalinks yielded, including what it did not."""

    rows: List[Happening] = field(default_factory=list)
    visits: List[FollowVisit] = field(default_factory=list)
    #: Hosts we stopped knocking on, and why. A wall on ONE listing is a hole
    #: on that listing — a members-only show on an open desk is exactly that —
    #: so it does NOT close the desk. Only a RUN of consecutive walls does, at
    #: `wall_streak_limit`, and that stop is OUR limit, reported as such: the
    #: pages behind it are `not_knocked`, never counted as walls we met.
    closed_hosts: Set[str] = field(default_factory=set)
    #: Consecutive walls seen per host so far, reset by any page that opens.
    wall_streaks: Dict[str, int] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    @property
    def followed_n(self) -> int:
        return sum(1 for v in self.visits
                   if v.statement is not None and not v.reused)

    @property
    def dated_n(self) -> int:
        """PAGES that stated a night. A page read once and applied to two rows
        is one page."""
        return sum(1 for v in self.visits if v.dated and not v.reused)

    @property
    def placed_n(self) -> int:
        return sum(1 for v in self.visits if v.placed and not v.reused)

    @property
    def blocked_n(self) -> int:
        return sum(1 for v in self.visits if v.blocked and not v.reused)

    @property
    def walled_n(self) -> int:
        """Walls we actually MET. A page we declined to knock on is not one."""
        return sum(1 for v in self.visits
                   if v.walled and not v.not_knocked and not v.reused)

    @property
    def not_knocked_n(self) -> int:
        return sum(1 for v in self.visits if v.not_knocked)

    @property
    def off_host_n(self) -> int:
        return sum(1 for v in self.visits if v.off_host)

    @property
    def filled_when_n(self) -> int:
        return sum(1 for v in self.visits if v.filled_when)

    @property
    def filled_place_n(self) -> int:
        return sum(1 for v in self.visits if v.filled_place)

    @property
    def conflict_n(self) -> int:
        return sum(1 for v in self.visits if v.when_conflict or v.place_conflict)

    @property
    def rows_dated_n(self) -> int:
        """Followed rows that CARRY a night afterwards — what a friend would
        see. `dated_n` counts pages that stated one, which is not the same
        number once a contested night is taken away."""
        return sum(1 for v in self.visits if v.row_when_after)

    @property
    def nulled_when_n(self) -> int:
        """Rows whose night this run TOOK AWAY because the desk's own two pages
        disagreed. Counted, because removing a claim is a decision."""
        return sum(1 for v in self.visits if v.when_conflict)


# --------------------------------------------------------------------------
# Reading ONE event page
# --------------------------------------------------------------------------

def _norm_url(url: str) -> str:
    """Compare form for "is this the same page": fragment dropped, trailing
    slash dropped, scheme and host lowered. Deliberately narrow — two addresses
    differing in a query parameter are two pages here, because assuming a
    stranger's routing treats them alike is how a foreign date gets adopted.
    """
    bare = urldefrag(url or "")[0].strip()
    if not bare:
        return ""
    parts = urlsplit(bare)
    path = parts.path.rstrip("/") or "/"
    if parts.netloc:
        return f"{parts.scheme.lower()}://{parts.netloc.lower()}{path}" + (
            f"?{parts.query}" if parts.query else "")
    return path + (f"?{parts.query}" if parts.query else "")


def _attr_tokens(node: _Node) -> str:
    """The element's own declaration surface: class, id and itemprop together.
    Matched as one string because a page may name its venue line in any of them.
    """
    return " ".join(filter(None, (
        node.attrs.get("class", ""),
        node.attrs.get("id", ""),
        node.attrs.get("itemprop", ""),
    )))


def _text_of(node: _Node, *, limit: int = 4000) -> str:
    out: List[str] = []
    size = 0

    def walk(n: _Node) -> None:
        nonlocal size
        for child in n.children:
            if size > limit:
                return
            if isinstance(child, str):
                out.append(child)
                size += len(child)
            else:
                walk(child)

    walk(node)
    return _ws(" ".join(out))


def _foreign_identity_ancestors(root: _Node, page_url: str) -> Set[int]:
    """Elements that ARE another listing on this page — a related-events card.

    A detail page's rail prints other listings' clocks and other listings'
    venues. Anything inside a container that links to a DIFFERENT same-host
    permalink belongs to that listing, not to this page, so its date is exactly
    the "date from a different page" the ticket forbids attaching.

    Identified by containment, never by class name: a card is the topmost
    element whose subtree addresses exactly ONE other page and never this one. A
    wrapper holding several is the rail itself, so we descend into it rather
    than marking it whole — a venue line printed beside the rail is not lost.

    One post-order pass computes every subtree's answer, then one top-down pass
    marks the cards. Scanning links again from each node (the first draft) is
    quadratic on a page with a long rail.
    """
    here = _norm_url(page_url)
    foreign_by_node: Dict[int, Set[str]] = {}
    self_by_node: Dict[int, bool] = {}
    page_level_by_node: Dict[int, bool] = {}

    def gather(node: _Node) -> Tuple[Set[str], bool, bool]:
        foreign: Set[str] = set()
        self_link = False
        page_level = False
        if node.tag == "a":
            href = (node.attrs.get("href") or "").strip()
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                absolute = href if urlsplit(href).netloc else _resolve(href, page_url)
                target = _norm_url(absolute)
                if target and target == here:
                    self_link = True
                elif target and _same_host(absolute, page_url):
                    foreign.add(target)
        for child in node.children:
            if isinstance(child, _Node):
                sub_foreign, sub_self, sub_page = gather(child)
                foreign |= sub_foreign
                self_link = self_link or sub_self
                page_level = page_level or sub_page or _is_page_structure(child)
        foreign_by_node[id(node)] = foreign
        self_by_node[id(node)] = self_link
        page_level_by_node[id(node)] = page_level
        return foreign, self_link, page_level

    gather(root)

    marked: Set[int] = set()

    def mark(node: _Node) -> None:
        # A card never CONTAINS the page around it. Without this bound the
        # `<html>` element of a page carrying exactly one outbound link is
        # itself "a card for another listing", and every date on the page is
        # dropped as foreign (`desk_read._has_page_level`, same rule, same
        # reason — it is what stops a row growing through the masthead).
        if (node.tag not in ("#root", "html", "body")
                and len(foreign_by_node.get(id(node), ())) == 1
                and not self_by_node.get(id(node))
                and not page_level_by_node.get(id(node))):
            marked.add(id(node))
            return
        for child in node.children:
            if isinstance(child, _Node):
                mark(child)

    mark(root)
    return marked


def _resolve(href: str, base_url: str) -> str:
    from urllib.parse import urljoin
    return urljoin(base_url, href)


def _is_furniture(node: _Node) -> bool:
    """True when this element is the page's own plumbing, or sits inside it.

    `desk_read._in_furniture` asks only about ANCESTORS, because it was written
    for anchors. Here the element itself can be the plumbing — a page-level
    `<footer class="location">` carrying the NEWSPAPER's street address is the
    exact shape that would publish a desk's office as tonight's venue.
    """
    if node.tag in _FURNITURE_TAGS:
        return True
    if node.tag in _SCOPED_FURNITURE_TAGS and not _inside_sectioning(node):
        return True
    return _in_furniture(node)


def _under_marked(node: _Node, marked: Set[int]) -> bool:
    cur: Optional[_Node] = node
    while cur is not None:
        if id(cur) in marked:
            return True
        cur = cur.parent
    return False


@dataclass(frozen=True)
class _DateCandidate:
    date: str                    # YYYY-MM-DD
    instant: Optional[str]       # full ISO value when the page stated a time
    text: str                    # what the page printed
    is_start: bool               # the page marked this one the START


def _time_candidates(root: _Node, page_url: str,
                     marked: Set[int]) -> Tuple[List[_DateCandidate], bool, int]:
    """Every `<time datetime>` this page states about ITSELF.

    Returns (candidates, clock_only_seen, foreign_dropped).
    """
    candidates: List[_DateCandidate] = []
    clock_only = False
    foreign = 0

    def visit(node: _Node) -> None:
        nonlocal clock_only, foreign
        if node.tag == "time" or node.attrs.get("itemprop", "").strip().lower() in (
                "startdate", "enddate"):
            raw = (node.attrs.get("datetime") or node.attrs.get("content") or "").strip()
            printed = _text_of(node, limit=200)
            if raw:
                if _under_marked(node, marked) or _is_furniture(node):
                    foreign += 1
                else:
                    m = _ISO_DATE_RE.match(raw)
                    if m:
                        itemprop = node.attrs.get("itemprop", "").strip().lower()
                        candidates.append(_DateCandidate(
                            date=m.group(1),
                            instant=raw if m.group(2) else None,
                            text=printed or raw,
                            is_start=itemprop == "startdate" or (
                                itemprop != "enddate"
                                and not _END_TOKEN_RE.search(_attr_tokens(node))),
                        ))
                    elif _CLOCK_ONLY_RE.match(raw):
                        # A time with no night. Named, never coerced onto a day.
                        clock_only = True
        for child in node.children:
            if isinstance(child, _Node):
                visit(child)

    visit(root)
    return candidates, clock_only, foreign


def _pick_date(candidates: Sequence[_DateCandidate]) -> Tuple[
        Optional[str], Optional[str], Optional[str], Tuple[str, ...]]:
    """(when, precision, when_text, ambiguous_dates) from one page's candidates.

    A page stating ONE date has stated this listing's night, whether it printed
    it once or five times (a start and an end are one night). A page stating
    TWO different dates has not told us which one this listing is, so we take
    neither and report both — the ticket's "no invented dates" applied to a
    choice we would otherwise be making on the page's behalf.
    """
    if not candidates:
        return None, None, None, ()
    dates = sorted({c.date for c in candidates})
    if len(dates) > 1:
        return None, None, None, tuple(dates)

    starts = [c for c in candidates if c.is_start] or list(candidates)
    marked_start = [c for c in candidates if c.is_start and c.instant]
    timed = {c.instant for c in starts if c.instant}
    if len(marked_start) == 1 and marked_start[0].instant:
        chosen = marked_start[0]
        return chosen.instant, "datetime", chosen.text or None, ()
    if len(timed) == 1:
        instant = timed.pop()
        text = next((c.text for c in starts if c.instant == instant), None)
        return instant, "datetime", text or None, ()
    # One night, and either no clock or several the page never ranked. The night
    # is stated; the minute is not — so the night is what we take.
    return dates[0], "date", (starts[0].text or None), ()


def _jsonld_for_this_page(html: str, page_url: str) -> Tuple[Optional[dict], int, List[str]]:
    """The schema.org Event this page is ABOUT, if it declares exactly one.

    Returns (event, foreign_dropped, notes). A page declaring several Events is
    a page carrying its neighbours' data too: we take the one whose own `url`
    IS this page, and otherwise take none — picking "the first" would publish a
    related listing's night under this listing's title, which is the mash.
    """
    notes: List[str] = []
    try:
        events = parse_jsonld(html)
    except Exception as exc:  # noqa: BLE001 — a bad block never loses the HTML rungs
        return None, 0, [f"JSON-LD parse raised ({exc}); HTML statements still read"]
    if not events:
        return None, 0, notes
    here = _norm_url(page_url)
    own = [ev for ev in events if ev.get("url") and _norm_url(ev["url"]) == here]
    if len(own) == 1:
        return own[0], len(events) - 1, notes
    if len(own) > 1:
        notes.append(f"{len(own)} JSON-LD Events claim this same address; none taken")
        return None, len(events), notes
    if len(events) == 1:
        # One Event, and it named no address (or named another). It is the only
        # thing this page declares itself to be.
        only = events[0]
        if only.get("url") and _norm_url(only["url"]) != here:
            notes.append(
                f"the page's only JSON-LD Event names another address "
                f"({only['url']}) — not read as this page's own statement")
            return None, 1, notes
        return only, 0, notes
    notes.append(f"{len(events)} JSON-LD Events on the page, none addressed to it; "
                 f"none taken")
    return None, len(events), notes


def _place_from_jsonld(ev: dict) -> Optional[str]:
    name = (ev.get("venue_name") or "").strip() or None
    address = (ev.get("venue_address") or "").strip() or None
    city = (ev.get("venue_city") or "").strip() or None
    parts = [p for p in (name, address or city) if p]
    if not parts:
        return None
    if len(parts) == 2 and parts[1].lower().startswith(parts[0].lower()):
        parts = [parts[1]]
    return _ws(", ".join(parts))[:MAX_PLACE_CHARS] or None


def _place_from_html(root: _Node, marked: Set[int]) -> Optional[str]:
    """The venue line this page prints about ITSELF, or None.

    Two declarations count, both the page's own: a microdata `itemprop`
    naming a location, and an element whose class/id names one. A line inside a
    related-listing card belongs to that listing and is skipped.
    """
    microdata: Optional[str] = None
    printed: Optional[str] = None

    def visit(node: _Node) -> None:
        nonlocal microdata, printed
        if not _under_marked(node, marked) and not _is_furniture(node):
            itemprop = node.attrs.get("itemprop", "").strip().lower()
            if itemprop == "location" and microdata is None:
                value = (node.attrs.get("content") or "").strip() or _text_of(node, limit=400)
                value = _clean_place(value)
                if value:
                    microdata = value
            elif printed is None and _PLACEISH_RE.search(_attr_tokens(node)):
                value = _clean_place(_text_of(node, limit=400))
                if value:
                    printed = value
        for child in node.children:
            if isinstance(child, _Node):
                visit(child)

    visit(root)
    if microdata:
        return microdata
    return printed


def _clean_place(value: str) -> Optional[str]:
    text = _PLACE_LABEL_RE.sub("", _ws(value or ""))
    if not text or len(text) > MAX_PLACE_CHARS:
        # Too long to be a venue line: a "location" class wrapped round the page
        # body. A paragraph published as a place is a worse hole than no place.
        return None
    return text


def read_event_page(html: str, page_url: str, *,
                    ics_fetch: Optional[Callable[[str], PageFetch]] = None
                    ) -> PageStatement:
    """What ONE event page states about itself: its night, and its place.

    `html` is the fetched page's bytes-as-text; `page_url` is where they came
    from (the FINAL url after redirects, so "is this element about this page"
    is asked against the address we actually landed on).

    `ics_fetch` is optional and same-host-checked by the caller: when the page
    states no date in its own markup but advertises an iCalendar file, that
    file is the third statement the ticket names. Without it, the ICS rung
    simply does not run — an absent fetcher never becomes an absent date.
    """
    if page_url is None or not str(page_url).strip():
        raise EventPageError("read_event_page() needs the url the page came from")
    html = html or ""
    notes: List[str] = []

    try:
        builder = _TreeBuilder()
        builder.feed(html)
        builder.close()
        root = builder.root
    except Exception as exc:  # noqa: BLE001 — a pathological page states nothing extra
        root = None
        notes.append(f"HTML parse raised ({exc}); JSON-LD statements still read")

    marked = _foreign_identity_ancestors(root, page_url) if root is not None else set()

    # Rung 1 — schema.org, the page's own machine statement about itself.
    ld_event, ld_foreign, ld_notes = _jsonld_for_this_page(html, page_url)
    notes.extend(ld_notes)

    when = precision = when_text = when_source = None
    ambiguous: Tuple[str, ...] = ()
    clock_only = False
    foreign_n = ld_foreign
    cross_rung_conflict = False
    rung_claims: Tuple[str, ...] = ()

    ld_when = ld_precision = None
    if ld_event and ld_event.get("start_time"):
        ld_when = ld_event["start_time"]
        ld_precision = "date" if ld_event.get("all_day") else "datetime"

    # Rung 2 — a `<time datetime>` the page printed about itself.
    #
    # BOTH rungs are read, always, even when rung 1 already answered (evaluator
    # finding, PR #237 r2). Skipping rung 2 once `when` was set hid the case
    # where a page's structured data says one night and its visible markup says
    # another: the JSON-LD night was reported as uncontested, and a reader would
    # be shown a night the page itself contradicts. The founder's ruling on the
    # list-vs-page disagreement is the same rule one layer in — A CONTESTED
    # NIGHT IS NO NIGHT — so a page that disagrees with itself states no night.
    html_when = html_precision = html_text = None
    if root is not None:
        candidates, clock_only, dropped = _time_candidates(root, page_url, marked)
        foreign_n += dropped
        html_when, html_precision, html_text, ambiguous = _pick_date(candidates)
        if ambiguous:
            notes.append(
                f"the page states {len(ambiguous)} different dates "
                f"({', '.join(ambiguous)}); none taken as this listing's night")

    if ld_when and ambiguous:
        # Structured data naming one night while the visible page prints two is
        # a page arguing with itself; picking the machine-readable one would be
        # resolving that argument on the publisher's behalf.
        cross_rung_conflict = True
        rung_claims = (f"jsonld_startDate={ld_when}",) + tuple(
            f"time_datetime={d}" for d in ambiguous)
    elif ld_when and html_when and not _same_moment(ld_when, html_when):
        cross_rung_conflict = True
        rung_claims = (f"jsonld_startDate={ld_when}", f"time_datetime={html_when}")
    elif ld_when:
        # Either the page printed no `<time>`, or it printed the same moment.
        when, precision, when_source = ld_when, ld_precision, "jsonld_startDate"
    elif html_when:
        when, precision, when_text = html_when, html_precision, html_text
        when_source = "time_datetime"

    if cross_rung_conflict:
        notes.append(
            "the page's structured data and its printed markup state different "
            f"nights ({'; '.join(rung_claims)}); neither is taken")

    # Rung 3 — an iCalendar file this page advertises. Only reached when the
    # page's own markup stated no date, and only ever a SAME-HOST file.
    #
    # A page that CONTRADICTS ITSELF is not a page with no date (evaluator
    # finding, PR #237 r2): letting the calendar file answer there would pick a
    # winner for a dispute we just declined, and the row would show one settled
    # night with the disagreement nowhere on it.
    if (when is None and ics_fetch is not None
            and not ambiguous and not cross_rung_conflict):
        when, precision, when_source, ics_notes = _read_ics(html, page_url, ics_fetch)
        notes.extend(ics_notes)
    elif ics_fetch is not None and (ambiguous or cross_rung_conflict):
        notes.append("a calendar file was not consulted: this page disagrees "
                     "with itself, and a dispute is not a hole to fill")

    place_text = place_source = None
    if ld_event:
        place_text = _place_from_jsonld(ld_event)
        if place_text:
            place_source = "jsonld_location"
    if place_text is None and root is not None:
        place_text = _place_from_html(root, marked)
        if place_text:
            place_source = ("microdata_location"
                            if _has_location_itemprop(root, marked)
                            else "printed_venue_line")

    return PageStatement(
        url=page_url,
        when=when,
        when_precision=precision,
        when_text=when_text,
        when_source=when_source,
        place_text=place_text,
        place_source=place_source,
        clock_only=bool(clock_only and when is None),
        ambiguous_dates=ambiguous,
        cross_rung_conflict=cross_rung_conflict,
        rung_claims=rung_claims,
        foreign_candidates=foreign_n,
        notes=tuple(notes),
    )


def _has_location_itemprop(root: _Node, marked: Set[int]) -> bool:
    found = False

    def visit(node: _Node) -> None:
        nonlocal found
        if found:
            return
        if (not _under_marked(node, marked) and not _is_furniture(node)
                and node.attrs.get("itemprop", "").strip().lower() == "location"):
            found = True
            return
        for child in node.children:
            if isinstance(child, _Node):
                visit(child)

    visit(root)
    return found


def _read_ics(html: str, page_url: str,
              ics_fetch: Callable[[str], PageFetch]) -> Tuple[
                  Optional[str], Optional[str], Optional[str], List[str]]:
    """DTSTART from an iCalendar file THIS page advertises, same host only.

    The same-host test is asked TWICE, and the second time is the one that
    matters (evaluator finding, PR #237, seat openai / lens absence-only): the
    pre-fetch check judges the address the page ADVERTISED, and a redirect
    happens after it. A `/event/foo-1.ics` link that 302s onto a third party's
    calendar host would otherwise have its DTSTART adopted as this page's own
    statement — a fabricated night on a public row, from a publisher this desk
    does not speak for. Reproduced before fixing: the third party's
    `2099-12-31` reached the row with `when_source="ics"`.

    So the answer is judged the way `follow()` judges an event page: the ingest
    loop's own wall authority, then the status, then WHERE IT LANDED. Anything
    else is a hole with a note, never a parse.
    """
    notes: List[str] = []
    try:
        links = discover_ics_links(html, page_url, limit=MAX_ICS_FETCHES + 2)
    except Exception as exc:  # noqa: BLE001
        return None, None, None, [f"ICS link scan raised ({exc})"]
    fetched = 0
    for link in links:
        if link.lower().startswith("webcal:"):
            link = "https:" + link.split(":", 1)[1]
        if not _same_host(link, page_url):
            notes.append(f"calendar file leaves the desk's host ({urlsplit(link).netloc})"
                         f" — not fetched")
            continue
        if fetched >= MAX_ICS_FETCHES:
            break
        fetched += 1
        try:
            answer = ics_fetch(link)
        except Exception as exc:  # noqa: BLE001 — one file's failure is one hole
            notes.append(f"calendar fetch raised: {type(exc).__name__}: {exc}"[:200])
            continue
        if not isinstance(answer, PageFetch) or answer.error or not answer.body:
            notes.append(f"calendar file unreadable ({link})")
            continue
        verdict = demote_on_response(
            DECLARED_PUBLIC, status=answer.status,
            final_url=answer.final_url, error=answer.error)
        if verdict.is_closed_door:
            notes.append(f"calendar file is a closed door — {verdict.reason}")
            continue
        if answer.status is not None and answer.status >= 400:
            notes.append(f"calendar file answered HTTP {answer.status}; no date taken")
            continue
        landed = answer.landed_url
        if not _same_host(landed, page_url):
            # The link was same-host; the REDIRECT was not. This is the check
            # the pre-fetch one cannot make.
            notes.append(
                f"calendar file redirected off the desk's host "
                f"({urlsplit(landed).netloc}) — not read; a stranger's calendar "
                f"is not this page's statement")
            continue
        try:
            events = parse_ics(answer.body)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"calendar parse raised ({exc})")
            continue
        # WHICH event in this file is THIS page's, asked exactly as
        # `_jsonld_for_this_page` asks it (evaluator finding, PR #237 r3). A
        # calendar file is routinely shared or reused across a desk, so a lone
        # VEVENT naming ANOTHER address is a neighbour's night, not this
        # listing's — and adopting it would print a fabricated date for the
        # wrong event. A VEVENT that names no url at all is the file's own
        # single statement and stands, as it does on the JSON-LD rung.
        here = _norm_url(page_url)
        own = [e for e in events if e.get("url") and _norm_url(e["url"]) == here]
        chosen = None
        if len(own) == 1:
            chosen = own[0]
        elif len(own) > 1:
            notes.append(f"calendar file holds {len(own)} events claiming this "
                         f"same address; none taken")
        elif len(events) == 1:
            only = events[0]
            if only.get("url") and _norm_url(only["url"]) != here:
                notes.append(
                    f"the calendar's only event names another address "
                    f"({only['url']}) — not read as this page's own statement")
            else:
                chosen = only
        else:
            notes.append(
                f"calendar file holds {len(events)} events, none addressed to this "
                f"page; no date taken")
        if chosen is None:
            continue
        start = chosen.get("start_time")
        if not start:
            continue
        return start, ("date" if chosen.get("all_day") else "datetime"), "ics", notes
    return None, None, None, notes


# --------------------------------------------------------------------------
# Following the permalinks
# --------------------------------------------------------------------------

def apply(row: Happening, statement: PageStatement) -> Tuple[Happening, FollowVisit]:
    """Fill this row's HOLES from its own page; on a contested night, take away.

    Two rules, and they point in opposite directions on purpose (founder ruling,
    2026-09-06):

      * HOLE-FILL. The list stated no night and the page states one -> take the
        page's. Same for the place. This is the ticket.
      * A CONTESTED NIGHT IS NO NIGHT. The list and the page both state a night
        and they are not the same moment -> `when` goes NULL and the
        disagreement is recorded. Neither claim wins: keeping the list's would
        publish a night its own event page contradicts, and taking the page's
        would be the mutation this ticket excludes. What both sides said is kept
        on the VISIT (`listed_when` / `page_when`), so nothing is lost to audit
        — it is only refused a public row.

    `when_text` and `when_precision` go with it. They are the same contested
    claim in other clothes, and a NULL `when` beside a `when_text` reading
    "Fri Sep 11, 8pm" is a night on any surface that renders text.

    The founder's ruling names the NIGHT. A contested PLACE still keeps the
    list's value and records `place_conflict` — unchanged, and not extended
    here on our own authority.
    """
    visit = FollowVisit(listing_url=row.listing_url or statement.url,
                        title=row.title, fetched_url=statement.url,
                        statement=statement)
    changes: Dict[str, object] = {}
    if statement.when:
        if not row.when:
            changes["when"] = statement.when
            changes["when_precision"] = statement.when_precision
            if statement.when_text and not row.when_text:
                changes["when_text"] = statement.when_text
            visit.filled_when = True
        elif not _same_moment(row.when, statement.when):
            visit.when_conflict = True
            visit.listed_when = row.when
            visit.page_when = statement.when
            changes["when"] = None
            changes["when_precision"] = None
            changes["when_text"] = None
    if statement.place_text:
        if not row.place_text:
            changes["place_text"] = statement.place_text
            visit.filled_place = True
        elif not _same_place(row.place_text, statement.place_text):
            visit.place_conflict = True
    filled = replace(row, **changes) if changes else row
    visit.row_when_after = filled.when
    return filled, visit


def _same_moment(a: Optional[str], b: Optional[str]) -> bool:
    """True when these two statements are the SAME moment, however written.

    `2026-09-11T20:00-05:00` and `2026-09-12T01:00:00Z` are one instant written
    two ways, and comparing the strings (or their date prefixes) reports a
    disagreement that does not exist — the defect PR #229 r8 fixed on the union
    path, arriving here for the same reason. One home for the question:
    `desk_publish._instant`. When either side states only a date, the night is
    all either one claims, so the nights are what is compared.
    """
    left, right = (a or "").strip(), (b or "").strip()
    if not left or not right:
        return left == right
    if len(left) == 10 or len(right) == 10:
        return left[:10] == right[:10]
    li, ri = _instant(left), _instant(right)
    if li is not None and ri is not None:
        if (li.tzinfo is None) != (ri.tzinfo is None):
            # One side is naive: we were not told its zone, and inventing one
            # is how a false agreement gets published. Compare what both stated.
            return left[:10] == right[:10] and left[11:16] == right[11:16]
        return li == ri
    return left == right


#: Consecutive walls on one host before we stop knocking on it. One wall is one
#: listing's hole (a members-only show behind an open desk); a RUN of them is a
#: door that has closed, and knocking five hundred more times is what gets an
#: address banned. The stop is ours and is reported as ours.
DEFAULT_WALL_STREAK_LIMIT = 3


def _same_place(a: Optional[str], b: Optional[str]) -> bool:
    """True when these two place statements name the SAME place.

    A detail page routinely states the venue the list stated PLUS its street —
    "The Fixture Room" and "The Fixture Room, 200 Placeholder St" are one venue
    described twice, not two venues. Calling that a disagreement fills the table
    with conflicts that are really elaborations, and a table nobody believes is
    worse than no table.

    The test is a TOKEN-BOUNDARY prefix, not a substring: the fuller statement
    has to BEGIN with the shorter one. Plain containment would read "Hall" and
    "Town Hall Annex" as one place, which is two venues in most towns.
    """
    left, right = _ws(a or "").casefold(), _ws(b or "").casefold()
    if not left or not right:
        return left == right
    if left == right:
        return True
    short, long = sorted((left, right), key=len)
    return long.startswith(short) and long[len(short)] in " ,-–—(/·|"


def follow(rows: Sequence[Happening], fetch: Callable[[str], PageFetch], *,
           limit: Optional[int] = None,
           read_ics: bool = True,
           wall_streak_limit: int = DEFAULT_WALL_STREAK_LIMIT) -> FollowRun:
    """Follow each row's own permalink and fill its holes from THAT page.

    Same host only: a `listing_url` on another host is not this desk's page, so
    it is reported `off_host` and never fetched.

    ONE KNOCK PER PAGE, never retried — a page is fetched at most once in a run
    and a wall is that page's hole, queued for the human claim path. A wall does
    NOT close the desk: a members-only listing on an open desk is one hole, and
    treating it as the desk's answer would blank rows the desk published (the
    coverage direction ONE-LIVE-COVERAGE-LAW forbids). What does stop us is a
    RUN of `wall_streak_limit` consecutive walls on one host — a door that has
    closed — and those later pages are marked `not_knocked`, OUR limit, never
    counted among the walls we met.
    """
    if not callable(fetch):
        raise EventPageError("follow() needs a callable fetch(url) -> PageFetch")
    run = FollowRun()
    #: What each permalink ANSWERED, keyed on its compare form. A second row at
    #: the same address is not re-fetched — one knock per page — but it is not
    #: skipped either (evaluator finding, PR #237 r2): skipping left a duplicate
    #: row carrying a list night the event page contradicts, with no conflict
    #: recorded, so a reader could still be shown a date that page disputes. The
    #: page's answer is applied to EVERY row at that address; only the knock is
    #: spent once.
    answered: Dict[str, FollowVisit] = {}

    for row in rows:
        if limit is not None and len(run.visits) >= limit:
            run.rows.append(row)
            continue
        url = (row.listing_url or "").strip()
        if not url:
            run.rows.append(row)
            continue
        key = _norm_url(url)
        earlier = answered.get(key)
        if earlier is not None:
            if earlier.statement is None:
                # The page never opened. Nothing to apply; the row keeps what
                # the list gave it, and the hole says why, once per row.
                repeat = replace_visit(earlier, row)
                run.visits.append(repeat)
                run.rows.append(row)
                continue
            filled, repeat = apply(row, earlier.statement)
            repeat.listing_url = url
            repeat.title = row.title
            repeat.status = earlier.status
            repeat.fetched_url = earlier.fetched_url
            repeat.reused = True
            run.visits.append(repeat)
            run.rows.append(filled)
            continue

        visit = FollowVisit(listing_url=url, title=row.title)
        if not _same_host(url, row.source_url):
            visit.off_host = True
            visit.blocked_reason = (
                f"off-host permalink ({urlsplit(url).netloc}) — same-host only")
            run.visits.append(visit)
            run.rows.append(row)
            answered[key] = visit
            continue

        host = urlsplit(url).netloc.lower()
        if host in run.closed_hosts:
            visit.not_knocked = True
            visit.walled = True
            visit.blocked_reason = (
                f"not knocked — {host} walled {wall_streak_limit} times in a row "
                f"earlier this run; OUR stop, not this listing's answer")
            run.visits.append(visit)
            run.rows.append(row)
            answered[key] = visit
            continue

        try:
            fetched = fetch(url)
        except Exception as exc:  # noqa: BLE001 — a fetcher blowing up is one page's news
            text = f"{type(exc).__name__}: {exc}"
            visit.blocked_reason = f"fetch raised: {text}"[:300]
            visit.walled = bool(_WALL_CODE_RE.search(text))
            _record_wall(run, host, visit, wall_streak_limit)
            run.visits.append(visit)
            run.rows.append(row)
            answered[key] = visit
            continue

        if not isinstance(fetched, PageFetch):
            raise EventPageError(
                f"fetch({url!r}) returned {type(fetched).__name__}; follow() needs a "
                f"PageFetch so status, body and the landing URL are all classifiable")

        visit.status = fetched.status
        visit.fetched_url = fetched.landed_url

        verdict = demote_on_response(
            DECLARED_PUBLIC, status=fetched.status,
            final_url=fetched.final_url, error=fetched.error)
        if verdict.is_closed_door:
            visit.blocked_reason = f"class D on contact — {verdict.reason}"
            visit.walled = True
            _record_wall(run, host, visit, wall_streak_limit)
            run.visits.append(visit)
            run.rows.append(row)
            answered[key] = visit
            continue
        if fetched.error:
            visit.blocked_reason = f"fetch failed: {fetched.error}"[:300]
            visit.walled = bool(fetched.walled) or bool(_WALL_CODE_RE.search(fetched.error))
            _record_wall(run, host, visit, wall_streak_limit)
            run.visits.append(visit)
            run.rows.append(row)
            answered[key] = visit
            continue
        if fetched.status is not None and fetched.status >= 400:
            visit.blocked_reason = f"HTTP {fetched.status}"
            run.visits.append(visit)
            run.rows.append(row)
            answered[key] = visit
            continue
        if not (fetched.body or "").strip():
            visit.blocked_reason = "page came back empty"
            run.visits.append(visit)
            run.rows.append(row)
            answered[key] = visit
            continue

        landed = fetched.landed_url
        if not _same_host(landed, row.source_url):
            # A redirect off the desk's host is a different publisher's page.
            visit.off_host = True
            visit.blocked_reason = (
                f"redirected off-host to {urlsplit(landed).netloc} — not read")
            run.visits.append(visit)
            run.rows.append(row)
            answered[key] = visit
            continue

        ics_fetch = None
        if read_ics:
            def ics_fetch(link: str, _f=fetch) -> PageFetch:  # noqa: E306
                return _f(link)

        run.wall_streaks[host] = 0
        statement = read_event_page(fetched.body, landed, ics_fetch=ics_fetch)
        filled, applied = apply(row, statement)
        applied.listing_url = url
        applied.title = row.title
        applied.status = fetched.status
        applied.fetched_url = fetched.landed_url
        run.visits.append(applied)
        run.rows.append(filled)
        answered[key] = applied

    return run


def replace_visit(earlier: FollowVisit, row: Happening) -> FollowVisit:
    """A second row at an address that never opened: the same hole, said again
    for this row. `reused` keeps it out of every per-PAGE count."""
    return FollowVisit(
        listing_url=earlier.listing_url, title=row.title,
        fetched_url=earlier.fetched_url, status=earlier.status,
        blocked_reason=earlier.blocked_reason, walled=earlier.walled,
        off_host=earlier.off_host, not_knocked=earlier.not_knocked,
        queued=False, reused=True, row_when_after=row.when)


def _record_wall(run: FollowRun, host: str, visit: FollowVisit,
                 wall_streak_limit: int) -> None:
    """One met wall: queue it, and count the streak that may close the host."""
    if not visit.walled:
        run.wall_streaks[host] = 0
        return
    visit.queued = True
    streak = run.wall_streaks.get(host, 0) + 1
    run.wall_streaks[host] = streak
    if streak >= wall_streak_limit:
        run.closed_hosts.add(host)
        run.notes.append(
            f"{host}: {streak} walls in a row — no further pages knocked on this "
            f"run. This is OUR stop; the pages behind it are unread, not empty.")


def follow_table(run: FollowRun, *, limit: int = 20) -> str:
    """The founder's table: url | dated? | place? | blocked reason."""
    lines = ["| # | url | dated? | place? | blocked reason |",
             "|---:|---|---|---|---|"]
    for i, v in enumerate(run.visits[:limit], start=1):
        if v.blocked:
            dated = place = "—"
        else:
            st = v.statement
            dated = (f"yes ({st.when})" if st and st.when else
                     ("no (clock only)" if st and st.clock_only else "no"))
            place = f"yes" if st and st.place_text else "no"
        reason = _escape_cell(v.blocked_reason or "")
        lines.append(f"| {i} | {_escape_cell(v.listing_url)} | {dated} | {place} | {reason} |")
    return "\n".join(lines)


def _escape_cell(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\n", " ")
