#!/usr/bin/env python3
"""Segment registry — validate sources/segments.json and report entity coverage.

Founder-directed 2026-08-06: a comprehensive segment / sub-segment /
sub-sub-segment identity table, with a code assignable to each distinct
venue / org / person.

Two jobs, both mechanical:

1. VALIDATE the registry against the ratified domain list. Layer 1 IS
   `worker.importers.domain_map.DOMAINS` — this file may not fork it, invent a
   domain, or drop one. Codes must be unique and well-formed, and a child's
   code must be prefixed by its parent's, so a code carries its own lineage and
   an orphan is impossible by construction.

2. REPORT coverage over the committed catalog: how many entities carry a
   segment, how many carry a subsegment, how deep the assignment actually goes.
   The point is to make the gap a NUMBER instead of an impression — the same
   reason the denominator census exists.

Honest limit, stated rather than discovered later: today the catalog stores a
`cultural_domain` (layer 1) and nothing below it, so layer-2/3 coverage will
read 0 until assignment happens. That zero is the finding, not a bug in this
tool.

  python3 tools/segment_registry.py [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
REGISTRY = REPO / "sources" / "segments.json"
CATALOG = REPO / "sources" / "master_sources_catalog_120.json"

_SEG_RE = re.compile(r"^[A-Z]{2,3}$")
_SUB_RE = re.compile(r"^[A-Z]{2,3}-[A-Z]{3}$")
_SUBSUB_RE = re.compile(r"^[A-Z]{2,3}-[A-Z]{3}-[A-Z]{3}$")


def load_registry(path: pathlib.Path = REGISTRY) -> dict:
    """Read the registry. An unreadable or malformed registry is a hard error —
    a taxonomy that silently loads empty would mark every entity unclassified
    and look like a data problem instead of a tooling one."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"segment_registry: FAIL — cannot read {path}: {exc}")
    if not isinstance(data.get("segments"), list) or not data["segments"]:
        raise SystemExit(f"segment_registry: FAIL — {path} has no segments")
    return data


def validate(reg: dict) -> list[str]:
    """Return the list of violations. Empty list == valid."""
    try:
        from worker.importers.domain_map import DOMAINS
    except Exception as exc:  # noqa: BLE001 — surfaced, never swallowed
        return [f"cannot import the ratified DOMAINS to check against: {exc}"]

    bad: list[str] = []
    seen: set[str] = set()
    declared_domains: set[str] = set()

    for seg in reg["segments"]:
        code, dom = seg.get("code", ""), seg.get("domain", "")
        if not _SEG_RE.match(code):
            bad.append(f"segment code {code!r} is not 2-3 uppercase letters")
        if code in seen:
            bad.append(f"duplicate code {code!r}")
        seen.add(code)
        if dom not in DOMAINS:
            bad.append(f"segment {code}: domain {dom!r} is not a ratified domain")
        declared_domains.add(dom)

        for sub in seg.get("subsegments", []):
            sc = sub.get("code", "")
            if not _SUB_RE.match(sc):
                bad.append(f"subsegment code {sc!r} is malformed")
            if not sc.startswith(code + "-"):
                bad.append(f"subsegment {sc!r} is not prefixed by its parent {code!r}")
            if sc in seen:
                bad.append(f"duplicate code {sc!r}")
            seen.add(sc)

            for ss in sub.get("sub", []):
                ssc = ss.get("code", "")
                if not _SUBSUB_RE.match(ssc):
                    bad.append(f"sub-subsegment code {ssc!r} is malformed")
                if not ssc.startswith(sc + "-"):
                    bad.append(f"sub-subsegment {ssc!r} is not prefixed by its parent {sc!r}")
                if ssc in seen:
                    bad.append(f"duplicate code {ssc!r}")
                seen.add(ssc)

    missing = set(DOMAINS) - declared_domains
    if missing:
        bad.append(f"ratified domains with no segment: {sorted(missing)}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    reg = load_registry()
    violations = validate(reg)

    segs = reg["segments"]
    n_sub = sum(len(s.get("subsegments", [])) for s in segs)
    n_subsub = sum(len(x.get("sub", [])) for s in segs for x in s.get("subsegments", []))

    print("=" * 70)
    print("SEGMENT REGISTRY")
    print("=" * 70)
    print(f"layer 1 segments        : {len(segs)}")
    print(f"layer 2 subsegments     : {n_sub}")
    print(f"layer 3 sub-subsegments : {n_subsub}")
    print(f"total assignable codes  : {len(segs) + n_sub + n_subsub}")

    if violations:
        print("\nVALIDATION FAILED:")
        for v in violations:
            print(f"  - {v}")
    else:
        print("\nvalidation: OK — codes unique, lineage intact, all 22 ratified domains covered")

    # Coverage over the committed catalog.
    try:
        with open(CATALOG, encoding="utf-8") as fh:
            raw = json.load(fh)
        rows = raw if isinstance(raw, list) else raw.get("sources", [])
    except (OSError, ValueError) as exc:
        print(f"\ncatalog unreadable ({exc}) — coverage UNKNOWN, not 0")
        return 1 if violations else 0

    dom_to_seg = {s["domain"]: s["code"] for s in segs}
    kinds = Counter(r.get("entity_type") or "(unset)" for r in rows)
    have_dom = sum(1 for r in rows if r.get("cultural_domain") in dom_to_seg)
    have_sub = sum(1 for r in rows if r.get("subsegment_code"))
    have_subsub = sum(1 for r in rows if r.get("sub_subsegment_code"))

    print()
    print("=" * 70)
    print(f"CATALOG COVERAGE — {len(rows)} entities")
    print("=" * 70)
    print(f"  layer 1 (segment)        {have_dom:4d}/{len(rows)}  ({100*have_dom//len(rows)}%)")
    print(f"  layer 2 (subsegment)     {have_sub:4d}/{len(rows)}  ({100*have_sub//len(rows)}%)")
    print(f"  layer 3 (sub-subsegment) {have_subsub:4d}/{len(rows)}  ({100*have_subsub//len(rows)}%)")
    print(f"  entity kind: {dict(kinds)}")
    print()
    print("  Layer 2/3 read 0 because the catalog has no field for them yet —")
    print("  that is the gap this registry exists to close, stated as a number.")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({
                "segments": len(segs), "subsegments": n_sub, "sub_subsegments": n_subsub,
                "violations": violations,
                "catalog_entities": len(rows),
                "layer1_assigned": have_dom,
                "layer2_assigned": have_sub,
                "layer3_assigned": have_subsub,
                "entity_kinds": dict(kinds),
            }, fh, indent=2, sort_keys=True)
        print(f"\nwrote {args.json}")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
