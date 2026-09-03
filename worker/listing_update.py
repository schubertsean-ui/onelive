"""What a re-read of a defining page may change about the listings it publishes.

The event-proximity queue (worker/crawl_state.py) re-reads the page that
DEFINES a published event as the event approaches. This module is what happens
next: it compares that page's fresh reading against the rows the page publishes
and decides, per event, whether anything changed — then writes the ones that
did, with the evidence.

FOUNDER'S RULE, verbatim (2026-09-02), and every branch below is one clause of
it:

    "Confirmed check MAY update a published listing (time, cancel, postpone,
    title) only with same-page evidence. Unconfirmed = no mutation. Do not
    delete the row from the catalog; mark cancelled/moved and keep evidence.
    Ambiguous parse = keep."

    "Confirmed gone (clean 404 of defining URL, or clean parse that the event
    is absent from that calendar): mark cancelled/moved with evidence; row
    remains."

PER EVENT, NEVER PER PAGE. This is the correction R-091(a) demanded and the
single most important property here. A page-level verdict is the verdict of ONE
candidate — worker/orchestrator.py gates the page on its first extracted
candidate — so a calendar of forty shows carries one PASS that says nothing
about the other thirty-nine. A page-level PASS is therefore a PRECONDITION and
never a licence: each published row is matched to a specific listing on the
page, and the update is licensed by THAT listing's own trust-gate verdict,
recomputed here from its real stored evidence (worker/trust_gate3.evaluate_gate,
the same gate the orchestrator runs) rather than read off a stamped status that
may be stale or may never have been written at all.

THE IDENTITY STACK (2026-09-03) is the third anchor everything below waited
for. R-095, R-097, R-099 and R-102 each ended at the same recorded trigger —
"a stable per-listing identifier on the candidate row" — because title and time
cannot tell a rename from a replacement, a re-time from the next occurrence, or
one of two 8pm bands from the other. When the SOURCE ITSELF states an id (an
ICS `UID`, a schema.org `Event.url`/`@id`, a claimant's own row url) that
question is answered by the source rather than inferred, and the fields the
inference could not license — `title`, `start_time` — become writable on
exactly that evidence and on nothing weaker. `worker/identity.py` holds the
stack; the order is the founder's: ADOPT the stated id, else COMPOSITE
(source, normalized title, start date), else REFUSE.

WITHOUT an id, every #214 refusal below stands verbatim, which is the common
case today: no class-B fixture in this repository carries a per-listing id, and
`worker/segment.py` reduces each event block to TEXT before the extractor sees
it, so nothing on the crawl path can state one yet (docs/RECORD.md R-103).

WHAT CANNOT HAPPEN HERE, structurally:

  * No delete. There is no DELETE statement in this file, at any verdict, for
    any reason (worker.crawl_state.may_delete_listing returns False for every
    input and is asserted before the writer runs). Coverage Law: a row we
    legally saw is never dropped.
  * No publish. This module imports no promote path and writes no INSERT into
    `event`; it can only change four columns of a row somebody already
    published through the gate. The orchestrator's promote-import ban
    (tools/trust_gate.py) is untouched and this file is under the same ban.
  * No new field. Exactly UPDATABLE_LISTING_FIELDS, from the founder's own
    enumeration, and `status` only ever moves to the confirmed-gone value.
  * No blanking. A field is written only when the page states a NEW value;
    "the page stopped mentioning the end time" is not evidence that the event
    lost its end time, so a null on the page leaves the published value alone.

THE FALSE-ABSENCE GUARD is the one piece of judgement this module adds beyond
the founder's text, and it exists because absence is the only evidence shape
here that can be manufactured by a page merely being SHORT. A calendar that
lists the next ten shows legitimately stops mentioning a show three months out;
reading that as "cancelled" would take a real event off the live feed on
evidence that was never about it. So an absence must be BRACKETED: the page's
own parsed listings have to reach both before and after the missing event's
start time before its silence about that event counts as a statement. An
unbracketed absence is ambiguous, and ambiguous keeps.

WHAT "MARK GONE" COSTS, stated because it is bigger than it looks: the live
consumer surface reads `status in (scheduled, moved)` (web/lib/promoted.ts,
web/lib/licensed.ts), so `cancelled` drops the row from the feed. It remains in
the catalog, keeps its evidence, is still reachable by direct link, and the
detail page says "This event has been cancelled." (web/lib/detail.ts::
statusNote) rather than 404-ing — which is exactly the founder's "row remains"
— but a wrong cancel is a user-visible error, which is why the guards above are
guards and not preferences.
"""
from __future__ import annotations

import html
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence

from worker.identity import (
    DIFFERENT,
    NO_IDENTITY,
    SAME,
    ListingIdentity,
    identity_verdict,
    read_identity,
)
from worker.crawl_state import (
    UNVERIFIED,
    UPDATABLE_LISTING_FIELDS,
    VERIFIED_ABSENT,
    VERIFIED_PRESENT,
    may_delete_listing,
    may_mark_gone,
    may_update_listing,
)

logger = logging.getLogger(__name__)

#: The status a CONFIRMED-GONE listing takes. The schema's closed vocabulary is
#: `scheduled|cancelled|moved` (migration 0001) and the founder wrote
#: "cancelled/moved", so the choice between them has to be made here rather
#: than guessed per row. It is `cancelled`, for a reason that is about evidence
#: and not preference: neither confirmed-gone shape tells us WHERE the event
#: went. A page that 404s and a calendar that no longer names a show both say
#: the same thing — it is not there — and `moved` would assert a fact ("the
#: venue shown is the current one", web/lib/detail.ts) that no page stated.
#:
#: The other half of the founder's phrase — "postpone" — is deliberately NOT
#: written as `moved` here either. A same-title listing at a new time is a
#: RESCHEDULE, but the same page evidence is equally consistent with a venue
#: correcting a typo, and telling those apart needs the listing's own timezone,
#: which the schema does not carry (R-090). So a moved time updates
#: `start_time` and leaves the row scheduled and VISIBLE with the new time,
#: which is what a person needs from it. Recorded, with R-090 as the trigger:
#: docs/RECORD.md R-092.
GONE_STATUS = "cancelled"

#: Decisions this module can reach. Every published row on a re-read page gets
#: exactly one, including the rows nothing happened to — a re-check that
#: decided to do nothing is a result, and the founder's table prints it.
ACTION_UPDATE = "update"
ACTION_MARK_GONE = "mark_gone"
ACTION_NONE = "none"


@dataclass(frozen=True)
class PublishedListing:
    """One published `event` row that a given page defines."""

    event_id: str
    title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = "scheduled"
    #: What the SOURCE said identifies this listing, carried from the candidate
    #: that promoted it (worker/identity.py). NO_IDENTITY is the honest default
    #: and the common case — see the module note on the identity stack.
    identity: ListingIdentity = NO_IDENTITY
    #: The source the promoting candidate was read from. The first element of
    #: the founder's composite key, and a guard rather than a matcher: two rows
    #: from different sources are never one listing, whatever they agree about.
    source_id: Optional[str] = None


@dataclass(frozen=True)
class ParsedListing:
    """One listing this run just extracted from that page."""

    candidate_id: str
    title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    #: The class the CANDIDATE ROW itself records, not the one the caller
    #: happens to be holding. Any evidence written about this listing must be
    #: labelled with its own provenance — see _write_all for why a default here
    #: would be a fabricated upgrade.
    source_class: Optional[str] = None
    #: What the SOURCE said identifies this listing, read from the candidate's
    #: own stored `extracted["_identity"]` (worker/identity.py).
    identity: ListingIdentity = NO_IDENTITY
    #: The source this listing was read from — see PublishedListing.source_id.
    source_id: Optional[str] = None


@dataclass(frozen=True)
class ListingDecision:
    """What the re-check decided about ONE published row, and why in plain words.

    `why` is written to be read by a person in the run table, not parsed by a
    caller — the machine-readable part is `action` and `fields`.
    """

    event_id: str
    action: str
    why: str
    fields: Dict[str, Any] = field(default_factory=dict)
    matched_candidate_id: Optional[str] = None
    #: The matched listing's OWN source class, carried so the evidence row can
    #: be labelled with the provenance it actually has.
    matched_source_class: Optional[str] = None

    @property
    def mutates(self) -> bool:
        return self.action in (ACTION_UPDATE, ACTION_MARK_GONE)


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """A naive timestamp is UTC — the same reading worker/crawl_state.py uses,
    because these values come from the same `timestamptz` columns."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


#: Everything that is not a letter or a digit, IN ANY SCRIPT. `\W` is
#: Unicode-aware for str patterns, so Cyrillic and CJK words survive instead of
#: being erased; `_` is added because `\W` alone would keep it.
_PUNCT = re.compile(r"[\W_]+")


def _fold_run(run: str, *, fold_marks: bool) -> str:
    """One run of non-word characters, reduced to what a comparison may turn on.

    Marks are `\\W`, so the punctuation pass would turn them into spaces — and a
    mark sits INSIDE a word (`Sigur Rós` decomposes to `sigur ro` + mark + `s`),
    so a space there splits the word in half. They are handled by CATEGORY,
    never by `unicodedata.combining()`, which returns 0 for spacing (Mc) and
    enclosing (Me) marks and so silently covers Latin while missing the scripts
    that need it most.

    `fold_marks` is the whole argument of round 9, and it exists because the two
    callers need OPPOSITE strictness:

      * fold_marks=False (identity, `normalize_title`) — every mark is KEPT,
        inline, as part of the word. Nothing is discarded, so no two visibly
        different titles can collapse into one.
      * fold_marks=True (the absence guard, `title_still_on_page`) — Mn and Me
        are DELETED and Mc is kept.

    Everything else — real punctuation and whitespace — collapses to ONE space
    either way, so a multi-word title still matches as a whole-word run.
    """
    kept = [ch for ch in run
            if unicodedata.category(ch)[0] == "M"
            and (not fold_marks or unicodedata.category(ch) == "Mc")]
    spaced = any(unicodedata.category(ch)[0] != "M" for ch in run)
    return "".join(kept) + (" " if spaced else "")


def _reduce(text: str, *, fold_marks: bool) -> str:
    """Case, punctuation and spacing removed; letters and digits kept, in every
    script. Marks are kept or folded away according to `fold_marks`.

    NFKD runs in BOTH modes, so a precomposed `é` and a decomposed `e` + mark
    compare equal — those are one character written two ways, which is an
    encoding difference and never a spelling one.

    THE TWO MODES ARE THE R9 FIX, and the third attempt at this line. Both
    earlier versions asked one reduction to serve two callers whose failure
    modes point in opposite directions:

      * The ABSENCE guard's dangerous answer is a false NO. `Beyoncé` and
        `Beyonce` failing to match makes a page that is naming the event read as
        silent, and with a gated bracket that CANCELS a live row. Folding marks
        away is the safe direction here: a false yes merely keeps the row.
      * IDENTITY's dangerous answer is a false YES. Two same-minute listings
        whose titles differ by one mark are two events, and treating them as one
        writes an end time onto the wrong published row. openai/absence-only
        raised exactly this at r9: `_fold_run` called every Mn "optional", but
        the Devanagari VIRAMA and NUKTA are Mn and are meaning-bearing —
        `नुक्कड़` and `नुक्कड` are different words and were collapsing to one.
        Keeping every mark is the safe direction here: a false no refuses.

    So the fold is not a property of the text, it is a property of the QUESTION.
    Asking it once and reusing the answer is what produced three rounds of
    findings on one function.
    """
    folded = unicodedata.normalize("NFKD", text.casefold())
    return _PUNCT.sub(
        lambda m: _fold_run(m.group(), fold_marks=fold_marks), folded).strip()


def normalize_title(title: Optional[str]) -> Optional[str]:
    """A title reduced to what an IDENTITY may turn on: case, punctuation and
    spacing are noise a CMS changes on its own; letters and their marks are not.

    Accents are NOT folded here, and that is deliberate (r9). This value decides
    whether one listing IS another, and a wrong yes writes to a published row.
    The absence guard folds instead — see `_reduce`.

    None for anything that reduces to nothing, INCLUDING an empty or missing
    title — two rows that both lack a title have not been shown to be the same
    row, and the extraction prompt makes a null title the common case
    (ai/prompts.py), so treating null == null as a match would marry unrelated
    listings on almost every page.
    """
    if not title:
        return None
    return _reduce(title.strip(), fold_marks=False) or None


def _same_minute(a: Optional[datetime], b: Optional[datetime]) -> bool:
    """Equal to the minute. Both must exist: a listing with no time has not
    matched a listing with one."""
    ua, ub = _as_utc(a), _as_utc(b)
    if ua is None or ub is None:
        return False
    return ua.replace(second=0, microsecond=0) == ub.replace(second=0, microsecond=0)


#: How far a TITLE-ONLY match may move a published start time before it stops
#: being a re-time and starts being a different occurrence of the same
#: recurring listing. Twelve hours.
#:
#: This bound exists because of a real defect the adversarial panel caught
#: (openai/attacker-smuggle, PR #214): normalized-title equality alone was
#: treated as identity, and recurring listings — "Open Mic", "Trivia Night",
#: "Sunday Service" — repeat that exact title on every occurrence. When the
#: published night has rolled off a calendar and only a LATER occurrence of the
#: same series is still listed, a title-only match is a single hit, and the
#: published row was retimed to the wrong night. A person reads that as "the
#: show moved" and turns up on a night with nothing on.
#:
#: Twelve hours, not twenty-four, and the difference is the point: a DAILY
#: series at a fixed hour puts its next occurrence exactly 24h away, so a 24h
#: window would admit the very case this excludes. Every genuine clock-time
#: correction is far smaller — doors moved an hour, a matinee moved to the
#: evening is six. Beyond the window we do not claim to know which occurrence
#: the page is showing us, and not-knowing keeps the last good row.
#:
#: A genuine reschedule of more than half a day is therefore NOT applied. That
#: is a real narrowing of the founder's "update time", taken deliberately over
#: a proven way to publish a wrong night, and recorded: docs/RECORD.md R-094.
#:
#: r8 WENT FURTHER, and this window no longer licenses a write at all. BOTH
#: openai seats blocked on the same defect from opposite sides: a same-title
#: listing with a DIFFERENT time inside the window (absence-only) and a
#: same-title listing with NO time (attacker-smuggle). The window was an attempt
#: to tell a re-time from another occurrence by distance alone, and it cannot:
#: a screening, a comedy early/late show, a museum tour and a club session all
#: repeat the same title within a few HOURS, and a catalog holding one published
#: occurrence sees exactly one match for the other one. So a title-only match is
#: now a NON-WRITING identity — it keeps the row from reading as absent, which
#: is what it is genuinely evidence of, and nothing more. The window still
#: separates MATCH_TITLE from MATCH_FAR for that purpose.
#:
#: Consequence, stated rather than buried: WITHOUT AN IDENTITY `start_time` is
#: unwritable BY CONSTRUCTION, because the only writing match left is a shared
#: minute and a shared minute has no start change. The founder's "update time"
#: survives there as an end-time correction on a listing that agrees with us on
#: both title and start minute; the cancel and postpone paths are untouched.
#: docs/RECORD.md R-099 — whose own trigger, a per-listing identifier, is what
#: MATCH_IDENTITY now supplies: a listing the source itself says is ours may
#: move its start, because the identity does not rest on the time that moved.
MAX_TITLE_ONLY_RETIME = timedelta(hours=12)

#: The identity a match establishes. These are not degrees of confidence —
#: they are different EVIDENCE, and they license different things.
MATCH_IDENTITY = "identity"  #: the SOURCE's own id says these are one listing
MATCH_TIME = "time"        #: same start time, and nothing contradicts it
MATCH_TITLE = "title"      #: same title — enough to keep the row, never to write it
MATCH_FAR = "far"          #: same title, too far away — probably another occurrence
MATCH_COLLISION = "collision"  #: same start time, but it is plainly a DIFFERENT event
MATCH_UNTITLED = "untitled"    #: same start time, but one side has no title to check


def match_kind(published: PublishedListing, parsed: ParsedListing) -> Optional[str]:
    """How (and whether) this parsed listing identifies the published row.

    Title OR time, never both-required, because the update path exists exactly
    for the cases where one of the two CHANGED: requiring both would make every
    real change look like a disappearance, and the disappearance branch cancels
    things. But the two are not equally strong evidence, and treating them as
    if they were is what produced the retiming defect above:

      * MATCH_TIME — the start times agree. The DATE pins which occurrence of a
        series this is, so a differing title is safely a rename.
      * MATCH_TITLE — the titles agree and the times are within
        MAX_TITLE_ONLY_RETIME (or the page states no time at all). THIS WRITES
        NOTHING. It is enough to keep a row from reading as absent and no more
        — see the narrowing note under MAX_TITLE_ONLY_RETIME.
      * MATCH_FAR — the titles agree and the times are far apart. This is NOT
        an identity: it is very likely the next occurrence of a recurring
        listing. It is reported rather than dropped, because "something on this
        page carries our title" is exactly the reason NOT to read the row as
        absent and cancel it.

    The cost is stated rather than hidden: a listing whose title AND time both
    changed in one edit identifies nothing here. It cannot be marked gone
    either — the page-text check in adjudicate_page sees its title is no longer
    on the page only if it truly is not — so the row simply stands, and the
    rewritten listing comes back through the normal extract → gate → promote
    path as the new row it now is.
    """
    # RUNG 1 — ADOPT. The source's own id, before anything is inferred from a
    # name or a clock. This is the third anchor R-095/R-097/R-099/R-102 all
    # named as their trigger, and it is decisive in BOTH directions:
    #
    #   SAME      — one listing, whatever the title and the clock now say. That
    #               is precisely what makes a rename and a re-time writable:
    #               identity no longer rests on the fields being changed.
    #   DIFFERENT — NOT this row, whatever they agree about. Two listings the
    #               source gave different ids are two listings, so a shared 8pm
    #               and even a shared title cannot make them one. The
    #               fall-through is blocked, because a weaker signal must never
    #               overrule a stronger one that already answered.
    #
    # A DIFFERENT verdict still returns a NON-IDENTITY rather than nothing when
    # the listings overlap, and that is deliberate: something known to be a
    # different event sitting on our start minute (or carrying our title) is a
    # reason to say nothing, never a reason to read our row as absent. Same
    # answer #214 gives without ids, reached with more certainty.
    verdict = identity_verdict(published.identity, parsed.identity)
    if verdict is SAME:
        return MATCH_IDENTITY

    pt, ct = normalize_title(published.title), normalize_title(parsed.title)

    if verdict is DIFFERENT:
        if _same_minute(published.start_time, parsed.start_time):
            return MATCH_COLLISION
        if pt is not None and pt == ct:
            return MATCH_FAR
        return None

    # RUNG 2 — COMPOSITE. No id on either side, so identity has to be inferred,
    # and the founder's key opens with the source: "(locale or source_id,
    # normalized title, start date)". There is no locale column anywhere in
    # supabase/migrations, so source_id is the element that exists.
    #
    # A GUARD rather than a matcher. `load_published_on_page` and
    # `load_parsed_listings` already scope both sides to one page of one source
    # through SQL, so this can only fire for a caller that assembled the two
    # lists itself — and `adjudicate_page` is PURE and takes whatever it is
    # given. Structural scoping in one function is not a property of the policy
    # in another, and a cross-source match writes one venue's change onto
    # another venue's row.
    if (published.source_id is not None and parsed.source_id is not None
            and str(published.source_id) != str(parsed.source_id)):
        return None

    if _same_minute(published.start_time, parsed.start_time):
        # A SHARED MINUTE IS NOT AN IDENTITY WHEN THE TITLES CONTRADICT IT, and
        # this was a blocking finding both openai seats raised on PR #214 r3.
        # A multi-room venue puts two different bands on at 8pm as a matter of
        # course; a replacement booking takes the slot of the show it replaced.
        # In both cases the parsed listing's gate PASS proves that IT is real —
        # it says nothing about it being OURS. Rewriting the published row from
        # it would replace a real event with a different one under the old
        # row's identity, which is the most misleading thing this module could
        # do to a person reading the feed.
        if pt is not None and ct is not None and pt != ct:
            return MATCH_COLLISION
        if pt is None or ct is None:
            # A SHARED MINUTE IS NOT AN IDENTITY WHEN NOBODY CAN NAME IT
            # EITHER, and this was a blocking finding openai/absence-only
            # raised at r7. The r3 fix handled titles that CONTRADICT; a title
            # that is simply MISSING fell through to MATCH_TIME and identified
            # the row. But the same multi-room page that puts two bands on at
            # 8pm also produces untitled listings, and an extraction that drops
            # a title produces them by the dozen: the gate PASS proves that the
            # anonymous listing is real, never that it is ours. Writing an
            # end_time from it would put a fabricated window on a public row.
            #
            # It is not a collision either — nothing contradicts. It is the
            # absence of evidence in both directions, so it identifies nothing
            # AND blocks the cancel path, exactly like MATCH_COLLISION does:
            # something sitting on our start time is a reason to say nothing.
            return MATCH_UNTITLED
        return MATCH_TIME
    if pt is None or pt != ct:
        return None
    if parsed.start_time is None or published.start_time is None:
        # A page that states no time for this listing cannot re-time anything:
        # _field_diff only ever writes values the page actually states.
        return MATCH_TITLE
    shift = abs(_as_utc(parsed.start_time) - _as_utc(published.start_time))
    return MATCH_TITLE if shift <= MAX_TITLE_ONLY_RETIME else MATCH_FAR


def matches(published: PublishedListing, parsed: ParsedListing) -> bool:
    """True when this parsed listing IDENTIFIES the published row.

    MATCH_FAR and MATCH_COLLISION are deliberately not identities — see
    match_kind.
    """
    return match_kind(published, parsed) in (MATCH_IDENTITY, MATCH_TIME, MATCH_TITLE)


_TAG = re.compile(r"<[^>]*>")


def _visible_text(page: str) -> str:
    """The page's words, with its MARKUP resolved — tags to spaces, entities to
    the characters they stand for.

    Blocking finding, openai/attacker-smuggle on PR #214 r3: the absence check
    searched the RAW html. A page that still says `Rock &amp; Roll` or
    `Beyonc&eacute;` reads as not containing "Rock & Roll" or "Beyoncé" once
    punctuation is stripped, because `&amp;` normalizes to the word "amp" and
    `&eacute;` to "eacute" — so a listing plainly present on the page is read
    as gone, and with a gated bracket that cancels a real event off the live
    feed. Titles with an ampersand are ordinary ("Sam & Dave", "Rock & Roll"),
    which makes this the common case rather than an exotic one.

    Tags become SPACES rather than nothing: `<b>Rock</b> &amp; Roll` must not
    collapse into a single run, and a title split across two table cells must
    not fuse with its neighbour's words into a match that was never there.
    Unescaping happens AFTER tag removal so that an escaped `&lt;b&gt;` in the
    page's own visible text is treated as the text it is, never as a tag.
    """
    return html.unescape(_TAG.sub(" ", page))


def title_still_on_page(title: Optional[str], page_text: Optional[str]) -> Optional[bool]:
    """Does the page ITSELF still name this listing? True / False / None (cannot tell).

    The second defect the adversarial panel caught (openai, PR #214): the
    absence branch read "the extractor did not return this event" as "the page
    no longer says it". Those are different claims. Extraction is the one
    probabilistic stage in the pipeline — a model that skips a listing, or a
    segmenter that drops a block, produces exactly the same empty result as a
    genuinely removed show. Cancelling on that hides a real event from the live
    feed on evidence that was never about it.

    So absence is corroborated against the RAW FETCHED TEXT, deterministically
    and without a model: normalize both sides the way titles are normalized
    everywhere else, and look for the title as a whole-word run. If the page
    still carries the words, the extractor missed it and nothing is marked.

    None means the question could not be asked at all — no page text, or a
    published row with no title to look for — and the caller treats that as
    "cannot tell", never as absence.
    """
    needle = _reduce(title, fold_marks=True) if title else None
    if not needle or not page_text:
        return None
    haystack = _reduce(_visible_text(page_text), fold_marks=True)
    return f" {needle} " in f" {haystack} "


def _brackets(
    parsed: Sequence[ParsedListing],
    start_time: datetime,
    gate_passes: Callable[[str], bool],
) -> bool:
    """Do the page's own GATE-PASSED listings reach both sides of this moment?

    The false-absence guard. A page proves it covers a date by listing
    something at or before it and something at or after it; a calendar
    truncated before that date has said nothing about it at all. Listings with
    no start time cannot bracket anything and are skipped — they are still
    evidence the page produced listings, just not evidence about when.

    THE BRACKET ITSELF MUST BE GATED, and this was a blocking finding both
    openai seats raised on PR #214 r2. The asymmetry was mine and it pointed
    the wrong way: an UPDATE already required the matched listing's own
    trust-gate PASS, while a CANCEL — the larger, user-visible action that
    takes a row off the live feed — rested on bracket timestamps that came
    straight from the extractor with no gate at all. A garbled or hostile
    extraction that omits the real event and emits plausible earlier+later
    listings around its date would manufacture exactly the coverage window this
    guard exists to demand, and the row would be marked cancelled on evidence
    the pipeline never validated.

    So a listing only counts toward the bracket if the gate PASSES it, on the
    same re-computed verdict every other decision here uses. The scan
    short-circuits: it stops as soon as both sides are satisfied, and it only
    asks the gate about candidates that could contribute at all, so the common
    case costs a handful of evaluations rather than one per listing on the page.
    """
    moment = _as_utc(start_time)
    before = after = False
    for item in parsed:
        if item.start_time is None:
            continue
        when = _as_utc(item.start_time)
        # Only ask the gate about a listing that would actually move the
        # answer. Written as "does it supply a side we still need" rather than
        # "is it on a side we already have": a listing exactly AT the moment
        # satisfies both comparisons, and the inverted form would skip it while
        # the side it could still fill was missing.
        supplies = (when <= moment and not before) or (when >= moment and not after)
        if not supplies:
            continue
        if not gate_passes(item.candidate_id):
            continue
        before = before or when <= moment
        after = after or when >= moment
        if before and after:
            return True
    return False


def _field_diff(
    published: PublishedListing, parsed: ParsedListing, *, kind: Optional[str] = None
) -> Dict[str, Any]:
    """The updatable fields the page now states DIFFERENTLY.

    Only fields the page actually states: a null from this read is silence, and
    silence never blanks a published value. `status` is absent by construction
    — extraction has no status field (ai/prompts.py), so the only status this
    module can ever write is the confirmed-gone one, from the absence branch.

    `kind` is the match that produced this pair, because WHICH fields may be
    written depends on WHAT identified the row — see the title note below.
    """
    diff: Dict[str, Any] = {}
    # `title` IS WRITTEN ONLY ON MATCH_IDENTITY, and that condition is R-095's
    # own recorded trigger arriving rather than a rule being relaxed.
    #
    # R-095 asked what would license a rewrite: proof that this parsed listing
    # IS that published row, HOLDING WHILE THE TITLE ITSELF CHANGES. Same start
    # time cannot supply it (a different band in the other room shares the
    # minute — MATCH_COLLISION), and same title supplies it only by being
    # EQUAL, in which case there is no title change to write. On title and time
    # alone there is no third anchor, so a rename and a replacement are
    # indistinguishable and one of those two outcomes puts a fabricated name on
    # a public listing. The record's stated trigger: "A STABLE PER-LISTING
    # IDENTIFIER captured at extraction... When a per-listing URL reaches the
    # candidate row, identity survives a rename and `title` becomes writable on
    # exactly that evidence."
    #
    # MATCH_IDENTITY is that evidence and nothing weaker is: the source itself
    # said these two are one listing, so the name changing is the source
    # renaming its own show. Every other match kind keeps the #214 refusal
    # verbatim, which is what the founder's "no identity -> no start_time/title
    # mutation" asks for.
    if kind == MATCH_IDENTITY and parsed.title is not None:
        pt, ct = normalize_title(published.title), normalize_title(parsed.title)
        if ct is not None and pt != ct:
            diff["title"] = parsed.title
    if parsed.start_time is not None and not _same_minute(
            published.start_time, parsed.start_time):
        diff["start_time"] = _as_utc(parsed.start_time)
    if parsed.end_time is not None and not _same_minute(
            published.end_time, parsed.end_time):
        diff["end_time"] = _as_utc(parsed.end_time)
    assert set(diff) <= set(UPDATABLE_LISTING_FIELDS), (
        "listing_update tried to write a field outside the founder's "
        f"enumeration: {sorted(set(diff) - set(UPDATABLE_LISTING_FIELDS))}")
    return diff


def _incoherent(published: PublishedListing, parsed: ParsedListing,
                diff: Dict[str, Any]) -> Optional[str]:
    """Why this diff must not be written, or None if the window it leaves is
    one the page actually states.

    Both openai seats blocked PR #214 at r7 on the same surface, from two
    sides, and both were right: `_UPDATE_SQL` writes with `coalesce`, so a diff
    that names only `start_time` KEEPS the published `end_time` — and nothing
    checked what the two of them said together.

      * A row published 20:00-22:00 whose page now says the show starts at
        23:00, without restating an end, would be written as 23:00-22:00: an
        event that ends before it begins, and one that any reader using
        `end_time` treats as already over. That is fabricated schedule data on
        the public surface, which is the thing this path exists not to do.
      * A gate PASS proves a listing's evidence was corroborated, not that its
        fields are sane. An extraction that emits `end_time` before its own
        `start_time` writes an impossible range through a gate that never
        asked.

    So the rule is the same one the rest of this module runs on — say only what
    the page said. The page must STATE the whole window it is changing, and the
    test is what the page stated, not what changed: a read that restates an end
    time has published that end, whether or not it moved. What it may not do is
    move the start in SILENCE about the end, because silence cannot be stretched
    over a time nobody published. The cost is real and bounded: a venue that
    moves a show and does not restate its end is not followed while the row
    carries an end. Recorded, docs/RECORD.md R-098.
    """
    if not diff:
        return None
    start = diff.get("start_time", _as_utc(published.start_time))
    end = diff.get("end_time", _as_utc(published.end_time))
    if "start_time" in diff and parsed.end_time is None and end is not None:
        return ("the page moves the start but states no end, and the published "
                "end was set against the old start — the window it would leave "
                "is one no page has stated")
    if start is not None and end is not None and end <= start:
        return ("the page's own times do not make a window (it would end at or "
                "before it starts)")
    return None


def _contested_minutes(parsed: Sequence[ParsedListing]) -> set:
    """Start minutes on this page that carry two or more listings with no id.

    A minute is contested when at least two parsed listings sit on it and the
    identities present cannot separate all of them: any listing there with no
    stated identity leaves the slot ambiguous, because an unidentified listing
    could be any of them. Two listings on one minute that BOTH state ids the
    source distinguished are separated, so that minute is not contested.

    Listings with no start time are skipped — they hold no minute to contest.
    """
    by_minute: Dict[datetime, List[ParsedListing]] = {}
    for item in parsed:
        when = _as_utc(item.start_time)
        if when is None:
            continue
        by_minute.setdefault(when.replace(second=0, microsecond=0), []).append(item)
    contested = set()
    for minute, items in by_minute.items():
        if len(items) < 2:
            continue
        # Separated only when every listing on the minute states an identity
        # and no two of them are the SAME one.
        stated = [i.identity for i in items if i.identity.stated]
        if len(stated) == len(items) and not any(
                identity_verdict(a, b) is SAME
                for x, a in enumerate(stated) for b in stated[x + 1:]):
            continue
        contested.add(minute)
    return contested


def adjudicate_page(
    *,
    verdict: str,
    verdict_reason: str = "",
    published: Sequence[PublishedListing],
    parsed: Sequence[ParsedListing],
    gate_passes: Callable[[str], bool],
    page_text: Optional[str] = None,
) -> List[ListingDecision]:
    """One decision per published row this page defines. PURE — no DB, no clock,
    no network, so the whole policy is testable from fixtures.

    `verdict` is worker.crawl_state.classify_recheck's verdict for the DEFINING
    door. `gate_passes(candidate_id)` answers "did the trust gate PASS this
    specific freshly-extracted listing" — the per-listing licence R-091(a)
    required, injected so this function never decides what it cannot see.
    `page_text` is the raw fetched page, used ONLY to corroborate absence
    against what the page says rather than against what the extractor
    returned; without it, nothing can be marked gone from a page that loads.
    """
    decisions: List[ListingDecision] = []

    if verdict == VERIFIED_ABSENT and may_mark_gone(verdict):
        # Confirmed gone, shape one: the defining page itself returned a clean
        # 404 (founder overrule 2026-09-02 — see worker/crawl_state.py's 404
        # note for what this costs and how it is bounded). Nothing to bracket
        # and nothing to match: there is no page. The licence is ASKED of
        # crawl_state rather than re-derived here, so the policy has one home.
        for row in published:
            decisions.append(ListingDecision(
                event_id=row.event_id,
                action=ACTION_MARK_GONE,
                why=("the defining page returned a clean 404 — confirmed gone; "
                     f"marked {GONE_STATUS}, row kept with its evidence"),
                fields={"status": GONE_STATUS},
            ))
        return decisions

    if verdict != VERIFIED_PRESENT:
        # Unconfirmed: timeout, 429/503, a wall, a budget or politeness
        # deferral, an off-site landing, a sensor rejection, or a parse the
        # trust gate declined. We learned nothing, so we change nothing — the
        # last good row stands and only the attempt is recorded.
        reason = verdict_reason or f"check did not confirm ({verdict or UNVERIFIED})"
        # classify_recheck's own reasons already end in "last good row stands";
        # repeating it here made the table read as a stutter.
        tail = "" if "last good row stands" in reason else "; last good row stands"
        for row in published:
            decisions.append(ListingDecision(
                event_id=row.event_id, action=ACTION_NONE,
                why=f"unconfirmed — {reason}{tail}"))
        return decisions

    if not parsed:
        # The page is verified present but produced no listings this read —
        # a byte-identical page (extraction is skipped by design) or a clean
        # parse that named nothing. Either way there is nothing to compare
        # against, and "the page listed nothing" is precisely the shape a
        # blank/broken render takes. Ambiguous keeps.
        for row in published:
            decisions.append(ListingDecision(
                event_id=row.event_id, action=ACTION_NONE,
                why=("page verified but it produced no listings this read — "
                     "nothing to compare; last good row stands")))
        return decisions

    # Matching is resolved for the WHOLE PAGE before any row is decided,
    # because one-to-many has two directions and only one of them was checked.
    # openai/absence-only blocked PR #214 at r6 on the other one: a page with
    # two same-title occurrences inside MAX_TITLE_ONLY_RETIME that returns only
    # the LATER one this read gives each published row exactly one match — the
    # same match. The earlier row then reads as "the page moved me" and is
    # retimed onto the later event, while the later row keeps its own time, so
    # the catalog ends up publishing a real event at an hour nobody announced.
    # A page listing is ONE listing: if two rows claim it, it identifies
    # neither, and both keep what they have.
    #
    # ADOPT THEN COMPOSITE, at the page level too: when a row is identified by
    # the source's own id AND by a weaker inference from some other listing's
    # title or clock, the id wins and the weaker hits are dropped rather than
    # counted as ambiguity. Otherwise the stack would be self-defeating — a
    # calendar that finally states an id would answer the question and then be
    # overruled into "ambiguous" by the very guesswork the id replaces. If two
    # listings both claim the row by IDENTITY, that is the source contradicting
    # itself and the ambiguity is real, so it falls through to the count below.
    hits_by_row = []
    for row in published:
        row_hits = [p for p in parsed if matches(row, p)]
        adopted = [p for p in row_hits if match_kind(row, p) == MATCH_IDENTITY]
        hits_by_row.append((row, adopted or row_hits))
    claims: Dict[str, int] = {}
    for _row, row_hits in hits_by_row:
        for p in row_hits:
            claims[p.candidate_id] = claims.get(p.candidate_id, 0) + 1

    # FOUNDER, VERBATIM: "Collision (two titles, one minute, no unique id) =
    # refuse write." Two listings sharing a start minute with nothing unique to
    # tell them apart make a same-minute identity NON-UNIQUE, even when one of
    # the two carries our exact title — because the other one could be the
    # renamed show and we cannot tell. #214's one-to-one rule does not reach
    # this: it counts how many listings match a ROW, and here exactly one does.
    #
    # The refusal is a NON-WRITE, not a non-match: a contested slot is still a
    # reason not to read the row as absent. And it is lifted by exactly what
    # the founder's clause says lifts it — a unique id. A listing whose
    # identity was ADOPTED is not on this list, because then the minute is not
    # what identified it.
    contested_minutes = _contested_minutes(parsed)

    for row, hits in hits_by_row:
        if len(hits) > 1:
            decisions.append(ListingDecision(
                event_id=row.event_id, action=ACTION_NONE,
                why=(f"{len(hits)} listings on the page match this row on title "
                     "or time — ambiguous; last good row stands")))
            continue

        if hits and claims.get(hits[0].candidate_id, 0) > 1:
            decisions.append(ListingDecision(
                event_id=row.event_id, action=ACTION_NONE,
                matched_candidate_id=hits[0].candidate_id,
                why=("another published row on this page matches the same "
                     "listing — one listing cannot be two rows; ambiguous; "
                     "last good row stands")))
            continue

        if not hits:
            near = {match_kind(row, p) for p in parsed}
            if MATCH_FAR in near or MATCH_COLLISION in near or MATCH_UNTITLED in near:
                # Something on the page is close enough to this row to make its
                # silence unreadable — either our title at a date too far off
                # to be the same occurrence, or a DIFFERENT event holding our
                # start time. Both are reasons to say nothing, and neither is a
                # reason to cancel: an event we cannot cleanly distinguish from
                # what the page shows has not been shown to be gone.
                if MATCH_FAR in near:
                    why = ("the page still lists this title, but at a date too "
                           "far off to be the same occurrence")
                elif MATCH_COLLISION in near:
                    why = ("a different event holds this row's start time on "
                           "the page, so its absence cannot be read cleanly")
                else:
                    why = ("something on the page holds this row's start time "
                           "with no title to check it against, so its absence "
                           "cannot be read cleanly")
                decisions.append(ListingDecision(
                    event_id=row.event_id, action=ACTION_NONE,
                    why=f"{why} — ambiguous; last good row stands"))
                continue
            still_named = title_still_on_page(row.title, page_text)
            if still_named is not False:
                # True  — the page names it and the EXTRACTOR missed it.
                # None  — no page text, or no title to look for: cannot ask.
                # Both are "we did not establish absence", and both keep.
                decisions.append(ListingDecision(
                    event_id=row.event_id, action=ACTION_NONE,
                    why=("the page still names this listing but the extraction "
                         "did not return it — an extraction miss is not a "
                         "cancellation; last good row stands"
                         if still_named
                         else "cannot check the page's own text for this "
                              "listing — absence unconfirmed; last good row stands")))
                continue
            bracketed = (row.start_time is not None
                         and _brackets(parsed, row.start_time, gate_passes))
            if not bracketed or not may_mark_gone(verdict):
                decisions.append(ListingDecision(
                    event_id=row.event_id, action=ACTION_NONE,
                    why=("not on the page, but the page's own gate-passed "
                         "listings do not reach this date — a short calendar, "
                         "or one the gate did not confirm, has not said this "
                         "event is gone; last good row stands")))
                continue
            decisions.append(ListingDecision(
                event_id=row.event_id,
                action=ACTION_MARK_GONE,
                why=("absent from a clean parse of the page that defines it, "
                     "its title is absent from the page's own raw text, and "
                     "the page's GATE-PASSED listings bracket its date — "
                     "confirmed gone; "
                     f"marked {GONE_STATUS}, row kept with its evidence"),
                fields={"status": GONE_STATUS},
            ))
            continue

        hit = hits[0]
        kind = match_kind(row, hit)
        hit_minute = _as_utc(hit.start_time)
        if (kind != MATCH_IDENTITY and hit_minute is not None
                and hit_minute.replace(second=0, microsecond=0) in contested_minutes):
            # The founder's collision clause. Something else sits on this exact
            # minute and nothing unique separates them, so a same-minute match
            # is not an identity here — even though this listing carries our
            # title, the other one could be the show that was renamed to it.
            # Non-writing, never a non-match: a contested slot still means the
            # row is not absent.
            decisions.append(ListingDecision(
                event_id=row.event_id, action=ACTION_NONE,
                matched_candidate_id=hit.candidate_id,
                why=("another listing shares this row's start minute and no "
                     "unique id separates them — collision; last good row "
                     "stands")))
            continue
        diff = _field_diff(row, hit, kind=kind)
        if not diff:
            decisions.append(ListingDecision(
                event_id=row.event_id, action=ACTION_NONE,
                matched_candidate_id=hit.candidate_id,
                why="the page still says exactly what we published — no change"))
            continue
        if not may_update_listing(verdict) or not gate_passes(hit.candidate_id):
            # R-091(a): the page's own gate verdict is a precondition, never
            # the licence. This listing's evidence did not pass the gate, so it
            # does not get to rewrite a published row.
            decisions.append(ListingDecision(
                event_id=row.event_id, action=ACTION_NONE,
                matched_candidate_id=hit.candidate_id,
                why=("the page states a change, but the trust gate did not PASS "
                     "that listing's own evidence — last good row stands")))
            continue
        if kind == MATCH_TITLE:
            # A TITLE IS NOT AN OCCURRENCE. Both openai seats blocked here at
            # r8, from the two sides of one defect: this branch would write a
            # start_time from a same-title listing at a different hour, and an
            # end_time from a same-title listing with no time at all. In both
            # the identity rests on the title alone, and a venue that runs the
            # same show twice in an evening — a screening, an early and late
            # set, a repeating tour slot — makes "the page moved it" and "this
            # is the other one" indistinguishable. The one-to-one rule above
            # catches it only when we have published BOTH occurrences; a
            # catalog holding one sees a single clean match for the other.
            #
            # The match still matters: something on the page carries our title,
            # so the row is not absent and must not be cancelled. That is what
            # a title match is evidence OF, and it is now all it does.
            decisions.append(ListingDecision(
                event_id=row.event_id, action=ACTION_NONE,
                matched_candidate_id=hit.candidate_id,
                why=("the page carries this row's title at a different time, and "
                     "a repeat cannot be told from a move on same-page evidence "
                     "— last good row stands")))
            continue
        bad_window = _incoherent(row, hit, diff)
        if bad_window:
            decisions.append(ListingDecision(
                event_id=row.event_id, action=ACTION_NONE,
                matched_candidate_id=hit.candidate_id,
                why=f"{bad_window} — last good row stands"))
            continue
        licence = ("the source's own id identifies this listing"
                   if kind == MATCH_IDENTITY
                   else "same start minute and a title that does not contradict it")
        decisions.append(ListingDecision(
            event_id=row.event_id, action=ACTION_UPDATE, fields=diff,
            matched_candidate_id=hit.candidate_id,
            matched_source_class=hit.source_class,
            why=(f"confirmed same-page change ({licence}), gate PASS on that "
                 "listing: " + ", ".join(sorted(diff)))))

    return decisions


# --- reads -------------------------------------------------------------------

#: `distinct on (e.event_id)` replaces a plain `distinct` because the identity
#: comes from the PROMOTING CANDIDATE and several candidates can point at one
#: event: projecting `c.extracted` under a plain DISTINCT would return the same
#: event once per differing payload and adjudicate it twice. The tie-break is
#: the EARLIEST promoting candidate (`c.created_at`, then `c.candidate_id` so
#: two rows written in the same transaction still order deterministically) —
#: the row that actually established this listing, and a stable choice across
#: runs rather than whichever the planner happened to return.
_PUBLISHED_ON_PAGE_SQL = """
select distinct on (e.event_id)
       e.event_id, e.title, e.start_time, e.end_time, e.status,
       c.extracted, c.source_id
from event e
join event_candidate c on c.promoted_event_id = e.event_id
where c.source_id = %s
  and c.source_url = %s
  and e.start_time is not null
  and coalesce(e.end_time, e.start_time) > now()
  and e.override_lock = false
  and e.status = 'scheduled'
order by e.event_id, c.created_at, c.candidate_id
"""

_PARSED_ON_PAGE_SQL = """
select candidate_id, title, start_time, end_time, source_class, extracted, source_id
from event_candidate
where candidate_id = any(%s::uuid[])
"""


def load_published_on_page(source_id: str, url: str, cur=None) -> List[PublishedListing]:
    """The published rows this page defines, and only the ones a re-check may
    speak for.

    Four filters, each load-bearing rather than tidy:
      * `start_time is not null` and not ended — the same two clauses
        worker/crawl_state.py's ladder query carries, so the set we adjudicate
        is the set we scheduled the fetch for. A finished show is not news.
      * `override_lock = false` — the schema's own "a human pinned this row"
        flag (migration 0001). A scheduled loop does not overrule a person.
      * `status = 'scheduled'` — a row already marked cancelled or moved has an
        adjudicated state; re-deciding it from a page read would let the loop
        flip a human's cancellation back and forth. Restoring one is a
        person's call, not a crawl's.
    """
    params = (source_id, url)
    if cur is not None:
        cur.execute(_PUBLISHED_ON_PAGE_SQL, params)
        return _to_published(cur.fetchall())
    from worker.candidate_store import db
    with db() as conn:
        with conn.cursor() as own:
            own.execute(_PUBLISHED_ON_PAGE_SQL, params)
            return _to_published(own.fetchall())


def _identity_of(row: Sequence[Any], index: int) -> ListingIdentity:
    """The identity stored on a candidate's `extracted`, or NO_IDENTITY.

    Tolerant of a short row on purpose: `_to_published`/`_to_parsed` are also
    fed by test doubles and by older callers that select fewer columns, and a
    missing column is an absent identity (a hole), never an error and never a
    guess.
    """
    if len(row) <= index:
        return NO_IDENTITY
    return read_identity(row[index])


def _to_published(rows: Sequence[Sequence[Any]]) -> List[PublishedListing]:
    return [PublishedListing(event_id=str(r[0]), title=r[1], start_time=r[2],
                             end_time=r[3], status=r[4],
                             identity=_identity_of(r, 5),
                             source_id=str(r[6]) if len(r) > 6 and r[6] else None)
            for r in rows]


def load_parsed_listings(candidate_ids: Sequence[str], cur=None) -> List[ParsedListing]:
    """The listings THIS run just extracted from the page, read back by id.

    By id rather than by URL on purpose: a URL query would also sweep up
    candidates from earlier runs of the same page, and "what the page says now"
    is the whole evidentiary basis for changing anything.
    """
    ids = [str(c) for c in candidate_ids if c]
    if not ids:
        return []
    if cur is not None:
        cur.execute(_PARSED_ON_PAGE_SQL, (ids,))
        return _to_parsed(cur.fetchall())
    from worker.candidate_store import db
    with db() as conn:
        with conn.cursor() as own:
            own.execute(_PARSED_ON_PAGE_SQL, (ids,))
            return _to_parsed(own.fetchall())


def _to_parsed(rows: Sequence[Sequence[Any]]) -> List[ParsedListing]:
    return [ParsedListing(candidate_id=str(r[0]), title=r[1],
                          start_time=r[2], end_time=r[3],
                          source_class=r[4] if len(r) > 4 else None,
                          identity=_identity_of(r, 5),
                          source_id=str(r[6]) if len(r) > 6 and r[6] else None)
            for r in rows]


def gate_passes_for(candidate_id: str, cur=None) -> bool:
    """Does the trust gate PASS this freshly-extracted listing, right now?

    RECOMPUTED, never read off `event_candidate.status`. A stamped status can
    be stale, can have been moved by an ops action, and — for every candidate
    after the first on a multi-event page — may not have been written yet at
    all (worker/orchestrator.py stamps the first inline and leaves the rest to
    the backlog sweep). The same evaluate_gate the orchestrator runs, over the
    candidate's real stored extraction + evidence signals, is the only honest
    answer.

    Fail closed: any error reading or evaluating is a NO. A listing we could
    not gate does not get to change a published row.
    """
    from worker.candidate_store import (
        list_candidate_source_classes,
        load_candidate_gate_signals,
    )
    from worker.trust_gate3 import GateDecision, evaluate_gate
    try:
        classes = list_candidate_source_classes(candidate_id)
        extracted, evidence_signals = load_candidate_gate_signals(candidate_id, cur=cur)
        verdict = evaluate_gate(
            source_classes=classes, sxsw_mode=False,
            extracted=extracted, evidence_signals=evidence_signals)
    except Exception as exc:  # noqa: BLE001 — fail closed, loudly
        logger.warning(
            "could not re-gate candidate %s for a listing update (%s) — "
            "treating it as NOT passed; the published row is left alone.",
            candidate_id, exc)
        return False
    return verdict.decision is GateDecision.PASS


# --- the write ---------------------------------------------------------------

#: One static statement, every field parameterized, nulls meaning "leave it".
#: Static because tools/trust_gate.py forbids composed SQL, and because a column
#: list built at runtime is exactly the shape in which a field outside the
#: founder's enumeration gets written by accident.
_UPDATE_SQL = """
update event
   set title      = coalesce(%s, title),
       start_time = coalesce(%s, start_time),
       end_time   = coalesce(%s, end_time),
       status     = coalesce(%s, status),
       updated_at = now()
 where event_id = %s
   and override_lock = false
   and status = 'scheduled'
"""

_EVIDENCE_SQL = """
insert into candidate_evidence(candidate_id, source_class, source_name, source_url, quote)
values (%s, %s, %s, %s, %s)
"""

_AUDIT_SQL = """
insert into audit_log(actor_type, action, entity_type, entity_id, payload)
values ('system', 'edit_event', 'event', %s, %s::jsonb)
"""


def apply_decisions(
    decisions: Sequence[ListingDecision],
    *,
    source_id: Optional[str],
    source_name: str,
    page_url: str,
    run_id: str,
    budget=None,
    cur=None,
) -> Dict[str, int]:
    """Write the decisions that mutate. Returns {'updated', 'marked_gone',
    'skipped_budget'}.

    Every write carries its evidence in the same transaction as the change:

      * `candidate_evidence` — the same-page provenance: the matched candidate,
        the page it was read from, and that listing's OWN source class, with no
        fallback to anything the caller holds. Absent for a 404 (no candidate,
        no page) and absent when the candidate records no class, because an
        evidence row asserting provenance it cannot support is worse than none.
        The `quote` column stays EMPTY: it holds text from the page, and this
        path has no page snippet to put in it.
      * `audit_log` — before and after, the page, the run, and the reason, for
        every mutation including the 404 one. An `edit_event` row on the
        `event` entity, the vocabulary migration 0001 already declares.

    The UPDATE re-asserts `override_lock = false` and `status = 'scheduled'` in
    its own WHERE, so a human action landing between the read and the write
    wins the race rather than being silently overwritten; a lost race is a
    no-op the caller counts as skipped, never a retry.
    """
    assert not may_delete_listing(VERIFIED_PRESENT), (
        "may_delete_listing must be False for every verdict — a published row "
        "is never removed by a re-check")
    counts = {"updated": 0, "marked_gone": 0, "skipped_budget": 0}
    to_write = [d for d in decisions if d.mutates]
    if not to_write:
        return counts
    if cur is None:
        from worker.candidate_store import db
        with db() as conn:
            with conn.cursor() as own:
                _write_all(own, to_write, counts, source_id=source_id,
                           source_name=source_name,
                           page_url=page_url, run_id=run_id, budget=budget)
            conn.commit()
        return counts
    _write_all(cur, to_write, counts, source_id=source_id,
               source_name=source_name,
               page_url=page_url, run_id=run_id, budget=budget)
    return counts


def _write_all(cur, decisions, counts, *, source_id, source_name,
               page_url, run_id, budget) -> None:
    for d in decisions:
        if budget is not None and not budget.may_mutate_listing():
            counts["skipped_budget"] += 1
            logger.warning(
                "listing-mutation budget spent for this tick — event %s was "
                "NOT changed (%s). The last good row stands and the next tick "
                "that reads this page decides again.", d.event_id, d.why)
            continue
        fields = d.fields
        cur.execute(_UPDATE_SQL, (
            fields.get("title"),
            fields.get("start_time"),
            fields.get("end_time"),
            fields.get("status"),
            d.event_id,
        ))
        if cur.rowcount != 1:
            # Lost the race with a human action (override_lock set, or the row
            # already adjudicated). Loud, and NOT retried: the newer state wins.
            logger.warning(
                "listing update for event %s changed no row — it was locked or "
                "already adjudicated between the read and the write; the newer "
                "state is kept.", d.event_id)
            continue
        if budget is not None:
            budget.record_listing_mutation()
        # THE EVIDENCE ROW CARRIES PROVENANCE, NEVER PROSE — two blocking
        # findings from openai/attacker-smuggle on PR #214 r4, and both were
        # right about the same thing: an evidence row is an ATTESTATION, so
        # every column of it has to be something that actually happened.
        #
        #   * `quote` holds text FROM THE PAGE. worker/ai_extract.py writes the
        #     listing's own block into it (text[:500]); this path was writing
        #     "re-check <run>: <why>" — the adjudicator's own sentence. Anything
        #     that surfaces a quote would then show a person words the venue
        #     never published. It is left EMPTY now, which is what
        #     candidate_store.add_evidence defaults to, and the reason lives in
        #     the audit row where the founder ruled it belongs (2026-09-03).
        #   * `source_class` is the listing's OWN class, read from the candidate
        #     row. The previous default of "venue_calendar" was an ANCHOR class
        #     in worker/gating.py, so a blank or unknown provenance was being
        #     silently upgraded to the strongest tier in the trust vocabulary —
        #     on a row attached to a published-data mutation. There is no
        #     default now: an unlabelled listing gets NO evidence row and says
        #     so in the log, because a row asserting a class it cannot support
        #     is worse than no row at all. The audit entry still records the
        #     mutation either way.
        # THE MATCHED CANDIDATE'S OWN CLASS OR NO ROW AT ALL. There is no
        # fallback to the caller's class — the parameter that used to carry one
        # into this function is GONE, so no future edit can reintroduce the
        # borrow by accident. Removing it is the r5 fix: openai/absence-only blocked on it and
        # openai/attacker-smuggle raised the same thing as a nit, both
        # observing that the code and the rule this file states had drifted
        # apart. The docstring already claimed "the listing's OWN class, read
        # from the candidate row"; the code still reached for the caller's
        # value when the candidate had none, and the caller's value can be an
        # ANCHOR class. A near-miss is the whole risk here: the evidence row
        # would look correct, cite a real source-level class, and still assert
        # provenance for a listing that never carried it.
        if d.matched_candidate_id and d.matched_source_class:
            cur.execute(_EVIDENCE_SQL, (
                d.matched_candidate_id, d.matched_source_class,
                source_name, page_url, "",
            ))
        elif d.matched_candidate_id:
            logger.warning(
                "listing update for event %s wrote NO evidence row: candidate "
                "%s records no source class of its own, and this path will not "
                "borrow one from the caller to fill the gap. The audit_log "
                "entry still records the change.",
                d.event_id, d.matched_candidate_id)
        cur.execute(_AUDIT_SQL, (d.event_id, json.dumps({
            "run_id": run_id,
            "kind": d.action,
            "page_url": page_url,
            "source_id": str(source_id) if source_id else None,
            "candidate_id": d.matched_candidate_id,
            "changed": {k: (v.isoformat() if isinstance(v, datetime) else v)
                        for k, v in fields.items()},
            "why": d.why,
        })))
        counts["updated" if d.action == ACTION_UPDATE else "marked_gone"] += 1


def render_decision_table(rows: Sequence[Sequence[Any]]) -> str:
    """The founder's table: `event | check result | mutated? | why`.

    Pure formatting over decisions the loop already made — it queries nothing
    and decides nothing, so printing it can never change a run.
    """
    header = ("event", "check result", "mutated?", "why")
    out_rows = [header]
    for name, verdict, decision in rows:
        out_rows.append((
            name,
            (verdict or UNVERIFIED).replace("verified_", "").replace("unverified", "no"),
            "yes" if decision.mutates else "no",
            decision.why,
        ))
    widths = [max(len(r[i]) for r in out_rows) for i in range(len(header))]
    lines = [" | ".join(c.ljust(widths[i]) for i, c in enumerate(out_rows[0])).rstrip(),
             "-+-".join("-" * w for w in widths)]
    for r in out_rows[1:]:
        lines.append(" | ".join(c.ljust(widths[i]) for i, c in enumerate(r)).rstrip())
    return "\n".join(lines)
