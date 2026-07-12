"""Real-source sensor probe — Gate 5, honest DB-less slice.

WHAT THIS ANSWERS. The full orchestrator (`worker/run_once.py --real`) is
DB-coupled from the very first stage: `fetch_url` writes a raw_fetch audit row,
and `extract_candidate` writes to the candidate store. Both are by design (every
fetch and extraction is auditable). So a genuine `--real` run REQUIRES a live
Postgres + Anthropic key, which the build sandbox does not have. Faking that run
would be exactly the "silent degradation" the operating rules forbid.

What CAN be verified honestly here, on REAL data, with no DB: whether real Austin
source pages (a) fetch at all, and (b) survive the hardened context-hygiene
sensor (`worker.sensors.assess_input`) rather than being silently rejected as
truncated / mojibake / boilerplate / injection. Sensor rejection is the first
real-world failure mode that would make a source invisible, and it is the one we
can measure without the DB. This probe reuses the SAME assess_input the
orchestrator uses (no second sensor — Sunset Law), so its verdicts are the real
pipeline's verdicts.

WHAT IT DELIBERATELY DOES NOT CLAIM. It does not exercise AI extraction, the
3-way gate, promotion, or hallucination_rate on real data — those need the prod
DB + model and are a Gate-9 founder-environment decision, documented as such in
docs/launch_plan.md. This probe is scoped, and honest about its scope.

Usage:
  python tools/real_source_probe.py --json sources/austin_metro_catalog.json --sample 20
  python tools/real_source_probe.py --json sources/austin_metro_catalog.json --all
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# Repo root on sys.path when invoked as `python tools/real_source_probe.py`
# (Python puts this file's dir, not the repo root, at sys.path[0]). No-op under
# `python -m tools.real_source_probe` or pytest. Mirrors worker/run_once.py.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from worker.sensors import assess_input

UA = "OneLiveBot/0.1 (+contact: ops@onelive.example)"


@dataclass
class ProbeRow:
    name: str
    url: str
    county: str
    fetched: bool
    http_status: Optional[int]
    sensor_ok: Optional[bool]
    sensor_reason: str
    bytes_len: int = 0


@dataclass
class ProbeReport:
    rows: List[ProbeRow] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.rows)

    @property
    def fetched_ok(self) -> int:
        return sum(1 for r in self.rows if r.fetched)

    @property
    def sensor_passed(self) -> int:
        return sum(1 for r in self.rows if r.sensor_ok is True)

    @property
    def sensor_rejected(self) -> int:
        return sum(1 for r in self.rows if r.sensor_ok is False)


def probe_one(entry: dict, timeout_s: int = 20) -> ProbeRow:
    name = entry.get("name", "<unnamed>")
    url = entry.get("base_url", "")
    county = entry.get("county") or "(metro)"
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout_s)
        status = r.status_code
        if status >= 400:
            return ProbeRow(name, url, county, fetched=False, http_status=status,
                            sensor_ok=None, sensor_reason=f"http {status}")
        # Decode as the pipeline would receive text.
        text = r.text or ""
        content_type = r.headers.get("Content-Type")
        reading = assess_input(text=text, content_type=content_type)
        return ProbeRow(name, url, county, fetched=True, http_status=status,
                        sensor_ok=reading.ok, sensor_reason=reading.reason,
                        bytes_len=len(text))
    except requests.RequestException as exc:
        # Reported loudly per row; one bad source never aborts the probe.
        return ProbeRow(name, url, county, fetched=False, http_status=None,
                        sensor_ok=None, sensor_reason=f"{type(exc).__name__}: {exc}")


def run_probe(entries: List[dict], timeout_s: int = 20) -> ProbeReport:
    report = ProbeReport()
    for e in entries:
        report.rows.append(probe_one(e, timeout_s=timeout_s))
    return report


def format_report(report: ProbeReport) -> str:
    lines: List[str] = []
    lines.append("=== OneLive Real-Source Sensor Probe (Gate 5, DB-less slice) ===")
    lines.append(f"probed: {report.n}")
    fetch_pct = (100.0 * report.fetched_ok / report.n) if report.n else 0.0
    lines.append(f"fetched OK: {report.fetched_ok}/{report.n} ({fetch_pct:.0f}%)")
    if report.fetched_ok:
        pass_pct = 100.0 * report.sensor_passed / report.fetched_ok
        lines.append(f"sensor PASSED (of fetched): {report.sensor_passed}/{report.fetched_ok} "
                     f"({pass_pct:.0f}%)")
        lines.append(f"sensor REJECTED (of fetched): {report.sensor_rejected}/{report.fetched_ok}")
    lines.append("")
    # Show every failure/rejection loudly; passes summarized.
    for r in report.rows:
        if not r.fetched:
            lines.append(f"  [FETCH-FAIL] {r.county:11s} {r.name}: {r.sensor_reason}")
        elif r.sensor_ok is False:
            lines.append(f"  [SENSOR-REJECT] {r.county:11s} {r.name}: {r.sensor_reason}")
    lines.append("")
    lines.append("NOTE: this probe verifies fetch + hardened sensor on REAL source pages only. "
                 "AI extraction, the 3-way gate, promotion, and hallucination_rate on real data "
                 "require the prod Postgres + model (Gate 9 founder-environment decision).")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Probe real source pages through the hardened sensor")
    ap.add_argument("--json", required=True, help="Path to a source catalog JSON array")
    ap.add_argument("--sample", type=int, default=0, help="Randomly sample N sources (0 = use --all)")
    ap.add_argument("--all", action="store_true", help="Probe every source (slow; polite delay applies)")
    ap.add_argument("--seed", type=int, default=71126, help="Sampling seed (reproducible)")
    ap.add_argument("--timeout", type=int, default=20)
    args = ap.parse_args(argv)

    path = Path(args.json)
    if not path.exists():
        print(f"ERROR: catalog not found: {path}", file=sys.stderr)
        return 2
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, list) or not entries:
        print("ERROR: catalog must be a non-empty JSON array", file=sys.stderr)
        return 2

    if args.sample and not args.all:
        rng = random.Random(args.seed)
        entries = rng.sample(entries, min(args.sample, len(entries)))
    elif not args.all and not args.sample:
        print("ERROR: pass --sample N or --all", file=sys.stderr)
        return 2

    report = run_probe(entries, timeout_s=args.timeout)
    print(format_report(report))
    # Non-zero only on catastrophic fetch failure (>50% unreachable), which would
    # indicate a network/environment problem, not per-source noise.
    if report.n and report.fetched_ok / report.n < 0.5:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
