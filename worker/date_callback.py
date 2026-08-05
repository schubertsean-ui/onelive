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
  2. Microdata ``itemprop="startDate"``/``"endDate"`` content attributes —
     but ONLY inside a schema.org Event ``itemscope``, only when the page
     declares exactly ONE such Event scope, and subject to the same identity
     guard as JSON-LD (evaluator blocker, PR #189 r3: an out-of-scope or
     unrelated microdata date must never donate itself to the candidate).

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
from html.parser import HTMLParser
from typing import Dict, List, Optional
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from worker.segment import _iter_jsonld_objects

logger = logging.getLogger(__name__)

_MAX_BYTES = 1_500_000
_UA = "1LiveBot/1.0 (+https://1live.co)"

_JSONLD_RE = re.compile(
    r'<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S)


def _url_admissible(url: str) -> bool:
    """http/https, real hostname, and no private/loopback/link-local literal
    IPs or localhost (evaluator, PR #189 r1/r2): a listing-published "link"
    of http://169.254.169.254/… must never turn this worker into an
    internal-network probe. Applied to the ORIGINAL url and, via the
    redirect handler below, to EVERY redirect hop. Literal-IP hosts are
    checked here; the worker environment holds no internal network today,
    so DNS-level rebinding is out of scope by architecture (recorded)."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    host = parsed.hostname
    if host.lower() == "localhost":
        return False
    try:
        if not ipaddress.ip_address(host).is_global:
            return False
    except ValueError:
        pass  # a DNS name, not a literal IP
    return True


class _AdmissibleRedirects(HTTPRedirectHandler):
    """Follow redirects only to admissible destinations (evaluator nit,
    PR #189 r2): the same refusal policy applies to every hop, so a public
    URL cannot bounce the callback into private address space."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urljoin(req.full_url, newurl)
        if not _url_admissible(target):
            raise HTTPError(target, code,
                            "redirect target refused by admissibility policy",
                            headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, target)


def _fetch(url: str, timeout: int = 15) -> Optional[str]:
    """Bounded fetch of the event's own page; None on any failure (logged).

    A page LARGER than the cap is refused outright rather than truncated
    (evaluator blocker, PR #189 r4): parsing a truncated prefix as if it
    were the whole document would let a prefix containing exactly one Event
    pass the single-Event attribution check while the real page declares
    more — the claim honestly stays refused instead.
    """
    if not _url_admissible(url):
        return None
    req = Request(url, headers={"User-Agent": _UA,
                                "Accept": "text/html,application/xhtml+xml"})
    try:
        with build_opener(_AdmissibleRedirects()).open(req, timeout=timeout) as resp:
            data = resp.read(_MAX_BYTES + 1)
    except Exception as exc:  # noqa: BLE001 — callback failure must never break extraction
        logger.info("date callback: fetch of %s failed (%s) — claim stays refused",
                    url, type(exc).__name__)
        return None
    if len(data) > _MAX_BYTES:
        logger.info("date callback: %s exceeds the %d-byte cap — refusing to "
                    "parse a truncated document; claim stays refused",
                    url, _MAX_BYTES)
        return None
    return data.decode("utf-8", errors="replace")


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
    name = events[0].get("name")
    if out and isinstance(name, str) and name.strip():
        out["_name"] = name.strip()  # for the caller's identity guard only
    return out


_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr"})


class _MicrodataEventScopes(HTMLParser):
    """Collect startDate/endDate/name itemprops PER schema.org Event scope.

    Evaluator blocker (PR #189 r3): the previous regex pass read itemprop
    content attributes from ANYWHERE on the page — a generic page with one
    unrelated microdata startDate could donate its date to the candidate.
    This parser attributes each itemprop to its nearest enclosing
    ``itemscope`` whose ``itemtype`` is a schema.org Event; itemprops outside
    any Event scope are ignored entirely.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._tag_stack: List[str] = []
        self._scope_depths: List[int] = []   # tag-stack depth of each open Event scope
        self._scope_events: List[dict] = []  # parallel: the dict being filled
        # Visible-text itemprop="name" capture (evaluator blocker, PR #189
        # r4: common microdata puts the name in element TEXT, not a content
        # attribute — dropping it let an unrelated Event slip past the
        # identity guard as "nameless"). Parallel stacks: capture depth,
        # buffer, and the Event dict the finished name belongs to.
        self._name_depths: List[int] = []
        self._name_bufs: List[List[str]] = []
        self._name_scopes: List[dict] = []
        self.events: List[dict] = []

    def _handle_tag(self, tag: str, attrs, closes_itself: bool) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        opens_scope = ("itemscope" in a and any(
            t.strip().lower().endswith(("schema.org/event", "schema.org/musicevent",
                                        "schema.org/theaterevent", "schema.org/comedyevent",
                                        "schema.org/danceevent", "schema.org/festival"))
            or t.strip().lower() == "event"
            for t in a.get("itemtype", "").split()))
        prop = a.get("itemprop", "").strip()
        if prop in ("startDate", "endDate", "name") and self._scope_events \
                and not opens_scope and a.get("content", "").strip():
            self._scope_events[-1].setdefault(prop, set()).add(a["content"].strip())
        elif prop == "name" and self._scope_events and not opens_scope \
                and not closes_itself and tag not in _VOID_TAGS:
            # No content attr: the name is the element's visible text.
            self._name_depths.append(len(self._tag_stack))
            self._name_bufs.append([])
            self._name_scopes.append(self._scope_events[-1])
        if opens_scope and not closes_itself:
            ev: dict = {}
            self.events.append(ev)
            self._scope_events.append(ev)
            self._scope_depths.append(len(self._tag_stack))
        if not closes_itself and tag not in _VOID_TAGS:
            self._tag_stack.append(tag)

    def handle_starttag(self, tag, attrs):
        self._handle_tag(tag, attrs, closes_itself=False)

    def handle_startendtag(self, tag, attrs):
        self._handle_tag(tag, attrs, closes_itself=True)

    def handle_data(self, data):
        for buf in self._name_bufs:
            buf.append(data)

    def _finish_names_at(self, depth: int) -> None:
        """Finalize any text-name captures whose element sits at >= depth."""
        while self._name_depths and self._name_depths[-1] >= depth:
            self._name_depths.pop()
            text = "".join(self._name_bufs.pop()).strip()
            scope = self._name_scopes.pop()
            if text:
                scope.setdefault("name", set()).add(text)

    def handle_endtag(self, tag):
        # Lenient close (real-world HTML): pop to the matching open tag if
        # one exists, closing any Event scopes and finishing any text-name
        # captures opened at or below that depth.
        if tag in _VOID_TAGS or tag not in self._tag_stack:
            return
        while self._tag_stack:
            depth_after_pop = len(self._tag_stack) - 1
            popped = self._tag_stack.pop()
            while self._scope_depths and self._scope_depths[-1] >= depth_after_pop:
                self._scope_depths.pop()
                self._scope_events.pop()
            self._finish_names_at(depth_after_pop)
            if popped == tag:
                break

    def close(self):
        super().close()
        self._finish_names_at(0)  # unclosed name elements still finalize


def _microdata_dates(html: str) -> Dict[str, str]:
    """{start_time, end_time} from microdata, iff exactly ONE Event scope
    on the page declares dates — same attribution rule as JSON-LD, plus
    ``_name`` for the caller's identity guard."""
    parser = _MicrodataEventScopes()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # noqa: BLE001 — malformed HTML: no recovery, claim stays refused
        return {}
    # Cardinality over ALL Event scopes, dated or not (evaluator blocker,
    # PR #189 r4): a page with one dated Event and one undated Event is
    # still a multi-event page — attributing the dated one to the candidate
    # would be a guess. Same total-count rule as the JSON-LD path.
    if len(parser.events) != 1:
        return {}  # zero: nothing to read; >1: attribution would be a guess
    ev = parser.events[0]
    if not (ev.get("startDate") or ev.get("endDate")):
        return {}
    out: Dict[str, str] = {}
    for field, prop in (("start_time", "startDate"), ("end_time", "endDate")):
        values = ev.get(prop) or set()
        if len(values) == 1:
            out[field] = next(iter(values))
    names = ev.get("name") or set()
    if out and len(names) == 1:
        out["_name"] = next(iter(names))  # for the caller's identity guard only
    return out


def _identity_aligned(candidate_title: Optional[str], event_name: Optional[str]) -> bool:
    """The linked page's single Event must plausibly BE the candidate
    (evaluator nit, PR #189 r2): a source-quoted but generic link (a venue
    homepage declaring one unrelated Event) must not donate its date. Rule:
    when both names exist, require containment either way or a majority of
    the candidate-title's words appearing in the Event name. A missing name
    on either side allows recovery (nothing to compare) — the date still
    faces the strict normalizer and gate3 either way."""
    if not candidate_title or not event_name:
        return True
    a = {w for w in candidate_title.casefold().split() if len(w) > 2}
    b = {w for w in event_name.casefold().split() if len(w) > 2}
    if not a or not b:
        return True
    if candidate_title.casefold() in event_name.casefold()             or event_name.casefold() in candidate_title.casefold():
        return True
    return len(a & b) / len(a) >= 0.5


def recover_dates_from_url(url: str, timeout: int = 15,
                           candidate_title: Optional[str] = None) -> Dict[str, str]:
    """Read explicit machine-declared dates off the event's own page.

    Returns raw claim strings keyed start_time/end_time (subset, possibly
    empty). The caller MUST re-run the strict normalizer on them — this
    function fetches and reads, it never validates or fabricates.
    """
    html = _fetch(url, timeout=timeout)
    if not html:
        return {}
    dates = _jsonld_event_dates(html)
    if dates and not _identity_aligned(candidate_title, dates.pop("_name", None)):
        logger.info("date callback: JSON-LD Event name does not align with "
                    "candidate title — recovery refused (identity guard)")
        dates = {}
    dates.pop("_name", None)
    if "start_time" in dates:
        return dates
    micro = _microdata_dates(html)
    if micro and not _identity_aligned(candidate_title, micro.pop("_name", None)):
        logger.info("date callback: microdata Event name does not align with "
                    "candidate title — recovery refused (identity guard)")
        micro = {}
    micro.pop("_name", None)
    micro.update(dates)  # JSON-LD end_time (if any) outranks microdata's
    return micro
