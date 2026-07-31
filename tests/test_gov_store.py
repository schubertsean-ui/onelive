"""Unit tests for the venue_truth store + gov import runner. NO DB, NO network:
the DB cursor is a recording stub and the Socrata GET is injected. Proves the
static-SQL upsert binds every column, and the runner's fail-loud discipline
(missing/empty config, all-zero systemic failure) + the happy path.
"""
import json

import pytest

import worker.importers.run_gov_import as runner
from worker.importers.gov_store import UPSERT_SQL, upsert_venue_truth


# ---- a recording cursor/conn stub (no DB) -----------------------------------

class _Cur:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params):
        self.calls.append((sql, params))


class _Conn:
    def __init__(self):
        self.cur = _Cur()
        self.commits = 0

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1


# ---- the static upsert ------------------------------------------------------

def test_upsert_sql_is_static_and_idempotent():
    # A constant statement (no runtime/external data formatted in), ON CONFLICT on
    # the composite key → idempotent, and last_seen_at bumps on update.
    assert "insert into venue_truth" in UPSERT_SQL
    assert "on conflict (source_provider, external_id) do update set" in UPSERT_SQL
    assert "last_seen_at = now()" in UPSERT_SQL
    # first_seen_at is set by the column default on insert and NEVER in the update.
    assert "first_seen_at" not in UPSERT_SQL


def test_upsert_venue_truth_binds_and_commits():
    conn = _Conn()
    rows = [
        {"source_provider": "socrata", "external_id": "L1", "name": "Mohawk",
         "capacity": 400.0, "license_type": "Mixed Beverage", "raw": {"x": 1}},
        {"source_provider": "socrata", "external_id": "L2", "name": "Stubbs"},
    ]
    n = upsert_venue_truth(conn, rows)
    assert n == 2
    assert conn.commits == 1
    assert len(conn.cur.calls) == 2
    # Every call binds the full fixed column list, key first.
    sql, params = conn.cur.calls[0]
    assert sql == UPSERT_SQL
    assert params[0] == "socrata" and params[1] == "L1"


def test_upsert_missing_key_raises_not_silently_drops():
    conn = _Conn()
    with pytest.raises(KeyError):
        upsert_venue_truth(conn, [{"name": "no key"}])


# ---- runner config loading (fail-loud) --------------------------------------

def test_runner_missing_config_fails_loud(tmp_path):
    with pytest.raises(SystemExit) as e:
        runner._load_specs(tmp_path / "nope.json")
    assert e.value.code == 2


def test_runner_empty_config_fails_loud(tmp_path):
    p = tmp_path / "cfg.json"
    p.write_text("[]")
    with pytest.raises(SystemExit) as e:
        runner._load_specs(p)
    assert e.value.code == 2  # no specs → never a silent no-op


def test_runner_invalid_json_fails_loud(tmp_path):
    p = tmp_path / "cfg.json"
    p.write_text("{not json")
    with pytest.raises(SystemExit) as e:
        runner._load_specs(p)
    assert e.value.code == 2


# ---- runner happy path + all-zero systemic fail (injected fetch) ------------

_SPEC = {
    "domain": "data.austintexas.gov", "dataset": "abcd-1234", "provider": "socrata",
    "source_name": "austin_tabc", "field_map": {"name": "trade_name", "external_id": "lic"},
}


def _write_cfg(tmp_path, specs):
    p = tmp_path / "gov.json"
    p.write_text(json.dumps(specs))
    return str(p)


def test_runner_dry_run_happy_path(tmp_path, monkeypatch):
    cfg = _write_cfg(tmp_path, [_SPEC])
    monkeypatch.setattr(
        "worker.importers.run_gov_import.fetch_dataset",
        lambda *a, **k: [{"trade_name": "The Mohawk", "lic": "L1"},
                         {"trade_name": "Stubbs", "lic": "L2"}],
    )
    assert runner.main(["--config", cfg, "--dry-run"]) == 0


def test_runner_all_zero_is_systemic_failure(tmp_path, monkeypatch):
    cfg = _write_cfg(tmp_path, [_SPEC])
    # Rows with nothing to anchor on → normalize drops all → 0 total → exit 3.
    monkeypatch.setattr(
        "worker.importers.run_gov_import.fetch_dataset",
        lambda *a, **k: [{"unrelated": "x"}],
    )
    assert runner.main(["--config", cfg, "--dry-run"]) == 3


def test_runner_one_bad_dataset_tolerated(tmp_path, monkeypatch):
    cfg = _write_cfg(tmp_path, [_SPEC, dict(_SPEC, source_name="bad", dataset="z")])

    def fake_fetch(domain, dataset, **k):
        if dataset == "z":
            raise OSError("404")
        return [{"trade_name": "The Mohawk", "lic": "L1"}]

    monkeypatch.setattr("worker.importers.run_gov_import.fetch_dataset", fake_fetch)
    assert runner.main(["--config", cfg, "--dry-run"]) == 0  # good one still imports
