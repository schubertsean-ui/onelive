"""Ticket D — the event-page reader runs inside the desk dry-run.

Ticket C proved the READER (`tests/test_event_page.py`). These tests prove the
GLUE in `tools/desk_ingest.py`: that the reader actually runs on the desks'
walk, that it runs under the founder's page budget spread across the desks,
and that a dry run still writes nothing.

The founder's four cases are the first four sections:

  (a) a permalink whose page states a date and a venue fills BOTH on the row
  (b) a page stating only a clock leaves the night NULL
  (c) a 403 is a hole — queued, one knock — and never a mash
  (d) the dry run writes nothing

The rest guard the two rules that live in the glue rather than in the reader,
because they are about which pages a RUN may spend: same-host only, and at most
`DEFAULT_FOLLOW_PAGES` pages per run, round-robin across the desks.

Hermetic: no network, no database, no clock. Every page is a string in this
file or a committed fixture; every fetcher is injected.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools.desk_ingest import (
    DEFAULT_FOLLOW_PAGES, _normalize, default_doors, follow_pages,
    follow_table, followable, main, round_robin, walk_doors,
)
from worker.locale.desk_read import Happening
from worker.locale.desk_walk import DeskWalk, PageFetch, PageVisit

LIST_URL = "https://desk.test/events/today"
OTHER_DESK = "https://elsewhere.test/events/today"


def row(listing_url, *, title="Foo at the Hall", when=None, when_text=None,
        place_text=None, source_url=LIST_URL) -> Happening:
    return Happening(
        title=title, when=when, when_text=when_text,
        when_precision=("date" if when and len(when) == 10 else
                        ("datetime" if when else None)),
        place_text=place_text, via="Test Desk", kind="other",
        door_id="test-desk", door_type="local_desk", locale_id="us-tx-capcog",
        source_url=source_url, listing_url=listing_url)


def walk_of(rows, *, door_id="test-desk", start_url=LIST_URL,
            pages=None) -> DeskWalk:
    return DeskWalk(door_id=door_id, door_type="local_desk", via="Test Desk",
                    start_url=start_url,
                    pages=list(pages or [PageVisit(n=1, url=start_url, status=200)]),
                    rows=list(rows), stopped_because="no_next_link")


def fetcher(pages, *, walls=()):
    """fetch(url) -> PageFetch over a dict of pages; anything else is a 404."""
    def fetch(url: str) -> PageFetch:
        if url in walls:
            return PageFetch(url=url, status=403, final_url=url, error="HTTP 403")
        body = pages.get(url)
        if body is None:
            return PageFetch(url=url, status=404, final_url=url, error="HTTP 404")
        return PageFetch(url=url, status=200, body=body, final_url=url)
    return fetch


DATE_AND_VENUE = """
<html><body><article>
  <h1>Foo at the Hall</h1>
  <time datetime="2026-09-11T20:00:00-05:00">Fri Sep 11, 8pm</time>
  <p class="venue">The Shape Hall</p>
</article></body></html>
"""

CLOCK_ONLY = """
<html><body><article>
  <h1>Foo at the Hall</h1>
  <p>Doors <time datetime="20:00">8pm</time></p>
  <p class="venue">The Shape Hall</p>
</article></body></html>
"""


# --------------------------------------------------------------------------
# (a) a permalink with a date AND a venue on the page fills both
# --------------------------------------------------------------------------

def test_a_permalink_stating_a_date_and_a_venue_fills_both_on_the_row():
    """The whole point of the ticket: the row a friend would see gets a night
    and a place it did not have, taken from its OWN page."""
    permalink = "https://desk.test/event/foo-1"
    walks = [walk_of([row(permalink)])]
    fetchers = {"test-desk": fetcher({permalink: DATE_AND_VENUE})}

    filled, runs = follow_pages(walks, fetchers, cap=DEFAULT_FOLLOW_PAGES)

    got = filled[0].rows[0]
    assert got.when == "2026-09-11T20:00:00-05:00"
    assert got.place_text == "The Shape Hall"
    assert runs["test-desk"].followed_n == 1
    assert runs["test-desk"].filled_when_n == 1
    assert runs["test-desk"].filled_place_n == 1

    table = follow_table(filled, runs, cap=DEFAULT_FOLLOW_PAGES)
    assert "| `test-desk` | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 0 |" in table


def test_the_row_the_walk_gave_us_is_the_row_we_give_back():
    """Following fills holes; it never adds, drops or reorders a happening.
    A table whose `rows_n` moved when we followed would be measuring us."""
    urls = [f"https://desk.test/event/foo-{i}" for i in range(4)]
    walks = [walk_of([row(u, title=f"Row {i}") for i, u in enumerate(urls)])]
    fetchers = {"test-desk": fetcher({urls[1]: DATE_AND_VENUE})}

    filled, _runs = follow_pages(walks, fetchers, cap=DEFAULT_FOLLOW_PAGES)

    assert [r.title for r in filled[0].rows] == ["Row 0", "Row 1", "Row 2", "Row 3"]
    assert filled[0].rows[1].place_text == "The Shape Hall"
    assert [r.place_text for r in filled[0].rows if r.title != "Row 1"] == [None] * 3


# --------------------------------------------------------------------------
# (b) a clock with no date leaves the night NULL
# --------------------------------------------------------------------------

def test_a_page_stating_only_a_clock_leaves_the_night_null():
    """"Doors 8pm" is a time, not a night. Publishing a night for it would be
    an invented date on a public row (ONE-LIVE-TRUST: null is correct)."""
    permalink = "https://desk.test/event/foo-2"
    walks = [walk_of([row(permalink)])]
    fetchers = {"test-desk": fetcher({permalink: CLOCK_ONLY})}

    filled, runs = follow_pages(walks, fetchers, cap=DEFAULT_FOLLOW_PAGES)

    got = filled[0].rows[0]
    assert got.when is None, "a clock with no date must not become a night"
    assert got.when_precision is None
    assert got.place_text == "The Shape Hall", "the place is still the page's own"
    assert runs["test-desk"].filled_when_n == 0

    table = follow_table(filled, runs, cap=DEFAULT_FOLLOW_PAGES)
    assert "| `test-desk` | 1 | 0 | 1 | 1 | 0 | 0 | 1 | 0 |" in table, (
        "an undated row is still_null, and the page was read — not a hole we made")


# --------------------------------------------------------------------------
# (c) a 403 is a hole, not a mash
# --------------------------------------------------------------------------

def test_a_wall_is_a_hole_and_never_a_mash():
    """A walled page's listing is UNKNOWN. The row keeps its own address and
    its holes; it never falls back to the LIST's url (§2 Forbidden), and the
    wall is counted where a reader can see it."""
    permalink = "https://desk.test/event/foo-3"
    walks = [walk_of([row(permalink)])]
    fetchers = {"test-desk": fetcher({}, walls={permalink})}

    filled, runs = follow_pages(walks, fetchers, cap=DEFAULT_FOLLOW_PAGES)

    got = filled[0].rows[0]
    assert got.listing_url == permalink, "a wall must not re-address the row"
    assert got.when is None and got.place_text is None
    run = runs["test-desk"]
    assert run.walled_n == 1
    assert run.followed_n == 0
    assert run.visits[0].queued, "a wall is queued for the human claim path"
    assert filled[0].mash_n == 0

    table = follow_table(filled, runs, cap=DEFAULT_FOLLOW_PAGES)
    assert "| `test-desk` | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 |" in table, (
        "the wall lands in 403_n, mash_n stays 0, and not_asked stays 0 — we asked")


def test_a_walled_page_is_knocked_on_exactly_once():
    knocks = []
    permalink = "https://desk.test/event/foo-4"

    def fetch(url):
        knocks.append(url)
        return PageFetch(url=url, status=403, final_url=url, error="HTTP 403")

    walks = [walk_of([row(permalink), row(permalink, title="same page, second row")])]
    follow_pages(walks, {"test-desk": fetch}, cap=DEFAULT_FOLLOW_PAGES)

    assert knocks == [permalink], "one knock per page, never retried"


def test_a_row_addressed_to_the_list_itself_is_never_followed():
    """A mash address is the LIST. Knocking on it would read a list page as an
    event page and staple its date onto a blob."""
    walks = [walk_of([row(LIST_URL)])]
    assert followable(walks[0]) == []

    knocks = []

    def fetch(url):
        knocks.append(url)
        return PageFetch(url=url, status=200, body=DATE_AND_VENUE, final_url=url)

    filled, runs = follow_pages(walks, {"test-desk": fetch}, cap=DEFAULT_FOLLOW_PAGES)
    assert knocks == []
    assert filled[0].rows[0].when is None
    assert runs["test-desk"].followed_n == 0


# --------------------------------------------------------------------------
# (d) the dry run writes nothing
# --------------------------------------------------------------------------

def _poison_the_write_seams(monkeypatch):
    """Every module the write path imports is replaced by one that refuses.

    Poisoning the MODULES rather than patching functions on the real ones is
    what makes this test hermetic AND strict: the write path imports its seams
    lazily (`from worker.candidate_store import ...` inside the branch), so the
    import itself trips the refusal, and the test needs no database driver
    installed to prove a dry run never reached for one.
    """
    import types

    class _Refuses(types.ModuleType):
        def __getattr__(self, name):
            raise AssertionError(
                f"a DRY RUN reached the write seam {self.__name__}.{name}")

    for name in ("worker.candidate_store", "worker.promote"):
        monkeypatch.setitem(sys.modules, name, _Refuses(name))


def test_the_fixture_dry_run_writes_nothing(monkeypatch, capsys):
    """The committed-fixture dry run, end to end through `main()`, with a DSN
    in the environment so the proof is "it did not write", not "it could not"."""
    _poison_the_write_seams(monkeypatch)
    monkeypatch.setenv("ONELIVE_DB_DSN", "postgresql://invalid.test/does-not-exist")

    code = main(["--dry-run"])

    out = capsys.readouterr().out
    assert code == 0
    assert "Nothing was written" in out
    assert "## 3. The event pages" in out, "the reader ran inside the dry run"


def test_write_without_real_is_refused_before_anything_is_walked(monkeypatch, capsys):
    _poison_the_write_seams(monkeypatch)
    monkeypatch.setenv("ONELIVE_DB_DSN", "postgresql://invalid.test/does-not-exist")
    assert main(["--write"]) == 2
    assert "--write requires --real" in capsys.readouterr().err


def test_write_without_a_dsn_is_refused(monkeypatch, capsys):
    _poison_the_write_seams(monkeypatch)
    monkeypatch.delenv("ONELIVE_DB_DSN", raising=False)
    assert main(["--write", "--real"]) == 2
    assert "ONELIVE_DB_DSN" in capsys.readouterr().err


# --------------------------------------------------------------------------
# The write path walks the same pages (founder, 2026-09-07)
# --------------------------------------------------------------------------
#
# "Dry-run and write must follow the same pages." Until this section existed,
# `--write` skipped following, and the test that stood here GREPPED the source
# for `if args.write:` to pin the skip in place. These tests replace it and are
# deliberately BEHAVIOURAL: they run `main()` and read what the run did, so a
# future refactor that keeps the behaviour stays green and a future edit that
# quietly stops following goes red no matter how it is spelled.
#
# Two seams are substituted, and only two, both of them the seams this design
# already injects:
#
#   * `walk_doors` walks the COMMITTED FIXTURES even under `--real`, because
#     the sandbox has no egress and a test may not depend on a live desk.
#   * `follow_fetchers` returns the committed EVENT-page fixtures for the same
#     reason.
#
# Everything between them — the follow selection, the round-robin, the cap, the
# union, the plan, the hold rules and the write loop — is the real code. The
# database is faked at the module seam (`worker.candidate_store`,
# `worker.promote`), so the write path runs end to end and records what it
# would have written without a database in the room.


def _fixture_seams(monkeypatch) -> list:
    """`--real` walks and follows the committed fixtures, hermetically.

    Returns the list of event-page urls the run actually knocked on, so a test
    can assert on the PAGES A RUN READ rather than only on a counter computed
    elsewhere. The recorder wraps the fixture fetcher and changes nothing about
    what it answers.
    """
    import tools.desk_ingest as tool

    real_walk = tool.walk_doors
    real_fetchers = tool.follow_fetchers
    knocked: list = []

    def walk(locale, door_ids, *, real, **kw):
        return real_walk(locale, door_ids, real=False, **kw)

    def fetchers(door_ids, *, real, **kw):
        built, notes = real_fetchers(door_ids, real=False, **kw)
        recorded = {}
        for door, fetch in built.items():
            def recording(url, _fetch=fetch):
                knocked.append(url)
                return _fetch(url)
            recorded[door] = recording
        return recorded, notes

    monkeypatch.setattr(tool, "walk_doors", walk)
    monkeypatch.setattr(tool, "follow_fetchers", fetchers)
    return knocked


class _FakeCursor:
    """Enough cursor for `snapshot()` and `existing_keys()`: an empty store."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.sql = sql

    def fetchone(self):
        return (0,)

    def fetchall(self):
        return []


class _FakeConnection:
    #: psycopg2 sets this when the server is gone; `one_connection` reads it
    #: before handing the connection out again.
    closed = 0

    def close(self):
        self.closed = 1

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return _FakeCursor()


def _fake_store(monkeypatch):
    """Replace the two write seams with recorders. Returns the record.

    The modules are replaced rather than their functions patched because the
    write path imports them lazily inside the branch — the same reason
    `_poison_the_write_seams` does it that way.
    """
    import types

    written = {"candidates": [], "evidence": [], "promoted": []}

    store = types.ModuleType("worker.candidate_store")
    # ONE connection, handed to every seam (`desk_ingest.one_connection`), so
    # the fake counts its dials: a write that went back to dialling per row
    # shows up here as more than one.
    dialled = []

    def _dial():
        dialled.append(_FakeConnection())
        return dialled[-1]

    store.db = _dial
    written["dialled"] = dialled

    def create_candidate(**kw):
        written["candidates"].append(kw)
        return f"cand-{len(written['candidates'])}"

    def add_evidence(cid, source_class, source_name, source_url, quote):
        written["evidence"].append((cid, source_class, source_name))

    store.create_candidate = create_candidate
    store.add_evidence = add_evidence

    promote = types.ModuleType("worker.promote")

    def promote_candidate(cid):
        # The REAL `promote_candidate` opens a connection of its own
        # (`worker/promote.py` has its own module-level `db`), so this
        # stand-in does too — otherwise a lease that left the publisher
        # dialling per row would look identical to one that did not.
        with promote.db():
            written["promoted"].append(cid)
        return f"event-{len(written['promoted'])}"

    promote.promote_candidate = promote_candidate
    # The publisher opens its own connections too (`worker/promote.py` has its
    # own module-level `db`), so the stand-in must have one or it would prove
    # the lease over a seam the real write path does not have.
    promote.db = _dial

    monkeypatch.setitem(sys.modules, "worker.candidate_store", store)
    monkeypatch.setitem(sys.modules, "worker.promote", promote)
    return written


def _fixture_list_urls() -> set:
    """Every LIST address the committed fixture desks walk — the addresses an
    event-page follow may never knock on."""
    walks, _reg, _tz, _tz_id, _skipped = walk_doors(
        "us-tx-capcog", default_doors("us-tx-capcog"), real=False, max_pages=40,
        timeout=20, min_interval=0.0)
    urls = set()
    for one in walks:
        urls.add(_normalize(one.start_url))
        urls.update(_normalize(p.url) for p in one.pages)
    return urls


def counters(out: str) -> dict:
    """The founder's counter row, read off the run's own printed table."""
    lines = out.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("| publish_n |"):
            names = [c.strip() for c in line.strip("|").split("|")]
            values = [c.strip() for c in lines[i + 2].strip("|").split("|")]
            return dict(zip(names, values))
    raise AssertionError(f"no counter table in this run's output:\n{out}")


def test_a_write_run_follows_event_pages(monkeypatch, capsys):
    """Must-do 1 and 2: the write path calls `follow()`, it is not skipped.

    Asserted on what the run DID — pages read, and rows the event pages filled
    reaching the write seam — rather than on how the branch is written."""
    _fixture_seams(monkeypatch)
    written = _fake_store(monkeypatch)
    monkeypatch.setenv("ONELIVE_DB_DSN", "postgresql://invalid.test/does-not-exist")

    assert main(["--write", "--real"]) == 0
    out = capsys.readouterr().out

    assert "## 3. The event pages" in out
    assert "**0** event page(s) read" not in out, (
        "a --write run read no event page — the skip is back")
    assert "event pages were NOT followed" not in out
    assert written["promoted"], "a write run that published nothing proves nothing here"

    # The rows that reached the write seam carry what the EVENT pages said.
    # `test_the_fixture_write_plans_what_the_fixture_dry_run_plans` is what
    # makes this specific: on these fixtures, following CHANGES the plan.
    starts = [c["extracted"].get("start_time") for c in written["candidates"]]
    assert any(starts), "no candidate carried a night at all"


def test_a_write_run_gets_the_same_cap_and_politeness_as_a_dry_run(monkeypatch, capsys):
    """Must-do 1, the other half: "Same host only. Same cap. Same politeness."

    The equal-plan test above would still pass if a write run followed the same
    pages more cheaply — a smaller cap on a fixture set that fits inside both,
    or a shorter sleep between live fetches, which costs the desks rather than
    us and would never show up in a fixture plan. So the arguments themselves
    are compared, on runs that differ ONLY in `--write`."""
    import tools.desk_ingest as tool

    seen: list = []
    real_walk = tool.walk_doors
    real_fetchers = tool.follow_fetchers
    real_follow = tool.follow_pages

    def walk(locale, door_ids, *, real, **kw):
        return real_walk(locale, door_ids, real=False, **kw)

    def fetchers(door_ids, *, real, timeout, min_interval):
        seen.append({"min_interval": min_interval, "timeout": timeout,
                     "doors": tuple(door_ids)})
        return real_fetchers(door_ids, real=False, timeout=timeout,
                             min_interval=min_interval)

    def follow(walks, built, *, cap, **kw):
        seen[-1]["cap"] = cap
        return real_follow(walks, built, cap=cap, **kw)

    monkeypatch.setattr(tool, "walk_doors", walk)
    monkeypatch.setattr(tool, "follow_fetchers", fetchers)
    monkeypatch.setattr(tool, "follow_pages", follow)
    _fake_store(monkeypatch)
    monkeypatch.setenv("ONELIVE_DB_DSN", "postgresql://invalid.test/does-not-exist")

    assert main(["--real", "--dry-run"]) == 0
    assert main(["--real", "--write"]) == 0
    capsys.readouterr()

    assert len(seen) == 2, "one of the two runs never asked for a fetcher"
    dry, write = seen
    assert write == dry, f"the write run walks on different terms: {dry} vs {write}"
    assert write["cap"] == DEFAULT_FOLLOW_PAGES, "the founder's cap, unchanged"
    assert write["min_interval"] == 2.0, "the CLI's politeness default, unchanged"


def test_the_fixture_write_plans_what_the_fixture_dry_run_plans(monkeypatch, capsys):
    """Must-do 3(b): same publish_n, dry-run and write, on the same fixtures.

    With a third leg that keeps the comparison from being vacuous: the same
    fixtures with `--follow-pages 0` plan a DIFFERENT publish_n, so equality
    above is a statement about following and not about two runs that could
    never have differed. (On these fixtures following LOWERS publish_n by one:
    a page contests a night the list stated, `event_page.apply()` takes the
    night back, and the row holds instead of publishing — following is not a
    machine for publishing more, it is a machine for publishing the truth.)"""
    _fixture_seams(monkeypatch)
    _fake_store(monkeypatch)
    monkeypatch.setenv("ONELIVE_DB_DSN", "postgresql://invalid.test/does-not-exist")

    assert main(["--dry-run"]) == 0
    dry = counters(capsys.readouterr().out)

    assert main(["--write", "--real"]) == 0
    write = counters(capsys.readouterr().out)

    assert main(["--dry-run", "--follow-pages", "0"]) == 0
    unfollowed = counters(capsys.readouterr().out)

    assert write["publish_n"] == dry["publish_n"], (
        f"the write plans {write['publish_n']} publishable row(s) and the dry "
        f"run plans {dry['publish_n']} — they did not walk the same pages")
    assert write["hold_n"] == dry["hold_n"]
    assert write["dated_n"] == dry["dated_n"]
    assert write["placed_n"] == dry["placed_n"]
    assert int(dry["publish_n"]) > 0, "a plan of 0 would make the equality empty"
    assert unfollowed["publish_n"] != dry["publish_n"], (
        f"following changes nothing on these fixtures (publish_n "
        f"{unfollowed['publish_n']} either way), so the equality above cannot "
        f"tell a followed write from a skipped one — this test needs fixtures "
        f"where an event page changes the plan")


def test_the_write_run_mashes_nothing(monkeypatch, capsys):
    """Must-do 3(c): `mash_n` stays 0 on the write path.

    A row whose address is the LIST's own url is ENTITY-SPLIT-LAW §2 Forbidden:
    following it would read a list page as an event page and staple a list's
    date onto a blob. `followable()` refuses it on both paths, and now that the
    write path follows at all, the write path is where it matters."""
    knocked = _fixture_seams(monkeypatch)
    _fake_store(monkeypatch)
    monkeypatch.setenv("ONELIVE_DB_DSN", "postgresql://invalid.test/does-not-exist")

    assert main(["--write", "--real"]) == 0
    write = counters(capsys.readouterr().out)

    assert knocked, "no page was knocked on, so nothing here is under test"
    assert write["mash_n"] == "0"
    assert write["tba_public_n"] == "0"


def test_a_write_run_never_knocks_on_a_list_page(monkeypatch, capsys):
    """The same rule where it can actually fail: a desk row ADDRESSED TO THE
    LIST ITSELF.

    The committed fixtures carry no such row (`mash_n` is 0 above, which is
    what the founder asks the live run to report), so asserting "no list page
    was knocked on" over them could never go red and would prove nothing. This
    test puts one in the walk: the run must REPORT it as a mash and must not
    spend a knock on it, because reading a list page as an event page staples a
    list's date onto a blob (ONE-LIVE-ENTITY-SPLIT-LAW §2 Forbidden)."""
    import tools.desk_ingest as tool
    from dataclasses import replace as dc_replace

    knocked = _fixture_seams(monkeypatch)
    _fake_store(monkeypatch)
    monkeypatch.setenv("ONELIVE_DB_DSN", "postgresql://invalid.test/does-not-exist")

    walk_fixtures = tool.walk_doors

    def with_a_mash(locale, door_ids, **kw):
        walks, reg, tz, tz_id, skipped = walk_fixtures(locale, door_ids, **kw)
        first = walks[0]
        mash = dc_replace(first.rows[0], listing_url=first.start_url)
        return ([dc_replace(first, rows=list(first.rows) + [mash])] + list(walks[1:]),
                reg, tz, tz_id, skipped)

    monkeypatch.setattr(tool, "walk_doors", with_a_mash)

    assert main(["--write", "--real"]) == 0
    write = counters(capsys.readouterr().out)

    assert write["mash_n"] != "0", "the mash row did not reach the run"
    lists = _fixture_list_urls()
    mashed = [url for url in knocked if _normalize(url) in lists]
    assert not mashed, (
        f"a --write run read a desk's own LIST page as an event page: {mashed}")


def test_a_written_row_with_no_night_or_no_place_still_holds(monkeypatch, capsys):
    """Must-do 3(d): #241's filter survives the wire.

    Following fills holes; it does not license publishing one. Every row that
    reached `promote()` carries a title, a night AND a place, and the rows that
    did not are in the store as candidates — written, never published, never
    deleted and never faked."""
    _fixture_seams(monkeypatch)
    written = _fake_store(monkeypatch)
    monkeypatch.setenv("ONELIVE_DB_DSN", "postgresql://invalid.test/does-not-exist")

    assert main(["--write", "--real"]) == 0
    out = capsys.readouterr().out

    by_id = {f"cand-{i}": c for i, c in enumerate(written["candidates"], 1)}
    assert written["promoted"], "nothing was promoted, so nothing is under test"
    for cid in written["promoted"]:
        extracted = by_id[cid]["extracted"]
        assert extracted.get("start_time"), f"{cid} was published with no night"
        assert extracted.get("venue_name"), f"{cid} was published with no place"
        assert extracted.get("title"), f"{cid} was published with no title"

    held = len(written["candidates"]) - len(written["promoted"])
    assert held > 0, (
        "no row was held on this run, so the hold rule is untested here")
    assert "| held |" in out, "the run must report what it held"


def test_a_dated_but_unplaced_row_is_held_by_the_write_path(monkeypatch, capsys):
    """Must-do 3(d) where it can actually fail.

    The committed fixtures happen to carry no row that is dated and unplaced,
    so the sweep above ("everything promoted carries all three") cannot go red
    on the place rule alone. This test puts one in the walk, and a second row
    that is placed and undated, and requires the WRITE path to hold both.

    Neither carries a `listing_url`, so following never touches them: the
    question here is what the write path does with a hole it still has after
    following, which is the question #241 answered."""
    import tools.desk_ingest as tool
    from dataclasses import replace as dc_replace

    _fixture_seams(monkeypatch)
    written = _fake_store(monkeypatch)
    monkeypatch.setenv("ONELIVE_DB_DSN", "postgresql://invalid.test/does-not-exist")

    walk_fixtures = tool.walk_doors

    def with_two_holes(locale, door_ids, **kw):
        walks, reg, tz, tz_id, skipped = walk_fixtures(locale, door_ids, **kw)
        first = walks[0]
        whole = next((r for r in first.rows
                      if r.when and (r.place_text or "").strip()), None)
        assert whole is not None, (
            "no fixture row is both dated and placed, so neither hole can be "
            "made from one")
        unplaced = dc_replace(whole, title="Unplaced Injected Show",
                              place_text=None, listing_url=None)
        undated = dc_replace(whole, title="Undated Injected Show", when=None,
                             when_text=None, when_precision=None,
                             listing_url=None)
        rows = list(first.rows) + [unplaced, undated]
        return ([dc_replace(first, rows=rows)] + list(walks[1:]), reg, tz,
                tz_id, skipped)

    monkeypatch.setattr(tool, "walk_doors", with_two_holes)

    assert main(["--write", "--real"]) == 0
    out = capsys.readouterr().out

    by_id = {f"cand-{i}": c for i, c in enumerate(written["candidates"], 1)}
    injected = {c["extracted"].get("title"): cid for cid, c in by_id.items()
                if c["extracted"].get("title", "").endswith("Injected Show")}
    assert set(injected) == {"Unplaced Injected Show", "Undated Injected Show"}, (
        f"both injected rows must be WRITTEN as candidates, never dropped: "
        f"{sorted(injected)}")
    for title, cid in injected.items():
        assert cid not in written["promoted"], (
            f"{title!r} was PUBLISHED with a hole in it")
    assert "no desk stated a place for this row" in out


# --------------------------------------------------------------------------
# same-host only, and the founder's page budget
# --------------------------------------------------------------------------

def test_an_off_host_permalink_is_never_followed():
    """Same-host only (Must-do 1). Another host's page is not this desk's page,
    and a budget spent on one is a budget not spent on a page we may read."""
    walks = [walk_of([row("https://elsewhere.test/event/foo-9")])]
    assert followable(walks[0]) == []

    knocks = []

    def fetch(url):
        knocks.append(url)
        return PageFetch(url=url, status=200, body=DATE_AND_VENUE, final_url=url)

    filled, runs = follow_pages(walks, {"test-desk": fetch}, cap=DEFAULT_FOLLOW_PAGES)
    assert knocks == []
    assert filled[0].rows[0].when is None


def test_the_budget_is_spread_across_the_desks_not_down_one():
    """The founder's cap is a cap AND a shape: a whole budget spent down one
    venue is the thing it forbids, at 40 and at 200 alike."""
    big = walk_of([row(f"https://a.test/event/{i}", source_url="https://a.test/list")
                   for i in range(30)], door_id="desk-a", start_url="https://a.test/list")
    other = walk_of([row(f"https://b.test/event/{i}", source_url="https://b.test/list")
                     for i in range(30)], door_id="desk-b", start_url="https://b.test/list")

    picked = round_robin([big, other], cap=40)

    assert len(picked["desk-a"]) == 20
    assert len(picked["desk-b"]) == 20
    assert sum(len(v) for v in picked.values()) == 40


def test_a_short_desk_strands_no_budget():
    """A desk with fewer pages than its share stops contributing; the rest of
    the budget keeps circulating rather than going unspent."""
    short = walk_of([row("https://a.test/event/only", source_url="https://a.test/list")],
                    door_id="desk-a", start_url="https://a.test/list")
    long = walk_of([row(f"https://b.test/event/{i}", source_url="https://b.test/list")
                    for i in range(10)], door_id="desk-b", start_url="https://b.test/list")

    picked = round_robin([short, long], cap=6)

    assert len(picked["desk-a"]) == 1
    assert len(picked["desk-b"]) == 5


def test_the_cap_is_on_pages_and_is_never_exceeded():
    urls = [f"https://a.test/event/{i}" for i in range(9)]
    walk = walk_of([row(u, source_url="https://a.test/list") for u in urls],
                   door_id="desk-a", start_url="https://a.test/list")
    knocks = []

    def fetch(url):
        knocks.append(url)
        return PageFetch(url=url, status=200, body=DATE_AND_VENUE, final_url=url)

    filled, runs = follow_pages([walk], {"desk-a": fetch}, cap=3)

    assert len(knocks) == 3
    assert runs["desk-a"].followed_n == 3
    assert sum(1 for r in filled[0].rows if r.when) == 3
    table = follow_table(filled, runs, cap=3)
    assert "| `desk-a` | 9 | 3 | 3 | 6 | 0 | 0 | 3 | 6 |" in table, (
        "the six rows beyond the budget are not_asked — never counted as walls")


def test_two_rows_at_one_address_cost_one_knock_and_both_get_the_answer():
    permalink = "https://desk.test/event/shared"
    knocks = []

    def fetch(url):
        knocks.append(url)
        return PageFetch(url=url, status=200, body=DATE_AND_VENUE, final_url=url)

    walks = [walk_of([row(permalink, title="first"), row(permalink, title="second")])]
    filled, runs = follow_pages(walks, {"test-desk": fetch}, cap=DEFAULT_FOLLOW_PAGES)

    assert knocks == [permalink]
    assert all(r.place_text == "The Shape Hall" for r in filled[0].rows)
    assert runs["test-desk"].followed_n == 1, "one PAGE, however many rows"


def test_a_cap_of_zero_follows_nothing():
    walks = [walk_of([row("https://desk.test/event/foo-0")])]

    def fetch(url):
        raise AssertionError("a cap of 0 must knock on nothing")

    filled, runs = follow_pages(walks, {"test-desk": fetch}, cap=0)
    assert filled[0].rows[0].when is None
    assert runs["test-desk"].followed_n == 0


def test_a_desk_we_cannot_fetch_for_strands_no_budget():
    """A desk with no fetcher must not be handed a share of the cap. It would
    be pages spent from the budget and read by nobody — the opposite of what a
    cap across desks is for."""
    a = walk_of([row(f"https://a.test/event/{i}", source_url="https://a.test/list")
                 for i in range(5)], door_id="desk-a", start_url="https://a.test/list")
    b = walk_of([row(f"https://b.test/event/{i}", source_url="https://b.test/list")
                 for i in range(5)], door_id="desk-b", start_url="https://b.test/list")
    knocks = []

    def fetch(url):
        knocks.append(url)
        return PageFetch(url=url, status=200, body=DATE_AND_VENUE, final_url=url)

    # desk-b has no fetcher at all (in a FIXTURE run: no committed event pages).
    filled, runs = follow_pages([a, b], {"desk-a": fetch}, cap=4)

    assert len(knocks) == 4, "the whole budget went to the desk we can read"
    assert all(u.startswith("https://a.test/") for u in knocks)
    assert runs["desk-b"].followed_n == 0
    assert sum(1 for r in filled[0].rows if r.when) == 4


def test_the_table_does_not_claim_a_spread_that_did_not_happen():
    """Found on the live run: one desk was walled, so all 40 pages went to the
    other — while the prose still said "spread round-robin across 2 desks". The
    sentence now says what the run DID, derived from the visits."""
    walled = walk_of([], door_id="desk-walled", start_url="https://b.test/list")
    open_desk = walk_of([row(f"https://a.test/event/{i}", source_url="https://a.test/list")
                         for i in range(3)], door_id="desk-a",
                        start_url="https://a.test/list")

    def fetch(url):
        return PageFetch(url=url, status=200, body=DATE_AND_VENUE, final_url=url)

    filled, runs = follow_pages([open_desk, walled],
                                {"desk-a": fetch, "desk-walled": fetch}, cap=40)
    one_desk = follow_table(filled, runs, cap=40)
    assert "the ONLY desk whose pages we knocked on this run" in one_desk
    assert "round-robin across" not in one_desk

    both = walk_of([row(f"https://b.test/event/{i}", source_url="https://b.test/list")
                    for i in range(3)], door_id="desk-b", start_url="https://b.test/list")
    filled2, runs2 = follow_pages([open_desk, both],
                                  {"desk-a": fetch, "desk-b": fetch}, cap=40)
    two_desks = follow_table(filled2, runs2, cap=40)
    assert "spent round-robin across 2 desk(s)" in two_desks
    assert "`desk-a` 3, `desk-b` 3 knock(s)" in two_desks


# --------------------------------------------------------------------------
# The evaluator's two findings, PR #238 (openai/attacker-smuggle)
# --------------------------------------------------------------------------

def test_the_note_says_how_much_of_the_plan_came_from_event_pages():
    """Finding 1, REAL, fixed in #238 and now OBSOLETE — the finding was that a
    dry run planned from FILLED rows while `--write` skipped following, so a
    section headed "The write plan" showed an operator writes the write path
    would not produce. The founder's answer (2026-09-07) was the same walk on
    both paths, so the caveat became a lie in the other direction. What the
    line reports now is the SIZE of following's contribution, still derived
    from the visits."""
    from tools.desk_ingest import follow_effect_note

    url = "https://desk.test/event/foo-7"
    walks = [walk_of([row(url)])]
    fetchers = {"test-desk": fetcher({url: DATE_AND_VENUE})}
    _filled, runs = follow_pages(walks, fetchers, cap=DEFAULT_FOLLOW_PAGES)

    note = follow_effect_note(runs)
    assert "1 night(s) and 1 place(s) in this plan came from an event page" in note
    assert "this is the plan it works from" in note
    assert "not what `--real --write` would plan" not in note, (
        "the write follows the same pages now; warning otherwise trains an "
        "operator to distrust a plan that is correct")


def test_a_run_that_changed_no_row_says_the_list_pages_said_it_all():
    """The note must not claim a contribution it did not make: when following
    changed nothing, the plan is what the list pages alone stated, and it is
    still the plan a write run works from."""
    from tools.desk_ingest import follow_effect_note

    url = "https://desk.test/event/foo-8"
    walks = [walk_of([row(url, when="2026-09-11T20:00:00-05:00",
                          place_text="The Shape Hall")])]
    fetchers = {"test-desk": fetcher({url: DATE_AND_VENUE})}
    _filled, runs = follow_pages(walks, fetchers, cap=DEFAULT_FOLLOW_PAGES)

    note = follow_effect_note(runs)
    assert "changed no row" in note
    assert "it plans these same rows" in note


def test_rows_sharing_one_permalink_are_all_counted_as_asked():
    """Finding 2, checked and NOT reproduced: the claim was that when several
    rows share one permalink, one knock answers all of them but the table still
    reports the extras as `not_asked`. It does not — `follow()` appends a visit
    per ROW (the repeats marked `reused`), and `asked` excludes only
    `not_knocked` and `off_host`, neither of which a reused visit carries. One
    knock, four rows answered, `not_asked` 0. Pinned so it stays true."""
    url = "https://desk.test/event/shared-4"
    knocks = []

    def fetch(u):
        knocks.append(u)
        return PageFetch(url=u, status=200, body=DATE_AND_VENUE, final_url=u)

    walks = [walk_of([row(url, title=f"row {i}") for i in range(4)])]
    filled, runs = follow_pages(walks, {"test-desk": fetch}, cap=DEFAULT_FOLLOW_PAGES)

    assert len(knocks) == 1, "one knock per page"
    assert runs["test-desk"].followed_n == 1, "one PAGE read"
    assert sum(1 for r in filled[0].rows if r.when) == 4, "all four rows answered"
    assert "| `test-desk` | 4 | 4 | 4 | 0 | 0 | 0 | 1 | 0 |" in follow_table(
        filled, runs, cap=DEFAULT_FOLLOW_PAGES), "not_asked is 0: every row was asked"


# --------------------------------------------------------------------------
# The evaluator's r2 findings, PR #238 (openai/attacker-smuggle) — both in the
# r1 fix itself
# --------------------------------------------------------------------------

def test_the_spread_counts_knocks_not_rows():
    """Finding B, REAL and fixed: the spread sentence derived its per-desk
    number from `len(visits)`, which counts ROWS. Three rows sharing one
    permalink cost ONE knock and were reported as three "pages", overstating
    how the founder's cap was spent — on a table whose whole job is to say what
    the cap bought."""
    shared = "https://a.test/event/one-page"
    rows_a = [row(shared, title=f"row {i}", source_url="https://a.test/list")
              for i in range(3)]
    a = walk_of(rows_a, door_id="desk-a", start_url="https://a.test/list")
    b = walk_of([row(f"https://b.test/event/{i}", source_url="https://b.test/list")
                 for i in range(2)], door_id="desk-b", start_url="https://b.test/list")
    knocks = []

    def fetch(url):
        knocks.append(url)
        return PageFetch(url=url, status=200, body=DATE_AND_VENUE, final_url=url)

    filled, runs = follow_pages([a, b], {"desk-a": fetch, "desk-b": fetch}, cap=40)

    assert len(knocks) == 3, "one knock for desk-a's shared page, two for desk-b"
    table = follow_table(filled, runs, cap=40)
    assert "`desk-a` 1, `desk-b` 2 knock(s)" in table, (
        "desk-a's three rows cost ONE knock and must be reported as one")
    assert "`desk-a` 3" not in table


def test_a_page_behind_our_wall_stop_is_not_counted_as_a_knock():
    """Same unit, the other direction: a page we declined to knock on after a
    run of walls cost nothing, so it cannot appear as budget spent."""
    from worker.locale.event_page import DEFAULT_WALL_STREAK_LIMIT

    urls = [f"https://a.test/event/{i}" for i in range(6)]
    walk = walk_of([row(u, source_url="https://a.test/list") for u in urls],
                   door_id="desk-a", start_url="https://a.test/list")

    def fetch(url):
        return PageFetch(url=url, status=403, final_url=url, error="HTTP 403")

    filled, runs = follow_pages([walk], {"desk-a": fetch}, cap=40)
    run = runs["desk-a"]

    assert run.walled_n == DEFAULT_WALL_STREAK_LIMIT, "we stop after a run of walls"
    assert run.not_knocked_n == 6 - DEFAULT_WALL_STREAK_LIMIT
    table = follow_table(filled, runs, cap=40)

    # ONE assertion on the WHOLE row. Evaluator, PR #238 r3: this was split
    # across two `assert`s and the first half was a bare f-string — always
    # truthy, so it could not fail, on the very row that separates "walled" from
    # "never asked". A test that cannot fail is worse than no test: it reports
    # confidence it never earned.
    assert "| `desk-a` | 6 | 0 | 0 | 6 | 3 | 0 | 0 | 3 |" in table, (
        f"6 rows, 3 walls MET, 3 pages we declined to knock on afterwards: the "
        f"walls belong in 403_n and OUR stop belongs in not_asked.\n{table}")
    assert "every knock went to `desk-a`" in table
    assert "`desk-a` 3 knock(s)" not in table, (
        "3 knocks were spent, but desk-a is the only desk here, so the "
        "single-desk sentence is the one that prints")


def test_the_heading_and_the_note_never_contradict_each_other(capsys, monkeypatch):
    """Finding A, REAL and fixed: the §4 heading was guarded by "a page was
    followed" while the caveat under it was guarded by "a row changed". A run
    that followed pages and changed nothing printed a heading saying this is
    NOT the write plan directly above a line saying it IS. Both paths follow
    the same pages now, so the heading has no variant left to contradict —
    which is the strongest form of the fix, and this test holds the plain
    heading in place on exactly the run that used to produce the clash."""
    from tools.desk_ingest import changed_rows_n, follow_effect_note

    url = "https://desk.test/event/foo-9"
    # The list already stated everything the page states: pages followed, no
    # row changed — the exact contradiction the evaluator found.
    walks = [walk_of([row(url, when="2026-09-11T20:00:00-05:00",
                          place_text="The Shape Hall")])]
    _filled, runs = follow_pages(walks, {"test-desk": fetcher({url: DATE_AND_VENUE})},
                                 cap=DEFAULT_FOLLOW_PAGES)

    assert runs["test-desk"].followed_n == 1, "a page WAS followed"
    assert changed_rows_n(runs) == 0, "and it changed nothing"
    assert "changed no row" in follow_effect_note(runs)

    # End to end through main() on the case the fix was FOR — pages followed,
    # no row changed. Evaluator, PR #238 r3 (nit, taken): the earlier version
    # ran `--follow-pages 0`, which exercises "followed nothing" and never
    # reaches the contradiction. Only the fetched BYTES are substituted here
    # (the seam the design already injects); every line of reporting code is
    # the real one, reading pages that state neither a date nor a venue.
    import tools.desk_ingest as tool

    blank = "<html><body><article><h1>A listing</h1><p>No date here.</p>"\
            "</article></body></html>"

    def blank_fetchers(door_ids, *, real, timeout, min_interval):
        def fetch(url):
            return PageFetch(url=url, status=200, body=blank, final_url=url)
        return {d: fetch for d in door_ids}, []

    monkeypatch.setattr(tool, "follow_fetchers", blank_fetchers)
    _poison_the_write_seams(monkeypatch)
    assert main(["--dry-run"]) == 0
    out = capsys.readouterr().out

    assert "event page(s) read of a founder cap" in out
    assert "**0** event page(s) read" not in out, "pages WERE followed"
    assert "## 4. The write plan\n" in out, "one heading, no variant"
    assert "DRY-RUN VIEW" not in out
    assert "changed no row, so this plan is what the list pages alone stated" in out


def test_the_heading_is_the_same_when_a_row_did_change(capsys, monkeypatch):
    """The other half of the pair: on the committed fixtures event pages DO
    change rows, and the heading is still the plain one, because a write run
    follows those same pages. The note underneath reports the change."""
    _poison_the_write_seams(monkeypatch)
    assert main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "## 4. The write plan\n" in out
    assert "DRY-RUN VIEW" not in out
    assert "in this plan came from an event page, not from a list page" in out
    assert "this is the plan it works from" in out


# --------------------------------------------------------------------------
# Ticket E — the founder cap is 200
# --------------------------------------------------------------------------
#
# The raise 40 -> 200 is a NUMBER, and a number can drift silently: an editor
# tidying a constant, a merge taking the wrong side, a later ticket "just
# lowering it while debugging". These tests make each of those red.
#
# The tests above already run at `DEFAULT_FOLLOW_PAGES`, so they now bind at
# 200 rather than 40 without being rewritten. These four bind the raise itself.


def test_the_founder_cap_is_two_hundred_pages_per_run():
    """The founder's number, pinned. 40 could not fill 1571 rows; 200 is what
    was authorised, and neither a quiet lowering nor a quiet raising of it is
    this repo's call to make (Ticket E Must-do 1)."""
    assert DEFAULT_FOLLOW_PAGES == 200


def test_the_cli_default_is_the_founder_cap(capsys):
    """`.github/workflows/desk-split-dryrun.yml` passes NO `--follow-pages`, so
    the constant only reaches the live run through this default. A default that
    drifted from the constant would dispatch a 40-page run while every test on
    this page passed."""
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "default 200" in capsys.readouterr().out


def test_the_cap_is_never_exceeded_at_the_founder_budget(monkeypatch, capsys):
    """300 pages on offer, 200 in the budget: exactly 200 knocks, never 201.

    The 100 rows beyond the budget are `not_asked` — pages we chose not to
    spend on, never walls and never empty desks.
    """
    rows_a = [row(f"https://a.test/event/{i}", source_url="https://a.test/list")
              for i in range(150)]
    rows_b = [row(f"https://b.test/event/{i}", source_url="https://b.test/list")
              for i in range(150)]
    a = walk_of(rows_a, door_id="desk-a", start_url="https://a.test/list")
    b = walk_of(rows_b, door_id="desk-b", start_url="https://b.test/list")
    knocks = []

    def fetch(url):
        knocks.append(url)
        return PageFetch(url=url, status=200, body=DATE_AND_VENUE, final_url=url)

    filled, runs = follow_pages([a, b], {"desk-a": fetch, "desk-b": fetch},
                                cap=DEFAULT_FOLLOW_PAGES)

    assert len(knocks) == DEFAULT_FOLLOW_PAGES == 200
    assert len(set(knocks)) == 200, "200 DISTINCT pages — the cap counts knocks"
    followed = sum(r.followed_n for r in runs.values())
    assert followed == 200
    assert sum(1 for w in filled for r in w.rows if r.when) == 200, (
        "exactly the followed rows got a night; the other 100 kept their hole")

    table = follow_table(filled, runs, cap=DEFAULT_FOLLOW_PAGES)
    assert "| `desk-a` | 150 | 100 | 100 | 50 | 0 | 0 | 100 | 50 |" in table
    assert "| `desk-b` | 150 | 100 | 100 | 50 | 0 | 0 | 100 | 50 |" in table
    assert "**200** event page(s) read of a founder cap of **200**" in table


def test_the_round_robin_still_spreads_at_the_founder_budget():
    """The raise must not turn the cap into "200 pages of the first desk".

    Chronicle alone offered 1571 rows on the live run, so at cap 200 a
    walk-order spend would hand the whole budget to it and knock on nothing of
    the second desk — exactly the shape the round-robin exists to forbid.
    """
    big = walk_of([row(f"https://a.test/event/{i}", source_url="https://a.test/list")
                   for i in range(1571)], door_id="desk-a",
                  start_url="https://a.test/list")
    other = walk_of([row(f"https://b.test/event/{i}", source_url="https://b.test/list")
                     for i in range(300)], door_id="desk-b",
                    start_url="https://b.test/list")

    picked = round_robin([big, other], cap=DEFAULT_FOLLOW_PAGES)

    assert len(picked["desk-a"]) == 100
    assert len(picked["desk-b"]) == 100
    assert sum(len(v) for v in picked.values()) == DEFAULT_FOLLOW_PAGES


# --------------------------------------------------------------------------
# (h) the first write must FINISH (founder, 2026-09-07) — proven through
# `main()`, because a lease the write path does not use is not a lease
# --------------------------------------------------------------------------

def test_a_write_run_opens_one_connection_for_the_whole_write(monkeypatch, capsys):
    """The bottleneck the founder measured: `create_candidate`, `add_evidence`
    and `promote_candidate` each dialled a fresh remote connection, three or
    four per row, and run 34079785167 was killed at 30 minutes still writing.

    Behavioural on purpose (the same rule Contract #74 was corrected by): this
    counts what the run DIALLED, so defining `one_connection` and forgetting to
    use it fails here rather than passing a grep.
    """
    _fixture_seams(monkeypatch)
    written = _fake_store(monkeypatch)
    monkeypatch.setenv("ONELIVE_DB_DSN", "postgresql://invalid.test/does-not-exist")

    assert main(["--write", "--real"]) == 0
    assert written["promoted"], "a write that published nothing proves nothing here"
    assert len(written["dialled"]) == 1, (
        f"the write opened {len(written['dialled'])} connections; the whole "
        f"run — before-counts, key scan, every seam call, after-counts — gets "
        f"ONE")
    assert written["dialled"][0].closed, (
        "and it is closed when the write is over, never leaked to whatever "
        "runs next")


def test_a_write_run_writes_its_public_rows_before_its_held_ones(monkeypatch, capsys):
    """Founder, 2026-09-07: "If the job dies, /tonight still has listings."

    The committed fixtures plan both kinds, so the order the seam SAW is the
    order the write used.
    """
    _fixture_seams(monkeypatch)
    written = _fake_store(monkeypatch)
    monkeypatch.setenv("ONELIVE_DB_DSN", "postgresql://invalid.test/does-not-exist")

    assert main(["--write", "--real"]) == 0
    created = [f"cand-{i}" for i in range(1, len(written["candidates"]) + 1)]
    promoted = written["promoted"]
    assert 0 < len(promoted) < len(created), (
        "these fixtures must plan BOTH publishing and held rows, or this test "
        f"proves nothing (created {len(created)}, promoted {len(promoted)})")
    assert promoted == created[:len(promoted)], (
        "the rows that publish are the FIRST rows written, so a run killed by "
        "the job timeout still leaves /tonight with listings; the seam saw "
        f"created={created} promoted={promoted}")
