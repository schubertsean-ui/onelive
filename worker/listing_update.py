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

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence

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


@dataclass(frozen=True)
class ParsedListing:
    """One listing this run just extracted from that page."""

    candidate_id: str
    title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


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


_PUNCT = re.compile(r"[^0-9a-z]+")


def normalize_title(title: Optional[str]) -> Optional[str]:
    """A title reduced to what a match may turn on: case, punctuation and
    spacing are noise a CMS changes on its own; words are not.

    None for anything that reduces to nothing, INCLUDING an empty or missing
    title — two rows that both lack a title have not been shown to be the same
    row, and the extraction prompt makes a null title the common case
    (ai/prompts.py), so treating null == null as a match would marry unrelated
    listings on almost every page.
    """
    if not title:
        return None
    reduced = _PUNCT.sub(" ", title.strip().casefold()).strip()
    return reduced or None


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
MAX_TITLE_ONLY_RETIME = timedelta(hours=12)

#: The identity a match establishes. These are not degrees of confidence —
#: they are different EVIDENCE, and they license different things.
MATCH_TIME = "time"        #: same start time: the date pins which occurrence
MATCH_TITLE = "title"      #: same title, close enough in time to be the same one
MATCH_FAR = "far"          #: same title, too far away — probably another occurrence


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
        MAX_TITLE_ONLY_RETIME (or the page states no time at all, which cannot
        move anything). A re-time.
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
    if _same_minute(published.start_time, parsed.start_time):
        return MATCH_TIME
    pt, ct = normalize_title(published.title), normalize_title(parsed.title)
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

    MATCH_FAR is deliberately not an identity — see match_kind.
    """
    return match_kind(published, parsed) in (MATCH_TIME, MATCH_TITLE)


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
    needle = normalize_title(title)
    if not needle or not page_text:
        return None
    haystack = _PUNCT.sub(" ", page_text.casefold())
    return f" {needle} " in f" {haystack} "


def _brackets(parsed: Sequence[ParsedListing], start_time: datetime) -> bool:
    """Do the page's own listings reach both sides of this moment?

    The false-absence guard. A page proves it covers a date by listing
    something at or before it and something at or after it; a calendar
    truncated before that date has said nothing about it at all. Listings with
    no start time cannot bracket anything and are ignored here — they still
    count as evidence the page produced listings, just not as evidence about
    when.
    """
    moment = _as_utc(start_time)
    times = [_as_utc(p.start_time) for p in parsed if p.start_time is not None]
    if not times:
        return False
    return any(t <= moment for t in times) and any(t >= moment for t in times)


def _field_diff(
    published: PublishedListing, parsed: ParsedListing
) -> Dict[str, Any]:
    """The updatable fields the page now states DIFFERENTLY.

    Only fields the page actually states: a null from this read is silence, and
    silence never blanks a published value. `status` is absent by construction
    — extraction has no status field (ai/prompts.py), so the only status this
    module can ever write is the confirmed-gone one, from the absence branch.
    """
    diff: Dict[str, Any] = {}
    if parsed.title and normalize_title(parsed.title) != normalize_title(published.title):
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

    for row in published:
        hits = [p for p in parsed if matches(row, p)]

        if len(hits) > 1:
            decisions.append(ListingDecision(
                event_id=row.event_id, action=ACTION_NONE,
                why=(f"{len(hits)} listings on the page match this row on title "
                     "or time — ambiguous; last good row stands")))
            continue

        if not hits:
            if any(match_kind(row, p) == MATCH_FAR for p in parsed):
                # Something on the page carries this row's title, just far away
                # in time — almost always the next occurrence of a recurring
                # listing. That is a reason to say nothing, never to cancel.
                decisions.append(ListingDecision(
                    event_id=row.event_id, action=ACTION_NONE,
                    why=("the page still lists this title, but at a date too "
                         "far off to be the same occurrence — ambiguous; last "
                         "good row stands")))
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
                         and _brackets(parsed, row.start_time))
            if not bracketed or not may_mark_gone(verdict):
                decisions.append(ListingDecision(
                    event_id=row.event_id, action=ACTION_NONE,
                    why=("not on the page, but the page's own listings do not "
                         "reach this date — a short calendar has not said this "
                         "event is gone; last good row stands")))
                continue
            decisions.append(ListingDecision(
                event_id=row.event_id,
                action=ACTION_MARK_GONE,
                why=("absent from a clean parse of the page that defines it, "
                     "its title is absent from the page's own raw text, and "
                     "the page's listings bracket its date — confirmed gone; "
                     f"marked {GONE_STATUS}, row kept with its evidence"),
                fields={"status": GONE_STATUS},
            ))
            continue

        hit = hits[0]
        diff = _field_diff(row, hit)
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
        decisions.append(ListingDecision(
            event_id=row.event_id, action=ACTION_UPDATE, fields=diff,
            matched_candidate_id=hit.candidate_id,
            why=("confirmed same-page change, gate PASS on that listing: "
                 + ", ".join(sorted(diff)))))

    return decisions


# --- reads -------------------------------------------------------------------

_PUBLISHED_ON_PAGE_SQL = """
select distinct e.event_id, e.title, e.start_time, e.end_time, e.status
from event e
join event_candidate c on c.promoted_event_id = e.event_id
where c.source_id = %s
  and c.source_url = %s
  and e.start_time is not null
  and coalesce(e.end_time, e.start_time) > now()
  and e.override_lock = false
  and e.status = 'scheduled'
"""

_PARSED_ON_PAGE_SQL = """
select candidate_id, title, start_time, end_time
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


def _to_published(rows: Sequence[Sequence[Any]]) -> List[PublishedListing]:
    return [PublishedListing(event_id=str(r[0]), title=r[1], start_time=r[2],
                             end_time=r[3], status=r[4]) for r in rows]


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
                          start_time=r[2], end_time=r[3]) for r in rows]


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
    source_class: str,
    page_url: str,
    run_id: str,
    budget=None,
    cur=None,
) -> Dict[str, int]:
    """Write the decisions that mutate. Returns {'updated', 'marked_gone',
    'skipped_budget'}.

    Every write carries its evidence in the same transaction as the change:

      * `candidate_evidence` — the same-page evidence itself, tied to the
        matched candidate, quoting the page and what it now says. Absent for a
        404 (there is no candidate and no page to quote); the audit row carries
        that case.
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
                           source_name=source_name, source_class=source_class,
                           page_url=page_url, run_id=run_id, budget=budget)
            conn.commit()
        return counts
    _write_all(cur, to_write, counts, source_id=source_id,
               source_name=source_name, source_class=source_class,
               page_url=page_url, run_id=run_id, budget=budget)
    return counts


def _write_all(cur, decisions, counts, *, source_id, source_name, source_class,
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
        if d.matched_candidate_id:
            cur.execute(_EVIDENCE_SQL, (
                d.matched_candidate_id, source_class or "venue_calendar",
                source_name, page_url,
                f"re-check {run_id}: {d.why}",
            ))
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
