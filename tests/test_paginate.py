"""Multi-page ingestion (worker/fetch/paginate.py + the orchestrator walk).

Founder-directed 2026-08-05 ("build multi-page ingestion next. It's the
single biggest lever left"). The proving case is the Austin Chronicle
calendar: 2,362 events across 60 pages, of which a one-page fetch reads ~40.

What must hold:
  - The next page is the SOURCE'S OWN published link — rel="next" first, then
    a next-page anchor. Never a constructed or incremented URL.
  - Same-origin only; loops are impossible; the walk is bounded.
  - Page 1's behavior (render fallback, 304, audit rows) is untouched, and a
    failure on any later page keeps everything already read.
"""
import worker.orchestrator as orch
from worker.fetch.paginate import discover_next_page


def test_rel_next_is_preferred():
    html = """
    <html><head><link rel="next" href="/cal?page=2"></head>
    <body><a href="/somewhere-else">More stuff</a></body></html>"""
    assert discover_next_page(html, "https://cal.example/cal") == \
        "https://cal.example/cal?page=2"


def test_next_anchor_text_is_recognized():
    for label in ("next", "Next", "next page", "Next ›", "older events"):
        html = f'<html><body><a href="/cal?page=3">{label}</a></body></html>'
        assert discover_next_page(html, "https://cal.example/cal") == \
            "https://cal.example/cal?page=3", label


def test_unrelated_links_are_not_pagination():
    html = """
    <html><body>
      <a href="/tickets">Buy tickets for next week's show</a>
      <a href="/about">About</a>
    </body></html>"""
    assert discover_next_page(html, "https://cal.example/cal") is None


def test_offsite_next_is_refused():
    html = '<link rel="next" href="https://evil.example/cal?page=2">'
    assert discover_next_page(html, "https://cal.example/cal") is None


def test_already_visited_and_self_links_are_refused():
    html = '<link rel="next" href="/cal?page=2">'
    seen = {"https://cal.example/cal", "https://cal.example/cal?page=2"}
    assert discover_next_page(html, "https://cal.example/cal", seen) is None
    self_link = '<link rel="next" href="/cal">'
    assert discover_next_page(self_link, "https://cal.example/cal") is None


def test_no_html_no_crash():
    assert discover_next_page("", "https://cal.example/cal") is None


# ---------------------------------------------------------------------------
# The orchestrator's bounded walk
# ---------------------------------------------------------------------------

def _page(n: int, last: int) -> str:
    nxt = f'<link rel="next" href="/cal?page={n + 1}">' if n < last else ""
    return f"<html><head>{nxt}</head><body>EVENTS PAGE {n}</body></html>"


def _install_fake_fetch(monkeypatch, pages: int, fail_on: int | None = None):
    """Fake page-1 fetch + plain fetch_url for later pages."""
    calls = []

    def fake_first(*, source_id, url, render_state):
        calls.append(url)
        return {"status": "ok", "text": _page(1, pages), "storage_ref": "x"}

    def fake_fetch_url(*, source_id, url):
        calls.append(url)
        n = int(url.rsplit("page=", 1)[1])
        if fail_on is not None and n == fail_on:
            raise RuntimeError("network went away")
        return {"status": "ok", "storage_ref": f"ref-{n}", "_n": n}

    monkeypatch.setattr(orch, "_fetch_with_render_fallback", fake_first)
    monkeypatch.setattr(orch, "fetch_url", fake_fetch_url)
    monkeypatch.setattr(orch, "_read_fetched_text",
                        lambda r: _page(r["_n"], pages))
    return calls


def test_walk_follows_pages_up_to_the_cap(monkeypatch):
    monkeypatch.setenv("INGEST_MAX_PAGES_PER_SOURCE", "5")
    _install_fake_fetch(monkeypatch, pages=60)
    out = orch._fetch_paginated(source_id=None, url="https://cal.example/cal",
                                render_state={})
    assert out["pages_fetched"] == 5
    for n in range(1, 6):
        assert f"EVENTS PAGE {n}" in out["text"]
    assert "EVENTS PAGE 6" not in out["text"]


def test_walk_stops_when_the_calendar_ends(monkeypatch):
    monkeypatch.setenv("INGEST_MAX_PAGES_PER_SOURCE", "10")
    _install_fake_fetch(monkeypatch, pages=3)
    out = orch._fetch_paginated(source_id=None, url="https://cal.example/cal",
                                render_state={})
    assert out["pages_fetched"] == 3


def test_a_later_page_failure_keeps_everything_already_read(monkeypatch):
    monkeypatch.setenv("INGEST_MAX_PAGES_PER_SOURCE", "5")
    _install_fake_fetch(monkeypatch, pages=60, fail_on=3)
    out = orch._fetch_paginated(source_id=None, url="https://cal.example/cal",
                                render_state={})
    assert out["pages_fetched"] == 2  # pages 1 and 2 survived
    assert "EVENTS PAGE 2" in out["text"]


def test_single_page_source_is_unchanged(monkeypatch):
    monkeypatch.setenv("INGEST_MAX_PAGES_PER_SOURCE", "5")
    monkeypatch.setattr(orch, "_fetch_with_render_fallback",
                        lambda **kw: {"status": "ok", "text": "<html>one page</html>"})
    out = orch._fetch_paginated(source_id=None, url="https://cal.example/cal",
                                render_state={})
    assert out["pages_fetched"] == 1
    assert out["text"] == "<html>one page</html>"


def test_not_modified_and_errors_never_paginate(monkeypatch):
    for first in ({"status": "not_modified"}, {"status": "error"},
                  {"status": "ok", "text": ""}):
        def _fake(_f=first, **kw):
            return dict(_f)

        monkeypatch.setattr(orch, "_fetch_with_render_fallback", _fake)
        out = orch._fetch_paginated(source_id=None, url="https://cal.example/c",
                                    render_state={})
        assert "pages_fetched" not in out  # untouched result, verbatim
        assert out["status"] == first["status"]


def test_cap_of_one_disables_the_walk(monkeypatch):
    monkeypatch.setenv("INGEST_MAX_PAGES_PER_SOURCE", "1")
    calls = _install_fake_fetch(monkeypatch, pages=60)
    out = orch._fetch_paginated(source_id=None, url="https://cal.example/cal",
                                render_state={})
    assert out.get("pages_fetched", 1) == 1
    assert len(calls) == 1  # no page-2 fetch at all


def test_malformed_cap_falls_back_to_the_default(monkeypatch):
    monkeypatch.setenv("INGEST_MAX_PAGES_PER_SOURCE", "not-a-number")
    assert orch._max_pages_per_source() == orch._DEFAULT_MAX_PAGES_PER_SOURCE
    monkeypatch.setenv("INGEST_MAX_PAGES_PER_SOURCE", "0")
    assert orch._max_pages_per_source() == orch._DEFAULT_MAX_PAGES_PER_SOURCE


# ── Adversarial pre-review blockers (2026-08-05) ────────────────────────────

def test_a_fragment_next_link_is_not_a_new_page():
    """BLOCKER: `<a href="#page-2">Next</a>` — an ordinary client-side
    pagination control — urljoin'd to "<current>#page-2", which was neither in
    `seen` nor string-equal to the current URL, so page 1 was fetched again and
    its events counted twice. (`href="#"` was already refused because urljoin
    drops an empty fragment, which is why this near-miss went unnoticed.)"""
    from worker.fetch.paginate import discover_next_page
    html = '<a href="#page-2">Next</a>'
    assert discover_next_page(html, "https://cal.example/events") is None
    assert discover_next_page('<link rel="next" href="#page-2">',
                              "https://cal.example/events") is None


def test_an_alternate_spelling_of_a_visited_page_is_refused():
    """BLOCKER: `seen` compared raw strings, so a next-link written with a
    different host case passed the origin check (urlparse lowercases .hostname)
    and re-entered the walk."""
    from worker.fetch.paginate import discover_next_page, canonical
    seen = {"https://cal.example/cal", "https://cal.example/cal?page=2"}
    for spelling in ('<link rel="next" href="https://CAL.EXAMPLE/cal">',
                     '<link rel="next" href="https://cal.example/cal#top">',
                     '<link rel="next" href="HTTPS://Cal.Example/cal?page=2">'):
        assert discover_next_page(spelling, "https://cal.example/cal?page=2",
                                  seen) is None, spelling
    # A genuinely new page is still followed.
    assert discover_next_page('<link rel="next" href="/cal?page=3">',
                              "https://cal.example/cal?page=2", seen) == \
        "https://cal.example/cal?page=3"
    # canonical() keeps what actually distinguishes pages.
    assert canonical("https://a.example/x?page=2") != canonical("https://a.example/x?page=3")
    assert canonical("https://a.example") == canonical("https://A.EXAMPLE/")


def test_a_bad_later_page_does_not_sink_the_good_ones(monkeypatch):
    """BLOCKER: the joined text goes to assess_input as ONE document, so an
    interstitial or truncated tail on page 3 rejected pages 1-2 with it and
    dropped the whole source to ZERO events. Rate-limit interstitials are the
    realistic trigger — the walk makes several requests to one host."""
    from worker import orchestrator

    good = ("<html><body>" + "".join(
        f"<div class='ev'><h3>Show {i}</h3><p>Aug {i}, 2026 at 8pm</p></div>"
        for i in range(1, 12)) + "</body></html>")
    interstitial = "<html><body><h1>Just a moment...</h1></body></html>"

    pages = {
        "https://cal.example/c": good,
        "https://cal.example/c?page=2": good.replace("Show", "Later"),
        "https://cal.example/c?page=3": interstitial,
    }
    order = ["https://cal.example/c?page=2", "https://cal.example/c?page=3", None]
    calls = {"n": 0}

    def fake_next(html, current_url, seen=None):
        i = calls["n"]
        calls["n"] += 1
        return order[i] if i < len(order) else None

    monkeypatch.setattr(orchestrator, "discover_next_page", fake_next)
    monkeypatch.setattr(orchestrator, "_fetch_with_render_fallback",
                        lambda **kw: {"status": "ok", "text": pages[kw["url"]]})
    monkeypatch.setattr(orchestrator, "fetch_url",
                        lambda **kw: {"status": "ok", "text": pages[kw["url"]]})
    monkeypatch.setattr(orchestrator, "_read_fetched_text",
                        lambda r: r.get("text", ""))
    monkeypatch.setenv("INGEST_MAX_PAGES_PER_SOURCE", "5")

    out = orchestrator._fetch_paginated(
        source_id="s1", url="https://cal.example/c", render_state={})

    # Pages 1 and 2 survive; the interstitial never joins the document.
    assert out["pages_fetched"] == 2
    assert "Just a moment" not in out["text"]
    assert "Show 1" in out["text"] and "Later 1" in out["text"]
    # And what survives still passes the sensor — the whole point.
    from worker.sensors import assess_input
    assert assess_input(text=out["text"], content_type=None).ok


def test_pages_beyond_the_extraction_budget_are_not_fetched(monkeypatch):
    """BLOCKER: the extraction cap applies to the CONCATENATION, so once page 1
    already fills the run's block budget, pages 2..N were fetched and then
    truncated away — requests, rate-limit exposure and wall clock spent for
    zero events. The walk now stops when the budget is already full."""
    from worker import orchestrator

    big = ("<html><body>" + "".join(
        f"<div class='ev'><h3>Show {i}</h3><p>Aug 1, 2026 at 8pm</p></div>"
        for i in range(1, 40)) + "</body></html>")
    fetched = []

    monkeypatch.setattr(orchestrator, "discover_next_page",
                        lambda html, url, seen=None: "https://cal.example/c?page=2")

    def _first(**kw):
        fetched.append(kw["url"])
        return {"status": "ok", "text": big}

    def _later(**kw):
        fetched.append(kw["url"])
        return {"status": "ok", "text": big}

    monkeypatch.setattr(orchestrator, "_fetch_with_render_fallback", _first)
    monkeypatch.setattr(orchestrator, "fetch_url", _later)
    monkeypatch.setattr(orchestrator, "_read_fetched_text", lambda r: r.get("text", ""))
    monkeypatch.setenv("INGEST_MAX_PAGES_PER_SOURCE", "5")
    # A budget page 1 alone already exceeds.
    monkeypatch.setenv("EXTRACT_MAX_EVENTS_PER_PAGE", "5")

    out = orchestrator._fetch_paginated(
        source_id="s1", url="https://cal.example/c", render_state={})

    assert out["pages_fetched"] == 1
    assert fetched == ["https://cal.example/c"], (
        f"no page should be fetched once the budget is full; fetched {fetched}")


def test_a_generous_budget_still_pages_normally(monkeypatch):
    """The budget stop must not become a new way to lose pages: with room left,
    the walk proceeds exactly as before."""
    from worker import orchestrator

    small = ("<html><body>"
             "<div class='ev'><h3>One Show</h3><p>Aug 1, 2026 at 8pm</p></div>"
             "</body></html>")
    order = ["https://cal.example/c?page=2", None]
    calls = {"n": 0}

    def fake_next(html, url, seen=None):
        i = calls["n"]
        calls["n"] += 1
        return order[i] if i < len(order) else None

    monkeypatch.setattr(orchestrator, "discover_next_page", fake_next)
    monkeypatch.setattr(orchestrator, "_fetch_with_render_fallback",
                        lambda **kw: {"status": "ok", "text": small})
    monkeypatch.setattr(orchestrator, "fetch_url",
                        lambda **kw: {"status": "ok", "text": small.replace("One", "Two")})
    monkeypatch.setattr(orchestrator, "_read_fetched_text", lambda r: r.get("text", ""))
    monkeypatch.setenv("INGEST_MAX_PAGES_PER_SOURCE", "5")
    monkeypatch.setenv("EXTRACT_MAX_EVENTS_PER_PAGE", "50")

    out = orchestrator._fetch_paginated(
        source_id="s1", url="https://cal.example/c", render_state={})
    assert out["pages_fetched"] == 2


def test_a_day_header_does_not_cross_the_page_seam(monkeypatch):
    """Adversarial-review BLOCKER (2026-08-05): the segmenter carries a
    calendar's day header forward as the governing date, so a page whose LAST
    element is a day header handed that date to the first event card of the
    NEXT page — a Sunday brunch published as Friday, from a page that never
    said so. Reproduced against the real segmenter before the fix."""
    from worker import orchestrator
    from worker.segment import _ElementTextCollector

    page1 = ("<html><body><div class='ev'>Late Set 9pm</div>"
             "<h2>Friday, August 14, 2026</h2></body></html>")
    page2 = "<div class='ev'>Brunch Jazz 11:00 AM</div>"
    order = ["https://cal.example/c?page=2", None]
    calls = {"n": 0}

    def fake_next(html, url, seen=None):
        i = calls["n"]
        calls["n"] += 1
        return order[i] if i < len(order) else None

    monkeypatch.setattr(orchestrator, "discover_next_page", fake_next)
    monkeypatch.setattr(orchestrator, "_fetch_with_render_fallback",
                        lambda **kw: {"status": "ok", "text": page1})
    monkeypatch.setattr(orchestrator, "fetch_url",
                        lambda **kw: {"status": "ok", "text": page2})
    monkeypatch.setattr(orchestrator, "_read_fetched_text", lambda r: r.get("text", ""))
    monkeypatch.setenv("INGEST_MAX_PAGES_PER_SOURCE", "5")
    monkeypatch.setenv("EXTRACT_MAX_EVENTS_PER_PAGE", "50")

    out = orchestrator._fetch_paginated(
        source_id="s1", url="https://cal.example/c", render_state={})
    assert out["pages_fetched"] == 2

    c = _ElementTextCollector(
        lambda t, a: t == "div" and "ev" in a.get("class", ""))
    c.feed(out["text"])
    c.close()
    ctx = c.contexts + [None] * (len(c.blocks) - len(c.contexts))
    got = dict(zip(c.blocks, ctx))
    assert got["Brunch Jazz 11:00 AM"] is None, (
        "page 1's trailing day header must not govern page 2's first card; "
        f"got {got}")


def test_the_run_records_which_page_each_fetch_came_from(monkeypatch):
    """Adversarial-review finding (2026-08-05): the combined document is
    extracted under the source's URL, so without this the run has no record
    that an event was found on page 3 rather than page 1."""
    from worker import orchestrator

    html = "<html><body><div class='ev'>A Show 8pm</div></body></html>"
    order = ["https://cal.example/c?page=2", "https://cal.example/c?page=3", None]
    calls = {"n": 0}

    def fake_next(h, u, seen=None):
        i = calls["n"]
        calls["n"] += 1
        return order[i] if i < len(order) else None

    monkeypatch.setattr(orchestrator, "discover_next_page", fake_next)
    monkeypatch.setattr(orchestrator, "_fetch_with_render_fallback",
                        lambda **kw: {"status": "ok", "text": html})
    monkeypatch.setattr(orchestrator, "fetch_url",
                        lambda **kw: {"status": "ok", "text": html})
    monkeypatch.setattr(orchestrator, "_read_fetched_text", lambda r: r.get("text", ""))
    monkeypatch.setenv("INGEST_MAX_PAGES_PER_SOURCE", "5")
    monkeypatch.setenv("EXTRACT_MAX_EVENTS_PER_PAGE", "50")

    out = orchestrator._fetch_paginated(
        source_id="s1", url="https://cal.example/c", render_state={})
    assert out["page_urls"] == ["https://cal.example/c",
                                "https://cal.example/c?page=2",
                                "https://cal.example/c?page=3"]
    assert len(out["page_urls"]) == out["pages_fetched"]
