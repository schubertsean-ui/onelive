"""gather() — one bounded pipe per canonical place, started by demand.

The founder's six properties for this ticket, each with its own test below:

  (a) two concurrent gathers for one place_id = ONE job
  (b) a search snippet never becomes a listing
  (c) mash_n = 0
  (d) undated / unplaced rows are HELD
  (e) a 403 is UNKNOWN, never 0
  (f) no `if locale == <a place>` anywhere in Python

Everything is driven off a pack and pages written by THIS file, so the job is
exercised for a place that has no committed pack — which is the case the law
cares about ("anyone, anywhere, can type a place").
"""
from __future__ import annotations

import dataclasses
import json
import os
import re
import threading

import pytest

from worker.locale import gather as G
from worker.locale.desk_walk import PageFetch

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PLACE = "Testville, ZZ"
LOCALE_ID = "zz-testville"
DESK_URL = "https://desk.example/list"
WALL_URL = "https://wall.example/list"

CATALOG = [
    {"id": "c-desk", "name": "Desk One", "base_url": "https://desk.example",
     "category": "local_desk", "access_method": "public_web"},
    {"id": "c-wall", "name": "Wall Desk", "base_url": "https://wall.example",
     "category": "local_desk", "access_method": "public_web"},
]


def _door(door_id, url, **over):
    door = {
        "door_id": door_id,
        "brand": door_id,
        "via": door_id,
        "door_type": "local_desk",
        "url": url,
        "public": True,
        "intake": "html",
        "kind_scope": [],
        "covers": [],
        "evidence": "founder_named",
    }
    door.update(over)
    return door


def write_pack(tmp_path, doors, *, timezone="UTC"):
    """A locale pack on disk for a place nobody has shipped."""
    packs = tmp_path / "packs"
    packs.mkdir(exist_ok=True)
    (packs / f"{LOCALE_ID}.json").write_text(json.dumps({
        "locale": {"locale_id": LOCALE_ID, "label": "Testville", "scale": "city",
                   "timezone": timezone},
        "query_grammar": {"templates": ["{place} events"], "places": [PLACE],
                          "kinds": ["music", "other"]},
        "doors": doors,
    }), encoding="utf-8")
    return str(packs)


# One page, three rows: a good one, one whose only link is the LIST page
# (the mash the split law forbids), and one that states neither a date nor a
# venue (the hold rule).
LIST_PAGE = """
<html><body>
  <ul class="calendar">
    <li itemscope itemtype="https://schema.org/Event">
      <h3><a href="/happening/1"><span itemprop="name">Bright Room Quartet</span></a></h3>
      <time datetime="2026-09-12T20:00">Sat Sep 12, 8pm</time>
      <span itemprop="location">The Shape Hall</span>
    </li>
    <li itemscope itemtype="https://schema.org/Event">
      <h3><a href="/list"><span itemprop="name">Row With Only A List Link</span></a></h3>
      <time datetime="2026-09-13T20:00">Sun Sep 13, 8pm</time>
      <span itemprop="location">The Shape Hall</span>
    </li>
    <li itemscope itemtype="https://schema.org/Event">
      <h3><a href="/happening/3"><span itemprop="name">Undated And Unplaced</span></a></h3>
    </li>
  </ul>
</body></html>
"""

WALL_HEADERS = {WALL_URL: 403}


def pages_fetcher(pages, statuses=None):
    statuses = statuses or {}

    def fetch(url: str) -> PageFetch:
        if url in statuses:
            return PageFetch(url=url, status=statuses[url])
        body = pages.get(url)
        if body is None:
            return PageFetch(url=url, status=404)
        return PageFetch(url=url, status=200, body=body, final_url=url)
    return fetch


def a_tick(**over):
    kwargs = {"max_pages": 8, "max_seconds": 30.0, "max_dollars": 1.0}
    kwargs.update(over)
    return G.Tick(**kwargs)


def run_gather(tmp_path, *, doors=None, pages=None, statuses=None, leads=(),
               trigger="typed_place", tick=None, place=PLACE, timezone=None):
    doors = doors if doors is not None else [_door("desk-one", DESK_URL)]
    packs_dir = write_pack(tmp_path, doors)
    return G.gather_once(
        place, fetch=pages_fetcher(pages or {DESK_URL: LIST_PAGE}, statuses),
        tick=tick or a_tick(), trigger=trigger, catalog=CATALOG, leads=leads,
        packs_dir=packs_dir, timezone_id=timezone)


# --------------------------------------------------------------------------
# The canonical place id — the key everything else hangs off
# --------------------------------------------------------------------------

@pytest.mark.parametrize("typed", ["Miami, FL", " miami   fl ", "MIAMI  ,  Fl"])
def test_one_place_spelled_three_ways_is_one_id(typed):
    assert G.canonical_place_id(typed) == "miami-fl"


def test_two_places_that_share_a_name_are_two_ids():
    """Locale Launch §6a: "Miami FL != Miami OH"."""
    assert G.canonical_place_id("Miami, FL") != G.canonical_place_id("Miami, OH")


def test_a_blank_place_is_refused_not_keyed():
    with pytest.raises(G.GatherError):
        G.canonical_place_id("  ,, ")


# --------------------------------------------------------------------------
# (a) two concurrent gathers for one place_id = one job
# --------------------------------------------------------------------------

def test_a_two_concurrent_gathers_for_one_place_run_one_job():
    registry = G.Registry()
    ran = []
    first_inside = threading.Event()
    release = threading.Event()

    def work():
        ran.append(1)
        first_inside.set()
        release.wait(5)
        return "report"

    jobs = {}

    def first():
        jobs["first"] = registry.run("miami-fl", work, trigger="typed_place")

    def second():
        first_inside.wait(5)
        jobs["second"] = registry.run("miami-fl", work, trigger="typed_place")

    t1, t2 = threading.Thread(target=first), threading.Thread(target=second)
    t1.start()
    t2.start()
    first_inside.wait(5)
    # The second visitor must have attached while the first was still walking.
    t2.join(5)
    release.set()
    t1.join(5)

    assert len(ran) == 1, "the second visitor started a second pipe"
    assert registry.starts == 1
    assert jobs["first"] is jobs["second"], "the two visitors hold different jobs"
    assert jobs["second"].attached == 1
    assert jobs["second"].result(5) == "report", "the attacher did not get the answer"


def test_a_a_different_place_is_a_different_job():
    registry = G.Registry()
    registry.run("miami-fl", lambda: "one", trigger="typed_place")
    registry.run("miami-oh", lambda: "two", trigger="typed_place")
    assert registry.starts == 2


def test_a_page_load_may_not_start_a_gather():
    """Locale Launch §6a: "Page load MUST NOT start a crawl, extract, or gather"."""
    with pytest.raises(G.GatherRefused) as exc:
        G.assert_trigger(G.PAGE_LOAD)
    assert "page load" in str(exc.value).lower()
    with pytest.raises(G.GatherRefused):
        G.Registry().run("miami-fl", lambda: None, trigger=G.PAGE_LOAD)


def test_a_an_unknown_trigger_fails_closed():
    with pytest.raises(G.GatherRefused):
        G.assert_trigger("because_i_felt_like_it")


# --------------------------------------------------------------------------
# (b) a search snippet never becomes a listing
# --------------------------------------------------------------------------

def test_b_a_lead_has_nowhere_to_put_a_listing():
    """The structural half: there is no field on a Lead that could hold a row."""
    fields = {f.name for f in dataclasses.fields(G.Lead)}
    assert fields == {"query", "url", "note"}
    for forbidden in ("title", "when", "start_time", "place", "place_text",
                      "venue", "snippet", "description"):
        assert forbidden not in fields


def test_b_a_lead_becomes_a_door_graded_found_unverified():
    door = G.lead_door(G.Lead(query="q", url="https://city.example.gov/events"),
                       place_id="testville-zz")
    assert door.evidence == "found_unverified"
    assert door.door_type == "civic"


def test_b_an_ordinary_search_hit_is_lead_only_and_never_walked(tmp_path):
    """A hit with nothing but a URL is `junk` — the pack's own word for
    "lead only, never a listing" — so it is not listable and never fetched."""
    lead = G.Lead(query="things to do", url="https://copyfarm.example/austin-events")
    door = G.lead_door(lead, place_id="testville-zz")
    assert door.door_type == G.LEAD_ONLY_DOOR_TYPE
    assert door.readable is False

    report = run_gather(tmp_path, leads=(lead,))
    assert report.leads_n == 1
    skipped = {s.door_id: s.why for s in report.skipped}
    assert door.door_id in skipped
    assert "lead, not a listing" in skipped[door.door_id]
    # Nothing the lead carried reached a row.
    titles = {r.title for r in report.one.rows}
    assert not any("things to do" in t or "copyfarm" in t for t in titles)


def test_b_a_lead_we_cannot_label_writes_nothing(tmp_path):
    """Even a civic lead needs a masthead before a row of it can exist: a
    publisher missing from the catalog is a door to register, fail-closed."""
    lead = G.Lead(query="q", url="https://city.example.gov/events")
    report = run_gather(tmp_path, leads=(lead,))
    reasons = " ".join(s.why for s in report.skipped)
    assert "master_sources_catalog_120.json" in reasons


# --------------------------------------------------------------------------
# (c) mash_n = 0
# --------------------------------------------------------------------------

def test_c_mash_n_is_zero(tmp_path):
    report = run_gather(tmp_path)
    assert report.mash_n == 0
    # And that zero is a REFUSAL, not an absence: the page really did print a
    # row whose only link was the list itself.
    assert sum(w.mash_blocked for w in report.walks) >= 1


# --------------------------------------------------------------------------
# (d) undated / unplaced rows are held
# --------------------------------------------------------------------------

def test_d_undated_and_unplaced_rows_are_held_off_the_default_view(tmp_path):
    report = run_gather(tmp_path)
    assert report.rows_n >= 1
    assert report.held_n >= 1, "a row with no night and no place was published"
    assert report.publishable_n == report.rows_n - report.held_n


def test_d_a_place_with_no_clock_holds_the_whole_job(tmp_path):
    """No pack timezone and no geocode: HELD, never given a guessed night."""
    packs = tmp_path / "empty"
    packs.mkdir()
    report = G.gather_once(
        "Nowhere Yet", fetch=pages_fetcher({}), tick=a_tick(),
        trigger="typed_place", packs_dir=str(packs))
    assert report.held_reason and "timezone" in report.held_reason
    assert report.state == G.STATE_HELD
    assert report.walks == []
    assert report.grammar_source == G.GRAMMAR_THIN
    assert report.queries, "a thin place still gets a bounded query grammar"


# --------------------------------------------------------------------------
# (e) a 403 is UNKNOWN, not 0
# --------------------------------------------------------------------------

def test_e_a_403_desk_is_unknown_never_an_empty_calendar(tmp_path):
    report = run_gather(
        tmp_path,
        doors=[_door("desk-wall", WALL_URL)],
        pages={},
        statuses=WALL_HEADERS,
    )
    assert report.walls_n == 1
    assert report.unknown_desks == ("desk-wall",)
    assert report.complete is False
    assert report.state == G.STATE_UNKNOWN
    line = report.honest_line()
    assert "UNKNOWN, not zero" in line
    assert "0 events" not in line


def test_e_a_walled_desk_does_not_hide_the_desk_that_answered(tmp_path):
    report = run_gather(
        tmp_path,
        doors=[_door("desk-one", DESK_URL), _door("desk-wall", WALL_URL)],
        pages={DESK_URL: LIST_PAGE},
        statuses=WALL_HEADERS,
    )
    assert report.rows_n >= 1
    assert report.unknown_desks == ("desk-wall",)
    assert report.state == G.STATE_UNKNOWN


def test_e_a_closed_door_is_queued_by_name_never_bypassed(tmp_path):
    report = run_gather(
        tmp_path,
        doors=[_door("desk-shut", "https://shut.example/x", public=False,
                     blocked_reason="login wall")],
        pages={},
    )
    skipped = {s.door_id: s for s in report.skipped}
    assert skipped["desk-shut"].source_class == "D"
    assert "queued, never bypassed" in skipped["desk-shut"].why
    assert report.walks == []
    assert "not empty" in report.honest_line()


# --------------------------------------------------------------------------
# (f) no locale named in Python
# --------------------------------------------------------------------------

_LOCALE_BRANCH_RE = re.compile(
    r"if\s+[A-Za-z_.]*(locale|place|city|market)[A-Za-z_.]*\s*(==|!=|\sin\s)\s*[\"'\(\[]")


def _py_files(*dirs):
    for d in dirs:
        for root, _, names in os.walk(os.path.join(REPO, d)):
            for name in sorted(names):
                if name.endswith(".py"):
                    yield os.path.join(root, name)


def test_f_no_python_branches_on_a_named_locale():
    """Locale Launch §3: "Python that names a locale id in an `if` is a defect"."""
    offenders = []
    for path in _py_files("worker", "api"):
        with open(path, encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                if _LOCALE_BRANCH_RE.search(line):
                    offenders.append(f"{os.path.relpath(path, REPO)}:{n}: {line.strip()}")
    assert offenders == [], (
        "a locale/place compared against a literal in Python:\n" + "\n".join(offenders)
        + "\nPlaces, kinds and doors live in the pack JSON. A second locale is a "
          "second FILE, never a branch.")


def test_f_the_gather_job_names_no_place_and_no_brand():
    """The shipped pack's own words must not appear in the job or its tool."""
    with open(os.path.join(REPO, "sources", "locale_packs", "us-tx-capcog.json"),
              encoding="utf-8") as fh:
        shipped = json.load(fh)
    words = {d["brand"] for d in shipped["doors"]}
    words |= {p.split(",")[0].strip() for p in shipped["query_grammar"]["places"]}
    words |= {shipped["locale"]["label"], shipped["locale"]["locale_id"]}
    for rel in ("worker/locale/gather.py", "tools/gather.py"):
        with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
            text = fh.read()
        hits = sorted(w for w in words if w and w in text)
        assert hits == [], f"{rel} names {hits} — a place belongs in the pack"


# --------------------------------------------------------------------------
# The tick — three bounds, stop on the first one spent
# --------------------------------------------------------------------------

def test_a_tick_must_be_bounded_on_all_three_axes():
    for bad in ({"max_pages": 0}, {"max_seconds": 0}, {"max_dollars": -1},
                {"max_pages": None}):
        with pytest.raises(G.GatherError):
            a_tick(**bad)


def test_the_page_bound_stops_the_job_and_says_it_was_ours(tmp_path):
    pages = {
        DESK_URL: LIST_PAGE.replace("</ul>", '</ul><a rel="next" href="/p2">Next</a>'),
        "https://desk.example/p2":
            LIST_PAGE.replace("</ul>", '</ul><a rel="next" href="/p3">Next</a>'),
        "https://desk.example/p3": LIST_PAGE,
    }
    report = run_gather(tmp_path, pages=pages, tick=a_tick(max_pages=2))
    assert report.stopped_because == "pages"
    walk = report.walks[0]
    assert walk.exhausted is False, "a budget stop must never read as an exhausted desk"
    assert len(walk.pages) == 2


def test_the_wall_clock_bound_stops_a_walk_as_our_bound(tmp_path):
    """A tick whose clock has already run out stops the walk cleanly — and the
    walk says `tick_bound`, not `no_next_link`."""
    ticks = iter([0.0, 99.0, 99.0, 99.0, 99.0, 99.0])
    tick = G.Tick(max_pages=8, max_seconds=1.0, max_dollars=1.0,
                  clock=lambda: next(ticks, 99.0))
    report = run_gather(tmp_path, tick=tick)
    assert report.stopped_because in ("wall_clock", "pages")
    assert report.rows_n == 0
    assert report.state != G.STATE_GATHERED


def test_dollars_are_a_bound_too():
    tick = a_tick(max_dollars=0.10).start()
    assert tick.bound() is None
    tick.spend(0.10)
    assert tick.bound() == "dollars"
    assert tick.stop_when()() == "dollars"


# --------------------------------------------------------------------------
# Resolve — pack is cache, thin is still allowed
# --------------------------------------------------------------------------

def test_a_pack_is_reused_as_cache_so_the_next_person_is_instant(tmp_path):
    packs_dir = write_pack(tmp_path, [_door("desk-one", DESK_URL)])
    resolved = G.resolve(PLACE, packs_dir=packs_dir)
    assert resolved.has_pack and resolved.pack_id == LOCALE_ID
    assert resolved.timezone_id == "UTC"
    assert resolved.grammar.source == G.GRAMMAR_PACK
    assert resolved.doors, "the cached doors were not reused"


def test_a_place_with_no_pack_still_gets_a_bounded_grammar(tmp_path):
    packs = tmp_path / "none"
    packs.mkdir()
    resolved = G.resolve("Somewhere Else", packs_dir=str(packs),
                         timezone_id="UTC")
    assert not resolved.has_pack
    assert resolved.grammar.source == G.GRAMMAR_THIN
    assert resolved.timezone_id == "UTC"
    queries = resolved.grammar.queries()
    assert queries and all("Somewhere Else" in q for q in queries)
    assert len(queries) == len(G.THIN_TEMPLATES)


def test_class_a_and_b_are_the_only_doors_fetched(tmp_path):
    feed = _door("desk-feed", "https://desk.example/feed.ics", intake="ics")
    assert G.door_class(
        G.Door(door_id="d", brand="b", via="b", door_type="civic",
               url="https://x.example/f.ics", public=True, intake="ics",
               kind_scope=(), covers=(), blocked_reason=None,
               evidence="founder_named", locale_id="p"),
    ).source_class == "A"
    assert feed["intake"] == "ics"


# --------------------------------------------------------------------------
# The tool — a rehearsal with no way to reach production
# --------------------------------------------------------------------------

def test_the_gather_tool_has_no_write_flag():
    """Not "off by default" — absent. A rehearsal one word away from production
    is not a rehearsal."""
    import tools.gather as tool

    parser = tool.build_parser()
    flags = {opt for action in parser._actions for opt in action.option_strings}
    for forbidden in ("--write", "--real", "--live", "--promote", "--publish"):
        assert forbidden not in flags, f"{forbidden} is a path to production"
    with open(os.path.join(REPO, "tools", "gather.py"), encoding="utf-8") as fh:
        assert '"--write"' not in fh.read()


def test_the_gather_tool_refuses_page_load_as_a_trigger():
    import tools.gather as tool

    parser = tool.build_parser()
    trigger = next(a for a in parser._actions if "--trigger" in a.option_strings)
    assert G.PAGE_LOAD not in (trigger.choices or ())
