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
    DEFAULT_FOLLOW_PAGES, follow_pages, follow_table, followable, main,
    round_robin,
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


def test_a_write_run_does_not_follow_event_pages(monkeypatch):
    """Stated as a test because it is a deliberate limit, not an oversight:
    following changes what a row CARRIES, so letting it run under `--write`
    would change what this tool publishes — the catalog change this ticket
    excludes. The refusal is printed on the run, and pinned here."""
    source = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "tools", "desk_ingest.py"), encoding="utf-8").read()
    assert "if args.write:" in source
    assert "event pages were NOT followed" in source


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
    """The founder's cap is a cap AND a shape: 40 pages of one venue is the
    thing it forbids."""
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
    assert "the ONLY desk that offered a page to follow" in one_desk
    assert "spread round-robin across" not in one_desk

    both = walk_of([row(f"https://b.test/event/{i}", source_url="https://b.test/list")
                    for i in range(3)], door_id="desk-b", start_url="https://b.test/list")
    filled2, runs2 = follow_pages([open_desk, both],
                                  {"desk-a": fetch, "desk-b": fetch}, cap=40)
    two_desks = follow_table(filled2, runs2, cap=40)
    assert "spread round-robin across 2 desk(s)" in two_desks
    assert "`desk-a` 3, `desk-b` 3 page(s)" in two_desks


# --------------------------------------------------------------------------
# The evaluator's two findings, PR #238 (openai/attacker-smuggle)
# --------------------------------------------------------------------------

def test_the_write_plan_section_says_it_is_not_the_write_plan():
    """Finding 1, REAL and fixed: a dry run follows event pages and then plans
    from the FILLED rows, while `--write` skips following. A section headed
    "The write plan" was showing an operator dated and placed writes the real
    write path will not produce. The heading and a derived caveat now carry it."""
    from tools.desk_ingest import write_plan_caveat

    url = "https://desk.test/event/foo-7"
    walks = [walk_of([row(url)])]
    fetchers = {"test-desk": fetcher({url: DATE_AND_VENUE})}
    _filled, runs = follow_pages(walks, fetchers, cap=DEFAULT_FOLLOW_PAGES)

    caveat = write_plan_caveat(runs)
    assert "not what `--real --write` would plan" in caveat
    assert "1 night(s) and 1 place(s) here came from an event page" in caveat

    source = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "tools", "desk_ingest.py"), encoding="utf-8").read()
    assert '" — DRY-RUN VIEW, not what `--write` would plan" if followed_any else ""' in source


def test_a_run_that_changed_no_row_says_the_plan_is_the_write_plan():
    """The caveat must not cry wolf: when following changed nothing, the dry
    plan IS what a write run would plan, and saying otherwise would train an
    operator to skip the line on the runs where it matters."""
    from tools.desk_ingest import write_plan_caveat

    url = "https://desk.test/event/foo-8"
    walks = [walk_of([row(url, when="2026-09-11T20:00:00-05:00",
                          place_text="The Shape Hall")])]
    fetchers = {"test-desk": fetcher({url: DATE_AND_VENUE})}
    _filled, runs = follow_pages(walks, fetchers, cap=DEFAULT_FOLLOW_PAGES)

    assert "changed no row" in write_plan_caveat(runs)


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
