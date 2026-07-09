"""Tests for worker/resolve_entities.py (exact -> trigram fuzzy -> placeholder).

These guard the three bugs fixed in the PR:
  * fuzzy match must be city-scoped (no cross-city merges),
  * placeholder creation must run on the caller's cursor/transaction (no orphans),
  * the fuzzy query must be able to use the trigram GIN index (DB integration).

Pure-logic tests use `FakeCursor`, an in-memory model of the venue/artist tables
that honours the WHERE clauses the code sends — so if the fuzzy step ever drops
its city filter again, the cross-city test fails. DB integration tests are marked
`@pytest.mark.dbintegration` and skip unless ONELIVE_TEST_DB_DSN is set (they need
a live Postgres with pg_trgm + migration 0005 applied).
"""
import re

import psycopg2
import pytest

from worker.resolve_entities import resolve_venue_id, resolve_artist_ids, FUZZY_THRESHOLD


def _norm(s: str) -> str:
    """Cheap stand-in for trigram similarity: drop 'the', case, punctuation."""
    s = (s or "").lower().strip()
    if s.startswith("the "):
        s = s[4:]
    return re.sub(r"[^a-z0-9]", "", s)


class FakeCursor:
    """In-memory cursor modelling `venue`, `artist`, and `audit_log` well enough
    to exercise the resolution branching without a real database."""

    def __init__(self):
        self.venues = []   # list of dicts: venue_id, name, city
        self.artists = []  # list of dicts: artist_id, name
        self.audit = []    # list of dicts: entity_type, entity_id, payload
        self._result = []

    # psycopg2 cursors expose `.connection`; the code touches it only on rollback.
    class _Conn:
        def rollback(self):
            pass
    connection = _Conn()

    def execute(self, sql, params=()):
        s = " ".join(sql.lower().split())
        self._result = []
        if s.startswith(("savepoint", "release", "rollback", "set ")):
            return
        if "insert into venue" in s:
            vid = "v%d" % (len(self.venues) + 1)
            self.venues.append({"venue_id": vid, "name": params[0], "city": params[1]})
            self._result = [(vid,)]
        elif "insert into artist" in s:
            aid = "a%d" % (len(self.artists) + 1)
            self.artists.append({"artist_id": aid, "name": params[0]})
            self._result = [(aid,)]
        elif "insert into audit_log" in s:
            self.audit.append({"entity_type": params[0], "entity_id": params[1], "payload": params[2]})
        elif "from venue" in s and "similarity" not in s:      # exact venue
            name, city = params
            for v in self.venues:
                city_ok = v["city"] is None or (city and v["city"].lower() == city.lower())
                if v["name"].lower() == name.lower() and city_ok:
                    self._result = [(v["venue_id"],)]
                    break
        elif "from venue" in s and "similarity" in s:          # fuzzy venue
            name = params[0]
            city_scoped = "lower(city)" in s
            city = params[2] if city_scoped else None
            for v in self.venues:
                if _norm(v["name"]) != _norm(name):
                    continue
                city_ok = (not city_scoped) or v["city"] is None or v["city"].lower() == city.lower()
                if city_ok:
                    self._result = [(v["venue_id"], 0.9)]
                    break
        elif "from artist" in s and "similarity" not in s:     # exact artist
            name = params[0]
            for a in self.artists:
                if a["name"].lower() == name.lower():
                    self._result = [(a["artist_id"],)]
                    break
        elif "from artist" in s and "similarity" in s:         # fuzzy artist
            name = params[0]
            for a in self.artists:
                if _norm(a["name"]) == _norm(name):
                    self._result = [(a["artist_id"], 0.9)]
                    break

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return list(self._result)


# --------------------------------------------------------------------------
# Pure-logic tests (no database)
# --------------------------------------------------------------------------

def test_venue_exact_match_returns_existing():
    cur = FakeCursor()
    cur.venues.append({"venue_id": "v1", "name": "Stubb's", "city": "Austin"})
    assert resolve_venue_id(cur, "stubb's", "Austin") == "v1"
    assert len(cur.venues) == 1          # no new row
    assert cur.audit == []               # exact match is not a fuzzy merge


def test_venue_fuzzy_match_within_city():
    cur = FakeCursor()
    cur.venues.append({"venue_id": "v1", "name": "The Mohawk", "city": "Austin"})
    # "Mohawk" is not an exact match but is a trigram variant of "The Mohawk".
    assert resolve_venue_id(cur, "Mohawk", "Austin") == "v1"
    assert len(cur.venues) == 1          # merged, no placeholder created
    assert len(cur.audit) == 1           # fuzzy merge is audited
    entry = cur.audit[0]
    assert entry["entity_type"] == "venue"
    assert entry["entity_id"] == "v1"
    assert "Mohawk" in entry["payload"]  # input name recorded in payload


def test_venue_fuzzy_does_not_merge_across_cities():
    cur = FakeCursor()
    cur.venues.append({"venue_id": "v1", "name": "Empire", "city": "Austin"})
    # Same name, different city — must NOT merge; a new placeholder is created.
    new_id = resolve_venue_id(cur, "Empire", "Dallas")
    assert new_id != "v1"
    assert len(cur.venues) == 2
    assert cur.venues[-1]["city"] == "Dallas"
    assert cur.audit == []               # nothing merged, so nothing audited


def test_venue_placeholder_created_when_no_match():
    cur = FakeCursor()
    new_id = resolve_venue_id(cur, "Brand New Room", "Austin")
    assert len(cur.venues) == 1
    assert cur.venues[0]["venue_id"] == new_id
    assert cur.venues[0]["city"] == "Austin"


def test_venue_blank_name_uses_unknown_placeholder():
    cur = FakeCursor()
    resolve_venue_id(cur, "", "Austin")
    assert cur.venues[0]["name"] == "Unknown Venue"
    assert cur.audit == []               # blank name skips the fuzzy step entirely


def test_artist_exact_then_fuzzy_then_placeholder():
    cur = FakeCursor()
    cur.artists.append({"artist_id": "a1", "name": "Spoon"})
    cur.artists.append({"artist_id": "a2", "name": "The Black Angels"})
    out = resolve_artist_ids(cur, ["Spoon", "Black Angels", "Unknown Opener", "", None])
    assert out == ["a1", "a2", "a3"]     # exact, fuzzy, placeholder; blanks skipped
    assert len(cur.artists) == 3
    # one fuzzy merge audited (Black Angels -> The Black Angels)
    assert [a["entity_id"] for a in cur.audit] == ["a2"]


def test_threshold_constant_is_sane():
    assert 0.0 < FUZZY_THRESHOLD < 1.0


class _UndefinedFunctionError(psycopg2.Error):
    # SQLSTATE 42883 = undefined_function ("operator/function does not exist").
    # Class attribute shadows the C-level descriptor so getattr sees "42883".
    pgcode = "42883"


class _OtherDBError(psycopg2.Error):
    pgcode = "40001"  # serialization_failure — a genuine transient, not schema.


class _SchemaFailCursor(FakeCursor):
    """FakeCursor whose fuzzy SELECT raises a chosen psycopg2 error, to exercise
    the fail-loud vs. soft-fallback branches of _fuzzy_match."""

    def __init__(self, error):
        super().__init__()
        self._error = error

    def execute(self, sql, params=()):
        s = " ".join(sql.lower().split())
        if "similarity" in s and "from" in s:
            raise self._error
        return super().execute(sql, params)


def test_fuzzy_reraises_on_schema_resolution_failure():
    """A 42883 (operator/function does not exist) means the extensions-qualified
    pg_trgm objects are unreachable — resolution must fail loudly, NOT silently
    fall back to a placeholder (the second-review-round bug)."""
    cur = _SchemaFailCursor(_UndefinedFunctionError("operator does not exist: text % text"))
    cur.venues.append({"venue_id": "v1", "name": "The Mohawk", "city": "Austin"})
    with pytest.raises(psycopg2.Error):
        resolve_venue_id(cur, "Mohawk", "Austin")
    assert len(cur.venues) == 1  # no placeholder silently created


def test_fuzzy_soft_falls_back_on_non_schema_error():
    """A non-42883 error is a genuine soft miss (e.g. transient) — degrade to the
    placeholder path rather than aborting."""
    cur = _SchemaFailCursor(_OtherDBError("could not serialize access"))
    cur.venues.append({"venue_id": "v1", "name": "The Mohawk", "city": "Austin"})
    new_id = resolve_venue_id(cur, "Mohawk", "Austin")
    assert new_id != "v1"          # fuzzy skipped, placeholder created instead
    assert len(cur.venues) == 2


# --------------------------------------------------------------------------
# DB integration (needs a live Postgres with pg_trgm + migration 0005)
# --------------------------------------------------------------------------

@pytest.fixture
def _seed_cur(db_conn):
    """Cursor on a savepoint; every change is rolled back after the test."""
    cur = db_conn.cursor()
    cur.execute("SAVEPOINT test_seed")
    yield cur
    cur.execute("ROLLBACK TO SAVEPOINT test_seed")


@pytest.mark.dbintegration
def test_db_exact_match(_seed_cur):
    cur = _seed_cur
    cur.execute("insert into venue(name, city) values ('Stubb''s BBQ','Austin') returning venue_id")
    vid = str(cur.fetchone()[0])
    assert resolve_venue_id(cur, "Stubb's BBQ", "Austin") == vid


@pytest.mark.dbintegration
def test_db_fuzzy_match_within_city(_seed_cur):
    cur = _seed_cur
    cur.execute("insert into venue(name, city) values ('The Mohawk','Austin') returning venue_id")
    vid = str(cur.fetchone()[0])
    assert resolve_venue_id(cur, "Mohawk", "Austin") == vid


@pytest.mark.dbintegration
def test_db_fuzzy_rejects_other_city(_seed_cur):
    cur = _seed_cur
    cur.execute("insert into venue(name, city) values ('Empire Control Room','Austin') returning venue_id")
    austin_id = str(cur.fetchone()[0])
    other = resolve_venue_id(cur, "Empire Control Room", "Dallas")
    assert other != austin_id
    cur.execute("select city from venue where venue_id=%s", (other,))
    assert cur.fetchone()[0] == "Dallas"


@pytest.mark.dbintegration
def test_db_placeholder_created(_seed_cur):
    cur = _seed_cur
    before = _count(cur, "venue")
    vid = resolve_venue_id(cur, "A Totally New Venue XYZ", "Austin")
    assert vid
    assert _count(cur, "venue") == before + 1


@pytest.mark.dbintegration
def test_db_fuzzy_query_uses_trgm_index(_seed_cur):
    """EXPLAIN confirms the `%` operator can use the trigram GIN index (the whole
    point of the rewrite). enable_seqscan is disabled so the planner must show the
    index scan rather than fall back to a seq scan on a small table."""
    cur = _seed_cur
    cur.execute("SET LOCAL pg_trgm.similarity_threshold = %s" % float(FUZZY_THRESHOLD))
    cur.execute("SET LOCAL enable_seqscan = off")
    cur.execute(
        "explain select venue_id, similarity(name, %s) as sim from venue "
        "where name %% %s and (city is null or lower(city)=lower(%s)) "
        "order by sim desc limit 1",
        ("Mohawk", "Mohawk", "Austin"))
    plan = "\n".join(r[0] for r in cur.fetchall()).lower()
    assert "idx_venue_name_trgm" in plan


def _count(cur, table):
    cur.execute("select count(*) from %s" % table)
    return cur.fetchone()[0]
