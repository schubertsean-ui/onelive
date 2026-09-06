"""follow(rows) — the date and place a happening's OWN page states.

Founder, this session's ticket: "For each happening whose listing_url is an
identity permalink, GET that URL (same host, on-origin only). Read date/time and
place from that page only (JSON-LD Event, ICS, visible text on that URL).
Same-page date rule still holds: clock with no date on that page stays NULL."
And: "Never invent a day. [A list page's] Date TBA is a hole, not a guess."

The split (ONE-LIVE-ENTITY-SPLIT-LAW.md §2) turned one list page into many
happenings, each holding the address the desk printed for it. Most of those rows
have an honest hole where the clock goes, because a list CARD routinely prints a
title and a link and nothing else. §4's spine answers that with the FIELD TICK:
"fetch best door -> fields (when, place, actors) same-page only". This module is
that tick, and every rule in it is a refusal to guess.

  * ONE PAGE, ONE HAPPENING'S FIELDS. A followed URL is read for the happening
    that stated it, and the fields come from THAT page's own words. Nothing is
    carried across pages: this module holds no state between reads, so a date
    from the list card has no path into the event page's clock. That is the
    ticket's third test, and it is the whole reason the same-page rule exists —
    a day from one page joined to a time from another is an instant nobody
    published.
  * A CLOCK WITH NO DATE STAYS NULL. The date rule is R-030's
    (`worker/same_page_dates.py`), imported rather than restated: machine
    carriers first (JSON-LD startDate, `<time datetime>`, ICS DTSTART), then
    visible prose, and a year missing from the page is supplied ONLY when the
    page's own weekday pins exactly one. There is no "today", no "this year",
    no next-occurrence guess anywhere in it.
  * A PAGE THAT STATES TWO DAYS HAS NOT STATED ONE. Two distinct dates, or two
    schema.org Events naming different venues, is REFUSED and reported — the
    hole stays. Which of them belongs to this happening is exactly what we
    cannot know, and picking the first would publish a real, well-formed date
    that is simply not this event's (RED_CLASSES: missing-cardinality-check).
  * A STATEMENT MUST BE ABOUT THIS HAPPENING. Structured markup says whose start
    it is about ITSELF, so a node naming another address — a sidebar, a featured
    show, a stale leftover — speaks for nothing here (`speaks_for`); printed text
    must sit in the page's content rather than its plumbing, and a clock must
    come from the same statement as the day. And the page that ANSWERS must be
    the page we asked for: a same-origin redirect onto the desk's index is a
    different address, so it is not read.
  * HOLES ONLY, NEVER AN OVERWRITE. A value the list page stated is never
    replaced. The follow can only ever turn None into something the event page
    said. `when_precision` and `when_text` travel WITH `when` as one unit, so a
    filled row is coherent afterwards rather than merely filled
    (RED_CLASSES: partial-write-whole-row).
  * A WALL IS A HOLE, QUEUED. 401/402/403/407/429 is class D through the ingest
    loop's own authority (`worker.sourcing.source_class.demote_on_response`). We
    knock ONCE: no retry, no login, no second address. The happening is kept
    exactly as it was, and the door is queued for a claim. An unread page is an
    UNKNOWN date, never an empty one.
  * THE BUDGET IS A FLOOR, NOT A FINDING. This tick opens at most `budget`
    pages. Rows past it are counted as NOT ASKED and are reported apart from
    rows whose page was read and stated no date, because the two are different
    facts and only one of them is about the desk
    (RED_CLASSES: pagination-integrity-gap).

WHAT THIS DOES NOT NARROW. Refusing to follow an off-origin permalink is a rule
about which URL this tick opens, not about which sources may carry a listing: no
row is dropped, no door is demoted, and a cross-host address stays on its row as
the next step it always was. The catalog is exactly as wide after this module
runs as before it (RED_CLASSES: hygiene-narrows-coverage).

Pure: stdlib plus this repo's own parsers. No network, no DB, no clock, no
model. `fetch` is injected and `as_of` — the calendar day the pages were fetched
on, which is what lets a page-stated weekday pin a year — is a parameter.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, replace
from datetime import date as _date, datetime, timezone as _tz
from html.parser import HTMLParser
from typing import (Callable, Dict, FrozenSet, List, Optional, Sequence,
                    Tuple)
from urllib.parse import parse_qsl, urlsplit

from worker.datetime_normalize import normalize_datetime_claim
from worker.importers.structured_feed import parse_jsonld
from worker.locale.desk_read import (
    FURNITURE_TAGS,
    says_place,
    SCOPED_FURNITURE_TAGS,
    SECTIONING_TAGS,
    Happening,
)
from worker.locale.desk_union import name_key
from worker.locale.desk_walk import DECLARED_PUBLIC, PageFetch
from worker.locale.identity_patterns import (
    IdentityPattern,
    load_patterns,
    match as match_identity,
)
from worker.same_page_dates import resolve_same_page_datetime, same_page_dates
from worker.sourcing.source_class import demote_on_response

_utc = _tz.utc

log = logging.getLogger(__name__)

#: How many event pages one tick may open. The founder's cap for this ticket:
#: "cap extra pages this ticket (default 40 permalinks, not 1565)". It is a
#: runaway backstop AND a spend ceiling; what it is not is a measurement, which
#: is why `not_followed` is counted and printed beside every table.
DEFAULT_BUDGET = 40

#: Where a clock may be found in a page's visible text. This is a LOCATOR, not a
#: parser: what it finds is handed to R-030's own clock/date rule, which decides
#: whether it means anything. Keeping it here (rather than reaching into that
#: module's internals) means a drift in this regex can only ever make us find
#: FEWER clocks — it cannot change what a found one is taken to mean.
_CLOCK_TOKEN_RE = re.compile(
    r"\b\d{1,2}(?::[0-5]\d)?\s*[ap]\.?m\.?\b"
    r"|\b(?:[01]?\d|2[0-3]):[0-5]\d\b", re.IGNORECASE)

#: Tag-stripping for that locator only, mirroring R-030's `_visible_text`:
#: script/style bodies go FIRST so a JSON-LD payload's own times are not read as
#: printed prose.
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)

#: An ISO value that already carries a time of day: `2026-09-06T21:00`, or ICS's
#: compact `20260906T210000`. Used to tell a date carrier that states the whole
#: instant from one that states only the day.
#:
#: The compact arm is anchored to the `T` deliberately. Written as `[T ]\d{2}\d\d`
#: it also matched the SPACE before a printed year — "September 6, 2026" read as
#: a time of day, so a prose date came back as a confident midnight and the
#: page's own printed clock was never consulted. A carrier either states the
#: instant or it does not; there is no third answer, so this test has to be exact.
_HAS_CLOCK_RE = re.compile(r"\d:[0-5]\d|T[0-2]\d[0-5]\d")

#: schema.org properties that name where a happening is.
_PLACE_ITEMPROPS = frozenset({"location", "address"})

#: What a page uses to say what it is ABOUT, STRONGEST FIRST. `<h1>` is the
#: page's subject by HTML's own semantics; `<h2>`/`<h3>` are subheadings and
#: stand in only for a page that prints no `<h1>` at all.
#:
#: The order matters and is the r6 finding: taking the FIRST heading of ANY of
#: these let a promotional block placed above the real article — carrying its
#: own `<h2>`, date and venue — become the page's subject and push the real
#: event content outside the card (evaluator, PR #235 r6,
#: openai/attacker-smuggle). A subheading is not a subject while a subject
#: exists.
_HEADING_TAGS = ("h1", "h2", "h3")


def _pick_subject(marks: Sequence[Tuple[str, Tuple[int, ...], str]],
                  top_sections: Sequence[int] = ()
                  ) -> Optional[Tuple[int, ...]]:
    """The sectioning elements enclosing the page's SUBJECT heading.

    ONE definition, used by both scanners and mirrored by `_headings` for the
    text side — the r6 absence-only finding was exactly these two drifting: the
    card boundary already treated `<h2>` as a page subject while the identity
    check still read only `<h1>`/`<title>`, so a page whose visible subject is
    an `<h2>` had NO headings to contradict a poisoned node with.

    A page that prints NO heading has to be answered without one, and
    "nothing is known, so exclude nothing" was the third and last fail-open
    default in this rule (evaluator, PR #235 r9, openai/absence-only): a
    title-only or image-headed page with an unrelated promo `<section>`
    published that section's date and venue. Not knowing what a page is about
    is a reason to trust it LESS, not more.

    But page-level-only is too blunt, and the tests said so: a heading-less page
    whose content sits in ONE `<article>` would lose everything. So when the
    page has exactly one top-level card, that card is the subject — it is the
    only thing the page could be about.

    Two or more, and r9 answered `()` — page level only, every section
    excluded. That reads as restrictive and IS restrictive on a page built from
    sectioning elements. It is the opposite on a page built from `<div>`s:
    `<div>` is a block boundary and not a sectioning tag, so such a page has NO
    top-level sections, every statement on it sits at page level, and `()`
    admits all of them — an unrelated promo `<div>` on a title-only page
    published its date and venue with no refusal at all (evaluator, PR #235
    r12, openai/attacker-smuggle; reproduced as `2026-12-25T20:00:00` at 'The
    Other Room'). Whether the rule fail-closed or fail-open depended on the
    desk's markup STYLE, which is the worst way for a trust boundary to vary.

    So the two situations are told apart, because they were never the same
    question. `()` means THE PAGE LEVEL IS THE SUBJECT — a heading exists and
    sits in no section, so its own statements are page-level ones (r6, tested).
    `None` means NO SUBJECT COULD BE IDENTIFIED — no heading at all, and no
    single card to fall back on — and nothing on such a page is inside a card
    this module can name. Not knowing what a page is about is a reason to trust
    it less, and that has to hold for every markup style, not just the one the
    fixture used.
    """
    for tag in _HEADING_TAGS:
        for mark_tag, sections, _text in marks:
            if mark_tag == tag:
                return sections
    alone = set(top_sections)
    return (top_sections[0],) if len(alone) == 1 else None


def _inside_the_card(sections: Tuple[int, ...],
                     subject: Optional[Tuple[int, ...]]) -> bool:
    """Is a statement printed inside the page's own card?

    The card is the innermost sectioning element holding the page's subject
    heading — or, when the heading sits in none, the page level itself.

    Both halves are r6 findings and they pull opposite ways, so the rule needs
    both clauses:

      * a statement OUTSIDE the heading's section is not the page's own (a
        month-grid `<table>` at body level beside an `<article>` that states
        the show's day) — so the heading's sections must be a PREFIX of the
        statement's, which also admits a subsection of the card;
      * a statement inside ANY section when the heading is in none is not the
        page's own either (an unlinked promo `<section>` supplying the only
        date on a page whose heading sits directly in `<body>`). Treating a
        sectionless heading as "no boundary at all" left exactly that open
        (evaluator, PR #235 r6, openai/attacker-smuggle).

    The third case — a page printing no heading at all — is the page level too,
    and it is the one r9 caught still fail-open. `_pick_subject` returns `()`
    for it rather than `None`, so it lands on the clause below and a promo
    `<section>` on an image-headed page is excluded like any other.
    """
    if subject is None:      # no caller produces this; kept as a fail-closed arm
        return False
    if not subject:
        return not sections
    return sections[:len(subject)] == subject

#: Elements whose text is never a place (or anything else this page STATES).
#: Form controls earn their place here from the live run: a `<select>` of
#: restaurant categories sitting inside a venue-labelled block was read as one of
#: the page's two "places". A picker offers choices; it does not say where this
#: happening is.
_SKIP_TEXT_TAGS = frozenset({
    "script", "style", "template", "select", "option", "optgroup", "datalist",
    "textarea", "button", "label",
})

#: Block-level containers. A page's printed text is cut into SEGMENTS on these,
#: and a segment is the closest thing a page has to "one statement": inline
#: markup (`span`, `a`, `time`, `em`) folds into the segment around it, so
#: `<span class="date">Sat Sep 5</span><span>9:00PM</span>` inside one `<div>`
#: is one statement, while two sibling `<div>`s are two.
_BLOCK_TAGS = frozenset({
    "address", "article", "aside", "blockquote", "dd", "details", "div", "dl",
    "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
    "h3", "h4", "h5", "h6", "header", "hgroup", "li", "main", "nav", "ol", "p",
    "pre", "section", "table", "tbody", "td", "tfoot", "th", "thead", "tr",
    "ul",
})

#: Date carriers that can say WHOSE start they are. A `<time>` tag and printed
#: prose cannot: they are text on a page, and have to be tied to this happening
#: by where they sit before they may date it.
#:
#: Being in this set is necessary, not sufficient. ICS qualifies outright — a
#: calendar file served AT this address is this happening's. JSON-LD says whose
#: start it is about ITSELF, and a permalink page can carry a node for something
#: else entirely, so a node must also SPEAK FOR this row (`speaks_for`) before
#: `field_read` treats it as event-scoped. Reading this constant as sufficient
#: on its own let a sidebar's node publish 2026-12-25 at "The Other Room" onto a
#: row titled something else (evaluator, PR #235 r2).
_EVENT_SCOPED_KINDS = frozenset({"jsonld", "ics"})

#: Carriers that are not part of any printed statement: a `<script>` payload, an
#: embedded calendar body. They state a moment on their own authority and own no
#: segment of the page's prose, so no clock printed elsewhere is theirs to take.
#: (Same members as the set above today, and a different question — that one asks
#: WHOSE start a carrier states, this one asks WHERE on the page it lives.)
_DOCUMENT_LEVEL_KINDS = frozenset({"jsonld", "ics"})


class DeskFollowError(ValueError):
    """The follow cannot run as asked — a caller that handed us something this
    module cannot classify. Raised, never downgraded to an empty result that
    would read as "no page stated anything".
    """


def _visible(html: str) -> str:
    return _TAG_RE.sub(" ", _SCRIPT_STYLE_RE.sub(" ", html or ""))


class _SegmentScanner(HTMLParser):
    """The page's printed text, cut into statements, with its plumbing removed.

    Two jobs, both from the evaluator's blocking finding on PR #235
    (openai/absence-only): a page's only date can be a "last updated" stamp in
    the footer, and a page's only clock can be a box office's opening hour — and
    a reader that takes "the one date anywhere" and "the one clock anywhere"
    publishes a well-formed instant that nobody stated.

      * FURNITURE IS NOT A STATEMENT ABOUT THIS HAPPENING. Text inside `<nav>`
        or `<aside>`, or inside a PAGE-level `<header>`/`<footer>`, is dropped —
        the same structural rule (and the same tag sets) `desk_read` already
        uses to keep a nav link from becoming a listing. Structural, not a list
        of chrome words: "updated", "posted" and "box office" are English, and
        an enumeration of them would look complete while missing the next one.
      * A SEGMENT IS ONE STATEMENT. `<time datetime>` values are inlined into
        the segment that printed them, so the machine form and the printed form
        of one statement stay together.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.segments: List[str] = []
        #: The card each segment was printed in, same scheme as the place scan:
        #: the ids of every element open when the segment started.
        self.segment_scopes: List[Tuple[int, ...]] = []
        #: (tag, enclosing sectioning ids, text) for every heading outside
        #: plumbing. The TEXT rides along so the identity check and the card
        #: boundary read one walk — see `_headings`.
        self.heading_marks: List[Tuple[str, Tuple[int, ...], str]] = []
        #: Ids of the page's top-level sectioning elements, in document order.
        self.top_sections: List[int] = []
        self._heading_open: Optional[Tuple[str, Tuple[int, ...]]] = None
        self._heading_parts: List[str] = []
        self._parts: List[str] = []
        self._skip = 0
        self._furniture = 0
        self._open: List[str] = []
        self._next_id = 0
        self._started_in: Tuple[int, ...] = ()

    def _flush(self) -> None:
        text = " ".join(" ".join(self._parts).split())
        if text:
            self.segments.append(text)
            self.segment_scopes.append(self._started_in)
        self._parts = []
        self._started_in = self._sections()

    def _sections(self) -> Tuple[int, ...]:
        """The sectioning elements currently open, outermost first."""
        return tuple(sid for _tag, _f, sid in self._open if sid is not None)

    def _in_sectioning(self) -> bool:
        return any(tag in SECTIONING_TAGS for tag, _f, _s in self._open)

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _SKIP_TEXT_TAGS:
            self._skip += 1
            return
        # Whether this element OPENED plumbing is remembered on the stack, and
        # only the elements that opened it close it. Deciding again at the close
        # tag gets it wrong the moment plumbing nests: a card's own `<footer>`
        # inside the page `<footer>` would decrement a counter it never raised,
        # and the rest of the page footer would stop being plumbing — putting
        # the site's "last updated" stamp back in play as a show's day. Found by
        # probing my own fix for this class before pushing it.
        furniture = tag in FURNITURE_TAGS or (
            tag in SCOPED_FURNITURE_TAGS and not self._in_sectioning())
        if furniture:
            self._flush()
            self._furniture += 1
        section_id = None
        if tag in SECTIONING_TAGS:
            self._next_id += 1
            section_id = self._next_id
            if not self._sections():
                # A sectioning element with no sectioning ancestor: one of the
                # page's top-level cards. Counted so a page with no heading can
                # still know whether it has exactly ONE.
                self.top_sections.append(section_id)
        self._open.append((tag, furniture, section_id))
        if tag in _HEADING_TAGS and not self._furniture:
            # Every heading is RECORDED; which one is the page's subject is
            # decided at close by `_pick_subject`, because a streaming scan
            # cannot know whether an <h1> is still coming.
            self._heading_open = (tag, self._sections())
            self._heading_parts = []
        if tag in _BLOCK_TAGS:
            self._flush()
        if tag == "time" and not self._furniture and not self._skip:
            stated = " ".join((dict(
                (k.lower(), v or "") for k, v in attrs).get("datetime") or "").split())
            if stated:
                self._parts.append(stated)

    def handle_startendtag(self, tag, attrs):
        if tag.lower() == "time":
            self.handle_starttag(tag, attrs)
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _SKIP_TEXT_TAGS:
            self._skip = max(0, self._skip - 1)
            return
        if self._heading_open is not None and tag == self._heading_open[0]:
            text = " ".join(" ".join(self._heading_parts).split())
            open_tag, sections = self._heading_open
            self.heading_marks.append((open_tag, sections, text))
            self._heading_open = None
            self._heading_parts = []
        if tag in _BLOCK_TAGS:
            self._flush()
        if any(open_tag == tag for open_tag, _f, _s in self._open):
            while self._open:
                closed, opened_furniture, _section = self._open.pop()
                if opened_furniture:
                    self._parts = []   # anything buffered in plumbing is dropped
                    self._furniture = max(0, self._furniture - 1)
                if closed == tag:
                    break
            self._started_in = self._sections()

    def handle_data(self, data):
        if not self._skip and not self._furniture:
            self._parts.append(data)
            if self._heading_open is not None:
                self._heading_parts.append(data)

    def close(self):
        super().close()
        self._flush()


def segments(html: str) -> List[str]:
    """The page's statements about ITSELF, plumbing removed. Empty when nothing
    can be read.

    THE CARD BOUNDARY APPLIES TO THE DATE PATH TOO. Rounds 1-5 gave the date its
    scope (plumbing excluded structurally) and its locality (a clock comes from
    the statement that gave the day), and round 5 gave the PLACE a card — the
    section holding the page's own heading. The date path still read every
    non-plumbing segment, so a related or promotional block printing the only
    date and clock on the page could date this row (evaluator, PR #235 r5,
    openai/attacker-smuggle: "a related/unlinked promo block in page content
    that prints the only date/clock can be attached to the current row").

    One boundary, both fields: a statement outside the section holding the
    page's heading is about something else. A page whose heading is in no
    section is ONE card and keeps all of its statements.
    """
    scanner = _SegmentScanner()
    try:
        scanner.feed(html or "")
        scanner.close()
    except Exception as exc:  # noqa: BLE001 — a pathological page states nothing, it never crashes
        log.debug("segment scan raised on a followed page: %s", exc)
        return []
    subject = _pick_subject(scanner.heading_marks, scanner.top_sections)
    return [text for text, scope in zip(scanner.segments, scanner.segment_scopes)
            if _inside_the_card(scope, subject)]


def _host(url: Optional[str]) -> str:
    host = (urlsplit(url or "").hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _address(url: Optional[str]) -> Tuple[str, str, Tuple[Tuple[str, str], ...]]:
    """The (host, path, query) a URL names, as one address.

    THE QUERY IS PART OF THE ADDRESS. It was dropped here until PR #235 r11
    (evaluator, openai/absence-only), which put this module at odds with the
    one that decides what a row IS: `desk_read._identity_of` KEEPS the query
    and says why in its own docstring — "two desks do use `?date=` to address
    two instances of one series, and collapsing those would delete a night".
    So for such a desk every night of a run shared one address here, and the
    two things this comparison guards both fell open: a redirect from one night
    to another passed `same_identity`, and a structured node naming a different
    night read as speaking for this one. Runs are not a hypothetical on this
    desk — they are the largest single cause of the refusals r8 exists for.

    The fragment is still dropped (it addresses a position inside a page, never
    another happening) and a trailing slash still normalises, both matching
    `_identity_of`. Tolerance for a query the DESK adds on a redirect belongs
    to `same_identity`, where it can be asymmetric, not here where it would
    also blind the node comparison.
    """
    parts = urlsplit(url or "")
    path = (parts.path or "/").rstrip("/") or "/"
    query = tuple(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    return _host(url), path, query


def _shown(address: Tuple[str, str, Tuple[Tuple[str, str], ...]]) -> str:
    """An address as a reader would see it in a refusal — path and query.

    The query joined the address at r11 and it has to reach the DIAGNOSTIC too:
    on a desk addressing a run with `?date=`, every night shares one path, so a
    message printing the path alone would say two nights have the same address
    and make a correct refusal read like a bug.
    """
    _host_part, path, query = address
    return path + ("?" + "&".join(f"{k}={v}" for k, v in query) if query else "")


def same_identity(landed: Optional[str], asked: Optional[str]) -> bool:
    """True when the page that answered is the page we asked for.

    Host, path AND query, all three exactly.

    r11 tolerated parameters the desk ADDED, on the argument that an added
    parameter cannot change which happening was addressed — and where the asked
    url carried no query at all, that its identity must therefore live in the
    path. Both halves were the same mistake this ticket keeps making: correct
    about the redirect in front of me, silent one step past it. `/event/show` →
    `/event/show?date=2026-09-19` is a desk CHOOSING an instance of a run for
    us, and the list page linking the run's own page rather than a night's is
    exactly how a row ends up with no query on a desk whose identity is
    query-based (evaluator, PR #235 r13, openai/absence-only).

    The `?ref=calendar` case r11 was protecting is a HYPOTHETICAL — no run in
    this ticket's evidence saw one — and telling a tracking parameter from an
    identifying one needs a registry of parameter names, which is the same
    class as the chrome-word list refused at r1: host knowledge in code. So the
    cost is paid the honest way: a desk that redirects with an added parameter
    is QUEUED with its reason, its row keeps its holes, and nothing is dropped
    or guessed. A hole we can see beats a field we cannot justify.
    """
    return _address(landed) == _address(asked)


# --------------------------------------------------------------------------
# What ONE page states
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class FieldRead:
    """The date and place ONE event page stated about itself, holes and all.

    `refusals` is the honest half: every field this page did not settle says why
    it did not, in the page's own terms ("clock with no date", "states 2 dates").
    A hole with no reason would be indistinguishable from a page nobody read.
    """

    url: str
    when: Optional[str] = None
    when_precision: Optional[str] = None
    when_text: Optional[str] = None
    #: Which carrier stated the date: `jsonld`, `time-tag`, `ics`,
    #: `visible-date` or `visible-weekday` (R-030's own vocabulary).
    when_carrier: Optional[str] = None
    place_text: Optional[str] = None
    #: `jsonld` or `labelled` — a page element the page itself marks as the
    #: location. Free prose is never a place.
    place_carrier: Optional[str] = None
    refusals: Tuple[str, ...] = ()
    #: The same refusals as short, stable CODES. The sentences above are for a
    #: person reading one page; these are for counting across a thousand of
    #: them, which is how "still_null_n is 1568" turns into a repairable fact
    #: instead of a number (ONE-LIVE-ENTITY-SPLIT-LAW.md §9.3: record it as
    #: data, not chat).
    codes: Tuple[str, ...] = ()

    @property
    def states_anything(self) -> bool:
        return bool(self.when or self.place_text)


class _PlaceScanner(HTMLParser):
    """Every element this page LABELS as the location, each captured whole.

    Labelled means the page said so: `itemprop="location"`/`"address"`, or a
    class/id naming a venue or a location. Prose is not scanned — a place read
    out of running text would be whatever noun happened to follow "at", which is
    a guess wearing an address's clothes.

    Nested labels collapse into the outermost one (an `itemprop="location"`
    holding an `itemprop="address"` is ONE statement about where), so a page
    does not look like it named two places by marking up one carefully.

    The page's own plumbing is skipped for the same reason the date rule skips
    it: a `<footer class="address">` holding the publisher's office is a
    statement about the SITE, and reading it would give every happening on that
    desk the desk's own address.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.places: List[str] = []
        #: Every address this page's CONTENT links to, under exactly the same
        #: plumbing rule the places are read by — so "does this page's content
        #: point at another happening" can be asked without a second parse and
        #: without a second definition of what counts as content.
        self.links: List[str] = []
        self._depth = 0
        self._parts: List[str] = []
        self._skip = 0
        self._furniture = 0
        self._open: List[str] = []
        #: A monotonic id per opened SECTIONING element, so a card can be
        #: named without buffering its subtree.
        self._next_id = 0
        #: (tag, enclosing sectioning ids, "") for every heading outside
        #: plumbing. This scan needs only the sections; the text side is read
        #: once, by the segment scan.
        self.heading_marks: List[Tuple[str, Tuple[int, ...], str]] = []
        #: Ids of the page's top-level sectioning elements, in document order.
        self.top_sections: List[int] = []
        #: Enclosing sectioning ids at the moment each place was captured.
        self._opened_in: Tuple[int, ...] = ()
        self.place_scopes: List[Tuple[int, ...]] = []

    @staticmethod
    def _labelled(attrs: Dict[str, str]) -> bool:
        if (attrs.get("itemprop") or "").strip().lower() in _PLACE_ITEMPROPS:
            return True
        return any(says_place(attrs.get(name))
                   for name in ("class", "id"))

    def _sections(self) -> Tuple[int, ...]:
        """The sectioning elements currently open, outermost first."""
        return tuple(sid for _tag, _f, sid in self._open if sid is not None)

    def _in_sectioning(self) -> bool:
        return any(tag in SECTIONING_TAGS for tag, _f, _s in self._open)

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _SKIP_TEXT_TAGS:
            self._skip += 1
            return
        # Same stack discipline as the segment scanner: only the element that
        # opened plumbing closes it, so nested `<footer>`s cannot un-suppress
        # the page footer around them.
        furniture = tag in FURNITURE_TAGS or (
            tag in SCOPED_FURNITURE_TAGS and not self._in_sectioning())
        if furniture:
            self._furniture += 1
        section_id = None
        if tag in SECTIONING_TAGS:
            self._next_id += 1
            section_id = self._next_id
            if not self._sections():
                # A sectioning element with no sectioning ancestor: one of the
                # page's top-level cards. Counted so a page with no heading can
                # still know whether it has exactly ONE.
                self.top_sections.append(section_id)
        self._open.append((tag, furniture, section_id))
        if tag in _HEADING_TAGS and not self._furniture:
            # Every heading is RECORDED; which one is the page's subject is
            # decided at close by `_pick_subject`, because a streaming scan
            # cannot know whether an <h1> is still coming.
            self.heading_marks.append((tag, self._sections(), ""))
        if tag == "a" and not self._skip and not self._furniture:
            href = " ".join(
                (dict((k.lower(), v or "") for k, v in attrs).get("href") or "").split())
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                self.links.append(href)
        if self._depth:
            self._depth += 1
            return
        if self._furniture:
            return
        flat = {k.lower(): (v or "") for k, v in attrs}
        if self._labelled(flat):
            self._depth = 1
            self._parts = []
            self._opened_in = self._sections()
            # schema.org may state the value in `content` when the visible text
            # is something else; that stated value is the place.
            stated = " ".join((flat.get("content") or "").split())
            if stated:
                self._parts.append(stated)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _SKIP_TEXT_TAGS:
            self._skip = max(0, self._skip - 1)
            return
        if any(open_tag == tag for open_tag, _f, _s in self._open):
            while self._open:
                closed, opened_furniture, _section = self._open.pop()
                if opened_furniture:
                    self._furniture = max(0, self._furniture - 1)
                if closed == tag:
                    break
        if not self._depth:
            return
        self._depth -= 1
        if self._depth == 0:
            text = " ".join(" ".join(self._parts).split())
            if text:
                self.places.append(text)
                self.place_scopes.append(getattr(self, "_opened_in", ()))
            self._parts = []

    def handle_data(self, data):
        if self._depth and not self._skip:
            self._parts.append(data)


def _named(event: Dict[str, object], page_url: str) -> set:
    """Every address a structured node names for ITSELF (`url`, `@id`/`uid`),
    resolved against the page it was published on.

    A publisher may state a ROOT-RELATIVE address ("/event/show-1"); skipping
    those would both lose a bind that exists and, worse, let a sidebar node
    naming `/event/other-99` look address-less and speak for this row. Resolving
    is therefore the strict direction as well as the useful one (evaluator NIT,
    PR #235 r3, gemini/spec-vs-contract).
    """
    from urllib.parse import urljoin
    out = set()
    for key in ("url", "uid"):
        raw = str(event.get(key) or "").strip()
        if not raw or raw.startswith(("mailto:", "tel:", "#")):
            continue
        resolved = raw if raw.lower().startswith(("http://", "https://")) else (
            urljoin(page_url, raw) if raw.startswith("/") else "")
        if resolved.lower().startswith(("http://", "https://")):
            out.add(_address(resolved))
    return out


def _instant_key(value: Optional[str]):
    """A comparable key for one stated instant, or None.

    `parse_jsonld` hands back a node's start already normalised to UTC, while
    `same_page_dates` keeps the page's RAW text — the same moment written two
    ways ("2026-12-26T02:00:00Z" and "2026-12-25T20:00:00-06:00"). Matching a
    date HIT back to the node that emitted it therefore has to compare instants,
    not strings.

    A value carrying no offset is read as UTC, which is what
    `structured_feed._to_utc_z` already did to the node side. Read any other way
    the two halves of the SAME node stop matching, and every desk that omits an
    offset would hole every one of its pages. This key only ever pairs a hit
    with the node that emitted it; nothing is published from it, and nothing
    about a row's stored timezone depends on it.
    """
    if not value:
        return None
    iso, _refusal = normalize_datetime_claim(value)
    if not iso:
        return None
    try:
        moment = datetime.fromisoformat(iso)
    except ValueError:  # pragma: no cover — normalize_datetime_claim round-trips
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=_utc)
    return moment.astimezone(_utc).timestamp()


def _named_urls(event: Dict[str, object], url: str) -> FrozenSet[str]:
    """The absolute addresses a node names, as addresses the identity table can
    be asked about. ONE definition: the arm of `speaks_for` that consults the
    table and the refusal that explains it must ask the same question, or the
    report describes a rule the code did not apply.

    A relative `url` or `@id` is resolved against the page. Written as a bare
    string comparison it bound nothing, so a desk publishing `/event/1846201`
    on `https://desk.test/event/1846201` looked like a node about somewhere
    else (gemini NIT, PR #235 r3).
    """
    from urllib.parse import urljoin
    out = set()
    for key in ("url", "uid"):
        raw = str(event.get(key) or "").strip()
        if raw and not raw.startswith(("mailto:", "tel:", "#")):
            out.add(raw if raw.lower().startswith(("http://", "https://"))
                    else urljoin(url, raw))
    return frozenset(out)


#: The document `<title>`. A WEAKER signal than a visible heading and read only
#: as a fallback — see `_headings`.
_TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _headings(html: str) -> List[str]:
    """What this page calls ITSELF, strongest evidence only.

    THE VISIBLE SUBJECT WINS, AND `<title>` IS ONLY A FALLBACK. Feeding both
    into one list let a STALE `<title>` rescue a node the visible `<h1>`
    contradicts — a CMS title goes stale routinely, and a poisoned schema.org
    Event naming the stale title would match it, contradict nothing, and fill
    this row's holes (evaluator, PR #235 r7, openai/absence-only). A page that
    prints its own subject has said what it is about; the tab caption does not
    get a second vote.

    Read from the SEGMENT SCAN rather than a regex over raw HTML, so headings
    inside `<nav>`, `<aside>` or a page-level `<header>`/`<footer>` are excluded
    by exactly the rule that excludes their text elsewhere (gemini NIT, same
    round). That also removes the last place where the heading rule was
    expressed twice: one walk, one precedence, one answer.

    Subheadings of a page that HAS an `<h1>` stay out: a promotional `<h2>`
    naming another show must not become a name this page answers to.
    """
    scanner = _SegmentScanner()
    try:
        scanner.feed(html or "")
        scanner.close()
    except Exception as exc:  # noqa: BLE001 — a pathological page names itself nothing
        log.debug("heading scan raised on a followed page: %s", exc)
        return []
    for tag in _HEADING_TAGS:
        named = [text for mark_tag, _sections, text in scanner.heading_marks
                 if mark_tag == tag and text]
        if named:
            return named
    title = _TITLE_RE.search(html or "")
    if title:
        text = " ".join(_TAG_RE.sub(" ", title.group(1)).split())
        if text:
            return [text]
    return []


def _wall_clock(iso: Optional[str]) -> Optional[Tuple[int, int]]:
    """The hour and minute an ISO string states, as written.

    LOCAL, not UTC: `2026-09-18T19:30:00-05:00` is a desk saying half past
    seven in the evening, and that is what its own card is compared against.
    Converting first would compare 00:30 the next day with the card's 8pm and
    call every desk a liar (the r3 lesson, applied before it could bite).
    """
    if not iso:
        return None
    try:
        moment = datetime.fromisoformat(iso)
    except ValueError:  # pragma: no cover — callers pass normalised values
        return None
    return moment.hour, moment.minute


#: Does a printed time say WHICH HALF OF THE DAY it means? Not a second clock
#: parser — one boolean about the raw characters, so the armed `same_page_dates`
#: stays the only thing that reads a time. Written narrowly on purpose: it is
#: asked only of tokens that module has already agreed are clocks.
_MERIDIEM_RE = re.compile(r"[ap]\.?\s?m\b", re.I)


def _clock_agrees(token: str, stated: Tuple[int, int], day: str,
                  as_of: Optional[_date]) -> Optional[bool]:
    """Does this printed time agree with the instant the markup states?

    `None` when the token cannot be read at all — an unreadable statement is
    not a contradicting one, and holing a field over text nobody could parse
    would fail closed on our own limits rather than on the desk's.

    Found by reading the first live run of r14's own rule, which is the third
    time this ticket a check was corrected by its own diagnostics. The run
    reported `/event/boeing-boeing-14285657` as contradicting itself because its
    card prints "7:30" while its markup states `19:30` — and 19:30 IS half past
    seven. A bare "7:30" states a clock face, not an hour of the day; anchoring
    it read 07:30 and called the desk a liar for agreeing with itself.

    So a token carrying no am/pm is compared modulo twelve hours: it agrees with
    either reading, because the desk did not say which it meant. That is the
    conservative direction and it is the same principle r12 stated and r14 then
    applied backwards — AN AMBIGUOUS STATEMENT IS NOT A CONTRADICTING ONE. The
    cost is real and small: a card printing a bare "9:00" no longer contradicts
    markup saying 21:00, which is precisely the case where the card has not said
    which one it means.

    A token that DOES say am or pm is compared exactly, so "8:00PM" against a
    19:30 node still refuses — the r10 finding, untouched. The comparison is
    ASYMMETRIC and has to be: the markup's instant is unambiguous by
    construction, and only the printed side can be a bare face.
    """
    iso, _refusal, _evidence = resolve_same_page_datetime(
        token, block_text=f"{day} {token}", as_of=as_of)
    wall = _wall_clock(iso)
    if wall is None:
        return None
    if _MERIDIEM_RE.search(token):
        return wall == stated
    return (wall[0] % 12, wall[1]) == (stated[0] % 12, stated[1])


def _name_tokens(name: str) -> List[str]:
    """A name as comparable words, in ANY script.

    Written `[^0-9a-z]` this stripped every character outside the Latin
    alphabet, and the damage ran both ways (evaluator, PR #235 r10,
    openai/attacker-smuggle). A page headed "Кино Night" collapsed to "night"
    and matched an unrelated node called "Night". Worse, and unreported: a page
    headed "Кино" alone collapsed to the EMPTY STRING, so `_same_name` could
    never be true for it — every lone node on that page refused, and every
    bound node read as contradicting the heading. A whole desk in a non-Latin
    script could not fill a single field, which is a LOCALE REFUSED IN CODE and
    Coverage Law forbids it outright. It was invisible because every fixture
    and every desk in this repo is English.

    The fix is NOT a new tokenizer. `worker/locale/desk_union` already carries
    this repo's answer — three review rounds deep against the
    `destructive-normalization` red class, which names "Кино Night -> night"
    and "Café -> caf" as its own worked examples. Writing a second one here is
    how the same defect got in: the class was recorded, the remedy was two
    modules away, and I typed the regex it warns about. One question, one
    answer, imported.
    """
    return name_key(name).split()


def _names_within(text: str, name: str) -> bool:
    """Does this text NAME this place — anywhere inside it?

    A different question from `_same_name`, split out at r15 because the two
    callers' dangerous answers point in opposite directions and this repo has
    already paid for that once (`destructive-normalization` r9: "if they do not,
    they share a NAME rather than a helper"). Identity fails badly on a false
    YES — another happening's node binds to this row. A labelled block fails
    badly on a false NO — the desk is reported as contradicting itself and a
    place we had is holed.

    So identity keeps r13's leading-token rule and this keeps plain containment:
    a card printing "Venue Details TexARTS 1110 S RR 620, Lakeway…" beside a
    node saying "TexARTS" names the same place, and the live run holed it as a
    contradiction until this split.

    Containment only, and only in this direction: the TEXT may say more than
    the name. A one-token floor still applies — a block containing the letter
    "A" has not named a venue called "A".
    """
    haystack, needle = _name_tokens(text), _name_tokens(name)
    if not haystack or not needle:
        return False
    if len(needle) < 2 and len(needle[0]) < 2:
        return False
    span = len(needle)
    return any(haystack[i:i + span] == needle
               for i in range(len(haystack) - span + 1))


def _same_name(a: str, b: str) -> bool:
    """Two names for the same thing, compared the way a reader would.

    Case, punctuation and spacing are noise ("Boeing Boeing" / "boeing-boeing").
    Containment is on whole WORDS and either way round, because a desk routinely
    heads a page with more than the node's name ("Prodigal Sun at Saengerrunde
    Hall") or with less — but "A" must not match "A Show", so a single letter
    names nothing.

    ONE WORD MUST MATCH AT THE START. R-113 recorded loose single-token
    containment as a bound residual and the bound did not cover the harm: a lone
    node called "Night" on a page headed "Jazz Night" bound, and published
    `2026-12-25T20:00:00-06:00` at 'The Other Room' with codes=() — not "a wrong
    field on the right happening", which is what the record said, but a whole
    fabricated instant (evaluator, PR #235 r13, openai/attacker-smuggle;
    `deferred-trust-work`, second time in this ticket).

    Position is the discriminator, and it costs nothing this desk uses. Headings
    are written `<name> <qualifier>` — "Gandahar (1988)", "Mohawk Austin",
    "Кино Night" — never `<qualifier> <name>`, so a lone word that opens the
    longer name is plausibly what it names, while one buried inside it is a
    fragment of somebody else's. The r10 objection to a leading-token rule was
    "Live at the Continental Club" vs "Continental Club", and that is a TWO
    token name: multi-token containment is unchanged, anywhere in the string.
    """
    left, right = _name_tokens(a), _name_tokens(b)
    if not left or not right:
        return False
    if left == right:
        # Identical names need no floor. A desk heading a page "D" with a node
        # called "D" has said the same thing twice, and refusing that was the
        # floor misfiring on an exact match rather than on a short containment.
        return True
    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    if len(shorter) < 2:
        return len(shorter[0]) >= 2 and longer[0] == shorter[0]
    span = len(shorter)
    return any(longer[i:i + span] == shorter
               for i in range(len(longer) - span + 1))


def _node_name(event: Dict[str, object]) -> str:
    return " ".join(str(event.get("title") or event.get("name") or "").split())


def _contradicts_this_page(event: Dict[str, object],
                           headings: Sequence[str]) -> bool:
    """Does this node call itself something this page does NOT call itself?

    The weaker half of the identity question, for a node that has already
    asserted its address. ABSENCE IS NOT DISAGREEMENT: a node with no name, or
    a page with no heading, contradicts nothing and keeps the bind it earned by
    naming this address. Only two names that both exist and match nothing in
    each other are a contradiction.
    """
    name = _node_name(event)
    if not name or not headings:
        return False
    return not any(_same_name(name, heading) for heading in headings)


def _names_this_page(event: Dict[str, object], headings: Sequence[str]) -> bool:
    """Does this node say it is ABOUT the thing this page is about?

    THE QUESTION IS IDENTITY, NOT AGREEMENT. The first version of this check
    asked whether the page's own content stated the DAY the node claims, and
    the live desk showed what is wrong with that: on
    `/event/prodigal-sun-14267156` the node states Sep 4 and the page displays
    Sep 6, because a run of performances has more than one date and the two
    statements are about different ones. That is not evidence the node belongs
    to another happening — and refusing on it took `structured-not-bound` from
    2 pages to 17 of 40, with 14 of them falling through to a date they could
    only find in their own plumbing.

    A node that names what the page names is this page's node. A promotional or
    stale Event is about something else and says so in its own `name`, which is
    exactly the evaluator's case (PR #235 r4: a node called "Something Else" on
    a page headed "Dominic Fike").
    """
    name = _node_name(event)
    if not name:
        return False
    return any(_same_name(name, heading) for heading in headings)


def speaks_for(events: Sequence[Dict[str, object]], url: str,
               patterns: Sequence[IdentityPattern] = (),
               *, headings: Sequence[str] = ()
               ) -> List[Dict[str, object]]:
    """The structured nodes on this page that are about THIS happening.

    A schema.org `Event` says whose start it is — but only about ITSELF, and a
    permalink page can publish one for something else entirely: a "related
    events" sidebar, a site-wide featured show, a stale node left behind when
    the listing changed. Treating any Event node on the page as this
    happening's took a sidebar's `startDate` and published 2026-12-25 at "The
    Other Room" for a row titled something else (evaluator, PR #235 r2,
    openai/attacker-smuggle; reproduced before fixing).

    So a node speaks for this happening only when it does not name a DIFFERENT
    address:

      * it names THIS address (`url` or `@id` resolving to the followed
        permalink) — the strong bind, and the common case;
      * or it is the page's only Event node AND it names no address at all — a
        permalink page publishing an Event about itself;
      * or it is the page's only Event node, the address it names is not
        ANOTHER HAPPENING'S, AND the page's own printed content states the day
        that node claims.

    That third arm needs both halves, and the second half is round 4's finding
    (evaluator, PR #235 r4, openai/attacker-smuggle): ABSENCE FROM THE IDENTITY
    TABLE IS NOT PROOF THE NODE IS THIS HAPPENING. A stale or promotional Event
    at an unpatterned address — a vanity URL, a ticket link, a partner site —
    passes the table test and is about something else entirely, and on a page
    whose own listing carries no structured markup it would be the lone node.
    So the page has to corroborate it: if the content this page prints never
    states the day that node claims, we have one witness we could not identify,
    and the row keeps its hole.

    The first half is the committed identity table, and the live run is why it
    exists. Requiring the node to name the followed permalink refused 29 of 40
    real pages, and the addresses they named say what they are:

        /backtotheranch     on  /event/back-to-the-ranch-the-lbj-bbq-returns-14329073
        /texarts_26_BB_ac   on  /event/boeing-boeing-14285657
        /events/269428      on  /event/prodigal-sun-14267156

    Those are the desk's own vanity and submitter links for the SAME happening,
    not other events — and none of them is an address the identity table calls a
    happening. A sidebar or related-events node is the opposite: it links to
    another happening's PERMALINK, which is exactly what the table matches, so
    it is still refused (evaluator, PR #235 r2 — that case stays closed).

    Anything else returns nothing, and the caller falls back to the page's
    printed text — where the plumbing and same-statement rules apply. That is
    the fail-closed direction: a hole rather than another event's day.
    """
    here = _address(url)
    bound = [ev for ev in events if here in _named(ev, url)]
    if bound:
        # A node naming THIS address has asserted whose page it is on, which is
        # the strongest thing markup can say — so here the name is asked only
        # not to CONTRADICT it. A node claiming to be about this permalink while
        # calling itself another show is a desk publishing two different answers
        # about one page, and there is no reading of that which dates this row
        # (evaluator, PR #235 r5, openai/attacker-smuggle). Silence is not
        # contradiction: a page with no heading, or a node with no name, still
        # binds on the address it named, because absence is not disagreement.
        return [ev for ev in bound if not _contradicts_this_page(ev, headings)]
    if len(events) != 1:
        return []
    named = _named_urls(events[0], url)
    if any(match_identity(one, patterns) is not None for one in named):
        # It names another happening. That is a different row's statement.
        return []
    if not _names_this_page(events[0], headings):
        # THE ADDRESS IT NAMES DOES NOT MATTER HERE; WHAT IT CALLS ITSELF DOES.
        # An unrecognised address is not the same as ours, and naming NO address
        # is not evidence either — a promotional Event node that omits `url` is
        # exactly as unidentified as one carrying a vanity link (evaluator, PR
        # #235 r4 second review, both openai seats: "a lone unaddressed JSON-LD
        # Event ... can be treated as this happening without checking
        # title/content/entity identity"). Unless the node says it is about the
        # thing this page says it is about, it is an unidentified witness, and
        # an unidentified witness dates nothing.
        return []
    return list(events)


def _scan_places(html: str) -> Tuple[List[str], List[str]]:
    """(places this page states about ITSELF, addresses its content links to).

    Both answers come from the SAME walk under the SAME plumbing rule, because
    the second is used to judge the first: two passes would be two definitions
    of what counts as this page's content, and they would drift.

    THE CARD BOUNDARY. A place is this page's only when it sits inside the
    section holding the page's own heading. That section IS the card, and HTML
    already names it — the sectioning elements the date path's scope rule
    reads. A page whose heading is in no section at all is one card, and every
    labelled place on it is that card's.

    This is the tie round 4 said the module could not build, recorded as R-112:
    a promotional or static block carrying venue markup and NO link was still
    read as this row's place, and both openai seats blocked on that residual
    (PR #235 r5). It needed no chrome-word list and no title match — only the
    observation that the page's heading has a section, and a block outside it
    is about something else.
    """
    scanner = _PlaceScanner()
    try:
        scanner.feed(html)
        scanner.close()
    except Exception as exc:  # noqa: BLE001 — a pathological page loses its place, not its row
        log.debug("place scan raised on a followed page: %s", exc)
        return [], []
    subject = _pick_subject(scanner.heading_marks, scanner.top_sections)
    out: List[str] = []
    for place, scope in zip(scanner.places, scanner.place_scopes):
        if not _inside_the_card(scope, subject):
            continue
        if place not in out:
            out.append(place)
    return out, list(scanner.links)


def _labelled_places(html: str) -> List[str]:
    return _scan_places(html)[0]


def _others_on_this_page(links: Sequence[str], url: str,
                         patterns: Sequence[IdentityPattern]) -> List[str]:
    """The OTHER happenings this page's content points at.

    A related-events card, a "you might also like" tile, a next-show promo: the
    thing that makes one another happening's is what the split ladder already
    uses to find it — a link to that happening's PERMALINK, which is exactly
    what the committed identity table matches (ONE-LIVE-ENTITY-SPLIT-LAW.md §2
    tier 2). Host knowledge stays in the data; this asks the table.
    """
    from urllib.parse import urljoin
    here = _address(url)
    out: List[str] = []
    for raw in links:
        target = (raw if raw.lower().startswith(("http://", "https://"))
                  else urljoin(url, raw))
        if _address(target) == here:
            continue
        if match_identity(target, patterns) is not None and target not in out:
            out.append(target)
    return out


def _clocks_printed(html: str) -> List[str]:
    """Every DISTINCT clock this text prints, in the order it prints them.

    Split out at r11 so the two callers cannot drift: `_clock_claim` wants the
    one clock a page settles on, and the cross-tier check wants all of them.
    Reading them twice is how the r3 instant keys and the r8 card days each
    went wrong — one walk, one answer, two questions asked of it.
    """
    found: List[str] = []
    for hit in _CLOCK_TOKEN_RE.findall(_visible(html)):
        token = " ".join(hit.split()).lower().replace(".", "")
        if token not in found:
            found.append(token)
    return found


def _clock_claim(html: str) -> Tuple[Optional[str], Optional[str]]:
    """The one clock this page prints, or None with the reason there isn't one.

    EXACTLY ONE distinct clock, or nothing: a page saying "Doors 7pm / Show 8pm"
    has not told us which one this happening starts at, and choosing either is
    the guess this module exists to refuse. Distinct is the test, so a page that
    prints the same time in its header and its footer still states one clock.
    """
    found = _clocks_printed(html)
    if not found:
        return None, None
    if len(found) > 1:
        return None, (f"page prints {len(found)} different clocks "
                      f"({', '.join(found[:4])}) — which one this happening "
                      f"starts at is not stated")
    return found[0], None


def field_read(html: str, *, url: str, as_of: Optional[_date] = None,
               patterns: Optional[Sequence[IdentityPattern]] = None
               ) -> FieldRead:
    """Read ONE event page into the fields it states about itself.

    The ladder is R-030's trust order, and it runs over THIS page's text only:

      1. the page's DATE — `same_page_dates()`: JSON-LD `startDate`,
         `<time datetime>`, ICS `DTSTART`, then visible prose, with a missing
         year supplied only by a weekday the page itself printed. Two distinct
         dates is a REFUSAL, not a choice.
      2. WHOSE date it is. A schema.org or ICS property says whose start it is
         and needs nothing more; anything else has to be stated by the page's
         CONTENT rather than its plumbing, or it is refused. A footer's "last
         updated" stamp is a date about the page, not a day about the show.
      3. the page's CLOCK — the date's own carrier when it states the whole
         instant; else the single clock in the SAME statement that gave the day.
         A clock anywhere else on the page is a different statement (a box
         office's hours, a byline) and does not join: the day stands at `date`
         precision, because refusing the time is not refusing the date. A clock
         with NO date leaves the row NULL, which is the ticket's second test and
         the reason this function cannot be written as "find a time".
      4. the page's PLACE — a schema.org Event's `location`, else an element the
         page labels as one, and again never one in the page's plumbing. One
         place, or a refusal.

    `as_of` is the day the page was fetched. Without it a weekday-only date
    ("Sat Sep 6") cannot be pinned to a year and stays a hole — R-030 turns
    weekday pinning OFF rather than assuming a year, and so does this.
    """
    if not isinstance(html, str) or not html.strip():
        return FieldRead(url=url, codes=("empty-body",),
                         refusals=("empty page body — nothing read "
                                   "(not 'nothing stated')",))
    # None means the COMMITTED table, so a caller that forgets to pass one gets
    # the strict answer rather than the permissive one: without patterns nothing
    # looks like another happening's address, and every sidebar node would speak
    # for the row it is sitting beside. Pass `()` to mean "no table" on purpose.
    if patterns is None:
        patterns = load_patterns()
    refusals: List[str] = []
    codes: List[str] = []

    def refuse(code: str, message: str) -> None:
        """One refusal, twice: a sentence for a person, a code for a counter."""
        refusals.append(message)
        codes.append(code)

    # CRLF -> LF before the date rule reads it. RFC 5545 ends every ICS line
    # with CRLF and R-030's DTSTART pattern is line-anchored, so a permalink
    # that answers with a calendar file would otherwise state no date at all.
    # This is a canonical FORM of the same text — it can only ever let the
    # committed rule see a line it already knows how to read, never change what
    # that rule makes of one.
    html = html.replace("\r\n", "\n")

    # The page's structured statement is read FIRST, because whether it speaks
    # for this happening decides both the date tier below and the place.
    try:
        ld_events = parse_jsonld(html)
    except Exception as exc:  # noqa: BLE001 — a pathological block must not lose the page
        ld_events = []
        refuse("jsonld-raised", f"JSON-LD parse raised ({exc}); the page's other "
                                f"statements were still read")
    # What the page calls ITSELF, read before the structured statement is
    # judged: the weak arm of `speaks_for` rests on it — a lone node at an
    # address the identity table cannot classify speaks for this page only when
    # it names the thing this page names.
    said = segments(html)
    headings = _headings(html)
    mine = speaks_for(ld_events, url, patterns, headings=headings)
    if ld_events and not mine:
        # Name the addresses. "A different address" is a verdict; WHICH address
        # is the evidence, and it is the difference between a sidebar event and
        # this desk addressing one happening two ways.
        named = sorted({_shown(a) for ev in ld_events for a in _named(ev, url)})
        refuse(
            "structured-not-bound",
            f"page publishes {len(ld_events)} schema.org event(s), and they name "
            f"{', '.join(named[:3]) or 'no address'} while this happening's "
            f"address is {_shown(_address(url))} — so none of them speaks for this "
            f"row, and none of them dates or places it"
            + ("" if len(ld_events) != 1 or not named
               or any(match_identity(a, patterns) is not None
                      for a in _named_urls(ld_events[0], url)) else
               f"; the address it names is one no committed pattern classifies, "
               f"and it calls itself "
               f"{str(ld_events[0].get('title') or ld_events[0].get('name') or '')!r} "
               f"while this page calls itself "
               f"{(headings[0] if headings else '')!r} — a node about something "
               f"else is not this row's"))

    # --- 1/2. when ---------------------------------------------------------
    when = when_precision = when_text = when_carrier = None
    page_clock, clock_refusal = _clock_claim(" ".join(said))

    # WHOSE DATE IT IS IS ASKED FIRST, AND CARDINALITY OVER THE ANSWER.
    # The other order — count every date on the document, then check scope —
    # refuses a page that states its day perfectly well in its content and
    # prints a "last updated" stamp in its footer: TWO dates, ambiguous, hole.
    # The first live run said exactly that, on 40 of 40 pages
    # (docs/evidence/2026-09-06_permalink-follow.md §9), which is how a rule
    # that is right about a page nobody publishes can still be wrong about
    # every page anybody does. Scope first, then count what is left: a
    # schema.org/ICS property says whose start it is, and printed text has to be
    # in the page's content rather than its plumbing.
    # WHICH NODE EMITTED THIS DATE. Asking only whether the page has SOME bound
    # node is not enough: a page with a bound node that states no start, plus a
    # sidebar node that does, hands the sidebar's day to this row under any
    # page-level test (evaluator, PR #235 r3, openai/attacker-smuggle —
    # reproduced as 2026-12-25T20:00 published for a row titled something else,
    # with no refusal recorded at all). The bind has to be PER HIT.
    bound_instants = {key for key in
                      (_instant_key(str(ev.get("start_time") or "")) for ev in mine)
                      if key is not None}

    def event_scoped(hit) -> bool:
        """Does this carrier say WHOSE start it is, for THIS happening?

        ICS does by construction: a calendar file served at this address is this
        happening's. A JSON-LD date does only when the node that emitted it is
        one that speaks for this row — matched on the INSTANT, because the
        parser normalises to UTC while the page keeps its own offset.
        """
        if hit.kind == "ics":
            return True
        return hit.kind == "jsonld" and _instant_key(hit.raw) in bound_instants

    def owned_by_this_happening(hit) -> bool:
        """Is this date a statement THIS HAPPENING'S OWN CARD makes?

        Two ways to be ours, and until r12 there was a third that was not.

        (1) The carrier says whose start it is (`event_scoped`) — a bound
        schema.org node, or an ICS file served at this address.

        (2) The carrier's own text SITS IN the card. That is positional, not
        semantic: `hit.raw` is the page's own characters, and the segment
        scanner keeps a `<time datetime>` attribute in the segment it appeared
        in, so a machine carrier inside this card is found here and one in the
        page's plumbing is not.

        A `<script>` payload can be NEITHER. It is refused explicitly rather
        than left to fail the text test by luck: the comment beside `stated`
        has claimed since r4 that a document-level carrier owns no statement,
        and prose claiming a mechanism the code does not have is exactly what
        r4's other finding was. Now it is a line, not a sentence.

        What stood here until r12 had a THIRD way to be ours — matching a
        hit's DAY against the days the card states — and that was the hole. A
        day is not a fingerprint. R-030 reports each date under the STRONGEST
        carrier that stated it, so a day the card prints AND an unrelated
        sidebar node also names comes back as ONE `jsonld` hit CARRYING THE
        SIDEBAR'S CLOCK; the day-match arm found that day in the card, called
        the hit ours, and let `_HAS_CLOCK_RE` publish another show's time onto
        this row — beside a `structured-not-bound` refusal saying none of the
        nodes dates this row (evaluator, PR #235 r12, both openai seats;
        reproduced as `2026-09-18T23:00:00`). A diagnostic and a behaviour
        disagreeing about one page is the `diagnostics-as-data` half of it.

        Removing that arm alone would have cost a real page, and the suite said
        so before any live run: `card_dates()` below is what it was doing that
        still has to happen.
        """
        if event_scoped(hit):
            return True
        if hit.kind == "jsonld":
            return False
        return any(hit.raw and hit.raw in s for s in said)

    def card_dates() -> List:
        """The dates this happening's own card states, read FROM THE CARD.

        The document-wide scan does not always find them. A page printing "Sat
        Sep 5 • 9:00PM" in its article beside a 31-cell calendar widget comes
        back from the whole-document scan with the widget's days and NOT its
        own — so the day-match arm removed above was doing two jobs, and only
        one of them was the defect. This is the other job, done positionally
        instead of by day: scan each of the card's own segments.

        Third time in this ticket that a document-wide scan had to become a
        per-card one (r8's card days, r10's clock comparison, this) — always
        for the same reason, that R-030 attributes a date to its strongest
        carrier and the card's own words go missing under it.

        Deduplicated by DAY: a card printing its date in a header and again in
        a body line has stated one date, not two, and cardinality below must
        not read that as ambiguity.
        """
        out, seen = [], set()
        for segment in said:
            for found in same_page_dates(segment, as_of=as_of):
                if found.date not in seen:
                    seen.add(found.date)
                    out.append(found)
        return out

    stated = same_page_dates(html, as_of=as_of)
    #: Set when the card and the bound markup name different days. It is not
    #: the same as "no structured hit": r8 EMPTIES both tiers on a
    #: contradiction because a desk disagreeing with itself has not stated a
    #: day, and the card fallback below must not then quietly re-supply the
    #: card's half of the disagreement as the answer (its own r8 test caught
    #: exactly that while this fallback was being written).
    contradicted = False
    # NEVER MIX TIERS (ONE-LIVE-ENTITY-SPLIT-LAW.md §2, the ladder's own rule,
    # here applied to fields rather than identities). A schema.org
    # `Event.startDate` or an ICS `DTSTART` states WHOSE start it is; printed
    # text does not. So when the page publishes one, it is the answer, and the
    # prose around it is not a competing claim to be counted against it —
    # otherwise an event page that declares its start perfectly well goes
    # dateless the moment it also prints a calendar widget beside it, which is
    # what the live run found on every page it opened. Within the tier,
    # cardinality still bites: two different `startDate`s refuse.
    # ICS stays event-scoped by construction: a calendar file served AT this
    # address is this happening's. JSON-LD only counts when a node on the page
    # speaks for this row (`speaks_for`) — otherwise its dates are just more
    # text on the page, and the plumbing/locality rules judge them like any
    # other, which for a `<script>` payload means owning no statement at all.
    structured = [hit for hit in stated if event_scoped(hit)]
    if structured:
        # THE TIER WINS, BUT NOT AGAINST THE CARD'S OWN WORDS.
        # "Never mix tiers" was written at r1 because counting prose against a
        # structured statement refused 40 of 40 live pages — a month grid in the
        # sidebar outvoted a node that declared the start perfectly well. What
        # has changed since is the CARD BOUNDARY (r5/r6): `said` is no longer
        # "text somewhere on the page", it is this happening's own card. So a
        # visible date there is not a competing tier, it is the SAME desk
        # contradicting itself about the same show, and a page that states two
        # different days about itself has not stated one (evaluator, PR #235 r8,
        # openai/attacker-smuggle).
        #
        # The commonest cause is a RUN: a JSON-LD `startDate` carrying the
        # opening night while the page displays the next performance
        # (`/event/prodigal-sun-14267156` states Sep 4 and displays Sep 6, both
        # about Prodigal Sun — §13b). Publishing the opening for a show whose
        # own page says otherwise puts a day in front of a reader that the desk
        # is visibly not claiming. Modelling runs is the next ticket's; holing
        # the day and COUNTING it is this one's, so that ticket opens with a
        # number instead of a hunch.
        # WHAT THE CARD PRINTS, READ FROM THE CARD. Not from the document-wide
        # scan filtered by carrier: R-030 reports each date under the STRONGEST
        # carrier that stated it, so a day the card prints AND the markup
        # states comes back as `jsonld` and disappears from a
        # "non-document-level kinds" filter. That is how the first cut of this
        # check refused a card listing "September 18, 19, 20" against markup
        # saying the 18th — the card's own 18th had been credited to the
        # script. Same class as the r3 instant keys: two computations of one
        # thing, compared.
        card_days = {found.date for segment in said
                     for found in same_page_dates(segment, as_of=as_of)}
        node_days = {hit.date for hit in structured}
        # A CONTRADICTION IS THE CARD NOT CARRYING THE NODE'S DAY — not the
        # card carrying MORE days than the node. The first live run of this
        # check read `card_days - node_days`, which fired on elaboration too:
        # a card listing four performances and the markup naming one of them is
        # the desk agreeing with itself at different resolutions, and refusing
        # it made the code's own sentence ("contradicting itself") untrue. That
        # is `diagnostics-as-data` — a reason that misdescribes what happened
        # sends the next reader at the wrong repair.
        if card_days and node_days - card_days:
            refuse(
                "card-contradicts-its-own-markup",
                f"this happening's own card states "
                f"{', '.join(sorted(d.isoformat() for d in card_days)[:3])} "
                f"while the page's structured data for it states "
                f"{', '.join(sorted(d.isoformat() for d in node_days)[:3])} — "
                f"the desk is contradicting itself about this show, so which "
                f"day it is on is not settled and the date stays NULL")
            structured = []
            stated = []
            contradicted = True
    if structured:
        stated = structured
    dates = [hit for hit in stated if owned_by_this_happening(hit)]
    if not structured and not contradicted:
        # A DAY THE CARD PRINTS IS THIS ROW'S EVEN WHEN THE DOCUMENT SCAN LOST
        # IT. Owned carriers come first — they are the stronger statement and
        # they carry the clock — and the card's own reading supplies only days
        # nothing owned has already stated. Not consulted at all when a bound
        # node speaks: that tier has already answered, and the card's words are
        # then a CHECK on it (`card-contradicts-its-own-markup`), never an
        # addition to it.
        owned_days = {hit.date for hit in dates}
        dates = dates + [hit for hit in card_dates()
                         if hit.date not in owned_days]
    in_plumbing = [hit for hit in stated
                   if hit.date not in {d.date for d in dates}]
    if len(dates) > 1:
        # RED_CLASSES: missing-cardinality-check. Three outcomes, three
        # behaviours — and "more than one" is not a longer list to pick from.
        refuse(
            "dates-ambiguous",
            f"page states {len(dates)} different dates "
            f"({', '.join(d.date.isoformat() for d in dates[:4])}) — which one "
            f"this happening is on is not stated, so the clock stays NULL")
    elif not dates:
        structured_orphans = [hit for hit in in_plumbing if hit.kind == "jsonld"]
        if structured_orphans and mine:
            refuse(
                "structured-hit-not-bound",
                f"a schema.org event on this page states "
                f"{', '.join(d.date.isoformat() for d in structured_orphans[:3])}, "
                f"and it is not one of the nodes that speaks for this happening — "
                f"another event's start is not this row's, so this stays NULL")
        elif in_plumbing:
            # There IS a date on the page and it is not this happening's: a
            # nav, a page header, a footer's "last updated" stamp (evaluator,
            # PR #235 r1) — or, since r5's card boundary, a related or
            # promotional block that is another happening's card. The counter
            # token stays as it was so its history is continuous; the SENTENCE
            # names both, because a reason that says "plumbing" about a promo
            # card sends the next reader at the wrong repair.
            refuse(
                "date-in-plumbing",
                f"the only date(s) on this page "
                f"({', '.join(d.date.isoformat() for d in in_plumbing[:3])}) are "
                f"stated outside anything this happening says about itself — in "
                f"the page's plumbing (a nav, a header, a footer) or in another "
                f"card beside its own — so this stays NULL")
        elif page_clock:
            # The founder's rule, verbatim: a clock with no date on that page
            # stays NULL. A time with no day is not a moment.
            refuse(
                "clock-without-date",
                f"page prints a clock ({page_clock}) and no date — a time with "
                f"no day is not a moment, so this stays NULL")
        else:
            refuse("no-date", "page states no date")
    else:
        hit = dates[0]
        # This date is already known to be this happening's — the scope question
        # was asked before the count. What is still needed is WHICH statement
        # carries it, because that statement is the only place a clock may come
        # from. A structured carrier belongs to no segment and gets none.
        if hit.kind in _DOCUMENT_LEVEL_KINDS:
            # A STRUCTURED CARRIER BELONGS TO NO SEGMENT, SO IT BORROWS NO
            # CLOCK. A `<script type="application/ld+json">` payload and an ICS
            # body are not sentences the page prints; matching them to a segment
            # BY DATE hands a structured `startDate: 2026-09-06` whatever clock
            # happens to sit in the one content block that also mentions Sep 6 —
            # "Box office Sep 6, 10:00AM" becomes a 10am show (evaluator, PR
            # #235 r4, openai/attacker-smuggle). The comment below has said this
            # since r1; the date-matching arm quietly did the opposite. A
            # structured node that states a day and no time has told us the day
            # and no time, and that is the honest output.
            owning = []
        else:
            owning = [s for s in said
                      if (hit.raw and hit.raw in s)
                      or hit.date in {d.date for d in same_page_dates(s, as_of=as_of)}]
        when_carrier, when_text = hit.kind, hit.raw
        if _HAS_CLOCK_RE.search(hit.raw or ""):
            # The carrier states the whole instant (an ISO startDate, a
            # DTSTART, a `<time datetime>` with a time). Normalised by
            # R-021's rule, so nothing enters here that the existing date
            # gate would refuse.
            iso, refusal = normalize_datetime_claim(hit.raw)
            if iso:
                when, when_precision = iso, "datetime"
                # AND THE NODE'S CLOCK MUST BE ONE THE CARD PRINTS.
                # r8 compared the two tiers' DAYS and stopped there, so a node
                # saying 19:30 on a card that visibly says 8:00PM published a
                # precise time the page's own statement contradicts (evaluator,
                # PR #235 r10, openai/attacker-smuggle). r10 then compared only
                # against `page_clock`, which is None the moment a card prints
                # TWO clocks — so "8:00PM; doors 7:00PM" beside a 19:30 node
                # walked straight through the guard that had just been added,
                # and the multi-clock diagnostic below is suppressed once a
                # carrier states the whole instant (r11, same seat).
                #
                # The rule that covers both is membership, not equality: the
                # card's clocks are the times this desk says are involved, and
                # the markup's job is to say WHICH of them starts the show. One
                # of them being the node's is the desk agreeing with itself at
                # two resolutions — the r8 lesson, applied to clocks. None of
                # them being the node's is the desk contradicting itself, and
                # then the agreed DAY stands while only the clock is holed,
                # which is the same shape as `clocks-ambiguous`.
                #
                # EACH PRINTED CLOCK IS ANCHORED TO THE NODE'S OWN DAY, not to
                # a date the card also has to print. r12 resolved every token
                # against the card's text, so a card saying "Show 8:00PM" and
                # no date produced NOTHING to compare — the resolver needs a
                # day to make an instant — and the node's 19:30 published as
                # settled under a page visibly saying eight o'clock (evaluator,
                # PR #235 r14, openai/absence-only). The comment beneath that
                # code said unreadable clocks are dropped, and conflated two
                # things: "8:00PM" is perfectly readable as a wall clock, it
                # simply has no day of its own. The day is scaffolding for the
                # parser here, never a claim — and the days are already known
                # to agree, because r8's check refuses and empties both tiers
                # before this point when they do not.
                #
                # Anchoring rather than writing a clock regex is deliberate:
                # `resolve_same_page_datetime` is the one place that knows what
                # a printed time means ("doors 7 pm", "10 pm", "19:30"), and a
                # second reader of the same thing is the class this ticket has
                # already paid for five times.
                said_text = " ".join(said)
                day = hit.date.isoformat()
                stated_wall = _wall_clock(when)
                verdicts = [v for v in (
                    _clock_agrees(token, stated_wall, day, as_of)
                    for token in _clocks_printed(said_text)) if v is not None]
                if verdicts and not any(verdicts):
                    shown = ", ".join(_clocks_printed(said_text)[:4])
                    refuse(
                        "card-contradicts-its-own-markup",
                        f"this happening's own card prints {shown} while "
                        f"its structured data states {when}, which is none of "
                        f"them — the desk is contradicting itself about the "
                        f"time, so the day stands and the clock stays a hole")
                    when, when_precision = hit.date.isoformat(), "date"
                    when_text = hit.raw
            else:
                refuse(
                    "carrier-refused",
                    f"page states {hit.raw!r} as its {hit.kind} date and the "
                    f"date rule refuses it ({(refusal or {}).get('reason')}) — "
                    f"kept as a hole rather than coerced")
        else:
            when, when_precision = hit.date.isoformat(), "date"
            # THE CLOCK MUST COME FROM THE STATEMENT THAT GAVE THE DAY.
            # "Sat Sep 5 - 9:00PM" is one sentence and combines; a day in
            # the listing and a "box office opens 10:00AM" two blocks away
            # are two statements, and joining them publishes an instant
            # neither one made. The day still stands — refusing the time is
            # not refusing the date.
            near, near_refusal = (_clock_claim(owning[0]) if len(owning) == 1
                                  else (None, None))
            if near:
                # The OWNING STATEMENT, not the page. R-030's `block_text` is
                # exactly this — "the event's own listing block", consulted
                # first — and handing it the whole document instead re-admits
                # every date the scope rule just excluded: a footer's "last
                # updated" stamp made the combine ambiguous and dropped a row
                # that had stated its day and its time in one sentence.
                iso, refusal, _evidence = resolve_same_page_datetime(
                    near, block_text=owning[0], as_of=as_of)
                if iso:
                    when, when_precision = iso, "datetime"
                    when_text = f"{hit.raw} {near}"
                else:
                    refuse(
                        "clock-unresolved",
                        f"page states {hit.date.isoformat()} and the clock "
                        f"{near!r} beside it does not settle against it "
                        f"({(refusal or {}).get('reason', 'unresolved')}) — "
                        f"the day stands, the time stays a hole")
            elif near_refusal:
                refuse("clocks-ambiguous",
                       near_refusal + " — the day stands without it")
            elif page_clock:
                refuse(
                    "clock-elsewhere",
                    f"page prints a clock ({page_clock}) somewhere other "
                    f"than in the statement that gave the day — two "
                    f"statements are not one, so the day stands and the "
                    f"time stays a hole")
            else:
                refuse("no-clock", "page states a day and no time")
    if (clock_refusal
            and when_precision != "datetime"
            and not any(clock_refusal in r for r in refusals)):
        # A REFUSAL CODE EXPLAINS A HOLE. THIS ROW HAS NO HOLE TO EXPLAIN.
        # The page-level clock scan is a last-resort reason for a MISSING time.
        # When a structured carrier already stated the whole instant, the prose
        # elsewhere on the page disagreeing with itself is not this row's
        # problem — and recording it anyway made the live table claim 7 pages
        # (17% of those opened) needed a clock repair when their rows were
        # already complete. A diagnostic that overstates the work is not a
        # smaller lie than one that hides it: the next ticket is chosen by
        # whichever count is largest (Law §9.3).
        refuse("clocks-ambiguous", clock_refusal)

    # --- 3. place ----------------------------------------------------------
    place_text = place_carrier = None
    ld_places: List[str] = []
    for ev in mine:
        # NOT `stated` — that name holds this page's date carriers, read above.
        # A loop variable that shadows the read it depends on is how an earlier
        # round of this ticket produced an AttributeError at the report edge.
        venue = ev.get("venue_name") or ev.get("venue_address") or ev.get("venue_city")
        venue = " ".join((venue or "").split())
        if venue and venue not in ld_places:
            ld_places.append(venue)
    if len(ld_places) == 1:
        # THE SAME CROSS-TIER CHECK THE DATE NOW MAKES. A bound node's venue is
        # the desk speaking in machine form; the card's labelled venue is the
        # desk speaking to a reader. When they name different places the desk is
        # contradicting itself about this show, and neither is settled
        # (evaluator, PR #235 r8, openai/attacker-smuggle).
        #
        # ASKED AS CONTAINMENT, NOT AS IDENTITY, AND THAT IS THE WHOLE POINT.
        # This shared `_same_name` with the identity check until r15, when the
        # live run showed the cost: r13 tightened `_same_name` so a lone token
        # must OPEN the longer name, which is right for identity (a false YES
        # binds another happening's node) and wrong here (a false NO invents a
        # contradiction and holes a place we had). `/event/boeing-boeing`'s card
        # labels "Venue Details TexARTS 1110 S RR 620, …" against a node saying
        # "TexARTS": the block CONTAINS the venue, it simply does not start with
        # it, and the run refused the place for it.
        #
        # This repo already wrote that lesson down — `destructive-normalization`
        # r9: "When one helper serves two callers, check whether their failure
        # modes point the same way; if they do not, they share a NAME rather
        # than a helper. Split on the QUESTION, not on the data." The questions
        # here are different: identity asks "are these the same name", a
        # labelled block asks "does this text NAME this place".
        on_the_card, _links = _scan_places(html)
        clashing = [one for one in on_the_card
                    if not _names_within(one, ld_places[0])]
        if clashing:
            refuse(
                "card-contradicts-its-own-markup",
                f"this happening's own card labels "
                f"{'; '.join(clashing[:2])} while the page's structured data "
                f"for it states {ld_places[0]} — the desk is contradicting "
                f"itself about where this show is, so the place stays NULL")
        else:
            place_text, place_carrier = ld_places[0], "jsonld"
    elif len(ld_places) > 1:
        refuse(
            "places-ambiguous",
            f"page publishes {len(ld_places)} schema.org events naming "
            f"different places ({'; '.join(ld_places[:3])}) — which one this "
            f"happening is at is not stated")
    else:
        # The UNBOUND fallback, and everything it now has to survive. A place
        # here is one this page states INSIDE the section holding its own
        # heading (`_scan_places`), on a page whose content does not also point
        # at other happenings. Round 4 built the second half from the split
        # ladder's own discriminator; round 5 built the first, which is the
        # residual R-112 recorded and both openai seats then blocked on — and
        # they were right on this repo's own rule, that a RECORD row is not a
        # safe harbour when the bound it states does not cover the harm it
        # names (RED_CLASSES: deferred-trust-work).
        labelled, links = _scan_places(html)
        others = _others_on_this_page(links, url, patterns)
        if len(labelled) == 1 and others:
            # A structured node that speaks for this row is bound and read
            # above; this fallback has no way to say whose venue it found. When
            # the page's content also points at other happenings, one labelled
            # venue is not evidence — it is a coin flip between this row and the
            # card beside it, and the hole is the honest answer (evaluator, PR
            # #235 r4 second pass, openai/attacker-smuggle).
            refuse(
                "place-among-other-happenings",
                f"page labels one place ({labelled[0]}) and its content also "
                f"links to {len(others)} other happening(s) "
                f"({', '.join(_shown(_address(o)) for o in others[:3])}) — nothing "
                f"on the page says the venue is this one's rather than theirs")
        elif len(labelled) == 1:
            place_text, place_carrier = labelled[0], "labelled"
        elif len(labelled) > 1:
            refuse(
                "places-ambiguous",
                f"page labels {len(labelled)} different places "
                f"({'; '.join(labelled[:3])}) — which one this happening is at "
                f"is not stated")
        else:
            refuse("no-place", "page labels no place")
    return FieldRead(
        url=url, when=when, when_precision=when_precision, when_text=when_text,
        when_carrier=when_carrier, place_text=place_text,
        place_carrier=place_carrier, refusals=tuple(refusals),
        codes=tuple(codes),
    )


# --------------------------------------------------------------------------
# Following, bounded
# --------------------------------------------------------------------------

@dataclass
class FollowResult:
    """One field tick: which pages were opened, what they filled, what they did
    not, and what nobody asked. The last of those is why `not_followed` exists.
    """

    door_id: str
    rows: List[Happening] = field(default_factory=list)
    budget: int = DEFAULT_BUDGET
    eligible: int = 0             # rows whose own address is a followable permalink
    fetched: int = 0              # pages actually opened (never more than budget)
    dated: int = 0                # rows this tick moved off a NULL clock
    placed: int = 0               # rows this tick gave a place
    walled: int = 0               # 401/402/403/407/429 or a sign-in redirect
    unread: int = 0               # opened and not readable for any other reason
    stated_nothing: int = 0       # read, and the page settled no field we lacked
    not_followed: int = 0         # eligible rows the budget did not reach
    skipped_off_origin: int = 0   # permalink on another host — not opened here
    skipped_no_identity: int = 0  # no committed pattern says this URL is one happening
    skipped_complete: int = 0     # row already carried both fields
    #: (url, reason) for every page that could not be read. A wall is a QUEUE
    #: entry: the door is asked for a claim, never retried and never deleted.
    queued: List[Tuple[str, str]] = field(default_factory=list)
    reads: List[FieldRead] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def budget_spent(self) -> bool:
        return self.not_followed > 0

    @property
    def dated_n(self) -> int:
        """Rows carrying a clock AFTER this tick, from either page."""
        return sum(1 for r in self.rows if r.when)

    @property
    def still_null_n(self) -> int:
        """Rows with no stated date after this tick. NOT a statement about the
        desks: it holds rows whose page said no date, rows whose page was
        walled, and rows nobody asked — see `not_followed`."""
        return sum(1 for r in self.rows if not r.when)


def followable(row: Happening, *, patterns: Sequence[IdentityPattern]
               ) -> Tuple[bool, Optional[str]]:
    """May this row's own address be opened by this tick? `(yes, refusal)`.

    Two gates, both from the founder's ticket, and both about the URL rather
    than about the happening: the address must be one a COMMITTED pattern calls
    a single happening, and it must be on the same origin as the page that
    printed it. Neither is a test a row has to pass to exist.
    """
    url = (row.listing_url or "").strip()
    if not url:
        return False, "row states no address of its own"
    if match_identity(url, patterns) is None:
        return False, ("no committed identity pattern says this address is one "
                       "happening")
    if _host(url) != _host(row.source_url):
        return False, (f"address is on {_host(url)}, the list was read from "
                       f"{_host(row.source_url)} — off-origin, not opened here")
    return True, None


def apply_read(row: Happening, read: FieldRead) -> Tuple[Happening, List[str]]:
    """Fill this row's HOLES from what its own page stated. Never an overwrite.

    `when`, `when_precision` and `when_text` move as ONE unit: after this call
    the row's date text is the words that justify its instant, rather than a
    sentence from a different page sitting beside a number from this one
    (RED_CLASSES: partial-write-whole-row). A row that already carried a clock
    keeps every one of the three, because the list page's statement is not this
    page's to correct — that is `worker/listing_update.py`'s reviewed seam.
    """
    patch: Dict[str, object] = {}
    filled: List[str] = []
    if row.when is None and read.when:
        patch.update(when=read.when, when_precision=read.when_precision,
                     when_text=read.when_text or row.when_text)
        filled.append("when")
    if row.place_text is None and read.place_text:
        patch["place_text"] = read.place_text
        filled.append("place_text")
    patch["detail_url"] = read.url
    patch["filled_from_detail"] = tuple(filled)
    return replace(row, **patch), filled


def follow(rows: Sequence[Happening], fetch: Callable[[str], PageFetch], *,
           door_id: str = "", budget: int = DEFAULT_BUDGET,
           as_of: Optional[_date] = None,
           patterns: Optional[Sequence[IdentityPattern]] = None) -> FollowResult:
    """Open each happening's own page, bounded, and fill the holes it states.

    Every page is opened AT MOST ONCE — there is no retry anywhere in this
    function, by construction rather than by policy: a wall, an error and an
    unreadable body all `continue` to the next row. Rows sharing one address
    share one fetch.

    `fetch` is injected (`worker.locale.desk_walk.PageFetch`), so the whole tick
    is testable against committed pages and a live run differs only in the
    fetcher it is handed. `patterns` defaults to the committed identity table.
    """
    if not callable(fetch):
        raise DeskFollowError("follow() needs a callable fetch(url) -> PageFetch")
    if not isinstance(budget, int) or budget < 0:
        raise DeskFollowError(
            f"budget must be a non-negative int, got {budget!r}")
    if patterns is None:
        patterns = load_patterns()

    result = FollowResult(door_id=door_id, budget=budget, rows=list(rows))
    plan: List[Tuple[int, str]] = []
    for index, row in enumerate(result.rows):
        ok, refusal = followable(row, patterns=patterns)
        if not ok:
            if refusal and "off-origin" in refusal:
                result.skipped_off_origin += 1
            elif refusal and "no committed identity pattern" in refusal:
                result.skipped_no_identity += 1
            continue
        result.eligible += 1
        if row.when is not None and row.place_text is not None:
            # Nothing to fill. Spending a page on it would spend the budget on
            # a row that is already answered while another row keeps its hole.
            result.skipped_complete += 1
            continue
        plan.append((index, row.listing_url.strip()))

    by_url: Dict[str, List[int]] = {}
    for index, url in plan:
        by_url.setdefault(url, []).append(index)

    for url, indexes in by_url.items():
        if result.fetched >= budget:
            result.not_followed += len(indexes)
            continue
        result.fetched += 1
        try:
            page = fetch(url)
        except Exception as exc:  # noqa: BLE001 — a fetcher blowing up is one page's news
            result.unread += 1
            result.queued.append((url, f"fetch raised: {type(exc).__name__}: {exc}"[:300]))
            continue
        if not isinstance(page, PageFetch):
            raise DeskFollowError(
                f"fetch({url!r}) returned {type(page).__name__}; follow() needs a "
                f"PageFetch so status, body and the landing URL are all classifiable")

        verdict = demote_on_response(
            DECLARED_PUBLIC, status=page.status, final_url=page.final_url,
            error=page.error)
        if verdict.is_closed_door:
            # We knocked once. The happening keeps every field it had, the door
            # goes to the claim queue, and nothing is retried.
            result.walled += 1
            result.queued.append((url, f"class D on contact — {verdict.reason}"))
            continue
        if page.error:
            result.unread += 1
            result.walled += 1 if page.walled else 0
            result.queued.append((url, f"fetch failed: {page.error}"[:300]))
            continue
        if page.status is not None and page.status >= 400:
            result.unread += 1
            result.queued.append((
                url, f"HTTP {page.status} — triage, not 'this happening has no date'"))
            continue
        landed = page.landed_url
        if not same_identity(landed, url):
            # THE PAGE THAT ANSWERS MUST BE THE PAGE WE ASKED FOR. Same host is
            # not enough: a deleted or soft-redirected permalink lands on the
            # desk's own index, its search page, or ANOTHER event — all on the
            # same origin — and reading fields off that publishes a stranger's
            # date and venue onto this happening (evaluator, PR #235 r2,
            # openai/absence-only; reproduced as `/whats-on` supplying
            # 2026-09-30 at "Front Desk"). The identity gate that chose this URL
            # has to hold after the redirect too, or it only ever guarded the
            # request.
            result.unread += 1
            result.queued.append((
                url, f"redirected to {landed} — a different address is a "
                     f"different happening (or none), so it is not read"))
            continue
        if not page.body or not page.body.strip():
            result.unread += 1
            result.queued.append((url, "empty body — nothing read (not 'nothing stated')"))
            continue

        # THE ROW'S OWN ADDRESS IS THE IDENTITY, not wherever the desk sent us.
        # `same_identity` above has already established that `landed` IS this
        # happening's page, so what is left to decide inside is which node
        # speaks for THIS ROW — and the row's address is the one the identity
        # ladder chose. Passing `landed` was harmless while `_address` dropped
        # the query and became a coverage loss the moment r11 stopped: a desk
        # redirecting to `?ref=cal` made every node naming the canonical
        # address stop matching (gemini/spec-vs-contract NIT, r12; fail-closed,
        # a hole rather than a wrong field, but a hole this desk need not have).
        # Nothing else in `field_read` prefers `landed`: `same_identity` pins
        # host and path, so relative links resolve identically against either.
        read = field_read(page.body, url=url, as_of=as_of,
                          patterns=patterns)
        result.reads.append(read)
        moved = False
        for index in indexes:
            patched, filled = apply_read(result.rows[index], read)
            result.rows[index] = patched
            if "when" in filled:
                result.dated += 1
                moved = True
            if "place_text" in filled:
                result.placed += 1
                moved = True
        if not moved:
            result.stated_nothing += 1

    if result.not_followed:
        result.notes.append(
            f"{result.not_followed} happening(s) with a followable address were "
            f"NOT opened: the {budget}-page budget for this tick was spent. "
            f"Their clocks are UNASKED, not absent — this run's dated count is a "
            f"floor")
    if result.walled:
        result.notes.append(
            f"{result.walled} page(s) answered a wall (401/402/403/407/429 or a "
            f"sign-in redirect). Knocked once, queued for a claim, not retried; "
            f"every one of those happenings is kept exactly as the list stated it")
    if result.skipped_off_origin:
        result.notes.append(
            f"{result.skipped_off_origin} row(s) carry an address on another "
            f"host and were not opened here (on-origin only, this ticket). The "
            f"address stays on the row as the next step it already was — no row "
            f"is dropped and no door is demoted by this")
    return result
