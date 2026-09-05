"""How 1Live reads a public desk: identity, robots, and re-used bytes.

`worker/locale/desk_fetch.py` is the only thing in the repo that opens a socket
at a desk, and from the 2026-09-05 ticket it does so on a SCHEDULE nobody
watches. Every test here pins the same rule from a different side: a page we
did not read must never come back looking like a page that held nothing.

Hermetic — no network, no clock, no sleeping. The transport is injected.
"""
from __future__ import annotations

import json
import os

import pytest

from worker.locale.desk_fetch import (
    CONTACT_URL,
    MAX_CACHED_BODY_BYTES,
    MAX_HONORED_CRAWL_DELAY_S,
    ROBOTS_AGENT,
    USER_AGENT,
    CachedPage,
    ConditionalStore,
    LiveFetcher,
    read_robots,
    robots_url,
)

ALLOW_ALL = "User-agent: *\nAllow: /\n"


class FakeTransport:
    """One injected `get` serving both shapes the module calls it with."""

    def __init__(self, robots=ALLOW_ALL, robots_status=200, robots_error=None,
                 pages=None):
        self.robots, self.robots_status, self.robots_error = robots, robots_status, robots_error
        self.pages = pages or {}
        self.sent = []

    def __call__(self, url, *, headers=None, timeout_s=20):
        if headers is None:                       # the robots.txt shape
            return self.robots_status, self.robots, self.robots_error
        self.sent.append((url, dict(headers)))
        page = self.pages.get(url)
        if page is None:
            return 404, "", None, url, None, None
        return page


def _fetcher(transport, **kw):
    kw.setdefault("timeout_s", 5)
    kw.setdefault("min_interval_s", 0)
    return LiveFetcher(requester=transport, sleep=lambda s: None,
                       clock=lambda: 0.0, **kw)


# --------------------------------------------------------------------------
# 1. Identity
# --------------------------------------------------------------------------

def test_the_user_agent_names_1live_and_carries_a_contact_url():
    assert "1Live" in USER_AGENT
    assert CONTACT_URL in USER_AGENT and CONTACT_URL.startswith("https://")
    # robots.txt rules are written against the token before the slash, so it
    # has to be one word and it has to be the one we match on.
    assert USER_AGENT.startswith(ROBOTS_AGENT + "/")
    assert " " not in ROBOTS_AGENT


def test_every_page_request_is_signed():
    t = FakeTransport(pages={"https://d.test/p": (200, "<html>x</html>", None,
                                                  "https://d.test/p", None, None)})
    _fetcher(t)("https://d.test/p")
    assert t.sent[0][1]["User-Agent"] == USER_AGENT


# --------------------------------------------------------------------------
# 2. robots.txt — unread rules are not permission
# --------------------------------------------------------------------------

def test_robots_url_is_the_hosts_own_root():
    assert robots_url("https://d.test/a/b?c=1") == "https://d.test/robots.txt"


@pytest.mark.parametrize("status", [429, 500, 503])
def test_robots_we_could_not_read_disallows(status):
    """RFC 9309 §2.3.1. "We could not ask" is never "they said yes"."""
    assert read_robots("https://d.test/p", lambda u: (status, "", None)).allowed is False


def test_a_transport_failure_reading_robots_disallows():
    v = read_robots("https://d.test/p", lambda u: (None, None, "ConnectionError"))
    assert v.allowed is False and "not permission" in v.reason


def test_robots_404_means_the_site_published_no_rules():
    assert read_robots("https://d.test/p", lambda u: (404, "", None)).allowed is True


def test_a_disallowed_page_is_reported_unread_never_empty():
    t = FakeTransport(robots=f"User-agent: {ROBOTS_AGENT}\nDisallow: /private\n")
    got = _fetcher(t)("https://d.test/private/page")
    assert got.error and "robots" in got.error
    assert got.body is None and got.status is None
    assert t.sent == [], "a disallowed page was fetched anyway"


def test_robots_is_read_once_per_host():
    t = FakeTransport(pages={f"https://d.test/{n}": (200, "x", None, f"https://d.test/{n}",
                                                     None, None) for n in "ab"})
    f = _fetcher(t)
    f("https://d.test/a")
    f("https://d.test/b")
    assert len(f._robots) == 1


def test_a_crawl_delay_we_cannot_honor_stops_the_page_it_does_not_speed_up():
    too_long = MAX_HONORED_CRAWL_DELAY_S + 1
    t = FakeTransport(robots=f"User-agent: *\nCrawl-delay: {too_long:g}\n",
                      pages={"https://d.test/p": (200, "x", None, "https://d.test/p",
                                                  None, None)})
    got = _fetcher(t)("https://d.test/p")
    assert got.error and "Crawl-delay" in got.error
    assert t.sent == [], "we crawled a desk faster than it asked"


def test_a_crawl_delay_we_can_honor_is_waited_out():
    waits = []
    t = FakeTransport(robots="User-agent: *\nCrawl-delay: 7\n",
                      pages={"https://d.test/a": (200, "x", None, "https://d.test/a", None, None),
                             "https://d.test/b": (200, "y", None, "https://d.test/b", None, None)})
    f = LiveFetcher(requester=t, timeout_s=5, min_interval_s=1,
                    sleep=waits.append, clock=lambda: 0.0)
    f("https://d.test/a")
    f("https://d.test/b")
    assert max(waits) == pytest.approx(7.0), waits


# --------------------------------------------------------------------------
# 3. Conditional GET — and the 304 that must never look like an empty page
# --------------------------------------------------------------------------

def test_a_200_is_remembered_and_the_next_request_asks_with_it():
    t = FakeTransport(pages={"https://d.test/p": (200, "<html>body</html>", None,
                                                  "https://d.test/p", '"v1"', "Mon, 1 Sep 2026")})
    f = _fetcher(t)
    f("https://d.test/p")
    f("https://d.test/p")
    assert t.sent[1][1]["If-None-Match"] == '"v1"'
    assert t.sent[1][1]["If-Modified-Since"] == "Mon, 1 Sep 2026"


def test_a_304_returns_the_cached_body_and_says_it_was_a_304():
    store = ConditionalStore({"https://d.test/p": CachedPage(
        etag='"v1"', body="<html>kept</html>", final_url="https://d.test/p")})
    t = FakeTransport(pages={"https://d.test/p": (304, None, None, "https://d.test/p",
                                                  None, None)})
    f = _fetcher(t)
    f.store = store
    got = f("https://d.test/p")
    assert got.status == 304, "the log must not show a re-used page as a download"
    assert got.body == "<html>kept</html>"
    assert f.not_modified == 1


def test_a_304_with_no_cached_body_is_unread_never_empty():
    """THE trap. The desk said "your copy is current" and we do not have that
    copy. An empty body here publishes "nothing on" over a page never opened."""
    t = FakeTransport(pages={"https://d.test/p": (304, None, None, "https://d.test/p",
                                                  None, None)})
    got = _fetcher(t)("https://d.test/p")
    assert got.error and "304" in got.error
    assert got.body is None


def test_validators_are_never_kept_without_the_body_they_refer_to():
    store = ConditionalStore()
    store.remember("u", etag='"v1"', last_modified=None, body=None, final_url="u")
    assert store.validators("u") == {}


def test_a_body_too_large_to_cache_is_not_half_cached():
    store = ConditionalStore()
    store.remember("u", etag='"v1"', last_modified=None,
                   body="x" * (MAX_CACHED_BODY_BYTES + 1), final_url="u")
    assert store.validators("u") == {}


def test_a_body_with_no_validators_is_not_cached_at_all():
    store = ConditionalStore()
    store.remember("u", etag=None, last_modified=None, body="hello", final_url="u")
    assert "u" not in store.entries


# --------------------------------------------------------------------------
# 4. The cache file is a convenience and can never become an outage
# --------------------------------------------------------------------------

def test_a_missing_cache_file_is_an_empty_cache(tmp_path):
    assert ConditionalStore.load(str(tmp_path / "nope.json")).entries == {}


def test_a_corrupt_cache_file_is_an_empty_cache_not_a_crash(tmp_path):
    path = tmp_path / "c.json"
    path.write_text("{not json", encoding="utf-8")
    assert ConditionalStore.load(str(path)).entries == {}


def test_a_saved_cache_round_trips(tmp_path):
    path = str(tmp_path / "sub" / "c.json")
    store = ConditionalStore()
    store.remember("u", etag='"v1"', last_modified=None, body="hi", final_url="u")
    store.save(path)
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as fh:
        assert json.load(fh)["user_agent"] == USER_AGENT
    assert ConditionalStore.load(path).validators("u") == {"If-None-Match": '"v1"'}


def test_the_summary_separates_downloaded_from_re_used():
    t = FakeTransport(pages={"https://d.test/p": (200, "x", None, "https://d.test/p",
                                                  '"v1"', None)})
    f = _fetcher(t)
    f("https://d.test/p")
    assert "1 page(s) downloaded" in f.summary()
    assert "0 unchanged" in f.summary()
