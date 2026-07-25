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
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from worker.classify import resolve_category
from worker.importers.domain_map import UNMAPPED, classify_from_title

# Two stable provenance tokens (mirrored by the provider CHECK in
# supabase/migrations/0013_structured_feed_provider.sql) — HOW the row was parsed.
logger = logging.getLogger(__name__)

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
    if provider not in (PROVIDER_ICS, PROVIDER_JSONLD):
        raise ValueError(
            f"provider must be {PROVIDER_ICS!r} or {PROVIDER_JSONLD!r}, got {provider!r}")
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

# A bare bot UA is refused by common WAFs (KXAN returned HTTP 403 on
# 2026-07-25). We identify honestly as OneLive AND present a normal browser
# profile so ordinary public pages are served; we never bypass auth, never
# ignore robots-disallowed paths, and never scrape behind a login.
_BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 "
               "(compatible; OneLiveBot/1.0; +https://onelive.example/bot)")
_BROWSER_ACCEPT = ("text/calendar, application/ld+json, text/html, "
                   "application/xhtml+xml, application/json;q=0.9, */*;q=0.5")


def fetch_url(url: str, *, timeout: int = 30) -> str:
    """GET a public structured feed / calendar page.

    Raises LOUD on any error (never returns empty on failure) — a fetch that
    fails must be visible, not a silent no-op. On a 403/406 (bot-blocked WAF) it
    retries ONCE with a browser profile: the content is public either way, we are
    only presenting headers an ordinary reader would send.
    """
    def _get(ua: str, accept: str) -> str:
        req = urllib.request.Request(url, headers={
            "User-Agent": ua,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")

    try:
        return _get(_USER_AGENT, _ACCEPT)
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 406, 429):
            return _get(_BROWSER_UA, _BROWSER_ACCEPT)
        raise


def _detect_provider(text: str, provider_hint: Optional[str]) -> str:
    if provider_hint in (PROVIDER_ICS, PROVIDER_JSONLD):
        return provider_hint
    head = text.lstrip()[:512].upper()
    if "BEGIN:VCALENDAR" in head or "BEGIN:VEVENT" in text[:4096].upper():
        return PROVIDER_ICS
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
_FEED_LINK_TYPES = (
    "text/calendar", "application/rss+xml", "application/atom+xml",
    "application/ld+json",
)

# 2) Platform endpoints — the big CMS/calendar plugins expose machine-readable
#    events at a known path. Detected from markup fingerprints in the base page.
_PLATFORM_ENDPOINTS = (
    # (fingerprint in HTML, path template relative to the site root)
    ("tribe-events", "/wp-json/tribe/events/v1/events?per_page=50"),
    ("the-events-calendar", "/wp-json/tribe/events/v1/events?per_page=50"),
    ("localist", "/api/2/events?days=60"),
    ("squarespace", "?format=json"),
)

# 3) Conventional calendar subpaths, tried in descending likelihood. The ICS
#    variants come first because a real .ics is unambiguous and cheap to parse.
# Bound the per-source discovery fan-out: enough to cover the declared
# feed + platform endpoint + the likely conventions, without turning one
# source into a crawl.
_MAX_DISCOVERY_TRIES = 8

_COMMON_FEED_PATHS = (
    "/events/?ical=1", "/events.ics", "/calendar.ics", "/?ical=1",
    "/events/feed/", "/calendar/feed/",
    "/events", "/events/", "/calendar", "/calendar/",
    "/shows", "/shows/", "/whats-on", "/upcoming-events", "/event-calendar",
)


class _LinkRelParser(HTMLParser):
    """Collect <link rel=alternate href=... type=...> feed candidates."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "link":
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        rel, typ, href = a.get("rel", "").lower(), a.get("type", "").lower(), a.get("href")
        if href and ("alternate" in rel or "feed" in rel) and any(t in typ for t in _FEED_LINK_TYPES):
            self.hrefs.append(href)


def discover_feed_urls(base_url: str, html: str) -> list[str]:
    """Ordered, de-duplicated candidate feed URLs for a first-party source.

    Order is deliberate — declared feeds first (the site TOLD us where its data
    is), then platform endpoints, then conventions. Returns absolute URLs.
    """
    out: list[str] = []

    def add(u: str) -> None:
        absu = urllib.parse.urljoin(base_url, u)
        if absu not in out and absu.rstrip("/") != base_url.rstrip("/"):
            out.append(absu)

    parser = _LinkRelParser()
    try:
        parser.feed(html or "")
    except Exception as exc:  # noqa: BLE001 - malformed markup must not kill discovery
        # Not swallowed: logged with the source URL. Broken markup on ONE page must
        # not lose the platform/convention candidates below, which need no parsing.
        logger.debug("feed discovery: could not parse markup at %s (%s: %s); "
                     "continuing with platform + convention candidates",
                     base_url, type(exc).__name__, exc)
    for href in parser.hrefs:
        add(href)

    low = (html or "").lower()
    root = f"{urllib.parse.urlsplit(base_url).scheme}://{urllib.parse.urlsplit(base_url).netloc}"
    for fingerprint, path in _PLATFORM_ENDPOINTS:
        if fingerprint in low:
            add(urllib.parse.urljoin(root + "/", path.lstrip("/")))

    for path in _COMMON_FEED_PATHS:
        add(urllib.parse.urljoin(root + "/", path.lstrip("/")))
    return out


def _events_from_text(text: str, *, provider_hint, source_name, cultural_domain) -> list[dict]:
    provider = _detect_provider(text, provider_hint)
    raws = parse_ics(text) if provider == PROVIDER_ICS else parse_jsonld(text)
    out: list[dict] = []
    for raw in raws:
        n = normalize_structured(raw, provider=provider, source_name=source_name,
                                 cultural_domain=cultural_domain)
        if n:
            out.append(n)
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

    provider_hint ('ics'|'jsonld') forces the parser; otherwise each body is
    sniffed (BEGIN:VCALENDAR ⇒ ICS). A candidate that errors is skipped — one
    dead guess must not lose the events another candidate would have found.
    """
    base_text = fetch_url(url)
    out = _events_from_text(base_text, provider_hint=provider_hint,
                            source_name=source_name, cultural_domain=cultural_domain)
    if out:
        return out

    for candidate in discover_feed_urls(url, base_text)[:_MAX_DISCOVERY_TRIES]:
        try:
            text = fetch_url(candidate)
        except Exception as exc:  # noqa: BLE001 - a dead guess is EXPECTED here
            # Discovery deliberately probes candidate paths that may not exist, so
            # a failure is normal control flow, NOT a swallowed error: it is logged
            # at debug with the URL and reason, and the loop moves to the next
            # candidate. A source that exhausts every candidate still surfaces as
            # "yielded 0 events" in the runner's per-source warning.
            logger.debug("source %s: candidate %s did not serve a feed (%s: %s)",
                         source_name, candidate, type(exc).__name__, exc)
            continue
        found = _events_from_text(text, provider_hint=provider_hint,
                                  source_name=source_name,
                                  cultural_domain=cultural_domain)
        if found:
            logger.info("source %s: base page had no events; discovered feed %s (%d events)",
                        source_name, candidate, len(found))
            return found
    return out
