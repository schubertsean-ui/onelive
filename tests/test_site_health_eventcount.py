"""`site_health.yml`'s event-count verdict must fail closed on any unreadable value.

`CLASS:fail-open-on-uncaught-invalid-input` (gemini/dataflow-taint, PR #76). The
`case "$COUNT"` statement handled `0)` and `UNKNOWN|UNPARSEABLE)` and had no
catch-all, so a negative number, a non-numeric string, `null`, or a JSON fragment
fell straight through and the workflow exited 0 — reporting a PASSING go/no-go
check over a number it could not interpret. This workflow is cited as the go-live
verifier by `docs/V1.md`, `TODOS.md` and bar row H7, so that is the worst place in
the repo for a fail-open.

The case arms are executed here with `bash`, not pattern-matched as text: a test
that greps for `*[!0-9]*` would pass on a broken arm placed after the catch-all.
"""
from __future__ import annotations

import pathlib
import subprocess

import pytest
import yaml

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_WORKFLOW = _ROOT / ".github" / "workflows" / "site_health.yml"


def _case_block() -> str:
    """The `case "$COUNT"` block, lifted verbatim from the workflow."""
    doc = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    body = next(s["run"] for s in doc["jobs"]["check"]["steps"]
                if "run" in s and "event_count" in s["run"])
    lines = body.splitlines()
    start = next(i for i, ln in enumerate(lines) if 'case "$COUNT" in' in ln)
    end = next(i for i, ln in enumerate(lines[start:], start)
               if ln.strip() == "esac")
    return "\n".join(lines[start:end + 1])


def _verdict(count: str) -> int:
    """Run the real case block against a value; return its exit status."""
    script = "set -u\nCOUNT=\"$1\"\n" + _case_block() + "\nexit 0\n"
    proc = subprocess.run(["bash", "-c", script, "bash", count],
                          capture_output=True, text=True, timeout=60)
    return proc.returncode


@pytest.mark.parametrize("count", [
    "-5",            # negative: not a real count
    "banana",        # non-numeric
    "null",          # JSON null leaking through as text
    "1.5",           # a float is not an event count
    "1e3",           # scientific notation
    " 12",           # leading whitespace — not a bare integer
    "12 ",           # trailing whitespace
    "",              # empty
    "{}",            # a JSON fragment
    "NaN",
])
def test_an_unreadable_event_count_fails_closed(count):
    assert _verdict(count) != 0, (
        f"event_count {count!r} exited 0 — the go/no-go verifier reported a PASS "
        f"over a value it cannot interpret")


@pytest.mark.parametrize("count", ["1", "42", "1532", "999999"])
def test_a_real_positive_count_passes(count):
    """The fix must not turn the gate into a permanent red — that is how a gate
    gets disabled rather than obeyed."""
    assert _verdict(count) == 0, f"event_count {count!r} should pass"


def test_zero_still_fails_with_its_own_message():
    """Unchanged property: a live site over an empty feed is a worse first
    impression than no site, so zero fails on its own arm rather than via the
    catch-all — the distinction matters because the remedy differs (run the
    importer, versus fix the endpoint)."""
    assert _verdict("0") != 0
    assert "The site is up and the feed is EMPTY" in _case_block()


@pytest.mark.parametrize("count", ["UNKNOWN", "UNPARSEABLE"])
def test_the_sentinels_keep_their_own_arm(count):
    assert _verdict(count) != 0
    assert "endpoint's shape changed" in _case_block()


def test_the_catchall_is_reached_and_not_shadowed():
    """A `*)` placed after a catch-all would be dead code. Executing the block is
    what proves the ordering; this asserts the arm exists at all, so a future edit
    that deletes it fails here with a readable reason rather than only via the
    behavioural cases above."""
    block = _case_block()
    assert "*[!0-9]*" in block, "the not-a-number arm is gone"
    assert block.index("*[!0-9]*") > block.index("UNKNOWN|UNPARSEABLE"), \
        "the catch-all must come AFTER the specific sentinels, or it shadows them"
