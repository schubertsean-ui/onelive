#!/usr/bin/env python3
"""Measure what a blocking prose claim-scanner WOULD fire on, before building it.

Counts lines this branch ADDS to the agent-authored record files, how many are
claim-shaped, and how many of those carry no proof token. A high fire rate
means a noisy gate — one that gets weakened, which is worse than none.

Run from the repo root:
    python docs/session_arcs/evidence/scripts/probe_claim_scan.py
"""
import re
import subprocess

FILES = ["STATE.md", "docs/ONE_LIVE_CHANGE_LOG.md", "docs/metrics/KAIZEN_LEDGER.md",
         "docs/memory/RED_CLASSES.md", "docs/RECORD.md"]
CLAIM = (r"\b(verified|proven|proves?|identical|measured|confirmed|guarantee[sd]?"
         r"|ensures?|never|always|every|all of|none|complete(?:ly)?|fully|first|only)\b")
PROOF = r"(job \d{6,}|run \d{6,}|[0-9a-f]{7,40}\b|\d+\.\d+s|\d+s\b|\d+%|`[^`]+`|tools/|tests/|https?://)"

diff = subprocess.run(["git", "diff", "origin/master", "-U0", "--", *FILES],
                      capture_output=True, text=True).stdout
added = [ln[1:] for ln in diff.splitlines()
         if ln.startswith("+") and not ln.startswith("+++")]
claim = [ln for ln in added if re.search(CLAIM, ln, re.I)]
naked = [ln for ln in claim if not re.search(PROOF, ln)]

print(f"added record lines : {len(added)}")
print(f"  claim-shaped     : {len(claim)}")
print(f"  WITHOUT any proof token (would fire): {len(naked)}")
if claim:
    print(f"  fire rate over claim lines: {100 * len(naked) // len(claim)}%")
