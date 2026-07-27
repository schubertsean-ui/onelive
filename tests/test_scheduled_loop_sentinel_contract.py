"""No scheduled loop ships with half the Sentinel contract.

`CLAUDE.md`: *"Sentry on web, API and worker; a dead-man alarm on every scheduled job.
No scheduled loop ships without both."* The dead-man half has had a mechanism since the
watchdog (`tests/test_watchdog_check.py` binds every scheduled workflow to its
WATCHED/EXPECTED_SOON/EXCLUDED tables). **The Sentry half had none**, and went unmet as
unenforced rules do — R-086.

The halves answer different questions, which is why one is not most of the way there:
the alarm notices the loop STOPPED; Sentry reports what broke while it still ran. A loop
failing every execution but still executing trips no alarm.

THE LIMIT: this asserts WIRING, not delivery — that the DSN reaches the process and the
process initialises the SDK. Proving Sentry received an event needs a real DSN and a real
failure (R-001).
"""
from __future__ import annotations

import pathlib
import re

import pytest
import yaml

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_WORKFLOW_DIR = _ROOT / ".github" / "workflows"

# Scheduled workflows that run NO application code, so there is nothing for Sentry to
# instrument. Each needs a reason, and the reason has to be about the workflow's own
# nature — never "it does not have a DSN yet", which is the thing being fixed.
_NO_APP_CODE = {
    "watchdog.yml": "the alarm itself — instrumenting the watchdog with the thing "
                    "that watches for silence would make its failure invisible to "
                    "the layer that is supposed to be independent of the app",
    "dependency-hygiene.yml": "runs npm/pip audit tooling, not worker code; its "
                              "findings ARE its output and a crash fails the job",
    # Found by this test on its first run, and named by nobody in review — which is
    # the derived-over-enumerated argument making itself again. Exempt on its nature,
    # not on convenience: it runs no worker/API/web process. It resolves a model name
    # with a one-shot local tool and then hands off to `claude-code-action`, whose
    # deliverable is a PULL REQUEST for founder review. There is no long-lived
    # in-process error path for Sentry to capture, and a failure is a red job plus an
    # absent PR — both loud.
    "source-backfill.yml": "invokes claude-code-action to open a PR for founder "
                           "review; no worker/API/web process runs in it, so there "
                           "is no in-process error path for Sentry to instrument",
}


def _scheduled_workflows() -> dict[str, dict]:
    """Every workflow with a `schedule:` trigger, parsed."""
    out = {}
    # BOTH extensions: GitHub accepts `.yml` and `.yaml`, so globbing one lets a
    # scheduled `.yaml` workflow ship with no Sentry half while this test reports
    # "every scheduled workflow" covered (`CLASS:incomplete-workflow-surface-scan`, r6).
    for path in sorted([*_WORKFLOW_DIR.glob("*.yml"), *_WORKFLOW_DIR.glob("*.yaml")]):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            continue
        triggers = doc.get("on", doc.get(True))
        if isinstance(triggers, dict) and "schedule" in triggers:
            out[path.name] = doc
    return out


def test_there_are_scheduled_workflows_to_check():
    """Guards against the whole file passing over an empty set."""
    found = _scheduled_workflows()
    assert found, (
        "no scheduled workflows parsed out of .github/workflows — either the parse "
        "broke or the trigger key moved; every assertion below would be vacuous")


@pytest.mark.parametrize("name", sorted(_scheduled_workflows()))
def test_every_scheduled_workflow_passes_SENTRY_DSN_or_is_exempt_with_a_reason(name):
    doc = _scheduled_workflows()[name]
    text = (_WORKFLOW_DIR / name).read_text(encoding="utf-8")

    if name in _NO_APP_CODE:
        reason = _NO_APP_CODE[name]
        assert len(reason) > 40, (
            f"{name} is exempt with a reason too short to be a real one")
        return

    assert "SENTRY_DSN" in text, (
        f"{name} is a scheduled loop and never passes SENTRY_DSN, so a failure "
        f"during a run is visible only in Actions logs. CLAUDE.md's Sentinel clause "
        f"requires Sentry AND a dead-man alarm — 'no scheduled loop ships without "
        f"both'. Either wire it, or add it to _NO_APP_CODE in this file with a "
        f"reason about the workflow's nature (not about the DSN not existing yet).")
    assert "secrets.SENTRY_DSN" in text, (
        f"{name} mentions SENTRY_DSN but not `secrets.SENTRY_DSN` — a hardcoded or "
        f"empty value would make the wiring look present while delivering nothing")


def test_the_scheduled_importers_actually_initialise_sentry():
    """The DSN in the environment is inert unless something calls `init_sentry`.

    This is the half that makes the workflow assertion above non-cosmetic: passing a
    DSN to a process that never initialises the SDK is a green row proving nothing —
    the shape this PR has hit repeatedly.
    """
    entrypoints = [
        "worker/importers/run_licensed_import.py",
        "worker/importers/run_structured_import.py",
    ]
    for rel in entrypoints:
        src = (_ROOT / rel).read_text(encoding="utf-8")
        assert "from worker.sentinel import init_sentry" in src, \
            f"{rel} does not import init_sentry"
        # Inside main(), not merely imported — an unused import satisfies a grep.
        main_body = src[src.index("def main("):]
        call = re.search(r"^\s+init_sentry\(", main_body, re.MULTILINE)
        assert call, (
            f"{rel} imports init_sentry but never calls it inside main() — the DSN "
            f"would be present in the environment and ignored by the process")


def test_the_deadman_half_is_still_enforced_elsewhere():
    """This file is about the Sentry half; the alarm half is bound by the watchdog's
    own test. Asserted so nobody reads this file as the whole contract and later
    weakens the other mechanism believing it is covered here."""
    watchdog_test = _ROOT / "tests" / "test_watchdog_check.py"
    assert watchdog_test.is_file(), (
        "tests/test_watchdog_check.py is gone — the dead-man half of the Sentinel "
        "contract has lost its mechanism and this file does not replace it")
    text = watchdog_test.read_text(encoding="utf-8")
    assert "EXCLUDED" in text and "WATCHED" in text, (
        "the watchdog test no longer references the WATCHED/EXCLUDED tables, so "
        "scheduled workflows may no longer be required to declare a dead-man alarm")
