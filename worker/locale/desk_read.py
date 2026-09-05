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
from worker.locale.identity_patterns import (
    IdentityPattern,
    load_patterns,
    match as match_identity,
)
from worker.locale.kind_map import KindMap
from worker.locale.pack import KIND_OTHER, Door, ListingSelector

log = logging.getLogger(__name__)

#: Intakes this reader understands. Anything else raises rather than returning
#: an empty list that would read as "this desk had nothing on".
READABLE_INTAKES = frozenset({"html", "json_ld"})

#: Cap on rows returned from one page. A desk with more than this is truncated
#: and the truncation is REPORTED on the result, never silent.
MAX_ROWS = 500

_WS_RE = re.compile(r"\s+")
_EVENT_ITEMTYPE_RE = re.compile(r"schema\.org/[A-Za-z]*Event\b", re.I)
# There is deliberately NO "class contains event|listing|card|show|gig|happening"
# regex here. ONE-LIVE-ENTITY-SPLIT-LAW.md §2 names it in Forbidden, and it is
# what read 40 Chronicle pages into ONE row on 2026-09-05: a substring rule
# matches the page's own wrapper (`class="eventList"`) as readily as a card, and
# the wrapper's text is every listing concatenated. Identity is DECLARED by the
# page (structured data, or a permalink in the committed identity table) or, at
# tier 3, by a selector committed for that one door. Nothing is guessed.
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
#: Elements whose meaning is PAGE-level by the HTML spec, not by anyone's CSS
#: convention. They bound how far a row may grow — see `_has_page_level`.
_PAGE_LEVEL_TAGS = frozenset({"body", "main", "nav", "header", "footer", "aside", "h1"})


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
    #: Which rung of the ONE-LIVE-ENTITY-SPLIT-LAW.md §2 ladder split this page:
    #: `structured`, `permalink`, `structured+permalink`, `desk_selector`, or
    #: `unsplit`. On the result, never inferred from the row count, so a table
    #: can always say HOW a page became rows.
    identity_tier: Optional[str] = None
    #: Distinct happening identities the page declared (structured urls +
    #: permalinks matching the committed table). A page declaring more than one
    #: is a LIST (§2), and a list that produced one row would be the mash.
    identities_declared: int = 0
    #: What the winning HTML rung matched on, each with its GRADE: pattern ids
    #: for the permalink rung, committed selectors for the desk-selector rung. A
    #: `fixture_shape` reading is a real reading — it splits — but it rides in
    #: the report beside the rows it produced, so no table can present a shape
    #: nobody has seen live as one that was observed.
    identity_evidence: List[str] = field(default_factory=list)
    #: Rows whose stated address was the LIST's own URL (or the site root) and
    #: was therefore dropped to a hole. §2 Forbidden: "Using the list URL as
    #: `listing_url` of a single event." Counted, because zero is the claim this
    #: ticket has to be able to make.
    mash_blocked: int = 0

    @property
    def unsplit(self) -> bool:
        """True when the page declared no identity we could commit to. Zero
        rows, and a coverage defect on that DOOR (§4) — never a reason to emit
        one mashed row, and never 'this desk had nothing on'."""
        return self.identity_tier == "unsplit"

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


def _has_page_level(node: _Node) -> bool:
    """True when this element contains something the page states as PAGE-level
    structure.

    A listing card never contains a `<main>`, a `<nav>`, a page `<header>` or
    `<footer>`, or the page's `<h1>`. An element that does is the page AROUND
    the row, not the row. This is the bound that holds when the page declares
    only ONE identity and there is no second identity to stop the walk upward
    (evaluator finding, PR #234): without it a filtered page or a last page —
    one event link, one wrapper — is read from the wrapper, and `_row_fields`
    publishes the page heading concatenated onto the event's own title. That is
    the mash this module exists to remove, arriving on the pages nobody thinks
    to check.
    """
    return any(n.tag in _PAGE_LEVEL_TAGS for n in node.descendants())


def _class_tokens(node: _Node) -> frozenset:
    """The element's class attribute as WHOLE tokens.

    Whitespace-split, never substring-searched: this is the one place a class
    could be read, and reading it as tokens is what makes `card` unable to match
    `card-grid` (ONE-LIVE-ENTITY-SPLIT-LAW.md §2).
    """
    return frozenset((node.attrs.get("class") or "").split())


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


def _identity_of(url: str) -> str:
    """The address a row IS, with the fragment dropped.

    A fragment addresses a position inside a page, never a different happening,
    so `/event/foo-1#tickets` and `/event/foo-1` are one identity. The query is
    KEPT: two desks do use `?date=` to address two instances of one series, and
    collapsing those would delete a night.
    """
    from urllib.parse import urldefrag
    return urldefrag(url)[0]


def _identity_rows(root: _Node, *, base_url: str, patterns: Sequence[IdentityPattern],
                   ) -> List[Tuple[str, _Node, IdentityPattern]]:
    """Tier 2 — every link on the page that a COMMITTED pattern says is one
    happening, paired with the smallest element that holds it alone.

    The pairing is what makes this a split rather than a link list: a card's
    title, its date, its venue and its category are siblings of the permalink,
    so the row is the NEAREST row-shaped ancestor that declares this identity
    and no other and holds no page-level structure. Nearest, and only one, is
    the point: growing the row to the outermost such ancestor reads a
    single-identity page from its own wrapper and concatenates the page heading
    onto the event's title (evaluator finding, PR #234).

    When no ancestor qualifies — a bare list of links, a card built from tags
    this module does not treat as row-shaped — the anchor itself is the row: a
    title, a listing URL, and honest holes everywhere else. That is a row this
    pipeline is built to carry, and it is the direction to be wrong in: a hole
    is a hole, while a too-large row publishes somebody else's words as this
    happening's.
    """
    if not patterns:
        return []
    anchors: List[Tuple[str, _Node, IdentityPattern]] = []
    beneath: Dict[int, frozenset] = {}

    def visit(node: _Node) -> frozenset:
        found: set = set()
        if node.tag == "a":
            href = _ws(node.attrs.get("href") or "")
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                url = _identity_of(_absolutize(href, base_url))
                hit = match_identity(url, patterns)
                if hit is not None:
                    found.add(url)
                    anchors.append((url, node, hit))
        for child in node.children:
            if isinstance(child, _Node):
                found |= visit(child)
        frozen = frozenset(found)
        beneath[id(node)] = frozen
        return frozen

    visit(root)

    out: List[Tuple[str, _Node, IdentityPattern]] = []
    for url, anchor, hit in anchors:
        alone = frozenset({url})
        row = anchor
        node = anchor.parent
        while node is not None and node.tag != "#root":
            if node.tag in _PAGE_LEVEL_TAGS or beneath.get(id(node)) != alone:
                # The page around the row, or an element holding a second
                # identity. Either way the row ends below here.
                break
            if node.tag in _ROW_TAGS and not _has_page_level(node):
                row = node
                break
            node = node.parent
        out.append((url, row, hit))
    return out


def _matches_selector(node: _Node, selector: ListingSelector) -> bool:
    if node.tag != selector.tag:
        return False
    if not set(selector.class_tokens) <= _class_tokens(node):
        return False
    if selector.container_tag is None:
        return True
    wanted = set(selector.container_class_tokens)
    parent = node.parent
    while parent is not None and parent.tag != "#root":
        if parent.tag == selector.container_tag and wanted <= _class_tokens(parent):
            return True
        parent = parent.parent
    return False


def _selector_rows(root: _Node,
                   selectors: Sequence[ListingSelector]) -> List[_Node]:
    """Tier 3 — rows a selector committed FOR THIS DOOR names. Empty when the
    door committed none, which is the normal case and lands the page on
    `unsplit` rather than on a guess.

    A match that CONTAINS another match is a wrapper, not a row, and is dropped.
    That is the opposite of the outermost-wins rule the structured tier uses,
    and deliberately so: the two mistakes are not symmetrical. Taking the outer
    element of `<div class="event"><div class="event">…` yields ONE row holding
    every listing's text — the mash this law exists to remove. Taking the inner
    ones yields rows that may be missing a field a sibling stated: a hole, which
    this pipeline carries honestly.
    """
    if not selectors:
        return []

    def matches(node: _Node) -> bool:
        return any(_matches_selector(node, sel) for sel in selectors)

    hits: List[_Node] = [n for n in root.descendants() if matches(n)]
    return [n for n in hits if not any(matches(d) for d in n.descendants())]


def _row_fields(node: _Node, *, base_url: str) -> Dict[str, object]:
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
             in_anchor: bool, in_place: bool, in_category: bool) -> None:
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
         in_anchor=node.tag == "a", in_place=False, in_category=False)

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


_PATTERN_CACHE: List[Tuple[IdentityPattern, ...]] = []


def _committed_patterns() -> Tuple[IdentityPattern, ...]:
    """The committed identity table, read once per process.

    Raises (via `load_patterns`) when the table is missing or malformed rather
    than falling back to an empty tuple: an empty table silently demotes every
    permalink page to `unsplit`, which would read as "these desks declare
    nothing" when the truth is that we lost our own data file.
    """
    if not _PATTERN_CACHE:
        _PATTERN_CACHE.append(load_patterns())
    return _PATTERN_CACHE[0]


def _is_list_url(candidate: str, source_url: str) -> bool:
    """True when this address is the LIST we read, not a row on it.

    Two shapes, both from the 2026-09-05 live run that mashed 40 Chronicle pages
    into one row keyed `url:https://www.austinchronicle.com`:

      * A SITE ROOT (`/` with no query) is never one happening — it is the
        masthead link every page prints.
      * The SAME host and path as the page being read is the list itself. The
        query is ignored on purpose: `?page=3` addresses another page OF the
        list, not an event on it.
    """
    from urllib.parse import urlsplit
    c, src = urlsplit(candidate or ""), urlsplit(source_url or "")
    cpath = (c.path or "/").rstrip("/") or "/"
    spath = (src.path or "/").rstrip("/") or "/"
    if cpath == "/" and not c.query:
        return True
    return ((c.hostname or "").lower() == (src.hostname or "").lower()
            and cpath == spath)


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
         kind_map: Optional[KindMap] = None,
         patterns: Optional[Sequence[IdentityPattern]] = None) -> DeskRead:
    """Read one public desk page into happening rows, by the SPLIT LADDER.

    ONE-LIVE-ENTITY-SPLIT-LAW.md §2: a page that declares more than one
    happening identity is a LIST, and a list is never one happening. Identity is
    declared by the page; we do not guess it from CSS. Four rungs:

      1. `structured`   — schema.org Event the page publishes as data: JSON-LD
                          (array or graph) and Event microdata.
      2. `permalink`    — an href matching a committed row of
                          `sources/identity_patterns.json` for that host family.
      3. `desk_selector`— `(tag, whole class tokens)` committed for THIS door in
                          its locale pack (`Door.listing_selectors`).
      4. `unsplit`      — stop. ZERO rows, `unsplit` in the notes. A coverage
                          defect on that door, to be answered by a pattern or a
                          claim — never by one mashed row.

    WHERE THE LADDER APPLIES, stated exactly because it is the one judgement
    call in this module. Rung 1 is not a splitter: a structured Event node IS
    one happening, so there is no splitting decision to make and no way for that
    rung to mash a page. The SPLITTING decision is over the page's printed HTML,
    and there the ladder is strict — permalink, else committed desk selector,
    else unsplit; first rung that yields an identity wins and the rungs are
    never mixed with each other, so no weaker reading can add rows on top of a
    declared split. The structured rung is then merged onto that split by
    ADDRESS (`row_key`), which is a de-duplication, not a second splitter: a
    node and the card linking to the same address are one row, and a node the
    HTML never printed is still its own row.

    Reading it any other way fails the ticket's own acceptance bar — "rows ≈
    events on the page". A desk that publishes one promoted JSON-LD Event above
    thirty printed cards would otherwise become ONE row: the same mash this law
    exists to stop, arriving through the top rung instead of the bottom one.

    `patterns` defaults to the committed table. Passing a table is how a test
    states the shapes of ITS pages; there is no way to pass a bare regex, which
    is what keeps host knowledge in data.

    `kind_map`, when given, is a committed mapping of THIS desk's own category
    labels onto our kinds (`worker.locale.kind_map`). A card that states a
    category the mapping covers takes that kind; a card that states nothing, or
    states something unmapped, falls back to the door's declared scope and then
    to `other`. The mapping can only ever change which of OUR kinds a row gets —
    it cannot make a row exist, disappear, or acquire a date.

    `door` must be readable (`Door.readable`) — that is the only gate, and it is
    a door fact, not a fact about any row. A wall or a copy farm raises here
    rather than being quietly fetched-and-dropped somewhere downstream.

    Two readings of the SAME card (its structured statement and its printed
    HTML) are merged on the card's own address, so a page that states an event
    twice yields it once and both readings' facts land on one row.
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
        if listing_url and _is_list_url(listing_url, source_url):
            # §2 Forbidden: "Using the list URL (`/EventSearch`, `/today`, a
            # Google SERP) as `listing_url` of a single event." The address of
            # the page a row was READ FROM is not the address of the row, and a
            # row carrying it keys every listing on the desk to one identity —
            # which is exactly how 40 Chronicle pages became one row. The hole
            # is the honest answer; `source_url` still records where we read it.
            listing_url = None
            result.mash_blocked += 1
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

    # ---------------------------------------------------------------
    # The split ladder (ONE-LIVE-ENTITY-SPLIT-LAW.md §2)
    # ---------------------------------------------------------------
    if patterns is None:
        patterns = _committed_patterns()

    # Rung 1 — the page's own STRUCTURED statement: schema.org Event published
    # as data (JSON-LD array/graph, or Event microdata). Each node is one event
    # by construction, so there is no splitting decision to make here and no way
    # for this rung to mash. parse_jsonld keeps every Event node whatever fields
    # it lacks; we deliberately do NOT continue into normalize_structured, whose
    # "no stable id or no title -> None" is the identity-gated existence test
    # this path replaces.
    try:
        ld_events = parse_jsonld(html)
    except Exception as exc:  # noqa: BLE001 — a pathological page must not lose the HTML rows
        ld_events = []
        result.notes.append(f"JSON-LD parse raised ({exc}); HTML rows still read")

    try:
        builder = _TreeBuilder()
        builder.feed(html)
        builder.close()
        root = builder.root
    except Exception as exc:  # noqa: BLE001 — a pathological page must not lose the JSON-LD rows
        root = None
        result.notes.append(f"HTML parse raised ({exc}); JSON-LD rows still read")

    microdata_rows = _topmost(root, _is_event_itemscope) if root is not None else []
    structured_n = len(ld_events) + len(microdata_rows)

    # Rungs 2, 3, 4 — the ladder over the page's PRINTED HTML, where the
    # splitting decision actually lives. First rung that yields an identity
    # wins; the rungs are never mixed with each other, which is what stops a
    # weaker reading from adding rows on top of a declared split.
    html_rows: List[Tuple[Optional[str], _Node]] = []
    html_tier: Optional[str] = None
    if root is not None:
        permalink_rows = _identity_rows(root, base_url=source_url, patterns=patterns)
        if permalink_rows:
            html_tier = "permalink"
            html_rows = [(url, node) for url, node, _ in permalink_rows]
            for _, _, hit in permalink_rows:
                stamp = f"{hit.pattern_id} ({hit.grade})"
                if stamp not in result.identity_evidence:
                    result.identity_evidence.append(stamp)
        else:
            selector_rows = _selector_rows(root, door.listing_selectors)
            if selector_rows:
                html_tier = "desk_selector"
                html_rows = [(None, node) for node in selector_rows]
                for sel in door.listing_selectors:
                    stamp = (f"{sel.tag}{''.join('.' + t for t in sel.class_tokens)} "
                             f"({sel.grade})")
                    if stamp not in result.identity_evidence:
                        result.identity_evidence.append(stamp)

    if structured_n and html_tier:
        result.identity_tier = f"structured+{html_tier}"
    elif html_tier:
        result.identity_tier = html_tier
    elif structured_n:
        result.identity_tier = "structured"
    else:
        result.identity_tier = "unsplit"

    for ev in ld_events:
        place = ev.get("venue_name") or ev.get("venue_address") or ev.get("venue_city")
        _add(ev.get("title"), ev.get("start_time"), None, place, ev.get("url"),
             hrefs=tuple(u for u in (ev.get("url"),) if u))
    for row_node in microdata_rows:
        fields = _row_fields(row_node, base_url=source_url)
        _add(fields["title"], fields["when"], fields["when_text"],
             fields["place_text"], fields["listing_url"],
             labels=tuple(fields.get("category_labels") or ()),
             hrefs=tuple(fields.get("hrefs") or ()))
    for identity, row_node in html_rows:
        fields = _row_fields(row_node, base_url=source_url)
        # On the permalink rung the row's address is the IDENTITY the committed
        # pattern matched, never whichever anchor `_row_fields` read first (a
        # card's ticket link, its venue link, its category link).
        _add(fields["title"], fields["when"], fields["when_text"],
             fields["place_text"], identity or fields["listing_url"],
             labels=tuple(fields.get("category_labels") or ()),
             hrefs=tuple(fields.get("hrefs") or ()))

    if len(rows) > MAX_ROWS:
        result.truncated_at = MAX_ROWS
        result.notes.append(
            f"page yielded {len(rows)} rows; truncated to {MAX_ROWS} (cap, not an empty desk)")
        rows = rows[:MAX_ROWS]
    result.rows = rows
    # Derived from the rows this read actually RETURNED — the same derivation
    # `tools/desk_ingest.py`'s table makes, so one idea never prints as two
    # different numbers, and a truncated page never claims identities it did
    # not hand back.
    result.identities_declared = len({r.listing_url for r in rows if r.listing_url})
    if result.unsplit:
        result.notes.append(
            "unsplit — this page declared no happening identity we hold: no "
            "schema.org Event, no href matching a committed identity pattern for "
            f"this host, and door {door.door_id!r} commits "
            f"{len(door.listing_selectors)} listing selector(s) that matched "
            "nothing. ZERO rows, and a coverage defect on this DOOR — the answer "
            "is a pattern or a claim, never one mashed row "
            "(ONE-LIVE-ENTITY-SPLIT-LAW.md §2/§4)")
    else:
        evidence = (" on " + ", ".join(result.identity_evidence)
                    if result.identity_evidence else "")
        result.notes.append(
            f"split by the {result.identity_tier} rung{evidence} — "
            f"{result.identities_declared} identity/identities declared, "
            f"{structured_n} structured node(s)")

    if result.skipped_untitled:
        result.notes.append(
            f"{result.skipped_untitled} block(s) carried no title text and were "
            f"skipped — counted, never silently dropped")
    if result.mash_blocked:
        result.notes.append(
            f"{result.mash_blocked} row(s) stated the LIST's own URL as their "
            f"address; dropped to a hole rather than keying a whole desk to one "
            f"identity (§2 Forbidden)")
    if result.unmapped_categories:
        result.notes.append(
            f"{len(result.unmapped_categories)} category/categories this page "
            f"stated are not in the committed mapping "
            f"({', '.join(result.unmapped_categories[:8])}) — those rows kept "
            f"the door's kind; the mapping is completed from the desk's own "
            f"words, never from memory")
    return result
