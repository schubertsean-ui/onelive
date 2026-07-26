"""Who owns the YAML that a repository secret is handed to.

THE CLASS: GitHub executes the workflow file on the TRIGGERING REF, so a trigger
reachable from an unreviewed branch hands repository secrets to YAML that branch
controls. Edit the curl target, and the secret leaves the repo. Found on PR #80
against `site_health.yml` by two lenses; this test scans EVERY workflow so the
class is enumerated rather than the one instance fixed.

A CLAIM THIS FILE USED TO MAKE, AND WHICH WAS FALSE — kept because it is why the
first fix stopped at `pull_request` and left `workflow_dispatch` open. It said
exposure was only to push-access actors "who can generally read the same secrets
from the settings page". **Actions secret VALUES are write-only in the UI at every
permission level.** Nobody reads them back, so this is a privilege boundary, not
defence in depth, and `workflow_dispatch` belongs in the risky set.

THE REAL LIMIT: a push-access actor can also merge to the default branch. This
gate shrinks the paths; it does not close the category. What it closes is the
accidental one — a secret quietly reachable from YAML nobody reviewed.
"""
from __future__ import annotations

import pathlib
import re

import pytest
import yaml

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_WORKFLOWS = _ROOT / ".github" / "workflows"

# Triggers that execute the YAML from a ref the triggering party can choose — the
# property that matters, which is why this set is named for OWNERSHIP rather than
# "automatic" as the first version was. `workflow_dispatch` is here despite needing
# write access (see the docstring). `schedule` is absent: GitHub only runs the
# default branch's copy. `pull_request_target` is absent: it runs the BASE copy,
# which is the fix, not the bug.
BRANCH_OWNED_TRIGGERS = frozenset({
    "push", "pull_request", "deployment", "deployment_status", "workflow_dispatch",
})

# GITHUB_TOKEN is not a stored secret: it is a per-run token scoped by the
# workflow's own `permissions:` block, so exfiltrating it buys the permissions the
# attacker's branch could grant itself anyway.
NOT_A_STORED_SECRET = frozenset({"GITHUB_TOKEN"})

# The one accepted instance, with the reason it is not fixed here rather than a
# silent omission. A NEW entry in this table is a decision someone has to write
# down; a new instance NOT in this table fails the test.
_DISPATCH_OPERATIONAL = (
    "Dispatching from a feature branch is a REAL operation: the importers get run by "
    "hand to seed or repair the feed, and that is how the 1,532-event feed got there. "
    "A default-branch guard would break the operation to close a path a push-access "
    "actor has anyway. Tracked as R-075, whose fix is a GitHub environment with "
    "required reviewers — closing the path WITHOUT removing the capability."
)

# Accepted instances, each with the reason it is not fixed here rather than a silent
# omission. A NEW entry is a decision someone has to write down; a new instance NOT
# in this table fails the test.
ACCEPTED: dict[str, str] = {
    "adversarial-review.yml":
        "The mandatory reviewer must run on every PR, so it cannot be restricted "
        "to the default branch, and it is PR-owned by design (it deliberately "
        "runs a BASE-owned trusted copy of adversarial_review.py, with "
        "feature-detection for version skew). The safe conversion is "
        "`pull_request_target`, which two other workflows here already use — but "
        "that changes which ref is checked out, and getting it wrong would make "
        "the mandatory gate review the WRONG DIFF while still reporting green. "
        "Recorded as R-072 with the conversion as its trigger, not waved past.",
    "import_licensed.yml": _DISPATCH_OPERATIONAL,
    "import_structured.yml": _DISPATCH_OPERATIONAL,
    "ingest.yml": _DISPATCH_OPERATIONAL,
    "dependency-hygiene.yml": _DISPATCH_OPERATIONAL,
    "source-backfill.yml": _DISPATCH_OPERATIONAL,
    "extraction-exam-dispatch.yml":
        "Dispatch-only by design: it exists so the golden exam can be run "
        "deliberately against a chosen ref, which is the whole point of the exam "
        "channel, and it consumes a dedicated exam-scoped key rather than a "
        "production credential. A default-branch guard would make it impossible to "
        "exam a branch, which is what it is for. Same R-075 trigger: an environment "
        "with required reviewers closes the path without removing the capability.",
}

_SECRET_REF = re.compile(r"secrets\.([A-Za-z_][A-Za-z0-9_]*)")
# A guard is any comparison of the running ref against the repository's default
# branch. Deliberately not a literal branch name: renaming the default branch
# must not silently reopen the hole.
_DEFAULT_BRANCH_GUARD = re.compile(
    r"github\.(ref|ref_name)\s*==\s*[^\n]*default_branch"
    r"|default_branch\s*==\s*[^\n]*github\.(ref|ref_name)")


def _workflows() -> list[pathlib.Path]:
    files = sorted(_WORKFLOWS.glob("*.yml")) + sorted(_WORKFLOWS.glob("*.yaml"))
    assert files, "no workflows found — this test would pass vacuously"
    return files


def _triggers(path: pathlib.Path) -> set[str]:
    """The trigger names, read from PARSED YAML rather than matched by regex.

    `on:` is the YAML 1.1 boolean `True` after safe_load, which is why the key is
    looked up both ways. Parsing rather than grepping is the point: a
    regex-only scan is the `incomplete-workflow-surface-scan` defect this repo
    has now been told about three times.
    """
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(doc, dict), f"{path.name}: not a YAML mapping"
    section = doc.get("on", doc.get(True))
    if isinstance(section, dict):
        return set(section)
    if isinstance(section, list):
        return set(section)
    if isinstance(section, str):
        return {section}
    raise AssertionError(f"{path.name}: unreadable `on:` section {section!r}")


def _stored_secrets(text: str) -> set[str]:
    return set(_SECRET_REF.findall(text)) - NOT_A_STORED_SECRET


def test_the_scan_sees_the_workflows_it_claims_to_cover():
    """Guards against a silently empty sweep — the shape that lets a gate pass
    while checking nothing."""
    names = {p.name for p in _workflows()}
    for expected in ("site_health.yml", "adversarial-review.yml",
                     "import_licensed.yml", "watchdog.yml"):
        assert expected in names, f"{expected} missing from the scan"


@pytest.mark.parametrize("path", _workflows(), ids=lambda p: p.name)
def test_a_stored_secret_is_never_handed_to_branch_owned_yaml_automatically(path):
    text = path.read_text(encoding="utf-8")
    secrets = _stored_secrets(text)
    if not secrets:
        return
    risky = _triggers(path) & BRANCH_OWNED_TRIGGERS
    if not risky:
        return
    if path.name in ACCEPTED:
        return
    assert _DEFAULT_BRANCH_GUARD.search(text), (
        f"{path.name} reads stored secret(s) {sorted(secrets)} and is triggered "
        f"automatically by {sorted(risky)}, which executes THIS BRANCH's copy of "
        f"the file. Either restrict the automatic path to the default branch "
        f"(compare github.ref_name to github.event.repository.default_branch), "
        f"move to pull_request_target so the base copy runs, or add an entry to "
        f"ACCEPTED in this file explaining why not.")


@pytest.mark.parametrize("name", ["site_health.yml", "experience_metrics.yml"])
def test_the_bypass_reading_workflows_guard_EVERY_path_including_dispatch(name):
    """`CLASS:secret-dispatch-branch-owned-yaml` (PR #80 r3).

    The first fix narrowed only `deployment_status`, leaving `workflow_dispatch`
    able to run branch-owned YAML with the secret. The guard has to sit where no
    path can miss it — the job condition, not one branch of it. Nothing is lost:
    dispatching from the default branch satisfies it, and the URL is an input.
    """
    path = _WORKFLOWS / name
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    job = next(iter(doc["jobs"].values()))
    condition = job.get("if", "")
    assert condition, f"{name}: the job has no `if:` — the secret is unguarded"
    assert _DEFAULT_BRANCH_GUARD.search(condition), (
        f"{name}: the default-branch comparison must be part of the JOB CONDITION "
        f"so every trigger path is covered, not only the automatic one. Got: "
        f"{condition!r}")
    # ...and it must not be reachable via an `or` that bypasses it. Every
    # top-level alternative in the condition has to carry the guard.
    for branch in re.split(r"\|\|", condition):
        assert _DEFAULT_BRANCH_GUARD.search(branch), (
            f"{name}: this alternative in the job condition runs WITHOUT a "
            f"default-branch guard, so it can execute branch-owned YAML with the "
            f"secret: {branch.strip()!r}")


def test_site_health_restricts_its_automatic_trigger_to_the_default_branch():
    """The specific instance, asserted specifically — the class test above would
    also pass if someone added site_health.yml to ACCEPTED."""
    path = _WORKFLOWS / "site_health.yml"
    text = path.read_text(encoding="utf-8")
    assert path.name not in ACCEPTED, \
        "this instance was FIXED, not accepted — it must not appear in ACCEPTED"
    assert "VERCEL_AUTOMATION_BYPASS" in text, "the secret this test is about is gone"
    assert "deployment_status" in _triggers(path)
    assert _DEFAULT_BRANCH_GUARD.search(text), \
        "the deployment_status path must be default-branch-only"
    assert "pull_request" not in _triggers(path), \
        "the pull_request trigger is the exfiltration path the reviewer blocked on"


def test_every_accepted_entry_names_a_real_workflow_and_gives_a_reason():
    """An allowlist that drifts from the tree is a gate that has stopped
    checking; a reason-free entry is a silent deferral (charter directive 7)."""
    names = {p.name for p in _workflows()}
    for name, reason in ACCEPTED.items():
        assert name in names, f"ACCEPTED names {name}, which no longer exists"
        assert len(reason) > 80, f"{name}: the reason is too thin to audit"
        assert "R-0" in reason, (
            f"{name}: an accepted deviation must cite its RECORD.md row, or it is "
            f"a deferral with no resolution trigger")


def test_every_accepted_entry_is_still_actually_an_instance():
    """If a workflow on the allowlist stops using secrets, or stops using a risky
    trigger, the entry must GO — a stale exemption is how the next real instance
    gets waved through."""
    for name in ACCEPTED:
        path = _WORKFLOWS / name
        text = path.read_text(encoding="utf-8")
        assert _stored_secrets(text), \
            f"{name} no longer reads a stored secret — remove it from ACCEPTED"
        assert _triggers(path) & BRANCH_OWNED_TRIGGERS, \
            f"{name} no longer has an automatic branch-owned trigger — remove it"
