"""Market registry (worker/sourcing/markets.py) — sourcing model Layer 2.

Covers: the live austin market loads and resolves; every fail-closed refusal
(unknown id, malformed JSON, bad timezone, missing catalog, bad boundary kind,
unresolvable boundary symbols, invalid specials); env selection; and the
mechanical-identity binding (market counties == capcog's set, resolved by
import, never mirrored). Plus the import_sources.py routing contract.
"""
import json
import os

import pytest

from worker.region.capcog import CAPCOG_COUNTIES, row_verdict
from worker.sourcing.markets import (
    DEFAULT_MARKET_ID,
    MARKET_ENV_VAR,
    Market,
    MarketConfigError,
    available_markets,
    get_market,
)


# ---------- the live austin market ----------

def test_austin_loads_and_is_default():
    m = get_market()
    assert m.id == DEFAULT_MARKET_ID == "austin"
    assert m.timezone == "America/Chicago"
    assert m.country == "US"
    assert "en-US" in m.locales


def test_austin_boundary_is_mechanically_identical_to_capcog():
    m = get_market("austin")
    # Resolved by import from the module — the SAME frozenset object's
    # contents, never a hand-mirrored copy that could drift.
    assert m.boundary_counties() == frozenset(CAPCOG_COUNTIES)
    assert len(m.boundary_counties()) == 14  # 10 CAPCOG + Hill Country 4
    assert m.row_verdict() is row_verdict


def test_austin_catalog_resolves_and_loads():
    m = get_market("austin")
    assert os.path.isfile(m.catalog_path())
    catalog = m.load_catalog()
    assert isinstance(catalog, list) and len(catalog) >= 100


def test_austin_specials_declared_with_built_sxsw():
    m = get_market("austin")
    by_id = {s.id: s for s in m.specials}
    assert by_id["sxsw_chaos_mode"].status == "built"
    assert "gating" in by_id["sxsw_chaos_mode"].impl
    assert by_id["hill_country_expansion"].status == "built"


def test_available_markets_lists_austin():
    assert "austin" in available_markets()


def test_env_var_selection(monkeypatch):
    monkeypatch.setenv(MARKET_ENV_VAR, "austin")
    assert get_market().id == "austin"
    monkeypatch.setenv(MARKET_ENV_VAR, "atlantis")
    with pytest.raises(MarketConfigError, match="unknown market 'atlantis'"):
        get_market()


# ---------- fail-closed refusals ----------

def _write_market(tmp_path, mid, payload):
    d = tmp_path / "markets"
    d.mkdir(exist_ok=True)
    (d / f"{mid}.json").write_text(json.dumps(payload), encoding="utf-8")
    return str(d)


def _valid_payload(mid="testm"):
    return {
        "id": mid,
        "name": "Test Market",
        "country": "US",
        "timezone": "America/Chicago",
        "locales": ["en-US"],
        "boundary": {
            "kind": "county_allowlist",
            "module": "worker.region.capcog",
            "counties_symbol": "CAPCOG_COUNTIES",
            "row_verdict_symbol": "row_verdict",
        },
        "catalog": "sources/master_sources_catalog_120.json",
        "specials": [],
    }


def test_unknown_market_refused(tmp_path):
    with pytest.raises(MarketConfigError, match="unknown market"):
        get_market("nope", markets_dir=str(tmp_path))


def test_malformed_json_refused(tmp_path):
    d = tmp_path / "markets"; d.mkdir()
    (d / "bad.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(MarketConfigError, match="unreadable/malformed"):
        get_market("bad", markets_dir=str(d))


def test_missing_required_key_refused(tmp_path):
    p = _valid_payload(); del p["timezone"]
    d = _write_market(tmp_path, "testm", p)
    with pytest.raises(MarketConfigError, match="missing required key 'timezone'"):
        get_market("testm", markets_dir=d)


def test_id_filename_mismatch_refused(tmp_path):
    p = _valid_payload("other")
    d = _write_market(tmp_path, "testm", p)
    with pytest.raises(MarketConfigError, match="!= filename id"):
        get_market("testm", markets_dir=d)


def test_bad_timezone_refused(tmp_path):
    p = _valid_payload(); p["timezone"] = "Mars/Olympus"
    d = _write_market(tmp_path, "testm", p)
    with pytest.raises(MarketConfigError, match="invalid timezone"):
        get_market("testm", markets_dir=d)


def test_unknown_boundary_kind_refused(tmp_path):
    p = _valid_payload(); p["boundary"]["kind"] = "vibes"
    d = _write_market(tmp_path, "testm", p)
    with pytest.raises(MarketConfigError, match="unknown boundary kind"):
        get_market("testm", markets_dir=d)


def test_missing_catalog_refused(tmp_path):
    p = _valid_payload(); p["catalog"] = "sources/does_not_exist.json"
    d = _write_market(tmp_path, "testm", p)
    with pytest.raises(MarketConfigError, match="not found"):
        get_market("testm", markets_dir=d)


def test_unresolvable_boundary_symbol_refused(tmp_path):
    p = _valid_payload(); p["boundary"]["counties_symbol"] = "NO_SUCH_SET"
    d = _write_market(tmp_path, "testm", p)
    m = get_market("testm", markets_dir=d)  # parse ok — resolution is lazy
    with pytest.raises(MarketConfigError, match="not found"):
        m.boundary_counties()


def test_unimportable_boundary_module_refused(tmp_path):
    p = _valid_payload(); p["boundary"]["module"] = "worker.region.atlantis"
    d = _write_market(tmp_path, "testm", p)
    m = get_market("testm", markets_dir=d)
    with pytest.raises(MarketConfigError, match="does not import"):
        m.row_verdict()


def test_invalid_special_status_refused(tmp_path):
    p = _valid_payload()
    p["specials"] = [{
        "id": "x", "kind": "k", "description": "d", "impl": "i",
        "status": "someday",
    }]
    d = _write_market(tmp_path, "testm", p)
    with pytest.raises(MarketConfigError, match="status 'someday'"):
        get_market("testm", markets_dir=d)


def test_special_missing_field_refused(tmp_path):
    p = _valid_payload()
    p["specials"] = [{"id": "x", "kind": "k", "status": "built"}]
    d = _write_market(tmp_path, "testm", p)
    with pytest.raises(MarketConfigError, match="missing"):
        get_market("testm", markets_dir=d)


# ---------- import_sources.py routing contract ----------

def test_import_sources_routes_through_market():
    from tools.import_sources import resolve_catalog_path
    path = resolve_catalog_path(None, "austin")
    assert path.endswith(os.path.join("sources", "master_sources_catalog_120.json"))
    assert os.path.isfile(path)


def test_import_sources_explicit_json_wins():
    from tools.import_sources import resolve_catalog_path
    assert resolve_catalog_path("/tmp/x.json", None) == "/tmp/x.json"


@pytest.mark.parametrize("json_arg,market_arg", [(None, None), ("p", "austin")])
def test_import_sources_refuses_ambiguous_selection(json_arg, market_arg):
    from tools.import_sources import resolve_catalog_path
    with pytest.raises(SystemExit, match="exactly one"):
        resolve_catalog_path(json_arg, market_arg)
