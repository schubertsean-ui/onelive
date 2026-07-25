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
import urllib.request
from html.parser import HTMLParser
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from worker.importers.domain_map import classify_from_title

# Two stable provenance tokens (mirrored by the provider CHECK in
# supabase/migrations/0013_structured_feed_provider.sql) — HOW the row was parsed.
PROVIDER_ICS = "ics"
PROVIDER_JSONLD = "jsonld"

_USER_AGENT = "OneLiveStructuredImporter/1.0 (+https://onelive.example; deterministic no-AI calendar import)"
_ACCEPT = "text/calendar, text/html, application/xhtml+xml, application/ld+json;q=0.9, */*;q=0.5"


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


def parse_ics(text: str) -> list[dict]:
    """Parse VEVENT blocks from iCalendar text into canonical intermediate dicts.

    Reads SUMMARY, DTSTART/DTEND (respecting TZID= and VALUE=DATE), LOCATION, URL,
    DESCRIPTION, UID. Handles RFC-5545 line folding. DTSTART/DTEND are converted to
    UTC ISO 'Z' (a bare/VALUE=DATE date is kept as an all-day date with a null
    time). A VEVENT with no SUMMARY or no DTSTART is SKIPPED — never fabricated.
    """
    events: list[dict] = []
    cur: Optional[dict] = None
    in_vevent = False
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            in_vevent = True
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


def parse_jsonld(html: str) -> list[dict]:
    """Extract schema.org/Event JSON-LD from HTML into canonical intermediate
    dicts. Every <script type="application/ld+json"> block is json.loads'd
    (tolerating a list, a single object, or an @graph array); only nodes whose
    @type is Event (or a subtype like MusicEvent/TheaterEvent/…) are kept. Missing
    fields stay None — never fabricated."""
    extractor = _LdJsonExtractor()
    extractor.feed(html)
    events: list[dict] = []
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
                events.append(_jsonld_event_to_intermediate(obj))
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


def normalize_structured(raw: dict, *, provider: str, source_name: str,
                         cultural_domain: Optional[str] = None) -> Optional[dict]:
    """Map a canonical intermediate dict (from parse_ics / parse_jsonld) into the
    EXACT licensed_event column dict normalize_ticketmaster returns.

    provider is 'ics' | 'jsonld' (provenance: HOW it was parsed). category uses the
    catalog's cultural_domain hint when supplied (a first-party calendar's own
    curated domain), else deterministic classify_from_title on the real title.
    Returns None when there is no stable id or no title — never invents data.
    """
    if provider not in (PROVIDER_ICS, PROVIDER_JSONLD):
        raise ValueError(
            f"provider must be {PROVIDER_ICS!r} or {PROVIDER_JSONLD!r}, got {provider!r}")
    title = raw.get("title")
    if not title:
        return None
    external_id = _stable_external_id(raw, provider=provider, source_name=source_name)
    if not external_id:
        return None

    if cultural_domain:
        category, subsegment = cultural_domain, None
    else:
        category, subsegment = classify_from_title(title)

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

def fetch_url(url: str, *, timeout: int = 30) -> str:
    """Plain urllib GET of a public structured feed. Declares a User-Agent and an
    Accept for calendar+HTML. Raises LOUD on any error (never returns empty on
    failure) — a fetch that fails must be visible, not a silent no-op."""
    req = urllib.request.Request(
        url, headers={"User-Agent": _USER_AGENT, "Accept": _ACCEPT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def _detect_provider(text: str, provider_hint: Optional[str]) -> str:
    if provider_hint in (PROVIDER_ICS, PROVIDER_JSONLD):
        return provider_hint
    head = text.lstrip()[:512].upper()
    if "BEGIN:VCALENDAR" in head or "BEGIN:VEVENT" in text[:4096].upper():
        return PROVIDER_ICS
    return PROVIDER_JSONLD


def import_source(url: str, *, provider_hint: Optional[str] = None,
                  source_name: str, cultural_domain: Optional[str] = None) -> list[dict]:
    """Fetch `url`, auto-detect ICS vs HTML-with-JSON-LD, parse every event, and
    return the normalized licensed_event dicts. provider_hint ('ics'|'jsonld')
    forces the parser; otherwise the body is sniffed (BEGIN:VCALENDAR ⇒ ICS)."""
    text = fetch_url(url)
    provider = _detect_provider(text, provider_hint)
    raws = parse_ics(text) if provider == PROVIDER_ICS else parse_jsonld(text)
    out: list[dict] = []
    for raw in raws:
        n = normalize_structured(
            raw, provider=provider, source_name=source_name,
            cultural_domain=cultural_domain)
        if n:
            out.append(n)
    return out
