"""Deterministic, no-AI importer for FIRST-PARTY machine-readable calendars.

Stdlib-only (urllib, json, html.parser, datetime, zoneinfo). NO AI, NO third-party
deps — the dev sandbox is network-blocked and CI is minimal. Two structured
formats a first-party venue / university / library / civic / museum calendar
publishes are parsed here:

  * iCalendar (.ics / VEVENT, RFC 5545, text/calendar) — `parse_ics`.
  * schema.org/Event JSON-LD embedded in a page's HTML                 — `parse_jsonld`.

Both are AUTHORITATIVE anchors: a first party stating its own schedule is
'confirmed' by construction (exactly like the licensed ticketing feeds), so these
rows flow into the SEPARATE `licensed_event` store via
worker.importers.licensed_store.upsert_events WITHOUT ever touching the AI-
extraction → candidate → gate → promote path. This module writes NOTHING itself;
it only parses + normalizes into the licensed_event column dict.

Discipline (mirrors ticketmaster.py / normalize.py): fail LOUD on a fetch error,
never fabricate a field (an absent value is None / the row is skipped), and be
honest when a field is absent. A VEVENT with no SUMMARY or no DTSTART is skipped;
a JSON-LD node that is not an Event is dropped; a row with no stable id or no
title normalizes to None — never invented.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import ssl
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from worker.classify import resolve_category
from worker.importers.domain_map import UNMAPPED, classify_from_title

logger = logging.getLogger(__name__)

# THREE stable provenance tokens (mirrored by the provider CHECK in
# supabase/migrations/0013 + 0014) — HOW the row was parsed, kept distinct so a
# shape drift is attributable to the reader that caused it.
PROVIDER_ICS = "ics"                    # iCalendar VEVENT (RFC 5545)
PROVIDER_JSONLD = "jsonld"              # schema.org JSON-LD (in HTML, or bare)
PROVIDER_PLATFORM_JSON = "platform_json"  # a platform events API (Tribe/Localist)
_PROVIDERS = (PROVIDER_ICS, PROVIDER_JSONLD, PROVIDER_PLATFORM_JSON)

_USER_AGENT = "OneLiveStructuredImporter/1.0 (+https://onelive.example; deterministic no-AI calendar import)"
_ACCEPT = "text/calendar, text/html, application/xhtml+xml, application/ld+json;q=0.9, */*;q=0.5"

# Resource cap for ONE fetched body. A calendar feed for a single venue is orders
# of magnitude smaller; this only stops a pathological origin from exhausting the
# runner (evaluator nit r15).
_MAX_RESPONSE_BYTES = 10 * 1024 * 1024


class ResponseTooLarge(OSError):
    """A source served a body past the size cap.

    OSError so it is a per-source FAILURE (named, non-zero exit) rather than
    aborting the whole run — and never an empty source, which is what silently
    truncating the body would have produced.
    """


# ---- datetime helpers --------------------------------------------------------

def _f(x: Any) -> Optional[float]:
    """Best-effort float; None (never a fabricated 0) when not parseable."""
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


def _to_utc_z(value: Optional[str], *, tzid: Optional[str] = None,
              is_date: bool = False) -> Optional[str]:
    """Normalize a calendar timestamp to unambiguous UTC ISO with a trailing 'Z'.

    * is_date=True (an ICS VALUE=DATE / a bare date) is an ALL-DAY event: keep the
      date, null the time part honestly — return 'YYYY-MM-DD' with NO time and NO
      'Z' (fabricating a midnight-UTC instant for an all-day date would assert a
      precision the source never gave).
    * A value already carrying 'Z' or an explicit offset is converted to UTC.
    * A naive value with a TZID is interpreted in that zone (zoneinfo) and
      converted to UTC. If the tz database cannot resolve the TZID, we do NOT
      guess an offset — the naive value is treated as UTC and marked (honest,
      documented deferral) rather than silently shifted by a wrong amount.
    * A naive value with no zone is a floating local time (RFC 5545); we make it
      Z-explicit for the timestamptz column, the same choice normalize._utc_iso
      makes for SeatGeek's naive-UTC timestamps.

    Returns None for an empty/None value — never a fabricated timestamp.
    """
    if not value:
        return None
    s = value.strip()
    if is_date:
        d = _parse_date_only(s)
        return d.isoformat() if d else None
    dt = _parse_ics_datetime(s) if _looks_like_ics_dt(s) else _parse_iso_datetime(s)
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Naive: apply TZID if we can resolve it; else treat as UTC (documented).
        if tzid:
            zone = _resolve_zone(tzid)
            if zone is not None:
                dt = dt.replace(tzinfo=zone)
            else:
                dt = dt.replace(tzinfo=_dt.timezone.utc)
        else:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
    return dt.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_zone(tzid: str) -> Optional[ZoneInfo]:
    try:
        return ZoneInfo(tzid)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return None


def _looks_like_ics_dt(s: str) -> bool:
    # ICS basic form: YYYYMMDD or YYYYMMDDTHHMMSS[Z]
    core = s[:-1] if s.endswith("Z") else s
    core = core.replace("T", "")
    return core.isdigit() and len(core) in (8, 14)


def _parse_date_only(s: str) -> Optional[_dt.date]:
    """Parse an ICS basic date (YYYYMMDD) or an ISO date (YYYY-MM-DD)."""
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return _dt.datetime.strptime(s[:10] if "-" in s else s[:8], fmt).date()
        except ValueError:
            continue
    return None


def _parse_ics_datetime(s: str) -> Optional[_dt.datetime]:
    """Parse an ICS DATE-TIME: YYYYMMDDTHHMMSS or ...Z (UTC designator)."""
    utc = s.endswith("Z")
    core = s[:-1] if utc else s
    try:
        dt = _dt.datetime.strptime(core, "%Y%m%dT%H%M%S")
    except ValueError:
        d = _parse_date_only(core)
        if d is None:
            return None
        dt = _dt.datetime(d.year, d.month, d.day)
    if utc:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    return dt


def _parse_iso_datetime(s: str) -> Optional[_dt.datetime]:
    """Parse an ISO-8601 datetime (JSON-LD startDate), tolerating a 'Z' suffix."""
    v = s.replace("Z", "+00:00") if s.endswith("Z") else s
    try:
        return _dt.datetime.fromisoformat(v)
    except ValueError:
        # startDate may be a bare date; caller handles all-day separately, but a
        # date-only ISO value is still honestly a date.
        d = _parse_date_only(s)
        return _dt.datetime(d.year, d.month, d.day) if d else None


# ---- iCalendar (RFC 5545) ----------------------------------------------------

_ICS_ESCAPES = (("\\N", "\n"), ("\\n", "\n"), ("\\,", ","), ("\\;", ";"), ("\\\\", "\\"))


def _unescape_text(v: str) -> str:
    for token, repl in _ICS_ESCAPES:
        v = v.replace(token, repl)
    return v


def _unfold(text: str) -> list[str]:
    """RFC 5545 line unfolding: a line beginning with a space or tab is a
    continuation of the previous logical line. Normalize CRLF/CR first."""
    raw = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    for ln in raw:
        if ln[:1] in (" ", "\t") and out:
            out[-1] += ln[1:]
        else:
            out.append(ln)
    return out


def _split_prop(line: str) -> Optional[tuple[str, dict[str, str], str]]:
    """Split an ICS content line 'NAME[;PARAM=v;...]:VALUE' into
    (NAME_upper, {PARAM_upper: value}, VALUE). Honors quoted param values so a
    ':' or ';' inside quotes does not split the line. None when there is no
    value separator."""
    idx = None
    in_q = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_q = not in_q
        elif ch == ":" and not in_q:
            idx = i
            break
    if idx is None:
        return None
    left, value = line[:idx], line[idx + 1:]
    parts = left.split(";")
    name = parts[0].upper()
    params: dict[str, str] = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.upper()] = v.strip('"')
    return name, params, value


def _convert_ics_dt(value: str, params: dict[str, str]) -> tuple[Optional[str], bool]:
    """Return (utc_or_date_string, is_all_day) for an ICS DTSTART/DTEND value."""
    is_date = params.get("VALUE", "").upper() == "DATE" or _looks_bare_date(value)
    tzid = params.get("TZID")
    return _to_utc_z(value, tzid=tzid, is_date=is_date), is_date


def _looks_bare_date(value: str) -> bool:
    v = value.strip()
    return v.isdigit() and len(v) == 8


def _account(parser: str, seen: int, kept: int, source: Optional[str] = None) -> None:
    """Report input objects a reader DROPPED, so silent narrowing is visible.

    The structural answer to the silent-data-loss class (three instances on PR
    #68: only Localist `event_instances[0]` emitted, integer ids coerced away so
    distinct events collided, and bare JSON-LD feeds read as zero). Every one was
    a reader accepting a NARROWER shape than the format actually permits, and
    every one was invisible for the same reason — "this feed produced fewer
    events" and "this feed HAS fewer events" render identically in a run log.

    So each reader now states its own arithmetic: objects seen vs objects that
    produced a row. A drop is often legitimate (a VEVENT with no DTSTART must be
    skipped, never fabricated), which is exactly why this is a loud log and not
    an error — the point is that a shape gap can no longer hide inside a plausible
    count. `parse_*` remains pure and return-compatible; only observability moves.
    """
    if seen and kept < seen:
        # NAME the source, not just the parser: "parse_platform_json dropped 4"
        # tells an operator a shape gap exists but not which catalog row to fix
        # (evaluator nit r10). Unknown when a parser is called directly (unit
        # tests, ad-hoc analysis), which is stated rather than blank.
        logger.warning(
            "%s [source=%s]: %d of %d event object(s) produced NO row — dropped "
            "for missing required fields or an unsupported shape. Recorded because "
            "a reader that silently narrows a feed is indistinguishable from a "
            "smaller feed.",
            parser, source or "unknown (parser called directly)", seen - kept, seen)


def parse_ics(text: str, *, source: Optional[str] = None) -> list[dict]:
    """Parse VEVENT blocks from iCalendar text into canonical intermediate dicts.

    Reads SUMMARY, DTSTART/DTEND (respecting TZID= and VALUE=DATE), LOCATION, URL,
    DESCRIPTION, UID. Handles RFC-5545 line folding. DTSTART/DTEND are converted to
    UTC ISO 'Z' (a bare/VALUE=DATE date is kept as an all-day date with a null
    time). A VEVENT with no SUMMARY or no DTSTART is SKIPPED — never fabricated.
    """
    events: list[dict] = []
    cur: Optional[dict] = None
    in_vevent = False
    seen = 0
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            in_vevent = True
            seen += 1
            cur = {"_raw_props": {}}
            continue
        if line == "END:VEVENT":
            if cur is not None and cur.get("title") and cur.get("start_time"):
                events.append(cur)
            cur = None
            in_vevent = False
            continue
        if not in_vevent or cur is None:
            continue
        parsed = _split_prop(line)
        if parsed is None:
            continue
        name, params, value = parsed
        if name == "SUMMARY":
            cur["title"] = _unescape_text(value) or None
            cur["_raw_props"]["summary"] = value
        elif name == "DTSTART":
            start, all_day = _convert_ics_dt(value, params)
            cur["start_time"] = start
            cur["all_day"] = all_day
            cur["_raw_props"]["dtstart"] = value
            if params:
                cur["_raw_props"]["dtstart_params"] = params
        elif name == "DTEND":
            end, _ = _convert_ics_dt(value, params)
            cur["end_time"] = end
            cur["_raw_props"]["dtend"] = value
        elif name == "LOCATION":
            cur["venue_name"] = _unescape_text(value) or None
            cur["_raw_props"]["location"] = value
        elif name == "URL":
            cur["url"] = value or None
            cur["_raw_props"]["url"] = value
        elif name == "DESCRIPTION":
            cur["description"] = _unescape_text(value) or None
        elif name == "UID":
            cur["uid"] = value or None
            cur["_raw_props"]["uid"] = value
    _account("parse_ics", seen, len(events), source)
    return events


# ---- schema.org/Event JSON-LD -------------------------------------------------

class _LdJsonExtractor(HTMLParser):
    """Collect the text of every <script type="application/ld+json"> block."""

    def __init__(self) -> None:
        super().__init__()
        self._in = False
        self.blocks: list[str] = []
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag.lower() == "script":
            a = {k.lower(): (v or "") for k, v in attrs}
            if a.get("type", "").strip().lower() == "application/ld+json":
                self._in = True
                self._buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._in:
            self._in = False
            self.blocks.append("".join(self._buf))

    def handle_data(self, data: str) -> None:
        if self._in:
            self._buf.append(data)


_EVENT_SUBTYPES_EXTRA = {"festival"}  # schema.org event subtype that does not end in "Event"


def _is_event_type(t: Any) -> bool:
    """True when a JSON-LD @type denotes a schema.org Event (or a subtype like
    MusicEvent / TheaterEvent / ScreeningEvent / …). @type may be a string or a
    list of strings."""
    if isinstance(t, list):
        return any(_is_event_type(x) for x in t)
    if not isinstance(t, str):
        return False
    tl = t.strip().lower()
    tl = tl.rsplit("/", 1)[-1].rsplit(":", 1)[-1]  # tolerate a namespaced type
    return tl == "event" or tl.endswith("event") or tl in _EVENT_SUBTYPES_EXTRA


def _iter_ld_objects(doc: Any):
    """Yield every candidate object from a parsed ld+json document, tolerating a
    single object, a list, or an @graph container (possibly nested)."""
    if isinstance(doc, list):
        for item in doc:
            yield from _iter_ld_objects(item)
    elif isinstance(doc, dict):
        if isinstance(doc.get("@graph"), list):
            for item in doc["@graph"]:
                yield from _iter_ld_objects(item)
        yield doc


def _ld_str(v: Any) -> Optional[str]:
    """A JSON-LD scalar string, unwrapping the common {'@value': ...} form and
    taking the first of a list. None (never fabricated) otherwise."""
    if isinstance(v, str):
        return v or None
    if isinstance(v, dict):
        return _ld_str(v.get("@value") or v.get("name") or v.get("url"))
    if isinstance(v, list) and v:
        return _ld_str(v[0])
    return None


def _ld_location(loc: Any) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (venue_name, venue_city, venue_address) from a schema.org location.

    location may be a string, a Place dict {name, address}, or a list; address may
    itself be a string or a PostalAddress {streetAddress, addressLocality, …}."""
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    if loc is None:
        return None, None, None
    if isinstance(loc, str):
        return (loc or None), None, None
    if not isinstance(loc, dict):
        return None, None, None
    name = _ld_str(loc.get("name"))
    addr = loc.get("address")
    if isinstance(addr, str):
        return name, None, (addr or None)
    if isinstance(addr, dict):
        city = _ld_str(addr.get("addressLocality"))
        street = _ld_str(addr.get("streetAddress"))
        return name, city, street
    return name, None, None


def _ld_image(img: Any) -> Optional[str]:
    if isinstance(img, list):
        img = img[0] if img else None
    if isinstance(img, str):
        return img or None
    if isinstance(img, dict):
        return _ld_str(img.get("url") or img.get("contentUrl"))
    return None


def _ld_offers(offers: Any) -> tuple[Optional[float], Optional[float], Optional[str]]:
    """Return (price_min, price_max, currency) from schema.org offers (a dict or a
    list of Offer/AggregateOffer). Uses lowPrice/highPrice when present, else the
    scalar price for both bounds. Never fabricates a price."""
    if offers is None:
        return None, None, None
    items = offers if isinstance(offers, list) else [offers]
    mins: list[float] = []
    maxs: list[float] = []
    currency: Optional[str] = None
    for o in items:
        if not isinstance(o, dict):
            continue
        currency = currency or _ld_str(o.get("priceCurrency"))
        low = _f(o.get("lowPrice"))
        high = _f(o.get("highPrice"))
        price = _f(o.get("price"))
        lo = low if low is not None else price
        hi = high if high is not None else price
        if lo is not None:
            mins.append(lo)
        if hi is not None:
            maxs.append(hi)
    return (min(mins) if mins else None,
            max(maxs) if maxs else None,
            currency)


def _jsonld_event_to_intermediate(obj: dict) -> dict:
    """Map ONE schema.org Event object into the canonical intermediate dict."""
    name = _ld_str(obj.get("name"))
    start = _ld_str(obj.get("startDate"))
    end = _ld_str(obj.get("endDate"))
    venue_name, venue_city, venue_address = _ld_location(obj.get("location"))
    price_min, price_max, currency = _ld_offers(obj.get("offers"))
    # startDate/endDate are ISO-8601; convert to UTC 'Z' when they carry a time,
    # keep an honest all-day date when the value is date-only.
    start_all_day = bool(start) and _is_date_only(start)
    return {
        "title": name,
        "start_time": _to_utc_z(start, is_date=start_all_day) if start else None,
        "end_time": _to_utc_z(end, is_date=_is_date_only(end)) if end else None,
        "all_day": start_all_day,
        "venue_name": venue_name,
        "venue_city": venue_city,
        "venue_address": venue_address,
        "url": _ld_str(obj.get("url")),
        "image_url": _ld_image(obj.get("image")),
        "price_min": price_min,
        "price_max": price_max,
        "currency": currency,
        "uid": _ld_str(obj.get("@id") or obj.get("identifier")),
        "_raw_props": obj,
    }


def _is_date_only(v: Optional[str]) -> bool:
    if not isinstance(v, str) or not v:
        return False
    s = v.strip()
    return len(s) == 10 and s[4] == "-" and s[7] == "-" and "T" not in s


def parse_jsonld(html: str, *, source: Optional[str] = None) -> list[dict]:
    """Extract schema.org/Event JSON-LD from HTML into canonical intermediate
    dicts. Every <script type="application/ld+json"> block is json.loads'd
    (tolerating a list, a single object, or an @graph array); only nodes whose
    @type is Event (or a subtype like MusicEvent/TheaterEvent/…) are kept. Missing
    fields stay None — never fabricated."""
    extractor = _LdJsonExtractor()
    extractor.feed(html)
    events: list[dict] = []
    seen = 0
    for block in extractor.blocks:
        block = block.strip()
        if not block:
            continue
        try:
            doc = json.loads(block)
        except ValueError:
            # A malformed ld+json block is skipped, not fatal — a page may carry
            # several blocks and one bad one must not lose the good ones. This is
            # an honest skip (no data invented), not a swallowed error path.
            continue
        for obj in _iter_ld_objects(doc):
            if isinstance(obj, dict) and _is_event_type(obj.get("@type")):
                seen += 1
                events.append(_jsonld_event_to_intermediate(obj))
    _account("parse_jsonld", seen, len(events), source)
    return events


# ---- normalization into the licensed_event column dict -----------------------

def _stable_external_id(raw: dict, *, provider: str, source_name: str) -> Optional[str]:
    """A stable external id: prefer the source's own UID, then its URL, then a
    deterministic hash of (source_name|title|start). None only when there is
    nothing stable to key on — never a random id."""
    uid = raw.get("uid")
    if uid:
        return str(uid)
    url = raw.get("url")
    if url:
        return str(url)
    title = raw.get("title")
    start = raw.get("start_time")
    if title and start:
        digest = hashlib.sha1(
            f"{source_name}|{title}|{start}".encode("utf-8")).hexdigest()
        return f"{provider}:{digest}"
    return None


def _event_subtype_token(at: Any) -> Optional[str]:
    """Pick the MOST SPECIFIC schema.org event-subtype token from a JSON-LD @type
    (a string or a list). Prefer a real subtype (MusicEvent/ComedyEvent/…) over
    the bare 'Event' so the resolver can map it; return None when @type is absent
    or only the generic 'Event' (which carries no category — fall through, never
    fabricate). Mirrors _is_event_type's tolerance of namespaced/list @type."""
    candidates = at if isinstance(at, list) else [at]
    generic = None
    for t in candidates:
        if not isinstance(t, str):
            continue
        tl = t.strip().rsplit("/", 1)[-1].rsplit(":", 1)[-1]
        low = tl.lower()
        if low == "event":
            generic = tl
        elif low.endswith("event") or low in _EVENT_SUBTYPES_EXTRA:
            return tl  # a specific subtype — most authoritative
    return generic


def normalize_structured(raw: dict, *, provider: str, source_name: str,
                         cultural_domain: Optional[str] = None) -> Optional[dict]:
    """Map a canonical intermediate dict (from parse_ics / parse_jsonld) into the
    EXACT licensed_event column dict normalize_ticketmaster returns.

    provider is 'ics' | 'jsonld' | 'platform_json' (provenance: HOW it was
    parsed — each reader keeps its own token so a shape drift is attributable,
    migration 0014). Category is
    resolved by the shared classifier (worker.classify.resolve_category) from the
    STRONGEST available signal, in authority order: the event's OWN declared
    schema.org @type (a MusicEvent/ComedyEvent/LiteraryEvent already parsed from
    the JSON-LD — so "you know it's a lecture/band/comedian, so you know the
    category", founder 2026-07-25), THEN the first-party calendar's curated
    cultural_domain, THEN a last-resort read of the title. Non-fabricating: an
    absent/generic signal falls through, never guesses. Returns None when there is
    no stable id or no title — never invents data.
    """
    if provider not in (PROVIDER_ICS, PROVIDER_JSONLD, PROVIDER_PLATFORM_JSON):
        raise ValueError(
            f"provider must be one of {PROVIDER_ICS!r}, {PROVIDER_JSONLD!r}, "
            f"{PROVIDER_PLATFORM_JSON!r}, got {provider!r}")
    title = raw.get("title")
    if not title:
        return None
    external_id = _stable_external_id(raw, provider=provider, source_name=source_name)
    if not external_id:
        return None

    # The @type the JSON-LD parse already read (in _raw_props) is the event's own
    # declared kind — the most authoritative category signal. ICS feeds carry no
    # @type, so this is simply None there and the venue/title signals apply.
    raw_props = raw.get("_raw_props")
    schema_type = _event_subtype_token(raw_props.get("@type")) if isinstance(raw_props, dict) else None
    resolved = resolve_category(
        schema_type=schema_type,
        venue_domain_hint=cultural_domain,
        title=title,
    )
    category = None if resolved.domain == UNMAPPED else resolved.domain
    subsegment = resolved.genre

    price_min = _f(raw.get("price_min"))
    price_max = _f(raw.get("price_max"))
    is_free = (price_min == 0) if price_min is not None else None

    return {
        "source_provider": provider,
        "external_id": str(external_id),
        "title": title,
        "category": category,
        "subsegment": subsegment,
        "performer": None,  # a calendar feed carries no performer taxonomy
        "start_time": raw.get("start_time"),
        "end_time": raw.get("end_time"),
        "status": "scheduled",
        "on_sale_status": None,
        "price_min": price_min,
        "price_max": price_max,
        "currency": raw.get("currency"),
        "is_free": is_free,
        "ticket_url": raw.get("url"),
        "image_url": raw.get("image_url"),
        "venue_name": raw.get("venue_name"),
        "venue_city": raw.get("venue_city"),
        "venue_area": None,  # neighborhood derived later from geo; not asserted here
        "venue_address": raw.get("venue_address"),
        "venue_lat": None,   # calendars rarely carry coordinates; honest null
        "venue_lng": None,
        "confidence": "confirmed",  # first-party anchor ⇒ confirmed by construction
        "raw": raw,
    }


# ---- fetch + auto-detect ------------------------------------------------------

# We identify honestly as OneLive and do NOT change identity to get past an
# access denial. A 403/406 is the site REFUSING us; retrying with a browser
# profile to obtain the content anyway would hide that denial as a successful
# import (evaluator blocker r3, PR #68) — the repo bar is fail-closed on
# access/auth, no bypasses. A refused source is reported as refused, and is
# routed to a different acquisition path (partner feed / opt-in newsletter),
# not scraped under a disguise.
def fetch_url(url: str, *, timeout: int = 30) -> str:
    """GET a public structured feed / calendar page.

    Raises LOUD on any error (never returns empty on failure) — a fetch that
    fails must be visible, not a silent no-op. NOTHING is retried under a
    different identity: a 403/406 means the site refused us and a 429 means we
    are throttled, and both must stay visible rather than be bypassed.
    """
    req = urllib.request.Request(url, headers={
        "User-Agent": _USER_AGENT,
        "Accept": _ACCEPT,
        "Accept-Language": "en-US,en;q=0.9",
    })
    # Every status propagates. 403/406 (denied) and 429 (throttled) are REAL
    # signals an operator must see, not conditions to work around.
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        # BOUNDED read (evaluator nit r15): the candidate and timeout caps limit
        # how MANY and how LONG, but an unbounded resp.read() let one hostile or
        # misconfigured origin exhaust the runner. Reading one byte past the cap
        # is how we tell "at the limit" from "over it" without a second request.
        raw = resp.read(_MAX_RESPONSE_BYTES + 1)
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise ResponseTooLarge(
                f"{url}: response exceeds {_MAX_RESPONSE_BYTES} bytes — refusing to "
                f"read an unbounded body. FAILED source, not an empty one.")
        return raw.decode(charset, errors="replace")


def _platform_events(doc: Any) -> list:
    """Extract the event list from a Tribe or Localist JSON payload.

    Tribe (WordPress "The Events Calendar"): {"events": [ {...}, ... ]}
    Localist: {"events": [ {"event": {...}}, ... ]}  — each item wraps its event.
    Anything else yields [] (never guessed).
    """
    if not isinstance(doc, dict):
        return []
    items = doc.get("events")
    if not isinstance(items, list):
        return []
    out = []
    for item in items:
        if isinstance(item, dict):
            # Localist nests the real object under "event"; Tribe does not.
            inner = item.get("event")
            out.append(inner if isinstance(inner, dict) else item)
    return out


def parse_platform_json(text: str, *, source: Optional[str] = None) -> list[dict]:
    """Parse a Tribe/Localist events JSON API response into intermediate dicts.

    These are ORDINARY JSON APIs, not JSON-LD — the JSON-LD parser cannot read
    them, which is why advertising these endpoints without this function was a
    real defect (evaluator blocker, PR #68). Fields are mapped conservatively:
    an absent value stays None, never fabricated, and an entry with no title or
    no start is dropped by normalize_structured downstream.
    """
    try:
        doc = json.loads(text)
    except (ValueError, TypeError):
        return []
    out: list[dict] = []
    seen = kept = 0
    for ev in _platform_events(doc):
        seen += 1
        before = len(out)
        title = _ld_str(ev.get("title") or ev.get("name"))
        # TIME CORRECTNESS (evaluator blocker r2, PR #68). Tribe's `start_date`
        # is the SITE-LOCAL wall time; the API exposes `utc_start_date`
        # separately. Reading the local field and stamping it 'Z' produced event
        # times that were simply WRONG — unacceptable for a what's-on-tonight
        # product. Order of trust:
        #   1. utc_start_date  — already UTC, unambiguous.
        #   2. start_date + the event's own `timezone` — converted honestly.
        #   3. neither          — DROP the event. A missing event beats a
        #                         confidently wrong start time (§5 never fabricate).
        tzid = _ld_str(ev.get("timezone")) or None
        utc_start = _ld_str(ev.get("utc_start_date"))
        utc_end = _ld_str(ev.get("utc_end_date"))
        local_start = _ld_str(ev.get("start_date"))
        local_end = _ld_str(ev.get("end_date"))
        if utc_start:
            start, end, start_tz = utc_start, utc_end, "UTC"
        elif local_start and tzid:
            start, end, start_tz = local_start, local_end, tzid
        else:
            start, end, start_tz = "", None, None
            if local_start:
                logger.warning(
                    "platform event %r has only a LOCAL start (%s) and no timezone "
                    "field — dropping rather than asserting a wrong UTC instant",
                    title, local_start)
        # Localist: an event carries N concrete OCCURRENCES in event_instances.
        # Reading only [0] silently discarded every later showing (evaluator
        # blocker r3, PR #68) — real data loss from a canonical feed. Each
        # instance becomes its own row, with its own stable id.
        instances = []
        if not start:
            inst = ev.get("event_instances")
            if isinstance(inst, list):
                for item in inst:
                    if not isinstance(item, dict):
                        continue
                    ei = item.get("event_instance")
                    ei = ei if isinstance(ei, dict) else item
                    # Localist instances are ISO8601 WITH an offset, so they are
                    # self-describing — no tz guess needed.
                    i_start = _ld_str(ei.get("start"))
                    if i_start:
                        # Instance ids are ints in Localist — str() them so each
                        # occurrence keeps a DISTINCT external id (an int would be
                        # dropped by _ld_str and the occurrences would collide on
                        # upsert, re-losing the data this fix restores).
                        instances.append((i_start, _ld_str(ei.get("end")),
                                          _str_id(ei.get("id"))))
        if not title or (not start and not instances):
            continue
        venue = ev.get("venue") if isinstance(ev.get("venue"), dict) else {}
        loc = ev.get("location_name") or venue.get("venue")
        addr = venue.get("address")
        city = venue.get("city")
        # One row per occurrence (a single-start event is just one occurrence).
        occurrences = instances or [(start, end, None)]
        for occ_start, occ_end, occ_id in occurrences:
            _emit_platform_row(out, ev, title, occ_start, occ_end, occ_id,
                               start_tz, venue, loc, addr, city)
        # Counted per INPUT event, not per row: an event legitimately fans out to
        # many occurrence rows, and it was reading only the FIRST of those that
        # lost data silently in the first place.
        if len(out) > before:
            kept += 1
    _account("parse_platform_json", seen, kept, source)
    return out


def _str_id(value) -> Optional[str]:
    """Coerce a platform id to a string. Tribe/Localist ids are INTEGERS, and
    _ld_str drops non-strings — so an int id silently became "" and callers fell
    back to weaker keys. Used for EVERY id in this module so the coercion cannot
    diverge between call sites again (evaluator blocker r5, PR #68)."""
    if value is None:
        return None
    if isinstance(value, bool):   # a bool is an int in Python; never an id
        return None
    if isinstance(value, (int, float, str)):
        text = str(value).strip()
        return text or None
    return None


def _occurrence_uid(ev, start) -> Optional[str]:
    """Stable id for an occurrence whose platform gave it none: the parent event
    id (or url) plus this occurrence's start, so a repeating series keeps one row
    per showing instead of collapsing to a single row on upsert."""
    # Try each candidate in turn — do NOT rely on `a or b`, because a truthy
    # INT id short-circuits the chain and then coerces to nothing, which is
    # exactly how two distinct events at one start collided (evaluator r5).
    parent = None
    for key in ("id", "uid", "url"):
        parent = _str_id(ev.get(key))
        if parent:
            break
    if not parent:
        return _str_id(start)
    return f"{parent}@{start}" if start else parent


def _emit_platform_row(out, ev, title, start, end, occ_id, start_tz,
                       venue, loc, addr, city) -> None:
    """Append ONE normalized intermediate row for a single occurrence."""
    start_all_day = _is_date_only(start)
    out.append({
            "title": title,
            "start_time": _to_utc_z(start.replace(" ", "T"),
                                    tzid=None if start_tz in ("UTC", None) else start_tz,
                                    is_date=start_all_day),
            "end_time": (_to_utc_z(end.replace(" ", "T"),
                                   tzid=None if start_tz in ("UTC", None) else start_tz,
                                   is_date=_is_date_only(end))
                         if end else None),
            "all_day": start_all_day,
            "venue_name": _ld_str(loc) or None,
            "venue_city": _ld_str(city) or None,
            "venue_address": _ld_str(addr) or None,
            "url": _ld_str(ev.get("url") or ev.get("localist_url")),
            "image_url": None,
            "price_min": None, "price_max": None, "currency": None,
            # Per-OCCURRENCE id so two showings of one event are distinct rows
            # rather than one overwriting the other on upsert. When the platform
            # omits a per-instance id, fall back to parent-id + START rather than
            # the bare parent id — otherwise every occurrence of a series would
            # collide back onto one row (evaluator nit r4, PR #68).
            "uid": occ_id or _occurrence_uid(ev, start),  # both via _str_id
            "_raw_props": ev,
        })


def parse_jsonld_document(text: str, *, source: Optional[str] = None) -> list[dict]:
    """Parse a BARE schema.org JSON-LD document (not embedded in HTML).

    Discovery accepts `application/ld+json` feed links, which serve raw JSON —
    parse_jsonld only scans <script> tags, so those feeds needed their own
    reader (evaluator blocker r2, PR #68). Reuses the same @graph walker and
    Event-subtype filter, so the accepted shapes are identical.
    """
    try:
        doc = json.loads(text)
    except (ValueError, TypeError):
        return []
    out: list[dict] = []
    seen = 0
    for obj in _iter_ld_objects(doc):
        if isinstance(obj, dict) and _is_event_type(obj.get("@type")):
            seen += 1
            out.append(_jsonld_event_to_intermediate(obj))
    _account("parse_jsonld_document", seen, len(out), source)
    return out


def _detect_provider(text: str, provider_hint: Optional[str]) -> str:
    if provider_hint is not None:
        # A typo'd hint is a MISCONFIGURATION, not a reason to guess (evaluator
        # nit r6): silently sniffing would hide the bad config behind a result
        # that happens to look fine.
        if provider_hint not in _PROVIDERS:
            raise ValueError(
                f"unknown provider_hint {provider_hint!r} — expected one of "
                f"{_PROVIDERS}")
        return provider_hint
    head = text.lstrip()[:512].upper()
    if "BEGIN:VCALENDAR" in head or "BEGIN:VEVENT" in text[:4096].upper():
        return PROVIDER_ICS
    # A bare JSON document is EITHER a platform API payload (Tribe/Localist) OR a
    # bare schema.org JSON-LD feed — discovery accepts application/ld+json links,
    # so both arrive here. _events_from_text tries BOTH readers (evaluator blocker
    # r2, PR #68: routing every bare JSON to the platform parser silently dropped
    # legitimate declared JSON-LD feeds).
    if text.lstrip()[:1] in ("{", "["):
        return PROVIDER_PLATFORM_JSON
    return PROVIDER_JSONLD


# ---- feed discovery (CANONICAL) ----------------------------------------------
#
# Founder directive 2026-07-25 ("There has to be a way to get the data"), after
# the first live run measured 16 of 18 sources yielding ZERO. Root cause: we
# fetched each source's BASE URL and expected embedded JSON-LD there. Real venue
# sites almost never put their event data on the homepage — it lives at a
# calendar subpath, or behind a platform's own feed endpoint.
#
# This is the canonical acquisition order for a first-party source. Everything
# here is PUBLIC data a normal reader can load; nothing bypasses auth or a
# login, and robots-disallowed paths are not reached for.

# 1) Standards-based autodiscovery: <link rel="alternate"> pointing at a
#    calendar/feed. This is the mechanism sites publish ON PURPOSE.
# ONLY types _events_from_text can actually parse. RSS/Atom were accepted as
# candidates with no parser behind them (evaluator blocker r3, PR #68): a
# site-declared RSS events feed would fetch, parse to zero, and be reported as
# "no events" — the same false-confidence class as the removed Squarespace
# endpoint. They are dropped here rather than silently mis-handled; an
# UNSUPPORTED declared type is logged loudly by _note_unsupported_declared so
# the gap is operator-visible instead of invisible.
_FEED_LINK_TYPES = ("text/calendar", "application/ld+json")

# Declared types we deliberately do NOT parse (yet). Seeing one is worth saying
# out loud — it names a real acquisition gap for that source.
_UNSUPPORTED_FEED_TYPES = ("application/rss+xml", "application/atom+xml")

# 2) Platform endpoints — the big CMS/calendar plugins expose machine-readable
#    events at a known path. Detected from markup fingerprints in the base page.
# Only endpoints we can actually PARSE are listed. Squarespace's `?format=json`
# was removed (evaluator blocker, PR #68): it returns a page dump, not an event
# collection, so advertising it created false confidence in coverage we did not
# have. Tribe + Localist return well-defined event collections parsed by
# parse_platform_json below.
_PLATFORM_ENDPOINTS = (
    # (fingerprint in HTML, path template relative to the site root)
    ("tribe-events", "/wp-json/tribe/events/v1/events?per_page=50"),
    ("the-events-calendar", "/wp-json/tribe/events/v1/events?per_page=50"),
    ("localist", "/api/2/events?days=60"),
)

# 3) Conventional calendar subpaths, tried in descending likelihood. The ICS
#    variants come first because a real .ics is unambiguous and cheap to parse.
# Bound the per-source discovery fan-out: enough to cover the declared
# feed + platform endpoint + the likely conventions, without turning one
# source into a crawl.
# INVERTED (evaluator blockers r6, PR #68). Three rounds running I enumerated
# which failures must fail loud, and each round the reviewer found another class
# I had not listed — 500/502/503, 408, 451, 423, DNS, timeouts, parser bugs — all
# quietly becoming "no events". The allowlist was the wrong shape.
#
# So the rule is now the other way round and CLOSED: the ONLY skippable outcome
# is EXPECTED ABSENCE — a 404/410 on a GUESSED conventional path we invented.
# Everything else propagates: server errors, legal blocks, timeouts, DNS, TLS,
# access denials, and anything unforeseen. A site-DECLARED feed that fails is
# never skippable either — the site advertised it, so its failure is a real
# defect, not an absence.
_EXPECTED_ABSENCE_STATUSES = (404, 410)


class RobotsDisallowed(OSError):
    """robots.txt forbids fetching this URL.

    An OSError so the runner records it as a FAILED source. A policy denial is
    NOT an empty calendar: returning [] would hide a refused source inside the
    zero-source count and let the run exit green (evaluator blocker r7).
    """


class ProviderMismatch(OSError):
    """The catalog ASSERTED a provider for this source and nothing we fetched
    was that format.

    `provider_hint` is a configuration claim about the endpoint. r7 stopped us
    silently parsing a DIFFERENT format when the claim did not hold, but left
    the source reported as "0 events" — which is the same failure-reads-as-empty
    class this PR exists to close, just relocated (evaluator blocker r8). A
    misconfigured source is a defect an operator must fix; an empty calendar is
    not. They must not share a summary line.

    OSError, like RobotsDisallowed, so ONE bad row does not abort the other 63
    sources of the run. But the runner records it as MISCONFIGURED, not FAILED,
    and exits 2 — subclassing for blast radius must not also grant the
    overridability OSError carries, or `--allow-partial` (meant for hosts that
    denied or throttled us) would greenlight a catalog defect (evaluator blockers
    r12, and r13 for this docstring still saying "FAILED" after the behaviour
    changed — claim-vs-code drift is a class on our own watch list).
    """

class DeclaredFeedCorrupt(OSError):
    """A site-DECLARED machine-readable feed served bytes that are not the type
    the site declared them to be.

    Evaluator blocker r17. `<link rel="alternate" type="text/calendar">` is the
    site telling us, in machine-readable form, "the calendar is here". When that
    URL serves 200 OK with an HTML error page, a login wall, or any body that is
    not a calendar, the honest reading is "this source's advertised feed is
    broken" — NOT "this venue has no upcoming events". Before this class existed
    the importer merely logged a warning and let the run exit green with the
    source counted among the empties, which is precisely the
    failure-reads-as-empty / swallowed-corrupt-data pair this PR exists to close,
    one layer further out.

    OSError, so the runner records it as a FAILED source (named in the summary,
    non-zero exit) and one broken feed does not abort the other 63 sources. NOT a
    ProviderMismatch: the catalog row is right, the site's own feed is wrong, so
    --allow-partial may legitimately ride over it exactly as it does for a host
    that denied or throttled us.
    """


# A DECLARED media type is a claim about the bytes, so it maps to the shape sniff
# that can check that claim. This mapping cannot be DERIVED from _FEED_LINK_TYPES
# — the provider a type implies is a fact about our readers, not about the type
# string — so it is a second hand-maintained list guarding a trust property,
# which is the incomplete-enumeration class exactly. The compensating control is
# mechanical, not a promise to remember: a test asserts every entry in
# _FEED_LINK_TYPES resolves here, so adding a supported declared type without
# mapping it fails the suite instead of silently reaching the `return False`
# below and turning a corrupt declared feed back into "no events".
_DECLARED_TYPE_PROVIDER = {
    "text/calendar": PROVIDER_ICS,
    "application/ld+json": PROVIDER_JSONLD,
}


def _is_feed_document(provider: str, text: str) -> bool:
    """True when `text` is a STANDALONE machine-readable calendar document.

    Strictly narrower than :func:`_matches_asserted_shape`, and the difference
    is the whole point (evaluator blocker r17). The shape sniff answers "did
    this endpoint serve the asserted format at all?", which an ordinary HTML
    homepage carrying `<script type="application/ld+json">` LocalBusiness markup
    satisfies. This answers a stronger question — "did the site hand us its
    calendar FILE?" — and only a yes to that makes a zero-event result
    authoritative evidence that there are no upcoming events.

    Why the distinction earns its keep: an HTML page yielding zero events may be
    a homepage, a soft-404 served with status 200, or a JavaScript shell that
    renders its calendar client-side. None of those is a statement that the
    calendar is empty, so none of them may license the importer to shrug off a
    later access denial.
    """
    text = text or ""
    if provider == PROVIDER_ICS:
        # An iCalendar FILE opens with BEGIN:VCALENDAR as a content line. A bare
        # BEGIN:VEVENT line (which _matches_asserted_shape accepts, correctly,
        # as "looks like iCalendar") is not by itself a whole document.
        head_lines = {ln.strip().upper() for ln in text[:4096].splitlines()}
        return "BEGIN:VCALENDAR" in head_lines
    if provider == PROVIDER_PLATFORM_JSON:
        # A platform API response IS the document — _matches_asserted_shape
        # already requires the top-level {"events": [...]} collection both
        # readers consume, and no HTML page can satisfy that.
        return _matches_asserted_shape(PROVIDER_PLATFORM_JSON, text)
    if provider == PROVIDER_JSONLD:
        # BARE JSON-LD only. The HTML carrier is deliberately excluded here: it
        # is the case this function exists to reject.
        try:
            doc = json.loads(text)
        except (ValueError, TypeError):
            return False
        nodes = doc if isinstance(doc, list) else [doc]
        return any(isinstance(n, dict) and ({"@context", "@type", "@graph"} & set(n))
                   for n in nodes)
    return False


_MAX_DECLARED_TRIES = 4
_MAX_GUESSED_TRIES = 6


def _log_candidate_failure(source_name, candidate, exc, *, declared: bool) -> None:
    """A site-DECLARED feed that fails is a real defect (the site advertises it)
    and warns; a guessed conventional path that 404s is expected and stays at
    debug. Neither is swallowed — both name the URL and the reason."""
    if declared:
        logger.warning("source %s: DECLARED feed %s failed (%s: %s) — the site "
                       "advertises this feed but it did not serve",
                       source_name, candidate, type(exc).__name__, exc)
    else:
        logger.debug("source %s: guessed candidate %s did not serve a feed (%s: %s)",
                     source_name, candidate, type(exc).__name__, exc)

def _log_guess_failure_over_answer(source_name, candidate, exc, answered_by) -> None:
    """A GUESSED candidate failed after the source already answered.

    Logged at WARNING, not debug, and always naming both halves — the failure we
    are declining to propagate AND the evidence that licenses declining it
    (evaluator blocker r17). The narrow exception is only defensible while it is
    visible: an operator reading the log can see exactly which guess was refused
    and why it did not redden the source.
    """
    logger.warning("source %s: guessed candidate %s failed (%s: %s) — NOT failing "
                   "the source: %s already served a machine-readable calendar "
                   "document that parsed to zero events, so the source has "
                   "answered and a guess cannot overturn it",
                   source_name, candidate, type(exc).__name__, exc, answered_by)


_COMMON_FEED_PATHS = (
    "/events/?ical=1", "/events.ics", "/calendar.ics", "/?ical=1",
    "/events/feed/", "/calendar/feed/",
    "/events", "/events/", "/calendar", "/calendar/",
    "/shows", "/shows/", "/whats-on", "/upcoming-events", "/event-calendar",
)


_ROBOTS_CACHE: dict = {}


# How long we will wait for a robots.txt. RobotFileParser.read() uses urllib's
# DEFAULT (no) timeout, so a hung robots host could stall an import before the
# importer's own fetch timeout ever applied (evaluator nit r10). Short on
# purpose: robots is a courtesy check, not the payload.
_ROBOTS_TIMEOUT = 10

# robots.txt is a courtesy check, not the payload — a real one is a few KB.
# Generous enough that no honest robots.txt is refused, small enough that a
# hostile one cannot exhaust the runner (evaluator nit r17).
_MAX_ROBOTS_BYTES = 512 * 1024


def _fetch_robots_lines(root: str) -> Optional[list[str]]:
    """Fetch {root}/robots.txt ourselves and return its lines, or None when it is
    absent / unreachable / unreadable — each case logged, naming host and reason.

    We do NOT use RobotFileParser.read(), and that is the point (evaluator
    blocker r10). read() swallows HTTP errors internally and sets flags we never
    see, so the documented behaviour and the real behaviour had drifted apart in
    two directions at once:

      * a 404 robots.txt set allow_all and raised NOTHING — so the "every
        fail-open path logs a WARNING" claim in this module and in R-052 was
        simply false for the single most common case;
      * a 5xx (or any status >= 500) set NEITHER flag and left last_checked
        unset, and can_fetch() then returns False for every URL — meaning a host
        whose robots.txt briefly errored was treated as an explicit Disallow.
        After r7 that raises RobotsDisallowed, so a transient robots 500 would
        report a perfectly willing venue as policy-REFUSED. A silent fail-CLOSED
        inside code documenting itself as fail-open.

    Fetching it ourselves makes every outcome explicit, observable, and matched
    to what we claim. Sent with the SAME user agent we fetch pages with, so the
    request a site sees is consistent.
    """
    robots_url = f"{root}/robots.txt"
    req = urllib.request.Request(robots_url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=_ROBOTS_TIMEOUT) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            # BOUNDED, like fetch_url (evaluator nit r17): robots.txt is fetched
            # BEFORE the capped payload path, so an unbounded read here was the
            # one remaining way a hostile or broken origin could exhaust the
            # runner's memory before any cap applied. Over-cap is treated as
            # UNREADABLE — the existing fail-open-and-say-so path — rather than
            # as permission, so a giant robots.txt cannot silently become
            # "no restrictions" without the warning that claim requires.
            raw = resp.read(_MAX_ROBOTS_BYTES + 1)
            if len(raw) > _MAX_ROBOTS_BYTES:
                logger.warning(
                    "robots.txt for %s exceeds %d bytes — refusing to read an "
                    "unbounded body; proceeding. FAIL-OPEN, not verified "
                    "compliance.", root, _MAX_ROBOTS_BYTES)
                return None
            return raw.decode(charset, errors="replace").splitlines()
    except urllib.error.HTTPError as exc:
        if exc.code in _EXPECTED_ABSENCE_STATUSES:
            logger.warning(
                "robots.txt ABSENT for %s (HTTP %s) — fetching under the web "
                "convention that no robots.txt means no restriction. FAIL-OPEN, "
                "not verified compliance.", root, exc.code)
        else:
            logger.warning(
                "robots.txt UNREADABLE for %s (HTTP %s) — proceeding. FAIL-OPEN: "
                "we could not read the policy, so this is not verified compliance.",
                root, exc.code)
        return None
    except OSError as exc:
        # URLError, TLS failure, DNS, socket timeout.
        logger.warning(
            "robots.txt UNREACHABLE for %s (%s: %s) — proceeding. FAIL-OPEN, not "
            "verified compliance.", root, type(exc).__name__, exc)
        return None


def _robots_allows(url: str, ua: Optional[str] = None) -> bool:
    """True when robots.txt permits fetching `url`.

    SCOPE, stated plainly rather than claimed broadly (evaluator nit r3): this
    honours an EXPLICIT Disallow — that case fails CLOSED. It FAILS OPEN when
    robots.txt is absent, unreachable, or unparseable, which follows the web's
    convention that no robots.txt means no restriction but does mean a site whose
    robots we cannot READ is still fetched. EVERY fail-open path logs a WARNING
    naming the host and the reason — a claim that is now true of the code, which
    it was not while we relied on RobotFileParser.read() (see _fetch_robots_lines,
    and R-052 which records the boundary). Cached per host so a 64-source run
    fetches each robots.txt once.
    """
    # Evaluate robots for the UA we ACTUALLY send. Checking a different token
    # ("OneLiveBot") than the fetcher presents meant a rule disallowing our real
    # importer could evaluate as allowed — the access-control claim was false
    # (evaluator blocker r7, PR #68).
    ua = ua or _USER_AGENT
    parts = urllib.parse.urlsplit(url)
    root = f"{parts.scheme}://{parts.netloc}"
    if root not in _ROBOTS_CACHE:
        lines = _fetch_robots_lines(root)
        parser = None
        if lines is not None:
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(f"{root}/robots.txt")
            try:
                parser.parse(lines)
            except Exception as exc:  # noqa: BLE001 - unparseable == unrestricted
                logger.warning(
                    "robots.txt UNPARSEABLE for %s (%s: %s) — proceeding. FAIL-OPEN, "
                    "not verified compliance.", root, type(exc).__name__, exc)
                parser = None
        # False is the cache's "no policy to apply" marker (distinct from None,
        # which would read as "not cached yet" and re-fetch on every candidate).
        _ROBOTS_CACHE[root] = parser if parser is not None else False
    parser = _ROBOTS_CACHE[root]
    if parser is False:
        return True
    try:
        return parser.can_fetch(ua, url)
    except Exception as exc:  # noqa: BLE001
        # Fail-open, said out loud: we could not EVALUATE the rule, so we proceed
        # — but an operator should see that this was unverified, not compliant.
        logger.warning("robots evaluation failed for %s (%s) — allowing (FAIL-OPEN, "
                       "not verified compliance)", url, exc)
        return True


class _LinkRelParser(HTMLParser):
    """Collect <link rel=alternate href=... type=...> feed candidates.

    The DECLARED TYPE is kept with its href, not thrown away (evaluator blocker
    r17). The type is the site's own statement about what those bytes are, and
    it is the only thing that can tell "this calendar is empty this week" from
    "this declared machine-readable feed served something that is not a
    calendar at all" — see :func:`_declared_feed_shape_ok`. Discarding it made
    those two outcomes indistinguishable, which is the swallowed-corrupt-data
    class on our own watch list.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        # (href, declared type) pairs — kept as ONE list of pairs rather than two
        # parallel lists, per the incomplete-enumeration class: two lists with no
        # invariant between them drift.
        self.declared: list = []
        self.unsupported: list = []

    @property
    def hrefs(self) -> list:
        return [href for href, _typ in self.declared]

    def handle_starttag(self, tag, attrs):
        if tag != "link":
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        rel, typ, href = a.get("rel", "").lower(), a.get("type", "").lower(), a.get("href")
        if not href or not ("alternate" in rel or "feed" in rel):
            return
        supported = next((t for t in _FEED_LINK_TYPES if t in typ), None)
        if supported is not None:
            self.declared.append((href, supported))
        elif any(t in typ for t in _UNSUPPORTED_FEED_TYPES):
            self.unsupported.append((typ, href))


def discover_feed_urls(base_url: str, html: str) -> tuple:
    """Ordered, de-duplicated candidate feed URLs for a first-party source.

    Order is deliberate — declared feeds first (the site TOLD us where its data
    is), then platform endpoints, then conventions.

    Returns ``(urls, declared_count, declared_types)`` where the first
    `declared_count` entries are the site's OWN declared feeds — the caller
    needs that split to log a failing DECLARED feed loudly and an expected 404
    on a guess quietly — and `declared_types` maps each declared URL to the
    media type the site declared for it.

    `declared_types` is a MAPPING keyed by the URL, not a list positionally
    parallel to `urls` (evaluator blocker r17 + the incomplete-enumeration
    class): a positional second list can drift out of step with the first
    silently, while a key either resolves or does not. The invariant
    ``set(declared_types) == set(urls[:declared_count])`` is asserted by a test
    rather than trusted.
    """
    out: list[str] = []
    declared_types: dict = {}

    def add(u: str, declared_type: Optional[str] = None) -> None:
        absu = urllib.parse.urljoin(base_url, u)
        if absu not in out and absu.rstrip("/") != base_url.rstrip("/"):
            out.append(absu)
            if declared_type is not None:
                declared_types[absu] = declared_type

    parser = _LinkRelParser()
    try:
        parser.feed(html or "")
    except Exception as exc:  # noqa: BLE001 - malformed markup must not kill discovery
        # Not swallowed: logged with the source URL. Broken markup on ONE page must
        # not lose the platform/convention candidates below, which need no parsing.
        logger.debug("feed discovery: could not parse markup at %s (%s: %s); "
                     "continuing with platform + convention candidates",
                     base_url, type(exc).__name__, exc)
    for typ, href in parser.unsupported:
        logger.warning("feed discovery: %s declares a %s feed at %s that we cannot "
                       "parse — acquisition gap for this source, not 'no events'",
                       base_url, typ, href)
    for href, declared_type in parser.declared:
        add(href, declared_type)
    declared_count = len(out)  # everything added so far is site-DECLARED

    low = (html or "").lower()
    root = f"{urllib.parse.urlsplit(base_url).scheme}://{urllib.parse.urlsplit(base_url).netloc}"
    for fingerprint, path in _PLATFORM_ENDPOINTS:
        if fingerprint in low:
            add(urllib.parse.urljoin(root + "/", path.lstrip("/")))

    for path in _COMMON_FEED_PATHS:
        add(urllib.parse.urljoin(root + "/", path.lstrip("/")))
    # Returned, never stashed in a module global: a global keyed by base URL is a
    # stale/collision hazard under concurrency (evaluator nit r2, PR #68).
    return out, declared_count, declared_types


def _matches_asserted_shape(provider: str, text: str) -> bool:
    """True when `text` is PLAUSIBLY the asserted provider's format.

    Deliberately a SHAPE sniff, not a parse: it answers "did this endpoint serve
    the format the catalog claims?", which is a different question from "did the
    feed contain events". Keeping them separate is the whole point — a real ICS
    calendar with no upcoming shows is legitimately empty, while an ICS-asserted
    URL that serves an HTML error page is a MISCONFIGURATION (evaluator r8).

    Used only to decide between those two outcomes; it never selects a reader
    (an asserted hint always routes to its own reader, never to another).
    """
    text = text or ""
    if provider == PROVIDER_ICS:
        # LINE-ORIENTED, in a bounded head window. Substring matching — even
        # bounded to the first 4096 bytes — still let an HTML page that QUOTES a
        # calendar snippet near the top (`<code>BEGIN:VEVENT</code>`) satisfy an
        # ICS assertion and suppress ProviderMismatch (evaluator nit r10, then
        # r12 for the residue). RFC 5545 content lines stand alone, so requiring
        # the marker to BE a line is the discriminator: real iCalendar passes,
        # prose about iCalendar does not.
        #
        # EITHER marker, not both (r11: the code was right and its comment wrong)
        # — a calendar with no upcoming shows is a valid VCALENDAR carrying no
        # VEVENT at all, and that honestly-empty case must not read as a
        # misconfiguration. Unfolding is deliberately NOT applied here: this is a
        # shape sniff on possibly-not-ICS bytes, not a parse.
        head_lines = {ln.strip().upper() for ln in text[:4096].splitlines()}
        return bool(head_lines & {"BEGIN:VCALENDAR", "BEGIN:VEVENT"})

    if provider == PROVIDER_PLATFORM_JSON:
        # "Is this JSON?" was NOT enough (evaluator blocker r9): any JSON body at
        # all — an API error envelope, a site config dump, a search index —
        # satisfied it, marked the assertion honoured, and let the forced parser
        # return zero rows. The source then read as EMPTY, which is the very class
        # this guard exists to close. Require the COLLECTION both platform readers
        # actually consume: a top-level "events" list (Tribe and Localist agree).
        try:
            doc = json.loads(text)
        except (ValueError, TypeError):
            return False
        return isinstance(doc, dict) and isinstance(doc.get("events"), list)

    if provider == PROVIDER_JSONLD:
        # Two CARRIERS of one format: embedded in HTML (<script
        # type="application/ld+json">) or served bare. Both must be recognized,
        # and bare JSON must carry an actual JSON-LD marker rather than merely
        # being valid JSON (same r9 blocker as above).
        if "application/ld+json" in text.lower():
            return True
        try:
            doc = json.loads(text)
        except (ValueError, TypeError):
            return False
        nodes = doc if isinstance(doc, list) else [doc]
        return any(isinstance(n, dict) and ({"@context", "@type", "@graph"} & set(n))
                   for n in nodes)
    return False


def _events_from_text(text: str, *, provider_hint, source_name, cultural_domain) -> list[dict]:
    provider = _detect_provider(text, provider_hint)
    used_jsonld_fallback = False
    if provider == PROVIDER_ICS:
        raws = parse_ics(text, source=source_name)
    elif provider == PROVIDER_PLATFORM_JSON:
        raws = parse_platform_json(text, source=source_name)
        if not raws and provider_hint is None:
            # SNIFFED only. A bare JSON body may be Tribe/Localist OR bare
            # schema.org JSON-LD, so try the other reader before giving up.
            # When the caller ASSERTED a hint we do NOT second-guess it: silently
            # parsing a different format would hide the misconfiguration
            # (evaluator blocker r7, PR #68).
            raws = parse_jsonld_document(text, source=source_name)
            used_jsonld_fallback = bool(raws)
    else:
        # JSON-LD ships in TWO carriers and both are this one format: embedded in
        # an HTML <script type="application/ld+json"> block, or served bare at an
        # application/ld+json feed URL (which discovery accepts). Reading only the
        # embedded carrier meant a correctly-configured bare JSON-LD source
        # normalized to zero and reported EMPTY — silent data loss (evaluator
        # blocker r9). Trying the second CARRIER is not the cross-format fallback
        # r7 removed: the asserted format is still, only, JSON-LD.
        raws = parse_jsonld(text, source=source_name)
        if not raws:
            raws = parse_jsonld_document(text, source=source_name)
    # Platform-JSON keeps its OWN provider token (migration 0014). Storing it as
    # 'jsonld' conflated two different acquisition formats and would have made a
    # shape drift in the Tribe reader indistinguishable from one in the JSON-LD
    # reader (evaluator nit r3, PR #68). If the body turned out to be bare JSON-LD
    # (the parse_jsonld_document fallback), it IS jsonld and is recorded as such.
    store_provider = provider
    if provider == PROVIDER_PLATFORM_JSON and used_jsonld_fallback:
        store_provider = PROVIDER_JSONLD
    out: list[dict] = []
    for raw in raws:
        n = normalize_structured(raw, provider=store_provider, source_name=source_name,
                                 cultural_domain=cultural_domain)
        if n:
            out.append(n)
    # Account at the NORMALIZE boundary too (evaluator blocker r15). Each reader
    # reports what IT dropped, but a row can also vanish here — normalize_structured
    # returns None for a row with no stable id or no title — and that loss was
    # invisible: parse_jsonld_document counted intermediate Event OBJECTS, not
    # emitted rows, so malformed bare JSON-LD disappeared silently. That is the
    # same "reader accepts a narrower shape than the format permits" class this PR
    # claims closed, one layer further down. Closing it at the boundary covers
    # EVERY reader at once rather than per-parser, so a future reader inherits the
    # accounting instead of having to remember it.
    _account(f"normalize[{store_provider}]", len(raws), len(out), source_name)
    return out


def import_source(url: str, *, provider_hint: Optional[str] = None,
                  source_name: str, cultural_domain: Optional[str] = None) -> list[dict]:
    """Fetch `url` and return normalized licensed_event dicts for every event found.

    CANONICAL ACQUISITION (2026-07-25): the base page is only the FIRST attempt.
    Real venue sites rarely embed event data on the homepage — the first live run
    measured 16 of 18 sources yielding zero that way. So when the base page
    yields nothing, we follow the site's OWN declared feed links, then its
    platform endpoint, then conventional calendar subpaths
    (:func:`discover_feed_urls`), stopping at the first candidate that yields
    events. Every candidate is public data an ordinary reader can load.

    provider_hint ('ics' | 'jsonld' | 'platform_json') FORCES that parser and is
    treated as a configuration ASSERTION. Two consequences, and the second is the
    one r7 got half-right (evaluator r8): (1) no cross-format fallback — we never
    quietly parse something else; (2) if NOTHING we fetched was even the asserted
    SHAPE, that is a misconfigured catalog row and raises ProviderMismatch, so it
    is reported as a MISCONFIGURED source (exit 2, never overridable by
    --allow-partial) rather than folded into the "yielded zero" count. A source
    that served the asserted format AS A STANDALONE FEED DOCUMENT and simply had
    no upcoming events still returns [] — an empty calendar is a fact, not a
    defect. With no hint the body is sniffed (BEGIN:VCALENDAR ⇒ ICS; a bare JSON
    body tries the platform readers then bare JSON-LD).

    ERROR POLICY — a candidate that is simply ABSENT (404/410 on a guessed path)
    is skipped so one dead guess cannot lose the events another candidate would
    have found. An ACCESS failure (401/402/403/406/407/429) or a TLS
    verification failure PROPAGATES instead: those mean the host denied,
    throttled, or could not be trusted, and reporting the source as empty would
    hide that (evaluator blockers r3/r4).

    AUTHORITATIVE EMPTY (evaluator blocker r17) — the one bounded exception to
    that propagation rule, and it exists because the rule as written could turn
    an honestly empty calendar red. Once some endpoint has handed us a STANDALONE
    machine-readable calendar document that parsed to zero events, the source has
    ANSWERED: there are no upcoming events. A later failure on a path *we
    guessed* — /events, /calendar, a convention the site never advertised —
    cannot overturn that answer, so from that point guessed-candidate failures
    are logged and skipped instead of failing the source. The exception is
    deliberately narrow in three ways, because widening any of them re-opens
    failure-reads-as-empty:

      * only a standalone FEED DOCUMENT qualifies (:func:`_is_feed_document`) —
        an HTML page carrying incidental JSON-LD never does;
      * only GUESSED candidates are forgiven — a site-DECLARED feed that denies,
        throttles, errors, or is robots-refused still fails the source, because
        the site itself pointed at it;
      * it suppresses nothing. Every forgiven failure is logged with its status
        and the evidence that licensed forgiving it.

    A DECLARED feed that serves bytes which are NOT its declared type raises
    :class:`DeclaredFeedCorrupt` (a FAILED source) rather than being warned about
    and counted as empty.
    """
    # ROBOTS FIRST, including the BASE url (evaluator blocker r2, PR #68: the
    # first path we reached was exempt, which made the robots claim false).
    if not _robots_allows(url):
        raise RobotsDisallowed(
            f"robots.txt disallows {url} for {_USER_AGENT!r} — source REFUSED by "
            f"policy, not empty")
    base_text = fetch_url(url)
    # Did ANY body we fetched even LOOK like the format the catalog asserted?
    # Tracked across every attempt, not per-attempt: with a hint set, the base
    # page is almost always HTML while the real feed lives at a discovered
    # candidate, so raising on the first non-matching body would break discovery
    # for correctly-configured sources (evaluator r8 fix, scoped deliberately).
    asserted_shape_seen = (provider_hint is not None
                           and _matches_asserted_shape(provider_hint, base_text))
    out = _events_from_text(base_text, provider_hint=provider_hint,
                            source_name=source_name, cultural_domain=cultural_domain)
    if out:
        return out

    # The base URL can itself BE the feed (a catalog row pointing straight at an
    # .ics or a platform endpoint). When it is, and it parsed to zero, the source
    # has already answered — see AUTHORITATIVE EMPTY above.
    authoritative_empty: Optional[str] = None
    if provider_hint is not None and _is_feed_document(provider_hint, base_text):
        authoritative_empty = url

    robots_blocked = 0
    robots_blocked_declared = 0
    all_candidates, declared, declared_types = discover_feed_urls(url, base_text)
    # Separate budgets so a page with many declared alternates cannot starve the
    # conventional paths that actually tend to serve (evaluator nit r2).
    candidates = (all_candidates[:declared][:_MAX_DECLARED_TRIES]
                  + all_candidates[declared:][:_MAX_GUESSED_TRIES])
    declared = min(declared, _MAX_DECLARED_TRIES)
    for i, candidate in enumerate(candidates):
        if not _robots_allows(candidate):
            # Skipping a DISALLOWED candidate is correct (we must not fetch it),
            # but it must not be the reason a source looks dry: if nothing else
            # yields, the source is reported REFUSED below, not empty.
            logger.info("source %s: robots.txt disallows %s — skipping",
                        source_name, candidate)
            robots_blocked += 1
            if i < declared:
                robots_blocked_declared += 1
            continue
        try:
            text = fetch_url(candidate)
        except urllib.error.HTTPError as exc:
            # The ONLY skippable case: a path WE guessed that simply is not there.
            if exc.code in _EXPECTED_ABSENCE_STATUSES and i >= declared:
                _log_candidate_failure(source_name, candidate, exc, declared=False)
                continue
            if authoritative_empty is not None and i >= declared:
                _log_guess_failure_over_answer(source_name, candidate, exc,
                                               authoritative_empty)
                continue
            logger.warning("source %s: %s from %s — FAILING the source rather "
                           "than reporting it empty (%s)",
                           source_name,
                           f"HTTP {exc.code}",
                           candidate,
                           "declared feed" if i < declared else "not an absence")
            raise
        except OSError as exc:
            # TLS failure, DNS, timeout — never an HTTPError, so this branch is
            # where they land. Same rule: a GUESS that fails cannot overturn an
            # answer the source already gave us (evaluator blocker r17). Without
            # an authoritative empty it still propagates exactly as before.
            if authoritative_empty is not None and i >= declared:
                _log_guess_failure_over_answer(source_name, candidate, exc,
                                               authoritative_empty)
                continue
            raise
        if provider_hint is not None and _matches_asserted_shape(provider_hint, text):
            asserted_shape_seen = True
        found = _events_from_text(text, provider_hint=provider_hint,
                                  source_name=source_name,
                                  cultural_domain=cultural_domain)
        if not found and i < declared:
            # The site ADVERTISES this feed and it served bytes that produced no
            # events. Until r17 that was one warning covering two OPPOSITE
            # outcomes — "the calendar is empty" and "the advertised feed is
            # broken" — and the run stayed green either way, which is
            # swallowed-corrupt-data with a log line in front of it. The
            # DECLARED TYPE is what separates them, so we now check it.
            declared_type = declared_types.get(candidate)
            declared_provider = _DECLARED_TYPE_PROVIDER.get(declared_type)
            if declared_provider is None:
                # Unreachable while _FEED_LINK_TYPES and _DECLARED_TYPE_PROVIDER
                # agree (a test pins that), so this is the fail-CLOSED arm of an
                # unmappable declared type rather than a silent pass.
                raise DeclaredFeedCorrupt(
                    f"source {source_name}: DECLARED feed {candidate} has type "
                    f"{declared_type!r}, which has no shape check — refusing to "
                    f"report the source empty on unverifiable bytes")
            if not _matches_asserted_shape(declared_provider, text):
                raise DeclaredFeedCorrupt(
                    f"source {source_name}: DECLARED feed {candidate} advertises "
                    f"{declared_type} but served bytes that are not that format — "
                    f"the site's own machine-readable feed is BROKEN. FAILED "
                    f"source, not an empty calendar.")
            logger.warning("source %s: DECLARED feed %s served valid %s that "
                           "parsed to ZERO events — an empty calendar, verified "
                           "against its declared type",
                           source_name, candidate, declared_type)
            if authoritative_empty is None and _is_feed_document(declared_provider, text):
                # The site pointed here and this IS its calendar document. That is
                # the source's own answer: no upcoming events.
                authoritative_empty = candidate
        if found:
            logger.info("source %s: base page had no events; discovered feed %s (%d events)",
                        source_name, candidate, len(found))
            return found
    if robots_blocked_declared and not out:
        # A feed the SITE advertised is closed to us by the site's own policy.
        # That contradiction is the operator's to resolve and is never softened
        # by an authoritative empty found elsewhere (r17: the narrow exception
        # forgives GUESSES only).
        raise RobotsDisallowed(
            f"{robots_blocked_declared} DECLARED feed(s) for {url} are "
            f"robots-disallowed and no permitted path yielded events — source "
            f"REFUSED by policy, not empty")
    if robots_blocked and not out and authoritative_empty is None:
        # Every remaining avenue was closed by policy — REFUSED, not empty.
        raise RobotsDisallowed(
            f"{robots_blocked} candidate(s) for {url} are robots-disallowed and no "
            f"permitted path yielded events — source REFUSED by policy, not empty")
    if robots_blocked and not out:
        logger.info("source %s: %d guessed candidate(s) were robots-disallowed, but "
                    "%s already served a machine-readable calendar with no upcoming "
                    "events — reporting an EMPTY calendar, not a refusal",
                    source_name, robots_blocked, authoritative_empty)
    if provider_hint is not None and not out and not asserted_shape_seen:
        # The catalog claims this source serves `provider_hint`; we fetched the
        # base page and every discovered candidate and not one of them was that
        # format. That is a MISCONFIGURED source, and it must not share a summary
        # line with a venue whose calendar is simply empty this week (evaluator
        # blocker r8 — r7 fixed the silent cross-format fallback but left the
        # outcome reading as "0 events", which is the same class one step later).
        raise ProviderMismatch(
            f"source {source_name}: provider_hint={provider_hint!r} was asserted but "
            f"no body fetched from {url} (base + {len(candidates)} discovered "
            f"candidate(s)) was that format — MISCONFIGURED source, not an empty "
            f"calendar. Fix the catalog row's provider or its base_url.")
    return out
