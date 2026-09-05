"""union(desks) — two desks become ONE happening table, deduped, in our model.

Founder, this session's ticket: "1Live holds the UNION, deduped, in OUR model,
then goes BROADER"; the de-dup rule is his, verbatim: "same night + same
place-text + same title-or-performer -> one row, many vias. No identity
service. No invented dates."

Every clause of that rule is implemented literally here, and the three refusals
inside it are what the module is shaped around:

  * SAME NIGHT. A night exists only when the desk STATED a machine date
    (`Happening.when`). Prose the desk printed ("this Saturday", "Ongoing") is
    carried through untouched and yields NO night — such a row can never join
    another desk's row, because joining them would assert a date nobody stated
    (ONE-LIVE-TRUST.md: a missing minute is not a missing night). This is why
    the module reads `when` and never `when_text`.

  * NO IDENTITY SERVICE. The match is one equality test on a composed key —
    night, place, name — computed by stated text rules that fit on a page. No
    scoring, no threshold, no fuzzy distance, no model, no registry of venues
    or artists. Two rows either state the same three things or they do not.

  * NO ROW IS EVER DROPPED. A row that cannot form a union key (no night, no
    place text, no title) still appears in the table under a DESK-LOCAL key. It
    is single-source and stays single-source. ONE-LIVE-COVERAGE-LAW.md: "Do not
    drop single-source rows" — a de-dup that quietly loses the unmatchable rows
    would be the exact failure the union is supposed to prevent.

WHY A TIMEZONE IS REQUIRED, and why it comes from the pack. Desks state the
same instant in different FORMS: the Chronicle fixture's opening listing is
`2026-09-12T01:00:00Z` for a show its own page prints as "Fri., Sept. 11, 8pm".
Slicing ten characters off that string calls it a September 12th night — wrong
against the desk's own words, and wrong in a way that also splits two desks
that agree. So the night is the calendar date of the stated instant PROJECTED
into the locale's timezone, and the timezone is pack DATA
(`locale.timezone`), never a constant in code: `worker.locale.pack` exists
precisely so that no home town is hardcoded. A pack that states no timezone
gets a `DeskUnionError`, not a guess.

WHAT THIS DOES NOT DO. It computes no rollover for late sets: a 12:30am listing
is keyed to its own calendar date, not to the evening before. Rolling it back
would be a rule the founder has not set, and it would silently move rows
between nights. The limit is printed with the tables rather than hidden.

Pure: stdlib only (plus this repo's own reader types), no network, no DB, no
clock, no model. It is handed walks somebody else fetched, and it writes
nothing.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from worker.locale.desk_read import Happening
from worker.locale.desk_walk import DeskWalk

#: Key bases, printed on every row so a reader can never mistake a row that
#: COULD have matched for one that was never eligible.
BASIS_UNION = "night+place+title"
BASIS_PERFORMER = "night+place+performer"
BASIS_LOCAL = "desk-local"

#: Why a row could not carry a union key. Printed verbatim in the table.
NO_NIGHT = "no night stated"
NO_PLACE = "no place text"
NO_TITLE = "no title"

#: Separators after which a desk names the VENUE. Stripped only when what
#: follows is this row's own place text — so "Fixture Quartet at the Shape
#: Hall" and "Fixture Quartet" are one performer at Shape Hall, while
#: "Breakfast at Tiffany's" at the Marquee Room keeps its whole title.
_VENUE_SEPARATORS = (" at ", " @ ")

#: Separators after which a desk names SUPPORT acts. One desk lists the whole
#: bill, the other prints the headliner; the head of the split is the performer
#: in every one of these forms. `presents` is deliberately absent: it runs the
#: other way ("Venue presents Artist"), so stripping its tail would keep the
#: promoter and throw away the act.
_SUPPORT_SEPARATORS = (" w/ ", " with ", " featuring ", " feat. ", " feat ",
                       " ft. ", " ft ")

_WS_RE = re.compile(r"\s+")
#: Deleted rather than spaced: an apostrophe sits INSIDE a word.
_APOSTROPHE_RE = re.compile(r"['\u2018\u2019\u02bc]")
_LEADING_THE_RE = re.compile(r"^the ")
_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class DeskUnionError(ValueError):
    """The union cannot be computed as asked. Always raised — never downgraded
    to a shorter table, because a union that quietly drops a desk reads exactly
    like a union of desks that had nothing on.
    """


# --------------------------------------------------------------------------
# The three key parts
# --------------------------------------------------------------------------

def _soft(value: Optional[str]) -> str:
    """Lowercase, whitespace-collapsed. Punctuation SURVIVES, because the
    separators that name a venue or a support act ("w/", "feat.") are
    punctuation.
    """
    return _WS_RE.sub(" ", (value or "").strip().lower())


def _fold(value: str) -> str:
    """Drop the diacritics from LATIN letters and leave every other script's
    marks alone.

    A normaliser that deletes what it cannot represent is the repo's
    `destructive-normalization` red class: `[^0-9a-z] -> space` turns "Café"
    into "caf" while "Cafe" stays "cafe" (two spellings of one venue that stop
    comparing equal), and it reduces "Кино Night" to "night". So a character is
    decomposed and its combining marks are dropped ONLY when what it decomposes
    onto is a plain ASCII letter or digit — the case where dropping the mark
    recovers the other desk's spelling.

    Everything else is kept whole, marks included, on purpose. In Devanagari and
    several other scripts a combining mark carries a vowel or changes the
    consonant, so folding it away would merge two DIFFERENT words — and in this
    module a wrong merge means two happenings printed as one, which is the one
    direction that loses a row.
    """
    out = []
    # Compose first, so a desk that spells its accent as two code points
    # ("e" + U+0301) and one that spells it as a single "é" reach the same
    # character before anything is dropped.
    for ch in unicodedata.normalize("NFC", value):
        decomposed = unicodedata.normalize("NFKD", ch)
        base = decomposed[0]
        if base.isascii() and base.isalnum():
            out.append("".join(c for c in decomposed if not unicodedata.combining(c)))
        else:
            out.append(ch)
    return "".join(out)


def _keep(ch: str) -> bool:
    """Letters, digits and combining marks survive; everything else becomes a
    space. `str.isalnum` is Unicode-aware, so Cyrillic, Greek and CJK titles
    keep their words instead of being emptied down to whatever ASCII they
    happened to carry.
    """
    return ch.isalnum() or unicodedata.category(ch).startswith("M")


def _hard(value: Optional[str]) -> str:
    """The comparison form: lowercase, Latin diacritics folded, punctuation
    flattened, whitespace collapsed, a leading article dropped. "The Fixture
    Room", "Fixture Room!" and "Fixture Rôom" are one place; "Fixture Room" and
    "Fixture Annex" are two.

    Apostrophes are DELETED while other punctuation becomes a space, because
    the two marks do opposite jobs inside a name: one desk writes "Curra's" and
    another "Curras" (same word), while one writes "Pop-Up" and another "Pop
    Up" (same two words). Flattening both the same way would split one of those
    pairs.
    """
    out = _APOSTROPHE_RE.sub("", _fold(_soft(value)))
    out = "".join(ch if _keep(ch) else " " for ch in out)
    out = _WS_RE.sub(" ", out).strip()
    return _LEADING_THE_RE.sub("", out)


def local_night(when: Optional[str], timezone) -> Tuple[Optional[str], Optional[str]]:
    """The calendar date of a stated instant, in the locale's timezone.

    Returns `(night, note)`. `night` is None whenever the desk stated no machine
    date or stated one this module will not vouch for; `note` says which, so a
    hole is always explained rather than blank.

    Three shapes, three answers:
      * a bare date (`2026-09-13`) is already a calendar date — used as-is, no
        projection, because there is no instant to project.
      * an instant carrying an offset or `Z` is projected into `timezone`. This
        is the only place a stated time is transformed, and it changes no fact:
        the same instant, read on the locale's clock.
      * an instant with no offset is a local wall time by construction — its
        own date is the night, unprojected.
    """
    if not when or not when.strip():
        return None, NO_NIGHT
    text = when.strip()
    if _DATE_ONLY_RE.match(text):
        return text, None
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        # A shape we will not interpret. Reported, never coerced.
        return None, f"unparsed date {text!r}"
    if moment.tzinfo is None:
        return moment.date().isoformat(), None
    return moment.astimezone(timezone).date().isoformat(), None


def place_key(place_text: Optional[str]) -> str:
    """The comparison form of the desk's own place text. Empty when the desk
    printed no place — which makes the row unmatchable, never invisible.
    """
    return _hard(place_text)


def performer_key(title: str, place: str) -> str:
    """The founder's "title-or-performer", as a text rule.

    The performer is the title with (a) a trailing "at <this row's own venue>"
    removed and (b) any support-act tail removed. Both strips are conditional
    and explainable in a sentence, which is the point: one desk prints
    "Quartet at the Shape Hall w/ Brass", the other prints "Quartet", and they
    are the same act on the same night at the same place.

    Returns the title's own comparison form when neither strip applies, so a
    performer key is never emptier than the title it came from.
    """
    soft = _soft(title)
    for sep in _VENUE_SEPARATORS:
        head, found, tail = soft.rpartition(sep)
        # Only when the tail IS this row's place: an "at" that names something
        # else is part of the title (ONE-LIVE-TRUST.md — never guess).
        if found and head and place and _hard(tail) == place:
            soft = head
            break
    for sep in _SUPPORT_SEPARATORS:
        head, found, _tail = soft.partition(sep)
        if found and head.strip():
            soft = head
            break
    return _hard(soft) or _hard(title)


# --------------------------------------------------------------------------
# Rows
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Keyed:
    """One desk row with its three key parts computed. Kept separate from
    `Happening` so nothing here can be mistaken for something a desk stated.
    """

    row: Happening
    via: str
    night: Optional[str]
    place: str
    title_key: str
    performer: str
    why_local: Optional[str]  # None when the row carries a union key

    @property
    def unionable(self) -> bool:
        return self.why_local is None


@dataclass
class UnionRow:
    """One row of the union table: one happening, one key, one or many vias."""

    key: str
    basis: str
    night: Optional[str]
    place_text: Optional[str]
    title: str
    kind: str
    kind_source: str
    members: List[Keyed] = field(default_factory=list)

    @property
    def vias(self) -> Tuple[str, ...]:
        """Every desk that printed this row, in first-seen order."""
        out: List[str] = []
        for m in self.members:
            if m.via not in out:
                out.append(m.via)
        return tuple(out)

    @property
    def dated(self) -> bool:
        """True when at least one desk stated a machine date. `when_text` prose
        never makes a row dated — that is the whole "no invented dates" clause.
        """
        return any(m.row.when for m in self.members)

    @property
    def when_stated(self) -> Optional[str]:
        for m in self.members:
            if m.row.when:
                return m.row.when
        return None

    @property
    def titles(self) -> Tuple[str, ...]:
        out: List[str] = []
        for m in self.members:
            if m.row.title not in out:
                out.append(m.row.title)
        return tuple(out)


@dataclass
class DeskState:
    """What one desk contributed, and whether it could be read at all."""

    door_id: str
    via: str
    rows: int
    pages_read: int
    pages_blocked: int
    exhausted: bool
    stopped_because: str
    blocked_reasons: Tuple[str, ...] = ()

    @property
    def readable(self) -> bool:
        """False when the desk gave us no page at all.

        A desk we could not open has an UNKNOWN list, never an empty one. The
        founder said it plainly this session: "403 is not a zero list." Every
        count that would otherwise read as this desk's absence is suppressed
        downstream on this flag.
        """
        return self.pages_read > 0

    @property
    def floor(self) -> bool:
        """True when this desk's list may continue past where the walk stopped,
        so its contribution is a floor rather than a measurement.
        """
        return not self.exhausted


@dataclass
class DeskUnion:
    """The whole union: every row once, plus everything the union could not do."""

    mode: str                       # "FIXTURE" | "LIVE"
    timezone_id: str
    desks: List[DeskState] = field(default_factory=list)
    rows: List[UnionRow] = field(default_factory=list)
    #: Pairs merged on the performer rather than the whole title. Listed so
    #: every judgment-bearing merge is visible and reversible by eye.
    performer_merges: List[Tuple[str, Tuple[str, ...]]] = field(default_factory=list)
    #: Two rows from the SAME desk that the founder's rule collapses. Reported
    #: because it makes this table's per-desk count differ from
    #: `tools/desk_coverage.py`, and an unexplained difference is a defect.
    within_desk_merges: List[Tuple[str, Tuple[str, ...]]] = field(default_factory=list)
    #: Rows on different desks that agree on night and place but not on the
    #: name, or that could not be keyed at all. Held APART, never merged.
    held_apart: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.rows)

    @property
    def both(self) -> int:
        return sum(1 for r in self.rows if len(r.vias) > 1)

    def only(self, via: str) -> int:
        return sum(1 for r in self.rows if r.vias == (via,))

    @property
    def all_readable(self) -> bool:
        return all(d.readable for d in self.desks)

    @property
    def any_floor(self) -> bool:
        return any(d.floor for d in self.desks if d.readable)


# --------------------------------------------------------------------------
# The union
# --------------------------------------------------------------------------

def _slug(k: Keyed) -> str:
    """A short, stable, READABLE tail for a desk-local key: the listing's own
    last path segment when it stated an address, else its title's key form.
    """
    url = (k.row.listing_url or "").rstrip("/")
    if url:
        tail = url.rsplit("/", 1)[-1]
        if tail:
            return tail
    return k.title_key or "untitled"


#: Joins the three key parts. `~` rather than `|`, because every one of these
#: keys is printed inside a markdown table and a pipe would split the cell —
#: the key parts are punctuation-stripped, so `~` can never appear inside one.
KEY_SEP = "~"


def _key_of(k: Keyed) -> str:
    if k.unionable:
        return f"{k.night}{KEY_SEP}{k.place}{KEY_SEP}{k.title_key}"
    return f"{k.row.door_id}#{_slug(k)}"


def _keyed(walk: DeskWalk, timezone) -> List[Keyed]:
    out: List[Keyed] = []
    via = walk.via or walk.door_id
    for row in walk.rows:
        night, _note = local_night(row.when, timezone)
        place = place_key(row.place_text)
        title_key = _hard(row.title)
        why = None
        if night is None:
            why = NO_NIGHT
        elif not place:
            why = NO_PLACE
        elif not title_key:
            why = NO_TITLE
        out.append(Keyed(row=row, via=via, night=night, place=place,
                         title_key=title_key,
                         performer=performer_key(row.title, place),
                         why_local=why))
    return out


def _desk_state(walk: DeskWalk) -> DeskState:
    return DeskState(
        door_id=walk.door_id,
        via=walk.via or walk.door_id,
        rows=len(walk.rows),
        pages_read=walk.pages_read,
        pages_blocked=walk.pages_blocked,
        exhausted=walk.exhausted,
        stopped_because=walk.stopped_because,
        blocked_reasons=tuple(
            f"page {p.n}: {p.blocked_reason}" for p in walk.pages if p.blocked),
    )


def union(walks: Sequence[DeskWalk], *, timezone, timezone_id: str,
          mode: str = "FIXTURE") -> DeskUnion:
    """Fold several desk walks into one table under the founder's de-dup rule.

    Order matters and is the caller's: the first desk that printed a row owns
    the title and the kind shown for it, and later desks add their `via`. That
    is a display choice, not a truth claim — every member row is kept, and the
    table prints the other desk's title whenever the two disagree.
    """
    if not walks:
        raise DeskUnionError("union() needs at least one walk — an empty union "
                             "would print as a locale with nothing on")
    if timezone is None:
        raise DeskUnionError(
            "no timezone for this locale: the union's 'same night' test cannot "
            "be computed without one, and this module will not assume a home "
            "town. State `locale.timezone` in the pack.")

    out = DeskUnion(mode=mode, timezone_id=timezone_id,
                    desks=[_desk_state(w) for w in walks])

    by_key: Dict[str, UnionRow] = {}
    # (night, place) -> performer -> key, so a second desk's differently-worded
    # title can still find the group it belongs to.
    by_performer: Dict[Tuple[str, str], Dict[str, str]] = {}

    for walk in walks:
        for k in _keyed(walk, timezone):
            key = _key_of(k)
            basis = BASIS_UNION if k.unionable else BASIS_LOCAL
            if k.unionable and key not in by_key:
                # The whole title did not match an existing group; the founder's
                # rule allows the PERFORMER to carry the match instead.
                slot = by_performer.setdefault((k.night, k.place), {})
                twin = slot.get(k.performer)
                if twin is not None:
                    key, basis = twin, BASIS_PERFORMER
            target = by_key.get(key)
            if target is None:
                target = UnionRow(
                    key=key, basis=basis, night=k.night,
                    place_text=k.row.place_text, title=k.row.title,
                    kind=k.row.kind, kind_source=k.row.kind_source)
                by_key[key] = target
            else:
                if basis == BASIS_PERFORMER:
                    target.basis = BASIS_PERFORMER
                # A kind the DESK stated outranks one the other desk defaulted
                # to — the same precedence one page already uses for its two
                # readings (`desk_read.fill_holes`). A default never displaces a
                # desk's own word.
                if (target.kind_source != "desk_category"
                        and k.row.kind_source == "desk_category"):
                    target.kind = k.row.kind
                    target.kind_source = k.row.kind_source
                if any(m.via == k.via for m in target.members):
                    out.within_desk_merges.append(
                        (key, (target.members[0].row.title, k.row.title)))
                elif basis == BASIS_PERFORMER:
                    out.performer_merges.append(
                        (key, (target.members[0].row.title, k.row.title)))
            target.members.append(k)
            if k.unionable:
                by_performer.setdefault((k.night, k.place), {}).setdefault(
                    k.performer, key)
            else:
                out.held_apart.append((f"{k.via}: {k.row.title or '(untitled)'}",
                                       k.why_local or ""))

    out.rows = list(by_key.values())
    return out


def near_misses(one: DeskUnion) -> List[Tuple[str, str, str, str]]:
    """Rows on DIFFERENT desks that share a night and a place but were not
    merged. Reported, never merged: the founder's rule needs all three parts,
    and a place plus a night is two.

    This is the honest ceiling on the union — every pair here is a row the table
    counts twice and might not have to.
    """
    groups: Dict[Tuple[str, str], List[UnionRow]] = {}
    for row in one.rows:
        if row.night and row.place_text:
            groups.setdefault((row.night, place_key(row.place_text)), []).append(row)
    out: List[Tuple[str, str, str, str]] = []
    for (night, _place), rows in sorted(groups.items()):
        if len(rows) < 2:
            continue
        for i, left in enumerate(rows):
            for right in rows[i + 1:]:
                if set(left.vias) & set(right.vias):
                    continue  # same desk listing two things — not a near miss
                out.append((night, left.place_text or "", left.title, right.title))
    return out


# --------------------------------------------------------------------------
# Tables — in this module, so a test can assert on the exact words a founder
# reads. Nothing here computes: every number comes off the dataclasses above.
# --------------------------------------------------------------------------

def _cell(value: Optional[str]) -> str:
    text = (value or "").replace("|", "\\|").strip()
    return text or "—"


def _sort_key(row: UnionRow) -> Tuple[int, str, str, str]:
    # Undated rows sort last, together: they are the honest holes, and burying
    # them among the dated rows is how they stop being noticed.
    return (0 if row.night else 1, row.night or "", _hard(row.place_text),
            _hard(row.title))


def union_table(one: DeskUnion) -> str:
    """The founder's table: unique key, via, kind-or-other, dated-or-not."""
    lines = ["| # | unique key | via | kind | dated | title | place |",
             "|---|---|---|---|---|---|---|"]
    for i, row in enumerate(sorted(one.rows, key=_sort_key), start=1):
        vias = " + ".join(row.vias)
        titles = row.titles
        title = titles[0] + (f"  _(also: {'; '.join(titles[1:])})_"
                             if len(titles) > 1 else "")
        # The basis is stated on the key whenever it is NOT the plain
        # night+place+title match, so a reader never has to guess whether a row
        # was matched, judged, or never eligible.
        basis = "" if row.basis == BASIS_UNION else f" _({row.basis})_"
        lines.append(
            f"| {i} | `{_cell(row.key)}`{basis} | {_cell(vias)} | `{row.kind}` | "
            f"{'yes' if row.dated else '**no**'} | {_cell(title)} | "
            f"{_cell(row.place_text)} |")
    return "\n".join(lines)


def desk_table(one: DeskUnion) -> str:
    """Per-desk state — the row that keeps a blocked desk from reading as an
    empty one.
    """
    lines = ["| desk | via | pages read | pages blocked | rows | walk ended | state |",
             "|---|---|---|---|---|---|---|"]
    for d in one.desks:
        if not d.readable:
            state = "**UNREADABLE — not a zero list**"
            rows = "unknown"
        elif d.floor:
            state = "partial — the desk's list continues"
            rows = str(d.rows)
        else:
            state = "read to the end of its list"
            rows = str(d.rows)
        lines.append(
            f"| `{d.door_id}` | {_cell(d.via)} | {d.pages_read} | "
            f"{d.pages_blocked} | {rows} | `{d.stopped_because}` | {state} |")
    return "\n".join(lines)


def board_table(one: DeskUnion) -> str:
    """<desk> only | <other desk> only | both | unique total.

    The bucket names come from the walks' own `via`, never from a brand written
    here: a brand literal in this package is how a locale stops being data
    (`worker.locale.pack`, and the guard in tests/test_locale_pack.py).

    "X only" is a claim about EVERY OTHER desk — that it did not have the row —
    so what those other desks gave us decides what may be printed, and each
    bucket carries the direction its number can still move in:

      * another desk UNREADABLE -> `unknown`. A desk we could not open supports
        no claim at all: 403 is not a zero list.
      * another desk PARTIAL (its list continues past where the walk stopped),
        this one exhausted -> **at most** N. Rows on its unread pages can still
        match these, which moves them out of "only" and into "both". An
        exact-looking count here would overstate one desk's exclusive coverage
        — the same defect as printing a blocked desk's zero, one degree weaker.
      * this desk partial, every OTHER desk read to the end -> **at least** N.
        Its unread pages can only add rows, and nothing left to read can claim
        them, so the count can only grow.
      * BOTH partial -> N so far, and neither bound is printed: reading on can
        take rows out of the bucket and put new ones in.
      * everything exhausted -> the exact number.

    `both` and the unique total are floors whenever anything is unread — a
    partial walk or an unreadable desk alike — because more reading reveals
    more overlap and more rows and never un-merges what is already matched.
    Every one of those floors PRINTS as "at least N": the word "floor" in a
    note does not undo a number that looks measured, which is the defect this
    docstring's own first draft shipped in the unreadable branch.
    """
    readable = [d for d in one.desks if d.readable]
    unreadable = [d for d in one.desks if not d.readable]
    lines = ["| bucket | rows | note |", "|---|---|---|"]
    for d in one.desks:
        others_partial = [o for o in one.desks
                          if o.door_id != d.door_id and o.readable and o.floor]
        if unreadable:
            note = ("cannot be stated: "
                    + ", ".join(f"`{u.door_id}` was not readable" for u in unreadable)
                    + " — 403 is not a zero list")
            value = "unknown"
        elif others_partial and d.floor:
            # Both directions are open at once: the other desk's unread pages
            # can take rows OUT of this bucket (they turn into `both`), and this
            # desk's own unread pages can put new ones IN. Neither bound holds,
            # so neither is printed.
            value = f"**{one.only(d.via)} so far**"
            note = ("neither a ceiling nor a floor: this desk AND "
                    + ", ".join(f"`{o.door_id}`" for o in others_partial)
                    + " both stopped short, so reading on can take rows out of "
                      "this bucket and add others to it")
        elif others_partial:
            value = f"**at most** {one.only(d.via)}"
            note = ("a claim about the OTHER desk: "
                    + ", ".join(f"`{o.door_id}`" for o in others_partial)
                    + " stopped short, and rows on its unread pages could still "
                      "match these — an exclusive count needs the other list whole")
        elif d.floor:
            value = f"**at least** {one.only(d.via)}"
            note = ("this desk's list continues, and every other desk was read to "
                    "the end — so these stay its own and the count can only grow")
        else:
            value = str(one.only(d.via))
            note = "exact — every desk was read to the end of its list"
        lines.append(f"| {_cell(d.via)} only | {value} | {note} |")
    if unreadable:
        lines.append("| both | unknown | one desk was not readable |")
        # A floor, and PRINTED as one. An exact-looking bold total beside
        # `unknown` buckets reads as the complete cross-desk count, which is
        # the same defect as printing a blocked desk's zero — the word "floor"
        # in the note does not undo a number that looks measured.
        lines.append(f"| **unique total** | **at least {one.total}** | "
                     f"a FLOOR from the readable desk(s) only "
                     f"({', '.join('`' + d.door_id + '`' for d in readable) or 'none'}) "
                     f"— the unread desk(s) can only add rows or merge into these |")
    else:
        matched = f"matched on `{BASIS_UNION}` (or `{BASIS_PERFORMER}`)"
        if one.any_floor:
            lines.append(f"| both | **at least** {one.both} | {matched}; a partial "
                         f"walk can reveal more overlap and never less |")
            lines.append(f"| **unique total** | **at least {one.total}** | "
                         f"the union, deduped — a FLOOR: at least one desk's list "
                         f"continues, and unread rows can only add or merge |")
        else:
            lines.append(f"| both | {one.both} | {matched} |")
            lines.append(f"| **unique total** | **{one.total}** | "
                         f"the union, deduped — every desk read to the end |")
    return "\n".join(lines)


def certainty_note(one: DeskUnion) -> str:
    """One sentence saying what the board's numbers prove — DERIVED from the
    same desk facts the buckets are labelled from.

    It exists because prose written ALONGSIDE a table makes its own certainty
    claim, and that claim drifts the moment the table's rules change. This
    module's own footer said "every count here is therefore a FLOOR" for two
    rounds after `board_table` started printing ceilings beside it: the report
    contradicted its own labels, and a reader was left to reconcile them. A
    summary of a computation belongs to that computation.
    """
    unreadable = [d for d in one.desks if not d.readable]
    if unreadable:
        return ("One or more desks did not open ("
                + ", ".join(f"`{d.door_id}`" for d in unreadable)
                + "), so no desk's exclusive count can be stated at all and the "
                  "unique total is only a FLOOR — a desk we could not read has "
                  "an unknown list, never an empty one.")
    partial = [d for d in one.desks if d.floor]
    if not partial:
        return ("Every desk was read to the end of its own list, so the counts "
                "above are exact rather than bounds.")
    if len(partial) > 1:
        return ("More than one desk stopped short ("
                + ", ".join(f"`{d.door_id}`" for d in partial)
                + "), so no exclusive count is even a bound: reading on can take "
                  "rows out of an `only` bucket and add others to it, which is "
                  "why those cells say `so far`. `both` and the unique total are "
                  "FLOORS — more reading merges more and un-merges nothing.")
    only_one = partial[0]
    return (f"`{only_one.door_id}` stopped short, so the counts above are bounds "
            f"and not all in the same direction: every OTHER desk's `only` count "
            f"is a CEILING (its rows can still turn out to be on the unread "
            f"pages), `{only_one.door_id}`'s own is a FLOOR, and `both` plus the "
            f"unique total are FLOORS.")


def held_apart_table(one: DeskUnion) -> str:
    """Every row the de-dup rule could not key, and why. These rows are IN the
    union table under a desk-local key — this is the reason list, not a
    discard pile.
    """
    if not one.held_apart:
        return "_None: every row carried a night, a place and a title._"
    lines = ["| row | why it can only ever be itself |", "|---|---|"]
    for what, why in one.held_apart:
        lines.append(f"| {_cell(what)} | {_cell(why)} |")
    return "\n".join(lines)


def near_miss_table(one: DeskUnion) -> str:
    """The ceiling: different desks, same night, same place, different name."""
    misses = near_misses(one)
    if not misses:
        return ("_None: no two desks put differently-named rows in the same "
                "place on the same night._")
    lines = ["| night | place | one desk says | the other says |", "|---|---|---|---|"]
    for night, place, left, right in misses:
        lines.append(f"| {night} | {_cell(place)} | {_cell(left)} | {_cell(right)} |")
    return "\n".join(lines)
