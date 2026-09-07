"""Gather — one bounded pipe per canonical place, started by demand.

Locale Launch Law §2 splits the product in two. SHOW is instant and reads what
we already hold. GATHER is "a job, not a page view": a typed place is a TRIGGER
to run the pipe once, inside a finite tick, and to leave a pack behind so the
next person in that place is instant.

This module is the JOB. It writes no parser, no de-dup rule and no write rule —
all of that already exists and is audited elsewhere:

    resolve            this module — place text -> place_id, clock, grammar
    propose doors      this module — pack doors + LEADS, graded before contact
    classify A-F       worker.sourcing.source_class
    walk               worker.locale.desk_walk      (pages, walls, mash refusal)
    split identities   worker.locale.desk_read      (via the walk)
    union              worker.locale.desk_union     (night+place+title)
    plan the write     worker.locale.desk_publish   (title+when+place or HOLD)

What is new here, and only here, is the four things a JOB has that a walk does
not:

1. A CANONICAL PLACE ID. `Miami, FL` and `miami fl` are one job; §6a's "Miami FL
   != Miami OH" is preserved because the state is part of what the person typed
   and therefore part of the id. Two spellings of one place must not run two
   pipes; two places that merely share a first word must not share one.
2. A TICK with three bounds — pages, wall-clock, dollars — that stops on the
   FIRST one spent. An unbounded gather is the crawl §6 forbids.
3. SINGLE FLIGHT. §6a: "Gather is a single-flight job keyed by canonical
   place_id. Concurrent visitors attach to the job that is already running."
   The second visitor waits on the first job's result; it does not start a
   second pipe, and it does not start from zero.
4. A REFUSED TRIGGER. §6a: "Page load MUST NOT start a crawl, extract, or
   gather." That is enforced as a value error on the trigger, not as a comment,
   so a caller that wires gather to a page render fails loudly at the first
   request rather than quietly at the first invoice.

LEADS ARE NOT LISTINGS. §2 step 2: "A search hit is a LEAD. It is not a
listing." A `Lead` here is a URL and the query that surfaced it. It carries no
title, no date and no venue, so there is no assignment anywhere in this package
that could turn a search snippet into a row — the only thing a lead can become
is a `Door` graded `found_unverified`, which then has to survive classification,
`readable`, a catalog masthead, a real fetch and the split before any row of it
exists. The snippet itself reaches nothing.

NO PLACE IS NAMED HERE. Locale Launch §5: "If Austin (or any place) is named in
code, the ticket failed." This module knows the SHAPE of a place and nothing
about any particular one: every door, phrasing, kind and clock comes from a pack
file or from what the person typed. The thin grammar below names no town, and a
place with no pack gets the same pipe with a smaller vocabulary.

Pure: stdlib only. No network (the fetcher is injected), no DB, no import from
the promote path.
"""
from __future__ import annotations

import threading
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from worker.locale.desk_publish import (
    DeskPublishError,
    DeskRegistration,
    plan,
    plan_digest,
    registration_for,
)
from worker.locale.desk_union import DeskUnion, union
from worker.locale.desk_walk import DeskWalk, PageFetch, walk
from worker.locale.pack import (
    Door,
    LocalePack,
    LocalePackError,
    available_locales,
    load_pack,
)
from worker.sourcing.source_class import (
    CLASS_A_STRUCTURED_OPEN,
    CLASS_B_PUBLIC_HTML,
    CLASS_D_CLOSED_DOOR,
    ClassVerdict,
    classify_entry,
)


class GatherError(ValueError):
    """The job cannot run as asked. Always raised: a gather that half-starts
    would report a short list as this place's night.
    """


class GatherRefused(GatherError):
    """The job may not run from this trigger at all (Locale Launch §6a)."""


# --------------------------------------------------------------------------
# 1. The canonical place id
# --------------------------------------------------------------------------

#: Triggers that MAY start a gather. Demand starts gather (§2); a scheduler
#: refreshes what demand already opened (§6a).
TRIGGERS: Tuple[str, ...] = ("typed_place", "opted_in_here", "url_place", "scheduler")

#: The one trigger that is refused by name, because it is the one a careless
#: wiring reaches for: rendering a page must never open a socket at a desk.
PAGE_LOAD = "page_load"


def assert_trigger(trigger: str) -> str:
    """The trigger, or raise. `page_load` gets its own message because it is the
    mistake the law names (§6a: "Page load is Show: catalog + cache").
    """
    if trigger == PAGE_LOAD:
        raise GatherRefused(
            "page load must not start a gather (Locale Launch §6a). A page load "
            "is SHOW: serve the catalog and the cache, and say we are gathering "
            "if it is thin. Start the job from a typed place, an opted-in here, "
            "a ?place= URL, or the refresh scheduler.")
    if trigger not in TRIGGERS:
        raise GatherRefused(
            f"unknown gather trigger {trigger!r} — known triggers are {TRIGGERS}. "
            f"An unknown trigger fails closed rather than defaulting to one that "
            f"is allowed.")
    return trigger


def canonical_place_id(text: str) -> str:
    """The stable id for a typed place: lowercase, unaccented, hyphen-joined.

    Two SPELLINGS of one place collapse ("Miami, FL" / "  miami   fl ") so the
    second visitor attaches to the first visitor's job. Two DIFFERENT places
    never collapse, because everything the person typed survives into the id —
    a state, a county or a country stays part of the key, which is how §6a's
    "ambiguous names are different places" holds without this module keeping a
    gazetteer of ambiguous names.

    Raises on an empty or punctuation-only place: an id of "" would be one
    global job that every visitor attaches to.
    """
    if not isinstance(text, str):
        raise GatherError(f"a place is typed text, got {type(text).__name__}")
    folded = unicodedata.normalize("NFKD", text)
    kept = "".join(
        ch.lower() if (ch.isalnum() and not unicodedata.combining(ch)) else " "
        for ch in folded
    )
    parts = [p for p in kept.split() if p]
    if not parts:
        raise GatherError(
            f"{text!r} names no place: a blank place id would make one job that "
            f"every visitor in the world attaches to")
    return "-".join(parts)


# --------------------------------------------------------------------------
# 2. Resolve — clock + query grammar, from a pack or thin
# --------------------------------------------------------------------------

#: The thin grammar (§3: "No pack yet: thin gather is still allowed"). It names
#: DOOR SHAPES a place tends to have — the civic desk, the library, the campus,
#: the local paper — and no town, no brand and no category weighting. `{place}`
#: is filled with what the person typed, verbatim, because their own words are
#: the only place-string this module is entitled to.
THIN_TEMPLATES: Tuple[str, ...] = (
    "{place} events calendar",
    "{place} city calendar",
    "things to do in {place} this week",
    "{place} public library events",
    "{place} university events calendar",
    "{place} downtown association events",
)

#: What a resolve is standing on, printed in every report so a thin run is never
#: mistaken for a compiled one.
GRAMMAR_PACK = "pack"
GRAMMAR_THIN = "thin"


@dataclass(frozen=True)
class Grammar:
    """The bounded query grammar for one place (§2 step 1)."""

    templates: Tuple[str, ...]
    places: Tuple[str, ...]
    kinds: Tuple[str, ...]
    source: str

    def queries(self) -> Tuple[str, ...]:
        """Template x place x kind, de-duplicated, deterministic order.

        Bounded by construction: the caller can count the queries before it
        spends anything, which is what makes "a bounded query grammar" a bound
        rather than an adjective.
        """
        out: List[str] = []
        seen = set()
        for template in self.templates:
            needs_kind = "{kind}" in template
            for place in self.places:
                for kind in (self.kinds if needs_kind else ("",)):
                    q = template.replace("{place}", place).replace("{kind}", kind)
                    q = " ".join(q.split())
                    if q and q not in seen:
                        seen.add(q)
                        out.append(q)
        return tuple(out)


@dataclass(frozen=True)
class Resolved:
    """A place, resolved as far as the data allows.

    `timezone_id` is Optional on purpose. A pack states its clock; a place with
    no pack has none until a geocode supplies one, and this module will not
    guess — a guessed clock puts rows on the wrong night, and the night is half
    the union's key. The job HOLDS on a missing clock instead (`no_timezone`).
    """

    place_id: str
    display: str
    timezone_id: Optional[str]
    grammar: Grammar
    doors: Tuple[Door, ...]
    pack_id: Optional[str]

    @property
    def has_pack(self) -> bool:
        return self.pack_id is not None


def _pack_place_ids(pack: LocalePack) -> Tuple[str, ...]:
    """Every place id this pack answers to: its own locale id, its label, and
    every place in its grammar. All canonicalised, so the match is the same
    normalisation the job key uses and cannot drift from it.
    """
    out: List[str] = []
    for raw in (pack.locale_id, pack.label, *(pack.query_grammar.get("places") or ())):
        if not isinstance(raw, str) or not raw.strip():
            continue
        try:
            pid = canonical_place_id(raw)
        except GatherError:
            continue
        if pid not in out:
            out.append(pid)
    return tuple(out)


def resolve(place_text: str, *, packs_dir: Optional[str] = None,
            timezone_id: Optional[str] = None) -> Resolved:
    """Resolve typed text to an id, a clock, a grammar and a door list.

    A pack that already covers the place is CACHE (§3): its clock, phrasings and
    doors are reused and nothing is rediscovered. No pack means a thin resolve,
    which is a smaller grammar and an empty door list — the doors then have to
    come from leads the caller proposes.

    `timezone_id` is the caller's geocode answer. A pack's own clock wins over
    it, because the pack is the compiled statement about that place.
    """
    place_id = canonical_place_id(place_text)
    display = " ".join(place_text.split())

    for locale_id in available_locales(packs_dir=packs_dir):
        try:
            pack = load_pack(locale_id, packs_dir=packs_dir)
        except LocalePackError:
            # A malformed pack is that pack's defect and is reported by its own
            # loader and its own test. It must not decide the fate of a place it
            # may not even cover, so resolve moves to the next file.
            continue
        if place_id not in _pack_place_ids(pack):
            continue
        return Resolved(
            place_id=place_id,
            display=display,
            timezone_id=pack.timezone or timezone_id,
            grammar=Grammar(
                templates=tuple(pack.query_grammar.get("templates") or ()),
                places=tuple(pack.query_grammar.get("places") or ()),
                kinds=pack.kinds,
                source=GRAMMAR_PACK,
            ),
            doors=pack.doors,
            pack_id=pack.locale_id,
        )

    return Resolved(
        place_id=place_id,
        display=display,
        timezone_id=timezone_id,
        grammar=Grammar(templates=THIN_TEMPLATES, places=(display,), kinds=(),
                        source=GRAMMAR_THIN),
        doors=(),
        pack_id=None,
    )


# --------------------------------------------------------------------------
# 3. Leads — a search hit is a door proposal, never a row
# --------------------------------------------------------------------------

#: The only thing a URL declares about itself without anybody reading it: its
#: registry suffix. `.gov` is a government body by registration, `.edu` an
#: accredited institution. That is a fact about the REGISTRY, not an inference
#: about the page, which is why it is allowed to set a door type. Everything
#: else is `junk` — the pack doctrine's "lead only, never a listing" — and a
#: `junk` door is not listable, so `Door.readable` is False and `walk()` refuses
#: it. A lead only becomes walkable when a pack or a person states its type.
DOOR_TYPE_BY_SUFFIX: Mapping[str, str] = {
    ".gov": "civic",
    ".mil": "civic",
    ".edu": "official_list",
}

LEAD_ONLY_DOOR_TYPE = "junk"


@dataclass(frozen=True)
class Lead:
    """One search hit: the query that surfaced it and the URL it points at.

    Deliberately narrow. There is no `title`, no `when`, no `place` and no
    `snippet` field on this type, so no code path in this package can copy a
    search result's words into a happening. Locale Launch §2: a search hit is a
    lead. The only door out of this dataclass is `lead_door`, and it carries the
    URL alone.
    """

    query: str
    url: str
    note: str = ""


def _host(url: str) -> str:
    rest = url.split("://", 1)[-1]
    return rest.split("/", 1)[0].split("@")[-1].split(":")[0].strip().lower()


def _suffix_door_type(host: str) -> str:
    for suffix, door_type in DOOR_TYPE_BY_SUFFIX.items():
        # Whole label, never a substring: `notagov.com` must not read as `.gov`.
        if host.endswith(suffix) or f"{suffix}." in host:
            return door_type
    return LEAD_ONLY_DOOR_TYPE


def lead_door(lead: Lead, *, place_id: str, door_type: Optional[str] = None) -> Door:
    """Propose a lead as a DOOR, graded honestly.

    `evidence="found_unverified"` is the pack's own word for "a URL named from a
    consumer query but never fetched", so a proposed door can never be presented
    as one we read. The type is the registry's answer unless a caller states a
    better one; an unstated type is `junk`, which is not listable and therefore
    not walkable.
    """
    if not isinstance(lead, Lead):
        raise GatherError(f"lead_door() takes a Lead, got {type(lead).__name__}")
    host = _host(lead.url)
    if not host:
        raise GatherError(f"lead {lead.url!r} names no host, so it names no door")
    resolved_type = door_type or _suffix_door_type(host)
    return Door(
        door_id=f"lead-{place_id}-{host}",
        brand=host,
        via=host,
        door_type=resolved_type,
        url=lead.url,
        public=True,
        intake="html",
        kind_scope=(),
        covers=(place_id,),
        blocked_reason=None,
        evidence="found_unverified",
        locale_id=place_id,
    )


# --------------------------------------------------------------------------
# 4. Classify A-F before contact
# --------------------------------------------------------------------------

def door_class(door: Door, catalog: Sequence[Mapping[str, Any]] = ()) -> ClassVerdict:
    """Grade one door A-F BEFORE anything is fetched (§2 step 3).

    A vetted catalog row wins: that is a declared access posture somebody
    reviewed, and `classify_entry` is the one implementation of the Coverage Law
    letters. With no catalog row the grade comes off the door's own declaration
    in the pack — never off the page, which we have not read.
    """
    host = _host(door.url)
    for entry in catalog or ():
        base = _host(str(entry.get("base_url") or ""))
        if base and (host == base or host.endswith("." + base) or base.endswith("." + host)):
            return classify_entry(dict(entry))

    if not door.public:
        return ClassVerdict(
            CLASS_D_CLOSED_DOOR,
            f"pack declares this door closed — {door.blocked_reason or 'no reason stated'}",
            fetchable=False)
    if door.intake == "none":
        return ClassVerdict(
            CLASS_D_CLOSED_DOOR, "pack declares no read path (intake=none)",
            fetchable=False)
    if door.intake in ("ics", "json_ld", "rss", "api"):
        return ClassVerdict(
            CLASS_A_STRUCTURED_OPEN, f"pack declares an open feed (intake={door.intake})",
            fetchable=True)
    return ClassVerdict(
        CLASS_B_PUBLIC_HTML, f"pack declares public html (intake={door.intake})",
        fetchable=True)


# --------------------------------------------------------------------------
# 5. The tick — three bounds, stop on the first one spent
# --------------------------------------------------------------------------

#: The bounds, in the order the tick reports them when more than one is spent.
BOUNDS: Tuple[str, ...] = ("pages", "wall_clock", "dollars")


@dataclass
class Tick:
    """One finite tick: pages, wall-clock, dollars (§6).

    Every bound is required and must be positive. There is no "unbounded" value
    and no default that stands in for one, because §6's whole point is that a
    gather is finite before it starts, not finite because somebody watched it.

    `clock` is injected so a test can spend wall-clock without sleeping.
    """

    max_pages: int
    max_seconds: float
    max_dollars: float
    clock: Callable[[], float] = time.monotonic
    pages_used: int = 0
    dollars_used: float = 0.0
    started_at: Optional[float] = None
    stopped_because: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.max_pages, int) or self.max_pages < 1:
            raise GatherError(
                f"max_pages must be a positive int, got {self.max_pages!r} — a "
                f"gather with no page bound is the unbounded crawl the law bans")
        for name in ("max_seconds", "max_dollars"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or value <= 0:
                raise GatherError(f"{name} must be a positive number, got {value!r}")

    def start(self) -> "Tick":
        self.started_at = self.clock()
        return self

    @property
    def seconds_used(self) -> float:
        if self.started_at is None:
            return 0.0
        return max(0.0, self.clock() - self.started_at)

    @property
    def pages_left(self) -> int:
        return max(0, self.max_pages - self.pages_used)

    def spend(self, dollars: float) -> None:
        if dollars < 0:
            raise GatherError("a tick cannot un-spend money")
        self.dollars_used += dollars

    def bound(self) -> Optional[str]:
        """The first bound that is spent, or None. Checked in `BOUNDS` order so
        two runs that hit the same wall report the same word.
        """
        if self.pages_used >= self.max_pages:
            return "pages"
        if self.seconds_used >= self.max_seconds:
            return "wall_clock"
        if self.dollars_used >= self.max_dollars:
            return "dollars"
        return None

    def stop_when(self) -> Callable[[], Optional[str]]:
        """The hook `desk_walk.walk` calls before opening each page.

        Pages are bounded by handing the walk its own `max_pages`, so this hook
        answers for the two bounds a page cap cannot see: time and money.
        """
        def _stop() -> Optional[str]:
            if self.seconds_used >= self.max_seconds:
                return "wall_clock"
            if self.dollars_used >= self.max_dollars:
                return "dollars"
            return None
        return _stop

    def note_stop(self, reason: str) -> None:
        """Record the first bound that stopped the job, and only the first."""
        if self.stopped_because is None:
            self.stopped_because = reason


# --------------------------------------------------------------------------
# 6. The report — what one tick found, and what it could not see
# --------------------------------------------------------------------------

#: The honest states a gather may end in. `EMPTY` is deliberately absent: a
#: gather never reports "nothing on here". It reports what it read and what it
#: could not (§2: "never '0 events in this city' as if we finished reading it").
STATE_GATHERED = "gathered"
STATE_GATHERING = "gathering"
STATE_UNKNOWN = "unknown"
STATE_HELD = "held"


@dataclass
class DoorSkip:
    """One door this tick did not walk, by name, with the reason and remedy."""

    door_id: str
    door_type: str
    source_class: str
    why: str


@dataclass
class GatherReport:
    """One tick's whole result: the go-live numbers, plus every hole."""

    place_id: str
    display: str
    trigger: str
    pack_id: Optional[str]
    grammar_source: str
    timezone_id: Optional[str]
    queries: Tuple[str, ...] = ()
    leads_n: int = 0
    doors_n: int = 0
    walks: List[DeskWalk] = field(default_factory=list)
    skipped: List[DoorSkip] = field(default_factory=list)
    one: Optional[DeskUnion] = None
    digest: Dict[str, Any] = field(default_factory=dict)
    stopped_because: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    held_reason: Optional[str] = None

    # --- the five numbers the go-live checklist reads (§4 step 5) ---
    @property
    def rows_n(self) -> int:
        return len(self.one.rows) if self.one else 0

    @property
    def dated_n(self) -> int:
        return int(self.digest.get("dated", 0))

    @property
    def placed_n(self) -> int:
        return int(self.digest.get("placed", 0))

    @property
    def mash_n(self) -> int:
        """List URLs standing in for a row's own address, summed over the walks.

        Read off the walks themselves, never off a counter this module keeps,
        so "mash_n = 0" stays a measurement of the output.
        """
        return sum(w.mash_n for w in self.walks)

    @property
    def walls_n(self) -> int:
        """Pages that hit a wall. The number that must never be read as a zero
        list (Operating Law, effectiveness rule 4)."""
        return sum(w.walled_n for w in self.walks)

    @property
    def held_n(self) -> int:
        """Rows planned but held off the default view for a missing title, when
        or place (§2 step 5)."""
        return int(self.digest.get("held", 0))

    @property
    def publishable_n(self) -> int:
        return int(self.digest.get("publishable", 0))

    @property
    def unknown_desks(self) -> Tuple[str, ...]:
        """Desks whose list we could not read at all. Their contribution is
        UNKNOWN, never empty."""
        return tuple(w.door_id for w in self.walks if w.pages_read == 0)

    @property
    def complete(self) -> bool:
        """True only when every desk opened and every desk ran out of list."""
        return bool(self.walks) and all(
            w.pages_read > 0 and w.exhausted for w in self.walks)

    @property
    def state(self) -> str:
        """The state a surface may show. Never "empty"."""
        if self.held_reason:
            return STATE_HELD
        if self.unknown_desks or not self.walks:
            return STATE_UNKNOWN
        if self.rows_n and self.complete:
            return STATE_GATHERED
        return STATE_GATHERING

    def honest_line(self) -> str:
        """One line a surface may print. It states what we read and what we
        could not, and it never claims a place has nothing on.
        """
        if self.held_reason:
            return f"not gathered yet — {self.held_reason}"
        if not self.walks:
            return ("no door here has been read yet — gathering, not empty "
                    f"({len(self.skipped)} door(s) queued)")
        unread = self.unknown_desks
        read_n = len(self.walks) - len(unread)
        tail = f"; {len(unread)} desk(s) unread (UNKNOWN, not zero)" if unread else ""
        floor = "" if self.complete else "; at least"
        return (f"{read_n} of {len(self.walks)} desk(s) read{floor} "
                f"{self.rows_n} row(s){tail}")


# --------------------------------------------------------------------------
# 7. Single flight — one job per place, concurrent visitors attach
# --------------------------------------------------------------------------

@dataclass
class Job:
    """One in-flight gather. Shared by every visitor who asked for this place."""

    place_id: str
    trigger: str
    attached: int = 0
    report: Optional[GatherReport] = None
    error: Optional[BaseException] = None
    done: threading.Event = field(default_factory=threading.Event)

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self.done.wait(timeout)

    def result(self, timeout: Optional[float] = None) -> GatherReport:
        if not self.wait(timeout):
            raise GatherError(
                f"gather for {self.place_id!r} did not finish inside {timeout}s")
        if self.error is not None:
            raise self.error
        if self.report is None:  # pragma: no cover - set together with `error`
            raise GatherError(f"gather for {self.place_id!r} produced no report")
        return self.report


class Registry:
    """Single-flight gather jobs, keyed by canonical place_id (§6a).

    The FIRST caller runs the work on its own thread. Every caller that arrives
    while it is running gets the SAME `Job` back and waits on it — one pipe, many
    readers, which is the difference between a place being popular and a place
    being crawled once per visitor.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._inflight: Dict[str, Job] = {}
        #: How many jobs this registry has actually STARTED. A test reads it to
        #: prove the second visitor started nothing.
        self.starts = 0

    def in_flight(self, place_id: str) -> Optional[Job]:
        with self._lock:
            return self._inflight.get(place_id)

    def run(self, place_id: str, work: Callable[[], GatherReport], *,
            trigger: str) -> Job:
        """Run `work` for this place, or attach to the run already going.

        Returns as soon as the caller has a Job to hold. The first caller
        returns with the work finished; an attaching caller returns immediately
        and calls `job.result()` when it wants the answer.
        """
        assert_trigger(trigger)
        if not place_id:
            raise GatherError("single flight needs a canonical place_id to key on")
        with self._lock:
            existing = self._inflight.get(place_id)
            if existing is not None:
                existing.attached += 1
                return existing
            job = Job(place_id=place_id, trigger=trigger)
            self._inflight[place_id] = job
            self.starts += 1

        try:
            job.report = work()
        except BaseException as exc:  # noqa: BLE001 — recorded on the job, then re-raised to every waiter
            job.error = exc
        finally:
            with self._lock:
                self._inflight.pop(place_id, None)
            job.done.set()
        if job.error is not None:
            raise job.error
        return job


#: The process-wide registry. A caller may pass its own; this one exists so two
#: request handlers in one process share a place by default rather than by
#: remembering to.
REGISTRY = Registry()


# --------------------------------------------------------------------------
# 8. The job
# --------------------------------------------------------------------------

def _zone(timezone_id: str):
    from zoneinfo import ZoneInfo
    try:
        return ZoneInfo(timezone_id)
    except Exception as exc:  # noqa: BLE001 — an unusable clock stops the job
        raise GatherError(
            f"timezone {timezone_id!r} is unusable here ({type(exc).__name__}: "
            f"{exc}). Install tzdata rather than letting the union guess a night."
        ) from exc


def gather_once(place_text: str, *, fetch: Callable[[str], PageFetch], tick: Tick,
                trigger: str, catalog: Sequence[Mapping[str, Any]] = (),
                leads: Sequence[Lead] = (), packs_dir: Optional[str] = None,
                timezone_id: Optional[str] = None, mode: str = "FIXTURE",
                kind_map_for: Optional[Callable[[str], Any]] = None,
                start_url_for: Optional[Callable[[Door], Optional[str]]] = None
                ) -> GatherReport:
    """Run the pipe ONCE for one place, inside one tick. No single flight here —
    `gather()` wraps this in the registry. Split out so the job is testable
    without threads.
    """
    assert_trigger(trigger)
    resolved = resolve(place_text, packs_dir=packs_dir, timezone_id=timezone_id)
    report = GatherReport(
        place_id=resolved.place_id, display=resolved.display, trigger=trigger,
        pack_id=resolved.pack_id, grammar_source=resolved.grammar.source,
        timezone_id=resolved.timezone_id, queries=resolved.grammar.queries(),
        leads_n=len(leads))

    if not resolved.timezone_id:
        # No clock, no night, no union. Held rather than guessed: a wrong night
        # is a wrong listing, and the fix is a pack or a geocode, not a default.
        report.held_reason = (
            "no timezone for this place. A pack states its clock; a place "
            "without one needs a geocode to supply it. This job will not assume "
            "a home town, because the night is half the de-dup key.")
        return report

    doors: List[Door] = list(resolved.doors)
    for lead in leads:
        doors.append(lead_door(lead, place_id=resolved.place_id))
    report.doors_n = len(doors)

    tick.start()
    walks: List[DeskWalk] = []
    registrations: Dict[str, DeskRegistration] = {}

    for door in doors:
        spent = tick.bound()
        if spent:
            tick.note_stop(spent)
            report.notes.append(
                f"tick spent on {spent} with {len(doors) - len(walks)} door(s) "
                f"still unopened — OUR bound, not the end of this place")
            break

        verdict = door_class(door, catalog)
        if not verdict.fetchable:
            report.skipped.append(DoorSkip(
                door.door_id, door.door_type, verdict.source_class,
                f"class {verdict.source_class}: {verdict.reason} — queued, never bypassed"))
            continue
        if not door.readable:
            report.skipped.append(DoorSkip(
                door.door_id, door.door_type, verdict.source_class,
                f"not a listable public desk (type={door.door_type}, "
                f"intake={door.intake}) — a lead, not a listing"))
            continue
        try:
            reg = registration_for(door, catalog)
        except DeskPublishError as exc:
            # A door we cannot put a masthead on writes nothing. Fail-closed and
            # NAMED, so it reads as a door to register rather than as a place
            # with less on.
            report.skipped.append(DoorSkip(
                door.door_id, door.door_type, verdict.source_class, str(exc)))
            continue
        registrations[reg.via] = reg

        kind_map = kind_map_for(door.door_id) if kind_map_for else None
        pages_left = tick.pages_left
        if pages_left < 1:  # pragma: no cover - `tick.bound()` catches this first
            tick.note_stop("pages")
            break
        one_walk = walk(door, fetch, max_pages=pages_left, kind_map=kind_map,
                        start_url=start_url_for(door) if start_url_for else None,
                        stop_when=tick.stop_when())
        tick.pages_used += len(one_walk.pages)
        if one_walk.stopped_because in ("max_pages", "tick_bound"):
            tick.note_stop("pages" if one_walk.stopped_because == "max_pages"
                           else (tick.bound() or "wall_clock"))
        walks.append(one_walk)

    report.walks = walks
    report.stopped_because = tick.stopped_because

    if not walks:
        # Not an empty place: a tick that opened no door. Every reason is on
        # `report.skipped`, by door name.
        return report

    report.one = union(walks, timezone=_zone(resolved.timezone_id),
                       timezone_id=resolved.timezone_id, mode=mode)
    report.digest = plan_digest(plan(report.one, registrations))
    return report


def gather(place_text: str, *, fetch: Callable[[str], PageFetch], tick: Tick,
           trigger: str, registry: Optional[Registry] = None,
           **kwargs: Any) -> GatherReport:
    """Start ONE bounded gather for this place, or attach to the one running.

    This is the entry point a surface calls when Show is thin. It is single
    flight by place_id (§6a) and refuses `page_load` outright.
    """
    place_id = canonical_place_id(place_text)
    reg = REGISTRY if registry is None else registry

    def _work() -> GatherReport:
        return gather_once(place_text, fetch=fetch, tick=tick, trigger=trigger,
                           **kwargs)

    job = reg.run(place_id, _work, trigger=trigger)
    return job.result()


# --------------------------------------------------------------------------
# 9. Tables — the dry-run report, printed by tools/gather.py
# --------------------------------------------------------------------------

def door_table(report: GatherReport) -> str:
    """Every door this tick considered, walked or not, with its class."""
    lines = ["| door | type | class | pages | rows | 403 | stopped |",
             "|---|---|---|---|---|---|---|"]
    for w in report.walks:
        lines.append(
            f"| {w.door_id} | {w.door_type} | fetched | {len(w.pages)} | "
            f"{w.count} | {w.walled_n} | {w.stopped_because} |")
    for s in report.skipped:
        lines.append(
            f"| {s.door_id} | {s.door_type} | {s.source_class} | 0 | — | — | "
            f"{s.why.splitlines()[0][:80]} |")
    if len(lines) == 2:
        lines.append("| (no door opened) | — | — | 0 | — | — | — |")
    return "\n".join(lines)


def summary_table(report: GatherReport) -> str:
    """The go-live numbers for this tick (§4 step 5), plus the tick itself."""
    rows = [
        ("place_id", report.place_id),
        ("pack", report.pack_id or "(none — thin gather)"),
        ("grammar", f"{report.grammar_source} ({len(report.queries)} queries)"),
        ("timezone", report.timezone_id or "(unresolved — job held)"),
        ("rows_n", report.rows_n),
        ("dated_n", report.dated_n),
        ("placed_n", report.placed_n),
        ("mash_n", report.mash_n),
        ("403_n", report.walls_n),
        ("held_n", report.held_n),
        ("publishable_n", report.publishable_n),
        ("state", report.state),
        ("stopped_because", report.stopped_because or "(no bound spent)"),
    ]
    out = ["| measure | value |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in rows]
    return "\n".join(out)
