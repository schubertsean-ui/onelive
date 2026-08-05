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

Deliberately imports nothing from the pipeline (no promote/gating/AI) — it only
partitions raw text, it has no opinion on trust, corroboration, or publishing.
"""
from __future__ import annotations

import json
import logging
import re
from html.parser import HTMLParser
from typing import Callable, Dict, List, Optional

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

# A FULL date (as opposed to the broad date-or-time anchor above): a month name
# with a day number (either order), an ISO date, or a numeric date WITH a year.
# This is the bar a block must itself meet to need no carried context — a bare
# time or weekday does not clear it. Year-less month+day forms DO clear it:
# the year is resolved downstream against the fetch date (founder-ratified
# 2026-08-05 "Yes on the year rule"), preferring callback evidence first.
_MONTHS_SRC = r"""(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may
    |jun[e]?|jul[y]?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?
    |nov(?:ember)?|dec(?:ember)?)"""
_FULL_DATE_RE = re.compile(
    r"""(?: \b""" + _MONTHS_SRC + r"""\.?\s+\d{1,2}(?:st|nd|rd|th)?\b
      | \b\d{1,2}(?:st|nd|rd|th)?\s+""" + _MONTHS_SRC + r"""\b
      | \b\d{4}-\d{1,2}-\d{1,2}\b
      | \b\d{1,2}/\d{1,2}/\d{2,4}\b
    )""",
    re.I | re.X,
)


def _has_full_date(s: str) -> bool:
    return _FULL_DATE_RE.search(s) is not None


# Words that legitimately accompany a calendar day-header. Anything else
# ("Updated", "Tickets on sale", "Posted") marks a line that merely MENTIONS
# a date rather than governing the listings under it (evaluator finding,
# PR #189 r1: a mention adopted as context stamps wrong dates onto
# time-only blocks — worse than leaving them dateless).
_HEADER_NOISE_RE = re.compile(
    r"""(?:\b(?:mon|tues?|wed(?:nes)?|thu(?:rs?)?|fri|sat(?:ur)?|sun)(?:day)?\b
      | \b""" + _MONTHS_SRC + r"""\.?\b
      | \b\d{1,4}\b | (?:st|nd|rd|th)\b
      | [\d:/\-.,'\u2013\u2014|\u00b7\u2022]+ | \s+
    )""",
    re.I | re.X,
)


def _is_date_header(line: str) -> bool:
    """True only for a date-DOMINANT line — a real day header like
    "Tuesday, August 5" — not a sentence that mentions a date. Mechanical
    rule: after removing date vocabulary (weekday/month names, numbers,
    ordinals, separators), almost nothing may remain."""
    if not _has_full_date(line):
        return False
    residue = _HEADER_NOISE_RE.sub("", line)
    return len(residue.strip()) <= 2


def _prepend_context(block: str, ctx: Optional[str]) -> str:
    """Re-attach a page-published date line to a block that lacks its own full
    date. The context is VERBATIM page text (a section header like "Tuesday,
    August 5") — re-attachment of what the source itself published above the
    block, never synthesis (founder 2026-08-05: "No one will post or announce
    [an] event with just a time" — the date is on the page; segmentation must
    not orphan it)."""
    if ctx and not _has_full_date(block):
        return f"{ctx}\n{block}"
    return block

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


class _ElementTextCollector(HTMLParser):
    """Collect the concatenated text of each OUTERMOST element for which
    ``should_start(tag, attrs)`` is true.

    Nesting is balanced on the tag that OPENED the capture, so a matched
    element containing a same-tag descendant (a <li> inside a <li>) is one
    block, not two — we never split a container at an inner boundary.
    """

    def __init__(self, should_start: Callable[[str, Dict[str, str]], bool]) -> None:
        super().__init__(convert_charrefs=True)
        self._should_start = should_start
        self.blocks: List[str] = []
        # Per-block governing date context: the most recent full-date line the
        # page published BETWEEN captures (a calendar's day header). Aligned
        # with ``blocks`` by index; None when no such header preceded the block.
        self.contexts: List[Optional[str]] = []
        self._date_ctx: Optional[str] = None
        self._ctx_buf: List[str] = []
        self._cap_tag: Optional[str] = None
        self._depth = 0
        self._buf: List[str] = []

    def _flush_ctx(self) -> None:
        line = _ws(" ".join(self._ctx_buf))
        self._ctx_buf = []
        if not line:
            return  # a pure structural boundary changes nothing
        # SET on a real day header; CLEAR on any other page text (evaluator
        # finding, PR #189 r2: a later, unrelated section must not inherit a
        # stale prior day header — wrongly-dated is worse than dateless, so
        # intervening non-date text always drops the context).
        if len(line) <= 120 and _is_date_header(line):
            self._date_ctx = line
        else:
            self._date_ctx = None

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if self._cap_tag is not None:
            if t == self._cap_tag:
                self._depth += 1
            return
        if t in _BLOCK_LEVEL_TAGS:
            self._flush_ctx()
        if self._should_start(t, {k.lower(): (v or "") for k, v in attrs}):
            self._cap_tag = t
            self._depth = 1
            self._buf = []

    def handle_startendtag(self, tag, attrs):
        # A self-closing element carries no text content; the only effect we
        # care about is separating adjacent text while capturing.
        if self._cap_tag is not None:
            self._buf.append(" ")

    def handle_endtag(self, tag):
        if self._cap_tag is not None and tag.lower() == self._cap_tag:
            self._depth -= 1
            if self._depth == 0:
                self.blocks.append(_ws(" ".join(self._buf)))
                self.contexts.append(self._date_ctx)
                self._cap_tag = None
                self._buf = []
        elif self._cap_tag is None and tag.lower() in _BLOCK_LEVEL_TAGS:
            self._flush_ctx()

    def handle_data(self, data):
        if self._cap_tag is not None:
            self._buf.append(data)
        else:
            self._ctx_buf.append(data)


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
    c = _ElementTextCollector(should_start)
    try:
        c.feed(html)
        c.close()
    except Exception:  # noqa: BLE001 — malformed markup must never crash the pipeline
        logger.warning("HTML element collection failed", exc_info=True)
        return []
    contexts = c.contexts + [None] * (len(c.blocks) - len(c.contexts))
    return [_prepend_context(b, ctx)
            for b, ctx in zip(c.blocks, contexts)
            if len(b.strip()) >= _MIN_BLOCK_CHARS]


def _jsonld_event_blocks(html: str) -> List[str]:
    """Extract schema.org Event objects embedded as JSON-LD script blocks.

    Each Event becomes a compact text block ("Name | startDate | venue |
    address | url") from ONLY the fields literally present — no invention.
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
                events.append(block)
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
        if len(chunk) < _MIN_BLOCK_CHARS:
            continue
        if not _has_full_date(chunk):
            # Nearest full-date line ABOVE this block, but ONLY across the
            # contiguous listing region: sibling event lines (they open with
            # a date/time anchor) are skipped; any OTHER non-empty line is a
            # section boundary that TERMINATES the search (evaluator finding,
            # PR #189 r2: an old day header must not leak past an unrelated
            # section — dateless beats wrongly dated).
            ctx = None
            for line in reversed(text[:s].splitlines()):
                line = line.strip()
                if not line:
                    continue
                if len(line) <= 120 and _is_date_header(line):
                    ctx = line
                    break
                if _ANCHOR_LINE_RE.match(line):
                    continue  # a sibling listing under the same header
                break  # non-listing text: a different section governs here
            chunk = _prepend_context(chunk, ctx)
        blocks.append(chunk)
    return blocks if len(blocks) >= 2 else [text]


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

    Returns a list of text blocks, one per detected event. Heuristics, in order:
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
            return _cap(blocks)
        text = _strip_tags(content)
    else:
        text = content

    blocks = _segment_by_date_anchors(text)
    if len(blocks) >= 2:
        return _cap(blocks)

    # Not confidently multi-event: hand back the whole original content, exactly
    # as today's single-event path receives it.
    return [content]
