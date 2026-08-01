# -*- coding: utf-8 -*-
# Artifact consistency regression (external review, adopted 2026-08-01):
# every builder must state the same canonical event facts, and no artifact may
# claim what the read pass did not verify. Run after any builder edit.
import sys, glob

SOURCES = {f: open(f, encoding="utf-8").read() for f in glob.glob("make_*.py") + glob.glob("build_*.py")}
errors = []

def require(fname, needle, why):
    if needle not in SOURCES[fname]:
        errors.append(f"{fname}: missing {needle!r} ({why})")

def forbid_everywhere(needle, why, allow_if=None):
    for f, s in SOURCES.items():
        if needle in s and not (allow_if and allow_if in s):
            errors.append(f"{f}: contains {needle!r} ({why})")

# canonical Aug 29 event: 8:00–9:30 pm CDT everywhere it appears
require("make_casestudy.py", "2026-08-29T20:00:00-05:00", "JSON-LD start = 8:00 pm")
require("make_casestudy.py", "2026-08-29T21:30:00-05:00", "JSON-LD end = 9:30 pm")
for f, s in SOURCES.items():
    if "Aug 29" in s and "8:00" in s and "11:" in s.replace("11:00 a", ""):
        pass  # times other than the event window are legitimate (hours etc.)
for f, s in SOURCES.items():
    for bad in ("2026-08-29T23:", "2026-08-29T22:"):
        if bad in s:
            errors.append(f"{f}: Aug 29 end-time drifted to {bad}*")

# venue identity
for f in ("make_casestudy.py", "make_kit2.py"):
    require(f, "1315 S Congress", "venue address consistent")

# never claim what was not verified
forbid_everywhere("InStock", "availability was never verified — the agent does not invent")
forbid_everywhere('"price"', "price was not verifiable from the read")

# crawler naming discipline (claim ledger C-04)
require("make_casestudy.py", "OAI-SearchBot", "ChatGPT search crawler named correctly")
for f, s in SOURCES.items():
    if "GPTBot" in s and "training" not in s:
        errors.append(f"{f}: names GPTBot without the training-decision framing")
    if "largely on Bing" in s:
        errors.append(f"{f}: retired claim C-04 reappeared")

# structured data shape
require("make_casestudy.py", "PostalAddress", "address must be structured")
require("make_casestudy.py", "unique per-event page URL", "one crawlable URL per event")

if errors:
    print("ARTIFACT CONSISTENCY: FAIL")
    for e in errors: print(" -", e)
    sys.exit(1)
print("ARTIFACT CONSISTENCY: PASS —", len(SOURCES), "builder sources checked")
