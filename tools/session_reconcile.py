#!/usr/bin/env python3
"""Session-start reconciliation — make STATE.md trustworthy before any work.

WHY THIS EXISTS
Continuity across sessions fails not from missing docs but from *unverified trust*
in them. A prior session left STATE.md asserting "PRs not merged / tables 0 rows"
after those were already done; only a manual check caught it. This script turns
that manual check into a mechanical, tiered guarantee (our Kaizen response to that
defect):

  - BENIGN drift (STATE.md agrees with, or is merely silent about, live state)
    -> auto-heal the machine-readable ground-truth block in STATE.md, log it,
       and proceed. No friction on the common path.
  - MATERIAL contradiction (STATE.md asserts X, live ground truth says NOT X, and
    acting on X could cause a wrong decision) -> HARD STOP (exit code 2). The
    session must resolve it before doing anything else.

It applies the project rule "findings are claims until verified" to STATE.md
itself. It also FAILS LOUDLY on things it could not verify (missing `gh`, no DB
access) rather than silently passing — an unverifiable claim is not a clean bill.

GROUND TRUTH SOURCES
  - git: current branch + local/remote heads (subprocess `git`)
  - PRs: `gh pr list --state all --json number,state,title`
  - migrations + core-table row counts: Supabase. Two paths:
      1. ONELIVE_DB_DSN set -> query directly via psycopg2 (preferred in CI/worker)
      2. otherwise -> emit the exact SQL to run via the Supabase connector and
         mark those facts UNVERIFIED (loud), so a human/agent supplies them.

STATE.md CONTRACT
STATE.md must contain a fenced block delimited by:
  <!-- GROUND_TRUTH:BEGIN -->
  ```json
  { ...machine-readable snapshot... }
  ```
  <!-- GROUND_TRUTH:END -->
If absent, the script creates it (benign) from whatever it could verify.

EXIT CODES
  0 = clean or only benign drift (auto-healed)
  2 = material contradiction OR unverifiable critical fact -> session must act
  3 = usage/environment error
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

BEGIN = "<!-- GROUND_TRUTH:BEGIN -->"
END = "<!-- GROUND_TRUTH:END -->"

# Core tables whose row counts are load-bearing for "has the pipeline run?".
CORE_TABLES = ["source", "event", "event_candidate", "candidate_evidence"]


# --- shell helpers -----------------------------------------------------------
def _run(cmd):
    """Run a command, return (ok, stdout, stderr). Never raises."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return p.returncode == 0, p.stdout.strip(), p.stderr.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return False, "", str(exc)


# --- live ground-truth gatherers --------------------------------------------
def gather_git():
    ok, branch, _ = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    _, head, _ = _run(["git", "rev-parse", "--short", "HEAD"])
    return {"verified": ok, "branch": branch if ok else None,
            "head": head or None}


def gather_prs():
    ok, out, err = _run(["gh", "pr", "list", "--state", "all", "--limit", "100",
                         "--json", "number,state,title"])
    if not ok:
        return {"verified": False, "error": err or "gh unavailable", "prs": None}
    try:
        prs = json.loads(out) if out else []
    except json.JSONDecodeError as exc:
        return {"verified": False, "error": f"bad gh json: {exc}", "prs": None}
    return {"verified": True, "prs": prs}


def gather_db(dsn):
    """Return migrations + row counts if a DSN is available; else UNVERIFIED with
    the exact SQL to run via the Supabase connector (loud, not silent)."""
    if not dsn:
        return {
            "verified": False,
            "reason": "ONELIVE_DB_DSN not set",
            "run_via_connector": {
                "migrations": "select version, name from supabase_migrations.schema_migrations order by version;",
                "row_counts": "select " + ", ".join(
                    f"(select count(*) from {t}) as {t}" for t in CORE_TABLES) + ";",
            },
            "migrations": None,
            "row_counts": None,
        }
    try:
        import psycopg2
    except ImportError:
        return {"verified": False, "reason": "psycopg2 not installed",
                "migrations": None, "row_counts": None}
    try:
        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("select version from supabase_migrations.schema_migrations order by version;")
                migs = [r[0] for r in cur.fetchall()]
                counts = {}
                for t in CORE_TABLES:
                    cur.execute(f"select count(*) from {t};")
                    counts[t] = cur.fetchone()[0]
        return {"verified": True, "migrations": migs, "row_counts": counts}
    except Exception as exc:  # noqa: BLE001 — reported loudly, not swallowed
        return {"verified": False, "reason": f"db query failed: {exc}",
                "migrations": None, "row_counts": None}


# --- STATE.md block I/O ------------------------------------------------------
def read_state_block(text):
    m = re.search(re.escape(BEGIN) + r"\s*```json\s*(.*?)\s*```\s*" + re.escape(END),
                  text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}


def write_state_block(text, snapshot):
    block = (BEGIN + "\n```json\n" +
             json.dumps(snapshot, indent=2, sort_keys=True) +
             "\n```\n" + END)
    pattern = re.escape(BEGIN) + r".*?" + re.escape(END)
    if re.search(pattern, text, re.DOTALL):
        return re.sub(pattern, block, text, flags=re.DOTALL)
    # Insert after the first heading line.
    lines = text.splitlines()
    insert_at = 1 if lines and lines[0].startswith("#") else 0
    lines.insert(insert_at, "\n" + block + "\n")
    return "\n".join(lines)


# --- drift classification ----------------------------------------------------
def classify(prev, live):
    """Compare the previous STATE.md snapshot against live ground truth.
    Returns (material, benign, unverified) lists of human-readable strings."""
    material, benign, unverified = [], [], []
    prev = prev or {}

    # PRs — a claimed-merged PR that is actually open (or vice versa) is material.
    if not live["prs"]["verified"]:
        unverified.append(f"PR state UNVERIFIED ({live['prs'].get('error')})")
    else:
        live_state = {p["number"]: p["state"].lower() for p in live["prs"]["prs"]}
        prev_state = {int(k): str(v).lower() for k, v in (prev.get("prs") or {}).items()}
        for num, ps in prev_state.items():
            ls = live_state.get(num)
            if ls is None:
                benign.append(f"STATE.md references PR #{num} not found live")
            elif ps != ls:
                material.append(f"PR #{num}: STATE.md says '{ps}', live is '{ls}'")

    # Row counts — "0 rows" claim vs populated table is material (pipeline status).
    if not live["db"]["verified"]:
        unverified.append(f"DB facts UNVERIFIED ({live['db'].get('reason')})")
    else:
        prev_counts = prev.get("row_counts") or {}
        for t, live_n in live["db"]["row_counts"].items():
            if t in prev_counts and int(prev_counts[t]) != int(live_n):
                # Zero-vs-nonzero is the decision-changing case -> material.
                if (int(prev_counts[t]) == 0) != (int(live_n) == 0):
                    material.append(f"table {t}: STATE.md says {prev_counts[t]} rows, live {live_n}")
                else:
                    benign.append(f"table {t}: count changed {prev_counts[t]} -> {live_n}")

    # Migrations — a migration STATE.md calls "not applied" that IS applied is benign
    # to heal; the reverse (claimed applied, actually missing) is material.
    if live["db"]["verified"]:
        live_migs = set(live["db"]["migrations"] or [])
        for m in (prev.get("applied_migrations") or []):
            if m not in live_migs:
                material.append(f"migration {m}: STATE.md claims applied, not present live")

    return material, benign, unverified


def build_snapshot(live):
    snap = {"reconciled_at": datetime.now(timezone.utc).isoformat(),
            "git": {"branch": live["git"]["branch"], "head": live["git"]["head"]}}
    if live["prs"]["verified"]:
        snap["prs"] = {str(p["number"]): p["state"].lower() for p in live["prs"]["prs"]}
    if live["db"]["verified"]:
        snap["applied_migrations"] = live["db"]["migrations"]
        snap["row_counts"] = live["db"]["row_counts"]
    return snap


def main():
    ap = argparse.ArgumentParser(description="Session-start reconciliation.")
    ap.add_argument("--state", default="STATE.md")
    ap.add_argument("--dsn", default=os.getenv("ONELIVE_DB_DSN"))
    ap.add_argument("--heal", action="store_true",
                    help="Rewrite STATE.md's ground-truth block from live data "
                         "when only benign drift is found.")
    args = ap.parse_args()

    if not os.path.exists(args.state):
        print(f"ERROR: {args.state} not found", file=sys.stderr)
        return 3

    with open(args.state, "r", encoding="utf-8") as f:
        text = f.read()

    prev = read_state_block(text)
    live = {"git": gather_git(), "prs": gather_prs(), "db": gather_db(args.dsn)}
    material, benign, unverified = classify(prev, live)

    print("=" * 66)
    print("SESSION RECONCILE —", datetime.now(timezone.utc).isoformat())
    print("=" * 66)
    print(f"git: branch={live['git']['branch']} head={live['git']['head']}")
    if live["prs"]["verified"]:
        merged = [p['number'] for p in live['prs']['prs'] if p['state'].lower() == 'merged']
        openn = [p['number'] for p in live['prs']['prs'] if p['state'].lower() == 'open']
        print(f"PRs: merged={merged} open={openn}")
    if live["db"]["verified"]:
        print(f"migrations: {live['db']['migrations']}")
        print(f"row_counts: {live['db']['row_counts']}")

    for label, items in (("MATERIAL CONTRADICTION", material),
                         ("BENIGN DRIFT", benign),
                         ("UNVERIFIED (loud)", unverified)):
        if items:
            print(f"\n[{label}]")
            for it in items:
                print(f"  - {it}")

    if prev is None:
        print("\nNo ground-truth block in STATE.md.")

    # Heal benign drift (and create a missing block) when asked and safe to do so.
    if args.heal and not material:
        new_text = write_state_block(text, build_snapshot(live))
        if new_text != text:
            with open(args.state, "w", encoding="utf-8") as f:
                f.write(new_text)
            print("\n[healed] STATE.md ground-truth block refreshed from live data.")

    if material:
        print("\nRESULT: MATERIAL CONTRADICTION — resolve in STATE.md before working. (exit 2)")
        return 2
    if unverified:
        print("\nRESULT: some critical facts UNVERIFIED — verify via the Supabase "
              "connector (SQL above) before trusting STATE.md. (exit 2)")
        return 2
    print("\nRESULT: clean (or benign drift only). Safe to proceed. (exit 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
