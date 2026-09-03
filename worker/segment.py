"""Deterministic page -> per-event block segmentation (stdlib only).

The certified single-event extractor (ai/prompts.py + AIEventExtraction) reads a
block of text and returns ONE event. A real source page, though, is rarely one
event: a venue calendar or listings page describes many separate shows. Rather
than change the certified extractor (which would drift the golden-exam
certification hash and force a founder re-certification), this module SPLITS a
fetched page into per-event text blocks. worker/ai_extract.py then runs the
UNCHANGED certified extractor once per block and fans out one candidate per
block — the same certified brain, run N times.

Design rules (in priority order, matching CLAUDE.md's truth-first bar):
  1. NEVER fabricate or duplicate an event. A 1-event page yields exactly 1
     block; segmentation only ever partitions text that is already present.
  2. Under-segment, don't over-segment. A wrong split that invents a garbage
     "event" is far worse than leaving two real shows fused in one block (the
     extractor then returns the first, which is exactly today's behavior). So a
     split is only taken when it is STRUCTURALLY confident (repeated schema.org
     Event containers or repeated dated items) or ANCHOR confident (repeated
     independent date/time anchors). Anything less falls back to a single block.
  3. The single-block fallback returns the WHOLE ORIGINAL content unchanged, so
     the extractor receives byte-identical input to today — behavior on the
     pages we already handle is provably unchanged.
  4. Bounded: at most ``MAX_BLOCKS`` blocks; a page that would exceed the cap is
     truncated to the cap and the drop is logged (never silent).
  5. A block CARRIES the identity its own markup stated, and never one it did
     not. R-103 recorded the consequence of not doing this: the identity stack
     (`worker/identity.py`) shipped with no producer on the crawl path, because
     the strip-to-text step here discarded every listing's own `<a href>` and
     every JSON-LD `@id` before `worker/ai_extract.py` ever saw the block. So a
     block cut from a JSON-LD Event object carries that object's `url`/`@id`,
     and a block cut from an HTML container carries that container's own
     unambiguous `<a href>` — as a SIDECAR on the block object
     (`worker.identity.carry_identity`), leaving the block TEXT byte-identical.
     The extractor's input, and the surface exam's, are unchanged.
     Nothing else carries anything: the anchor-split path cuts at text offsets
     with no structure to attribute an address to, and the single-block
     fallback IS the whole page, whose url every listing on it shares. An
     address two blocks both state is dropped from both — it identifies what
     they have in common, not either of them.

Deliberately imports nothing from the pipeline (no promote/gating/AI). The one
import, `worker.identity`, is a pure stdlib value module with no DB, clock,
network or pipeline import of its own; it is imported rather than mirrored so
the shape of an identity has exactly one home. This module still partitions raw
text and has no opinion on trust, corroboration, or publishing — an identity it
carries is a fact the page stated, and what that licenses is decided elsewhere
(`worker/listing_update.py`).
"""
from __future__ import annotations

import json
import logging
import re
from html.parser import HTMLParser
from typing import Callable, Dict, List, Optional, Tuple

from worker.identity import (
    ListingIdentity,
    NO_IDENTITY,
    carried_identity,
    carry_identity,
    jsonld_identity,
)

logger = logging.getLogger(__name__)

# Upper bound on blocks returned from one page. A calendar with more than this
# many events is unusual; rather than fan out an unbounded number of AI calls
# (cost + a runaway page), cap and log. Kept generous so real month-view
# calendars (typically 20-60 shows) are never clipped in practice.
MAX_BLOCKS = 200

# A block is only kept if it has at least this much substantive text, so an
# empty <li></li> or a whitespace-only anchor gap never becomes a candidate.
_MIN_BLOCK_CHARS = 8

# schema.org Event microdata: itemtype URL ends in /Event (or a subtype like
# /MusicEvent, /TheaterEvent). Matched case-insensitively on the attribute.
_EVENT_ITEMTYPE_RE = re.compile(r"schema\.org/[A-Za-z]*Event\b", re.I)

# A "date or time anchor": the textual cue that a new event listing begins.
# Weekday / month names, numeric dates (8/1, 8/1/26, 2026-08-01), and clock
# times (8pm, 8 PM, 8:00, 20:00, doors 8PM). Deliberately broad on RECOGNITION
# (we want to notice anchors) but the SPLIT only fires when >=2 are found, so a
# lone stray time never fragments a single-event blurb.
_DATE_TIME_SRC = r"""
    \b\d{1,2}\s*[:.]\d{2}\s*(?:am|pm)?\b          # 8:00, 8.00, 8:00 pm, 20:00
  | \b\d{1,2}\s*(?:am|pm)\b                       # 8pm, 8 PM
  | \b\d{4}-\d{1,2}-\d{1,2}\b                     # 2026-08-01 (ISO)
  | \b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b              # 8/1, 8/1/26
  | \b(?:mon|tue|tues|wed|weds|thu|thur|thurs|fri|sat|sun)
        (?:day|nesday|rsday|urday)?\b             # Mon..Sunday
  | \b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)
        (?:uary|ruary|ch|il|e|y|ust|tember|ober|ember)?\b  # Jan..December
"""
_DATE_TIME_RE = re.compile(_DATE_TIME_SRC, re.I | re.X)

# Anchor at the START of a line (after optional list/quote/bullet punctuation).
# A new event listing conventionally opens on its own line with its date/time.
_ANCHOR_LINE_RE = re.compile(
    r"(?m)^[ \t>*•‣●.\-–—#]*(?:" + _DATE_TIME_SRC + r")",
    re.I | re.X,
)

# class attribute values that mark a repeated event/card container. Substring,
# case-insensitive — matches "event-card", "eventItem", "show", "listing", etc.
_CARDISH_CLASS_RE = re.compile(r"event|card|listing|show|gig|happening", re.I)

# Headings INSIDE a listing container. A listing conventionally names itself in
# a heading, and the anchor on that heading is conventionally the listing's own
# page — which is why a heading anchor outranks the other links in a card (a
# "Tickets" link is a vendor's page, an image link is the same page again).
# Convention is not proof, so this rung is bounded twice: it fires only when the
# heading states exactly ONE address, and every captured href then has to
# survive the page-wide uniqueness pass in `_drop_shared_identities`.
_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})

# Schemes that are not the address of anything a calendar lists. Excluded before
# hrefs are counted, so a card carrying one listing link plus a mailto/tel/JS
# handle still reads as UNAMBIGUOUS rather than as two competing addresses. This
# is a fact about the schemes, not a preference between two candidate listings.
_NON_ADDRESS_SCHEMES = ("javascript:", "mailto:", "tel:", "sms:", "data:")

# Block-level tags: stripping HTML to text, we insert a newline at each so that
# date anchors that begin a listing land at the start of a line for the
# anchor-split fallback.
_BLOCK_LEVEL_TAGS = frozenset({
    "p", "div", "li", "ul", "ol", "article", "section", "tr", "table",
    "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr", "header", "footer", "dd", "dt",
})


def _ws(s: str) -> str:
    """Collapse runs of whitespace to single spaces and strip."""
    return " ".join(s.split())


def _has_date_or_time(s: str) -> bool:
    return _DATE_TIME_RE.search(s) is not None


def _looks_like_html(content: str, content_type: Optional[str]) -> bool:
    if content_type and "html" in content_type.lower():
        return True
    # Structural tags a listings page would carry. A plain-text page mentioning
    # "<3" or "a < b" won't match these anchored tag patterns.
    return re.search(
        r"</?(?:html|body|div|article|section|ul|ol|li|table|tr|script|p|h[1-6])\b",
        content, re.I,
    ) is not None


def _href_of(attrs: Dict[str, str]) -> Optional[str]:
    """The address an element states, or None. Never a fabricated value.

    Whitespace-stripped and VERBATIM otherwise: a relative href stays relative,
    because `segment_events` is handed a page's CONTENT and not its url, and
    resolving one against a url we were never given would be inventing an
    address (founder, verbatim: "Do not invent URLs"). Comparisons downstream
    are source-scoped, so a relative anchor is still a usable identity.
    """
    raw = (attrs.get("href") or "").strip()
    if not raw or raw == "#":
        # A bare "#" is a no-op link (a menu toggle), not an address.
        return None
    if raw.lower().startswith(_NON_ADDRESS_SCHEMES):
        return None
    return raw


def _itemprop_url_of(attrs: Dict[str, str]) -> Optional[str]:
    """The address an element states while LABELLING itself the listing's url
    (``itemprop="url"``), or None — the source naming the field itself, which
    is the strongest signal a card can carry short of being the anchor."""
    tokens = (attrs.get("itemprop") or "").lower().split()
    if "url" not in tokens:
        return None
    return _href_of(attrs) or (attrs.get("content") or "").strip() or None


class _ElementTextCollector(HTMLParser):
    """Collect the concatenated text of each OUTERMOST element for which
    ``should_start(tag, attrs)`` is true, together with the address that
    element's OWN markup states for it.

    Nesting is balanced on the tag that OPENED the capture, so a matched
    element containing a same-tag descendant (a <li> inside a <li>) is one
    block, not two — we never split a container at an inner boundary.

    The address is read in a fixed order, and the order is the point: each rung
    is a place the SOURCE said "this listing lives here", and the last rung
    refuses rather than picking between links that say nothing about which is
    the listing's own.

      1. the container IS an anchor (the card-as-link pattern, reachable via the
         schema.org-microdata strategy) -> its href;
      2. something inside is labelled ``itemprop="url"`` ONCE  -> that address;
      3. the container's heading states exactly one address    -> that href;
      4. the container states exactly one address in total     -> that href;
      5. anything else -> NO address (an ambiguous card is not an identity).

    Text is unaffected by all of this: the block string is byte-identical to
    what this collector returned before it read attributes at all.
    """

    def __init__(self, should_start: Callable[[str, Dict[str, str]], bool]) -> None:
        super().__init__(convert_charrefs=True)
        self._should_start = should_start
        #: (text, source_href) per captured element; the href may be None.
        self.blocks: List[Tuple[str, Optional[str]]] = []
        self._cap_tag: Optional[str] = None
        self._depth = 0
        self._buf: List[str] = []
        self._cap_href: Optional[str] = None
        self._itemprop_urls: List[str] = []
        self._heading_depth = 0
        self._heading_hrefs: List[str] = []
        self._hrefs: List[str] = []

    # -- capture bookkeeping --------------------------------------------------

    def _note_attrs(self, tag: str, attrs: Dict[str, str]) -> None:
        """Record what an element INSIDE the current capture states."""
        labelled = _itemprop_url_of(attrs)
        if labelled is not None and labelled not in self._itemprop_urls:
            self._itemprop_urls.append(labelled)
        if tag != "a":
            return
        href = _href_of(attrs)
        if href is None:
            return
        if href not in self._hrefs:
            self._hrefs.append(href)
        if self._heading_depth and href not in self._heading_hrefs:
            self._heading_hrefs.append(href)

    def _resolved_href(self) -> Optional[str]:
        """The rungs above, in order. None when the card is ambiguous."""
        if self._cap_href:
            return self._cap_href
        if len(self._itemprop_urls) == 1:
            return self._itemprop_urls[0]
        if self._itemprop_urls:
            # A card labelling TWO different addresses as its url has
            # contradicted itself, and a contradiction is never an identity
            # (worker/identity.py's own rule). Refuse outright rather than
            # falling to a weaker rung: the weaker rungs read conventions, and
            # a convention must not outrank a declaration the source made —
            # even when the source made it twice and disagreed with itself.
            return None
        if len(self._heading_hrefs) == 1:
            return self._heading_hrefs[0]
        if len(self._hrefs) == 1:
            return self._hrefs[0]
        return None

    def _reset_capture(self) -> None:
        self._cap_tag = None
        self._depth = 0
        self._buf = []
        self._cap_href = None
        self._itemprop_urls = []
        self._heading_depth = 0
        self._heading_hrefs = []
        self._hrefs = []

    # -- parser callbacks -----------------------------------------------------

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        a = {k.lower(): (v or "") for k, v in attrs}
        if self._cap_tag is not None:
            if t == self._cap_tag:
                self._depth += 1
            if t in _HEADING_TAGS:
                self._heading_depth += 1
            self._note_attrs(t, a)
            return
        if self._should_start(t, a):
            self._cap_tag = t
            self._depth = 1
            self._buf = []
            self._cap_href = _href_of(a) if t == "a" else None
            self._itemprop_urls = []
            self._heading_depth = 0
            self._heading_hrefs = []
            self._hrefs = []

    def handle_startendtag(self, tag, attrs):
        # A self-closing element carries no text content; the only effects we
        # care about are separating adjacent text and the address a void
        # element can still state (<link itemprop="url" href="..."/>).
        if self._cap_tag is not None:
            self._note_attrs(tag.lower(), {k.lower(): (v or "") for k, v in attrs})
            self._buf.append(" ")

    def handle_endtag(self, tag):
        if self._cap_tag is None:
            return
        t = tag.lower()
        if t in _HEADING_TAGS and self._heading_depth:
            self._heading_depth -= 1
        if t == self._cap_tag:
            self._depth -= 1
            if self._depth == 0:
                self.blocks.append((_ws(" ".join(self._buf)), self._resolved_href()))
                self._reset_capture()

    def handle_data(self, data):
        if self._cap_tag is not None:
            self._buf.append(data)


class _TextStripper(HTMLParser):
    """Flatten HTML to text, inserting newlines at block-level boundaries so the
    anchor-split fallback sees each listing on its own line. <script>/<style>
    contents are dropped."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: List[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in ("script", "style"):
            self._skip += 1
        elif t in _BLOCK_LEVEL_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ("script", "style") and self._skip:
            self._skip -= 1
        elif t in _BLOCK_LEVEL_TAGS:
            self._parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def text(self) -> str:
        return "".join(self._parts)


def _strip_tags(html: str) -> str:
    p = _TextStripper()
    try:
        p.feed(html)
        p.close()
    except Exception:  # noqa: BLE001 — malformed markup must never crash the pipeline
        logger.warning("HTML strip failed; falling back to raw content", exc_info=True)
        return html
    return p.text()


def _collect(html: str, should_start: Callable[[str, Dict[str, str]], bool]) -> List[str]:
    """Blocks for the matched containers, each CARRYING its own `source_href`
    when its markup stated one unambiguously (see `_ElementTextCollector`).

    A block whose container stated no address is a plain `str`, identical in
    type and value to what this returned before the carrier existed.
    """
    c = _ElementTextCollector(should_start)
    try:
        c.feed(html)
        c.close()
    except Exception:  # noqa: BLE001 — malformed markup must never crash the pipeline
        logger.warning("HTML element collection failed", exc_info=True)
        return []
    return [
        carry_identity(text, ListingIdentity(source_href=href))
        for text, href in c.blocks
        if len(text.strip()) >= _MIN_BLOCK_CHARS
    ]


def _jsonld_event_blocks(html: str) -> List[str]:
    """Extract schema.org Event objects embedded as JSON-LD script blocks.

    Each Event becomes a compact text block ("Name | startDate | venue |
    address | url") from ONLY the fields literally present — no invention —
    CARRYING the identity that same object stated (`url` -> listing_url,
    `@id`/`identifier` -> uid, read by `worker.identity.jsonld_identity`, the
    one place in the tree that decides which JSON-LD keys are an identity).
    The identity is paired with the object it was read FROM at construction, so
    the traversal's order can never attach one event's id to another's text.
    Returns [] unless the parse is clean and finds >= 2 events, so a single
    JSON-LD event never diverts from the whole-page single-block path.
    """
    events: List[str] = []
    for m in re.finditer(
        r'<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.I | re.S,
    ):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        for obj in _iter_jsonld_objects(data):
            block = _jsonld_event_text(obj)
            if block:
                events.append(carry_identity(block, jsonld_identity(obj)))
    return events


def _iter_jsonld_objects(data):
    """Yield candidate dict nodes from a JSON-LD payload (handles a bare object,
    a list, and an @graph wrapper)."""
    stack = [data]
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, dict):
            yield node
            graph = node.get("@graph")
            if isinstance(graph, list):
                stack.extend(graph)


def _jsonld_event_text(obj: Dict) -> Optional[str]:
    t = obj.get("@type")
    types = t if isinstance(t, list) else [t]
    if not any(isinstance(x, str) and x.lower().endswith("event") for x in types):
        return None
    parts: List[str] = []
    for key in ("name", "startDate", "start_date"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    loc = obj.get("location")
    if isinstance(loc, dict):
        name = loc.get("name")
        if isinstance(name, str) and name.strip():
            parts.append(name.strip())
        addr = loc.get("address")
        if isinstance(addr, str) and addr.strip():
            parts.append(addr.strip())
        elif isinstance(addr, dict):
            for ak in ("streetAddress", "addressLocality"):
                av = addr.get(ak)
                if isinstance(av, str) and av.strip():
                    parts.append(av.strip())
    elif isinstance(loc, str) and loc.strip():
        parts.append(loc.strip())
    url = obj.get("url")
    if isinstance(url, str) and url.strip():
        parts.append(url.strip())
    text = " | ".join(parts)
    return text if len(text.strip()) >= _MIN_BLOCK_CHARS else None


def _majority_dated(blocks: List[str]) -> bool:
    """True when the repeated items look like an EVENT list, not a nav/menu.
    Requires at least two dated items and a clear majority of items dated — a
    conservative bar that rejects a repeated <li> menu (no dates) while
    accepting a calendar (nearly every row dated)."""
    if len(blocks) < 2:
        return False
    dated = sum(1 for b in blocks if _has_date_or_time(b))
    return dated >= 2 and dated / len(blocks) >= 0.6


def _segment_html(content: str) -> List[str]:
    """Structural HTML segmentation. Returns >= 2 blocks only when confident,
    else [] (caller falls back to anchor split, then to a single block)."""
    # (1) JSON-LD Event objects — explicit, machine-declared events.
    blocks = _jsonld_event_blocks(content)
    if len(blocks) >= 2:
        return blocks

    # (2) schema.org microdata Event containers.
    blocks = _collect(
        content,
        lambda tag, attrs: bool(_EVENT_ITEMTYPE_RE.search(attrs.get("itemtype", ""))),
    )
    if _majority_dated(blocks):
        return blocks

    # (3) Repeated structural items, each bearing a date/time. Tried in order of
    # specificity; the first that yields a confident, dated set wins.
    strategies: List[Callable[[str, Dict[str, str]], bool]] = [
        lambda tag, attrs: tag == "article",
        lambda tag, attrs: tag in ("div", "li", "section")
        and bool(_CARDISH_CLASS_RE.search(attrs.get("class", ""))),
        lambda tag, attrs: tag == "li",
    ]
    for should_start in strategies:
        blocks = _collect(content, should_start)
        if _majority_dated(blocks):
            return blocks
    return []


def _segment_by_date_anchors(text: str) -> List[str]:
    """Split plain text at repeated line-initial date/time anchors. Returns >= 2
    blocks only when at least two independent anchors are found, else [text]."""
    anchors = [m.start() for m in _ANCHOR_LINE_RE.finditer(text)]
    if len(anchors) < 2:
        return [text]
    # Cut points define the block boundaries. A non-trivial preamble before the
    # first anchor (e.g. a shared venue header) rides with the FIRST event
    # rather than being dropped — losing it would strip context from a real
    # event, worse than the known limitation that it is NOT propagated to the
    # later blocks (recorded as a heuristic gap).
    if anchors[0] > 0 and text[: anchors[0]].strip():
        cut = [0] + anchors[1:]
    else:
        cut = anchors
    starts = cut
    ends = cut[1:] + [len(text)]
    blocks: List[str] = []
    for s, e in zip(starts, ends):
        chunk = text[s:e].strip()
        if len(chunk) >= _MIN_BLOCK_CHARS:
            blocks.append(chunk)
    return blocks if len(blocks) >= 2 else [text]


def _drop_shared_identities(blocks: List[str]) -> List[str]:
    """Strip any identity VALUE that two blocks on this page both state.

    A page-wide cardinality check, and the one bound on the conventional rungs
    above: an address two listings share does not identify either of them. It
    identifies something they have in common — an artist page, a series page,
    a venue page, a "Tickets" vendor — and adopting it would let a later tick
    rewrite one listing's public row from the other's facts, which is exactly
    the harm R-095/R-097/R-099 refuse to risk.

    Only the SHARED field is dropped, per block: a page whose two listings
    share a `listing_url` but state distinct `uid`s keeps both uids. A block
    left with nothing stated becomes a plain `str` again, indistinguishable
    from a block whose page never stated anything — because the two cases mean
    the same thing.

    Runs over ALL blocks before the MAX_BLOCKS cap, so a shared address is
    still caught when one of its two carriers is about to be truncated away.
    """
    counts: Dict[Tuple[str, str], int] = {}
    for block in blocks:
        for field, value in carried_identity(block).as_dict().items():
            counts[(field, value)] = counts.get((field, value), 0) + 1
    shared = {key for key, n in counts.items() if n > 1}
    if not shared:
        return blocks
    logger.warning(
        "segment_events: %d identity value(s) are stated by more than one block "
        "on this page and are therefore NOT per-listing identities — dropped "
        "rather than adopted: %s",
        len(shared), sorted(f"{field}={value!r}" for field, value in shared),
    )
    out: List[str] = []
    for block in blocks:
        stated = carried_identity(block).as_dict()
        kept = {f: v for f, v in stated.items() if (f, v) not in shared}
        if kept == stated:
            out.append(block)
        else:
            out.append(carry_identity(str(block), ListingIdentity(**kept)))
    return out


def _cap(blocks: List[str]) -> List[str]:
    if len(blocks) > MAX_BLOCKS:
        logger.warning(
            "segment_events: %d blocks exceeds MAX_BLOCKS=%d; truncating "
            "(the tail events on this page will not be extracted this run).",
            len(blocks), MAX_BLOCKS,
        )
        return blocks[:MAX_BLOCKS]
    return blocks


def segment_events(content: Optional[str], *, content_type: Optional[str] = None) -> List[str]:
    """Split a fetched page into per-event text blocks.

    Returns a list of text blocks, one per detected event; a block whose own
    markup stated an address or id is an `IdentifiedBlock` carrying it (a `str`
    in every other respect). Heuristics, in order:
      (a) if HTML carries repeated schema.org Event containers or repeated dated
          structural items (<article>/<li>/event-card <div>), each is a block;
      (b) else split plain text on repeated line-initial date/time anchors;
      (c) else return a SINGLE block — the whole original content — so behavior
          is byte-identical to feeding the page straight to the extractor.

    A 1-event page always yields exactly 1 block; nothing is ever fabricated or
    duplicated. Result length is bounded by ``MAX_BLOCKS`` (over-cap is logged).
    """
    if content is None:
        return []
    if not content.strip():
        return [content]

    if _looks_like_html(content, content_type):
        blocks = _segment_html(content)
        if len(blocks) >= 2:
            return _cap(_drop_shared_identities(blocks))
        text = _strip_tags(content)
    else:
        text = content

    blocks = _segment_by_date_anchors(text)
    if len(blocks) >= 2:
        return _cap(blocks)

    # Not confidently multi-event: hand back the whole original content, exactly
    # as today's single-event path receives it.
    return [content]
