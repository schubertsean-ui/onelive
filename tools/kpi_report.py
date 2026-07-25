#!/usr/bin/env python3
"""kpi_report — CLI scorecard for the KPI-setting + quarterly-prioritization
process (docs/strategy/ONE_LIVE_KPI_FRAMEWORK_v1.md).

SUMMARY: this is the AGGREGATION layer over measures that already exist
elsewhere in the harness — it computes NOTHING new. Every number here is
read from a file already on disk or a check already run by another tool:
  - the extraction certification record (ai/golden/CERTIFIED_HARNESS.json)
    vs its ratified thresholds (ai/exam_thresholds.py);
  - the Kaizen ledger (docs/metrics/KAIZEN_LEDGER.md via
    tools/kaizen_trends.py: escapes(), build_report());
  - the Brain IQ score (brain/iq.py, docs/metrics/BRAIN_IQ_LEDGER.md via
    tools/brain_iq.py);
  - the trust gate (tools/trust_gate.py exit code);
  - the deviations register (docs/RECORD.md — OPEN vs RESOLVED rows);
  - the loop-stage model router (tools/model_router.py);
  - the pytest suite (collect-only count).
Founder direction (CLAUDE.md "Cost discipline" / "Measure, don't guess"):
EXTEND the existing ledgers, never reinvent or duplicate them.

Goodhart-honesty control (mirrors brain/iq.py's MEASURED/NOT_YET_MEASURED
split, extended with area/kind/owner for the KPI ledger's shape): every KPI
this tool cannot yet compute is named explicitly, with WHY and an objective
TRIGGER, in ``NOT_YET_INSTRUMENTED`` below — never silently skipped, never
guessed at. A KPI this tool cannot compute is reported as the literal text
"not yet instrumented (trigger: ...)", never a fabricated number.

Registry (founder directive — changing WHICH KPIs are tracked, their
TARGETS, or their FREQUENCY must be a simple config edit, never a code
change): the KPI list itself is pure data in ``docs/metrics/
kpi_registry.json`` (schema + how-to-change recipe: see that file's
``_comment`` and docs/strategy/ONE_LIVE_KPI_FRAMEWORK_v1.md's "How to change
a KPI, its target, or its frequency" section). This module reads and
VALIDATES that file (``load_kpi_registry``) — it never hardcodes the list.
Only a genuinely NEW measurement source needs a code change: add one
``_kpi_*`` function and register it by name in ``_COMPUTE_FUNCTIONS``: every
other change (target/frequency/area/owner/enable/disable, or a new KPI that
reuses an existing compute or is a named "manual_gap") is JSON-only.

Modes:
  --print              compute + print the scorecard (no write; default)
  --append TIMESTAMP   append one snapshot's rows to docs/metrics/KPI_LEDGER.md
                       (TIMESTAMP is caller/CI-supplied — this module never
                       reads the wall clock)
  --check              exit 1 if any COMPUTED (not gap) KPI is OFF_TARGET
  --registry PATH       KPI registry JSON to read (default: docs/metrics/
                       kpi_registry.json)

Exit codes (tools/README.md convention):
  0 = ok (printed / appended / --check found nothing off target)
  1 = --check found an off-target KPI
  2 = could not compute something required, or the registry is malformed —
      fail loud, never invent a number or silently skip a bad entry

Usage:
  python tools/kpi_report.py
  python tools/kpi_report.py --append 2026-07-25T12:00:00Z
  python tools/kpi_report.py --check
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Optional

# Running as a script puts tools/ on sys.path[0], not the repo root; add the
# root so `tools.*`/`brain.*`/`ai.*` import exactly as they do under pytest
# (mirrors tools/brain_iq.py's bootstrap).
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ai.exam_thresholds import HALLUCINATION_MAX, RECALL_MIN  # noqa: E402
from brain.iq import CoverageItem, compute_brain_iq, trend_symbol  # noqa: E402
from tools.brain_iq import DEFAULT_LEDGER as _BRAIN_IQ_LEDGER  # noqa: E402
from tools.brain_iq import LedgerError as BrainIQLedgerError  # noqa: E402
from tools.brain_iq import load_ledger_rows as load_brain_iq_rows  # noqa: E402
from tools.kaizen_trends import build_report as kaizen_build_report  # noqa: E402
from tools.kaizen_trends import escapes as kaizen_escapes  # noqa: E402
from tools.model_router import STAGE_MODELS, resolve_model  # noqa: E402

DEFAULT_LEDGER = _REPO_ROOT / "docs" / "metrics" / "KPI_LEDGER.md"
DEFAULT_KAIZEN_LEDGER = _REPO_ROOT / "docs" / "metrics" / "KAIZEN_LEDGER.md"
DEFAULT_RECORD = _REPO_ROOT / "docs" / "RECORD.md"
DEFAULT_CERTIFIED_HARNESS = _REPO_ROOT / "ai" / "golden" / "CERTIFIED_HARNESS.json"
DEFAULT_TRUST_GATE = _REPO_ROOT / "tools" / "trust_gate.py"
DEFAULT_KPI_REGISTRY = _REPO_ROOT / "docs" / "metrics" / "kpi_registry.json"

ON_TARGET = "ON_TARGET"
OFF_TARGET = "OFF_TARGET"
INFO = "INFO"
NOT_YET_INSTRUMENTED = "NOT_YET_INSTRUMENTED"

# The machine-readable table marker for docs/metrics/KPI_LEDGER.md.
_TABLE_HEADER_CELLS = ("timestamp", "area", "metric", "kind", "target",
                       "current", "trend", "owner")

# Valid values for the registry's controlled-vocabulary fields — anything
# else fails registry load loudly (see load_kpi_registry).
_VALID_KINDS = frozenset({"leading", "lagging"})
_VALID_DIRECTIONS = frozenset(
    {"higher_better", "lower_better", "boolean", "informational"})
_VALID_FREQUENCIES = frozenset(
    {"per_run", "daily", "weekly", "monthly", "quarterly"})


class KPIComputeError(Exception):
    """Raised when a KPI that SHOULD be computable could not be — fail loud.

    Distinct from a legitimate OFF_TARGET result (a real, informative
    measurement that just misses its target): this means the measurement
    itself could not be taken (file missing/unparseable, a subprocess could
    not run at all) and the tool refuses to guess a number.
    """


class KPIRegistryError(Exception):
    """The KPI registry (docs/metrics/kpi_registry.json) is missing, is not
    valid JSON, or contains a malformed/unknown-compute entry — fail loud,
    never silently drop or guess at a KPI definition."""


# ============================================================================
# KPI value + registry shape
# ============================================================================
@dataclass
class KPIValue:
    """One computed KPI's live reading."""

    current: str
    status: str  # ON_TARGET | OFF_TARGET | INFO
    raw: Optional[float]  # numeric reading for trend purposes, or None


@dataclass
class KPISlot:
    """One line of the KPI ledger: either COMPUTED (``compute`` set) or a
    named gap (``compute`` is None, ``why``/``trigger`` are set instead) —
    mirrors brain/iq.py's MEASURED/NOT_YET_MEASURED split, extended with the
    area/kind/owner columns this ledger's shape needs.

    Built exclusively by ``load_kpi_registry`` from the JSON registry
    (docs/metrics/kpi_registry.json) — ``id``/``direction``/``frequency``/
    ``enabled`` are first-class config fields, not derived. The fields here
    default so ad-hoc/test construction (e.g. a synthetic gap slot in a
    test) stays terse; the registry LOADER is what enforces every field is
    actually present and well-formed for real entries.
    """

    area: str
    metric: str
    kind: str  # "leading" | "lagging"
    owner: str
    target: str
    id: str = ""
    direction: str = "informational"  # higher_better|lower_better|boolean|informational
    frequency: str = "per_run"  # per_run|daily|weekly|monthly|quarterly
    enabled: bool = True
    compute: Optional[Callable[[], KPIValue]] = None
    why: Optional[str] = None
    trigger: Optional[str] = None

    def is_gap(self) -> bool:
        return self.compute is None


# ============================================================================
# Individual KPI computations — each reads something ALREADY on disk/already
# run elsewhere; none of these introduce a new measurement system.
# ============================================================================
def _read_certified_harness() -> dict:
    try:
        text = DEFAULT_CERTIFIED_HARNESS.read_text(encoding="utf-8")
    except OSError as exc:
        raise KPIComputeError(
            f"cannot read {DEFAULT_CERTIFIED_HARNESS}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise KPIComputeError(
            f"{DEFAULT_CERTIFIED_HARNESS} is not valid JSON: {exc}") from exc
    metrics = data.get("metrics")
    if not isinstance(metrics, dict):
        raise KPIComputeError(
            f"{DEFAULT_CERTIFIED_HARNESS} has no 'metrics' object — cannot "
            "read the certified extraction rate.")
    return data


def _kpi_hallucination_rate() -> KPIValue:
    data = _read_certified_harness()
    rate = data["metrics"]["hallucination_rate"]
    status = ON_TARGET if rate <= HALLUCINATION_MAX else OFF_TARGET
    current = (f"{rate * 100:.2f}% (at certification {data.get('verified_at', '?')}"
               f", run {data.get('run_id', '?')}, model {data.get('model', '?')})")
    return KPIValue(current=current, status=status, raw=rate)


def _kpi_recall() -> KPIValue:
    data = _read_certified_harness()
    recall = data["metrics"]["recall"]
    status = ON_TARGET if recall >= RECALL_MIN else OFF_TARGET
    current = f"{recall * 100:.2f}% (at certification {data.get('verified_at', '?')})"
    return KPIValue(current=current, status=status, raw=recall)


def _read_kaizen_ledger_text() -> str:
    try:
        return DEFAULT_KAIZEN_LEDGER.read_text(encoding="utf-8")
    except OSError as exc:
        raise KPIComputeError(
            f"cannot read {DEFAULT_KAIZEN_LEDGER}: {exc}") from exc


def _kpi_escaped_defects() -> KPIValue:
    text = _read_kaizen_ledger_text()
    n = kaizen_escapes(text)
    status = ON_TARGET if n == 0 else OFF_TARGET
    return KPIValue(current=f"{n} (all-time, docs/metrics/KAIZEN_LEDGER.md)",
                    status=status, raw=float(n))


def _kpi_repeat_class_alarms() -> KPIValue:
    text = _read_kaizen_ledger_text()
    try:
        _report, findings = kaizen_build_report(text)
    except ValueError as exc:
        raise KPIComputeError(f"tools.kaizen_trends.build_report failed: {exc}") from exc
    alarms = [f for f in findings if f.startswith("REPEAT-CLASS ALARM")]
    status = ON_TARGET if not alarms else OFF_TARGET
    current = f"{len(alarms)} active" if alarms else "0 active"
    return KPIValue(current=current, status=status, raw=float(len(alarms)))


def _kpi_trust_gate() -> KPIValue:
    try:
        proc = subprocess.run(
            [sys.executable, str(DEFAULT_TRUST_GATE)],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise KPIComputeError(f"could not run {DEFAULT_TRUST_GATE}: {exc}") from exc
    ok = proc.returncode == 0
    msg = (proc.stdout or proc.stderr or "").strip().splitlines()
    detail = msg[0] if msg else f"exit {proc.returncode}"
    current = "PASS" if ok else f"FAIL: {detail}"
    return KPIValue(current=current, status=(ON_TARGET if ok else OFF_TARGET),
                    raw=(1.0 if ok else 0.0))


_RECORD_ROW_RE = re.compile(r"^\|\s*(R-\d+)\s*\|")
_RECORD_STATUS_RE = re.compile(r"\|\s*((?:OPEN|RESOLVED)\b[^|]*)\s*\|\s*$")


def _kpi_record_open_rows() -> KPIValue:
    try:
        text = DEFAULT_RECORD.read_text(encoding="utf-8")
    except OSError as exc:
        raise KPIComputeError(f"cannot read {DEFAULT_RECORD}: {exc}") from exc
    open_n = 0
    resolved_n = 0
    unparsed: list[str] = []
    for line in text.splitlines():
        row_match = _RECORD_ROW_RE.match(line.strip())
        if not row_match:
            continue
        status_match = _RECORD_STATUS_RE.search(line.rstrip())
        if status_match is None:
            unparsed.append(row_match.group(1))
            continue
        status_cell = status_match.group(1).strip()
        if status_cell.startswith("OPEN"):
            open_n += 1
        elif status_cell.startswith("RESOLVED"):
            resolved_n += 1
        else:
            unparsed.append(row_match.group(1))
    if unparsed:
        raise KPIComputeError(
            f"{DEFAULT_RECORD}: could not read the status cell of "
            f"{', '.join(unparsed)} — refusing to guess an open-row count.")
    total = open_n + resolved_n
    if total == 0:
        raise KPIComputeError(f"{DEFAULT_RECORD}: parsed zero R-### rows — the "
                              "parser is almost certainly broken, not the file.")
    current = f"{open_n} OPEN / {resolved_n} RESOLVED ({total} total rows)"
    return KPIValue(current=current, status=INFO, raw=float(open_n))


_PYTEST_COUNT_RE = re.compile(r"(\d+)\s+tests?\s+collected")


def _kpi_pytest_count() -> KPIValue:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--collect-only"],
            capture_output=True, text=True, timeout=120, cwd=str(_REPO_ROOT),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise KPIComputeError(f"could not run pytest --collect-only: {exc}") from exc
    match = _PYTEST_COUNT_RE.search(proc.stdout)
    if match is None:
        raise KPIComputeError(
            "could not parse a test count out of `pytest --collect-only` "
            f"output (exit {proc.returncode}); refusing to guess a count. "
            f"stdout tail: {proc.stdout[-300:]!r}")
    n = int(match.group(1))
    return KPIValue(current=f"{n} tests collected", status=INFO, raw=float(n))


def _kpi_brain_iq() -> KPIValue:
    iq = compute_brain_iq(now_iso="(kpi_report run — unrecorded instant)")
    try:
        rows = load_brain_iq_rows(_BRAIN_IQ_LEDGER)
        previous = rows[-1]["composite"]
    except BrainIQLedgerError:
        previous = None
    trend = trend_symbol(iq.composite, previous)
    current = (f"composite={iq.composite:.4f} (knowledge={iq.knowledge.score:.4f} "
               f"efficiency={iq.efficiency.score:.4f} learning={iq.learning.score:.4f}) "
               f"trend vs last Brain IQ ledger row: {trend}")
    return KPIValue(current=current, status=INFO, raw=iq.composite)


def _kpi_model_routing() -> KPIValue:
    ok_stages = []
    other_stages = []
    for stage in sorted(STAGE_MODELS):
        try:
            model = resolve_model(stage)
            ok_stages.append(f"{stage}={model}")
        except (ValueError, KeyError) as exc:
            # A stage can legitimately be fail-closed (e.g. extraction while
            # its release gate is shut, R-013) — that is the invariant WORKING,
            # not a broken tool, so it is reported, not raised.
            other_stages.append(f"{stage}=fail-closed ({exc})")
    current = "; ".join(ok_stages + other_stages)
    status = ON_TARGET if not other_stages else INFO
    return KPIValue(current=current, status=status, raw=float(len(ok_stages)))


# ============================================================================
# Compute-function registry — the ONLY place a JSON registry entry's
# ``compute`` key is resolved to actual Python. Adding a genuinely new
# measurement means writing one ``_kpi_*`` function above and adding one line
# here; every other registry change (new KPI reusing an existing key or
# "manual_gap", re-targeting, re-cadencing, re-owning, enabling/disabling) is
# then a pure JSON edit with zero code touched.
# ============================================================================
_COMPUTE_FUNCTIONS: dict[str, Callable[[], KPIValue]] = {
    "hallucination_rate": _kpi_hallucination_rate,
    "recall": _kpi_recall,
    "escaped_defects": _kpi_escaped_defects,
    "repeat_class_alarms": _kpi_repeat_class_alarms,
    "trust_gate": _kpi_trust_gate,
    "record_open_rows": _kpi_record_open_rows,
    "pytest_count": _kpi_pytest_count,
    "brain_iq": _kpi_brain_iq,
    "model_routing": _kpi_model_routing,
}

# Registry entry fields every KPI must carry — see docs/metrics/
# kpi_registry.json's own _comment for the schema in prose.
_REQUIRED_ENTRY_FIELDS = ("id", "area", "metric", "kind", "target", "direction",
                          "frequency", "owner", "enabled", "compute")
_REQUIRED_STRING_FIELDS = ("area", "metric", "target", "owner")


def load_kpi_registry(path: pathlib.Path) -> tuple[KPISlot, ...]:
    """Load + validate the editable KPI registry (JSON) into KPISlot objects.

    Fail-CLOSED, per CLAUDE.md's no-silent-deferral rule: any malformed
    entry — a missing field, an unknown kind/direction/frequency, an unknown
    compute key, a "manual_gap" entry missing why/trigger, a duplicate id, or
    a registry that isn't valid JSON/isn't shaped {"kpis": [...]} — raises
    KPIRegistryError. Nothing is ever silently skipped or guessed.

    This is the ONLY function that reads the registry file, and it treats
    every field generically — which is what makes re-targeting, re-
    cadencing, re-owning, enabling/disabling, or adding a KPI (that reuses an
    existing compute key or is a named "manual_gap") a pure JSON edit: no
    code path here is specific to any one KPI.
    """
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise KPIRegistryError(f"cannot read KPI registry at {path}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise KPIRegistryError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("kpis"), list):
        raise KPIRegistryError(
            f"{path}: expected a top-level JSON object with a 'kpis' list.")
    entries = data["kpis"]
    if not entries:
        raise KPIRegistryError(f"{path}: 'kpis' list is empty.")

    seen_ids: set[str] = set()
    slots: list[KPISlot] = []
    for i, entry in enumerate(entries):
        label = f"{path} kpis[{i}]"
        if not isinstance(entry, dict):
            raise KPIRegistryError(f"{label}: entry is not a JSON object.")
        missing = [k for k in _REQUIRED_ENTRY_FIELDS if k not in entry]
        if missing:
            raise KPIRegistryError(
                f"{label} (id={entry.get('id', '?')!r}): missing required "
                f"field(s): {', '.join(missing)}.")
        entry_id = entry["id"]
        if not isinstance(entry_id, str) or not entry_id:
            raise KPIRegistryError(f"{label}: 'id' must be a non-empty string.")
        if entry_id in seen_ids:
            raise KPIRegistryError(f"{label}: duplicate id {entry_id!r}.")
        seen_ids.add(entry_id)

        for field in _REQUIRED_STRING_FIELDS:
            if not isinstance(entry[field], str) or not entry[field]:
                raise KPIRegistryError(
                    f"{label} ({entry_id}): '{field}' must be a non-empty string.")

        if entry["kind"] not in _VALID_KINDS:
            raise KPIRegistryError(
                f"{label} ({entry_id}): 'kind' must be one of "
                f"{sorted(_VALID_KINDS)}, got {entry['kind']!r}.")
        if entry["direction"] not in _VALID_DIRECTIONS:
            raise KPIRegistryError(
                f"{label} ({entry_id}): 'direction' must be one of "
                f"{sorted(_VALID_DIRECTIONS)}, got {entry['direction']!r}.")
        if entry["frequency"] not in _VALID_FREQUENCIES:
            raise KPIRegistryError(
                f"{label} ({entry_id}): 'frequency' must be one of "
                f"{sorted(_VALID_FREQUENCIES)}, got {entry['frequency']!r}.")
        if not isinstance(entry["enabled"], bool):
            raise KPIRegistryError(
                f"{label} ({entry_id}): 'enabled' must be a boolean.")

        compute_key = entry["compute"]
        if not isinstance(compute_key, str) or not compute_key:
            raise KPIRegistryError(
                f"{label} ({entry_id}): 'compute' must be a non-empty string.")

        common = dict(id=entry_id, area=entry["area"], metric=entry["metric"],
                      kind=entry["kind"], owner=entry["owner"], target=entry["target"],
                      direction=entry["direction"], frequency=entry["frequency"],
                      enabled=entry["enabled"])

        if compute_key == "manual_gap":
            why = entry.get("why")
            trigger = entry.get("trigger")
            if not isinstance(why, str) or not why:
                raise KPIRegistryError(
                    f"{label} ({entry_id}): compute:'manual_gap' requires a "
                    "non-empty 'why'.")
            if not isinstance(trigger, str) or not trigger:
                raise KPIRegistryError(
                    f"{label} ({entry_id}): compute:'manual_gap' requires a "
                    "non-empty 'trigger'.")
            slots.append(KPISlot(**common, compute=None, why=why, trigger=trigger))
            continue

        compute_fn = _COMPUTE_FUNCTIONS.get(compute_key)
        if compute_fn is None:
            raise KPIRegistryError(
                f"{label} ({entry_id}): unknown compute key {compute_key!r} — "
                f"known keys: {sorted(_COMPUTE_FUNCTIONS)}, or the literal "
                "'manual_gap' for a not-yet-instrumented KPI.")
        slots.append(KPISlot(**common, compute=compute_fn))
    return tuple(slots)


# ============================================================================
# The registry — every KPI line the ledger/scorecard renders, loaded from
# docs/metrics/kpi_registry.json (CLAUDE.md areas: Ingestion/Coverage,
# Extraction Correctness, Cost-efficiency, Brain quality, UX/consumer,
# Trust/safety). Disabled entries stay in the file (so re-enabling is a
# one-line edit) but are filtered out of what the scorecard renders.
# ============================================================================
ALL_KPI_SLOTS: tuple[KPISlot, ...] = load_kpi_registry(DEFAULT_KPI_REGISTRY)
KPI_SLOTS: tuple[KPISlot, ...] = tuple(s for s in ALL_KPI_SLOTS if s.enabled)

# The canonical list of named gaps, rendered by --print, for the
# Goodhart-honesty control (docs/strategy/ONE_LIVE_KPI_FRAMEWORK_v1.md).
# (Named *_SLOTS, distinct from the NOT_YET_INSTRUMENTED status constant above
# — a prior version of this module shadowed the constant with this tuple.)
NOT_YET_INSTRUMENTED_SLOTS: tuple[KPISlot, ...] = tuple(s for s in KPI_SLOTS if s.is_gap())
MEASURED_SLOTS: tuple[KPISlot, ...] = tuple(s for s in KPI_SLOTS if not s.is_gap())


# ============================================================================
# Rendering
# ============================================================================
def _slot_value(slot: KPISlot) -> KPIValue:
    if slot.compute is None:
        return KPIValue(current=f"not yet instrumented (trigger: {slot.trigger})",
                        status=NOT_YET_INSTRUMENTED, raw=None)
    return slot.compute()


def _print_scorecard(results: list[tuple[KPISlot, KPIValue]]) -> None:
    print("=" * 88)
    print(" OneLive - KPI scorecard - quarterly-prioritization aggregation layer")
    print(" every number is READ from an existing ledger/gate, never recomputed")
    print("=" * 88)
    area = None
    for slot, value in results:
        if slot.area != area:
            area = slot.area
            print(f"-- {area} " + "-" * max(1, 80 - len(area)))
        tag = {ON_TARGET: "ON-TARGET", OFF_TARGET: "OFF-TARGET",
              INFO: "INFO      ", NOT_YET_INSTRUMENTED: "GAP       "}[value.status]
        print(f"  [{tag}] ({slot.kind:<7}) {slot.metric}")
        print(f"            target: {slot.target}")
        print(f"            current: {value.current}")
        print(f"            frequency: {slot.frequency}")
        print(f"            owner: {slot.owner}")
    print("-" * 88)
    n_off = sum(1 for _, v in results if v.status == OFF_TARGET)
    n_gap = sum(1 for _, v in results if v.status == NOT_YET_INSTRUMENTED)
    print(f"  {len(results)} KPIs tracked - {n_off} off-target - {n_gap} not yet "
          "instrumented (see docs/strategy/ONE_LIVE_KPI_FRAMEWORK_v1.md)")
    print("=" * 88)


# ============================================================================
# Ledger read/append (docs/metrics/KPI_LEDGER.md) — mirrors tools/brain_iq.py's
# markdown-table-as-store discipline.
# ============================================================================
class KPILedgerError(Exception):
    """The KPI ledger could not be read/parsed — fail loud."""


def _parse_ledger_row(cells: list[str]) -> dict:
    return {
        "timestamp": cells[0], "area": cells[1], "metric": cells[2],
        "kind": cells[3], "target": cells[4], "current": cells[5],
        "trend": cells[6] if len(cells) > 6 else "", "owner": cells[7] if len(cells) > 7 else "",
    }


def _is_ledger_data_row(stripped: str) -> bool:
    if not stripped.startswith("|"):
        return False
    cells = [c.strip() for c in stripped.strip("|").split("|")]
    if len(cells) < 8:
        return False
    if cells[0].lower() == _TABLE_HEADER_CELLS[0]:
        return False
    if set(cells[1]) <= set("-: "):
        return False
    return True


def load_kpi_ledger_rows(path: pathlib.Path) -> list[dict]:
    """Parsed data rows of docs/metrics/KPI_LEDGER.md, oldest-first.

    An absent file, or a file with zero parseable rows, raises — mirrors
    tools/brain_iq.py's load_ledger_rows (a trend/ratchet needs history to
    compare against; silently returning [] would hide that).
    """
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise KPILedgerError(f"cannot read KPI ledger at {path}: {exc}") from exc
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not _is_ledger_data_row(stripped):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        rows.append(_parse_ledger_row(cells))
    if not rows:
        raise KPILedgerError(
            f"KPI ledger at {path} has no parseable data rows yet.")
    return rows


def _previous_raw(rows: list[dict], area: str, metric: str) -> Optional[float]:
    """The most recent prior row's numeric Current value for (area, metric).

    Reads the FIRST float-looking token out of the Current cell (handles a
    trailing '%'); returns None if no prior row exists or it isn't numeric
    (e.g. it was itself "not yet instrumented").
    """
    match_re = re.compile(r"-?\d+(?:\.\d+)?")
    for row in reversed(rows):
        if row["area"] == area and row["metric"] == metric:
            m = match_re.search(row["current"])
            return float(m.group(0)) if m else None
    return None


def _format_ledger_row(timestamp: str, slot: KPISlot, value: KPIValue,
                       previous_raw: Optional[float]) -> str:
    trend = "-" if value.raw is None else trend_symbol(value.raw, previous_raw)
    current = value.current.replace("|", "/")  # never let a cell break the table
    target = slot.target.replace("|", "/")
    return (f"| {timestamp} | {slot.area} | {slot.metric} | {slot.kind} | "
            f"{target} | {current} | {trend} | {slot.owner} |")


def append_snapshot(path: pathlib.Path, timestamp: str,
                    results: list[tuple[KPISlot, KPIValue]]) -> list[str]:
    """Append one snapshot (one row per KPI slot) into the ledger's table.

    Rows land after the last existing data row (or the table's separator
    line when the table is empty), same insertion discipline as
    tools/brain_iq.py::append_row, so the ledger stays one real table with
    any prose (Goodhart-honesty section, etc.) sitting below it untouched.
    """
    try:
        previous_rows = load_kpi_ledger_rows(path)
    except KPILedgerError:
        previous_rows = []

    new_lines = [
        _format_ledger_row(timestamp, slot, value,
                           _previous_raw(previous_rows, slot.area, slot.metric))
        for slot, value in results
    ]

    lines = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
    insert_at = None
    separator_at = None
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped.startswith("|") and set(stripped.strip("|")) <= set("-: |"):
            separator_at = i
        if _is_ledger_data_row(stripped):
            insert_at = i
    if insert_at is None:
        if separator_at is None:
            raise KPILedgerError(
                f"KPI ledger at {path} has no trend table to append into.")
        insert_at = separator_at
    for offset, line in enumerate(new_lines, start=1):
        lines.insert(insert_at + offset, line)
    pathlib.Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return new_lines


# ============================================================================
# Modes
# ============================================================================
def _compute_all(
    slots: Optional[tuple[KPISlot, ...]] = None,
) -> tuple[list[tuple[KPISlot, KPIValue]], list[str]]:
    """Compute every slot; a per-slot KPIComputeError is collected, not fatal
    to the whole run, so one broken reading doesn't hide every other KPI —
    but it IS surfaced loudly, and --check/--append still fail overall.

    ``slots`` defaults to the module-level KPI_SLOTS (loaded from
    docs/metrics/kpi_registry.json at import time) — pass an explicit tuple
    (e.g. from a temp registry via load_kpi_registry) to compute over a
    different config without touching the global.
    """
    if slots is None:
        slots = KPI_SLOTS
    results: list[tuple[KPISlot, KPIValue]] = []
    errors: list[str] = []
    for slot in slots:
        try:
            results.append((slot, _slot_value(slot)))
        except KPIComputeError as exc:
            errors.append(f"{slot.area} / {slot.metric}: {exc}")
    return results, errors


def _do_print(slots: Optional[tuple[KPISlot, ...]] = None) -> int:
    results, errors = _compute_all(slots)
    _print_scorecard(results)
    if errors:
        for err in errors:
            print(f"kpi_report: COMPUTE ERROR — {err}", file=sys.stderr)
        return 2
    return 0


def _do_check(slots: Optional[tuple[KPISlot, ...]] = None) -> int:
    results, errors = _compute_all(slots)
    if errors:
        for err in errors:
            print(f"kpi_report: COMPUTE ERROR — {err}", file=sys.stderr)
        return 2
    off = [(s, v) for s, v in results if v.status == OFF_TARGET]
    for slot, value in off:
        print(f"kpi_report: OFF-TARGET — {slot.area} / {slot.metric}: "
              f"{value.current} (target: {slot.target})", file=sys.stderr)
    if off:
        return 1
    print(f"kpi_report: PASS — {len(results)} KPIs computed, none off target.")
    return 0


def _do_append(timestamp: str, ledger: pathlib.Path,
               slots: Optional[tuple[KPISlot, ...]] = None) -> int:
    if not timestamp:
        print("kpi_report: INVALID — --append requires a TIMESTAMP (caller/CI "
              "supplies it; code never reads the wall clock).", file=sys.stderr)
        return 2
    results, errors = _compute_all(slots)
    if errors:
        for err in errors:
            print(f"kpi_report: COMPUTE ERROR — {err}", file=sys.stderr)
        return 2
    try:
        new_lines = append_snapshot(ledger, timestamp, results)
    except KPILedgerError as exc:
        print(f"kpi_report: {exc}", file=sys.stderr)
        return 2
    print(f"kpi_report: APPENDED {len(new_lines)} rows to {ledger}:")
    for line in new_lines:
        print(f"  {line}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", type=pathlib.Path, default=DEFAULT_LEDGER,
                        help="KPI ledger path for --append (default: "
                             "docs/metrics/KPI_LEDGER.md)")
    parser.add_argument("--registry", type=pathlib.Path, default=DEFAULT_KPI_REGISTRY,
                        help="KPI registry JSON path (default: docs/metrics/"
                             "kpi_registry.json) — the editable list of "
                             "tracked KPIs/targets/frequencies")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--print", action="store_true", dest="do_print",
                      help="compute + print the scorecard (default)")
    mode.add_argument("--append", metavar="TIMESTAMP", default=None,
                      help="append one snapshot to docs/metrics/KPI_LEDGER.md")
    mode.add_argument("--check", action="store_true",
                      help="exit 1 if any computed KPI is off target")
    args = parser.parse_args(argv)

    if args.registry == DEFAULT_KPI_REGISTRY:
        slots = KPI_SLOTS  # already loaded at import time; avoid a redundant read
    else:
        try:
            all_slots = load_kpi_registry(args.registry)
        except KPIRegistryError as exc:
            print(f"kpi_report: REGISTRY ERROR — {exc}", file=sys.stderr)
            return 2
        slots = tuple(s for s in all_slots if s.enabled)

    if args.append is not None:
        return _do_append(args.append, args.ledger, slots)
    if args.check:
        return _do_check(slots)
    return _do_print(slots)


if __name__ == "__main__":
    raise SystemExit(main())
