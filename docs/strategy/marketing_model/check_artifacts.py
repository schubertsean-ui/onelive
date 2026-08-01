# -*- coding: utf-8 -*-
# Artifact consistency regression (external review, adopted 2026-08-01;
# formalized as a standing gate by founder ratification the same day —
# tests/test_artifact_consistency.py runs this inside the pytest sweep):
# every builder must state the same canonical event facts, and no artifact may
# claim what the read pass did not verify. Run after any builder edit.
import sys, glob, re

SOURCES = {f: open(f, encoding="utf-8").read() for f in glob.glob("make_*.py") + glob.glob("build_*.py")}
errors = []

def require(fname, needle, why):
    if needle not in SOURCES[fname]:
        errors.append(f"{fname}: missing {needle!r} ({why})")

def forbid_everywhere(needle, why, allow_if=None):
    for f, s in SOURCES.items():
        if needle in s and not (allow_if and allow_if in s):
            errors.append(f"{f}: contains {needle!r} ({why})")

# canonical Aug 29 event: 8:00–9:30 pm CDT everywhere it appears.
# (Evaluator catch, PR #142 r1: the original loop here only `pass`ed and could
# never fail — a check that cannot fail proves nothing. Now: EVERY ISO
# timestamp on the event date, in every source, must be one of the two
# canonical instants; anything else is a drifted or invented time.)
require("make_casestudy.py", "2026-08-29T20:00:00-05:00", "JSON-LD start = 8:00 pm")
require("make_casestudy.py", "2026-08-29T21:30:00-05:00", "JSON-LD end = 9:30 pm")
CANONICAL = {"2026-08-29T20:00:00-05:00", "2026-08-29T21:30:00-05:00"}
for f, s in SOURCES.items():
    for ts in re.findall(r"2026-08-29T[0-9:.+-]+", s):
        if ts not in CANONICAL:
            errors.append(f"{f}: non-canonical Aug 29 timestamp {ts!r} (event is 20:00-21:30 CDT)")

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

# truth-states v2 (founder-ratified 2026-08-01): the model is six-state;
# stray "4-state" wording in deliverable sources is stale canon
forbid_everywhere("4-state", "truth-states v2 is six-state (decision 2026-08-01)")

# claim-ledger population scopes stay attached to their numbers (evaluator
# catches, PR #142 r1: 83% broadened past C-01; r2: 76% broadened past C-08 —
# so the guard now covers the CLASS: every ledger-scoped percentage must
# carry its population keyword wherever it appears)
SCOPED = {
    "83%": ("restaurant", "QSR"),          # C-01 — Uberall restaurant/QSR
    "76%": ("smartphone",),                # C-08 — smartphone local searchers
    "45%": ("survey",),                    # C-02 — surveyed US consumers
    "97%": ("Ahrefs", "crawl"),            # C-05 — Ahrefs crawl sample
}
for f, s in SOURCES.items():
    for pct, keywords in SCOPED.items():
        for m in re.finditer(re.escape(pct) + r"[^.\n]{0,140}", s):
            frag = m.group(0)
            if not any(k.lower() in frag.lower() for k in keywords):
                errors.append(f"{f}: {pct} claim without its ledger population scope {keywords}: {frag[:90]!r}")

# positive six-state guard (evaluator suggestion, PR #142 r2): a source that
# enumerates the confidence-state model must anchor it to Truth States v2 —
# stating only the observed subset as if it were the model is the same
# scope-drift class as the percentages above
for f, s in SOURCES.items():
    if "CONFIRMED / LIKELY / UNVERIFIED" in s and not ("six-state" in s or "Truth States v2" in s):
        errors.append(f"{f}: enumerates confidence states without anchoring to the six-state model (Truth States v2)")

# connector honesty (evaluator catch, PR #142 r1): the customer document's
# channel table must be registry-bound — it may not present PLANNED
# connectors as live. The builder must carry the pilot-status disclosure
# verbatim and must not use bare "Connected" wording.
require("build_customer.py", "connector registry", "channel table must cite the registry")
require("build_customer.py", "in build", "channel statuses must disclose build status")
if re.search(r"<td>Connected", SOURCES.get("build_customer.py", "")):
    errors.append("build_customer.py: presents a channel as 'Connected' — registry says PLANNED; use design-preview wording")

if errors:
    print("ARTIFACT CONSISTENCY: FAIL")
    for e in errors: print(" -", e)
    sys.exit(1)
print("ARTIFACT CONSISTENCY: PASS —", len(SOURCES), "builder sources checked")
