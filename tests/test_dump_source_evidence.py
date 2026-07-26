"""The evidence dump is the join between the database and the scorecard.

Every test here guards the same failure: an identifier that maps to nothing
contributes to no source, and the scorecard then reports a LIVE feed as
NEVER_TRIED with zero throughput. Nothing raises on its own — the rows simply
vanish — so the miss has to be detected and made loud, or the scorecard becomes
a confident lie about which sources work.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import tools.dump_source_evidence as dump  # noqa: E402

REGISTRY = {"sources": [
    {"id": "ticketmaster_discovery", "name": "Ticketmaster Discovery API",
     "code_id": "ticketmaster_api"},
    {"id": "mohawk", "name": "Mohawk Austin"},
]}


def test_the_provider_string_the_importer_writes_resolves_to_a_registry_id():
    """licensed_event stores 'ticketmaster', the registry id is
    'ticketmaster_discovery'. Nothing joins these but this table."""
    index = dump.build_name_index(REGISTRY)
    unmapped: set = set()
    assert dump.resolve("ticketmaster", index, unmapped) == "ticketmaster_discovery"
    assert not unmapped


def test_the_catalog_human_name_resolves_to_a_registry_id():
    """event_candidate and raw_fetch speak the catalog's human name."""
    index = dump.build_name_index(REGISTRY)
    unmapped: set = set()
    assert dump.resolve("Mohawk Austin", index, unmapped) == "mohawk"
    assert dump.resolve("  MOHAWK   austin ", index, unmapped) == "mohawk"
    assert not unmapped


def test_the_merged_code_id_still_resolves():
    """A source merged onto its catalog row keeps its code-side id reachable —
    otherwise the merge would break the very join it was meant to unify."""
    index = dump.build_name_index(REGISTRY)
    unmapped: set = set()
    assert dump.resolve("ticketmaster_api", index, unmapped) == "ticketmaster_discovery"
    assert not unmapped


def test_an_identifier_that_maps_to_nothing_is_RECORDED_not_dropped():
    """The whole point. A silent drop reads downstream as 'this source is dead'."""
    index = dump.build_name_index(REGISTRY)
    unmapped: set = set()
    assert dump.resolve("Some Venue We Never Catalogued", index, unmapped) is None
    assert "Some Venue We Never Catalogued" in unmapped


def test_a_blank_identifier_is_not_counted_as_an_unmapped_source():
    """A null source_name is missing provenance, not an unknown source; putting
    it in the unmapped list would send someone hunting for a source named ''."""
    index = dump.build_name_index(REGISTRY)
    unmapped: set = set()
    assert dump.resolve(None, index, unmapped) is None
    assert dump.resolve("   ", index, unmapped) is None
    assert not unmapped


def test_an_empty_dsn_REFUSES_rather_than_writing_empty_evidence(monkeypatch):
    """Empty evidence files are indistinguishable from 'no source ever worked'."""
    monkeypatch.delenv("ONELIVE_DB_DSN", raising=False)
    with pytest.raises(SystemExit):
        dump.main([])


class _Cursor:
    """Returns each query's rows in the order read_evidence issues them."""

    def __init__(self, batches):
        self._batches = list(batches)
        self._current: list = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, *args):
        self._current = self._batches.pop(0) if self._batches else []

    def fetchall(self):
        return self._current


class _Conn:
    def __init__(self, batches):
        self._cur = _Cursor(batches)

    def cursor(self):
        return self._cur

    def close(self):
        self.closed = True


def test_the_dump_reports_a_live_source_and_flags_an_unknown_one():
    index = dump.build_name_index(REGISTRY)
    unmapped: set = set()
    conn = _Conn([
        [("ticketmaster", "Mohawk", "Austin"),
         ("a_provider_nobody_registered", "X", "Austin")],   # licensed_event
        [("Mohawk Austin", "Mohawk", "Austin")],             # promoted candidates
        [("Mohawk Austin", None)],                           # raw_fetch
    ])
    rows, attempts = dump.read_evidence(conn, index, unmapped)
    assert [r["source_name"] for r in rows] == ["ticketmaster_discovery", "mohawk"]
    assert attempts == [{"source_name": "mohawk", "ok": True, "at": None}]
    assert unmapped == {"a_provider_nobody_registered"}


def test_an_unmapped_identifier_makes_the_whole_run_EXIT_NON_ZERO(monkeypatch, tmp_path):
    """A partial dump is worse than no dump: it looks like a measurement."""
    monkeypatch.setenv("ONELIVE_DB_DSN", "postgres://stub")
    reg_file = tmp_path / "registry.json"
    reg_file.write_text(json.dumps(REGISTRY), encoding="utf-8")

    monkeypatch.setitem(
        sys.modules, "psycopg2",
        type("m", (), {"connect": staticmethod(lambda dsn: _Conn([
            [("a_provider_nobody_registered", "X", "Austin")], [], []]))})())

    code = dump.main(["--registry", str(reg_file),
                      "--rows-out", str(tmp_path / "rows.json"),
                      "--attempts-out", str(tmp_path / "attempts.json")])
    assert code == 1, "an unmapped identifier must fail the run, not warn"


def test_a_clean_dump_exits_zero(monkeypatch, tmp_path):
    monkeypatch.setenv("ONELIVE_DB_DSN", "postgres://stub")
    reg_file = tmp_path / "registry.json"
    reg_file.write_text(json.dumps(REGISTRY), encoding="utf-8")
    monkeypatch.setitem(
        sys.modules, "psycopg2",
        type("m", (), {"connect": staticmethod(lambda dsn: _Conn([
            [("ticketmaster", "Mohawk", "Austin")], [], []]))})())

    rows_out = tmp_path / "rows.json"
    assert dump.main(["--registry", str(reg_file),
                      "--rows-out", str(rows_out),
                      "--attempts-out", str(tmp_path / "attempts.json")]) == 0
    assert json.loads(rows_out.read_text())[0]["source_name"] == "ticketmaster_discovery"
