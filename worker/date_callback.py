"""Date recovery by CALLBACK to the source — founder-directed (2026-08-05).

Founder, verbatim: "No one will post or announce [an] event with just a time -
do a better [job] searching … so it really is more of a call back position
than a logic process." When extraction yields an event whose date claim was
refused (time-only), the date almost always exists in machine-readable form on
the event's OWN page — the ticket/detail link the listing itself published.
This module goes back and READS it; nothing is inferred.

What it reads, in order of explicitness, from the linked page:
  1. JSON-LD schema.org Event ``startDate``/``endDate`` — but ONLY when the
     page declares exactly ONE Event object. A multi-event page cannot be
     attributed to one candidate without guessing, so it returns nothing.
  2. Microdata ``itemprop="startDate"``/``"endDate"`` content attributes,
     same single-occurrence rule per field.

Bounds and honesty:
  - One bounded HTTP fetch per call (timeout, 1.5 MB cap, http/https only),
    with the pipeline's honest identified User-Agent. Any failure — network,
    parse, ambiguity — returns {} and the claim simply stays refused; this
    module can only ADD evidence, never block or degrade the pipeline.
  - Recovered strings are returned RAW; the caller re-runs the strict
    normalizer on them, so a callback can never bypass the full-date bar.
  - Every recovery is recorded in candidate provenance by the caller
    (method + URL), so an auditor can re-fetch and re-verify the claim.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import re
from typing import Dict, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from worker.segment import _iter_jsonld_objects

logger = logging.getLogger(__name__)

_MAX_BYTES = 1_500_000
_UA = "1LiveBot/1.0 (+https://1live.co)"

_JSONLD_RE = re.compile(
    r'<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S)
_ITEMPROP_RE_TMPL = (
    r'itemprop\s*=\s*["\']{field}["\'][^>]*\scontent\s*=\s*["\']([^"\']+)["\']'
    r'|content\s*=\s*["\']([^"\']+)["\'][^>]*\sitemprop\s*=\s*["\']{field}["\']')


def _fetch(url: str, timeout: int = 15) -> Optional[str]:
    """Bounded fetch of the event's own page; None on any failure (logged)."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
    # No callbacks into private/loopback/link-local space (evaluator nit,
    # PR #189 r1): a listing-published "link" of http://169.254.169.254/…
    # must never turn this worker into an internal-network probe. Literal-IP
    # hosts are checked here; the worker environment holds no internal
    # network today, so DNS-level rebinding is out of scope by architecture.
    host = parsed.hostname
    if host.lower() == "localhost":
        return None
    try:
        if not ipaddress.ip_address(host).is_global:
            return None
    except ValueError:
        pass  # a DNS name, not a literal IP
    req = Request(url, headers={"User-Agent": _UA,
                                "Accept": "text/html,application/xhtml+xml"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read(_MAX_BYTES).decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 — callback failure must never break extraction
        logger.info("date callback: fetch of %s failed (%s) — claim stays refused",
                    url, type(exc).__name__)
        return None


def _jsonld_event_dates(html: str) -> Dict[str, str]:
    """{start_time, end_time} from JSON-LD iff exactly ONE Event is declared."""
    events = []
    for m in _JSONLD_RE.finditer(html):
        try:
            data = json.loads(m.group(1).strip())
        except (ValueError, TypeError):
            continue
        for obj in _iter_jsonld_objects(data):
            t = obj.get("@type")
            types = t if isinstance(t, list) else [t]
            if any(isinstance(x, str) and x.lower().endswith("event")
                   for x in types):
                events.append(obj)
    if len(events) != 1:
        return {}  # zero: nothing to read; >1: attribution would be a guess
    out = {}
    for field, key in (("start_time", "startDate"), ("end_time", "endDate")):
        v = events[0].get(key)
        if isinstance(v, str) and v.strip():
            out[field] = v.strip()
    return out


def _microdata_dates(html: str) -> Dict[str, str]:
    """{start_time, end_time} from itemprop content attrs, one occurrence each."""
    out = {}
    for field, prop in (("start_time", "startDate"), ("end_time", "endDate")):
        pat = re.compile(_ITEMPROP_RE_TMPL.format(field=prop), re.I)
        values = {a or b for a, b in pat.findall(html) if (a or b).strip()}
        if len(values) == 1:
            out[field] = values.pop().strip()
    return out


def recover_dates_from_url(url: str, timeout: int = 15) -> Dict[str, str]:
    """Read explicit machine-declared dates off the event's own page.

    Returns raw claim strings keyed start_time/end_time (subset, possibly
    empty). The caller MUST re-run the strict normalizer on them — this
    function fetches and reads, it never validates or fabricates.
    """
    html = _fetch(url, timeout=timeout)
    if not html:
        return {}
    dates = _jsonld_event_dates(html)
    if "start_time" in dates:
        return dates
    micro = _microdata_dates(html)
    micro.update(dates)  # JSON-LD end_time (if any) outranks microdata's
    return micro
