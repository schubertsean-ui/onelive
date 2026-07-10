"""Structural tests for migration 0008 (source-trust config + 4-state lock-in).

Pure-text assertions (no DB): verify the config tables, seeds, and the
event.confidence CHECK constraint are present and that the seeded defaults match
sources/trust_config.json (single source of truth for the numbers). A
@dbintegration test applies the migration to a live DB when ONELIVE_TEST_DB_DSN
is set.
"""
import json
import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRATION = os.path.join(REPO_ROOT, "supabase", "migrations", "0008_source_trust_config.sql")
CONFIG = os.path.join(REPO_ROOT, "sources", "trust_config.json")


@pytest.fixture(scope="module")
def sql():
    with open(MIGRATION, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def cfg():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def _num(value) -> str:
    """Regex for a numeric literal tolerant of trailing zeros (0.4 matches 0.40)."""
    return re.escape(str(value)) + r"0*(?![0-9])"


def test_migration_file_exists(sql):
    assert "source_type_weight" in sql


@pytest.mark.parametrize("table", [
    "source_type_weight",
    "confidence_weight_threshold",
    "priority_formula_version",
    "priority_formula_coefficient",
    "priority_band",
    "reputation_update_version",
    "reputation_update_param",
])
def test_all_config_tables_created(sql, table):
    assert re.search(rf"create table if not exists {table}\b", sql), table


def test_seeds_are_idempotent(sql):
    # Every insert must be conflict-guarded so re-running the migration is safe.
    inserts = re.findall(r"insert into", sql)
    conflicts = re.findall(r"on conflict", sql)
    assert len(inserts) == len(conflicts), "every seed insert must have ON CONFLICT"


def test_seeded_type_weights_match_config(sql, cfg):
    for stype, weight in cfg["source_type_weights"].items():
        assert re.search(rf"\('{stype}',\s*{_num(weight)}\)", sql), f"{stype}={weight} not seeded"


def test_seeded_priority_coefficients_match_config(sql, cfg):
    coeffs = cfg["priority_formula"]["versions"]["v1"]["coefficients"]
    for subscore, coef in coeffs.items():
        assert re.search(rf"'v1',\s*'{subscore}',\s*{_num(coef)}", sql), f"{subscore}={coef}"


def test_seeded_reputation_params_match_config(sql, cfg):
    params = cfg["reputation_decay_growth"]["versions"]["v1"]
    for param, value in params.items():
        assert re.search(rf"'v1',\s*'{param}',\s*{_num(value)}", sql), f"{param}={value}"


def test_seeded_bands_match_config(sql, cfg):
    for b in cfg["priority_bands"]:
        assert re.search(rf"'{b['band']}',\s*'{re.escape(b['label'])}',\s*{int(b['min_score'])}", sql)


def test_confidence_thresholds_seeded(sql, cfg):
    for row in cfg["confidence_weight_thresholds"]:
        assert re.search(rf"\('{row['state']}',\s*{_num(row['min_weight'])}\)", sql)


def test_event_confidence_check_constraint_is_4state(sql):
    # The CHECK must pin exactly the 4 canonical states — including disputed.
    m = re.search(r"check\s*\(\s*confidence\s+in\s*\(([^)]*)\)", sql, re.IGNORECASE)
    assert m, "no CHECK constraint on event.confidence"
    states = {s.strip().strip("'") for s in m.group(1).split(",")}
    assert states == {"unverified", "likely", "confirmed", "disputed"}


def test_check_constraint_dropped_first_for_idempotency(sql):
    assert "drop constraint if exists event_confidence_4state_chk" in sql


def test_confidence_threshold_table_only_allows_canonical_states(sql):
    # The threshold table's own CHECK must not admit a stray/legacy state.
    m = re.search(
        r"create table if not exists confidence_weight_threshold.*?check\s*\(\s*state\s+in\s*\(([^)]*)\)",
        sql, re.IGNORECASE | re.DOTALL,
    )
    assert m
    states = {s.strip().strip("'") for s in m.group(1).split(",")}
    assert states == {"unverified", "likely", "confirmed", "disputed"}


# --------------------------------------------------------------------------
# Optional DB integration: the migration applies and enforces the constraint.
# --------------------------------------------------------------------------

@pytest.mark.dbintegration
def test_migration_applies_and_enforces_4state(db_conn, sql):
    cur = db_conn.cursor()
    cur.execute(sql)

    # Seeds landed.
    cur.execute("select count(*) from source_type_weight")
    assert cur.fetchone()[0] >= 12
    cur.execute("select default_weight from source_type_weight where source_type='ticketing'")
    assert float(cur.fetchone()[0]) == 0.9

    # 4-state CHECK rejects a 3-state-era invalid write.
    cur.execute(
        "insert into venue(name, city) values ('Chk Hall','Austin') returning venue_id"
    )
    venue_id = cur.fetchone()[0]
    with pytest.raises(Exception):
        cur.execute(
            "insert into event(venue_id, confidence) values (%s, 'bogus')",
            (venue_id,),
        )
    db_conn.rollback()
