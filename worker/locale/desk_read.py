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
from dataclasses import dataclass, field, replace
from html.parser import HTMLParser
from typing import Dict, List, Optional, Sequence, Tuple

from worker.importers.structured_feed import parse_jsonld
from worker.locale.kind_map import KindMap
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
#: Where a card may STATE its own category. Every one of these is a DECLARATION
#: — a `rel` the page wrote, a schema.org property, a class the page named after
#: its own taxonomy. None of it is a guess from the title, which is why a card
#: that declares nothing simply has no category (and lands on `other`).
_CATEGORYISH_CLASS_RE = re.compile(r"categor|section|genre|event-?type|tag\b", re.I)
_CATEGORY_ITEMPROPS = frozenset({"genre", "eventtype", "keywords"})
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
    #: What the DESK called this, verbatim, when it stated a category we map.
    #: None when the desk said nothing (or said something unmapped) — their
    #: label is recorded, never adopted as our schema.
    category_text: Optional[str] = None
    #: Which authority set `kind`: the desk's own category, the door's declared
    #: scope, or the `other` fallback. On the row, so a table can never present
    #: a fallback as a reading.
    kind_source: str = "door_scope"


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
    #: How many times a second reading of the SAME card was merged into the
    #: first (its structured statement and its printed HTML). Reported, so a
    #: page's row count is never quietly two numbers.
    merged_readings: int = 0
    #: Categories this page STATED that the committed mapping does not cover.
    #: Printed by the tools so the table is completed from the desk's own words
    #: rather than from anyone's memory of its taxonomy.
    unmapped_categories: List[str] = field(default_factory=list)

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


def _matching_href(node: _Node, rx) -> Optional[str]:
    """The listing door this anchor points at, if it points at one."""
    if node.tag != "a":
        return None
    href = _ws(node.attrs.get("href") or "")
    return href if href and rx.search(href) else None


def _by_listing_link(root: _Node, rx) -> List[Tuple[_Node, str]]:
    """Rows anchored on the desk's OWN listing door.

    The founder's rule for this desk, verbatim: "Event identity for Austin
    Chronicle is not a CSS card." It is the `/event/{slug}-{id}` address the
    desk gives each listing, so that is what a row is built around here.

    For each distinct listing URL on the page, the row is the OUTERMOST
    row-shaped ancestor that still contains exactly that one listing — the
    whole card, with its venue and its date, and never the wrapper above it
    that holds the next listing too. Containment is counted in DISTINCT URLs,
    not in anchors, because a card routinely links its image and its title to
    the same event; counting anchors would refuse to climb out of either one
    and would return two half-rows for one listing.

    A page where nothing matches yields nothing, and the caller falls through
    to the tiers below: this tier never turns a readable page into an empty
    desk.
    """
    anchors: List[Tuple[_Node, str]] = []
    for node in root.descendants():
        href = _matching_href(node, rx)
        if href:
            anchors.append((node, href))
    if not anchors:
        return []

    counts: Dict[int, int] = {}

    def distinct_below(node: _Node) -> int:
        key = id(node)
        got = counts.get(key)
        if got is None:
            seen = {href for d in node.descendants()
                    if (href := _matching_href(d, rx))}
            got = len(seen)
            counts[key] = got
        return got

    out: List[Tuple[_Node, str]] = []
    claimed: set = set()
    for anchor, href in anchors:
        chosen: _Node = anchor
        node = anchor.parent
        while node is not None and node.tag != "#root":
            if distinct_below(node) != 1:
                break
            if node.tag in _ROW_TAGS:
                chosen = node
            node = node.parent
        if id(chosen) in claimed:
            # The image link and the title link of one card climb to the same
            # card. One listing, one row.
            continue
        claimed.add(id(chosen))
        out.append((chosen, href))
    return out


def _select_rows(html: str, listing_url_pattern: Optional[str] = None,
                 ) -> Tuple[List[Tuple[_Node, Optional[str]]], Optional[str]]:
    """The rows one page states, and which tier found them.

    Tiers of decreasing confidence; the FIRST that yields anything wins, and
    the tiers are never mixed. Mixing them is how one listing becomes two rows
    — the card and the `<li>` wrapping it — and a duplicated public row is a
    worse failure than a missed one (the same under-segment-don't-over-segment
    discipline as `worker/segment.py`).

    The `listing_link` tier runs FIRST, and only for a door whose pack states
    where its listings live. It is first because that statement is the DESK's
    own account of its identity, while every tier below is a guess we make from
    the outside — and the guess is what failed: on the live list page of the
    desk this ticket names ([brand elided: a committed gate keeps brands in the
    pack so a locale module stays data]) the `class` tier matches an outermost
    wrapper and returns the
    entire page as ONE row (40 pages read, one row out, its title eleven
    headlines and its place forty venues; run 33989221309). A door that states
    nothing reads exactly as it did before.

    Each row is returned with the listing URL it was anchored on, so the row's
    identity is the address the desk gave it rather than whichever link happens
    to appear first inside the card.
    """
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()
    root = builder.root

    if listing_url_pattern:
        try:
            rx = re.compile(listing_url_pattern)
        except re.error as exc:
            # A door that cannot say where its listings live is a
            # misconfiguration, and misconfiguration fails LOUDLY here rather
            # than quietly falling through to the tier that swallows the page.
            raise DeskReadError(
                f"listing_url_pattern {listing_url_pattern!r} is not a usable "
                f"regex ({exc})") from exc
        linked = _by_listing_link(root, rx)
        if linked:
            return linked, "listing_link"

    for name, rows in (
        ("microdata", _topmost(root, _is_event_itemscope)),
        ("class", _topmost(root, _is_eventish)),
        ("time", _innermost_dated(root)),
    ):
        if rows:
            return [(node, None) for node in rows], name
    return [], None


def _row_fields(node: _Node, *, base_url: str,
                listing_href: Optional[str] = None) -> Dict[str, object]:
    """Reduce one row node to its stated fields, plus the category signals it
    declared (`category_labels`, `hrefs`) for a committed mapping to read.

    Every value returned is either an attribute the page declared or a substring
    of the text the page printed. Nothing is composed, normalized into an
    instant, or inferred.
    """
    text_parts: List[str] = []
    time_text_parts: List[str] = []
    name_parts: List[str] = []
    heading_parts: List[str] = []
    anchor_parts: List[str] = []
    listing_anchor_parts: List[str] = []
    place_parts: List[str] = []
    category_parts: List[str] = []
    category_labels: List[str] = []
    hrefs: List[str] = []
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

    def _is_categoryish(n: "_Node") -> bool:
        itemprop = (n.attrs.get("itemprop") or "").lower()
        if itemprop in _CATEGORY_ITEMPROPS:
            return True
        rel = (n.attrs.get("rel") or "").lower()
        if "categor" in rel or "tag" in rel.split():
            return True
        for attr in ("class", "id"):
            if _CATEGORYISH_CLASS_RE.search(n.attrs.get(attr) or ""):
                return True
        return False

    def walk(n: _Node, *, in_time: bool, in_name: bool, in_heading: bool,
             in_anchor: bool, in_place: bool, in_category: bool,
             in_listing_anchor: bool = False) -> None:
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
                if in_category:
                    category_parts.append(child)
                if in_listing_anchor:
                    # The text of the link to THIS listing's own door. A card
                    # prints other links too — its venue, its section, the
                    # masthead — and concatenating them made a title like
                    # "Gestures of Care [+ the masthead's own link text]"
                    # (brand elided: brands live in the pack, never in code).
                    listing_anchor_parts.append(child)
                if in_name:
                    name_parts.append(child)
                elif in_heading:
                    # A heading OUTRANKS an anchor: a card's title is normally a
                    # link inside its heading, and a card's other links (its
                    # category, its venue) are anchors too. Reading anchors first
                    # concatenated the category onto the title.
                    heading_parts.append(child)
                elif in_anchor:
                    anchor_parts.append(child)
                continue
            itemprop = (child.attrs.get("itemprop") or "").lower()
            if child.tag == "time":
                value = _ws(child.attrs.get("datetime") or "")
                if value and time_iso is None and _ISO_DATETIME_RE.match(value):
                    time_iso = value
            declared = declared_date(child)
            if declared and itemprop_date is None:
                itemprop_date = declared
            if child.tag == "a":
                candidate = _ws(child.attrs.get("href") or "")
                if candidate and not candidate.startswith(
                        ("#", "javascript:", "mailto:", "tel:")):
                    if href is None:
                        href = candidate
                    if candidate not in hrefs:
                        hrefs.append(candidate)
            child_category = in_category or _is_categoryish(child)
            if child_category and itemprop in _CATEGORY_ITEMPROPS:
                # schema.org states a value in `content` when the visible text
                # is something else; that stated value is the category.
                stated = _ws(child.attrs.get("content") or "")
                if stated and stated not in category_labels:
                    category_labels.append(stated)
            walk(
                child,
                in_time=in_time or child.tag == "time",
                in_name=in_name or itemprop == "name",
                in_heading=in_heading or child.tag in ("h1", "h2", "h3", "h4", "h5", "h6"),
                in_anchor=in_anchor or child.tag == "a",
                in_listing_anchor=in_listing_anchor or (
                    bool(listing_href) and child.tag == "a"
                    and _ws(child.attrs.get("href") or "") == listing_href),
                in_place=(
                    in_place
                    or itemprop in ("location", "address")
                    or bool(_PLACEISH_RE.search(child.attrs.get("class") or ""))
                ),
                in_category=child_category,
            )
            if child_category and not in_category:
                # Close this category element: whatever text it printed is one
                # label, kept verbatim and kept SEPARATE from its siblings.
                label = _ws(" ".join(category_parts))
                del category_parts[:]
                if label and label not in category_labels:
                    category_labels.append(label)

    # The row node's OWN attributes count too: a card may itself be the anchor,
    # or itself carry itemprop="url".
    if node.tag == "a":
        own = _ws(node.attrs.get("href") or "")
        if own and not own.startswith(("#", "javascript:", "mailto:", "tel:")):
            href = own
    itemprop_date = itemprop_date or declared_date(node)
    if node.tag == "a":
        own_href = _ws(node.attrs.get("href") or "")
        if own_href and not own_href.startswith(("#", "javascript:", "mailto:", "tel:")):
            if own_href not in hrefs:
                hrefs.append(own_href)
    walk(node, in_time=node.tag == "time", in_name=False, in_heading=False,
         in_anchor=node.tag == "a", in_place=False, in_category=False,
         in_listing_anchor=bool(listing_href) and node.tag == "a"
         and _ws(node.attrs.get("href") or "") == listing_href)

    when_text = _ws(" ".join(time_text_parts)) or None
    when = time_iso or itemprop_date

    # Title, in authority order: the row's own declared name, then its heading,
    # then its link text, then whatever text is left once the time text is
    # removed. Every branch returns text the page printed.
    title = (_ws(" ".join(name_parts)) or _ws(" ".join(heading_parts))
             or _ws(" ".join(listing_anchor_parts))
             or _ws(" ".join(anchor_parts)))
    if not title:
        leftover = _ws(" ".join(text_parts))
        if when_text and when_text in leftover:
            leftover = _ws(leftover.replace(when_text, " ", 1))
        title = _ws(leftover.lstrip("-\u2013\u2014\u2022\u00b7 ").strip())
    if listing_href:
        # The row was selected BECAUSE it holds this listing's own door, so
        # that door is its identity — not whichever link the card happens to
        # print first (a venue link, a "buy tickets" link, a share link).
        href = listing_href
    return {
        "title": title or None,
        "when": when,
        "when_text": when_text,
        "place_text": _ws(" ".join(place_parts)) or None,
        "listing_url": _absolutize(href, base_url) if href else None,
        # Everything the card DECLARED about its own category, for a committed
        # mapping to read. Lists, not strings — a card may state several.
        "category_labels": category_labels,
        "hrefs": [_absolutize(h, base_url) for h in hrefs],
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


def row_key(title: str, when: Optional[str], when_text: Optional[str],
            listing_url: Optional[str]) -> Tuple[str, str, str]:
    """The identity two READINGS of the same card share.

    A page is read twice — once as the structured statement it publishes
    (JSON-LD), once as the HTML it prints — because real desks state different
    things in each. When the card declares its own address, that address is what
    makes the two readings the same card: the two readings routinely disagree on
    the FORM of the date (`2026-09-11T20:00:00-05:00` and the same instant in
    UTC), so keying on the date text would split one card into two rows and
    inflate every count downstream.

    With no declared address we fall back to title + whatever was said about
    when. Identity is used here ONLY to avoid counting one card twice; a card
    with neither an address nor a date still exists (ONE-LIVE-TRUST.md).
    """
    if listing_url and listing_url.strip():
        return ("url", listing_url.strip(), "")
    key = _dedupe_key(title, when, when_text)
    return ("t", key[0], key[1])


def fill_holes(kept: Happening, incoming: Happening) -> Happening:
    """Merge a second reading of the SAME card into the first, filling HOLES
    only. Nothing already stated is ever overwritten.

    This is same-page evidence in the sense ONE-LIVE-TRUST.md allows, and it is
    weaker still: no row here is published, nothing is written anywhere, and a
    value the first reading stated wins by construction. What it buys is that
    the structured reading's precise instant and the HTML reading's stated
    category end up on ONE row instead of two half-rows.
    """
    patch = {}
    for hole in ("when", "when_text", "place_text", "listing_url"):
        if getattr(kept, hole) is None and getattr(incoming, hole) is not None:
            patch[hole] = getattr(incoming, hole)
    if "when" in patch:
        patch["when_precision"] = _precision(patch["when"])
    # A kind the DESK stated outranks one we defaulted to. The reverse never
    # happens: a default never displaces a desk's own word.
    if kept.kind_source != "desk_category" and incoming.kind_source == "desk_category":
        patch["kind"] = incoming.kind
        patch["kind_source"] = incoming.kind_source
        patch["category_text"] = incoming.category_text
    return replace(kept, **patch) if patch else kept


def _dedupe_key(title: str, when: Optional[str], when_text: Optional[str]) -> Tuple[str, str]:
    return (_ws(title).casefold(), (when or when_text or "").strip().casefold())


def read(door: Door, html: str, *, base_url: Optional[str] = None,
         kind_map: Optional[KindMap] = None) -> DeskRead:
    """Read one public desk page into happening rows.

    `kind_map`, when given, is a committed mapping of THIS desk's own category
    labels onto our kinds (`worker.locale.kind_map`). A card that states a
    category the mapping covers takes that kind; a card that states nothing, or
    states something unmapped, falls back to the door's declared scope and then
    to `other`. The mapping can only ever change which of OUR kinds a row gets —
    it cannot make a row exist, disappear, or acquire a date.

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

    door_kind = door.declared_kind or KIND_OTHER
    door_kind_source = "door_scope" if door_kind != KIND_OTHER else "default"
    if kind_map is not None and not kind_map.applies_to(door.door_id):
        # A mapping for a DIFFERENT desk must never colour this desk's rows.
        result.notes.append(
            f"kind map {kind_map.map_id!r} does not claim this door; "
            f"kinds come from the door's declared scope")
        kind_map = None
    at: Dict[Tuple[str, str, str], int] = {}
    rows: List[Happening] = []

    def _add(title: Optional[str], when, when_text, place_text, listing_url,
             *, labels: Sequence[str] = (), hrefs: Sequence[str] = ()) -> None:
        if not title:
            result.skipped_untitled += 1
            return
        kind, kind_source, category_text = door_kind, door_kind_source, None
        if kind_map is not None:
            mapped, matched = kind_map.resolve(labels=labels, hrefs=hrefs)
            if mapped:
                kind, kind_source, category_text = mapped, "desk_category", matched
            for unmapped in kind_map.unmapped_from(labels=labels, hrefs=hrefs):
                if unmapped not in result.unmapped_categories:
                    result.unmapped_categories.append(unmapped)
        row = Happening(
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
            category_text=category_text,
            kind_source=kind_source,
        )
        key = row_key(row.title, row.when, row.when_text, row.listing_url)
        if key in at:
            # The same card, read a second way. Merge holes; never overwrite.
            index = at[key]
            merged = fill_holes(rows[index], row)
            if merged is not rows[index]:
                rows[index] = merged
            result.merged_readings += 1
            return
        at[key] = len(rows)
        rows.append(row)

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
        _add(ev.get("title"), ev.get("start_time"), None, place, ev.get("url"),
             hrefs=tuple(u for u in (ev.get("url"),) if u))

    # 2. The page's own HTML listing rows.
    try:
        html_rows, tier = _select_rows(html, door.listing_url_pattern)
    except DeskReadError:
        raise
    except Exception as exc:  # noqa: BLE001 — a pathological page must not lose the JSON-LD rows
        html_rows, tier = [], None
        result.notes.append(f"HTML parse raised ({exc}); JSON-LD rows still read")
    if tier:
        result.notes.append(f"HTML rows selected by the {tier} tier")
    for row_node, listing_href in html_rows:
        fields = _row_fields(row_node, base_url=source_url,
                             listing_href=listing_href)
        _add(fields["title"], fields["when"], fields["when_text"],
             fields["place_text"], fields["listing_url"],
             labels=tuple(fields.get("category_labels") or ()),
             hrefs=tuple(fields.get("hrefs") or ()))

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
    if result.unmapped_categories:
        result.notes.append(
            f"{len(result.unmapped_categories)} category/categories this page "
            f"stated are not in the committed mapping "
            f"({', '.join(result.unmapped_categories[:8])}) — those rows kept "
            f"the door's kind; the mapping is completed from the desk's own "
            f"words, never from memory")
    return result
