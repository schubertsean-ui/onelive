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
from datetime import date as _date
from html.parser import HTMLParser
from typing import Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from worker.datetime_normalize import normalize_datetime_claim
from worker.importers.structured_feed import parse_jsonld
from worker.locale.desk_read import (
    FURNITURE_TAGS,
    PLACEISH_RE,
    SCOPED_FURNITURE_TAGS,
    SECTIONING_TAGS,
    Happening,
)
from worker.locale.desk_walk import DECLARED_PUBLIC, PageFetch
from worker.locale.identity_patterns import (
    IdentityPattern,
    load_patterns,
    match as match_identity,
)
from worker.same_page_dates import resolve_same_page_datetime, same_page_dates
from worker.sourcing.source_class import demote_on_response

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

#: Elements whose text is never a place (or anything else printed).
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
        self._parts: List[str] = []
        self._skip = 0
        self._furniture = 0
        self._open: List[str] = []

    def _flush(self) -> None:
        text = " ".join(" ".join(self._parts).split())
        if text:
            self.segments.append(text)
        self._parts = []

    def _in_sectioning(self) -> bool:
        return any(tag in SECTIONING_TAGS for tag, _ in self._open)

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
        self._open.append((tag, furniture))
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
        if tag in _BLOCK_TAGS:
            self._flush()
        if any(open_tag == tag for open_tag, _ in self._open):
            while self._open:
                closed, opened_furniture = self._open.pop()
                if opened_furniture:
                    self._parts = []   # anything buffered in plumbing is dropped
                    self._furniture = max(0, self._furniture - 1)
                if closed == tag:
                    break

    def handle_data(self, data):
        if not self._skip and not self._furniture:
            self._parts.append(data)

    def close(self):
        super().close()
        self._flush()


def segments(html: str) -> List[str]:
    """The page's statements, plumbing removed. Empty when nothing can be read."""
    scanner = _SegmentScanner()
    try:
        scanner.feed(html or "")
        scanner.close()
    except Exception as exc:  # noqa: BLE001 — a pathological page states nothing, it never crashes
        log.debug("segment scan raised on a followed page: %s", exc)
        return []
    return scanner.segments


def _host(url: Optional[str]) -> str:
    host = (urlsplit(url or "").hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _address(url: Optional[str]) -> Tuple[str, str]:
    """The (host, path) a URL names, as one address.

    The QUERY is dropped and the fragment with it, because a desk that appends
    its own tracking parameter on a redirect (`?ref=calendar`) has sent us to
    the same page — and a trailing slash is the same address too, which is the
    rule `desk_read._identity_of` already applies on the way in.
    """
    parts = urlsplit(url or "")
    path = (parts.path or "/").rstrip("/") or "/"
    return _host(url), path


def same_identity(landed: Optional[str], asked: Optional[str]) -> bool:
    """True when the page that answered is the page we asked for."""
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
        self._depth = 0
        self._parts: List[str] = []
        self._skip = 0
        self._furniture = 0
        self._open: List[str] = []

    @staticmethod
    def _labelled(attrs: Dict[str, str]) -> bool:
        if (attrs.get("itemprop") or "").strip().lower() in _PLACE_ITEMPROPS:
            return True
        return any(PLACEISH_RE.search(attrs.get(name) or "")
                   for name in ("class", "id"))

    def _in_sectioning(self) -> bool:
        return any(tag in SECTIONING_TAGS for tag, _ in self._open)

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
        self._open.append((tag, furniture))
        if self._depth:
            self._depth += 1
            return
        if self._furniture:
            return
        flat = {k.lower(): (v or "") for k, v in attrs}
        if self._labelled(flat):
            self._depth = 1
            self._parts = []
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
        if any(open_tag == tag for open_tag, _ in self._open):
            while self._open:
                closed, opened_furniture = self._open.pop()
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
            self._parts = []

    def handle_data(self, data):
        if self._depth and not self._skip:
            self._parts.append(data)


def _addresses_named(event: Dict[str, object]) -> set:
    """Every address a structured node names for ITSELF (`url`, `@id`/`uid`)."""
    out = set()
    for key in ("url", "uid"):
        raw = str(event.get(key) or "").strip()
        if raw.lower().startswith(("http://", "https://")):
            out.add(_address(raw))
    return out


def speaks_for(events: Sequence[Dict[str, object]], url: str,
               patterns: Sequence[IdentityPattern] = ()
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
      * or it is the page's only Event node and the address it names is not
        ANOTHER HAPPENING'S. A node naming no address at all is a permalink page
        publishing an Event about itself; so is one naming an address that no
        committed identity pattern calls a happening.

    That last arm is the committed identity table doing the work, and the live
    run is why it exists. Requiring the node to name the followed permalink
    refused 29 of 40 real pages, and the addresses they named say what they are:

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
    bound = [ev for ev in events if here in _addresses_named(ev)]
    if bound:
        return bound
    if len(events) != 1:
        return []
    named = {raw for raw in (str(events[0].get(k) or "").strip()
                             for k in ("url", "uid"))
             if raw.lower().startswith(("http://", "https://"))}
    if any(match_identity(one, patterns) is not None for one in named):
        # It names another happening. That is a different row's statement.
        return []
    return list(events)


def _labelled_places(html: str) -> List[str]:
    scanner = _PlaceScanner()
    try:
        scanner.feed(html)
        scanner.close()
    except Exception as exc:  # noqa: BLE001 — a pathological page loses its place, not its row
        log.debug("place scan raised on a followed page: %s", exc)
        return []
    out: List[str] = []
    for place in scanner.places:
        if place not in out:
            out.append(place)
    return out


def _clock_claim(html: str) -> Tuple[Optional[str], Optional[str]]:
    """The one clock this page prints, or None with the reason there isn't one.

    EXACTLY ONE distinct clock, or nothing: a page saying "Doors 7pm / Show 8pm"
    has not told us which one this happening starts at, and choosing either is
    the guess this module exists to refuse. Distinct is the test, so a page that
    prints the same time in its header and its footer still states one clock.
    """
    found: List[str] = []
    for hit in _CLOCK_TOKEN_RE.findall(_visible(html)):
        token = " ".join(hit.split()).lower().replace(".", "")
        if token not in found:
            found.append(token)
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
    mine = speaks_for(ld_events, url, patterns)
    if ld_events and not mine:
        # Name the addresses. "A different address" is a verdict; WHICH address
        # is the evidence, and it is the difference between a sidebar event and
        # this desk addressing one happening two ways.
        named = sorted({a for ev in ld_events for _, a in _addresses_named(ev)})
        refuse(
            "structured-not-bound",
            f"page publishes {len(ld_events)} schema.org event(s), and they name "
            f"{', '.join(named[:3]) or 'no address'} while this happening's "
            f"address is {_address(url)[1]} — so none of them speaks for this "
            f"row, and none of them dates or places it")

    # --- 1/2. when ---------------------------------------------------------
    when = when_precision = when_text = when_carrier = None
    said = segments(html)
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
    def event_scoped(hit) -> bool:
        """Does this carrier say WHOSE start it is, for THIS happening?

        ICS does by construction: a calendar file served at this address is this
        happening's. JSON-LD does only when a node on the page speaks for this
        row — an unbound node is a statement about some OTHER event, and the one
        thing it must not get is the exemption meant for statements about this
        one (evaluator, PR #235 r2).
        """
        return hit.kind == "ics" or (hit.kind == "jsonld" and bool(mine))

    def owned_by_this_happening(hit) -> bool:
        if event_scoped(hit):
            return True
        return any((hit.raw and hit.raw in s)
                   or hit.date in {d.date for d in same_page_dates(s, as_of=as_of)}
                   for s in said)

    stated = same_page_dates(html, as_of=as_of)
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
        stated = structured
    dates = [hit for hit in stated if owned_by_this_happening(hit)]
    in_plumbing = [hit for hit in stated if hit not in dates]
    if len(dates) > 1:
        # RED_CLASSES: missing-cardinality-check. Three outcomes, three
        # behaviours — and "more than one" is not a longer list to pick from.
        refuse(
            "dates-ambiguous",
            f"page states {len(dates)} different dates "
            f"({', '.join(d.date.isoformat() for d in dates[:4])}) — which one "
            f"this happening is on is not stated, so the clock stays NULL")
    elif not dates:
        if in_plumbing:
            # There IS a date on the page and it is not this happening's: a nav,
            # a page header, a footer's "last updated" stamp. A page timestamp
            # is not a show's day (evaluator, PR #235, openai/absence-only).
            refuse(
                "date-in-plumbing",
                f"the only date(s) on this page "
                f"({', '.join(d.date.isoformat() for d in in_plumbing[:3])}) are "
                f"stated in its own plumbing — a nav, a page header or footer — "
                f"not in anything this happening says about itself, so this "
                f"stays NULL")
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
    if clock_refusal and not any(clock_refusal in r for r in refusals):
        refuse("clocks-ambiguous", clock_refusal)

    # --- 3. place ----------------------------------------------------------
    place_text = place_carrier = None
    ld_places: List[str] = []
    for ev in mine:
        stated = ev.get("venue_name") or ev.get("venue_address") or ev.get("venue_city")
        stated = " ".join((stated or "").split())
        if stated and stated not in ld_places:
            ld_places.append(stated)
    if len(ld_places) == 1:
        place_text, place_carrier = ld_places[0], "jsonld"
    elif len(ld_places) > 1:
        refuse(
            "places-ambiguous",
            f"page publishes {len(ld_places)} schema.org events naming "
            f"different places ({'; '.join(ld_places[:3])}) — which one this "
            f"happening is at is not stated")
    else:
        labelled = _labelled_places(html)
        if len(labelled) == 1:
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

        read = field_read(page.body, url=landed, as_of=as_of,
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
