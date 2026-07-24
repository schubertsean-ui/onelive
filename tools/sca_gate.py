#!/usr/bin/env python3
"""SCA (supply-chain) gate with a managed, self-maintaining exception allowlist.

This replaces the raw `npm audit --omit=dev --audit-level=high` CI step. It
enforces the SAME policy — production dependencies must be clean at high/critical
— but lets a *reviewed, expiring, scoped* allowlist suppress findings we cannot
fix under our own control (an upstream advisory with no released fix), WITHOUT
ever becoming a blanket "ignore problems" switch.

The mechanism and its guarantees are documented in
docs/EXTERNAL_FINDINGS_POLICY.md. The load-bearing safety properties, all
enforced here:

  * SCOPED      — an entry matches an exact (package, ghsa); no wildcards.
  * FAIL-CLOSED — unreadable/malformed allowlist, or unparseable audit output,
                  FAILS the gate. Absence of proof is never a pass.
  * AUTO-RE-BLOCK — an entry suppresses ONLY while npm reports fixAvailable=false
                  for that package. The instant a fix ships, the gate FAILS and
                  the exception must be removed (upgrade instead).
  * TIME-BOXED  — an entry past its `expires` date FAILS the gate.
  * NARROW      — only high/critical PRODUCTION advisories are gated (unchanged
                  policy). This tool NEVER governs trust-invariant gates.

Any high/critical advisory that is not covered by a valid entry FAILS the gate,
exactly as the raw `npm audit` step did.

Usage (CI, from the web app dir after `npm ci`):
    python3 tools/sca_gate.py --web-dir web

Testing (no npm/network — feed fixtures):
    python3 tools/sca_gate.py --audit-json fixture.json \
        --allowlist some.json --today 2026-07-24
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_ALLOWLIST = _REPO_ROOT / "security" / "sca_allowlist.json"
_BLOCKING = ("high", "critical")
# Every field the policy (docs/EXTERNAL_FINDINGS_POLICY.md) promises is
# mechanically required — so an exception cannot pass without its written
# no-fix + exposure justification, owner, and resolution trigger. The gate is
# only as auditable as the fields it actually enforces.
_REQUIRED_ENTRY_FIELDS = (
    "package",
    "ghsa",
    "severity",
    "expires",
    "owner",
    "added",
    "no_fix_reason",
    "operational_exposure",
    "resolution_trigger",
)


class GateError(Exception):
    """Any condition that must FAIL the gate closed."""


def _ghsa_from_url(url: str) -> str:
    return (url or "").rstrip("/").rsplit("/", 1)[-1]


def _load_audit(args) -> dict:
    """Return the parsed `npm audit --omit=dev --json` document, fail-closed."""
    if args.audit_json:
        raw = Path(args.audit_json).read_text(encoding="utf-8")
    else:
        # npm audit exits NON-ZERO when vulnerabilities exist — that is normal
        # and NOT a tool failure. We therefore ignore the exit code and rely on
        # parsing valid JSON. A genuine failure (npm missing, no node_modules,
        # network error) yields non-JSON output and fails closed below.
        proc = subprocess.run(
            ["npm", "audit", "--omit=dev", "--json"],
            cwd=args.web_dir,
            capture_output=True,
            text=True,
        )
        raw = proc.stdout
        if not raw.strip():
            raise GateError(
                "npm audit produced no output — cannot verify supply chain "
                f"(exit {proc.returncode}). stderr:\n{proc.stderr.strip()[:800]}"
            )
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GateError(f"npm audit output was not valid JSON: {exc}")
    if not isinstance(doc, dict) or "vulnerabilities" not in doc:
        raise GateError("npm audit JSON is missing the 'vulnerabilities' object.")
    return doc


def _load_allowlist(path: Path, today: _dt.date) -> dict[tuple[str, str], dict]:
    """Return {(package, ghsa): entry}. Fail-closed on any malformation."""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        # A missing allowlist is not an error — it just means "no exceptions".
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"allowlist {path} is unreadable/unparseable: {exc}")

    entries = doc.get("entries")
    if not isinstance(entries, list):
        raise GateError(f"allowlist {path}: 'entries' must be a list.")

    out: dict[tuple[str, str], dict] = {}
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise GateError(f"allowlist entry #{i} is not an object.")
        missing = [f for f in _REQUIRED_ENTRY_FIELDS if not e.get(f)]
        if missing:
            raise GateError(
                f"allowlist entry #{i} ({e.get('package', '?')}/{e.get('ghsa', '?')}) "
                f"is missing required field(s): {', '.join(missing)}."
            )
        try:
            _dt.date.fromisoformat(e["expires"])
        except ValueError:
            raise GateError(
                f"allowlist entry {e['package']}/{e['ghsa']}: "
                f"'expires' is not an ISO date (YYYY-MM-DD): {e['expires']!r}."
            )
        out[(e["package"], e["ghsa"])] = e
    return out


def _direct_advisories(doc: dict) -> list[dict]:
    """Flatten the blocking (high/critical) *direct* advisory objects.

    Each record: {package, ghsa, severity, fix_available}. `fix_available` is
    read from the node that carries the advisory (npm reports it per node).
    Transitive-only nodes (via = list of package-name strings, e.g. `next`
    inheriting from postcss/sharp) contribute no direct advisory — suppressing
    the ROOT advisory covers everything that inherits it.
    """
    records = []
    for name, node in (doc.get("vulnerabilities") or {}).items():
        if not isinstance(node, dict):
            continue
        for via in node.get("via", []) or []:
            if not isinstance(via, dict):
                continue  # string = transitive reference, handled via its root
            sev = via.get("severity")
            if sev not in _BLOCKING:
                continue
            records.append(
                {
                    "package": name,
                    "ghsa": _ghsa_from_url(via.get("url", "")),
                    "severity": sev,
                    "title": (via.get("title") or "")[:80],
                    "fix_available": node.get("fixAvailable"),
                }
            )
    return records


def evaluate(doc: dict, allowlist: dict[tuple[str, str], dict], today: _dt.date):
    """Return (ok, lines). ok=False means the gate FAILS."""
    advisories = _direct_advisories(doc)
    failures: list[str] = []
    suppressed: list[str] = []
    used: set[tuple[str, str]] = set()

    for a in advisories:
        key = (a["package"], a["ghsa"])
        entry = allowlist.get(key)
        label = f"{a['package']} {a['ghsa']} ({a['severity']}) — {a['title']}"
        if entry is None:
            failures.append(f"UNLISTED high/critical advisory: {label}")
            continue
        used.add(key)
        # AUTO-RE-BLOCK: an entry only holds while there is genuinely no fix.
        if a["fix_available"] is not False:
            failures.append(
                f"FIX NOW AVAILABLE (remove the exception and upgrade): {label} "
                f"— npm fixAvailable={a['fix_available']!r}"
            )
            continue
        # TIME-BOXED.
        exp = _dt.date.fromisoformat(entry["expires"])
        if exp < today:
            failures.append(
                f"EXCEPTION EXPIRED {entry['expires']} (re-review required): {label}"
            )
            continue
        suppressed.append(f"{label}  [expires {entry['expires']}]")

    lines = []
    for s in suppressed:
        lines.append(f"  SUPPRESSED (reviewed exception): {s}")
    unused = sorted(set(allowlist) - used)
    for pkg, ghsa in unused:
        # Non-fatal: an unused entry hides nothing (it matched no live advisory).
        # It just means the vuln is gone and the entry should be cleaned up.
        lines.append(f"  STALE exception (advisory no longer present — remove it): {pkg} {ghsa}")
    for f in failures:
        lines.append(f"  FAIL: {f}")
    return (len(failures) == 0, lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--web-dir", default="web", help="dir to run npm audit in")
    p.add_argument("--allowlist", default=str(_DEFAULT_ALLOWLIST))
    p.add_argument("--audit-json", help="read audit JSON from a file (testing)")
    p.add_argument("--today", help="override today's date YYYY-MM-DD (testing)")
    args = p.parse_args(argv)

    today = (
        _dt.date.fromisoformat(args.today)
        if args.today
        else _dt.date.today()  # noqa: DTZ011 — calendar date is intended
    )

    print("── SCA gate (npm audit, prod, high/critical) ──────────────────")
    try:
        doc = _load_audit(args)
        allowlist = _load_allowlist(Path(args.allowlist), today)
    except GateError as exc:
        print(f"  FAIL (closed): {exc}")
        print("RESULT: FAIL — supply-chain gate could not be verified.")
        return 1

    ok, lines = evaluate(doc, allowlist, today)
    for line in lines:
        print(line)
    if not lines:
        print("  clean — no high/critical production advisories.")
    if ok:
        print("RESULT: PASS — no unmanaged high/critical production advisories.")
        return 0
    print(
        "RESULT: FAIL — high/critical production advisory not covered by a valid "
        "exception. Fix it, or add a reviewed entry per docs/EXTERNAL_FINDINGS_POLICY.md."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
