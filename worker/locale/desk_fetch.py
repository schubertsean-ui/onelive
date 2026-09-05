#!/usr/bin/env python3
"""How 1Live reads a public desk: one identity, robots honored, bytes re-used.

The desk walk (`worker/locale/desk_walk.py`) never opens a socket — it takes a
`fetch(url) -> PageFetch` callable. This module is the LIVE one. It exists
because a scheduled walk is a different animal from a walk somebody watches: it
runs unattended, every few hours, forever, against sites that never agreed to
host us. Three obligations follow, and each is a function below.

  1. SAY WHO WE ARE. One User-Agent, naming 1Live and carrying a URL a
     webmaster can open to find out what we are. A crawler that will not sign
     its requests has no standing to complain about a 403.

  2. HONOR robots.txt, INCLUDING Crawl-delay. Per host, fetched once per
     process with the same identity. RFC 9309 §2.3.1: a robots.txt we cannot
     read (429, 5xx, transport failure) means DISALLOW, not "assume yes" — so a
     desk whose robots we could not read comes back UNREADABLE, which is a
     failed check upstream, never an empty list. A 404 means the site published
     no rules, which really does mean allow.

  3. DO NOT RE-DOWNLOAD WHAT HAS NOT CHANGED. Every 200 stores the page's
     validators (ETag / Last-Modified) and its body; the next run sends
     If-None-Match / If-Modified-Since and a 304 costs the desk a header
     exchange instead of a page. `ingest.yml` already runs the pipeline this
     way; this is the same manners for the desk walk.

THE ONE TRAP THIS MODULE IS BUILT AROUND. Every failure path here must produce
a page that reads as UNREADABLE, never as a page that was fine and held nothing.
A desk with an empty list gets its rows deleted from nobody's screen, but it
does tell the founder "nothing is on tonight", and that is a lie we would be
publishing on the desk's behalf. So: robots unreadable -> unreadable. Disallowed
-> unreadable. A 304 whose cached body we no longer hold -> unreadable (the
server said "your copy is current" and we do not have that copy; the honest
answer is that we did not read the page, not that the page was blank).
"""
from __future__ import annotations

import json
import os
import time
import urllib.robotparser
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

from worker.locale.desk_walk import PageFetch

#: The identity every live desk fetch carries. It names 1Live and points at a
#: page a webmaster can actually open — the live site — so a request of ours is
#: traceable to a person. The token before the slash is what robots.txt rules
#: are matched against (`ROBOTS_AGENT`), which is why it is a single word.
CONTACT_URL = "https://1live.co"
ROBOTS_AGENT = "1LiveBot"
USER_AGENT = f"{ROBOTS_AGENT}/1.0 (+{CONTACT_URL})"

#: A Crawl-delay longer than this cannot be honored inside one scheduled run,
#: so the desk is reported UNREADABLE rather than crawled faster than it asked.
#: Ignoring the number would be the other option and it is not one: the whole
#: point of reading robots.txt is that the answer binds us when it is
#: inconvenient. 60s x the page budget still fits a scheduled job; past that the
#: desk needs its own cadence, which is a ticket, not a shortcut.
MAX_HONORED_CRAWL_DELAY_S = 60.0

#: Bodies larger than this are not kept in the conditional-GET cache. A cache
#: is a convenience; a cache that fills the runner's disk is an outage. When a
#: body is too large we store NO validators for it either, so the next run
#: re-reads it unconditionally instead of asking a question whose "unchanged"
#: answer we could not use.
MAX_CACHED_BODY_BYTES = 4 * 1024 * 1024


class DeskFetchError(RuntimeError):
    """The fetcher itself is misconfigured (a cache path we cannot use)."""


# --------------------------------------------------------------------------
# The conditional-GET cache
# --------------------------------------------------------------------------

@dataclass
class CachedPage:
    """What we keep about a page so the next run can ask "still current?"."""

    etag: Optional[str] = None
    last_modified: Optional[str] = None
    body: Optional[str] = None
    final_url: Optional[str] = None

    @property
    def usable_on_304(self) -> bool:
        """A 304 is only usable if we still hold the body it refers to."""
        return bool(self.body)


class ConditionalStore:
    """URL -> CachedPage, persisted as one JSON file between runs.

    Deliberately a plain file and not the database: the walk runs in dry-run
    with no DSN at all, and a cache that only works when the credential is
    present would silently stop being a cache exactly where it is cheapest to
    test. The workflow persists the file with `actions/cache`; a cache miss is
    a full read, which is correct, just less polite.
    """

    def __init__(self, entries: Optional[Dict[str, CachedPage]] = None):
        self.entries: Dict[str, CachedPage] = dict(entries or {})
        self.hits = 0
        self.misses = 0
        self.stale = 0

    @classmethod
    def load(cls, path: Optional[str]) -> "ConditionalStore":
        """Read the cache. A missing or unreadable file is an EMPTY cache.

        Never an error: the worst a broken cache file can do is cost us a full
        re-read, and failing a scheduled ingest because a convenience file was
        corrupt would trade a small cost for an outage.
        """
        if not path or not os.path.exists(path):
            return cls()
        try:
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, ValueError):
            return cls()
        if not isinstance(raw, dict):
            return cls()
        entries: Dict[str, CachedPage] = {}
        for url, item in (raw.get("pages") or {}).items():
            if isinstance(item, dict):
                entries[url] = CachedPage(
                    etag=item.get("etag"), last_modified=item.get("last_modified"),
                    body=item.get("body"), final_url=item.get("final_url"))
        return cls(entries)

    def save(self, path: Optional[str]) -> None:
        if not path:
            return
        directory = os.path.dirname(os.path.abspath(path))
        try:
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"version": 1, "user_agent": USER_AGENT, "pages": {
                    url: {"etag": p.etag, "last_modified": p.last_modified,
                          "body": p.body, "final_url": p.final_url}
                    for url, p in self.entries.items()}}, fh)
        except OSError as exc:
            raise DeskFetchError(f"cannot write the fetch cache at {path}: {exc}") from exc

    def validators(self, url: str) -> Dict[str, str]:
        entry = self.entries.get(url)
        if not entry:
            return {}
        headers = {}
        if entry.etag:
            headers["If-None-Match"] = entry.etag
        if entry.last_modified:
            headers["If-Modified-Since"] = entry.last_modified
        return headers

    def remember(self, url: str, *, etag, last_modified, body, final_url) -> None:
        """Keep a 200's validators AND its body, or keep neither.

        Keeping validators without the body is the one combination that breaks
        the next run: it would ask "unchanged?", hear "unchanged", and hold
        nothing to show for it.
        """
        if not body or len(body.encode("utf-8", "ignore")) > MAX_CACHED_BODY_BYTES:
            self.entries.pop(url, None)
            return
        if not etag and not last_modified:
            # Nothing to ask with next time; the body alone would never be used.
            self.entries.pop(url, None)
            return
        self.entries[url] = CachedPage(etag=etag, last_modified=last_modified,
                                       body=body, final_url=final_url)


# --------------------------------------------------------------------------
# robots.txt
# --------------------------------------------------------------------------

@dataclass
class RobotsVerdict:
    """What a host's robots.txt says about us."""

    allowed: bool
    reason: str
    crawl_delay_s: Optional[float] = None


def robots_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme or "https", parts.netloc, "/robots.txt", "", ""))


def read_robots(url: str, get: Callable[[str], Tuple[Optional[int], Optional[str], Optional[str]]]
                ) -> RobotsVerdict:
    """Fetch and read one host's robots.txt. `get` returns (status, text, error).

    RFC 9309 §2.3.1, and the direction every branch here leans:
      * 200 with rules  -> those rules decide, Crawl-delay included.
      * 4xx (not 429)   -> the site published no rules. Allowed.
      * 429 / 5xx / any transport failure -> UNREADABLE, so DISALLOWED. We do
        not get to treat "we could not ask" as "they said yes"; the desk is
        reported unread, which is loud, instead of crawled, which is rude.
    """
    target = robots_url(url)
    status, text, error = get(target)
    if error is not None:
        return RobotsVerdict(False, f"robots.txt at {target} could not be read ({error}) "
                                    f"— unread rules are not permission")
    if status == 429 or (status is not None and status >= 500):
        return RobotsVerdict(False, f"robots.txt at {target} answered HTTP {status} "
                                    f"— unread rules are not permission")
    if status is not None and 400 <= status < 500:
        return RobotsVerdict(True, f"robots.txt at {target} answered HTTP {status} "
                                   f"— the site published no crawl rules")
    if status != 200 or text is None:
        return RobotsVerdict(False, f"robots.txt at {target} answered HTTP {status} with no "
                                    f"body — unread rules are not permission")
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(text.splitlines())
    if not parser.can_fetch(ROBOTS_AGENT, url):
        return RobotsVerdict(False, f"robots.txt at {target} disallows {ROBOTS_AGENT} here")
    delay = parser.crawl_delay(ROBOTS_AGENT)
    return RobotsVerdict(True, f"robots.txt at {target} allows {ROBOTS_AGENT}",
                         crawl_delay_s=float(delay) if delay is not None else None)


# --------------------------------------------------------------------------
# The live fetcher
# --------------------------------------------------------------------------

class LiveFetcher:
    """A polite `fetch(url) -> PageFetch`, callable, with its state on the side.

    A class rather than a closure because a scheduled run has to REPORT what it
    did — which desks robots kept us out of, how many pages came back 304 — and
    a closure's notes are unreachable from the caller that has to print them.
    """

    def __init__(self, *, timeout_s: int, min_interval_s: float,
                 cache_path: Optional[str] = None, requester=None,
                 sleep=time.sleep, clock=time.monotonic):
        self.timeout_s = timeout_s
        self.min_interval_s = max(0.0, float(min_interval_s))
        self.cache_path = cache_path
        self.store = ConditionalStore.load(cache_path)
        self._sleep = sleep
        self._clock = clock
        self._robots: Dict[str, RobotsVerdict] = {}
        self._last_touch: Dict[str, float] = {}
        self.notes: list = []
        self.not_modified = 0
        self.downloaded = 0
        self.blocked_by_robots = 0
        self._requester = requester or _requests_getter()

    # -- politeness ------------------------------------------------------
    def _host(self, url: str) -> str:
        return (urlsplit(url).netloc or "").lower()

    def _wait(self, host: str, delay_s: float) -> None:
        last = self._last_touch.get(host)
        now = self._clock()
        if last is not None:
            remaining = delay_s - (now - last)
            if remaining > 0:
                self._sleep(remaining)
        elif self.min_interval_s:
            self._sleep(self.min_interval_s)
        self._last_touch[host] = self._clock()

    def _robots_for(self, url: str) -> RobotsVerdict:
        host = self._host(url)
        verdict = self._robots.get(host)
        if verdict is None:
            self._wait(host, self.min_interval_s)
            verdict = read_robots(url, self._requester)
            self._robots[host] = verdict
            self.notes.append(verdict.reason)
        return verdict

    # -- the call --------------------------------------------------------
    def __call__(self, url: str) -> PageFetch:
        host = self._host(url)
        verdict = self._robots_for(url)
        if not verdict.allowed:
            self.blocked_by_robots += 1
            # An error, never a status: `demote_on_response` reads a 403 as the
            # site refusing us, and this is us refusing ourselves. The walk
            # records it as a page we did not read, which is the truth.
            return PageFetch(url=url, error=f"robots: {verdict.reason}")

        delay = max(self.min_interval_s, verdict.crawl_delay_s or 0.0)
        if verdict.crawl_delay_s and verdict.crawl_delay_s > MAX_HONORED_CRAWL_DELAY_S:
            return PageFetch(
                url=url,
                error=f"robots: Crawl-delay {verdict.crawl_delay_s:g}s exceeds this run's "
                      f"{MAX_HONORED_CRAWL_DELAY_S:g}s ceiling — this desk needs its own "
                      f"cadence; it is NOT crawled faster than it asked")
        self._wait(host, delay)

        headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
        headers.update(self.store.validators(url))
        status, text, error, final_url, etag, last_modified = self._requester(
            url, headers=headers, timeout_s=self.timeout_s)
        if error is not None:
            return PageFetch(url=url, error=error)

        if status == 304:
            entry = self.store.entries.get(url)
            if entry is None or not entry.usable_on_304:
                # The desk said "your copy is current" and we no longer hold
                # that copy. We did NOT read this page. Saying so is the whole
                # contract of this module; returning an empty body here would
                # publish "nothing on" over a page we never opened.
                self.store.entries.pop(url, None)
                self.store.stale += 1
                return PageFetch(
                    url=url,
                    error="HTTP 304 but the cached copy is gone — the page was NOT read "
                          "(re-run: the next request is unconditional)")
            self.store.hits += 1
            self.not_modified += 1
            # Status stays 304 on purpose: the walk reads the body and the run
            # report prints the honest transport code, so "we re-used bytes" and
            # "we downloaded bytes" never look the same in the log.
            return PageFetch(url=url, status=304, body=entry.body,
                             final_url=entry.final_url or url)

        if status == 200:
            self.store.misses += 1
            self.downloaded += 1
            self.store.remember(url, etag=etag, last_modified=last_modified,
                                body=text, final_url=final_url)
        return PageFetch(url=url, status=status, body=text, final_url=final_url)

    # -- close -----------------------------------------------------------
    def save(self) -> None:
        self.store.save(self.cache_path)

    def summary(self) -> str:
        parts = [f"{self.downloaded} page(s) downloaded",
                 f"{self.not_modified} unchanged (HTTP 304, no body re-sent)"]
        if self.blocked_by_robots:
            parts.append(f"{self.blocked_by_robots} not fetched because robots.txt said so")
        if self.store.stale:
            parts.append(f"{self.store.stale} 304 with no cached copy (reported unread)")
        return "; ".join(parts)


def _requests_getter():
    """The real transport, adapted to the two shapes this module calls it with.

    `read_robots` wants (status, text, error); the page path wants the
    validators too. One function serves both so a test substitutes ONE thing.
    """
    try:
        import requests
    except ImportError:  # pragma: no cover - environment-dependent
        def unavailable(url: str, *, headers=None, timeout_s: int = 20):
            if headers is None:
                return None, None, "requests is not installed"
            return None, None, "requests is not installed", None, None, None
        return unavailable

    def get(url: str, *, headers=None, timeout_s: int = 20):
        want_page = headers is not None
        send = dict(headers or {"User-Agent": USER_AGENT})
        try:
            resp = requests.get(url, headers=send, timeout=timeout_s,
                                allow_redirects=True)
        except Exception as exc:  # noqa: BLE001 — a failed page is a row, not a crash
            message = f"{type(exc).__name__}: {exc}"[:200]
            if want_page:
                return None, None, message, None, None, None
            return None, None, message
        if not want_page:
            return resp.status_code, resp.text, None
        body = None if resp.status_code == 304 else resp.text
        return (resp.status_code, body, None, str(resp.url),
                resp.headers.get("ETag"), resp.headers.get("Last-Modified"))

    return get


def live_fetcher(*, timeout_s: int, min_interval_s: float,
                 cache_path: Optional[str] = None) -> LiveFetcher:
    """The fetcher a live desk walk is handed. Callable; call `.save()` after."""
    return LiveFetcher(timeout_s=timeout_s, min_interval_s=min_interval_s,
                       cache_path=cache_path)
