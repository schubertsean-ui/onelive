"""Every workflow step that reads a repo file must be preceded by a checkout.

Caught for real on 2026-07-26: `site_health.yml` gained a step running
`python3 tools/check_console_links.py` but the job had no `actions/checkout`,
because the job's original steps only needed `curl`. It failed on its very first
execution with *"can't open file .../check_console_links.py"* — a check that
could never run.

Same family as R-054 (the project's first escaped defect): the trigger fires, the
step executes, and a precondition that was never on the runner kills it. That one
escaped to production because nothing tested the path. This one was caught by CI
in one run, and this test is the mechanical form so it is caught before CI.

Deliberately conservative about what counts as "reads a repo file": a first-party
directory prefix appearing in a `run:` block. False positives are cheap to fix by
adding the checkout that should be there anyway; a false negative ships a dead
step.
"""
from __future__ import annotations

import pathlib

import pytest
import yaml

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW_DIR = _REPO_ROOT / ".github" / "workflows"

# First-party paths whose appearance in a shell command means "this reads the
# repository". `web/` is included: a build step needs the source too.
REPO_PATH_TOKENS = ("tools/", "docs/", "worker/", "ai/", "brain/", "web/",
                    "tests/", "supabase/", "social/")

# Things that look like a repo path but are not reads of the checkout.
_ALLOWED_SUBSTRINGS = ("docs/RECORD.md is",)


def _workflows() -> list[pathlib.Path]:
    return sorted(p for ext in ("*.yml", "*.yaml") for p in WORKFLOW_DIR.glob(ext))


def _jobs(doc: dict) -> dict:
    return doc.get("jobs") or {}


def _reads_repo(run_text: str) -> list[str]:
    hits = [t for t in REPO_PATH_TOKENS if t in run_text]
    if any(a in run_text for a in _ALLOWED_SUBSTRINGS):
        return []
    return hits


def test_there_are_workflows_to_check():
    # A contract test that passes by finding nothing proves nothing.
    assert _workflows(), f"no workflows found under {WORKFLOW_DIR}"


@pytest.mark.parametrize("path", _workflows(), ids=lambda p: p.name)
def test_a_step_reading_repo_files_has_a_checkout_before_it(path):
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(doc, dict), f"{path.name}: not a mapping"
    for job_name, job in _jobs(doc).items():
        steps = (job or {}).get("steps") or []
        seen_checkout = False
        for index, step in enumerate(steps):
            uses = str((step or {}).get("uses") or "")
            if uses.startswith("actions/checkout"):
                seen_checkout = True
                continue
            run_text = str((step or {}).get("run") or "")
            if not run_text:
                continue
            hits = _reads_repo(run_text)
            if hits and not seen_checkout:
                label = (step or {}).get("name") or f"step #{index + 1}"
                pytest.fail(
                    f"{path.name}: job '{job_name}' step '{label}' reads "
                    f"{hits} from the repository but no actions/checkout runs "
                    f"before it — the step would fail with 'No such file or "
                    f"directory' on every run. Add "
                    f"'- uses: actions/checkout@v4' as an earlier step.")


def test_the_guard_catches_a_missing_checkout():
    """Prove the gate can fail — the version of site_health.yml that shipped
    broken must be red under this test."""
    broken = {
        "jobs": {"check": {"steps": [
            {"name": "curl something", "run": "curl -sS https://example.com"},
            {"name": "read a repo file", "run": "python3 tools/whatever.py"},
        ]}}
    }
    offenders = []
    for job_name, job in _jobs(broken).items():
        seen = False
        for step in job["steps"]:
            if str(step.get("uses") or "").startswith("actions/checkout"):
                seen = True
                continue
            if _reads_repo(str(step.get("run") or "")) and not seen:
                offenders.append(step["name"])
    assert offenders == ["read a repo file"]


def test_the_guard_accepts_a_checkout_first():
    fixed = {
        "jobs": {"check": {"steps": [
            {"uses": "actions/checkout@v4"},
            {"name": "read a repo file", "run": "python3 tools/whatever.py"},
        ]}}
    }
    for job_name, job in _jobs(fixed).items():
        seen = False
        for step in job["steps"]:
            if str(step.get("uses") or "").startswith("actions/checkout"):
                seen = True
                continue
            if _reads_repo(str(step.get("run") or "")):
                assert seen, "checkout should have been seen first"
