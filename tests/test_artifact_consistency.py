"""The deliverable cross-artifact consistency gate, in the normal pytest sweep.

Founder-ratified 2026-08-01 ("adopt their meta-recommendation (an automated
cross-artifact consistency test)" — decision record
docs/memory/decisions/2026-08-01_truth-states-v2-and-hypothesis-split.md).
The check itself lives with the deliverable sources
(docs/strategy/marketing_model/check_artifacts.py) so it runs standalone
during deliverable work; this wrapper makes tools/validate fail when any
builder source contradicts canonical event facts, retired claims (ledger
C-03/C-04), claim scopes (C-01), the six-state truth model, or the
registry-bound channel-status disclosure in the customer document.
"""
import subprocess
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent.parent / "docs" / "strategy" / "marketing_model"


def test_deliverable_artifact_consistency():
    assert (MODEL_DIR / "check_artifacts.py").is_file(), (
        "check_artifacts.py missing — the consistency gate is ratified canon; "
        "removing it is a gate-threshold relaxation (founder-crucial)"
    )
    proc = subprocess.run(
        [sys.executable, "-I", "check_artifacts.py"],
        cwd=MODEL_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, (
        "deliverable artifact consistency FAILED:\n" + proc.stdout + proc.stderr
    )
    # the checker must actually have scanned sources — an empty glob passing
    # silently would be a check that cannot fail
    assert "builder sources checked" in proc.stdout
    n = int(proc.stdout.rsplit("—", 1)[1].split()[0])
    assert n >= 10, f"only {n} builder sources scanned — glob broke?"
