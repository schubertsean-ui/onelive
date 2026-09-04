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
     and a block cut from an HTML container carries the address that container
     DECLARES for itself — an `itemprop="url"` stated once at the card's own
     scope, and nothing else. Never one merely conventional: not a title link,
     not a card's sole link, and not the href of a container that happens to BE
     an anchor. Each of those points at an artist or a ticket vendor as readily
     as at the listing, and all three were deleted at adversarial-panel
     findings (rounds 1 and 4), which were right. As a SIDECAR
     on the block object
     (`worker.identity.carry_identity`), leaving the block TEXT byte-identical.
     The extractor's input, and the surface exam's, are unchanged.
     Nothing else carries anything: the anchor-split path cuts at text offsets
     with no structure to attribute an address to, and the single-block
     fallback IS the whole page, whose url every listing on it shares. An
     address two blocks both declare is dropped from both — it identifies what
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
    identity_address,
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

# Elements that cannot contain content, so an `itemscope` on one opens no
# nested item worth tracking. Listed so a stray `<meta itemscope>` cannot leave
# a scope permanently open (which would silently refuse every later
# declaration on the page — the safe direction, but for the wrong reason).
_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
})

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

    What counts as usable is `worker.identity.identity_address`'s question, not
    this module's — one check for every URL-VALUED carrier of an identity, here
    and in the JSON-LD reader, because four review rounds found the same defect
    four times in the shape of one carrier validated and its siblings not. That
    check also refuses a PAGE-RELATIVE address (`details`, `?id=1`): the
    segmenter has no page url to resolve one against, so the same string on two
    pages of a source would compare equal and license a write from the wrong
    occurrence.
    """
    return identity_address(attrs.get("href"))


def _itemprop_url_of(attrs: Dict[str, str]) -> Optional[str]:
    """The address an element states while LABELLING itself the listing's url
    (``itemprop="url"``), or None — the source naming the field itself, which
    is the strongest signal a card can carry short of being the anchor.

    BOTH carriers go through `_href_of`. A `<meta itemprop="url" content="...">`
    is the microdata spelling of the same declaration, and the `content` value
    used to be taken verbatim — so `content="javascript:..."`, `content="#"` or
    `content="mailto:..."` could be stored as a listing's identity, and a
    placeholder repeated across ticks would then read as the same listing and
    license a public write. Caught by the adversarial panel (round 2, both
    openai seats; the gemini dataflow-taint seat raised the identical thing as
    a nit with this exact fix). One validation for one meaning: the label says
    "this is a url", so the value has to be one — and since round 3 that one
    validation is `worker.identity.identity_value`, shared with the JSON-LD
    carrier rather than mirrored beside it.
    """
    tokens = (attrs.get("itemprop") or "").lower().split()
    if "url" not in tokens:
        return None
    return _href_of(attrs) or identity_address(attrs.get("content"))


class _ElementTextCollector(HTMLParser):
    """Collect the concatenated text of each OUTERMOST element for which
    ``should_start(tag, attrs)`` is true, together with the address that
    element's OWN markup states for it.

    Nesting is balanced on the tag that OPENED the capture, so a matched
    element containing a same-tag descendant (a <li> inside a <li>) is one
    block, not two — we never split a container at an inner boundary.

    EXACTLY ONE THING IS READ, and the narrowness is the whole design: an
    address something inside the card labels ``itemprop="url"``, stated once,
    AT THE CARD'S OWN SCOPE. Anything else is no address.

    Three CONVENTIONS were tried and all three were deleted at the adversarial
    panel's blocking findings — a card's heading anchor, a card's sole link
    (round 1), and a container that IS an anchor (round 4). Each looks like the
    listing's own address and none is declared to be one: an ordinary venue
    card links the ARTIST or the SERIES from its title as readily as the event,
    a card's only link is as often a ticket vendor's, and an Event container
    that happens to be an `<a>` can wrap event text while pointing at an artist
    page. Adopting any of them means a later tick can read the same address on
    a DIFFERENT occurrence, answer SAME, and rewrite a published listing with
    another show's title and clock — user-facing false facts, from a guess. The
    page-wide uniqueness pass in `_drop_shared_identities` cannot save it: that
    catches an address repeated on ONE page, and this harm is across ticks.

    "At the card's own scope" is the microdata spec, and skipping it let a
    deleted convention back in through the front door (round 2): a well-formed
    Event card nests `performer`, `location` and `offers` items, and each has
    its own `url` — the artist's page, the venue's page, the vendor's. Reading
    a descendant's `url` as the EVENT's is the artist-link defect wearing
    microdata clothes, so a declaration is recorded only while no nested
    `itemscope` is open.

    So the cost is deliberately accepted in the safe direction: a card with a
    title link and a "Tickets" link states NO identity, and the listing keeps
    being matched by the composite rung, which licenses nothing. Under-matching
    costs a refusal; over-matching costs a wrong public listing.

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
        self._itemprop_urls: List[str] = []
        #: Every element open INSIDE the capture, as (tag, opened_an_itemscope).
        #: Tracking all of them — not only the scope openers — is what makes
        #: `<div itemscope><div></div></div>` balance correctly: the inner
        #: `</div>` closes the inner div, never the outer item (the panel's
        #: round-3 nit, which failed OPEN and so is fixed rather than noted).
        self._open: List[Tuple[str, bool]] = []
        #: How many of those are open items. Non-zero means "we are describing
        #: something OTHER than this listing", so no declaration is read.
        self._scopes = 0
        #: Did the CARD ELEMENT ITSELF declare an item? An `itemprop` means
        #: something only relative to its nearest ENCLOSING item, so with no
        #: item there is nothing for the property to be a property OF (round
        #: 8). The item's TYPE is not checked: a presenter's own page is a
        #: trusted door whose per-item declaration is usable identity (founder,
        #: 2026-09-04) — see `_note_attrs`.
        self._card_is_item = False

    # -- capture bookkeeping --------------------------------------------------

    def _note_attrs(self, tag: str, attrs: Dict[str, str], *, nests: bool) -> None:
        """Record an address an element INSIDE the current capture DECLARES
        FOR THIS LISTING, and track nested microdata scopes.

        Undeclared `<a href>`s are not recorded at all — not counted, not
        ranked, not remembered. There is no rung they could feed.

        The property is read BEFORE this element's own `itemscope` is pushed,
        because an `itemprop` belongs to its nearest ENCLOSING scope: an
        element that is both `itemprop="url"` of the card and a nested item in
        its own right still states the card's url.

        And it is read ONLY when the card is itself the LISTING's item, which
        took two passes to state properly. Three of the four capture strategies
        find cards STRUCTURALLY — `<article>`, a cardish class, `<li>` — and
        those carry no microdata at all, so `self._scopes` is trivially 0
        inside them and every `itemprop="url"` would look like a declaration.
        But microdata gives an `itemprop` meaning only against its nearest
        enclosing item; with no item there is nothing it is a property OF. A
        venue that sprinkles `itemprop="url"` on the ARTIST link inside a plain
        `<article class="event">` would otherwise hand us the artist's address
        as the listing's identity, and the next occurrence by that artist would
        answer SAME and license a write onto the wrong published row.

        The item's TYPE is deliberately NOT checked, and that is a founder
        ruling (2026-09-04) that reversed a stricter rule this file carried for
        about an hour. An OFFICIAL PRESENTER — musician, chef, visual artist,
        professor, author, speaker, personality, company, any named person or
        group — is a TRUSTED DOOR, and a public list of upcoming work on their
        own site is a source: "Do not require a calendar UI or /events. Do not
        exclude those sites as sources." So `<article itemscope
        itemtype="https://schema.org/Person">` on a presenter's own page states
        a usable per-item identity, and refusing it would have narrowed the
        catalogue, which Coverage Law forbids.

        What IS refused is narrower and unchanged: a presenter's homepage url
        standing in as ANOTHER entity's listing_url on that entity's card. That
        case never had a declaration to read in the first place — an
        undeclared artist link is not counted, ranked or remembered — and where
        one address is declared by two cards on a page, `_drop_shared_identities`
        removes it from both, because an address two listings share describes
        neither.
        """
        if self._card_is_item and not self._scopes:
            labelled = _itemprop_url_of(attrs)
            if labelled is not None and labelled not in self._itemprop_urls:
                self._itemprop_urls.append(labelled)
        if not nests or tag in _VOID_TAGS:
            return
        opens_scope = "itemscope" in attrs
        self._open.append((tag, opens_scope))
        if opens_scope:
            self._scopes += 1

    def _resolved_href(self) -> Optional[str]:
        """The declared address, or None. Never a conventional one."""
        if len(self._itemprop_urls) == 1:
            return self._itemprop_urls[0]
        # Zero declarations is a hole. TWO different ones is a contradiction,
        # and a contradiction is never an identity (worker/identity.py's own
        # rule). Both answer None, because both mean the same thing: the source
        # did not tell us where this listing lives.
        return None

    def _reset_capture(self) -> None:
        self._cap_tag = None
        self._depth = 0
        self._buf = []
        self._itemprop_urls = []
        self._open = []
        self._scopes = 0
        self._card_is_item = False

    # -- parser callbacks -----------------------------------------------------

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        a = {k.lower(): (v or "") for k, v in attrs}
        if self._cap_tag is not None:
            if t == self._cap_tag:
                self._depth += 1
            self._note_attrs(t, a, nests=True)
            return
        if self._should_start(t, a):
            self._cap_tag = t
            self._depth = 1
            self._buf = []
            self._itemprop_urls = []
            # The CARD's own itemscope is the scope we are reading properties
            # at, so it is deliberately not pushed: only items nested INSIDE it
            # are somebody else's. But it must EXIST — a structurally-found
            # card declares no item, and a property of no item is not a
            # declaration (see _note_attrs). The item's TYPE is deliberately
            # NOT checked: a presenter's own page is a trusted door and its
            # per-item declaration is usable identity (founder, 2026-09-04).
            self._card_is_item = "itemscope" in a
            self._open = []
            self._scopes = 0

    def handle_startendtag(self, tag, attrs):
        # A self-closing element carries no text content; the only effects we
        # care about are separating adjacent text and the address a void
        # element can still state (<link itemprop="url" href="..."/>).
        if self._cap_tag is not None:
            # A self-closing element is closed the moment it opens, so it never
            # nests a scope — recording only.
            self._note_attrs(tag.lower(),
                             {k.lower(): (v or "") for k, v in attrs},
                             nests=False)
            self._buf.append(" ")

    def handle_endtag(self, tag):
        if self._cap_tag is None:
            return
        t = tag.lower()
        # Close back to the most recent element with this tag name, so an inner
        # element that was never closed cannot leave an item open forever and a
        # same-named inner element cannot close its parent's item. An end tag
        # matching nothing open is ignored, exactly as a browser ignores it.
        for i in range(len(self._open) - 1, -1, -1):
            if self._open[i][0] == t:
                for _, opened_scope in self._open[i:]:
                    if opened_scope:
                        self._scopes -= 1
                del self._open[i:]
                break
        # Both apply: a nested item can be opened on the same tag name the
        # capture was opened on, and that end tag closes the item AND one level
        # of same-tag nesting.
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
