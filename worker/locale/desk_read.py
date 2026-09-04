"""read(public_desk) — a desk page becomes happening rows, holes and all.

Founder, this session's ticket: "read(public_desk) -> happening rows (title,
when if on page, place text, via=desk). Unknown kind = other. No invented dates."

Every clause of that is a refusal to guess, and this module is built around the
three of them:

  * WHEN IF ON PAGE. A date is taken only from markup the page itself states as
    a date — a `<time datetime="...">` attribute, or a schema.org
    `Event.startDate`. Prose ("this Friday", "Labor Day weekend") is carried
    VERBATIM in `when_text` with `when=None`. Parsing prose into an instant
    would be inventing a date, and a wrong clock on a public row is worse than
    an honest hole (ONE-LIVE-TRUST.md: "A missing minute is not a missing
    night").
  * UNKNOWN KIND = OTHER. The kind comes from the DOOR's declared scope
    (`worker.locale.pack.Door.declared_kind`) — a station's concert calendar
    states `music` for everything behind it. A general desk states nothing, so
    its rows are `other`. Kind is never read out of a title: that is a guess,
    and it would weight one category over another (ONE-LIVE-VISION.md, "no
    category weighting").
  * VIA = DESK. The card's trust statement is the door's own brand, which lives
    in the pack, never here (ONE-LIVE-TRUST.md: "Card grade: `via [door]`").

WHAT THIS REPLACES, and why (ticket item 4). The licensed-import path reaches
happening rows through `worker.importers.structured_feed.normalize_structured`,
which "Returns None when there is no stable id or no title". That None is an
EXISTENCE answer given by an IDENTITY test: a desk row whose markup states no
uid and no listing url simply ceases to exist, however plainly the desk printed
it. ONE-LIVE-TRUST.md forbids exactly that shape ("Existence must not use
mutation tests ... If a gate answers existence with a field or mutation test,
the gate is wrong"). So this path reuses that module's PARSER (`parse_jsonld`,
one home for "which JSON-LD keys mean what") and stops before its normalizer: a
row here exists because a trusted door printed it. An identity, when the markup
states one, is RECORDED on `listing_url` for a later match — it is never a
condition of existing.

The one gate on this path is a DOOR gate, `Door.readable`: a listable door type,
public, with a read path. A wall is never fetched and a copy farm is never a
listing — both are door facts, decided before any page is read.

Pure: stdlib only (plus this repo's own parsers), no network, no DB, no clock,
no model. `read()` is handed bytes somebody else fetched.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, List, Optional, Sequence, Tuple

from worker.importers.structured_feed import parse_jsonld
from worker.locale.pack import KIND_OTHER, Door

log = logging.getLogger(__name__)

#: Intakes this reader understands. Anything else raises rather than returning
#: an empty list that would read as "this desk had nothing on".
READABLE_INTAKES = frozenset({"html", "json_ld"})

#: Cap on rows returned from one page. A desk with more than this is truncated
#: and the truncation is REPORTED on the result, never silent.
MAX_ROWS = 500

_WS_RE = re.compile(r"\s+")
_EVENT_ITEMTYPE_RE = re.compile(r"schema\.org/[A-Za-z]*Event\b", re.I)
_EVENTISH_CLASS_RE = re.compile(r"\b(?:event|listing|card|show|gig|happening)", re.I)
_PLACEISH_RE = re.compile(r"venue|location|place|where", re.I)
#: A `datetime` attribute we will accept as the page's OWN machine date. ISO
#: date or date+time; anything else (a duration, a bare year, a weekday) is kept
#: as text instead of being coerced.
_ISO_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?$")

_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
})
#: Containers that can hold one listing. `time` is not here: it marks a row, it
#: is not a row.
_ROW_TAGS = ("li", "article", "tr", "div", "section")


class DeskReadError(ValueError):
    """The desk cannot be read as asked — a closed door, or an intake this
    reader does not implement. Raised, never downgraded to an empty result.
    """


def _ws(value: str) -> str:
    return _WS_RE.sub(" ", value or "").strip()


@dataclass(frozen=True)
class Happening:
    """One row a desk printed. Holes are expected and are represented as None,
    never as a filled-in guess.
    """

    title: str
    when: Optional[str]           # ISO instant/date the PAGE stated, or None
    when_text: Optional[str]      # the date text the page printed, verbatim
    when_precision: Optional[str] # "datetime" | "date" | None
    place_text: Optional[str]
    via: Optional[str]
    kind: str
    door_id: str
    door_type: str
    locale_id: str
    source_url: str               # the desk page this was read from
    listing_url: Optional[str]    # the row's OWN address, when it stated one


@dataclass
class DeskRead:
    """What one page yielded, including what it did not."""

    door_id: str
    door_type: str
    via: Optional[str]
    source_url: str
    rows: List[Happening] = field(default_factory=list)
    skipped_untitled: int = 0
    truncated_at: Optional[int] = None
    notes: List[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.rows)

    @property
    def dated(self) -> int:
        return sum(1 for r in self.rows if r.when)


# --------------------------------------------------------------------------
# HTML row collection
# --------------------------------------------------------------------------

class _Node:
    """One element of a minimal parse tree: tag, attributes, ordered children
    (nodes and text). A tree rather than a running parser state, because the
    row-selection rules below are about CONTAINMENT, and containment questions
    asked of a stateful parser answer whichever element opened first — which is
    how a `<div class="feed">` wrapper swallows every listing inside it.
    """

    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag: str, attrs: Dict[str, str], parent: Optional["_Node"] = None) -> None:
        self.tag = tag
        self.attrs = attrs
        self.children: List[object] = []
        self.parent = parent

    def descendants(self):
        for child in self.children:
            if isinstance(child, _Node):
                yield child
                yield from child.descendants()

    def has_tag(self, tag: str) -> bool:
        return any(n.tag == tag for n in self.descendants())


class _TreeBuilder(HTMLParser):
    """Build the tree. Unbalanced markup closes implicitly at the nearest match,
    the same tolerance html.parser gives everywhere else in this repo."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("#root", {})
        self._cur = self.root

    @staticmethod
    def _attrs(attrs) -> Dict[str, str]:
        return {k.lower(): (v if v is not None else "") for k, v in attrs}

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, self._attrs(attrs), self._cur)
        self._cur.children.append(node)
        if tag not in _VOID_TAGS:
            self._cur = node

    def handle_startendtag(self, tag, attrs):
        self._cur.children.append(_Node(tag, self._attrs(attrs), self._cur))

    def handle_endtag(self, tag):
        node = self._cur
        while node is not self.root:
            if node.tag == tag:
                self._cur = node.parent or self.root
                return
            node = node.parent or self.root
        # No matching open tag: a stray close, ignored rather than fatal.

    def handle_data(self, data):
        self._cur.children.append(data)


def _is_event_itemscope(node: _Node) -> bool:
    return "itemscope" in node.attrs and bool(
        _EVENT_ITEMTYPE_RE.search(node.attrs.get("itemtype") or ""))


def _is_eventish(node: _Node) -> bool:
    return node.tag in _ROW_TAGS and bool(
        _EVENTISH_CLASS_RE.search(node.attrs.get("class") or ""))


def _topmost(root: _Node, predicate) -> List[_Node]:
    """Matching nodes, outermost-wins: a match nested inside another match is
    part of that row, not a second row."""
    out: List[_Node] = []

    def walk(node: _Node) -> None:
        for child in node.children:
            if not isinstance(child, _Node):
                continue
            if predicate(child):
                out.append(child)
            else:
                walk(child)

    walk(root)
    return out


def _innermost_dated(root: _Node) -> List[_Node]:
    """Row-shaped nodes containing a `<time>`, INNERMOST-wins.

    The opposite rule to `_topmost`, deliberately: tier 3 matches any row-shaped
    tag, so its outermost match is usually a page wrapper. The smallest
    row-shaped element that still contains a date is the listing.
    """
    out: List[_Node] = []

    def walk(node: _Node) -> bool:
        """True when this subtree already claimed a row."""
        claimed = False
        for child in node.children:
            if isinstance(child, _Node) and walk(child):
                claimed = True
        if claimed:
            return True
        if node.tag in _ROW_TAGS and node.has_tag("time"):
            out.append(node)
            return True
        return False

    for child in root.children:
        if isinstance(child, _Node):
            walk(child)
    return out


def _select_rows(html: str) -> Tuple[List[_Node], Optional[str]]:
    """The rows one page states, and which tier found them.

    Three tiers of decreasing confidence; the FIRST that yields anything wins,
    and the tiers are never mixed. Mixing them is how one listing becomes two
    rows — the card and the `<li>` wrapping it — and a duplicated public row is
    a worse failure than a missed one (the same under-segment-don't-over-segment
    discipline as `worker/segment.py`).
    """
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()
    root = builder.root
    for name, rows in (
        ("microdata", _topmost(root, _is_event_itemscope)),
        ("class", _topmost(root, _is_eventish)),
        ("time", _innermost_dated(root)),
    ):
        if rows:
            return rows, name
    return [], None


def _row_fields(node: _Node, *, base_url: str) -> Dict[str, Optional[str]]:
    """Reduce one row node to (title, when, when_text, place_text, listing_url).

    Every value returned is either an attribute the page declared or a substring
    of the text the page printed. Nothing is composed, normalized into an
    instant, or inferred.
    """
    text_parts: List[str] = []
    time_text_parts: List[str] = []
    name_parts: List[str] = []
    heading_parts: List[str] = []
    anchor_parts: List[str] = []
    place_parts: List[str] = []
    time_iso: Optional[str] = None
    itemprop_date: Optional[str] = None
    href: Optional[str] = None

    def declared_date(n: _Node) -> Optional[str]:
        itemprop = (n.attrs.get("itemprop") or "").lower()
        if itemprop in ("startdate", "startdatetime"):
            value = _ws(n.attrs.get("content") or n.attrs.get("datetime") or "")
            if value and _ISO_DATETIME_RE.match(value):
                return value
        return None

    def walk(n: _Node, *, in_time: bool, in_name: bool, in_heading: bool,
             in_anchor: bool, in_place: bool) -> None:
        nonlocal time_iso, itemprop_date, href
        for child in n.children:
            if isinstance(child, str):
                if not _ws(child):
                    continue
                text_parts.append(child)
                if in_time:
                    time_text_parts.append(child)
                if in_place:
                    place_parts.append(child)
                if in_name:
                    name_parts.append(child)
                elif in_anchor:
                    anchor_parts.append(child)
                elif in_heading:
                    heading_parts.append(child)
                continue
            itemprop = (child.attrs.get("itemprop") or "").lower()
            if child.tag == "time":
                value = _ws(child.attrs.get("datetime") or "")
                if value and time_iso is None and _ISO_DATETIME_RE.match(value):
                    time_iso = value
            declared = declared_date(child)
            if declared and itemprop_date is None:
                itemprop_date = declared
            if child.tag == "a" and href is None:
                candidate = _ws(child.attrs.get("href") or "")
                if candidate and not candidate.startswith(
                        ("#", "javascript:", "mailto:", "tel:")):
                    href = candidate
            walk(
                child,
                in_time=in_time or child.tag == "time",
                in_name=in_name or itemprop == "name",
                in_heading=in_heading or child.tag in ("h1", "h2", "h3", "h4", "h5", "h6"),
                in_anchor=in_anchor or child.tag == "a",
                in_place=(
                    in_place
                    or itemprop in ("location", "address")
                    or bool(_PLACEISH_RE.search(child.attrs.get("class") or ""))
                ),
            )

    # The row node's OWN attributes count too: a card may itself be the anchor,
    # or itself carry itemprop="url".
    if node.tag == "a":
        own = _ws(node.attrs.get("href") or "")
        if own and not own.startswith(("#", "javascript:", "mailto:", "tel:")):
            href = own
    itemprop_date = itemprop_date or declared_date(node)
    walk(node, in_time=node.tag == "time", in_name=False, in_heading=False,
         in_anchor=node.tag == "a", in_place=False)

    when_text = _ws(" ".join(time_text_parts)) or None
    when = time_iso or itemprop_date

    # Title, in authority order: the row's own declared name, then its heading,
    # then its link text, then whatever text is left once the time text is
    # removed. Every branch returns text the page printed.
    title = (_ws(" ".join(name_parts)) or _ws(" ".join(heading_parts))
             or _ws(" ".join(anchor_parts)))
    if not title:
        leftover = _ws(" ".join(text_parts))
        if when_text and when_text in leftover:
            leftover = _ws(leftover.replace(when_text, " ", 1))
        title = _ws(leftover.lstrip("-\u2013\u2014\u2022\u00b7 ").strip())
    return {
        "title": title or None,
        "when": when,
        "when_text": when_text,
        "place_text": _ws(" ".join(place_parts)) or None,
        "listing_url": _absolutize(href, base_url) if href else None,
    }


def _absolutize(href: str, base_url: str) -> str:
    """Resolve a row's own href against the desk page. `urljoin` handles an
    already-absolute href by returning it unchanged, so a row that states a full
    address keeps it exactly.
    """
    from urllib.parse import urljoin
    try:
        return urljoin(base_url, href)
    except ValueError:
        return href


def _precision(when: Optional[str]) -> Optional[str]:
    if not when:
        return None
    return "date" if len(when.strip()) == 10 else "datetime"


def _dedupe_key(title: str, when: Optional[str], when_text: Optional[str]) -> Tuple[str, str]:
    return (_ws(title).casefold(), (when or when_text or "").strip().casefold())


def read(door: Door, html: str, *, base_url: Optional[str] = None) -> DeskRead:
    """Read one public desk page into happening rows.

    `door` must be readable (`Door.readable`) — that is the only gate, and it is
    a door fact, not a fact about any row. A wall or a copy farm raises here
    rather than being quietly fetched-and-dropped somewhere downstream.

    Rows come from two readers over the SAME page, because a real desk uses
    both: the page's schema.org Event JSON-LD (parsed by the repo's one JSON-LD
    authority) and its own HTML listing rows. They are merged and de-duplicated
    on (title, when) so a page that states an event twice yields it once.
    """
    if not isinstance(door, Door):
        raise DeskReadError(f"read() takes a Door, got {type(door).__name__}")
    if not door.readable:
        raise DeskReadError(
            f"door {door.door_id!r} is not a readable public desk "
            f"(type={door.door_type}, public={door.public}, intake={door.intake}"
            + (f", blocked_reason={door.blocked_reason!r}" if door.blocked_reason else "")
            + ")")
    if door.intake not in READABLE_INTAKES:
        raise DeskReadError(
            f"door {door.door_id!r} declares intake {door.intake!r}; this reader "
            f"implements {sorted(READABLE_INTAKES)}. Refusing rather than "
            f"returning an empty read that would look like an empty desk.")

    source_url = base_url or door.url
    result = DeskRead(
        door_id=door.door_id, door_type=door.door_type, via=door.via,
        source_url=source_url,
    )
    if not isinstance(html, str) or not html.strip():
        result.notes.append("empty page body — nothing read (not 'nothing on')")
        return result

    kind = door.declared_kind or KIND_OTHER
    seen: set = set()
    rows: List[Happening] = []

    def _add(title: Optional[str], when, when_text, place_text, listing_url) -> None:
        if not title:
            result.skipped_untitled += 1
            return
        key = _dedupe_key(title, when, when_text)
        if key in seen:
            return
        seen.add(key)
        rows.append(Happening(
            title=_ws(title),
            when=when,
            when_text=when_text,
            when_precision=_precision(when),
            place_text=place_text,
            via=door.via,
            kind=kind,
            door_id=door.door_id,
            door_type=door.door_type,
            locale_id=door.locale_id,
            source_url=source_url,
            listing_url=listing_url,
        ))

    # 1. The page's own structured statement. parse_jsonld keeps every Event
    #    node whatever fields it lacks; we deliberately do NOT continue into
    #    normalize_structured, whose "no stable id or no title -> None" is the
    #    identity-gated existence test this path replaces.
    try:
        ld_events = parse_jsonld(html)
    except Exception as exc:  # noqa: BLE001 — a pathological page must not lose the HTML rows
        ld_events = []
        result.notes.append(f"JSON-LD parse raised ({exc}); HTML rows still read")
    for ev in ld_events:
        place = ev.get("venue_name") or ev.get("venue_address") or ev.get("venue_city")
        _add(ev.get("title"), ev.get("start_time"), None, place, ev.get("url"))

    # 2. The page's own HTML listing rows.
    try:
        html_rows, tier = _select_rows(html)
    except Exception as exc:  # noqa: BLE001 — a pathological page must not lose the JSON-LD rows
        html_rows, tier = [], None
        result.notes.append(f"HTML parse raised ({exc}); JSON-LD rows still read")
    if tier:
        result.notes.append(f"HTML rows selected by the {tier} tier")
    for row_node in html_rows:
        fields = _row_fields(row_node, base_url=source_url)
        _add(fields["title"], fields["when"], fields["when_text"],
             fields["place_text"], fields["listing_url"])

    if len(rows) > MAX_ROWS:
        result.truncated_at = MAX_ROWS
        result.notes.append(
            f"page yielded {len(rows)} rows; truncated to {MAX_ROWS} (cap, not an empty desk)")
        rows = rows[:MAX_ROWS]
    result.rows = rows
    if result.skipped_untitled:
        result.notes.append(
            f"{result.skipped_untitled} block(s) carried no title text and were "
            f"skipped — counted, never silently dropped")
    return result
