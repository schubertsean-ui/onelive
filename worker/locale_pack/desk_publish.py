"""Ticket A publish. Existence=title. Date/place never hold."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit
from worker.locale_pack.desk_union import BASIS_LOCAL, DeskUnion, UnionRow
from worker.locale_pack.pack import Door
from worker.locale_pack.existence import hold_reason as existence_hold
DESK_KEY = "_desk"
LIVE = "LIVE"

class DeskPublishError(ValueError):
    pass

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
        name = (door.via or door.door_id or "desk").strip()
        return DeskRegistration(door_id=door.door_id, via=name, source_name=name, source_class="local_media", base_url=door.url or "", catalog_id=f"pack:{door.door_id}")
    if len(hits) > 1:
        names = sorted(str(r.get("name")) for r in hits)
        raise DeskPublishError(f"door {door.door_id!r} matches {len(hits)} catalog rows")
    row = hits[0]
    source_class = str(row.get("category") or row.get("source_type") or "").strip()
    name = str(row.get("name") or "").strip()
    if not source_class or not name:
        raise DeskPublishError(f"catalog row for {door.door_id!r} missing name or category")
    return DeskRegistration(door_id=door.door_id, via=door.via or name, source_name=name, source_class=source_class, base_url=str(row.get("base_url") or ""), catalog_id=str(row.get("id") or ""))

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
    if row.basis != BASIS_LOCAL:
        return row.key
    url = _listing_url(row)
    if url:
        return f"url:{url}"
    member = row.members[0]
    return f"desk:{member.via}~{member.place}~{member.title_key}"

CONTRADICTING = ("title", "place", "night", "clocks", "listing_url")
CORROBORATING = ("vias",)
WATCHED = CONTRADICTING + CORROBORATING

def _statement(row: UnionRow, clocks: List[str], listing_url: Optional[str]) -> Dict[str, Any]:
    return {"title": row.title, "place": row.place_text, "night": row.night, "clocks": list(clocks), "listing_url": listing_url, "vias": list(row.vias)}

def drift(stored: Optional[Mapping[str, Any]], fresh: Mapping[str, Any]) -> List[str]:
    if not stored:
        return []
    return [field for field in WATCHED if stored.get(field) != fresh.get(field)]

def contradicts(stored: Optional[Mapping[str, Any]], fresh: Mapping[str, Any]) -> List[str]:
    return [f for f in drift(stored, fresh) if f in CONTRADICTING]

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
        raise DeskPublishError(f"row {row.key!r} came from desk {vias[0]!r} with no registration")
    clocks = _stated_clocks(row)
    clock_hole: Optional[str] = None
    clock_disputed = False
    start_time: Optional[str] = None
    if len(clocks) == 1:
        start_time = clocks[0]
    elif len(clocks) > 1:
        clock_hole = f"{len(clocks)} times stated"
        clock_disputed = True
    elif row.night:
        clock_hole = "date printed, clock not printed"
    else:
        clock_hole = "date not printed"
    hold_reason = existence_hold(door_readable=True, title=row.title, listing_url=_listing_url(row), is_fixture=(mode != LIVE))
    listing_url = _listing_url(row)
    desk_note = {"key": ingest_key(row), "union_key": row.key, "basis": row.basis, "night": row.night, "vias": list(vias), "doors": sorted({m.row.door_id for m in row.members}), "kind": row.kind, "kind_source": row.kind_source, "titles": list(row.titles), "clocks_stated": clocks, "clock_hole": clock_hole, "clock_disputed": clock_disputed, "held": hold_reason, "walk_mode": mode, "statement": _statement(row, clocks, listing_url)}
    extracted: Dict[str, Any] = {"title": row.title, "start_time": start_time, "start_date": row.night, "clock_stated": bool(start_time), "end_time": None, "venue_name": row.place_text, "city": None, "artist_names": [], "ticket_link": None, "rsvp_link": None, "is_private_rsvp": False, "private_access": {}, DESK_KEY: desk_note}
    if clock_disputed:
        extracted["start_times"] = [{"source": registrations[m.via].source_name, "at": m.row.when} for m in row.members if m.row.when and m.row.when_precision == "datetime" and m.via in registrations]
    if listing_url:
        extracted["listing_url"] = listing_url
    raw_lines = [f"{m.via}: {_quote(row, m)}" for m in row.members]
    raw_lines.append(f"[1Live desk walk — key {desk_note['key']}]")
    evidence = []
    for member in row.members:
        reg = registrations.get(member.via)
        if reg is None:
            raise DeskPublishError(f"row {row.key!r} carries desk {member.via!r} with no registration")
        evidence.append(Evidence(source_class=reg.source_class, source_name=reg.source_name, source_url=member.row.listing_url or member.row.source_url, quote=_quote(row, member)))
    return CandidateWrite(ingest_key=desk_note["key"], source_name=first.source_name, source_class=first.source_class, source_url=row.members[0].row.source_url, raw_text="\n".join(raw_lines), extracted=extracted, evidence=evidence, vias=vias, clock_hole=clock_hole, clock_disputed=clock_disputed, hold_reason=hold_reason)

def refuse_fixture_write(one: DeskUnion) -> None:
    if one.mode != LIVE:
        raise DeskPublishError(f"refusing to write a {one.mode} union: fixtures never reach the catalog")

def plan(one: DeskUnion, registrations: Mapping[str, DeskRegistration]) -> List[CandidateWrite]:
    return [write_for(row, registrations, mode=one.mode) for row in one.rows]

def plan_digest(writes: Sequence[CandidateWrite]) -> Dict[str, Any]:
    held = sum(1 for w in writes if w.hold_reason)
    public = [w for w in writes if not w.hold_reason]
    return {"rows": len(writes), "timed": sum(1 for w in writes if w.start_time), "clock_holes": sum(1 for w in writes if w.clock_hole), "held": held, "clock_disputed": sum(1 for w in writes if w.clock_disputed), "publishable": len(writes) - held, "publish_timed": sum(1 for w in public if w.start_time), "publish_disputed": sum(1 for w in public if w.clock_disputed), "tba_public": sum(1 for w in public if not w.start_time and not w.clock_disputed), "dated": sum(1 for w in writes if str(w.extracted.get(DESK_KEY, {}).get("night") or "").strip()), "placed": sum(1 for w in writes if str(w.extracted.get("venue_name") or "").strip()), "single_desk": sum(1 for w in writes if w.single_desk), "multi_desk": sum(1 for w in writes if not w.single_desk), "by_source": _by_source(writes)}

def _by_source(writes: Sequence[CandidateWrite]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for w in writes:
        for via in w.vias:
            out[via] = out.get(via, 0) + 1
    return dict(sorted(out.items()))

def extracted_json(write: CandidateWrite) -> str:
    return json.dumps(write.extracted, sort_keys=True, default=str)
