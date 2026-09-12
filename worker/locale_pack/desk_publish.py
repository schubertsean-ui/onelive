"""publish(desk union) — listings from the desk walk.

FL-013: ingest_key is identity_key. Clock and Place stay out of the key.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from worker.locale_pack.desk_union import DeskUnion, UnionRow
from worker.locale_pack.happening_key import identity_key
from worker.locale_pack.pack import Door

DESK_KEY = "_desk"
LIVE = "LIVE"


class DeskPublishError(ValueError):
    """The write cannot be planned: a door with no catalog row, or a union that was not walked live."""


@dataclass(frozen=True)
class DeskRegistration:
    door_id: str
    via: str
    source_name: str
    source_class: str
    base_url: str
    catalog_id: str


def _host(url: str) -> str:
    host = (urlsplit(url or "").hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _same_publisher(door_url: str, base_url: str) -> bool:
    door, base = _host(door_url), _host(base_url)
    if not door or not base:
        return False
    return door == base or door.endswith("." + base) or base.endswith("." + door)


def registration_for(door: Door, catalog: Sequence[Mapping[str, Any]]) -> DeskRegistration:
    hits = [row for row in catalog if _same_publisher(door.url, str(row.get("base_url") or ""))]
    if not hits:
        raise DeskPublishError(
            f"door {door.door_id!r} ({door.url}) matches no row in the committed source catalog, so its listings could not be LABELLED with a source. Add the publisher to sources/master_sources_catalog_120.json (name + base_url + category) before walking it into the catalog.")
    if len(hits) > 1:
        names = sorted(str(r.get("name")) for r in hits)
        raise DeskPublishError(
            f"door {door.door_id!r} ({door.url}) matches {len(hits)} catalog rows ({names}) — the source label would be a guess. Narrow the base_url of the rows that do not own this door.")
    row = hits[0]
    source_class = str(row.get("category") or row.get("source_type") or "").strip()
    name = str(row.get("name") or "").strip()
    if not source_class or not name:
        raise DeskPublishError(
            f"catalog row {row.get('id')!r} for door {door.door_id!r} is missing a name or a category; the gate reads the category as evidence strength and promote.py reads the name as the public label.")
    return DeskRegistration(
        door_id=door.door_id,
        via=door.via or name,
        source_name=name,
        source_class=source_class,
        base_url=str(row.get("base_url") or ""),
        catalog_id=str(row.get("id") or ""),
    )


@dataclass(frozen=True)
class Evidence:
    source_class: str
    source_name: str
    source_url: str
    quote: str


@dataclass
class CandidateWrite:
    ingest_key: str
    source_name: str
    source_class: str
    source_url: str
    raw_text: str
    extracted: Dict[str, Any]
    evidence: List[Evidence] = field(default_factory=list)
    vias: Tuple[str, ...] = ()
    clock_hole: Optional[str] = None
    clock_disputed: bool = False
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
    try:
        return datetime.fromisoformat(stated)
    except (TypeError, ValueError):
        return None


def _night_as_public_clock(night: str) -> str:
    day = datetime.strptime(night, "%Y-%m-%d")
    local = day.replace(hour=17, minute=0, second=0, tzinfo=ZoneInfo("America/Chicago"))
    return local.isoformat()


def _stated_clocks(row: UnionRow) -> List[str]:
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
    """Listing URL, or title + local date. Clock and Place stay out."""
    return identity_key(row)


CONTRADICTING = ("title", "place", "night", "clocks", "listing_url")
CORROBORATING = ("vias",)
WATCHED = CONTRADICTING + CORROBORATING


def _statement(row: UnionRow, clocks: List[str], listing_url: Optional[str]) -> Dict[str, Any]:
    return {
        "title": row.title,
        "place": row.place_text,
        "night": row.night,
        "clocks": list(clocks),
        "listing_url": listing_url,
        "vias": list(row.vias),
    }


def drift(stored: Optional[Mapping[str, Any]], fresh: Mapping[str, Any]) -> List[str]:
    if not stored:
        return [field for field in WATCHED if fresh.get(field)]
    return [field for field in WATCHED if stored.get(field) != fresh.get(field)]


def contradicts(stored: Optional[Mapping[str, Any]], fresh: Mapping[str, Any]) -> List[str]:
    out = []
    for f in drift(stored, fresh):
        if f not in CONTRADICTING:
            continue
        if not stored.get(f) and fresh.get(f):
            continue
        out.append(f)
    return out


def describe_drift(stored: Mapping[str, Any], fresh: Mapping[str, Any], fields: Sequence[str]) -> str:
    return "; ".join(f"{f}: {stored.get(f)!r} -> {fresh.get(f)!r}" for f in fields)


def _quote(row: UnionRow, member) -> str:
    parts = [member.row.title or "(untitled)"]
    if member.row.when_text:
        parts.append(member.row.when_text)
    if member.row.place_text:
        parts.append(member.row.place_text)
    return " — ".join(parts)[:500]


def write_for(row: UnionRow, registrations: Mapping[str, DeskRegistration], *, mode: str) -> CandidateWrite:
    vias = row.vias
    first = registrations.get(vias[0]) if vias else None
    if first is None:
        raise DeskPublishError(
            f"row {row.key!r} came from desk {vias[0]!r} with no registration — every walked door must resolve to a catalog row before any of its rows are written.")
    clocks = _stated_clocks(row)
    clock_desks = {m.via for m in row.members if m.row.when and m.row.when_precision == "datetime"}
    clock_hole: Optional[str] = None
    clock_disputed = False
    hold_reason: Optional[str] = None
    start_time: Optional[str] = None
    if len(clocks) == 1:
        start_time = clocks[0]
    elif len(clocks) > 1 and len(clock_desks) < 2:
        clock_hole = f"one desk states {len(clocks)} different times for this row: {', '.join(clocks)}"
        clock_disputed = True
        start_time = row.night
    elif len(clocks) > 1:
        clock_hole = f"{len(clocks)} desks state different times for this happening: {', '.join(clocks)}"
        clock_disputed = True
    elif row.night:
        clock_hole = "the desk stated a night, not a time"
        start_time = row.night
    else:
        clock_hole = "no desk stated a date for this row"
    gaps = [reason for missing, reason in ((not (row.title or "").strip(), "no desk stated a title for this row"),) if missing]
    if gaps:
        hold_reason = "; ".join(([hold_reason] if hold_reason else []) + gaps)
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
        "statement": _statement(row, clocks, listing_url),
    }
    extracted: Dict[str, Any] = {
        "title": row.title,
        "start_time": start_time,
        "end_time": None,
        "venue_name": row.place_text,
        "city": None,
        "artist_names": [],
        "ticket_link": getattr(row, "ticket_link", None),
        "rsvp_link": None,
        "is_private_rsvp": False,
        "private_access": {},
        DESK_KEY: desk_note,
    }
    if clock_disputed:
        extracted["start_times"] = [
            {"source": registrations[m.via].source_name, "at": m.row.when}
            for m in row.members
            if m.row.when and m.row.when_precision == "datetime" and m.via in registrations
        ]
    if listing_url:
        extracted["listing_url"] = listing_url
    raw_lines = [f"{m.via}: {_quote(row, m)}" for m in row.members]
    raw_lines.append(f"[1Live desk walk — key {desk_note['key']}]")
    evidence = []
    for member in row.members:
        reg = registrations.get(member.via)
        if reg is None:
            raise DeskPublishError(
                f"row {row.key!r} carries desk {member.via!r} with no registration — its evidence could not name a source class.")
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
    if one.mode != LIVE:
        raise DeskPublishError(
            f"refusing to write a {one.mode} union to a database: fixture titles must never reach the catalog. Walk the live desks (--real) on a machine with egress, or use --dry-run to print the plan.")


def plan(one: DeskUnion, registrations: Mapping[str, DeskRegistration]) -> List[CandidateWrite]:
    return [write_for(row, registrations, mode=one.mode) for row in one.rows]


def plan_digest(writes: Sequence[CandidateWrite]) -> Dict[str, Any]:
    held = sum(1 for w in writes if w.hold_reason)
    public = [w for w in writes if not w.hold_reason]
    return {
        "rows": len(writes),
        "timed": sum(1 for w in writes if w.start_time),
        "clock_holes": sum(1 for w in writes if w.clock_hole),
        "held": held,
        "clock_disputed": sum(1 for w in writes if w.clock_disputed),
        "publishable": len(writes) - held,
        "publish_timed": sum(1 for w in public if w.start_time),
        "publish_disputed": sum(1 for w in public if w.clock_disputed),
        "tba_public": sum(1 for w in public if not w.start_time and not w.clock_disputed),
        "dated": sum(1 for w in writes if str(w.extracted.get(DESK_KEY, {}).get("night") or "").strip()),
        "placed": sum(1 for w in writes if str(w.extracted.get("venue_name") or "").strip()),
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
    return json.dumps(write.extracted, sort_keys=True, default=str)
