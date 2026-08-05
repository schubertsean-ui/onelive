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
     scoped to their enclosing schema.org Event ``itemscope``.

Trust doctrine (founder rulings 2026-08-05, decision record
2026-08-05_source-site-authoritative.md): the link is PROVEN to be the
source's own before any fetch (the caller's verbatim URL-token check), and
from there the page's declarations are AUTHORITATIVE — no identity
cross-examination, no contradiction refusals. A single declared Event is
the candidate's, full stop; on a MULTI-event page (a venue calendar), the
candidate's title SELECTS its match — selection adds recovery, it never
gates. The only remaining bounds are security (SSRF/size), never distrust
of the source.

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


def _jsonld_events(html: str) -> List[dict]:
    """Every schema.org Event object declared in the page's JSON-LD blocks."""
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
    return events


def _jsonld_event_dates(event: dict) -> Dict[str, str]:
    """{start_time, end_time} from ONE JSON-LD Event object."""
    out = {}
    for field, key in (("start_time", "startDate"), ("end_time", "endDate")):
        v = event.get(key)
        if isinstance(v, str) and v.strip():
            out[field] = v.strip()
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
    any Event scope are ignored entirely (attribution, not distrust).
    Names are captured (content attr or visible text) ONLY so multi-event
    pages can be attributed by title match — founder ruling 2026-08-05:
    matching selects, it never refuses.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._tag_stack: List[str] = []
        self._scope_depths: List[int] = []   # tag-stack depth of each open Event scope
        self._scope_events: List[dict] = []  # parallel: the dict being filled
        self._name_depths: List[int] = []    # visible-text name captures
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
        while self._name_depths and self._name_depths[-1] >= depth:
            self._name_depths.pop()
            text = "".join(self._name_bufs.pop()).strip()
            scope = self._name_scopes.pop()
            if text:
                scope.setdefault("name", set()).add(text)

    def handle_endtag(self, tag):
        # Lenient close (real-world HTML): pop to the matching open tag if
        # one exists, closing any Event scopes and name captures opened at
        # or below that depth.
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


def _microdata_events(html: str) -> List[dict]:
    """Every schema.org Event itemscope on the page (parser above)."""
    parser = _MicrodataEventScopes()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # noqa: BLE001 — malformed HTML: no recovery, claim stays refused
        return []
    return parser.events


def _microdata_event_dates(ev: dict) -> Dict[str, str]:
    """{start_time, end_time} from ONE microdata Event scope, single
    occurrence per itemprop."""
    if not (ev.get("startDate") or ev.get("endDate")):
        return {}
    out: Dict[str, str] = {}
    for field, prop in (("start_time", "startDate"), ("end_time", "endDate")):
        values = ev.get(prop) or set()
        if len(values) == 1:
            out[field] = next(iter(values))
    return out


def _jsonld_names(ev: dict) -> List[str]:
    name = ev.get("name")
    return [name.strip()] if isinstance(name, str) and name.strip() else []


def _microdata_names(ev: dict) -> List[str]:
    return sorted(ev.get("name") or set())


def _select_event(events: List[dict], candidate_title: Optional[str],
                  names_of) -> Optional[dict]:
    """Which of the page's declared Events is the candidate's?

    - Exactly one Event: it IS the candidate's (the source linked this page
      from the candidate's own listing — authoritative, no matching).
    - Several Events (founder ruling 2026-08-05: a venue calendar page must
      not be skipped): the candidate's TITLE selects the best name-token
      match. Matching here only ADDS recovery — it picks among the source's
      own declarations, it never refuses a single-event page. A page where
      no name shares a word with the title, or where two tie, stays
      unattributable and contributes nothing (the claim just stays as-is).
    """
    if len(events) == 1:
        return events[0]
    if not events or not candidate_title:
        return None
    ct = {w for w in candidate_title.casefold().split() if len(w) > 2}
    if not ct:
        return None
    best: Optional[dict] = None
    best_score = 0
    tied = False
    for ev in events:
        score = max((len(ct & {w for w in n.casefold().split() if len(w) > 2})
                     for n in names_of(ev)), default=0)
        if score > best_score:
            best, best_score, tied = ev, score, False
        elif score == best_score and best is not None and ev is not best:
            tied = True
    if best is None or best_score == 0 or tied:
        logger.info("date callback: %d declared Events but none uniquely "
                    "matches the candidate title — cannot attribute",
                    len(events))
        return None
    return best


def recover_dates_from_url(url: str, timeout: int = 15,
                           candidate_title: Optional[str] = None) -> Dict[str, str]:
    """Read explicit machine-declared dates off the event's own page.

    The caller has already PROVEN the URL is the source's own (verbatim
    URL-token check), and from there the page's declarations are
    AUTHORITATIVE (founder rulings 2026-08-05, decision record
    2026-08-05_source-site-authoritative.md) — no identity
    cross-examination, no contradiction refusals. On a MULTI-event page
    (a venue calendar), the candidate's title selects the matching Event;
    selection adds recovery, it never gates.

    Returns raw claim strings keyed start_time/end_time (subset, possibly
    empty). The caller MUST re-run the strict normalizer on them — this
    function fetches and reads, it never validates or fabricates.
    """
    html = _fetch(url, timeout=timeout)
    if not html:
        return {}
    jl = _select_event(_jsonld_events(html), candidate_title, _jsonld_names)
    dates = _jsonld_event_dates(jl) if jl else {}
    if "start_time" in dates:
        return dates
    md = _select_event(_microdata_events(html), candidate_title, _microdata_names)
    micro = _microdata_event_dates(md) if md else {}
    micro.update(dates)  # JSON-LD end_time (if any) outranks microdata's
    return micro
