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
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from worker.classify import resolve_category
from worker.identity import jsonld_identity, ld_scalar
from worker.importers.domain_map import UNMAPPED, classify_from_title

# Two stable provenance tokens (mirrored by the provider CHECK in
# supabase/migrations/0013_structured_feed_provider.sql) — HOW the row was parsed.
PROVIDER_ICS = "ics"
PROVIDER_JSONLD = "jsonld"
# A hosted event-calendar PLATFORM's JSON API. "localist" is a third-party vendor
# (localist.com) that universities, libraries, and cities pay to run their public
# calendars; its /api/2/events endpoint returns the same schedule as structured
# JSON. First-party + deterministic (no AI) exactly like ics/jsonld, so its rows
# are 'confirmed' by construction. Registered in the provider CHECK by
# supabase/migrations/0015_localist_provider.sql.
PROVIDER_LOCALIST = "localist"

log = logging.getLogger("structured_feed")

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


#: A JSON-LD scalar string, unwrapping the common {'@value': ...} form and
#: taking the first of a list. None (never fabricated) otherwise.
#: Defined in `worker/identity.py` and imported rather than mirrored: the crawl
#: path reads the same JSON-LD through the same reader, and a second copy here
#: would be free to drift from it.
_ld_str = ld_scalar


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
    # ONE home for "which JSON-LD keys are an identity" (worker/identity.py):
    # this importer feeds the licensed store and worker/segment.py feeds the
    # crawl path, and the two must never disagree about what a source stated.
    identity = jsonld_identity(obj)
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
        "url": identity.listing_url,
        "image_url": _ld_image(obj.get("image")),
        "price_min": price_min,
        "price_max": price_max,
        "currency": currency,
        "uid": identity.uid,
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

    provider is 'ics' | 'jsonld' (provenance: HOW it was parsed). Category is
    resolved by the shared classifier (worker.classify.resolve_category) from the
    STRONGEST available signal, in authority order: the event's OWN declared
    schema.org @type (a MusicEvent/ComedyEvent/LiteraryEvent already parsed from
    the JSON-LD — so "you know it's a lecture/band/comedian, so you know the
    category", founder 2026-07-25), THEN the first-party calendar's curated
    cultural_domain, THEN a last-resort read of the title. Non-fabricating: an
    absent/generic signal falls through, never guesses. Returns None when there is
    no stable id or no title — never invents data.
    """
    if provider not in (PROVIDER_ICS, PROVIDER_JSONLD, PROVIDER_LOCALIST):
        raise ValueError(
            f"provider must be one of {PROVIDER_ICS!r}, {PROVIDER_JSONLD!r}, "
            f"{PROVIDER_LOCALIST!r}, got {provider!r}")
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
        # ICS/JSON-LD calendars rarely carry coordinates (the key is absent →
        # honest null); a platform feed that DOES (Localist geo) keeps them.
        "venue_lat": _f(raw.get("venue_lat")),
        "venue_lng": _f(raw.get("venue_lng")),
        "confidence": "confirmed",  # first-party anchor ⇒ confirmed by construction
        "raw": raw,
    }


# ---- ICS feed auto-discovery from an HTML calendar page ----------------------
#
# Most first-party venue / civic / university calendars render their event LIST
# in the browser (client-side JS) — so the index HTML carries no schema.org
# Event JSON-LD to parse — yet they DO publish the same schedule as an iCalendar
# feed, advertised as a <link rel="alternate" type="text/calendar"> in the page
# head or a visible "Subscribe / Add to calendar" .ics / webcal: link. When the
# JSON-LD parse of a page yields nothing, we look for that feed and parse it with
# the already-proven parse_ics, instead of reporting the source as empty. This is
# still first-party structured data (the venue's OWN .ics) — no AI, no scraping
# of rendered HTML, no fabricated field.

class _CalendarLinkExtractor(HTMLParser):
    """Collect candidate iCalendar-feed URLs from an HTML page, kept in three
    priority tiers so the most authoritative advertisement wins:

      1. <link rel="alternate" type="text/calendar" href="…"> — the standard,
         explicit feed declaration (highest confidence).
      2. any href whose scheme is webcal: — a calendar-subscription link.
      3. any href ending in '.ics' (querystring tolerated) — a download link.

    href values are captured verbatim here; resolution to absolute URLs and
    de-duplication happen in discover_ics_links so this parser stays a pure
    collector.
    """

    def __init__(self) -> None:
        super().__init__()
        self.alternate: list[str] = []
        self.webcal: list[str] = []
        self.dotics: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        href = a.get("href", "").strip()
        if not href:
            return
        t = tag.lower()
        if t == "link":
            rel = a.get("rel", "").lower()
            typ = a.get("type", "").strip().lower()
            if typ == "text/calendar" or ("alternate" in rel and typ == "text/calendar"):
                self.alternate.append(href)
            return
        if t == "a":
            low = href.lower()
            if low.startswith("webcal:"):
                self.webcal.append(href)
            elif low.split("?", 1)[0].split("#", 1)[0].endswith(".ics"):
                self.dotics.append(href)


def _normalize_feed_url(href: str, base_url: str) -> Optional[str]:
    """Resolve one discovered href to an absolute http(s) feed URL, or None if it
    is not a fetchable calendar link. A 'webcal:' scheme (subscription form of an
    ICS feed) is rewritten to 'https:' — urllib cannot open webcal, but the same
    host serves the identical body over https. Only http(s)/webcal are accepted;
    mailto:, tel:, javascript:, and data: are dropped."""
    href = href.strip()
    if href.lower().startswith("webcal:"):
        href = "https:" + href[len("webcal:"):]
    absolute = urllib.parse.urljoin(base_url, href)
    scheme = urllib.parse.urlparse(absolute).scheme.lower()
    if scheme not in ("http", "https"):
        return None
    return absolute


def discover_ics_links(html: str, base_url: str, *, limit: int = 5) -> list[str]:
    """Return up to `limit` absolute ICS-feed URLs advertised by an HTML calendar
    page, most-authoritative first (declared <link> feeds, then webcal:, then
    .ics hrefs), de-duplicated while preserving that order. Empty when the page
    advertises no calendar feed."""
    ex = _CalendarLinkExtractor()
    try:
        ex.feed(html)
    except Exception as exc:  # noqa: BLE001 — a malformed page must not crash discovery
        # html.parser is lenient, but never let a pathological page raise here:
        # discovery is a best-effort fallback, so we LOG the parse failure (not
        # silently swallow it) and fall through to whatever links were collected
        # before the error — an empty result is the honest outcome, not a crash.
        log.warning("ICS-link discovery: HTML parse raised (%s); using partial "
                    "results (%d link(s) collected).", exc,
                    len(ex.alternate) + len(ex.webcal) + len(ex.dotics))
    seen: set[str] = set()
    out: list[str] = []
    for href in (*ex.alternate, *ex.webcal, *ex.dotics):
        absolute = _normalize_feed_url(href, base_url)
        if absolute and absolute not in seen:
            seen.add(absolute)
            out.append(absolute)
            if len(out) >= limit:
                break
    return out


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


def _normalize_all(raws: list[dict], *, provider: str, source_name: str,
                   cultural_domain: Optional[str]) -> list[dict]:
    out: list[dict] = []
    for raw in raws:
        n = normalize_structured(
            raw, provider=provider, source_name=source_name,
            cultural_domain=cultural_domain)
        if n:
            out.append(n)
    return out


# ---- Localist calendar-platform JSON API -------------------------------------
#
# Localist (localist.com) is a hosted calendar platform many universities,
# libraries, and cities use; it exposes a public, documented JSON API at
# /api/2/events. A page on such a site renders its event list client-side (so
# JSON-LD and ICS discovery both come up empty), but the API returns the same
# schedule as structured JSON — deterministic, no key, no AI. The adapter is
# reusable for EVERY Localist customer in any market, which is the whole point of
# a platform pathway.

def localist_events_url(base_url: str, *, page: int = 1, per_page: int = 100,
                        days: int = 365) -> str:
    """Derive the Localist /api/2/events endpoint for a site from its base URL.
    Pulls the full forward window (days) at the API's max page size. Raises
    ValueError on a base URL with no scheme/host (never guesses a host)."""
    p = urllib.parse.urlparse(base_url)
    if not p.scheme or not p.netloc:
        raise ValueError(f"cannot derive a Localist API URL from {base_url!r}")
    return (f"{p.scheme}://{p.netloc}/api/2/events"
            f"?days={int(days)}&pp={int(per_page)}&page={int(page)}")


def _localist_first_instance(ev: dict) -> tuple[Optional[str], Optional[str]]:
    """Return (start, end) ISO strings from a Localist event's first
    event_instance, or (None, None). Localist nests instances as
    [{'event_instance': {'start': ..., 'end': ...}}, ...]."""
    instances = ev.get("event_instances")
    if not isinstance(instances, list) or not instances:
        return None, None
    first = instances[0]
    inst = first.get("event_instance") if isinstance(first, dict) else None
    if not isinstance(inst, dict):
        return None, None
    start = inst.get("start")
    end = inst.get("end")
    return (start if isinstance(start, str) else None,
            end if isinstance(end, str) else None)


def parse_localist(json_text: str) -> list[dict]:
    """Parse a Localist /api/2/events JSON body into canonical intermediate dicts.

    Reads title, the first instance's start/end (ISO-8601 with offset → UTC 'Z'),
    location_name/address, geo lat/lng/city, localist_url, photo_url, and a stable
    id. Non-fabricating: a wrapper that is not an event, or an event with no
    title, is skipped; absent fields stay None. Raises ValueError (json.loads)
    when the body is not JSON — the caller treats that as "not a Localist host"
    and moves on, never as fatal."""
    doc = json.loads(json_text)
    if not isinstance(doc, dict):
        return []
    events = doc.get("events")
    if not isinstance(events, list):
        return []
    out: list[dict] = []
    for wrapper in events:
        ev = wrapper.get("event") if isinstance(wrapper, dict) else None
        if not isinstance(ev, dict):
            continue
        start, end = _localist_first_instance(ev)
        geo = ev.get("geo") if isinstance(ev.get("geo"), dict) else {}
        eid = ev.get("id")
        out.append({
            "title": _ld_str(ev.get("title")),
            "start_time": _to_utc_z(start) if start else None,
            "end_time": _to_utc_z(end) if end else None,
            "all_day": bool(ev.get("allday")),
            "venue_name": (ev.get("location_name") or None),
            "venue_city": (_ld_str(geo.get("city")) if geo else None),
            "venue_address": (ev.get("address") or (_ld_str(geo.get("street")) if geo else None) or None),
            "venue_lat": _f(geo.get("latitude")) if geo else None,
            "venue_lng": _f(geo.get("longitude")) if geo else None,
            "url": (ev.get("localist_url") or None),
            "image_url": (ev.get("photo_url") or None),
            "price_min": None,
            "price_max": None,
            "currency": None,
            "uid": (f"localist:{eid}" if eid is not None else None),
            "_raw_props": ev,
        })
    return out


def import_localist(base_url: str, *, source_name: str,
                    cultural_domain: Optional[str] = None,
                    max_pages: int = 5, per_page: int = 100) -> list[dict]:
    """Fetch + normalize a Localist calendar via its JSON API, paging until a
    short page (the last) or max_pages. Self-detecting: if the host is not a
    Localist site the endpoint 404s (OSError) or returns non-JSON (ValueError),
    and we return [] — never raise, so a non-Localist source is a clean skip, not
    a failure. De-dupes by external_id across pages."""
    out: list[dict] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        api_url = localist_events_url(base_url, page=page, per_page=per_page)
        try:
            body = fetch_url(api_url)
        except OSError:
            break  # not a Localist host / unreachable — clean skip
        try:
            raws = parse_localist(body)
        except ValueError:
            break  # not JSON → not Localist
        if not raws:
            break
        for n in _normalize_all(raws, provider=PROVIDER_LOCALIST,
                                source_name=source_name, cultural_domain=cultural_domain):
            if n["external_id"] not in seen:
                seen.add(n["external_id"])
                out.append(n)
        if len(raws) < per_page:
            break  # last page reached
    return out


def import_source(url: str, *, provider_hint: Optional[str] = None,
                  source_name: str, cultural_domain: Optional[str] = None) -> list[dict]:
    """Fetch `url`, auto-detect ICS vs HTML-with-JSON-LD, parse every event, and
    return the normalized licensed_event dicts. provider_hint ('ics'|'jsonld')
    forces the parser; otherwise the body is sniffed (BEGIN:VCALENDAR ⇒ ICS).

    ICS-FEED FALLBACK: when the page is HTML (JSON-LD path) and carries NO
    schema.org Event JSON-LD — the common case for a calendar whose event list is
    rendered client-side — we look for an iCalendar feed the page advertises
    (<link rel="alternate" type="text/calendar">, a webcal: link, or a visible
    .ics link) and parse THAT with parse_ics. This is still the venue's own
    first-party structured schedule; it turns "16 of 18 sources yield zero" into
    real coverage without AI, scraping, or a fabricated field. A discovered feed
    that fails to fetch is tried-then-skipped (logged, never fatal) so one dead
    link does not sink the source; the caller's loud-fail on the PRIMARY fetch is
    unchanged.

    LOCALIST FALLBACK: if the page still yields nothing (no JSON-LD, no advertised
    ICS feed), try the Localist calendar-platform JSON API at the same host. On a
    non-Localist site this is one extra GET that 404s or returns non-JSON and is
    skipped cleanly — never a failure.
    """
    text = fetch_url(url)
    provider = _detect_provider(text, provider_hint)
    raws = parse_ics(text) if provider == PROVIDER_ICS else parse_jsonld(text)
    out = _normalize_all(raws, provider=provider, source_name=source_name,
                         cultural_domain=cultural_domain)
    if out or provider == PROVIDER_ICS:
        return out

    # Tier 2 — HTML page with no parseable JSON-LD events: try the advertised ICS feed.
    for feed_url in discover_ics_links(text, url):
        try:
            feed_text = fetch_url(feed_url)
        except OSError as exc:
            log.warning("source %s: advertised ICS feed %s failed to fetch (%s) — "
                        "trying next.", source_name, feed_url, exc)
            continue
        feed_events = _normalize_all(
            parse_ics(feed_text), provider=PROVIDER_ICS,
            source_name=source_name, cultural_domain=cultural_domain)
        if feed_events:
            log.info("source %s: %d event(s) via advertised ICS feed %s (page had "
                     "no JSON-LD).", source_name, len(feed_events), feed_url)
            return feed_events

    # Tier 3 — a Localist calendar-platform JSON API at this host (self-detecting).
    localist_events = import_localist(
        url, source_name=source_name, cultural_domain=cultural_domain)
    if localist_events:
        log.info("source %s: %d event(s) via the Localist JSON API (page had no "
                 "JSON-LD or ICS feed).", source_name, len(localist_events))
        return localist_events
    return out
