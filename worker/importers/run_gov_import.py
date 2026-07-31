#!/usr/bin/env python3
"""Run the government open-data (Socrata) venue-truth import: read a dataset
config → fetch each Socrata dataset → normalize rows into venue-truth → upsert
into `venue_truth`. Deterministic, no AI. Runs on GitHub Actions (egress reaches
the portals; the dev sandbox is network-blocked). Fails LOUD on a missing/empty
config or a systemic zero — never a silent no-op.

VENUE enrichment + triangulation anchor, NOT events: this writes only
`venue_truth` and never touches `licensed_event`, `event`, or the AI/promote path.

The dataset config (sources/gov_open_data_datasets.json by default) is a list of:
  {"domain": "data.austintexas.gov", "dataset": "abcd-1234",
   "provider": "socrata", "source_name": "austin_...",
   "field_map": {"name": "col", "capacity": "col", ...},
   "where": "optional SoQL filter", "page_size": 1000}
Real dataset ids + column names must be filled from the live portals (a networked
lookup); an empty config FAILS LOUD rather than pretending to import.

Usage: python -m worker.importers.run_gov_import [--config PATH] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import logging
import pathlib
from collections import Counter

from worker.db_config import resolve_dsn
from worker.importers.socrata import fetch_dataset, normalize_dataset

log = logging.getLogger("gov_import")

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIG = REPO / "sources" / "gov_open_data_datasets.json"


def _load_specs(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        log.error("dataset config %s does not exist — cannot import. Failing closed.", path)
        raise SystemExit(2)
    try:
        specs = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        log.error("dataset config %s is not valid JSON (%s) — failing closed.", path, exc)
        raise SystemExit(2)
    if not isinstance(specs, list) or not specs:
        log.error("dataset config %s has no dataset specs — add real Socrata datasets "
                  "(domain + 4x4 id + field_map). Failing loud, never a silent no-op.", path)
        raise SystemExit(2)
    return specs


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch + normalize + summarize, but do NOT write the DB")
    ap.add_argument("--app-token", default=None,
                    help="optional Socrata app token (raises rate limits; not required)")
    args = ap.parse_args(argv)

    specs = _load_specs(pathlib.Path(args.config))
    log.info("scope: %d government open-data dataset(s) from %s",
             len(specs), pathlib.Path(args.config).name)

    all_norm: list[dict] = []
    per_source: Counter = Counter()
    zero: list[str] = []
    for spec in specs:
        name = str(spec.get("source_name") or spec.get("dataset"))
        try:
            rows = fetch_dataset(
                spec["domain"], spec["dataset"], app_token=args.app_token,
                where=spec.get("where"), select=spec.get("select"),
                page_size=int(spec.get("page_size", 1000)),
                max_rows=int(spec.get("max_rows", 20000)),
            )
        except (OSError, ValueError, KeyError) as exc:
            # One unreachable/misconfigured dataset is logged, not fatal — the
            # others still import (surfaced in the run log, never swallowed).
            log.warning("dataset %-26s FETCH/CONFIG FAILED (%s)", name, exc)
            zero.append(name)
            continue
        norm = normalize_dataset(rows, spec.get("field_map") or {},
                                 provider=spec.get("provider", "socrata"),
                                 source_name=name)
        per_source[name] = len(norm)
        if not norm:
            log.warning("dataset %-26s yielded 0 venue-truth rows — logged, not fatal.", name)
            zero.append(name)
            continue
        log.info("dataset %-26s %5d venue-truth rows", name, len(norm))
        all_norm.extend(norm)

    with_cap = sum(1 for n in all_norm if n.get("capacity") is not None)
    with_lic = sum(1 for n in all_norm if n.get("license_type"))
    log.info("Gov import: %d dataset(s), %d yielded zero, %d rows total (capacity %d, license %d)",
             len(specs), len(zero), len(all_norm), with_cap, with_lic)

    # A real-data importer must not exit green on nothing. ONE empty dataset is
    # tolerated (logged); EVERY dataset empty is a systemic failure.
    if not all_norm:
        log.error("normalized 0 venue-truth rows across ALL %d dataset(s) — bad ids/"
                  "field_maps, an API-shape change, or normalization drift. Failing loud.",
                  len(specs))
        return 3

    if args.dry_run:
        log.info("dry-run: no DB write")
        return 0

    import psycopg2

    from worker.importers.gov_store import upsert_venue_truth
    conn = psycopg2.connect(resolve_dsn())  # fail loud on missing DSN
    try:
        written = upsert_venue_truth(conn, all_norm)
    finally:
        conn.close()
    log.info("upserted %d rows into venue_truth", written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
