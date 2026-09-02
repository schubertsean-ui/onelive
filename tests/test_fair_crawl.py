"""Fair crawl end to end — many sources per wave, few pages each.

Founder, 2026-09-02: "many sources per wave, few pages each. Stop two fat
calendars from consuming the run." These tests pin that as behaviour, not as a
comment, and they produce the run table the ticket asks for.

Fully hermetic: fetch_url, extract_candidates, the candidate-store calls and
the crawl-state reads are faked in the orchestrator's namespace, so nothing
here touches the network, a model, or a database.

What is pinned:
  1. THE WAVE — the next K DUE sources by rotation cursor, not whoever has the
     most pages; and no source takes more than two fetches.
  2. THE DOOR — best_url is knocked on directly; an off-origin or dead one
     falls back to the registered start URL.
  3. UNCHANGED — 304 and an identical body hash both skip EXTRACTION (the part
     that costs money), and the conditional-GET validators are actually sent.
  4. WALLS — 401/403 is class D and one knock; 429/503 is a back-off and NOT a
     demotion; and a source whose catalog posture is undeclared is still
     FETCHED (Coverage Law: the catalog is greedy).
  5. THE TABLE — source | url fetched | changed? | candidates |
     skipped-unchanged | blocked.
"""
import datetime as _dt

import pytest

from worker.ai_extract import ExtractionOutcome
from worker.crawl_state import DoorFingerprint, SourceCrawlState
import worker.orchestrator as orchestrator
from worker.orchestrator import CLASS_D_WALL_MARKER, render_run_table, run_loop
from worker.run_once import order_for_rotation, take_due_wave

_TZ = _dt.timezone.utc
NOW = _dt.datetime(2026, 9, 2, 12, 0, tzinfo=_TZ)

CLASS_B_CONFIG = {"access_method": "public_web", "allowed": ["public_pages"]}

HOME_HTML = """
<html><body>
  <p>Venue marketing copy, long enough for the input sensor, saying nothing
     whatsoever about which bands are playing this week.</p>
  <nav><a href="/events">Events</a><a href="/calendar">Calendar</a></nav>
</body></html>
"""
PAGE_HTML = """
<html><body><p>Thursday: The Reverbs, 9pm, $10. Friday: Nightjar, 8pm, free.
Saturday: an actual listing with enough text for the input-quality sensor.</p>
</body></html>
"""


class FakeAIProvider:
    def extract_event_json(self, text, schema_json, system_prompt=None):
        raise AssertionError("extract_candidates is faked; the provider is never called")


class _HttpError(Exception):
    """Shaped like requests.HTTPError: the status lives on `.response`."""

    def __init__(self, status, url):
        super().__init__(f"HTTP {status}")
        self.response = type("R", (), {"status_code": status, "url": url})()


@pytest.fixture(autouse=True)
def _hermetic(tmp_path, monkeypatch):
    from worker.sourcing import catalog_posture
    monkeypatch.setattr(catalog_posture, "_INDEX", {})
    monkeypatch.setenv("ONELIVE_REPLAY_LOG_DIR", str(tmp_path / "replay"))
    monkeypatch.delenv("ONELIVE_MAX_FOLLOW_PAGES_PER_RUN", raising=False)
    monkeypatch.delenv("ONELIVE_DOORS_PER_SOURCE", raising=False)
    monkeypatch.setenv("ONELIVE_MAX_RENDERS_PER_RUN", "0")
    yield


def _source(name="venue", url="https://venue.example/", config=None, state=None):
    return {
        "source_id": f"src-{name}",
        "name": name,
        "url": url,
        "source_class": "venue_site",
        "config": CLASS_B_CONFIG if config is None else config,
        "crawl_state": state,
    }


def _install(monkeypatch, tmp_path, *, pages=None, errors=None, hashes=None,
             fingerprints=None, not_modified=(), candidates_per_page=1):
    """A fake server plus a fake crawl history.

    `hashes` maps url -> the content_hash the fetch reports; `fingerprints`
    maps url -> the hash already on record. Equal values are what "unchanged"
    means. `not_modified` is the set of urls whose server answers 304.
    """
    pages, errors = dict(pages or {}), dict(errors or {})
    hashes, fingerprints = dict(hashes or {}), dict(fingerprints or {})
    not_modified = set(not_modified)
    requested, conditional, extracted = [], [], []

    def fake_fetch_url(*, source_id, url, etag=None, last_modified=None, **kwargs):
        requested.append(url)
        conditional.append((url, etag, last_modified))
        if url in errors:
            raise errors[url]
        if url in not_modified:
            return {"status": "not_modified", "url": url}
        if url not in pages:
            raise FileNotFoundError(f"HTTP 404 for {url}")  # no .response: not a wall
        path = tmp_path / f"body-{len(requested)}.bin"
        path.write_bytes(pages[url].encode("utf-8"))
        return {
            "status": "ok", "url": url, "storage_ref": str(path), "final_url": url,
            "content_type": "text/html",
            "content_hash": hashes.get(url, f"h{len(requested)}"),
        }

    def fake_extract_candidates(*, ai, text, source_class, source_name, source_url,
                                sxsw_mode=False, source_id=None):
        extracted.append(source_url)
        return ExtractionOutcome(
            candidate_ids=[f"cand-{len(extracted)}-{i}"
                           for i in range(candidates_per_page)])

    def fake_fingerprint(source_id, url, cur=None):
        if url not in fingerprints:
            return None
        return DoorFingerprint(url=url, content_hash=fingerprints[url],
                               etag=f'W/"{url}"', last_modified="Mon, 01 Sep 2026")

    monkeypatch.setattr(orchestrator, "fetch_url", fake_fetch_url)
    monkeypatch.setattr(orchestrator, "extract_candidates", fake_extract_candidates)
    monkeypatch.setattr(orchestrator, "load_door_fingerprint", fake_fingerprint)
    monkeypatch.setattr(orchestrator, "list_candidate_source_classes",
                        lambda candidate_id: ["venue_site"])
    monkeypatch.setattr(orchestrator, "load_candidate_gate_signals",
                        lambda candidate_id, cur=None: (
                            {}, {"start_times": [], "dedupe_ambiguous": False}))
    monkeypatch.setattr(orchestrator, "stamp_gate_verdict", lambda candidate_id, **kw: True)
    return requested, conditional, extracted


# --- 1. the wave -------------------------------------------------------------

def _row(name, last):
    return (name, name, f"https://{name}.example/", "venue_site", {}, last)


def test_the_wave_is_the_next_k_due_sources_by_cursor():
    """Round-robin: least-recently-attempted first, K of them, and the ones
    that are not due are DEFERRED, not dropped — they lead the next wave."""
    rows = order_for_rotation([
        _row("fresh", NOW - _dt.timedelta(minutes=2)),
        _row("stalest", NOW - _dt.timedelta(days=9)),
        _row("never", None),
        _row("stale", NOW - _dt.timedelta(days=2)),
    ])
    sources = [{"source_id": r[0], "name": r[1], "url": r[2]} for r in rows]
    states = {
        "fresh": SourceCrawlState("fresh", last_attempt_at=NOW - _dt.timedelta(minutes=2)),
        "stalest": SourceCrawlState("stalest", last_attempt_at=NOW - _dt.timedelta(days=9)),
        "stale": SourceCrawlState("stale", last_attempt_at=NOW - _dt.timedelta(days=2)),
    }

    wave, deferred = take_due_wave(sources, states, 2, now=NOW)

    assert [s["source_id"] for s in wave] == ["never", "stalest"]
    assert deferred == 1, "'fresh' is inside its interval; it is not in the wave"


def test_a_source_with_no_crawl_history_is_due():
    """A row imported since the last run has no raw_fetch history. "We know
    nothing about it" must never read as "skip it" — that is silent coverage
    loss on exactly the rows an import just added."""
    sources = [{"source_id": "brand-new", "name": "n", "url": "https://n.example/"}]
    wave, deferred = take_due_wave(sources, {}, 5, now=NOW)
    assert [s["source_id"] for s in wave] == ["brand-new"]
    assert deferred == 0


def test_no_source_takes_more_than_two_fetches_from_a_wave(monkeypatch, tmp_path):
    """The defect this pass fixes: a link-heavy calendar used to walk 15 pages
    while the sources behind it got zero. Every source in this wave advertises
    two event pages; none of them gets to spend more than its two fetches."""
    requested, _, _ = _install(monkeypatch, tmp_path, pages={
        f"https://{n}.example/": HOME_HTML for n in ("a", "b", "c")
    } | {
        f"https://{n}.example/{p}": PAGE_HTML
        for n in ("a", "b", "c") for p in ("events", "calendar")
    })

    report = run_loop(ai=FakeAIProvider(), sources=[
        _source(n, url=f"https://{n}.example/") for n in ("a", "b", "c")])

    per_source = {n: [u for u in requested if f"//{n}." in u] for n in ("a", "b", "c")}
    assert all(len(urls) == 2 for urls in per_source.values()), per_source
    assert report.counts["fetched"] == 3, "every source in the wave was reached"
    assert report.counts["pages_followed"] == 3


# --- 2. the door -------------------------------------------------------------

def test_a_known_best_url_is_the_door_and_the_homepage_is_not_fetched(monkeypatch, tmp_path):
    """The steady state: one fetch, straight at the page that works."""
    requested, _, extracted = _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
        "https://venue.example/events": PAGE_HTML,
    })
    state = SourceCrawlState("src-venue", best_url="https://venue.example/events")

    run_loop(ai=FakeAIProvider(), sources=[_source(state=state)])

    assert requested == ["https://venue.example/events"]
    assert extracted == ["https://venue.example/events"]


def test_an_off_origin_best_url_is_refused_and_the_start_url_is_used(monkeypatch, tmp_path):
    requested, _, _ = _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
        "https://venue.example/events": PAGE_HTML,
    })
    state = SourceCrawlState("src-venue", best_url="https://tickets.example.com/venue")

    run_loop(ai=FakeAIProvider(), sources=[_source(state=state)])

    assert "https://tickets.example.com/venue" not in requested
    assert requested[0] == "https://venue.example/"


def test_a_dead_best_url_falls_back_to_the_start_url_in_the_same_wave(monkeypatch, tmp_path):
    """A venue moves its calendar. best_url is a shortcut, never a commitment:
    the source re-discovers itself on the very next run instead of quietly
    losing its coverage until a human notices."""
    requested, _, extracted = _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
    })
    state = SourceCrawlState("src-venue", best_url="https://venue.example/old-calendar")

    report = run_loop(ai=FakeAIProvider(), sources=[_source(state=state)])

    assert requested[:2] == ["https://venue.example/old-calendar", "https://venue.example/"]
    assert extracted == ["https://venue.example/"]
    assert report.counts["errors"] == 0
    assert len(requested) == 2, "the fallback IS the second door, not a third fetch"


# --- 3. unchanged ------------------------------------------------------------

def test_a_304_skips_extraction_entirely(monkeypatch, tmp_path):
    requested, _, extracted = _install(
        monkeypatch, tmp_path,
        pages={"https://venue.example/": HOME_HTML},
        fingerprints={"https://venue.example/": "h-old"},
        not_modified={"https://venue.example/"})

    report = run_loop(ai=FakeAIProvider(), sources=[_source()])

    assert extracted == [], "a 304 must never cost a model call"
    assert report.counts["skipped_unchanged"] == 1
    assert report.counts["not_modified"] == 1
    assert len(requested) == 1, "an unchanged door ends the source for this wave"


def test_the_previous_validators_are_actually_sent(monkeypatch, tmp_path):
    """The 304 above only happens if we ASK for it. Without these headers the
    server has no way to answer 'unchanged' and every run re-reads every page."""
    _, conditional, _ = _install(
        monkeypatch, tmp_path,
        pages={"https://venue.example/": HOME_HTML},
        fingerprints={"https://venue.example/": "h-old"})

    run_loop(ai=FakeAIProvider(), sources=[_source()])

    url, etag, last_modified = conditional[0]
    assert etag == 'W/"https://venue.example/"'
    assert last_modified == "Mon, 01 Sep 2026"


def test_an_identical_body_skips_extraction_even_without_validators(monkeypatch, tmp_path):
    """Plenty of venue sites send no ETag at all. The body's own sha256 is the
    backstop, and it is the extraction — not the fetch — that costs money."""
    requested, _, extracted = _install(
        monkeypatch, tmp_path,
        pages={"https://venue.example/": HOME_HTML},
        hashes={"https://venue.example/": "same-bytes"},
        fingerprints={"https://venue.example/": "same-bytes"})

    report = run_loop(ai=FakeAIProvider(), sources=[_source()])

    assert extracted == []
    assert report.counts["skipped_unchanged"] == 1
    assert report.counts["fetched"] == 1, "the bytes did arrive; only the extract was saved"
    assert len(requested) == 1


def test_a_changed_body_still_extracts(monkeypatch, tmp_path):
    _, _, extracted = _install(
        monkeypatch, tmp_path,
        pages={"https://venue.example/": HOME_HTML,
               "https://venue.example/events": PAGE_HTML},
        hashes={"https://venue.example/": "new-bytes"},
        fingerprints={"https://venue.example/": "old-bytes"})

    report = run_loop(ai=FakeAIProvider(), sources=[_source()])

    assert "https://venue.example/" in extracted
    assert report.counts["skipped_unchanged"] == 0


def test_a_fingerprint_lookup_failure_extracts_rather_than_losing_the_page(
        monkeypatch, tmp_path, caplog):
    """Fail OPEN on availability, closed on trust. A lost optimisation costs
    one extraction; a lost page costs a venue's whole calendar."""
    _install(monkeypatch, tmp_path, pages={"https://venue.example/": HOME_HTML})

    def _boom(source_id, url, cur=None):
        raise RuntimeError("DSN not configured")

    monkeypatch.setattr(orchestrator, "load_door_fingerprint", _boom)
    with caplog.at_level("WARNING"):
        report = run_loop(ai=FakeAIProvider(), sources=[_source()])

    assert report.counts["extracted"] == 1
    assert any("fingerprint lookup failed" in r.message for r in caplog.records)


# --- 4. walls and back-offs --------------------------------------------------

@pytest.mark.parametrize("status", [401, 403])
def test_a_wall_on_the_start_page_is_class_d_and_one_knock(
        monkeypatch, tmp_path, caplog, status):
    requested, _, extracted = _install(
        monkeypatch, tmp_path,
        pages={"https://venue.example/": HOME_HTML},
        errors={"https://venue.example/": _HttpError(status, "https://venue.example/")})

    with caplog.at_level("WARNING"):
        report = run_loop(ai=FakeAIProvider(), sources=[_source()])

    assert requested == ["https://venue.example/"], "we knock once"
    assert extracted == []
    assert report.counts["blocked"] == 1
    assert report.counts["errors"] == 0, (
        "a closed door is a classified outcome, not a harness failure")
    assert any(CLASS_D_WALL_MARKER in r.message for r in caplog.records), (
        "ops greps this marker to build the claim queue")
    assert "class D" in report.results[0].blocked


@pytest.mark.parametrize("status", [429, 503])
def test_rate_limiting_is_a_backoff_not_a_demotion(monkeypatch, tmp_path, caplog, status):
    """Founder's rule, verbatim: "401/403 -> class D, one knock, fail_streak++.
    429/503 -> back off." A server saying "slow down" has not said "you are not
    invited", and demoting it to class D would route a public source to the
    claim queue for being popular."""
    requested, _, _ = _install(
        monkeypatch, tmp_path,
        pages={"https://venue.example/": HOME_HTML},
        errors={"https://venue.example/": _HttpError(status, "https://venue.example/")})

    with caplog.at_level("WARNING"):
        report = run_loop(ai=FakeAIProvider(), sources=[_source()])

    assert requested == ["https://venue.example/"]
    assert report.counts["blocked"] == 1
    assert report.counts["errors"] == 0
    assert not any(CLASS_D_WALL_MARKER in r.message for r in caplog.records)
    assert "backing off" in report.results[0].blocked


def test_a_source_with_no_declared_posture_is_still_fetched(monkeypatch, tmp_path):
    """Coverage Law: the catalog is GREEDY. 264 of 266 enabled rows declare no
    access posture, so classifying them D before a fetch would refuse almost
    the whole catalog. The class letter gates FOLLOWING, never fetching."""
    requested, _, extracted = _install(
        monkeypatch, tmp_path, pages={"https://venue.example/": HOME_HTML})

    report = run_loop(ai=FakeAIProvider(), sources=[_source(config={})])

    assert requested == ["https://venue.example/"]
    assert extracted == ["https://venue.example/"]
    assert report.counts["fetched"] == 1
    assert report.counts["blocked"] == 0


def test_a_404_on_the_start_page_is_still_this_sources_error(monkeypatch, tmp_path):
    """A broken page is not a wall, and it must keep surfacing as this source's
    loud per-source failure exactly as it did before fair crawl."""
    _install(monkeypatch, tmp_path, pages={})
    report = run_loop(ai=FakeAIProvider(), sources=[_source()])
    assert report.counts["errors"] == 1
    assert report.counts["blocked"] == 0


# --- 5. the table ------------------------------------------------------------

def test_the_run_table_reports_every_column_the_ticket_asks_for(monkeypatch, tmp_path):
    """The founder's table. Fair crawl is a claim about DISTRIBUTION, and a
    counts dict cannot show distribution — one row per source can."""
    _install(
        monkeypatch, tmp_path,
        pages={"https://a.example/": HOME_HTML, "https://a.example/events": PAGE_HTML,
               "https://b.example/": HOME_HTML},
        hashes={"https://b.example/": "same"},
        fingerprints={"https://b.example/": "same"},
        errors={"https://c.example/": _HttpError(403, "https://c.example/")},
        candidates_per_page=2)

    report = run_loop(ai=FakeAIProvider(), sources=[
        _source("a", url="https://a.example/"),
        _source("b", url="https://b.example/"),
        _source("c", url="https://c.example/"),
    ])
    table = render_run_table(report)
    print("\n" + table)

    header = table.splitlines()[0]
    for column in ("source", "url fetched", "changed?", "candidates",
                   "skipped-unchanged", "blocked"):
        assert column in header
    rows = {line.split("|")[0].strip(): line for line in table.splitlines()[2:]}
    assert "yes" in rows["a"] and "4" in rows["a"]   # 2 candidates x 2 doors
    assert "no" in rows["b"] and rows["b"].split("|")[4].strip() == "1"
    assert "class D" in rows["c"]
