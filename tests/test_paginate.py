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
