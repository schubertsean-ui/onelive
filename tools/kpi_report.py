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

Modes:
  --print              compute + print the scorecard (no write; default)
  --append TIMESTAMP   append one snapshot's rows to docs/metrics/KPI_LEDGER.md
                       (TIMESTAMP is caller/CI-supplied — this module never
                       reads the wall clock)
  --check              exit 1 if any COMPUTED (not gap) KPI is OFF_TARGET

Exit codes (tools/README.md convention):
  0 = ok (printed / appended / --check found nothing off target)
  1 = --check found an off-target KPI
  2 = could not compute something required — fail loud, never invent a number

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

ON_TARGET = "ON_TARGET"
OFF_TARGET = "OFF_TARGET"
INFO = "INFO"
NOT_YET_INSTRUMENTED = "NOT_YET_INSTRUMENTED"

# The machine-readable table marker for docs/metrics/KPI_LEDGER.md.
_TABLE_HEADER_CELLS = ("timestamp", "area", "metric", "kind", "target",
                       "current", "trend", "owner")


class KPIComputeError(Exception):
    """Raised when a KPI that SHOULD be computable could not be — fail loud.

    Distinct from a legitimate OFF_TARGET result (a real, informative
    measurement that just misses its target): this means the measurement
    itself could not be taken (file missing/unparseable, a subprocess could
    not run at all) and the tool refuses to guess a number.
    """


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
    """

    area: str
    metric: str
    kind: str  # "leading" | "lagging"
    owner: str
    target: str
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
# The registry — every KPI line the ledger/scorecard renders, one commit's
# worth of ground truth per Area (CLAUDE.md areas: Ingestion/Coverage,
# Extraction Correctness, Cost-efficiency, Brain quality, UX/consumer,
# Trust/safety).
# ============================================================================
KPI_SLOTS: tuple[KPISlot, ...] = (
    # --- Ingestion / Coverage -------------------------------------------------
    KPISlot(area="Ingestion/Coverage", metric="Source catalog size (enabled sources)",
            kind="lagging", owner="ingestion loop (Sentinel)",
            target=">=120 sources (R-007)",
            why="requires a live DB connection (ONELIVE_DB_DSN); this tool is "
                "stdlib-only/no-network by design",
            trigger="a session with ONELIVE_DB_DSN present runs `select count(*) "
                    "from source where enabled` and folds it in"),
    KPISlot(area="Ingestion/Coverage", metric="Scheduled cron slot-fire density",
            kind="leading", owner="ingestion loop (Sentinel)",
            target=">=80% of eligible 20-min slots fire (R-023)",
            why="requires the read-only healthchecks.io API + GitHub Actions "
                "API, neither reachable from this offline tool",
            trigger="a session with HEALTHCHECKS_API_KEY_RO + `gh` computes the "
                    "trailing 24h slot-fire rate and folds it in"),

    # --- Extraction Correctness (zero-escaped-defects — the reputation metric)
    KPISlot(area="Extraction Correctness",
            metric="Field-level hallucination rate @ last certification",
            kind="lagging", owner="extraction loop / evaluator gate",
            target=f"<= {HALLUCINATION_MAX:.0%} (one-way ratchet, KAIZEN.md §M7)",
            compute=_kpi_hallucination_rate),
    KPISlot(area="Extraction Correctness",
            metric="Recall @ last certification (anti-gaming pair)",
            kind="leading", owner="extraction loop / evaluator gate",
            target=f">= {RECALL_MIN:.0%}", compute=_kpi_recall),
    KPISlot(area="Extraction Correctness", metric="All-time escaped defects (M3)",
            kind="lagging", owner="Kaizen / evaluator gate",
            target="0, absolute (Deming zero-escaped-defects goal)",
            compute=_kpi_escaped_defects),
    KPISlot(area="Extraction Correctness", metric="Production trailing hallucination rate",
            kind="lagging", owner="extraction loop / Kaizen M7 ratchet",
            target="tracked weekly; ratchets the certified bar down when it "
                   "holds at <= half the current bar for 4 cycles",
            why="KAIZEN.md §M7 names admin-review verdicts + user reports as "
                "the production-sampling input, but no code yet tallies "
                "confirmed extraction errors against total assertions",
            trigger="first batch of admin-review verdicts and/or user "
                    "\"Something off?\" reports flows and a script tallies "
                    "confirmed errors / total field assertions"),

    # --- Cost-efficiency -------------------------------------------------------
    KPISlot(area="Cost-efficiency", metric="Cost per verified published event (§14.2)",
            kind="lagging", owner="FinOps / model router",
            target="no baseline yet — §14.2: 'it becomes your own baseline'",
            why="no live cost meter exists yet; tokens+fetch+ops-minutes per "
                "promoted event is not logged anywhere",
            trigger="first real scheduled ingestion run with per-event cost "
                    "logging wired (§14.2) and at least one promoted event to "
                    "divide by"),
    KPISlot(area="Cost-efficiency", metric="Loop-stage model routing wired (no hardcoded ids)",
            kind="leading", owner="model_router / Generator",
            target="every declared stage resolves via tools/model_router.py",
            compute=_kpi_model_routing),

    # --- Brain quality -----------------------------------------------------
    KPISlot(area="Brain quality", metric="Brain IQ composite (knowledge/efficiency/learning)",
            kind="lagging", owner="brain loop",
            target="one-way ratchet: knowledge & efficiency never regress "
                   "(tools/brain_iq.py --check, wired into tools/validate)",
            compute=_kpi_brain_iq),

    # --- UX / consumer -------------------------------------------------------
    KPISlot(area="UX/consumer", metric="Web app test suite (vitest) green",
            kind="leading", owner="web loop",
            target="100% green on every web PR",
            why="a different toolchain (Node/vitest); this stdlib-only Python "
                "tool does not shell into npm to keep --no-network determinism",
            trigger="a stdlib-safe reader of the web CI job's test-count "
                    "artifact/log is wired into this tool"),
    KPISlot(area="UX/consumer", metric="Real user engagement / retention",
            kind="lagging", owner="web loop / growth",
            target="TBD — defined at public launch (SS15 growth, PROPOSAL)",
            why="the site is behind the Clerk stealth gate; there is no public "
                "traffic to measure yet",
            trigger="public launch + analytics wired (Vercel Analytics, TODOS "
                    "P1) define and start reporting real engagement metrics"),

    # --- Trust / safety ------------------------------------------------------
    KPISlot(area="Trust/safety", metric="trust_gate clean (trust invariants hold)",
            kind="lagging", owner="gate custody / evaluator",
            target="PASS, always (CLAUDE.md prime directive 1)",
            compute=_kpi_trust_gate),
    KPISlot(area="Trust/safety", metric="Kaizen repeat-class alarms active",
            kind="lagging", owner="Kaizen / evaluator gate",
            target="0 active (docs/KAIZEN.md repeat-class rule)",
            compute=_kpi_repeat_class_alarms),
    KPISlot(area="Trust/safety", metric="docs/RECORD.md open deviations",
            kind="leading", owner="gate custody / Generator",
            target="every OPEN row carries a live trigger; not a fixed number",
            compute=_kpi_record_open_rows),
    KPISlot(area="Trust/safety", metric="pytest suite size (breadth)",
            kind="leading", owner="Generator",
            target="grows or holds steady; never silently shrinks",
            compute=_kpi_pytest_count),
)

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
def _compute_all() -> tuple[list[tuple[KPISlot, KPIValue]], list[str]]:
    """Compute every slot; a per-slot KPIComputeError is collected, not fatal
    to the whole run, so one broken reading doesn't hide every other KPI —
    but it IS surfaced loudly, and --check/--append still fail overall."""
    results: list[tuple[KPISlot, KPIValue]] = []
    errors: list[str] = []
    for slot in KPI_SLOTS:
        try:
            results.append((slot, _slot_value(slot)))
        except KPIComputeError as exc:
            errors.append(f"{slot.area} / {slot.metric}: {exc}")
    return results, errors


def _do_print() -> int:
    results, errors = _compute_all()
    _print_scorecard(results)
    if errors:
        for err in errors:
            print(f"kpi_report: COMPUTE ERROR — {err}", file=sys.stderr)
        return 2
    return 0


def _do_check() -> int:
    results, errors = _compute_all()
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


def _do_append(timestamp: str, ledger: pathlib.Path) -> int:
    if not timestamp:
        print("kpi_report: INVALID — --append requires a TIMESTAMP (caller/CI "
              "supplies it; code never reads the wall clock).", file=sys.stderr)
        return 2
    results, errors = _compute_all()
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--print", action="store_true", dest="do_print",
                      help="compute + print the scorecard (default)")
    mode.add_argument("--append", metavar="TIMESTAMP", default=None,
                      help="append one snapshot to docs/metrics/KPI_LEDGER.md")
    mode.add_argument("--check", action="store_true",
                      help="exit 1 if any computed KPI is off target")
    args = parser.parse_args(argv)

    if args.append is not None:
        return _do_append(args.append, args.ledger)
    if args.check:
        return _do_check()
    return _do_print()


if __name__ == "__main__":
    raise SystemExit(main())
