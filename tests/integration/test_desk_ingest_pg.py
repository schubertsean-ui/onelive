"""Real-Postgres leg for the DESK WRITE path (OPERATING_RULES: 'Real-database
leg for publish-path changes', founder-ratified 2026-08-05 — decision record
docs/memory/decisions/2026-08-05_founder-path-preflight-and-real-db-leg.md).

WHY THIS EXISTS: `tests/test_desk_publish.py` proves what the walker DECIDES,
with the three DB seams injected — and by construction it cannot see a
server-side type, a constraint, or what `promote_candidate` actually does with
the payload (red class db-type-mismatch-invisible-to-hermetic-tests, the class
that shipped the artist_ids uuid[] refusal through 2,000+ green tests). This
module runs the founder's own path for real: plan -> create_candidate ->
add_evidence -> promote_candidate -> the before/after counts the ticket asks
for, against a real PostgreSQL with the repo's committed migrations applied.

It is also the answer to red class founder-path-unprobed. The founder's path is
"run the tool, refresh /tonight, see more than one listing". The only step of
it this sandbox cannot perform is READING THE DESKS (the egress proxy 403s the
CONNECT), so the rows here are built in-process rather than fetched — but every
step AFTER the walk is the real one, including the SQL the API serves from.

ENV-GATED, loud (red class env-dependent-hermetic-test): runs only when
ONELIVE_TEST_PG_DSN is set (CI's db-integration workflow sets it against a
service container; locally, point it at any disposable database — this suite
DROPS AND RECREATES public objects, so never a real DSN). Without the env it
SKIPs with a visible reason, never a silent pass.
"""
from __future__ import annotations

import os
import pathlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from zoneinfo import ZoneInfo

DSN = os.environ.get("ONELIVE_TEST_PG_DSN")

pytestmark = pytest.mark.skipif(
    not DSN,
    reason="ONELIVE_TEST_PG_DSN not set — the real-Postgres desk-write leg "
    "runs in CI (db-integration.yml); this skip is loud by design, not a pass.",
)

MIGRATIONS = pathlib.Path(__file__).resolve().parents[2] / "supabase" / "migrations"
TZ = ZoneInfo("America/Chicago")

CHRONICLE_DOOR = "austin-chronicle-eventsearch"
DO512_DOOR = "do512-today"


@pytest.fixture(scope="module")
def pg():
    import psycopg2

    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("drop schema if exists public cascade")
        cur.execute("drop schema if exists extensions cascade")
        cur.execute("create schema public")
        cur.execute("grant all on schema public to public")
        for role in ("anon", "authenticated"):
            cur.execute(
                "do $$ begin if not exists (select 1 from pg_roles where "
                f"rolname = '{role}') then create role {role} nologin; end if; "
                "end $$;")
        cur.execute("create schema if not exists extensions")
        cur.execute("select current_database()")
        dbname = cur.fetchone()[0]
        cur.execute(
            f'alter database "{dbname}" set search_path = public, extensions')
        cur.execute("set search_path = public, extensions")
        for path in sorted(MIGRATIONS.glob("*.sql")):
            cur.execute(path.read_text())
    os.environ["ONELIVE_DB_DSN"] = DSN
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def registrations(pg):
    """The two desks, registered in `source` exactly as the committed catalog
    spells them — because the public row's label is a REGISTRY lookup, and a
    test that skipped it would prove the label works while it silently didn't.
    """
    from worker.locale.desk_publish import DeskRegistration

    rows = {
        "Austin Chronicle": ("Austin Chronicle Events",
                             "https://www.austinchronicle.com/events/"),
        "Do512": ("Do512", "https://do512.com/"),
    }
    with pg.cursor() as cur:
        for name, base_url in rows.values():
            cur.execute(
                "insert into source(name, source_type, base_url) values "
                "(%s,'local_media',%s) on conflict do nothing", (name, base_url))
    return {via: DeskRegistration(door_id=via, via=via, source_name=name,
                                  source_class="local_media", base_url=base_url,
                                  catalog_id=via.lower())
            for via, (name, base_url) in rows.items()}


def _happening(title, *, when, place, via, door_id, listing_url=None):
    from worker.locale.desk_read import Happening

    return Happening(
        title=title, when=when.isoformat() if when else None,
        when_text=when.strftime("%a., %b. %d, %I:%M%p") if when else None,
        when_precision="datetime" if when else None, place_text=place, via=via,
        kind="music", door_id=door_id, door_type="local_desk",
        locale_id="us-tx-capcog", source_url=f"https://{door_id}.example/list",
        listing_url=listing_url)


def _walk(door_id, via, rows):
    from worker.locale.desk_walk import DeskWalk, PageVisit

    return DeskWalk(
        door_id=door_id, door_type="local_desk", via=via,
        start_url=f"https://{door_id}.example/list",
        pages=[PageVisit(n=1, url=f"https://{door_id}.example/list", status=200,
                         rows_seen=len(rows), new_rows=len(rows))],
        rows=list(rows), stopped_because="no_next_link")


def _live_union(*walks):
    from worker.locale.desk_union import union

    return union(list(walks), timezone=TZ, timezone_id="America/Chicago",
                 mode="LIVE")


def _run(writes, *, pg):
    """The tool's own write loop against the real seams — nothing injected but
    the store's current keys, which the tool reads the same way.
    """
    import importlib.util

    from worker.candidate_store import add_evidence, create_candidate
    from worker.promote import promote_candidate

    root = pathlib.Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "_desk_ingest_it", root / "tools" / "desk_ingest.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)

    with pg.cursor() as cur:
        seen = tool.existing_keys(cur)
    result = tool.ingest(writes, seen=seen, create=create_candidate,
                         add_evidence=add_evidence, promote=promote_candidate,
                         dispute=tool.dispute_superseded)
    return tool, result


def _tonight_rows(pg, *, city="Austin", hours=168):
    """`GET /tonight`'s own query, run against this database."""
    now = datetime.now(timezone.utc)
    with pg.cursor() as cur:
        cur.execute(
            """
            select e.title, e.source_name, e.confidence, e.start_time
            from event e
            left join venue v on v.venue_id = e.venue_id
            where e.status='scheduled'
              and e.start_time >= %s and e.start_time <= %s
              and (v.city is null or v.city = %s)
            order by e.start_time asc
            """, (now, now + timedelta(hours=hours), city))
        return cur.fetchall()


# --------------------------------------------------------------------------

def test_a_single_desk_row_reaches_tonight_labelled(pg, registrations):
    """The whole ticket in one test: one desk, one row, no corroboration — and
    it must appear on `/tonight` carrying that desk's name.
    """
    from worker.locale.desk_publish import plan
    from tools.desk_ingest import counts_table  # noqa: F401  (import-shape check)

    tag = uuid.uuid4().hex[:8]
    when = datetime.now(timezone.utc) + timedelta(hours=5)
    one = _live_union(_walk(CHRONICLE_DOOR, "Austin Chronicle", [
        _happening(f"Solo Desk Show {tag}", when=when, place=f"Room {tag}",
                   via="Austin Chronicle", door_id=CHRONICLE_DOOR,
                   listing_url=f"https://chronicle.example/e/{tag}")]))
    writes = plan(one, registrations)

    before = _tonight_rows(pg)
    _tool, result = _run(writes, pg=pg)
    after = _tonight_rows(pg)

    assert not result["failed"], result["failed"]
    assert len(result["promoted"]) == 1, result["held"]
    assert len(after) == len(before) + 1

    row = [r for r in after if r[0] == f"Solo Desk Show {tag}"]
    assert row, "the single-desk listing never reached /tonight"
    title, source_name, confidence, start_time = row[0]
    assert source_name == "Austin Chronicle Events", (
        "the public row must carry the desk's registry label")
    assert confidence == "confirmed"
    assert start_time is not None


def test_one_show_on_two_desks_is_one_listing_with_two_evidence_rows(pg, registrations):
    from worker.locale.desk_publish import plan

    tag = uuid.uuid4().hex[:8]
    when = datetime.now(timezone.utc) + timedelta(hours=6)
    place = f"Shared Room {tag}"
    one = _live_union(
        _walk(CHRONICLE_DOOR, "Austin Chronicle", [
            _happening(f"Both Desks {tag}", when=when, place=place,
                       via="Austin Chronicle", door_id=CHRONICLE_DOOR)]),
        _walk(DO512_DOOR, "Do512", [
            _happening(f"Both Desks {tag}", when=when, place=place,
                       via="Do512", door_id=DO512_DOOR)]))
    writes = plan(one, registrations)
    assert len(writes) == 1

    _tool, result = _run(writes, pg=pg)
    assert len(result["promoted"]) == 1, result

    with pg.cursor() as cur:
        cur.execute("select count(*) from event where title=%s", (f"Both Desks {tag}",))
        assert cur.fetchone()[0] == 1, "two desks must not become two listings"
        cur.execute(
            """
            select count(*) from candidate_evidence ce
            join event_candidate c on c.candidate_id = ce.candidate_id
            where c.title = %s
            """, (f"Both Desks {tag}",))
        assert cur.fetchone()[0] == 2, "both desks must be recorded as evidence"


def test_running_twice_does_not_publish_the_same_happening_twice(pg, registrations):
    """The re-run guard, against the real store. A nightly job that doubled the
    catalog every night would be worse than no job.
    """
    from worker.locale.desk_publish import plan

    tag = uuid.uuid4().hex[:8]
    when = datetime.now(timezone.utc) + timedelta(hours=7)
    rows = [_happening(f"Nightly {tag}", when=when, place=f"Venue {tag}",
                       via="Do512", door_id=DO512_DOOR)]
    writes = plan(_live_union(_walk(DO512_DOOR, "Do512", rows)), registrations)

    _tool, first = _run(writes, pg=pg)
    assert len(first["promoted"]) == 1

    # Re-plan from a fresh walk of the same list, exactly as tomorrow's run would.
    writes_again = plan(_live_union(_walk(DO512_DOOR, "Do512", rows)), registrations)
    _tool, second = _run(writes_again, pg=pg)
    assert len(second["skipped"]) == 1, second
    assert not second["promoted"]

    with pg.cursor() as cur:
        cur.execute("select count(*) from event where title=%s", (f"Nightly {tag}",))
        assert cur.fetchone()[0] == 1


def test_a_row_with_no_stated_time_publishes_with_a_null_start(pg, registrations):
    """Date-TBA reaches the catalog rather than being withheld — `web/lib/feed.ts`
    renders a null start honestly and never hides it. The row must NOT appear
    in a /tonight window, because it never claimed to be in one.
    """
    from worker.locale.desk_publish import plan

    tag = uuid.uuid4().hex[:8]
    one = _live_union(_walk(DO512_DOOR, "Do512", [
        _happening(f"No Clock {tag}", when=None, place=f"Somewhere {tag}",
                   via="Do512", door_id=DO512_DOOR,
                   listing_url=f"https://do512.example/e/{tag}")]))
    writes = plan(one, registrations)
    assert writes[0].start_time is None

    _tool, result = _run(writes, pg=pg)
    assert len(result["promoted"]) == 1, result

    with pg.cursor() as cur:
        cur.execute("select start_time, source_name, status from event where title=%s",
                    (f"No Clock {tag}",))
        start_time, source_name, status = cur.fetchone()
    assert start_time is None
    assert source_name == "Do512"
    assert status == "scheduled"
    assert not [r for r in _tonight_rows(pg) if r[0] == f"No Clock {tag}"]


def test_the_before_after_counts_are_the_apis_own_predicates(pg, registrations):
    """The ticket's deliverable is a before/after table. This proves the table's
    numbers are the ones `/events` and `/tonight` serve, not a parallel count.
    """
    import importlib.util

    from worker.locale.desk_publish import plan

    root = pathlib.Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "_desk_ingest_counts", root / "tools" / "desk_ingest.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)

    tag = uuid.uuid4().hex[:8]
    when = datetime.now(timezone.utc) + timedelta(hours=8)
    writes = plan(_live_union(_walk(DO512_DOOR, "Do512", [
        _happening(f"Counted {tag}", when=when, place=f"Counted Room {tag}",
                   via="Do512", door_id=DO512_DOOR)])), registrations)

    with pg.cursor() as cur:
        before = tool.snapshot(cur, city="Austin", hours=168)
    _t, result = _run(writes, pg=pg)
    with pg.cursor() as cur:
        after = tool.snapshot(cur, city="Austin", hours=168)

    assert len(result["promoted"]) == 1
    assert after["events"] == before["events"] + 1
    assert after["tonight_168h"] == before["tonight_168h"] + 1
    # The row is 8 hours out, so the 12-hour window moves too — and the wide
    # window can never be smaller than the narrow one.
    assert after["tonight_168h"] >= after["tonight_12h"]


def test_a_desk_that_corrects_a_time_is_recorded_and_the_row_is_not_duplicated(pg, registrations):
    """The evaluator's blocking finding (PR #229 r1), against real SQL.

    A desk correcting 8pm to 9:30pm on the same night keys IDENTICALLY, so the
    key alone says "already have it" and the published 8pm stays live under
    that desk's name. Here the drift is detected from the stored statement,
    recorded as a new candidate, and — critically — NOT published: a second
    listing beside the first is worse for a reader than the stale field.

    This runs against a real database because the detection turns on a
    `distinct on … order by created_at desc` read of a jsonb path, which no
    fake cursor can prove.
    """
    from worker.locale.desk_publish import plan

    tag = uuid.uuid4().hex[:8]
    first = datetime.now(timezone.utc) + timedelta(hours=4)
    place = f"Correction Room {tag}"
    title = f"Retimed Show {tag}"

    rows = [_happening(title, when=first, place=place, via="Do512", door_id=DO512_DOOR)]
    _t, published = _run(plan(_live_union(_walk(DO512_DOOR, "Do512", rows)), registrations), pg=pg)
    assert len(published["promoted"]) == 1, published

    # The desk re-prints the same night, same place, same title — later clock.
    corrected = [_happening(title, when=first + timedelta(minutes=90), place=place,
                            via="Do512", door_id=DO512_DOOR)]
    writes = plan(_live_union(_walk(DO512_DOOR, "Do512", corrected)), registrations)
    _t, second = _run(writes, pg=pg)

    assert len(second["changed"]) == 1, second
    assert not second["skipped"] and not second["promoted"]
    assert "clocks" in second["changed"][0][1]

    with pg.cursor() as cur:
        cur.execute("select count(*) from event where title=%s", (title,))
        assert cur.fetchone()[0] == 1, (
            "the drift must not publish a second listing for one happening")
        cur.execute(
            "select count(*) from event_candidate where title=%s and status='needs_review'",
            (title,))
        assert cur.fetchone()[0] == 1, "the desk's new word must be on the record"
        cur.execute(
            """
            select extracted->'_desk'->'supersedes'->>'event_id'
            from event_candidate
            where title=%s and extracted->'_desk' ? 'supersedes'
            """, (title,))
        superseded = cur.fetchone()[0]
        cur.execute("select event_id::text from event where title=%s", (title,))
        assert superseded == cur.fetchone()[0], (
            "the drift candidate must name the published row it disagrees with")

    # A THIRD run sees the desk's latest word, not its first: no second alarm.
    _t, third = _run(
        plan(_live_union(_walk(DO512_DOOR, "Do512", corrected)), registrations), pg=pg)
    assert len(third["skipped"]) == 1, third
    assert not third["changed"], (
        "the same correction must not re-alarm on every subsequent run")


def test_a_superseded_row_reads_disputed_on_the_real_feed_query(pg, registrations):
    """Evaluator, PR #229 r2, against a real database: once the desk that
    sourced a listing contradicts it, the published row must stop reading
    `confirmed`. It stays on the feed — `disputed` is shown, never hidden — but
    a reader is no longer told the older detail is settled.
    """
    from worker.locale.desk_publish import plan

    tag = uuid.uuid4().hex[:8]
    when = datetime.now(timezone.utc) + timedelta(hours=5)
    title, place = f"Disputed Show {tag}", f"Disputed Room {tag}"

    rows = [_happening(title, when=when, place=place, via="Do512", door_id=DO512_DOOR)]
    _t, first = _run(plan(_live_union(_walk(DO512_DOOR, "Do512", rows)), registrations), pg=pg)
    assert len(first["promoted"]) == 1

    with pg.cursor() as cur:
        cur.execute("select confidence from event where title=%s", (title,))
        assert cur.fetchone()[0] == "confirmed"

    corrected = [_happening(title, when=when + timedelta(minutes=90), place=place,
                            via="Do512", door_id=DO512_DOOR)]
    _t, second = _run(
        plan(_live_union(_walk(DO512_DOOR, "Do512", corrected)), registrations), pg=pg)
    assert len(second["changed"]) == 1, second
    assert "DISPUTED" in second["changed"][0][1]

    with pg.cursor() as cur:
        cur.execute("select confidence, status from event where title=%s", (title,))
        confidence, status = cur.fetchone()
    assert confidence == "disputed", "the superseded row must not read confirmed"
    assert status == "scheduled", "disputed is shown as disputed, never withdrawn"

    # STILL ON THE FEED. /tonight's own query returns it — the invariant is
    # "shown as disputed", and a flag that quietly removed the row would be a
    # worse defect than the one it fixes.
    assert [r for r in _tonight_rows(pg) if r[0] == title], (
        "a disputed row is shown as disputed, never dropped")


def test_a_claim_locked_row_is_not_disputed_by_a_desk(pg, registrations):
    """A venue's or artist's own claim overrides a third-party desk (CLAUDE.md
    agent org). A newspaper disagreeing with the principal's own listing is not
    evidence against the principal, so its confidence is left alone — and the
    run says so rather than silently doing nothing.
    """
    from worker.locale.desk_publish import plan

    tag = uuid.uuid4().hex[:8]
    when = datetime.now(timezone.utc) + timedelta(hours=6)
    title, place = f"Claimed Show {tag}", f"Claimed Room {tag}"

    rows = [_happening(title, when=when, place=place, via="Do512", door_id=DO512_DOOR)]
    _t, first = _run(plan(_live_union(_walk(DO512_DOOR, "Do512", rows)), registrations), pg=pg)
    assert len(first["promoted"]) == 1

    with pg.cursor() as cur:
        cur.execute("update event set override_lock=true where title=%s", (title,))

    corrected = [_happening(title, when=when + timedelta(minutes=45), place=place,
                            via="Do512", door_id=DO512_DOOR)]
    _t, second = _run(
        plan(_live_union(_walk(DO512_DOOR, "Do512", corrected)), registrations), pg=pg)

    assert len(second["changed"]) == 1, second
    assert "claim-locked" in second["changed"][0][1]
    with pg.cursor() as cur:
        cur.execute("select confidence from event where title=%s", (title,))
        assert cur.fetchone()[0] == "confirmed", (
            "a claim overrides a desk — the desk's disagreement must not "
            "downgrade the principal's own listing")


def test_a_date_only_row_never_reaches_the_public_table(pg, registrations):
    """Evaluator, PR #229 r3, against a real database. A date-only row would
    publish with a NULL clock and render as "Date TBA" — telling a reader we do
    not know a date the desk stated. It is held as a candidate instead: in the
    catalog, auditable, and not on the feed saying something false.
    """
    from worker.locale.desk_publish import plan

    tag = uuid.uuid4().hex[:8]
    title = f"Night Only {tag}"
    rows = [_happening(title, when=None, place=f"Day Room {tag}", via="Do512",
                       door_id=DO512_DOOR)]
    # A date-only Happening: the desk stated the day, not the instant.
    rows[0] = type(rows[0])(**{**rows[0].__dict__, "when": "2026-09-13",
                               "when_precision": "date",
                               "when_text": "Sun., Sept. 13"})
    writes = plan(_live_union(_walk(DO512_DOOR, "Do512", rows)), registrations)
    assert writes[0].hold_reason

    _t, result = _run(writes, pg=pg)
    assert len(result["held"]) == 1, result
    assert not result["promoted"]

    with pg.cursor() as cur:
        cur.execute("select count(*) from event where title=%s", (title,))
        assert cur.fetchone()[0] == 0, "a date-only row must not reach `event`"
        cur.execute(
            "select status, extracted->'_desk'->>'night' from event_candidate "
            "where title=%s", (title,))
        status, night = cur.fetchone()
    assert status == "needs_review", "it is in the catalog, awaiting a display"
    assert night == "2026-09-13", "and the night the desk gave us is kept"


def test_a_contested_clock_publishes_disputed_on_the_real_feed(pg, registrations):
    """Two desks, two times, one show. It publishes — the desks agree it is on —
    and reads `disputed` rather than `confirmed`, so a reader is not told the
    clock is merely unknown when it is contested.
    """
    from worker.locale.desk_publish import plan

    tag = uuid.uuid4().hex[:8]
    title, place = f"Contested {tag}", f"Contested Room {tag}"
    when = datetime.now(timezone.utc) + timedelta(hours=4)
    one = _live_union(
        _walk(CHRONICLE_DOOR, "Austin Chronicle",
              [_happening(title, when=when, place=place, via="Austin Chronicle",
                          door_id=CHRONICLE_DOOR)]),
        _walk(DO512_DOOR, "Do512",
              [_happening(title, when=when + timedelta(minutes=90), place=place,
                          via="Do512", door_id=DO512_DOOR)]))
    writes = plan(one, registrations)
    assert len(writes) == 1 and writes[0].clock_disputed

    _t, result = _run(writes, pg=pg)
    assert len(result["promoted"]) == 1, result
    assert "disputed at publish" in result["promoted"][0][1]

    with pg.cursor() as cur:
        cur.execute("select confidence, start_time, status from event where title=%s",
                    (title,))
        confidence, start_time, status = cur.fetchone()
    assert confidence == "disputed"
    assert start_time is None, "no desk's clock is picked as the winner"
    assert status == "scheduled", "shown as disputed, never withdrawn"


def test_a_contested_clock_is_disputed_by_promote_itself_not_by_a_later_write(pg, registrations):
    """Evaluator, PR #229 r5: "publish as disputed or do not publish" is an
    invariant only the PUBLISHER can hold. Proven by calling `promote_candidate`
    directly, with no ingest tool in the picture at all — if the label came
    from a second write by the walker, this row would read `confirmed`.
    """
    import json as _json

    from worker.promote import promote_candidate

    tag = uuid.uuid4().hex[:8]
    title = f"Publisher Disputes {tag}"
    with pg.cursor() as cur:
        cur.execute(
            """
            insert into event_candidate(
              source_name, source_class, raw_text, extracted, title, start_time,
              venue_name, city, status)
            values (%s,'local_media','raw', %s::jsonb, %s,
                    now() + interval '3 day', %s, 'Austin', 'needs_review')
            returning candidate_id
            """,
            ("Do512",
             # A SECOND, different instant in the payload: exactly the shape
             # `evaluate_gate` reads as irreconcilable start-time claims.
             _json.dumps({"start_time": "2027-01-01T20:00:00+00:00"}),
             title, f"Publisher Room {tag}"))
        cid = str(cur.fetchone()[0])
        cur.execute(
            "insert into candidate_evidence(candidate_id, source_class, source_name)"
            " values (%s,'local_media','Do512')", (cid,))

    event_id = promote_candidate(cid)

    with pg.cursor() as cur:
        cur.execute("select confidence, start_time, status from event where event_id=%s",
                    (event_id,))
        confidence, start_time, status = cur.fetchone()
    assert confidence == "disputed", (
        "the publisher must write the contested label itself — a promote that "
        "returns `confirmed` re-opens the window a later write cannot close")
    assert start_time is None
    assert status == "scheduled"


def test_one_source_cannot_manufacture_a_contested_clock(pg, registrations):
    """Evaluator, PR #229 r6. `extracted` is producer-supplied, so an unchecked
    `start_times` list would let any payload null a REAL scheduled time into
    "Date TBA" and stamp `disputed` on a listing whose sources never disagreed.
    A contested clock means two or more sources said different things, so it
    takes two or more of them to exist — one source cannot contest itself.
    """
    import json as _json

    from worker.promote import promote_candidate

    tag = uuid.uuid4().hex[:8]
    title = f"Single Source {tag}"
    with pg.cursor() as cur:
        cur.execute(
            """
            insert into event_candidate(
              source_name, source_class, raw_text, extracted, title, start_time,
              venue_name, city, status)
            values ('Do512','local_media','raw', %s::jsonb, %s,
                    now() + interval '4 day', %s, 'Austin', 'needs_review')
            returning candidate_id
            """,
            (_json.dumps({"start_times": [
                {"source": "Do512", "at": "2027-01-01T20:00:00+00:00"},
                {"source": "Do512", "at": "2027-01-01T23:00:00+00:00"}]}),
             title, f"Single Room {tag}"))
        cid = str(cur.fetchone()[0])
        # ONE evidence row: one source, however many instants it lists.
        cur.execute(
            "insert into candidate_evidence(candidate_id, source_class, source_name)"
            " values (%s,'local_media','Do512')", (cid,))

    event_id = promote_candidate(cid)

    with pg.cursor() as cur:
        cur.execute("select confidence, start_time from event where event_id=%s",
                    (event_id,))
        confidence, start_time = cur.fetchone()
    assert confidence == "confirmed", (
        "a lone source's payload must not degrade its own listing to disputed")
    assert start_time is not None, (
        "and must not null a real scheduled time into 'Date TBA'")

    # Ignored, but never in silence.
    with pg.cursor() as cur:
        cur.execute(
            "select count(*) from audit_log where entity_id=%s "
            "and action='promote_unsourced_clock_claims'", (cid,))
        assert cur.fetchone()[0] == 1, "the unsourced claim must be recorded"


def test_a_clock_claim_from_a_source_with_no_evidence_row_is_not_counted(pg, registrations):
    """Evaluator, PR #229 r7. Counting the candidate's evidence rows and then
    trusting the whole list was too coarse: a candidate that happens to have
    two rows could carry an instant attributed to nobody. Each claim must name
    a source that has an evidence row HERE, and the conflict must span two
    DISTINCT such sources.
    """
    import json as _json

    from worker.promote import promote_candidate

    tag = uuid.uuid4().hex[:8]
    title = f"Unbound Claim {tag}"
    with pg.cursor() as cur:
        cur.execute(
            """
            insert into event_candidate(
              source_name, source_class, raw_text, extracted, title, start_time,
              venue_name, city, status)
            values ('Do512','local_media','raw', %s::jsonb, %s,
                    now() + interval '5 day', %s, 'Austin', 'needs_review')
            returning candidate_id
            """,
            (_json.dumps({"start_times": [
                {"source": "Do512", "at": "2027-02-02T20:00:00+00:00"},
                # A source nobody recorded: no evidence row names it.
                {"source": "Somebody Who Never Wrote Evidence",
                 "at": "2027-02-02T23:00:00+00:00"}]}),
             title, f"Unbound Room {tag}"))
        cid = str(cur.fetchone()[0])
        # TWO evidence rows, so the r6 count-based guard would have passed —
        # but only ONE of them is named by a claim.
        for name in ("Do512", "Austin Chronicle Events"):
            cur.execute(
                "insert into candidate_evidence(candidate_id, source_class, source_name)"
                " values (%s,'local_media',%s)", (cid, name))

    event_id = promote_candidate(cid)

    with pg.cursor() as cur:
        cur.execute("select confidence, start_time from event where event_id=%s",
                    (event_id,))
        confidence, start_time = cur.fetchone()
    assert confidence == "confirmed", (
        "an instant attributed to a source with no evidence row must not "
        "contest anything")
    assert start_time is not None
    with pg.cursor() as cur:
        cur.execute(
            "select payload->>'bound_to_evidence' from audit_log where entity_id=%s "
            "and action='promote_unsourced_clock_claims'", (cid,))
        bound = cur.fetchone()
    assert bound is not None, "the refusal is recorded, never silent"
    assert "Do512" in bound[0] and "Never Wrote Evidence" not in bound[0]
