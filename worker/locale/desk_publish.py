"""publish(desk union) — the two desks stop being a report and become listings.

Founder, this session's ticket: "Take the [two local desks'] walker that already
exists and write candidates + promote into the catalog (same key: night +
place-text + title-or-performer). Single-source rows stay and are labelled. Do
not require a second desk to publish." (The desks are named in the locale pack
and in `tools/desk_ingest.py`, never here: a brand literal in a locale module is
how a locale stops being data — `tests/test_locale_pack.py` greps for exactly
that, and it caught this file's first draft.)

`desk_walk.walk()` reads a desk's whole public list and `desk_union.union()`
folds several of those into one table on the founder's rule. Both stop at a
printed table — the catalog never hears about any of it, which is why the live
site shows one listing while the walk parses thirty-three. This module is the
missing seam: one `UnionRow` in, one candidate write out, in the exact shape
`worker/candidate_store.create_candidate` already takes.

It writes NOTHING itself. It is pure — no DB, no network, no clock — so what
gets published is decided in a function a test can call, and `tools/desk_ingest.py`
does nothing but hand the result to the seams that already exist
(`create_candidate` -> `add_evidence` -> `promote_candidate`). Five rules hold
it to what the desks actually printed:

  * THE DESK'S CLASS COMES FROM THE COMMITTED CATALOG, never from this file.
    A door is matched to its `sources/master_sources_catalog_120.json` row by
    domain, and that row's `category` is the `source_class` the gate will judge
    and its `name` is the label `worker/promote.py` binds onto the public row.
    A door with no catalog row REFUSES to write (`DeskPublishError`) rather
    than publishing an unlabelled listing: the founder asked for the source to
    be labelled, so an unlabelled row is not a lesser version of this ticket,
    it is the wrong artifact. Both desks here are already `local_media`, which
    `worker/gating.py` has promoted on ONE source since the founder's 2026-08-05
    ruling — so "do not require a second desk" needs no gate change, and this
    module deliberately makes none.

  * ONE HAPPENING, ONE ROW, ACROSS RUNS. The write is keyed on the founder's
    own de-dup key (`night~place~title-or-performer`), so the same show read on
    both desks is one candidate carrying two evidence rows, and tomorrow's walk
    finds today's row instead of writing a second one. A row the union could
    not key (no night, or no place) falls back to its OWN address, and only
    then to its desk-local shape WITHOUT the walk ordinal — the ordinal moves
    when the desk reorders its list, so keying on it would mint a fresh
    duplicate on every run.

  * ONLY A CLOCK A DESK STATED — AND THE HOLE MUST READ AS THE RIGHT HOLE.
    `when_precision` must be `datetime`; writing midnight for a date-only row
    would invent the one field this pipeline exists to be honest about. But
    `event` has a single clock column, so every unstated clock becomes the same
    NULL, and the feed renders every NULL as "Date TBA" — one display for three
    very different truths. So the three are separated HERE, before they
    collapse (evaluator PR #229 r3):
      - no desk stated a date -> publish with NULL. "Date TBA" is exactly true.
      - desks state DIFFERENT times -> publish `disputed`. The desks agree it
        is on; they disagree about when, and a reader shown a bare TBA beside
        `confirmed` has been told the clock is merely unknown when it is
        contested. Both instants are passed to the gate as `start_times`
        EVIDENCE rather than resolved here — each ATTRIBUTED to the desk that
        stated it, so the publisher can check every claim against a real
        evidence row before letting it null a clock — and `worker/promote.py`
        finds the conflict itself, writing the label inside the same
        transaction as the insert. That ordering is the point: a walker that promoted and then
        marked the row would leave a window in which a contested listing is
        public and labelled confirmed (evaluator PR #229 r5).
      - a desk stated the NIGHT and no time -> HOLD as a candidate. Publishing
        would say "we do not know the date" about a date we were given, under
        that desk's masthead; manufacturing an absence is the mirror of
        fabricating a fact. The row is in the catalog and in the ops queue, and
        it publishes when the public row can carry a date without a clock
        (R-111).

  * NO FIELD IS INVENTED TO FILL A COLUMN. `artist_names` stays empty — the
    performer this module can derive is a de-dup heuristic over a title, and
    minting artist entities from it would put a guess in the graph. `city` is
    left unstated: these desks name a venue, not a city, and the publish seam
    already applies its own default (`worker/promote.py`), so this module
    asserts nothing it was not told. `ticket_link` stays empty because a
    listing page is not a ticket; the row's own address is passed as
    `listing_url`, which `worker/identity.py` reads as the listing's identity.

  * FIXTURES NEVER REACH A DATABASE. `refuse_fixture_write` raises on a union
    that was not walked LIVE. The founder's "Do not ship fixture titles to
    production" is a Must-not, and a Must-not that depends on remembering to
    pass the right flag is a comment, not a guard.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from worker.locale.desk_union import BASIS_LOCAL, DeskUnion, UnionRow
from worker.locale.pack import Door

#: Written into `extracted` under this key, so every published row can be
#: traced back to the desks, the doors and the key that produced it without
#: reading anything but the candidate itself.
DESK_KEY = "_desk"

#: The mode a union must carry before any of it may be written.
LIVE = "LIVE"


class DeskPublishError(ValueError):
    """The write cannot be planned: a door with no catalog row, or a union that
    was not walked live. Raised, never downgraded into a partial write — a
    listing published without the label the founder asked for is a defect, and
    a fixture title in the catalog is the Must-not.
    """


# --------------------------------------------------------------------------
# Which source is this desk, in the registry the rest of the stack already uses
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class DeskRegistration:
    """One door's row in the committed source catalog.

    `source_name` is matched by `worker/promote.py` against the `source` table
    to fill the public row's provenance columns, so it must be the registry's
    own spelling — this is why the name is READ from the catalog rather than
    taken from the pack's `via` — the two spellings routinely differ (a pack
    naming a paper, a registry naming that paper's events desk), and only the
    registry's own string matches a `source` row and labels the listing.
    """

    door_id: str
    via: str
    source_name: str
    source_class: str
    base_url: str
    catalog_id: str


def _host(url: str) -> str:
    """A url's host, `www.` folded. Nothing else is normalised: the match below
    is a suffix test at a label boundary, so it needs the real labels.
    """
    host = (urlsplit(url or "").hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _same_publisher(door_url: str, base_url: str) -> bool:
    """True when the door is the catalog row's own site.

    Exact host, or the door sits UNDER the registry's host at a label boundary
    (`calendar.example.com` under `example.com` — a paper's calendar commonly
    lives on its own subdomain while the catalog names the paper), or the
    registry row points at a subdomain of the door's host. A label boundary is
    required in both directions so `notexample.com` can never match
    `example.com`, and no public-suffix list is guessed at: a domain we cannot
    match fails loud, which is the safe direction when the consequence is a
    listing labelled with somebody else's masthead.
    """
    door, base = _host(door_url), _host(base_url)
    if not door or not base:
        return False
    return (door == base
            or door.endswith("." + base)
            or base.endswith("." + door))


def registration_for(door: Door, catalog: Sequence[Mapping[str, Any]]) -> DeskRegistration:
    """The catalog row this door belongs to, or raise.

    Ambiguity fails too: two catalog rows claiming one door means the label is
    a coin flip, and this module does not flip coins about whose masthead goes
    on a listing.
    """
    hits = [row for row in catalog
            if _same_publisher(door.url, str(row.get("base_url") or ""))]
    if not hits:
        raise DeskPublishError(
            f"door {door.door_id!r} ({door.url}) matches no row in the committed "
            f"source catalog, so its listings could not be LABELLED with a "
            f"source. Add the publisher to sources/master_sources_catalog_120.json "
            f"(name + base_url + category) before walking it into the catalog.")
    if len(hits) > 1:
        names = sorted(str(r.get("name")) for r in hits)
        raise DeskPublishError(
            f"door {door.door_id!r} ({door.url}) matches {len(hits)} catalog "
            f"rows ({names}) — the source label would be a guess. Narrow the "
            f"base_url of the rows that do not own this door.")
    row = hits[0]
    source_class = str(row.get("category") or row.get("source_type") or "").strip()
    name = str(row.get("name") or "").strip()
    if not source_class or not name:
        raise DeskPublishError(
            f"catalog row {row.get('id')!r} for door {door.door_id!r} is missing "
            f"a name or a category; the gate reads the category as evidence "
            f"strength and promote.py reads the name as the public label.")
    return DeskRegistration(
        door_id=door.door_id,
        via=door.via or name,
        source_name=name,
        source_class=source_class,
        base_url=str(row.get("base_url") or ""),
        catalog_id=str(row.get("id") or ""),
    )


# --------------------------------------------------------------------------
# The write, planned
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Evidence:
    """One desk's statement that this happening exists. One row per desk, which
    is what makes a two-desk row provably corroborated in the store even though
    neither desk needed the other to publish.
    """

    source_class: str
    source_name: str
    source_url: str
    quote: str


@dataclass
class CandidateWrite:
    """Everything one union row needs to become a candidate and, if the gate
    passes it, a listing. The field names are `create_candidate`'s, so the
    caller does no translating (and no field can be quietly renamed here
    without the caller failing loudly).
    """

    ingest_key: str
    source_name: str
    source_class: str
    source_url: str
    raw_text: str
    extracted: Dict[str, Any]
    evidence: List[Evidence] = field(default_factory=list)
    #: Every desk that printed this row, first-seen order — the labelling the
    #: founder asked for, kept beside the single `source_name` the public
    #: `event` row has room for.
    vias: Tuple[str, ...] = ()
    #: Why the clock is NULL, when it is. Printed by the tool so a "Date TBA"
    #: listing is never mistaken for a parser that failed silently.
    clock_hole: Optional[str] = None
    #: Set when the desks state DIFFERENT times for this one happening. The row
    #: publishes — the desks agree it is ON — but its confidence is `disputed`,
    #: because a reader shown a bare "Date TBA" beside a `confirmed` label has
    #: been told the clock is merely unknown when it is actually contested
    #: (evaluator PR #229 r3, openai/attacker-smuggle).
    clock_disputed: bool = False
    #: Set when the desk stated a NIGHT and no time. Such a row is written as a
    #: candidate and NOT published, because `event` has one clock column and a
    #: NULL in it renders publicly as "Date TBA" — which would say "we do not
    #: know the date" about a date the desk gave us, on the surface a reader
    #: uses to decide whether to go. Manufacturing that absence is the mirror
    #: of fabricating a fact, and it wears the desk's masthead. R-111.
    hold_reason: Optional[str] = None

    @property
    def title(self) -> str:
        return str(self.extracted.get("title") or "")

    @property
    def start_time(self) -> Optional[str]:
        return self.extracted.get("start_time")

    @property
    def single_desk(self) -> bool:
        return len(self.vias) < 2


def _instant(stated: str):
    """One stated time as a comparable INSTANT, or None when it will not parse.

    Two desks can state the same moment in different forms —
    `2026-09-13T01:00:00Z` and `2026-09-12T20:00:00-05:00` are one instant
    written two ways — so comparing the STRINGS finds a disagreement that does
    not exist and loses a time both desks agreed on (evaluator PR #229 r8).
    A naive value is left naive rather than being assigned a timezone we were
    not given; it can then only equal another naive value, which is the safe
    direction for a comparison whose false YES costs a real clock.
    """
    try:
        return datetime.fromisoformat(stated)
    except (TypeError, ValueError):
        return None


def _stated_clocks(row: UnionRow) -> List[str]:
    """The DISTINCT instants this row's desks stated, in first-seen order.

    Only `datetime` precision counts. A `date` row states a night; the union
    already keys on that night, and turning it into 00:00 would be an invented
    time on a public listing.

    Distinctness is by INSTANT, not by string: the first form of each moment is
    the one kept, and a second desk writing that same moment differently adds
    nothing. An unparseable value keeps its own text as its identity rather
    than collapsing into the parsed ones — the same rule
    `worker/trust_gate3.start_time_claims` applies one layer down.
    """
    out: List[str] = []
    seen = []
    for member in row.members:
        if not (member.row.when and member.row.when_precision == "datetime"):
            continue
        moment = _instant(member.row.when)
        key = moment if moment is not None else f"unparseable:{member.row.when}"
        if key not in seen:
            seen.append(key)
            out.append(member.row.when)
    return out


def _listing_url(row: UnionRow) -> Optional[str]:
    for member in row.members:
        if member.row.listing_url:
            return member.row.listing_url
    return None


def ingest_key(row: UnionRow) -> str:
    """The handle a re-run finds this row by.

    The union key when the row HAS one — that is the founder's rule, and it is
    the same string whether the row came off one desk or both, which is exactly
    what stops a second desk from doubling the catalog. A row the union could
    not key falls back to its own address, and only then to its desk-local
    shape with the walk ORDINAL STRIPPED: the ordinal is a position in a list
    that reorders between runs, so a key carrying it would write a new row
    every night for the same untitled, undated listing.
    """
    if row.basis != BASIS_LOCAL:
        return row.key
    url = _listing_url(row)
    if url:
        return f"url:{url}"
    member = row.members[0]
    return f"desk:{member.via}~{member.place}~{member.title_key}"


#: Fields whose change means the desk now says something DIFFERENT about this
#: happening than the row we published. These, and only these, put the
#: published row's confidence in question.
CONTRADICTING = ("title", "place", "night", "clocks", "listing_url")

#: Fields whose change is not a contradiction. `vias` grows when a SECOND desk
#: starts carrying a row the first one already gave us — that is more agreement,
#: not less, and marking the row `disputed` for it would show a reader stronger
#: corroboration as a dispute (evaluator PR #229 r6). It shrinks when a desk
#: stops listing something, which is an ABSENCE — and absence is the one
#: evidence shape a short page can manufacture, so it is never read as a
#: contradiction either (the same rule `worker/listing_update.py` calls its
#: false-absence guard). Either way it is worth RECORDING, which is why it is
#: still watched.
CORROBORATING = ("vias",)

#: The fields of a desk's statement a re-run compares. Named as data rather
#: than compared field-by-field in a function body, so a field added to the
#: statement without a decision about what its CHANGING means is a visible
#: omission rather than a silently unwatched value.
WATCHED = CONTRADICTING + CORROBORATING


def _statement(row: UnionRow, clocks: List[str], listing_url: Optional[str]) -> Dict[str, Any]:
    """What the desk said about this happening, in comparable form.

    The founder's key answers "is this the same happening?". It deliberately
    cannot answer "is the desk still saying the same THING about it?" — a desk
    that corrects 8pm to 9:30pm on the same night keys identically, which is
    correct for de-duplication and wrong for a re-run that skips on the key
    alone. This is the second question's evidence, stored beside the first.
    """
    return {
        "title": row.title,
        "place": row.place_text,
        "night": row.night,
        "clocks": list(clocks),
        "listing_url": listing_url,
        "vias": list(row.vias),
    }


def drift(stored: Optional[Mapping[str, Any]], fresh: Mapping[str, Any]) -> List[str]:
    """Which watched fields the desk has changed since we published, in order.

    An ABSENT stored statement returns no drift, and that is deliberate rather
    than lenient: rows written before this field existed have nothing to
    compare against, and inventing a difference from a hole would report every
    one of them as changed on the next run. They are reported as ordinary
    skips, exactly as they were, and acquire a statement the first time the
    desk actually changes something about them.
    """
    if not stored:
        return []
    return [field for field in WATCHED if stored.get(field) != fresh.get(field)]


def contradicts(stored: Optional[Mapping[str, Any]],
                fresh: Mapping[str, Any]) -> List[str]:
    """Which of the changed fields actually CONTRADICT the published row.

    A re-run asks two different questions and they must not share an answer:
    "has anything changed?" (`drift`, which decides whether to record the
    desk's new word) and "does the desk now disagree with what we published?"
    (this, which decides whether the published row may still read `confirmed`).
    A second desk picking up a row the first already gave us changes `vias` and
    contradicts nothing — disputing on it would show a reader MORE agreement as
    a dispute.
    """
    return [f for f in drift(stored, fresh) if f in CONTRADICTING]


def describe_drift(stored: Mapping[str, Any], fresh: Mapping[str, Any],
                   fields: Sequence[str]) -> str:
    """The change in the desk's own values, for a report a person reads."""
    return "; ".join(
        f"{f}: {stored.get(f)!r} -> {fresh.get(f)!r}" for f in fields)


def _quote(row: UnionRow, member) -> str:
    """What this desk printed, in its own words. Stored as the evidence quote so
    an audit reads the desk's line, not our summary of it.
    """
    parts = [member.row.title or "(untitled)"]
    if member.row.when_text:
        parts.append(member.row.when_text)
    if member.row.place_text:
        parts.append(member.row.place_text)
    return " — ".join(parts)[:500]


def write_for(row: UnionRow, registrations: Mapping[str, DeskRegistration],
              *, mode: str) -> CandidateWrite:
    """One union row as a candidate write.

    The candidate's own `source_name`/`source_class` are the FIRST desk that
    printed it (the union's own display order). Every desk gets an evidence
    row, so the store holds all of them; the public `event` row has one
    provenance column pair (migration 0020) and it carries the first desk.
    """
    vias = row.vias
    first = registrations.get(vias[0]) if vias else None
    if first is None:
        raise DeskPublishError(
            f"row {row.key!r} came from desk {vias[0]!r} with no registration — "
            f"every walked door must resolve to a catalog row before any of "
            f"its rows are written.")

    clocks = _stated_clocks(row)
    clock_hole: Optional[str] = None
    clock_disputed = False
    hold_reason: Optional[str] = None
    start_time: Optional[str] = None
    if len(clocks) == 1:
        start_time = clocks[0]
    elif len(clocks) > 1:
        # Two desks, two clocks, one show. ONE-LIVE-TRUST.md: the disagreement
        # is a hole on the FIELD, never a reason to withhold the listing — and
        # never a tiebreak, because neither desk is the venue.
        #
        # But a NULL clock renders as "Date TBA", which reads as "nobody said",
        # and here somebody said twice. So the listing publishes and its
        # confidence is `disputed` — the state the four-state model has for
        # evidence that no longer agrees with itself, shown never hidden. The
        # existence is not in doubt; the clock is.
        clock_hole = (f"{len(clocks)} desks state different times for this "
                      f"happening: {', '.join(clocks)}")
        clock_disputed = True
    elif row.night:
        # THE DESK GAVE US THE NIGHT. `event` has one clock column, so the only
        # way to publish this row is with a NULL that the feed renders as "Date
        # TBA" — telling a reader we do not know a date we were given, under
        # this desk's masthead. Manufacturing an absence is the mirror image of
        # fabricating a fact, so the row is HELD as a candidate instead: it is
        # in the catalog, auditable and in the ops queue, and it publishes the
        # day the public model can say "this night, time not stated" (R-111).
        clock_hole = "the desk stated a night, not a time"
        hold_reason = (
            f"the desk stated the night ({row.night}) and no time; publishing "
            f"would render as 'Date TBA' and hide a date we were given — held "
            f"until the public row can carry a date without a clock (R-111)")
    else:
        clock_hole = "no desk stated a date for this row"

    listing_url = _listing_url(row)
    desk_note = {
        "key": ingest_key(row),
        "union_key": row.key,
        "basis": row.basis,
        "night": row.night,
        "vias": list(vias),
        "doors": sorted({m.row.door_id for m in row.members}),
        "kind": row.kind,
        "kind_source": row.kind_source,
        "titles": list(row.titles),
        "clocks_stated": clocks,
        "clock_hole": clock_hole,
        "clock_disputed": clock_disputed,
        "held": hold_reason,
        "walk_mode": mode,
        # What the desk SAID, kept so a later walk can tell "we already have
        # this" from "we already have this and the desk has since changed its
        # mind". Without it the key alone answers only the first question —
        # see `statement()`.
        "statement": _statement(row, clocks, listing_url),
    }
    extracted: Dict[str, Any] = {
        "title": row.title,
        "start_time": start_time,
        "end_time": None,
        "venue_name": row.place_text,
        # Deliberately unstated: a desk names a venue, not a city. The publish
        # seam applies its own default rather than this module asserting one.
        "city": None,
        "artist_names": [],
        "ticket_link": None,
        "rsvp_link": None,
        "is_private_rsvp": False,
        "private_access": {},
        DESK_KEY: desk_note,
    }
    if clock_disputed:
        # STATED AS EVIDENCE, NOT RESOLVED INTO A VALUE. `start_time` above is
        # the hole we publish; this is what we were actually told, and it is
        # what lets `evaluate_gate` find the conflict for itself and publish
        # the row `disputed` inside the same transaction as the insert. Without
        # it the walker would have to mark the row afterwards, which leaves a
        # window where a contested listing is public and labelled `confirmed`
        # (evaluator PR #229 r5).
        #
        # EACH CLAIM NAMES ITS SOURCE (evaluator PR #229 r6/r7). A bare list of
        # instants says "these were claimed" and nothing about BY WHOM, so the
        # publisher could only count evidence rows and hope the two matched. A
        # claim is attributed here, to the registry name the evidence row is
        # written under, and `worker/promote.py` keeps only the claims whose
        # source actually has one — so a conflict has to be sourced twice over
        # before it can null a real clock and stamp a row `disputed`.
        extracted["start_times"] = [
            {"source": registrations[m.via].source_name, "at": m.row.when}
            for m in row.members
            if m.row.when and m.row.when_precision == "datetime"
            and m.via in registrations
        ]
    if listing_url:
        # Read by worker/identity.py as this listing's own identity — the
        # strongest handle a later source can match against. Not a ticket link.
        extracted["listing_url"] = listing_url

    raw_lines = [f"{m.via}: {_quote(row, m)}" for m in row.members]
    raw_lines.append(f"[1Live desk walk — key {desk_note['key']}]")

    evidence = []
    for member in row.members:
        reg = registrations.get(member.via)
        if reg is None:
            raise DeskPublishError(
                f"row {row.key!r} carries desk {member.via!r} with no "
                f"registration — its evidence could not name a source class.")
        evidence.append(Evidence(
            source_class=reg.source_class,
            source_name=reg.source_name,
            source_url=member.row.listing_url or member.row.source_url,
            quote=_quote(row, member),
        ))

    return CandidateWrite(
        ingest_key=desk_note["key"],
        source_name=first.source_name,
        source_class=first.source_class,
        source_url=row.members[0].row.source_url,
        raw_text="\n".join(raw_lines),
        extracted=extracted,
        evidence=evidence,
        vias=vias,
        clock_hole=clock_hole,
        clock_disputed=clock_disputed,
        hold_reason=hold_reason,
    )


def refuse_fixture_write(one: DeskUnion) -> None:
    """Raise unless this union came off the live desks.

    Founder Must-not, this session: "Do not ship fixture titles to production."
    The committed fixtures say "Fixture Quartet at the Shape Hall", and a
    catalog holding that is worse than an empty one — it is a lie a friend can
    read. Enforced here, at the only function every write path passes through,
    rather than by a flag a caller must remember.
    """
    if one.mode != LIVE:
        raise DeskPublishError(
            f"refusing to write a {one.mode} union to a database: fixture "
            f"titles must never reach the catalog. Walk the live desks "
            f"(--real) on a machine with egress, or use --dry-run to print "
            f"the plan.")


def plan(one: DeskUnion, registrations: Mapping[str, DeskRegistration]) -> List[CandidateWrite]:
    """Every row of the union as a candidate write, in the union's own order.

    A desk that could not be READ contributes nothing here and that is not a
    silence: `desk_union` already carries its blocked pages and the tool prints
    them. A blocked desk writing zero rows is a blocked desk, never an empty
    one — nothing in this module ever turns an unread list into a deletion,
    because nothing in this module deletes.
    """
    return [write_for(row, registrations, mode=one.mode) for row in one.rows]


def plan_digest(writes: Sequence[CandidateWrite]) -> Dict[str, Any]:
    """Counts a report can print without recomputing them from the table."""
    held = sum(1 for w in writes if w.hold_reason)
    return {
        "rows": len(writes),
        "timed": sum(1 for w in writes if w.start_time),
        "clock_holes": sum(1 for w in writes if w.clock_hole),
        # The three shapes a clock hole takes, counted apart, because they
        # reach a reader as three different things (evaluator PR #229 r3) and
        # a summary that adds them up would be the prose-restates-computation
        # defect this ledger has recorded twice.
        "held": held,
        "clock_disputed": sum(1 for w in writes if w.clock_disputed),
        "publishable": len(writes) - held,
        "single_desk": sum(1 for w in writes if w.single_desk),
        "multi_desk": sum(1 for w in writes if not w.single_desk),
        "by_source": _by_source(writes),
    }


def _by_source(writes: Sequence[CandidateWrite]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for w in writes:
        for via in w.vias:
            out[via] = out.get(via, 0) + 1
    return dict(sorted(out.items()))


def extracted_json(write: CandidateWrite) -> str:
    """The payload as it will be stored, for a dry run to print verbatim."""
    return json.dumps(write.extracted, sort_keys=True, default=str)
