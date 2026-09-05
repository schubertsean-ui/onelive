"""A desk's own category labels, mapped to OUR kinds — as data, never as schema.

Founder, this session's ticket: "Commit a mapping table: <desk> category -> our
kind | other. Our kinds stay ours; their labels do not become the schema."

Both halves of that sentence are enforced here:

  * THEIR LABELS DO NOT BECOME THE SCHEMA. A desk's taxonomy lives in a JSON
    file under `sources/kind_maps/`, keyed by the desk's own label text or its
    own section id. Nothing about a desk's categories reaches code: this module
    knows how to READ a mapping, not what any desk calls anything.
  * OUR KINDS STAY OURS. Every `our_kind` in a mapping is validated against the
    locale pack's `query_grammar.kinds` at load time, and a mapping naming a
    kind we do not have is a load ERROR, not a silently-dropped row. A desk that
    invents a category simply lands on `other`.

`other` is not a failure state. It is the honest answer for "this desk stated a
category we have not mapped", and it is what an unmapped row gets — never a
guess from the title, which would both fabricate and weight one category over
another (ONE-LIVE-VISION.md: no category weighting).

Three evidence grades, because a mapping row is a claim and claims are graded:

  `desk_observed`   we read this label off the desk's own page (a committed
                    fixture or a live read) and mapped it.
  `desk_id_cited`   the desk's own section id, cited to a committed locale-pack
                    door that carries it in its URL.
  `language_rule`   an ordinary English category word that NAMES one of our
                    kinds ("movies" -> film). This is a statement about OUR
                    vocabulary applied to whatever text a desk prints — never a
                    claim that any particular desk prints it.

Pure: stdlib only, no network, no DB, no clock, no model.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from worker.locale.pack import KIND_OTHER, LocalePackError, load_pack

#: Where committed mappings live, alongside the packs they answer to.
MAPS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "sources", "kind_maps",
)

#: What a mapping row may claim about itself. See the module docstring.
EVIDENCE_GRADES: Tuple[str, ...] = ("desk_observed", "desk_id_cited", "language_rule")

#: How a desk may STATE a category on one of its cards. A signal says where to
#: look; it never says what the found text means — that is the row table's job.
#:
#: `href_param` and `href_path` are the same statement in the two shapes desks
#: actually publish it: a category-filtered URL, addressed either by a query
#: parameter (`?eventSection=2151678`) or by a path segment
#: (`/events/live-music/today`). A desk that routes by path can state nothing a
#: query-parameter signal will ever see, so a map for one would silently read
#: every card as uncategorised.
SIGNAL_KINDS: Tuple[str, ...] = ("label", "href_param", "href_path")

#: What a LISTING SELECTOR may claim about itself. A selector says "on THIS
#: desk, one listing card is this element" — a per-desk declaration, which is
#: the only thing that may split a page into cards (`worker/segment.py` strategy
#: (c); founder, this session: "It does not get a guessed card").
#:
#: `desk_observed` we read this markup off the desk's own live page.
#: `fixture_shape` we read it off our own committed shape fixture under
#:                 `tests/fixtures/desk_pages/<door>/`, which is SYNTHETIC —
#:                 nobody here has loaded the live desk (egress to both desks is
#:                 denied from this sandbox: CONNECT 403, 2026-09-04). The grade
#:                 exists so a selector can never imply a reading that did not
#:                 happen, and so the first authorized live run knows exactly
#:                 which selectors are still unconfirmed against the real page.
SELECTOR_EVIDENCE_GRADES: Tuple[str, ...] = ("desk_observed", "fixture_shape")

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^a-z0-9]+")


class KindMapError(ValueError):
    """A mapping is missing, malformed, or names a kind we do not have.

    Always raised. A half-read mapping would silently send real rows to `other`
    and look exactly like a desk that states no categories.
    """


def normalize_label(value: Optional[str]) -> str:
    """Fold a printed label to its comparison form: lowercase, punctuation and
    runs of whitespace to single spaces, trimmed.

    "Food & Drink", "food and drink" and "FOOD  &  DRINK " are the same key;
    keeping them apart would make a mapping table a list of typos.
    """
    if not value:
        return ""
    text = _PUNCT_RE.sub(" ", str(value).lower())
    text = text.replace(" and ", " ")
    return _WS_RE.sub(" ", text).strip()


def segment_after(url: Optional[str], prefix: str) -> Optional[str]:
    """The path segment a desk states directly after `prefix`, or None.

    `segment_after("https://desk.example/events/live-music/today", "/events/")`
    is `"live-music"` — the desk's own routing, read rather than inferred.

    Two deliberate refusals, both of which would otherwise put noise into a
    coverage table and, worse, a wrong kind on a row:

      * ANCHORED AT THE ROOT. The prefix must be the START of the path. A
        category root is where a desk hangs its sections; matching the prefix
        anywhere would make `/tickets/events/2026` state a category too.
      * A PURELY NUMERIC SEGMENT IS NEVER A CATEGORY. Desks address individual
        listings under the same root (`/events/2026/9/4/some-show`), so the
        segment after the prefix is often a year. It is a date or an id, and
        reading it as a section name would invent a category the desk never
        published.
    """
    if not url or not prefix:
        return None
    try:
        path = urlsplit(url).path
    except ValueError:
        return None
    prefix_parts = [p for p in prefix.split("/") if p]
    parts = [p for p in path.split("/") if p]
    if len(parts) <= len(prefix_parts) or parts[:len(prefix_parts)] != prefix_parts:
        return None
    segment = parts[len(prefix_parts)].strip()
    if not segment or segment.isdigit():
        return None
    return segment


@dataclass(frozen=True)
class MapRow:
    """One mapping: what the desk calls it -> what we call it."""

    desk_category: str          # verbatim, as the desk prints it
    our_kind: str
    evidence: str
    note: Optional[str] = None

    @property
    def key(self) -> str:
        return normalize_label(self.desk_category)


@dataclass(frozen=True)
class Signal:
    """Where on a card this desk states a category."""

    how: str                    # one of SIGNAL_KINDS
    param: Optional[str] = None  # for href_param: the query parameter's name
    prefix: Optional[str] = None  # for href_path: the path root categories hang off


@dataclass(frozen=True)
class ListingSelector:
    """One element shape that IS a listing card on this desk.

    Deliberately not a CSS selector: a selector language invites `div div > a`
    and with it a whole matching engine to review. What a desk walk actually
    yields is "the card is a `<div>` carrying these class tokens", so that is
    all this holds — a tag name plus the class tokens an element must carry,
    ALL of them, as WHOLE tokens.

    Whole tokens and all-of-them are the difference between this and the guess
    it replaces. `_CARDISH_CLASS_RE` matched the substring `event` anywhere in
    any class, so `class="eventual"`, `class="showcase"` and `class="listing-nav"`
    all read as listing cards on any page in the world. `("div", ("ds-listing",
    "event-card"))` is a statement about ONE desk, and `class="event-cards-off"`
    does not satisfy it.
    """

    tag: str
    classes: Tuple[str, ...]
    evidence: str
    note: Optional[str] = None

    @property
    def matcher(self) -> Tuple[str, Tuple[str, ...]]:
        """The plain-data form `worker.segment.segment_events` consumes.

        A tuple rather than this object, so the segmenter stays a pure text
        module that imports no loader and reads no file: the caller resolves
        the desk, the segmenter is handed a value.
        """
        return self.tag, self.classes


@dataclass(frozen=True)
class KindMap:
    """A whole committed mapping for one desk (or family of desk doors)."""

    map_id: str
    kinds_from: str             # the locale pack whose kind vocabulary is ours
    our_kinds: Tuple[str, ...]
    default_kind: str
    applies_to_doors: Tuple[str, ...]
    signals: Tuple[Signal, ...]
    label_rows: Mapping[str, MapRow]
    id_rows: Mapping[str, MapRow]
    #: How a listing card is SHAPED on this desk, if we have walked it. Empty is
    #: the normal answer and never an error: a desk we have not walked has no
    #: selector, and its pages are segmented by their own JSON-LD, their own
    #: microdata, or by date anchors — never by a guess at its class names.
    listing_selectors: Tuple[ListingSelector, ...] = ()

    def applies_to(self, door_id: str) -> bool:
        return door_id in self.applies_to_doors

    @property
    def selector_matchers(self) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
        """This desk's selectors as plain data for `worker.segment`."""
        return tuple(s.matcher for s in self.listing_selectors)

    @property
    def rows(self) -> Tuple[MapRow, ...]:
        """Every committed row, label rows first, each once."""
        return tuple(self.label_rows.values()) + tuple(self.id_rows.values())

    def kind_for_label(self, label: Optional[str]) -> Optional[str]:
        row = self.label_rows.get(normalize_label(label))
        return row.our_kind if row else None

    def kind_for_id(self, section_id: Optional[str]) -> Optional[str]:
        if section_id is None:
            return None
        row = self.id_rows.get(str(section_id).strip())
        return row.our_kind if row else None

    def section_ids_in(self, url: Optional[str]) -> Tuple[str, ...]:
        """Every section id this map's href signals find in one URL.

        The desk's own address bar is a category statement when the desk
        publishes category-filtered URLs — reading it is reading what the desk
        said, not inferring from the title. Two shapes, because desks publish
        both: a query parameter (`href_param`) and a path segment
        (`href_path`).
        """
        if not url:
            return ()
        found = []
        for signal in self.signals:
            if signal.how == "href_param" and signal.param:
                for match in re.finditer(
                        r"[?&]" + re.escape(signal.param) + r"=([^&#\s\"']+)", url):
                    value = match.group(1).strip()
                    if value and value not in found:
                        found.append(value)
            elif signal.how == "href_path" and signal.prefix:
                value = segment_after(url, signal.prefix)
                if value and value not in found:
                    found.append(value)
        return tuple(found)

    @property
    def reads_labels(self) -> bool:
        return any(s.how == "label" for s in self.signals)

    def resolve(self, *, labels: Sequence[str] = (),
                hrefs: Sequence[str] = ()) -> Tuple[Optional[str], Optional[str]]:
        """Decide a kind from what ONE card stated. Returns `(kind, matched)`.

        `matched` is the desk's own text or id that decided it, kept so a table
        can show what the desk actually said. `(None, None)` means this card
        stated no category this map recognises — the caller then falls back to
        the door's declared scope, and finally to `other`. Ids are read before
        labels: a section id is the desk's own identifier and cannot be a
        near-miss on wording.
        """
        for href in hrefs:
            for section_id in self.section_ids_in(href):
                kind = self.kind_for_id(section_id)
                if kind:
                    return kind, section_id
        if self.reads_labels:
            for label in labels:
                kind = self.kind_for_label(label)
                if kind:
                    return kind, str(label).strip()
        return None, None

    def unmapped_from(self, *, labels: Sequence[str] = (),
                      hrefs: Sequence[str] = ()) -> Tuple[str, ...]:
        """What this card stated that the table does NOT map yet.

        A live run prints these so the committed table can be completed from
        the desk's own words instead of from anybody's memory of them.
        """
        out = []
        for href in hrefs:
            for section_id in self.section_ids_in(href):
                if not self.kind_for_id(section_id) and section_id not in out:
                    out.append(section_id)
        if self.reads_labels:
            for label in labels:
                text = str(label or "").strip()
                if not text or normalize_label(text) in self.label_rows:
                    continue
                if text not in out:
                    out.append(text)
        return tuple(out)


def _require(obj: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in obj:
        raise KindMapError(f"{where}: missing required key {key!r}")
    return obj[key]


def _row_from(raw: Any, *, where: str, our_kinds: frozenset, keyed: str) -> MapRow:
    if not isinstance(raw, dict):
        raise KindMapError(f"{where}: each row must be an object, got {type(raw).__name__}")
    category = _require(raw, keyed, where)
    if not isinstance(category, str) or not category.strip():
        raise KindMapError(f"{where}: {keyed!r} must be a non-empty string, got {category!r}")
    where = f"{where} row {category!r}"
    our_kind = _require(raw, "our_kind", where)
    # OUR KINDS STAY OURS: a mapping may not introduce a kind. Refused loudly,
    # because a dropped row would look exactly like a desk category we chose to
    # send to `other`.
    if our_kind not in our_kinds:
        raise KindMapError(
            f"{where}: our_kind {our_kind!r} is not one of this locale's kinds "
            f"({sorted(our_kinds)}) — a mapping maps INTO our vocabulary, it "
            f"never extends it")
    evidence = _require(raw, "evidence", where)
    if evidence not in EVIDENCE_GRADES:
        raise KindMapError(
            f"{where}: evidence {evidence!r} is not one of {EVIDENCE_GRADES}")
    note = raw.get("note")
    if note is not None and not isinstance(note, str):
        raise KindMapError(f"{where}: note must be a string or null, got {note!r}")
    return MapRow(desk_category=category.strip(), our_kind=our_kind,
                  evidence=evidence, note=note)


def _signal_from(raw: Any, *, where: str) -> Signal:
    if not isinstance(raw, dict):
        raise KindMapError(f"{where}: each signal must be an object, got {type(raw).__name__}")
    how = _require(raw, "how", where)
    if how not in SIGNAL_KINDS:
        raise KindMapError(f"{where}: signal how={how!r} is not one of {SIGNAL_KINDS}")
    param = raw.get("param")
    if how == "href_param" and (not isinstance(param, str) or not param.strip()):
        raise KindMapError(
            f"{where}: an href_param signal must name its param, got {param!r}")
    prefix = raw.get("prefix")
    if how == "href_path" and (not isinstance(prefix, str) or not prefix.strip()):
        raise KindMapError(
            f"{where}: an href_path signal must name the path prefix its "
            f"categories hang off, got {prefix!r}")
    return Signal(how=how,
                  param=(param.strip() if isinstance(param, str) else None),
                  prefix=(prefix.strip() if isinstance(prefix, str) else None))


def _listing_selector_from(raw: Any, *, where: str) -> ListingSelector:
    """One committed listing selector, or a loud refusal.

    Every refusal here is the same refusal: a selector that is broader than one
    desk's own card would put non-events into the catalog, which is the harm the
    class-substring guess caused and this table exists to end.
    """
    if not isinstance(raw, dict):
        raise KindMapError(
            f"{where}: each listing selector must be an object, got "
            f"{type(raw).__name__}")
    tag = _require(raw, "tag", where)
    if not isinstance(tag, str) or not tag.strip().isalnum():
        raise KindMapError(
            f"{where}: a listing selector's tag must be an element name, got {tag!r}")
    tag = tag.strip().lower()
    classes_raw = _require(raw, "classes", where)
    where = f"{where} selector {tag!r}"
    if (not isinstance(classes_raw, list) or not classes_raw
            or any(not isinstance(c, str) or not c.strip() or c.split() != [c.strip()]
                   for c in classes_raw)):
        raise KindMapError(
            f"{where}: classes must be a non-empty list of single class tokens, "
            f"got {classes_raw!r}")
    classes = tuple(sorted({c.strip().lower() for c in classes_raw}))
    # A selector with no class token would match EVERY element of that tag —
    # `("div",)` splits a page at every div, which is the guess with extra steps.
    # Refused above by requiring a non-empty list; stated here because the reason
    # is the whole point of the table.
    evidence = _require(raw, "evidence", where)
    if evidence not in SELECTOR_EVIDENCE_GRADES:
        raise KindMapError(
            f"{where}: evidence {evidence!r} is not one of "
            f"{SELECTOR_EVIDENCE_GRADES}")
    note = raw.get("note")
    if note is not None and not isinstance(note, str):
        raise KindMapError(f"{where}: note must be a string or null, got {note!r}")
    return ListingSelector(tag=tag, classes=classes, evidence=evidence, note=note)


def load_kind_map(map_id: str, *, maps_dir: Optional[str] = None,
                  packs_dir: Optional[str] = None) -> KindMap:
    """Read and validate one committed mapping. Raises on anything it cannot
    vouch for — there is no partial mapping.
    """
    if not isinstance(map_id, str) or not map_id.strip():
        raise KindMapError(f"map_id must be a non-empty string, got {map_id!r}")
    # A map id names a FILE, so it may not steer the path.
    if map_id != os.path.basename(map_id) or map_id in (".", ".."):
        raise KindMapError(f"map_id {map_id!r} is not a plain mapping name")
    directory = maps_dir or MAPS_DIR
    path = os.path.join(directory, f"{map_id}.json")
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError as exc:
        raise KindMapError(
            f"no mapping {map_id!r} in {directory} — have "
            f"{sorted(available_maps(maps_dir=directory))}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise KindMapError(f"mapping {map_id!r} is unreadable: {exc}") from exc
    if not isinstance(raw, dict):
        raise KindMapError(f"mapping {map_id!r}: top level must be an object")

    where = f"kind map {map_id!r}"
    stated_id = _require(raw, "map_id", where)
    if stated_id != map_id:
        raise KindMapError(
            f"{where}: file states map_id {stated_id!r} — a mapping that does "
            f"not know its own name cannot be cited")

    kinds_from = _require(raw, "kinds_from", where)
    try:
        pack = load_pack(kinds_from, packs_dir=packs_dir)
    except LocalePackError as exc:
        raise KindMapError(
            f"{where}: kinds_from {kinds_from!r} does not load: {exc}") from exc
    our_kinds = frozenset(pack.kinds)
    if not our_kinds:
        raise KindMapError(f"{where}: locale {kinds_from!r} states no kinds")

    default_kind = raw.get("default_kind", KIND_OTHER)
    if default_kind not in our_kinds:
        raise KindMapError(
            f"{where}: default_kind {default_kind!r} is not one of this locale's "
            f"kinds ({sorted(our_kinds)})")

    doors = raw.get("applies_to_doors") or []
    if not isinstance(doors, list) or any(not isinstance(d, str) for d in doors):
        raise KindMapError(f"{where}: applies_to_doors must be a list of door ids")
    if not doors:
        raise KindMapError(
            f"{where}: a mapping that applies to no door can only mislead — "
            f"name the door ids it answers for")
    unknown = [d for d in doors if d not in {door.door_id for door in pack.doors}]
    if unknown:
        raise KindMapError(
            f"{where}: applies_to_doors names door(s) not in pack {kinds_from!r}: "
            f"{unknown}")

    signals_raw = raw.get("category_signals") or []
    if not isinstance(signals_raw, list):
        raise KindMapError(f"{where}: category_signals must be a list")
    signals = tuple(_signal_from(s, where=where) for s in signals_raw)

    label_rows: Dict[str, MapRow] = {}
    for row_raw in (raw.get("label_rows") or []):
        row = _row_from(row_raw, where=where, our_kinds=our_kinds, keyed="desk_category")
        if row.key in label_rows:
            raise KindMapError(
                f"{where}: two rows normalise to the same label {row.key!r} "
                f"({label_rows[row.key].desk_category!r} and {row.desk_category!r}) "
                f"— one of them would never be read")
        label_rows[row.key] = row

    id_rows: Dict[str, MapRow] = {}
    for row_raw in (raw.get("id_rows") or []):
        row = _row_from(row_raw, where=where, our_kinds=our_kinds, keyed="desk_category")
        key = row.desk_category
        if key in id_rows:
            raise KindMapError(f"{where}: duplicate section id row {key!r}")
        id_rows[key] = row
    if id_rows and not any(s.how in ("href_param", "href_path") for s in signals):
        raise KindMapError(
            f"{where}: id_rows are keyed by a section id, but no href_param or "
            f"href_path signal says where to find one — those rows could never "
            f"match")

    selectors_raw = raw.get("listing_selectors") or []
    if not isinstance(selectors_raw, list):
        raise KindMapError(f"{where}: listing_selectors must be a list")
    selectors = tuple(_listing_selector_from(sel, where=where) for sel in selectors_raw)
    seen_selectors = set()
    for selector in selectors:
        if selector.matcher in seen_selectors:
            raise KindMapError(
                f"{where}: duplicate listing selector {selector.matcher!r}")
        seen_selectors.add(selector.matcher)

    return KindMap(
        map_id=map_id,
        kinds_from=kinds_from,
        our_kinds=tuple(pack.kinds),
        default_kind=default_kind,
        applies_to_doors=tuple(doors),
        signals=signals,
        label_rows=label_rows,
        id_rows=id_rows,
        listing_selectors=selectors,
    )


def available_maps(*, maps_dir: Optional[str] = None) -> Tuple[str, ...]:
    directory = maps_dir or MAPS_DIR
    try:
        names = os.listdir(directory)
    except OSError:
        return ()
    return tuple(sorted(n[:-5] for n in names if n.endswith(".json")))


def map_for_door(door_id: str, *, maps_dir: Optional[str] = None,
                 packs_dir: Optional[str] = None) -> Optional[KindMap]:
    """The committed mapping that claims this door, or None.

    None is a real answer — a desk we have not mapped reads with the door's
    declared scope, exactly as before. It is never an error, because coverage
    must not depend on a taxonomy being finished.
    """
    for map_id in available_maps(maps_dir=maps_dir):
        candidate = load_kind_map(map_id, maps_dir=maps_dir, packs_dir=packs_dir)
        if candidate.applies_to(door_id):
            return candidate
    return None


def iter_map_ids(maps: Iterable[KindMap]) -> Tuple[str, ...]:
    return tuple(m.map_id for m in maps)


def _host_of(url: Optional[str]) -> str:
    """A URL's host, folded for comparison, or "" when there is none.

    `www.` is stripped because a desk publishes the same door both ways; nothing
    else is: `family.do512.com` is a DIFFERENT desk from `do512.com` and has its
    own door, so a suffix match would hand one desk's card shape to another's
    pages. Fold, never guess.
    """
    if not url:
        return ""
    try:
        host = (urlsplit(str(url)).hostname or "").strip().lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def desk_selectors_for_door(door_id: str, *, maps_dir: Optional[str] = None,
                            packs_dir: Optional[str] = None
                            ) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    """The committed card shapes for one door, as plain data for the segmenter.

    `()` is the normal answer for a desk nobody has walked, and it is never an
    error: an empty tuple means the page is segmented by what IT declares
    (JSON-LD, microdata) or by its date anchors, which is exactly the founder's
    rule — "If a desk has no selector and no JSON-LD, it uses (d) or (e). It
    does not get a guessed card."
    """
    mapping = map_for_door(door_id, maps_dir=maps_dir, packs_dir=packs_dir)
    return mapping.selector_matchers if mapping else ()


def desk_selectors_for_url(url: Optional[str], *, maps_dir: Optional[str] = None,
                           packs_dir: Optional[str] = None
                           ) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    """The committed card shapes for the desk a fetched page came FROM, by host.

    The crawl path knows a page's `source_url`, not a locale-pack `door_id`, so
    this is the seam that makes strategy (c) reachable in production. It matches
    on HOST — the one part of a URL that says which desk answered — because a
    desk's card shape is a property of the desk, not of one path on it; a door
    is committed per path, and `do512.com/events/live-music/today` must read the
    same as `do512.com/events/today`.

    `()` for any host no committed map claims, which is most of the catalog.
    """
    host = _host_of(url)
    if not host:
        return ()
    for map_id in available_maps(maps_dir=maps_dir):
        mapping = load_kind_map(map_id, maps_dir=maps_dir, packs_dir=packs_dir)
        if not mapping.listing_selectors:
            continue
        pack = load_pack(mapping.kinds_from, packs_dir=packs_dir)
        doors = {door.door_id: door for door in pack.doors}
        for door_id in mapping.applies_to_doors:
            door = doors.get(door_id)
            if door is not None and _host_of(door.url) == host:
                return mapping.selector_matchers
    return ()
