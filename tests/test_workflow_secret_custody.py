"""Who owns the YAML that a repository secret is handed to.

THE DEFECT CLASS, in one sentence: the workflow FILE that GitHub executes is the
one on the triggering ref, so a trigger that fires automatically on a push to any
branch hands repository secrets to a workflow definition that branch controls.
Edit the curl target in the PR, and the secret leaves the repo.

Found on PR #80 by two independent reviewer lenses (openai/attacker-smuggle as
`CLASS:secret-exfiltration-pr-workflow`, openai/absence-only as
`CLASS:secret-in-pr-owned-workflow`) against `site_health.yml`, which had a
`pull_request` trigger and read `secrets.VERCEL_AUTOMATION_BYPASS`. Fixing only
that file would have left the class unenumerated, which is the failure mode this
repo has hit repeatedly — so this test scans EVERY workflow and requires each
instance to be either safe by construction or listed below with a reason.

THE HONEST LIMIT, stated rather than buried. GitHub already withholds secrets
from `pull_request` runs originating in FORKS, so the exposure is to actors with
push access to this repository — who can generally read the same secrets from the
settings page, meaning this is defence in depth rather than a privilege boundary.
It still matters: it shrinks the blast radius of one leaked collaborator token,
and it is free wherever a trigger has a safe equivalent.
"""
from __future__ import annotations

import pathlib
import re

import pytest
import yaml

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_WORKFLOWS = _ROOT / ".github" / "workflows"

# Triggers that fire WITHOUT a deliberate act by a privileged actor AND execute
# the YAML from the triggering ref. `workflow_dispatch` and `schedule` are absent
# on purpose: dispatch requires write access (so it grants nothing new), and
# schedule only ever runs the default branch's copy. `pull_request_target` is
# absent because it deliberately runs the BASE copy — that is the fix, not the bug.
AUTOMATIC_BRANCH_OWNED_TRIGGERS = frozenset({
    "push", "pull_request", "deployment", "deployment_status",
})

# GITHUB_TOKEN is not a stored secret: it is a per-run token scoped by the
# workflow's own `permissions:` block, so exfiltrating it buys the permissions the
# attacker's branch could grant itself anyway.
NOT_A_STORED_SECRET = frozenset({"GITHUB_TOKEN"})

# The one accepted instance, with the reason it is not fixed here rather than a
# silent omission. A NEW entry in this table is a decision someone has to write
# down; a new instance NOT in this table fails the test.
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
    risky = _triggers(path) & AUTOMATIC_BRANCH_OWNED_TRIGGERS
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
        assert _triggers(path) & AUTOMATIC_BRANCH_OWNED_TRIGGERS, \
            f"{name} no longer has an automatic branch-owned trigger — remove it"
