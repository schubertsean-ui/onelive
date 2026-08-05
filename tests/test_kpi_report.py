"""Tests for tools/kpi_report.py — the KPI-setting/quarterly-prioritization
scorecard (docs/strategy/ONE_LIVE_KPI_FRAMEWORK_v1.md).

Proves: the tool runs; it computes deterministically what it CAN compute
(reading real, already-existing sources — the extraction certification
record, the Kaizen ledger, the trust gate, RECORD.md, the model router, the
Brain IQ score); it marks the not-yet-instrumented KPIs HONESTLY (the literal
"not yet instrumented (trigger: ...)" text, never a fabricated number); a
planted OFF_TARGET regression turns the corresponding check red (a gate that
cannot fail proves nothing, OPERATING_RULES §9.6); and the CLI's --print /
--append / --check modes behave per tools/README.md's exit-code convention.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import tools.kpi_report as kpi_report
from tools.kpi_report import (
    INFO,
    NOT_YET_INSTRUMENTED,
    NOT_YET_INSTRUMENTED_SLOTS,
    OFF_TARGET,
    ON_TARGET,
    KPIComputeError,
    KPILedgerError,
    KPIRegistryError,
    KPISlot,
    KPIValue,
    _kpi_hallucination_rate,
    _kpi_record_open_rows,
    _kpi_recall,
    _slot_value,
    append_snapshot,
    load_kpi_ledger_rows,
    load_kpi_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "tools" / "kpi_report.py"
REAL_LEDGER = REPO_ROOT / "docs" / "metrics" / "KPI_LEDGER.md"
REAL_REGISTRY = REPO_ROOT / "docs" / "metrics" / "kpi_registry.json"

_EMPTY_LEDGER_BODY = (
    "# fixture\n\n"
    "| timestamp | area | metric | kind | target | current | trend | owner |\n"
    "|---|---|---|---|---|---|---|---|\n"
)


def _run_cli(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CLI), *args],
                          capture_output=True, text=True, timeout=60)


# ============================================================================
# Registry sanity — every slot is well-formed and the gap/measured split is
# honest (mirrors brain/iq.py's MEASURED/NOT_YET_MEASURED completeness test).
# ============================================================================
def test_every_slot_has_area_kind_owner_target():
    for slot in kpi_report.KPI_SLOTS:
        assert slot.area, slot
        assert slot.kind in ("leading", "lagging"), slot
        assert slot.owner, slot
        assert slot.target, slot


def test_gap_slots_have_no_compute_and_a_trigger():
    assert NOT_YET_INSTRUMENTED_SLOTS, "the not-yet-instrumented list must " \
        "not be empty — a scorecard claiming full coverage is a Goodhart trap"
    for slot in NOT_YET_INSTRUMENTED_SLOTS:
        assert slot.compute is None
        assert slot.trigger, f"{slot.metric} has no objective trigger"
        assert slot.why, f"{slot.metric} has no stated reason"


def test_measured_slots_all_have_a_compute_callable():
    for slot in kpi_report.MEASURED_SLOTS:
        assert callable(slot.compute), slot


def test_gap_and_measured_partition_the_full_registry():
    # KPISlot is a plain (unhashable) dataclass, so partition by identity via
    # id() rather than putting the slots themselves in a set.
    measured_ids = {id(s) for s in kpi_report.MEASURED_SLOTS}
    gap_ids = {id(s) for s in NOT_YET_INSTRUMENTED_SLOTS}
    all_ids = {id(s) for s in kpi_report.KPI_SLOTS}
    assert measured_ids | gap_ids == all_ids
    assert not (measured_ids & gap_ids)


# ============================================================================
# Config-driven registry — proves the founder directive: changing WHICH
# KPIs are tracked, their TARGETS, or their FREQUENCY is a JSON edit, never a
# code change. Every test below drives docs/metrics/kpi_registry.json (or a
# temp copy of it) through load_kpi_registry — the only function that reads
# the file — with zero edits to tools/kpi_report.py.
# ============================================================================
_VALID_FREQUENCIES = frozenset(
    {"per_run", "daily", "weekly", "monthly", "quarterly"})
_VALID_DIRECTIONS = frozenset(
    {"higher_better", "lower_better", "boolean", "informational"})


def _load_real_registry_dict() -> dict:
    return json.loads(REAL_REGISTRY.read_text(encoding="utf-8"))


def _write_registry(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_real_registry_reproduces_the_15_prior_hardcoded_kpis():
    # The migrated JSON registry must carry every KPI the old hardcoded
    # Python tuple defined, with the same values — this is the "the refactor
    # changed nothing observable" proof.
    slots = kpi_report.KPI_SLOTS
    # 15 migrated + coverage-discovered-to-licensed-ratio (registered
    # 2026-08-05, kickoff WS10 — the founder's 50:1 KPI). The 15 originals
    # below must remain byte-identical; growth is legitimate, silent
    # mutation of the migrated rows is not.
    assert len(slots) == 16
    by_metric = {s.metric: s for s in slots}
    assert by_metric["Recall @ last certification (anti-gaming pair)"].target == ">= 80%"
    assert by_metric["Field-level hallucination rate @ last certification"].target == \
        "<= 1% (one-way ratchet, KAIZEN.md §M7)"
    assert by_metric["trust_gate clean (trust invariants hold)"].area == "Trust/safety"
    assert by_metric["trust_gate clean (trust invariants hold)"].owner == \
        "gate custody / evaluator"
    assert by_metric["All-time escaped defects (M3)"].kind == "lagging"
    areas = {s.area for s in slots}
    assert areas == {"Ingestion/Coverage", "Extraction Correctness", "Cost-efficiency",
                     "Brain quality", "UX/consumer", "Trust/safety"}


def test_every_slot_has_a_first_class_frequency_and_direction():
    for slot in kpi_report.KPI_SLOTS:
        assert slot.id, slot
        assert slot.frequency in _VALID_FREQUENCIES, slot
        assert slot.direction in _VALID_DIRECTIONS, slot


def test_frequency_is_surfaced_in_the_printed_scorecard():
    proc = _run_cli(["--print"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "frequency: weekly" in proc.stdout
    assert "frequency: per_run" in proc.stdout
    # every slot's block prints exactly one frequency line
    assert proc.stdout.count("frequency:") == len(kpi_report.KPI_SLOTS)


def test_change_a_target_via_config_only_no_code_change(tmp_path):
    """The founder-directed proof: edit ONLY the JSON, never tools/kpi_report.py,
    and see a target change take effect."""
    data = _load_real_registry_dict()
    changed = False
    for entry in data["kpis"]:
        if entry["id"] == "extraction-recall":
            entry["target"] = ">= 95% (edited in a temp config only)"
            changed = True
    assert changed
    registry_path = tmp_path / "kpi_registry.json"
    _write_registry(registry_path, data)

    slots = load_kpi_registry(registry_path)
    by_id = {s.id: s for s in slots}
    assert by_id["extraction-recall"].target == ">= 95% (edited in a temp config only)"
    # nothing else about that slot moved
    assert by_id["extraction-recall"].area == "Extraction Correctness"
    assert by_id["extraction-recall"].compute is not None


def test_change_a_frequency_via_config_only_no_code_change(tmp_path):
    data = _load_real_registry_dict()
    for entry in data["kpis"]:
        if entry["id"] == "cost-per-verified-event":
            assert entry["frequency"] == "monthly"
            entry["frequency"] = "daily"
    registry_path = tmp_path / "kpi_registry.json"
    _write_registry(registry_path, data)

    slots = load_kpi_registry(registry_path)
    by_id = {s.id: s for s in slots}
    assert by_id["cost-per-verified-event"].frequency == "daily"


def test_add_a_new_kpi_via_config_only_appears(tmp_path):
    data = _load_real_registry_dict()
    data["kpis"].append({
        "id": "test-new-kpi-added-via-config",
        "area": "Trust/safety",
        "metric": "A brand new KPI added purely via config",
        "kind": "leading",
        "target": "some target",
        "direction": "informational",
        "frequency": "weekly",
        "owner": "test",
        "enabled": True,
        "compute": "manual_gap",
        "why": "test fixture — not really measured",
        "trigger": "never (test fixture)",
    })
    registry_path = tmp_path / "kpi_registry.json"
    _write_registry(registry_path, data)

    slots = load_kpi_registry(registry_path)
    assert len(slots) == len(kpi_report.KPI_SLOTS) + 1
    added = next(s for s in slots if s.id == "test-new-kpi-added-via-config")
    assert added.is_gap()
    value = _slot_value(added)
    assert value.status == NOT_YET_INSTRUMENTED
    assert "never (test fixture)" in value.current


def test_add_a_new_kpi_reusing_an_existing_compute_key(tmp_path):
    """A new KPI whose measurement ALREADY has a compute function (no new
    Python) is also a pure config addition."""
    data = _load_real_registry_dict()
    data["kpis"].append({
        "id": "test-new-kpi-reusing-compute",
        "area": "Trust/safety",
        "metric": "A second read of trust_gate, added via config",
        "kind": "lagging",
        "target": "PASS, always",
        "direction": "boolean",
        "frequency": "per_run",
        "owner": "test",
        "enabled": True,
        "compute": "trust_gate",
    })
    registry_path = tmp_path / "kpi_registry.json"
    _write_registry(registry_path, data)

    slots = load_kpi_registry(registry_path)
    added = next(s for s in slots if s.id == "test-new-kpi-reusing-compute")
    assert not added.is_gap()
    value = _slot_value(added)
    assert value.status in (ON_TARGET, OFF_TARGET)


def test_disabling_a_kpi_via_config_excludes_it_from_active_slots(tmp_path):
    data = _load_real_registry_dict()
    for entry in data["kpis"]:
        if entry["id"] == "ux-real-user-engagement":
            entry["enabled"] = False
    registry_path = tmp_path / "kpi_registry.json"
    _write_registry(registry_path, data)

    all_slots = load_kpi_registry(registry_path)
    active_slots = tuple(s for s in all_slots if s.enabled)
    assert len(all_slots) == len(kpi_report.ALL_KPI_SLOTS)
    assert len(active_slots) == len(kpi_report.KPI_SLOTS) - 1
    assert all(s.id != "ux-real-user-engagement" for s in active_slots)


# --- Fail-closed on a malformed registry ------------------------------------
def test_registry_missing_file_raises_loud(tmp_path):
    with pytest.raises(KPIRegistryError):
        load_kpi_registry(tmp_path / "does_not_exist.json")


def test_registry_bad_json_raises_loud(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(KPIRegistryError):
        load_kpi_registry(bad)


def test_registry_not_shaped_kpis_list_raises_loud(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"not_kpis": []}), encoding="utf-8")
    with pytest.raises(KPIRegistryError):
        load_kpi_registry(bad)


def test_registry_empty_kpis_list_raises_loud(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"kpis": []}), encoding="utf-8")
    with pytest.raises(KPIRegistryError):
        load_kpi_registry(bad)


def test_registry_entry_missing_required_field_raises_loud(tmp_path):
    data = _load_real_registry_dict()
    del data["kpis"][0]["frequency"]
    bad = tmp_path / "bad.json"
    _write_registry(bad, data)
    with pytest.raises(KPIRegistryError, match="frequency"):
        load_kpi_registry(bad)


def test_registry_unknown_kind_raises_loud(tmp_path):
    data = _load_real_registry_dict()
    data["kpis"][0]["kind"] = "sideways"
    bad = tmp_path / "bad.json"
    _write_registry(bad, data)
    with pytest.raises(KPIRegistryError, match="kind"):
        load_kpi_registry(bad)


def test_registry_unknown_direction_raises_loud(tmp_path):
    data = _load_real_registry_dict()
    data["kpis"][0]["direction"] = "sideways_better"
    bad = tmp_path / "bad.json"
    _write_registry(bad, data)
    with pytest.raises(KPIRegistryError, match="direction"):
        load_kpi_registry(bad)


def test_registry_unknown_frequency_raises_loud(tmp_path):
    data = _load_real_registry_dict()
    data["kpis"][0]["frequency"] = "biannually"
    bad = tmp_path / "bad.json"
    _write_registry(bad, data)
    with pytest.raises(KPIRegistryError, match="frequency"):
        load_kpi_registry(bad)


def test_registry_unknown_compute_key_raises_loud(tmp_path):
    data = _load_real_registry_dict()
    data["kpis"][0]["compute"] = "this_compute_key_does_not_exist"
    bad = tmp_path / "bad.json"
    _write_registry(bad, data)
    with pytest.raises(KPIRegistryError, match="unknown compute key"):
        load_kpi_registry(bad)


def test_registry_manual_gap_missing_why_raises_loud(tmp_path):
    data = _load_real_registry_dict()
    for entry in data["kpis"]:
        if entry["compute"] == "manual_gap":
            del entry["why"]
            break
    bad = tmp_path / "bad.json"
    _write_registry(bad, data)
    with pytest.raises(KPIRegistryError, match="why"):
        load_kpi_registry(bad)


def test_registry_manual_gap_missing_trigger_raises_loud(tmp_path):
    data = _load_real_registry_dict()
    for entry in data["kpis"]:
        if entry["compute"] == "manual_gap":
            del entry["trigger"]
            break
    bad = tmp_path / "bad.json"
    _write_registry(bad, data)
    with pytest.raises(KPIRegistryError, match="trigger"):
        load_kpi_registry(bad)


def test_registry_duplicate_id_raises_loud(tmp_path):
    data = _load_real_registry_dict()
    data["kpis"][1]["id"] = data["kpis"][0]["id"]
    bad = tmp_path / "bad.json"
    _write_registry(bad, data)
    with pytest.raises(KPIRegistryError, match="duplicate"):
        load_kpi_registry(bad)


def test_cli_registry_error_exits_2_with_a_clear_message(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"kpis": [{"id": "x"}]}), encoding="utf-8")
    proc = _run_cli(["--print", "--registry", str(bad)])
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "REGISTRY ERROR" in proc.stderr
    assert "missing required field" in proc.stderr


def test_cli_honors_a_custom_registry_end_to_end(tmp_path):
    """Full proof the CLI itself (not just the loader) is config-driven: a
    trimmed registry with one enabled KPI produces a one-KPI scorecard."""
    data = _load_real_registry_dict()
    data["kpis"] = [e for e in data["kpis"] if e["id"] == "trust-gate-clean"]
    custom = tmp_path / "kpi_registry.json"
    _write_registry(custom, data)
    proc = _run_cli(["--print", "--registry", str(custom)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "1 KPIs tracked" in proc.stdout
    assert "trust_gate clean" in proc.stdout


def test_slot_value_of_a_gap_slot_is_the_literal_honest_text():
    gap = KPISlot(area="Test", metric="fake metric", kind="leading", owner="nobody",
                 target="n/a", trigger="something specific happens")
    value = _slot_value(gap)
    assert value.status == NOT_YET_INSTRUMENTED
    assert value.current == "not yet instrumented (trigger: something specific happens)"
    assert value.raw is None


# ============================================================================
# Individual computations — deterministic given a fixed input file/fixture.
# ============================================================================
def test_hallucination_rate_reads_the_real_certification_record():
    value = _kpi_hallucination_rate()
    assert value.raw is not None and 0.0 <= value.raw <= 1.0
    assert value.status in (ON_TARGET, OFF_TARGET)
    assert "certification" in value.current


def test_recall_reads_the_real_certification_record():
    value = _kpi_recall()
    assert value.raw is not None and 0.0 <= value.raw <= 1.0
    assert value.status in (ON_TARGET, OFF_TARGET)


def test_hallucination_rate_planted_regression_turns_off_target(tmp_path, monkeypatch):
    """A gate that cannot fail proves nothing (OPERATING_RULES §9.6): plant a
    certification record whose rate is above the ratified threshold and prove
    the KPI reports OFF_TARGET, not a silently-passing green."""
    bad = tmp_path / "CERTIFIED_HARNESS.json"
    bad.write_text(json.dumps({
        "verified_at": "2020-01-01T00:00:00Z", "run_id": "0", "model": "x",
        "metrics": {"hallucination_rate": 0.5, "recall": 0.99},
    }), encoding="utf-8")
    monkeypatch.setattr(kpi_report, "DEFAULT_CERTIFIED_HARNESS", bad)
    value = _kpi_hallucination_rate()
    assert value.status == OFF_TARGET
    assert value.raw == 0.5


def test_recall_planted_regression_turns_off_target(tmp_path, monkeypatch):
    bad = tmp_path / "CERTIFIED_HARNESS.json"
    bad.write_text(json.dumps({
        "verified_at": "2020-01-01T00:00:00Z", "run_id": "0", "model": "x",
        "metrics": {"hallucination_rate": 0.001, "recall": 0.10},
    }), encoding="utf-8")
    monkeypatch.setattr(kpi_report, "DEFAULT_CERTIFIED_HARNESS", bad)
    value = _kpi_recall()
    assert value.status == OFF_TARGET
    assert value.raw == 0.10


def test_certification_missing_file_raises_compute_error(tmp_path, monkeypatch):
    monkeypatch.setattr(kpi_report, "DEFAULT_CERTIFIED_HARNESS", tmp_path / "nope.json")
    with pytest.raises(KPIComputeError):
        _kpi_hallucination_rate()


def test_certification_bad_json_raises_compute_error(tmp_path, monkeypatch):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(kpi_report, "DEFAULT_CERTIFIED_HARNESS", bad)
    with pytest.raises(KPIComputeError):
        _kpi_hallucination_rate()


def test_certification_missing_metrics_key_raises_compute_error(tmp_path, monkeypatch):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"no_metrics_here": True}), encoding="utf-8")
    monkeypatch.setattr(kpi_report, "DEFAULT_CERTIFIED_HARNESS", bad)
    with pytest.raises(KPIComputeError):
        _kpi_hallucination_rate()


# --- RECORD.md open/resolved parser -----------------------------------------
_FAKE_RECORD = """# fixture record

| # | Opened | What | Bar | Trigger | Status |
|---|---|---|---|---|---|
| R-001 | 2020-01-01 | thing one | bar | trigger | OPEN |
| R-002 | 2020-01-01 | thing two | bar | trigger | RESOLVED (fixed it) |
| R-003 | 2020-01-01 | thing three with a | pipe in prose | bar | trigger | OPEN (still going) |
"""


def test_record_open_rows_counts_open_vs_resolved(tmp_path, monkeypatch):
    fixture = tmp_path / "RECORD.md"
    fixture.write_text(_FAKE_RECORD, encoding="utf-8")
    monkeypatch.setattr(kpi_report, "DEFAULT_RECORD", fixture)
    value = _kpi_record_open_rows()
    assert value.status == INFO
    assert "2 OPEN" in value.current
    assert "1 RESOLVED" in value.current
    assert value.raw == 2.0


def test_record_open_rows_real_file_parses_cleanly():
    # The real docs/RECORD.md must parse with zero unparseable rows — this is
    # a live integration check against the actual register, not a fixture.
    value = _kpi_record_open_rows()
    assert value.status == INFO
    assert "OPEN" in value.current and "RESOLVED" in value.current


# ============================================================================
# Ledger read/append
# ============================================================================
def _seed_ledger(path: Path) -> None:
    path.write_text(_EMPTY_LEDGER_BODY, encoding="utf-8")


def test_append_snapshot_writes_one_row_per_slot(tmp_path):
    ledger = tmp_path / "kpi_ledger.md"
    _seed_ledger(ledger)
    results, errors = kpi_report._compute_all()
    assert not errors, errors
    new_lines = append_snapshot(ledger, "2026-07-25T00:00:00Z", results)
    assert len(new_lines) == len(kpi_report.KPI_SLOTS)
    rows = load_kpi_ledger_rows(ledger)
    assert len(rows) == len(kpi_report.KPI_SLOTS)
    assert all(r["timestamp"] == "2026-07-25T00:00:00Z" for r in rows)


def test_append_snapshot_first_row_has_no_trend():
    ledger_rows = load_kpi_ledger_rows(REAL_LEDGER)
    # every metric's FIRST-ever appearance in the ledger carries trend "-"
    seen = set()
    for row in ledger_rows:
        key = (row["area"], row["metric"])
        if key not in seen:
            assert row["trend"] == "-", row
            seen.add(key)


def test_append_snapshot_computes_trend_against_prior_row(tmp_path):
    ledger = tmp_path / "kpi_ledger.md"
    _seed_ledger(ledger)
    # Hand-seed a lower prior reading for the hallucination-rate metric so the
    # next real append computes an UP trend against it.
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write("| 2020-01-01T00:00:00Z | Extraction Correctness | "
                 "Field-level hallucination rate @ last certification | "
                 "lagging | <= 1% | 0.00% (fixture) | - | nobody |\n")
    results, errors = kpi_report._compute_all()
    assert not errors, errors
    append_snapshot(ledger, "2026-07-25T00:00:00Z", results)
    rows = load_kpi_ledger_rows(ledger)
    last = [r for r in rows
           if r["metric"] == "Field-level hallucination rate @ last certification"
           and r["timestamp"] == "2026-07-25T00:00:00Z"][0]
    assert last["trend"] == "↑"  # real rate (>0%) vs the fixture's seeded 0.00%


def test_load_kpi_ledger_rows_raises_loud_on_missing_file(tmp_path):
    with pytest.raises(KPILedgerError):
        load_kpi_ledger_rows(tmp_path / "does_not_exist.md")


def test_load_kpi_ledger_rows_raises_loud_on_empty_table(tmp_path):
    ledger = tmp_path / "empty.md"
    _seed_ledger(ledger)
    with pytest.raises(KPILedgerError):
        load_kpi_ledger_rows(ledger)


def test_real_ledger_parses_and_has_a_row_per_slot_in_its_last_snapshot():
    rows = load_kpi_ledger_rows(REAL_LEDGER)
    last_ts = rows[-1]["timestamp"]
    last_snapshot = [r for r in rows if r["timestamp"] == last_ts]
    assert len(last_snapshot) == len(kpi_report.KPI_SLOTS)


# ============================================================================
# CLI smoke tests (subprocess, matching tools/brain_iq.py's own test style)
# ============================================================================
def test_cli_print_runs_clean():
    proc = _run_cli(["--print"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "KPI scorecard" in proc.stdout
    assert "not yet instrumented" in proc.stdout


def test_cli_check_holds_on_the_real_repo_state():
    proc = _run_cli(["--check"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS" in proc.stdout


def test_cli_append_then_reload(tmp_path):
    ledger = tmp_path / "kpi_ledger.md"
    _seed_ledger(ledger)
    proc = _run_cli(["--append", "2026-07-25T00:00:00Z", "--ledger", str(ledger)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rows = load_kpi_ledger_rows(ledger)
    assert len(rows) == len(kpi_report.KPI_SLOTS)


def test_cli_append_requires_a_timestamp():
    proc = _run_cli(["--append", ""])
    assert proc.returncode == 2
    assert "TIMESTAMP" in proc.stderr


def test_cli_help_does_not_crash():
    proc = _run_cli(["--help"])
    assert proc.returncode == 0
    assert "kpi_report" in proc.stdout.lower()
