"""The armed loop's class B multi-page follow (worker/orchestrator.py).

Fully hermetic: fetch_url, extract_candidates and the candidate-store calls are
faked in the orchestrator's namespace, so nothing here touches the network, a
model, or a database. The replay log is redirected to tmp_path.

What these tests pin, in the order the Coverage Law rules matter:

  1. A class B source's OWN advertised event pages are followed, and each one
     runs the SAME sensor -> extract -> gate3 path as the start page — a
     followed page earns no trust shortcut.
  2. The class letter is the CATALOG'S verdict (source['config']), so a row
     with no declared public-read posture is fetched exactly as before and
     followed not at all — fail-closed, and the start page is never gated on
     the letter (that would shrink the catalog).
  3. A WALL ends the source: the exact set of URLs requested proves the pages
     after the wall were never fetched. We knock once.
  4. A 404 is a miss, not a wall — the walk continues.
  5. Both ceilings bind, and a malformed ceiling aborts the run BEFORE the
     first fetch.
  6. The loop still never promotes.
"""
import pytest

from worker.ai_extract import ExtractionOutcome
import worker.orchestrator as orchestrator
from worker.orchestrator import run_loop

# A catalog entry whose DECLARED posture is class B (public HTML, no login).
def _no_fingerprint(source_id, url, cur=None):  # noqa: ARG001
    """No crawl history: every page is "changed", so these tests keep pinning
    the extract/gate path rather than the fair-crawl skip. Hermetic — the real
    lookup would need a DB."""
    return None


CLASS_B_CONFIG = {"access_method": "public_web", "allowed": ["public_pages"]}
# A structured open feed — class A. Fetched as always, never walked.
CLASS_A_CONFIG = {"access_method": "public_web_or_ics", "allowed": ["official_feed"]}

HOME_HTML = """
<html><body>
  <p>Some venue marketing copy that is long enough to satisfy the input sensor
     and says nothing whatsoever about which bands are playing this week.</p>
  <nav>
    <a href="/events">Events</a>
    <a href="/calendar">Calendar</a>
    <a href="https://ticketing.example.com/venue">Buy tickets</a>
    <a href="/account/login">Sign in</a>
  </nav>
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


class _WallError(Exception):
    """Shaped like requests.HTTPError: the status lives on `.response`."""

    def __init__(self, status, url):
        super().__init__(f"HTTP {status}")
        self.response = type("R", (), {"status_code": status, "url": url})()


@pytest.fixture(autouse=True)
def _hermetic(tmp_path, monkeypatch):
    # Isolate the committed source catalog: these sources declare their own
    # posture inline, and a real catalog entry that happened to share one of
    # their synthetic names would silently change what they prove.
    from worker.sourcing import catalog_posture
    monkeypatch.setattr(catalog_posture, "_INDEX", {})
    monkeypatch.setenv("ONELIVE_REPLAY_LOG_DIR", str(tmp_path / "replay"))
    monkeypatch.delenv("ONELIVE_MAX_FOLLOW_PAGES_PER_RUN", raising=False)
    monkeypatch.delenv("ONELIVE_DOORS_PER_SOURCE", raising=False)
    monkeypatch.setenv("ONELIVE_MAX_RENDERS_PER_RUN", "0")
    yield


def _source(name="venue", config=None, url="https://venue.example/"):
    return {
        "source_id": f"src-{name}",
        "name": name,
        "url": url,
        "source_class": "venue_site",
        "config": CLASS_B_CONFIG if config is None else config,
    }


def _install(monkeypatch, tmp_path, *, pages=None, errors=None, candidates_per_page=1,
             lands_on=None):
    """Serve `pages` (url -> html) through a fake fetch_url; `errors` (url ->
    exception) raises instead. `lands_on` (url -> final url) simulates a 200 OK
    that arrived after redirects, which is the whole point of the final-url
    re-check. Records every URL the loop asked for, in order."""
    pages = dict(pages or {})
    errors = dict(errors or {})
    lands_on = dict(lands_on or {})
    requested = []
    extracted_urls = []

    def fake_fetch_url(*, source_id, url, **kwargs):
        requested.append(url)
        if url in errors:
            raise errors[url]
        if url not in pages:
            raise FileNotFoundError(f"HTTP 404 for {url}")  # no .response: not a wall
        path = tmp_path / f"body-{len(requested)}.bin"
        path.write_bytes(pages[url].encode("utf-8"))
        return {
            "status": "ok", "url": url, "storage_ref": str(path),
            "final_url": lands_on.get(url, url),
            "content_type": "text/html", "content_hash": f"h{len(requested)}",
        }

    def fake_extract_candidates(*, ai, text, source_class, source_name, source_url,
                                sxsw_mode=False, source_id=None):
        extracted_urls.append(source_url)
        return ExtractionOutcome(
            candidate_ids=[f"cand-{len(extracted_urls)}-{i}"
                           for i in range(candidates_per_page)])

    monkeypatch.setattr(orchestrator, "fetch_url", fake_fetch_url)
    monkeypatch.setattr(orchestrator, "load_door_fingerprint", _no_fingerprint)
    monkeypatch.setattr(orchestrator, "extract_candidates", fake_extract_candidates)
    monkeypatch.setattr(orchestrator, "list_candidate_source_classes",
                        lambda candidate_id: ["venue_site"])
    monkeypatch.setattr(orchestrator, "load_candidate_gate_signals",
                        lambda candidate_id, cur=None: (
                            {}, {"start_times": [], "dedupe_ambiguous": False}))
    monkeypatch.setattr(orchestrator, "stamp_gate_verdict",
                        lambda candidate_id, **kw: True)
    return requested, extracted_urls


# --- 1. the click actually happens, through the same pipeline ---------------

def test_class_b_source_follows_the_pages_its_homepage_advertises(monkeypatch, tmp_path):
    """FAIR CRAWL: the click still happens, but it is ONE click.

    The homepage advertises both /events and /calendar. Under the default door
    budget the loop takes the top-ranked one only — two fetches for this source
    this wave, so eleven other sources get theirs. /calendar is not dropped: it
    is what the NEXT wave discovers if /events stops being the best door.
    """
    requested, extracted = _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
        "https://venue.example/events": PAGE_HTML,
        "https://venue.example/calendar": PAGE_HTML,
    }, candidates_per_page=3)

    report = run_loop(ai=FakeAIProvider(), sources=[_source()])

    assert requested == ["https://venue.example/", "https://venue.example/events"], (
        "one source costs at most two fetches a wave")
    # The SAME extract path ran on the followed page, not just the homepage.
    assert extracted == ["https://venue.example/", "https://venue.example/events"]
    assert report.counts["pages_followed"] == 1
    assert report.counts["pages_extracted"] == 1
    # 3 candidates per page x (1 start page + 1 followed) = 6.
    assert report.counts["candidates"] == 6
    assert report.counts["errors"] == 0


def test_the_door_budget_is_the_only_thing_that_widens_the_walk(monkeypatch, tmp_path):
    """The fairness bound is a number, not a special case: raise it and the
    same code walks two doors. This is what keeps the default honest — nothing
    else in the loop knows about "1"."""
    monkeypatch.setenv("ONELIVE_DOORS_PER_SOURCE", "2")
    requested, extracted = _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
        "https://venue.example/events": PAGE_HTML,
        "https://venue.example/calendar": PAGE_HTML,
    })

    report = run_loop(ai=FakeAIProvider(), sources=[_source()])

    assert requested == ["https://venue.example/", "https://venue.example/events",
                         "https://venue.example/calendar"]
    assert report.counts["pages_followed"] == 2


def test_follow_never_leaves_the_origin_or_knocks_on_a_login_page(monkeypatch, tmp_path):
    requested, _ = _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
        "https://venue.example/events": PAGE_HTML,
        "https://venue.example/calendar": PAGE_HTML,
    })
    run_loop(ai=FakeAIProvider(), sources=[_source()])

    assert not any("ticketing.example.com" in u for u in requested), (
        "an off-site link is a different source with its own catalog row")
    assert not any("/account/login" in u for u in requested), (
        "Coverage Law: no login/paywall/bot-protection bypass, ever")


# --- 2. the class letter is the catalog's, and it never gates the fetch -----

@pytest.mark.parametrize("config", [None, {}, CLASS_A_CONFIG], ids=["missing", "empty", "class_a"])
def test_only_class_b_is_walked_and_every_source_is_still_fetched(
        monkeypatch, tmp_path, config):
    source = _source(config=config)
    if config is None:
        source.pop("config")
    requested, extracted = _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
        "https://venue.example/events": PAGE_HTML,
    })

    report = run_loop(ai=FakeAIProvider(), sources=[source])

    assert requested == ["https://venue.example/"], "the walk must not run"
    assert extracted == ["https://venue.example/"], "the start page still extracts"
    assert report.counts["fetched"] == 1, "reading the class letter never costs coverage"
    assert report.counts["pages_followed"] == 0


# --- 3. a wall ends the source ---------------------------------------------

def test_a_wall_on_a_followed_page_stops_the_walk_and_demotes_to_class_d(
        monkeypatch, tmp_path, caplog):
    requested, _ = _install(
        monkeypatch, tmp_path,
        pages={"https://venue.example/": HOME_HTML,
               "https://venue.example/calendar": PAGE_HTML},
        errors={"https://venue.example/events": _WallError(403, "https://venue.example/events")},
    )

    with caplog.at_level("WARNING"):
        report = run_loop(ai=FakeAIProvider(), sources=[_source()])

    assert requested == ["https://venue.example/", "https://venue.example/events"], (
        "we knock once: nothing after the wall may be requested")
    assert report.counts["pages_walled"] == 1
    assert report.counts["pages_followed"] == 0
    assert any(orchestrator.CLASS_D_WALL_MARKER in r.message for r in caplog.records), (
        "the wall must be greppable — the log line IS the claim-queue routing")
    assert "class D" in report.results[0].detail or "claim path" in report.results[0].detail


def test_a_sign_in_redirect_is_a_wall_too(monkeypatch, tmp_path):
    requested, _ = _install(
        monkeypatch, tmp_path,
        pages={"https://venue.example/": HOME_HTML,
               "https://venue.example/calendar": PAGE_HTML},
        errors={"https://venue.example/events":
                _WallError(500, "https://venue.example/accounts/login")},
    )
    report = run_loop(ai=FakeAIProvider(), sources=[_source()])
    assert requested == ["https://venue.example/", "https://venue.example/events"]
    assert report.counts["pages_walled"] == 1


# --- 4. a 404 is a miss, not a wall ----------------------------------------

def test_a_missing_page_is_a_miss_and_the_walk_continues(monkeypatch, tmp_path):
    # /events is absent from the fake server -> 404-shaped error with no
    # .response, exactly what a common-path GUESS produces at a real venue.
    # Two doors, because "the walk continues" is only observable when there is
    # a second door to continue TO; the default of one is pinned above.
    monkeypatch.setenv("ONELIVE_DOORS_PER_SOURCE", "2")
    requested, extracted = _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
        "https://venue.example/calendar": PAGE_HTML,
    })

    report = run_loop(ai=FakeAIProvider(), sources=[_source()])

    assert "https://venue.example/calendar" in requested, (
        "one dead guess must not cost the rest of the venue's calendar")
    assert report.counts["pages_walled"] == 0
    assert report.counts["pages_missed"] >= 1
    assert report.counts["pages_followed"] == 1
    assert "https://venue.example/calendar" in extracted


# --- 5. the ceilings bind, and a bad one aborts before the first fetch ------

def test_per_source_ceiling_bounds_the_walk(monkeypatch, tmp_path):
    monkeypatch.setenv("ONELIVE_DOORS_PER_SOURCE", "1")
    requested, _ = _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
        "https://venue.example/events": PAGE_HTML,
        "https://venue.example/calendar": PAGE_HTML,
    })
    report = run_loop(ai=FakeAIProvider(), sources=[_source()])
    assert report.counts["pages_followed"] == 1
    assert len(requested) == 2


def test_per_run_ceiling_is_shared_across_sources(monkeypatch, tmp_path):
    monkeypatch.setenv("ONELIVE_MAX_FOLLOW_PAGES_PER_RUN", "1")
    _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
        "https://venue.example/events": PAGE_HTML,
        "https://venue.example/calendar": PAGE_HTML,
        "https://other.example/": HOME_HTML,
        "https://other.example/events": PAGE_HTML,
    })
    report = run_loop(ai=FakeAIProvider(), sources=[
        _source("venue"), _source("other", url="https://other.example/")])
    assert report.counts["pages_followed"] == 1
    assert report.counts["fetched"] == 2, "both start pages still ran"
    assert any("budget spent" in r.detail for r in report.results)


def test_zero_run_ceiling_disables_following_entirely(monkeypatch, tmp_path):
    monkeypatch.setenv("ONELIVE_MAX_FOLLOW_PAGES_PER_RUN", "0")
    requested, _ = _install(monkeypatch, tmp_path, pages={
        "https://venue.example/": HOME_HTML,
        "https://venue.example/events": PAGE_HTML,
    })
    report = run_loop(ai=FakeAIProvider(), sources=[_source()])
    assert requested == ["https://venue.example/"]
    assert report.counts["pages_followed"] == 0


@pytest.mark.parametrize("env", ["ONELIVE_MAX_FOLLOW_PAGES_PER_RUN",
                                 "ONELIVE_DOORS_PER_SOURCE"])
@pytest.mark.parametrize("bad", ["fifteen", "-1", "3.5"])
def test_malformed_ceiling_aborts_before_the_first_fetch(monkeypatch, tmp_path, env, bad):
    monkeypatch.setenv(env, bad)
    requested, _ = _install(monkeypatch, tmp_path,
                            pages={"https://venue.example/": HOME_HTML})
    with pytest.raises(ValueError, match=env):
        run_loop(ai=FakeAIProvider(), sources=[_source()])
    assert requested == [], "a budget that cannot be read must stop the run cold"


# --- 6. the invariant --------------------------------------------------------

def test_following_pages_never_reaches_the_promote_path():
    """The structural guarantee, restated for the walk: more pages must not
    mean a new way to publish. The orchestrator imports no promote path, so
    there is nothing for a followed page to reach."""
    import ast
    import pathlib

    src = pathlib.Path(orchestrator.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any("promote" in name for name in imported)
    called = {
        node.func.attr if isinstance(node.func, ast.Attribute) else
        getattr(node.func, "id", "")
        for node in ast.walk(tree) if isinstance(node, ast.Call)
    }
    assert "promote_candidate" not in called


# --- 7. where we LANDED, not where we aimed (evaluator finding, PR #205 r1) ---

def test_a_followed_page_that_redirects_off_site_is_not_extracted(monkeypatch, tmp_path):
    """Discovery cleared this link as same-site BEFORE the fetch. The site then
    answered 200 from a ticketing host. Extracting that page would attribute a
    third party's listings to this venue."""
    monkeypatch.setenv("ONELIVE_DOORS_PER_SOURCE", "2")
    requested, extracted = _install(
        monkeypatch, tmp_path,
        pages={"https://venue.example/": HOME_HTML,
               "https://venue.example/events": PAGE_HTML,
               "https://venue.example/calendar": PAGE_HTML},
        lands_on={"https://venue.example/events": "https://tickets.example.com/venue"},
    )

    report = run_loop(ai=FakeAIProvider(), sources=[_source()])

    assert "https://venue.example/events" in requested, "the fetch itself is fine"
    assert "https://tickets.example.com/venue" not in extracted
    assert "https://venue.example/events" not in extracted, (
        "the page we landed on is a different source; it must not be ingested "
        "under this one's name")
    # Not a wall, and not fatal: the walk goes on to the venue's other page.
    assert report.counts["pages_walled"] == 0
    assert "https://venue.example/calendar" in extracted
    assert report.counts["pages_followed"] == 1
    assert report.counts["pages_missed"] >= 1


def test_a_followed_page_that_redirects_to_sign_in_walls_the_source(monkeypatch, tmp_path, caplog):
    """A 200 OK from a login page is the same wall as a 401 — one knock."""
    requested, extracted = _install(
        monkeypatch, tmp_path,
        pages={"https://venue.example/": HOME_HTML,
               "https://venue.example/events": PAGE_HTML,
               "https://venue.example/calendar": PAGE_HTML},
        lands_on={"https://venue.example/events": "https://venue.example/accounts/login"},
    )

    with caplog.at_level("WARNING"):
        report = run_loop(ai=FakeAIProvider(), sources=[_source()])

    assert report.counts["pages_walled"] == 1
    assert requested == ["https://venue.example/", "https://venue.example/events"], (
        "nothing after the wall may be requested")
    assert extracted == ["https://venue.example/"], "the sign-in page is never extracted"
    assert any(orchestrator.CLASS_D_WALL_MARKER in r.message for r in caplog.records)


def test_landing_on_the_same_site_still_extracts(monkeypatch, tmp_path):
    """The check must not cost a legitimate redirect: www., a trailing slash,
    or a canonical path on the SAME site is still the venue's own page."""
    _, extracted = _install(
        monkeypatch, tmp_path,
        pages={"https://venue.example/": HOME_HTML,
               "https://venue.example/events": PAGE_HTML},
        lands_on={"https://venue.example/events": "https://www.venue.example/events/upcoming"},
    )
    run_loop(ai=FakeAIProvider(), sources=[_source()])
    assert "https://venue.example/events" in extracted


def test_a_fetch_result_without_a_final_url_falls_back_to_the_requested_url(
        monkeypatch, tmp_path):
    """No regression for a fetch adapter that reports no final url: the URL we
    asked for is the best available answer, and discovery already cleared it."""
    def _no_final_url(*, source_id, url, **kwargs):
        path = tmp_path / f"nf-{abs(hash(url))}.bin"
        body = HOME_HTML if url.endswith("/") else PAGE_HTML
        path.write_bytes(body.encode("utf-8"))
        return {"status": "ok", "url": url, "storage_ref": str(path),
                "content_type": "text/html", "content_hash": "h"}

    _install(monkeypatch, tmp_path, pages={"https://venue.example/": HOME_HTML})
    monkeypatch.setattr(orchestrator, "fetch_url", _no_final_url)

    report = run_loop(ai=FakeAIProvider(), sources=[_source()])
    assert report.counts["pages_followed"] > 0
    assert report.counts["pages_walled"] == 0
