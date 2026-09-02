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
from worker.crawl_state import (
    QUEUE_DISCOVER,
    QUEUE_EVENT,
    QUEUE_REFRESH,
    UNVERIFIED,
    VERIFIED_ABSENT,
    VERIFIED_PRESENT,
    DoorFingerprint,
    EventRefresh,
    SourceCrawlState,
    TickBudget,
)
import worker.orchestrator as orchestrator
from worker.orchestrator import CLASS_D_WALL_MARKER, render_run_table, run_loop
from worker.run_once import order_for_rotation, plan_tick, render_outcomes

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
    # The class the GATE sees for this page's evidence. `venue_calendar` is an
    # anchor class (worker/gating.py), so a page that parses cleanly reaches
    # PASS — which since R-091(a) is what `verified_present` requires. The
    # earlier fixture used `venue_site`, a class the gate does not recognise at
    # all (it logs UNCLASSIFIED and HOLDs), so every fixture check would now be
    # unverified for a reason that was never what these tests are about.
    monkeypatch.setattr(orchestrator, "list_candidate_source_classes",
                        lambda candidate_id: ["venue_calendar"])
    monkeypatch.setattr(orchestrator, "load_candidate_gate_signals",
                        lambda candidate_id, cur=None: (
                            {}, {"start_times": [], "dedupe_ambiguous": False}))
    monkeypatch.setattr(orchestrator, "stamp_gate_verdict", lambda candidate_id, **kw: True)
    return requested, conditional, extracted


# --- 1. the wave -------------------------------------------------------------

def _row(name, last):
    return (name, name, f"https://{name}.example/", "venue_site", {}, last)


def _plan_sources(names_and_last):
    rows = order_for_rotation([_row(n, t) for n, t in names_and_last])
    return [{"source_id": r[0], "name": r[1], "url": r[2]} for r in rows]


def test_the_tick_plan_is_ordered_most_overdue_first():
    """Not "the next K sources": the plan is everything DUE, most overdue
    first, and how much of it happens is decided by the tick's budgets."""
    sources = _plan_sources([
        ("fresh", NOW - _dt.timedelta(minutes=2)),
        ("stalest", NOW - _dt.timedelta(days=9)),
        ("never", None),
        ("stale", NOW - _dt.timedelta(days=2)),
    ])
    states = {
        "fresh": SourceCrawlState("fresh", last_attempt_at=NOW - _dt.timedelta(minutes=2)),
        "stalest": SourceCrawlState("stalest", last_attempt_at=NOW - _dt.timedelta(days=9)),
        "stale": SourceCrawlState("stale", last_attempt_at=NOW - _dt.timedelta(days=2)),
    }

    planned, deferred = plan_tick(sources, states, now=NOW)

    assert [s["source_id"] for s in planned] == ["never", "stalest", "stale"]
    assert deferred == 1, "'fresh' is inside its interval; it leads a later tick"


def test_a_source_with_no_crawl_history_is_due():
    """A row imported since the last tick has no raw_fetch history. "We know
    nothing about it" must never read as "skip it" — that is silent coverage
    loss on exactly the rows an import just added."""
    sources = [{"source_id": "brand-new", "name": "n", "url": "https://n.example/"}]
    planned, deferred = plan_tick(sources, {}, now=NOW)
    assert [s["source_id"] for s in planned] == ["brand-new"]
    assert planned[0]["queue"] == QUEUE_DISCOVER
    assert deferred == 0


def test_event_proximity_pages_lead_the_plan_and_carry_their_door():
    """A published event near a rung outranks routine turns, and the item is a
    PAGE — the loop is handed the defining URL, not the source's homepage."""
    sources = _plan_sources([("venue", None)])
    refresh = EventRefresh(source_id="venue", url="https://venue.example/calendar",
                           rung_hours=6, overdue_seconds=3600, events=4)

    planned, _ = plan_tick(sources, {}, [refresh], now=NOW)

    assert planned[0]["queue"] == QUEUE_EVENT
    assert planned[0]["door"] == "https://venue.example/calendar"
    assert "4 published event(s)" in planned[0]["queue_reason"]


def test_one_page_is_not_fetched_twice_in_one_tick():
    """Dedupe across queues: if the event page IS the source's best door, the
    event item covers it and the source item is dropped for this tick."""
    sources = _plan_sources([("venue", None)])
    state = SourceCrawlState("venue", best_url="https://venue.example/calendar")
    refresh = EventRefresh(source_id="venue", url="https://venue.example/calendar",
                           rung_hours=6, overdue_seconds=3600)

    planned, _ = plan_tick(sources, {"venue": state}, [refresh], now=NOW)

    assert len(planned) == 1
    assert planned[0]["queue"] == QUEUE_EVENT


def test_no_source_takes_more_than_two_fetches_from_a_tick(monkeypatch, tmp_path):
    """The defect this pass fixes: a link-heavy calendar used to walk 15 pages
    while the sources behind it got zero. Every source here advertises two
    event pages; none of them gets to spend more than its two fetches."""
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


def test_a_fallback_never_reports_the_gone_page_as_verified(monkeypatch, tmp_path):
    """Evaluator finding (seat openai / lens absence-only, PR #213), and it was
    a real one: when a remembered best door 404s, the loop falls back to the
    registered start URL — and the fallback's SUCCESS was overwriting the
    defining page's verdict, so a page that is gone displayed as
    `verified? present`. A gone page shown as re-verified is precisely the
    misleading trust display the fail-closed rule exists to prevent, and it
    would have poisoned the listing-update path the moment that path is built.

    The verdict must describe the page the tick came to read. The fallback is
    still reported — as the different fact it is: the source's door was
    re-found."""
    _install(monkeypatch, tmp_path,
             pages={"https://venue.example/": HOME_HTML},
             errors={"https://venue.example/gone":
                     _HttpError(404, "https://venue.example/gone")})
    state = SourceCrawlState("src-venue", best_url="https://venue.example/gone")

    report = run_loop(ai=FakeAIProvider(), sources=[_source(state=state)],
                      budget=TickBudget())

    result = report.results[0]
    assert result.verdict == VERIFIED_ABSENT, (
        "the defining page 404'd; the homepage answering says nothing about it")
    assert "re-found" in result.verdict_reason
    assert "https://venue.example/gone" in result.verdict_reason
    # The table a human reads must not say "present" for the page that is gone.
    assert "present" not in render_run_table(report).split("\n")[2]
    # ...and the fallback still did its job: the source was read, not lost.
    assert report.counts["extracted"] == 1
    assert report.counts["errors"] == 0


def test_a_healthy_door_still_reports_present(monkeypatch, tmp_path):
    """The guard above must not make every source unverified — no fallback
    happened here, so the door's own clean parse stands."""
    _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
        "https://venue.example/events": PAGE_HTML})
    state = SourceCrawlState("src-venue", best_url="https://venue.example/events")
    report = run_loop(ai=FakeAIProvider(), sources=[_source(state=state)],
                      budget=TickBudget())
    assert report.results[0].verdict == VERIFIED_PRESENT


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
    for column in ("source", "queue", "url fetched", "changed?", "verified?",
                   "candidates", "skipped-unchanged", "blocked"):
        assert column in header
    cells = {line.split("|")[0].strip(): [c.strip() for c in line.split("|")]
             for line in table.splitlines()[2:]}
    assert cells["a"][3] == "yes" and cells["a"][5] == "4"  # 2 candidates x 2 doors
    # b: identical bytes -> not changed, still VERIFIED present, extract saved.
    assert cells["b"][3] == "no"
    assert cells["b"][4] == "present"
    assert cells["b"][6] == "1"
    # c: a wall confirms nothing about c's listings — fail closed.
    assert "class D" in cells["c"][7]
    assert cells["c"][4] == "no"


# --- 6. the tick stops on budgets, and says which one ------------------------

class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _many(monkeypatch, tmp_path, n):
    names = [f"s{i}" for i in range(n)]
    _install(monkeypatch, tmp_path,
             pages={f"https://{n_}.example/": PAGE_HTML for n_ in names})
    return [_source(n_, url=f"https://{n_}.example/") for n_ in names]


def test_the_tick_stops_on_the_wall_clock_and_defers_the_rest(monkeypatch, tmp_path):
    """How many sources a tick reaches is an OUTCOME. Everything it did not
    reach is DEFERRED and counted — a tick that quietly stopped early would
    look exactly like a catalog with nothing to say."""
    sources = _many(monkeypatch, tmp_path, 5)
    clock = _Clock()
    budget = TickBudget(max_seconds=10, clock=clock)

    real = orchestrator._run_one_source

    def _slow(**kwargs):
        clock.t += 4          # each source burns 4 of the 10 seconds
        return real(**kwargs)

    monkeypatch.setattr(orchestrator, "_run_one_source", _slow)
    report = run_loop(ai=FakeAIProvider(), sources=sources, budget=budget)

    assert report.outcomes["stop_reason"] == "wall_clock"
    # Two sources ran inside the budget. The third started, found the clock
    # spent at its first fetch, and was deferred individually; the remaining
    # two never started and were deferred in bulk. Every one of the five is
    # accounted for — a tick that quietly stopped early would look exactly
    # like a catalog with nothing to say.
    assert report.outcomes["sources_touched"] == 2
    assert report.outcomes["sources_deferred"] == 3
    assert report.counts["deferred"] == 3


def test_the_tick_stops_on_the_model_budget(monkeypatch, tmp_path):
    sources = _many(monkeypatch, tmp_path, 4)
    report = run_loop(ai=FakeAIProvider(), sources=sources,
                      budget=TickBudget(max_extract_calls=2))
    assert report.outcomes["stop_reason"] == "model_budget"
    assert report.outcomes["extract_calls"] == 2


def test_the_fetch_cap_is_a_bug_safety_net_not_the_schedule(monkeypatch, tmp_path):
    sources = _many(monkeypatch, tmp_path, 6)
    report = run_loop(ai=FakeAIProvider(), sources=sources,
                      budget=TickBudget(max_fetches=3))
    assert report.outcomes["stop_reason"] == "fetch_budget"
    assert report.outcomes["fetches"] == 3


def test_host_politeness_defers_a_source_without_ending_the_tick(monkeypatch, tmp_path):
    """Two catalog rows on one host: the second waits, and the tick goes on to
    a source somewhere else."""
    _install(monkeypatch, tmp_path, pages={
        "https://shared.example/one": PAGE_HTML,
        "https://shared.example/two": PAGE_HTML,
        "https://other.example/": PAGE_HTML,
    })
    sources = [
        _source("one", url="https://shared.example/one"),
        _source("two", url="https://shared.example/two"),
        _source("three", url="https://other.example/"),
    ]
    report = run_loop(ai=FakeAIProvider(), sources=sources,
                      budget=TickBudget(max_fetches_per_host=1))

    by_name = {r.source_name: r for r in report.results}
    assert by_name["two"].decision == "deferred"
    assert "host" in by_name["two"].detail
    assert by_name["three"].decision != "deferred", "the tick was not ended"
    assert report.outcomes["stop_reason"] == "exhausted"


def test_a_tick_reports_fetches_extracts_and_dollars(monkeypatch, tmp_path):
    """Founder: "Report fetches/extracts/$ as outcomes." Measured, not planned."""
    sources = _many(monkeypatch, tmp_path, 2)
    report = run_loop(ai=FakeAIProvider(), sources=sources, budget=TickBudget())
    line = render_outcomes(report, model_id="claude-haiku-4-5-20251001")
    assert "fetches:" in line and "extract calls:" in line
    # Two discover sources: each spends its start page plus one probe of the
    # conventional /events path, which 404s here.
    assert report.outcomes["fetches"] == 4
    assert report.outcomes["extract_calls"] == 2
    # The fake extractor reports no token usage, so the cost must say so rather
    # than print $0.00 — a fabricated cost is worse than no cost.
    assert "unknown (the provider reported no token usage)" in line


def test_an_unpriced_model_is_reported_as_unknown_not_as_free(monkeypatch, tmp_path):
    sources = _many(monkeypatch, tmp_path, 1)
    report = run_loop(ai=FakeAIProvider(), sources=sources, budget=TickBudget())
    assert "not in the docs/MODEL_ROUTING.md price table" in render_outcomes(
        report, model_id="claude-something-unreleased")


# --- 7. verification is fail-closed ------------------------------------------

def test_an_unchanged_page_is_positive_confirmation(monkeypatch, tmp_path):
    """A 304 or an identical hash is EVIDENCE the page still says what it said —
    stronger than a fresh parse, not weaker."""
    _install(monkeypatch, tmp_path,
             pages={"https://venue.example/": HOME_HTML},
             hashes={"https://venue.example/": "same"},
             fingerprints={"https://venue.example/": "same"})
    report = run_loop(ai=FakeAIProvider(), sources=[_source()], budget=TickBudget())
    assert report.results[0].verdict == VERIFIED_PRESENT


@pytest.mark.parametrize("status,expected", [
    (403, UNVERIFIED),      # a wall confirms nothing
    (429, UNVERIFIED),      # rate limiting confirms nothing
])
def test_a_blocked_check_confirms_nothing(monkeypatch, tmp_path, status, expected):
    _install(monkeypatch, tmp_path,
             pages={"https://venue.example/": HOME_HTML},
             errors={"https://venue.example/": _HttpError(status, "https://venue.example/")})
    report = run_loop(ai=FakeAIProvider(), sources=[_source()], budget=TickBudget())
    assert report.results[0].verdict == expected
    assert "last good row stands" in report.results[0].verdict_reason


def test_a_clear_404_on_the_defining_page_is_confirmed_absence(monkeypatch, tmp_path):
    """And it is absence of the PAGE. Whether a particular event vanished from a
    page that still loads is the mutation path's question, not this one's."""
    _install(monkeypatch, tmp_path, pages={"https://venue.example/": HOME_HTML},
             errors={"https://venue.example/events":
                     _HttpError(404, "https://venue.example/events")})
    state = SourceCrawlState("src-venue", best_url="https://venue.example/events")
    report = run_loop(ai=FakeAIProvider(), sources=[_source(state=state)],
                      budget=TickBudget())
    # The best door 404'd, so the tick fell back to the start URL and the
    # source's own verdict is about what it finally read. The 404 itself is
    # classified where it happens:
    from worker.crawl_state import classify_recheck
    assert classify_recheck(door_kind="missed", http_status=404)[0] == VERIFIED_ABSENT
    assert report.counts["errors"] == 0


def test_the_loop_never_publishes_and_carries_no_sql_of_its_own():
    """Founder: "no delete, no cancel, no date edit" unless confirmed.

    RESTATED at Session Contract #55, because the loop now CAN change a
    published listing and a test claiming otherwise would be a false green. What
    is still structurally true, and is what this checks: the loop never
    PROMOTES, and it carries no SQL of its own — the one path that can change
    an `event` row is worker/listing_update.py, which owns every guard, has no
    DELETE and no INSERT, and is pinned by its own structural test
    (tests/test_listing_update.py). Checked over the AST rather than the text,
    so prose in a docstring cannot fail it and — far more important — cannot
    satisfy it either."""
    import ast
    import pathlib
    import re
    tree = ast.parse(pathlib.Path(orchestrator.__file__).read_text())

    called = {getattr(n.func, "id", None) or getattr(n.func, "attr", None)
              for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert "promote_candidate" not in called
    assert "execute" not in called, (
        "the loop issues no SQL of its own — every DB touch goes through a "
        "store module that owns the statement and its guards")

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert not re.search(r"\b(update|delete\s+from)\s+event\b",
                                 node.value, re.IGNORECASE), node.value[:80]


def test_only_the_event_proximity_queue_can_change_a_published_listing():
    """A published row may only be touched by the queue whose whole purpose is
    re-reading the page that defines it. A refresh or discover source taking its
    ordinary turn never reaches the writer — checked structurally, because this
    is a guard that a later "while I'm here" edit could quietly widen."""
    import ast
    import pathlib
    tree = ast.parse(pathlib.Path(orchestrator.__file__).read_text())
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call)
             and (getattr(n.func, "id", None) == "_update_listings_for")]
    assert len(calls) == 1, "exactly one call site, so the guard has one home"
    guarded = [n for n in ast.walk(tree)
               if isinstance(n, ast.If)
               and any(isinstance(c, ast.Call)
                       and getattr(c.func, "id", None) == "_update_listings_for"
                       for c in ast.walk(n))
               and "QUEUE_EVENT" in ast.dump(n.test)]
    assert guarded, "the call site is not guarded on QUEUE_EVENT"


def test_extraction_is_the_only_stage_that_may_call_a_model():
    """Founder: "Extract is the only stage that may call Anthropic." The AI
    provider must reach exactly one callee in the loop — extract_candidates.
    Everything else (fetch, sensor, discovery, gate, scheduling) is
    deterministic, so a model call anywhere else is spend nobody budgeted."""
    import ast
    import pathlib
    tree = ast.parse(pathlib.Path(orchestrator.__file__).read_text())
    callees = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        passes_ai = any(
            kw.arg == "ai" and isinstance(kw.value, ast.Name) and kw.value.id == "ai"
            for kw in node.keywords)
        if passes_ai:
            callees.add(getattr(node.func, "id", None) or getattr(node.func, "attr", None))
    assert callees == {"extract_candidates", "_process_fetched_page",
                       "_discover_second_door", "_run_one_source"}, callees
    # ...and of those, only extract_candidates is not a function in this module
    # that merely forwards it onward to the same place.
    assert "extract_event_json" not in pathlib.Path(orchestrator.__file__).read_text()

# --- 8. the listing-update path, end to end through the loop -----------------
#
# The adjudication itself is pinned field by field in tests/test_listing_update.py.
# These prove the WIRING, which is the half a pure test cannot reach: that the
# loop reaches the writer at all, that it reaches it ONLY from the
# event-proximity queue, and that the verdict it hands over is the defining
# page's own.

def _install_listings(monkeypatch, *, published, gate_pass=True):
    """Fake the four DB touches the listing path makes, in the orchestrator's
    namespace. `written` collects the decisions that reached the writer, so a
    test can assert what WOULD have been written without a database."""
    from worker import listing_update

    written = []
    monkeypatch.setattr(orchestrator, "load_published_on_page",
                        lambda source_id, url: list(published))
    monkeypatch.setattr(
        orchestrator, "load_parsed_listings",
        lambda ids: [listing_update.ParsedListing(
            candidate_id=str(c), title="Nightjar",
            start_time=_dt.datetime(2026, 9, 15, 2, 0, tzinfo=_TZ)) for c in ids])
    monkeypatch.setattr(orchestrator, "gate_passes_for", lambda cid: gate_pass)

    def fake_apply(decisions, **kw):
        written.extend(d for d in decisions if d.mutates)
        return {"updated": sum(1 for d in decisions if d.action == "update"),
                "marked_gone": sum(1 for d in decisions if d.action == "mark_gone"),
                "skipped_budget": 0}

    monkeypatch.setattr(orchestrator, "apply_decisions", fake_apply)
    return written


def _published(**kw):
    from worker.listing_update import PublishedListing
    base = dict(event_id="e1", title="Nightjar",
                start_time=_dt.datetime(2026, 9, 15, 1, 0, tzinfo=_TZ))
    base.update(kw)
    return PublishedListing(**base)


def _event_source(door="https://venue.example/events"):
    src = _source()
    src["queue"] = QUEUE_EVENT
    src["door"] = door
    return src


def test_a_confirmed_event_recheck_updates_the_listing_through_the_loop(
        monkeypatch, tmp_path):
    """The whole pipe: the ladder hands the loop a PAGE, the page is fetched,
    extracted and gate-PASSed, and the published row it defines gets the new
    time the page now states."""
    _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
        "https://venue.example/events": PAGE_HTML})
    written = _install_listings(monkeypatch, published=[_published()])

    report = run_loop(ai=FakeAIProvider(), sources=[_event_source()],
                      budget=TickBudget())

    assert report.results[0].verdict == VERIFIED_PRESENT
    assert [d.action for d in written] == ["update"]
    assert "start_time" in written[0].fields
    assert report.counts["listings_updated"] == 1


def test_an_ordinary_source_turn_never_reaches_the_writer(monkeypatch, tmp_path):
    """Coverage Law's own shape of this rule: a refresh or discover source
    taking its normal turn re-reads pages all day and changes nothing
    published. Only the queue whose PURPOSE is the defining page may."""
    _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
        "https://venue.example/events": PAGE_HTML})
    written = _install_listings(monkeypatch, published=[_published()])

    for queue in (QUEUE_REFRESH, QUEUE_DISCOVER):
        src = _source()
        src["queue"] = queue
        report = run_loop(ai=FakeAIProvider(), sources=[src], budget=TickBudget())
        assert written == [], f"{queue} reached the listing writer"
        assert report.counts["listings_updated"] == 0


def test_a_walled_event_recheck_changes_nothing(monkeypatch, tmp_path):
    """Founder: "Unconfirmed = no mutation." A 403 on the defining page is a
    closed door, not a cancelled show."""
    _install(monkeypatch, tmp_path,
             pages={"https://venue.example/": HOME_HTML},
             errors={"https://venue.example/events":
                     _HttpError(403, "https://venue.example/events")})
    written = _install_listings(monkeypatch, published=[_published()])

    report = run_loop(ai=FakeAIProvider(), sources=[_event_source()],
                      budget=TickBudget())

    assert report.results[0].verdict == UNVERIFIED
    assert written == []


def test_a_dead_defining_page_marks_gone_even_though_the_fallback_answered(
        monkeypatch, tmp_path):
    """The founder's 404 overrule, through the loop, WITH the property the
    evaluator forced on PR #213 still holding: the best door 404s, the loop
    falls back to the registered start URL and reads it fine — and the verdict
    is still about the page that vanished, so the row is marked from the 404
    and NOT from the healthy homepage's parse."""
    _install(monkeypatch, tmp_path,
             pages={"https://venue.example/": HOME_HTML},
             errors={"https://venue.example/events":
                     _HttpError(404, "https://venue.example/events")})
    written = _install_listings(monkeypatch, published=[_published()])

    report = run_loop(ai=FakeAIProvider(), sources=[_event_source()],
                      budget=TickBudget())

    assert report.results[0].verdict == VERIFIED_ABSENT
    assert [d.action for d in written] == ["mark_gone"]
    assert written[0].fields == {"status": "cancelled"}
    assert report.counts["listings_marked_gone"] == 1


def test_a_failure_in_the_writer_costs_one_source_not_the_tick(
        monkeypatch, tmp_path):
    """Per-source isolation, same as the read pass. A listing-update failure
    leaves the last good rows standing and the tick goes on."""
    _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
        "https://venue.example/events": PAGE_HTML,
        "https://other.example/": HOME_HTML,
        "https://other.example/events": PAGE_HTML})
    _install_listings(monkeypatch, published=[_published()])
    monkeypatch.setattr(orchestrator, "load_published_on_page",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down")))

    report = run_loop(ai=FakeAIProvider(),
                      sources=[_event_source(), _source(name="other",
                                                        url="https://other.example/")],
                      budget=TickBudget())

    assert len(report.results) == 2
    assert report.counts["errors"] == 0
    assert report.counts["listings_updated"] == 0


def test_the_founders_listing_table_from_fixtures(monkeypatch, tmp_path, capsys):
    """`event | check result | mutated? | why` — the ticket's artifact, over one
    fixture wave carrying every outcome class the founder enumerated."""
    from worker.listing_update import render_decision_table

    rows = []

    # 1. confirmed change on the defining page.
    _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
        "https://venue.example/events": PAGE_HTML})
    _install_listings(monkeypatch, published=[_published()])
    r = run_loop(ai=FakeAIProvider(), sources=[_event_source()],
                 budget=TickBudget()).results[0]
    rows.append(("Nightjar (time moved)", r.verdict, r.listing_decisions[0]))

    # 2. the gate declined the matched listing's evidence.
    _install_listings(monkeypatch, published=[_published(event_id="e2")],
                      gate_pass=False)
    r = run_loop(ai=FakeAIProvider(), sources=[_event_source()],
                 budget=TickBudget()).results[0]
    rows.append(("Nightjar (gate declined)", r.verdict, r.listing_decisions[0]))

    # 3. rate-limited: unconfirmed.
    _install(monkeypatch, tmp_path,
             pages={"https://venue.example/": HOME_HTML},
             errors={"https://venue.example/events":
                     _HttpError(429, "https://venue.example/events")})
    _install_listings(monkeypatch, published=[_published(event_id="e3")])
    r = run_loop(ai=FakeAIProvider(), sources=[_event_source()],
                 budget=TickBudget()).results[0]
    rows.append(("Nightjar (429)", r.verdict, r.listing_decisions[0]))

    # 4. clean 404 of the defining URL: confirmed gone.
    _install(monkeypatch, tmp_path,
             pages={"https://venue.example/": HOME_HTML},
             errors={"https://venue.example/events":
                     _HttpError(404, "https://venue.example/events")})
    _install_listings(monkeypatch, published=[_published(event_id="e4")])
    r = run_loop(ai=FakeAIProvider(), sources=[_event_source()],
                 budget=TickBudget()).results[0]
    rows.append(("Nightjar (page 404)", r.verdict, r.listing_decisions[0]))

    table = render_decision_table(rows)
    print(table)
    assert [c.strip() for c in table.splitlines()[0].split("|")] == [
        "event", "check result", "mutated?", "why"]
    body = table.splitlines()[2:]
    assert [line.split("|")[2].strip() for line in body] == ["yes", "no", "no", "yes"]
