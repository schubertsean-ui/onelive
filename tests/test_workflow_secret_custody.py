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
# THE ONE REMAINING INSTANCE, and it is founder-crucial rather than deferred.
#
# Everything else that read a stored secret from a dispatchable branch is now
# guarded on the default branch — the six schedule+dispatch workflows included,
# at the cost of no longer being able to dispatch an UNMERGED importer (stated in
# each file). An earlier round accepted those six in prose; the reviewer was right
# that an allowlist entry is not a control, and the guard is.
#
# `adversarial-review.yml` cannot take that guard: it must run on every PR, which
# is the opposite of default-branch-only. Its correct fix is `pull_request_target`
# — two workflows here already use it — and that is a change to the MANDATORY
# EXAMINER's trigger, which decides which ref supplies the reviewed diff. Getting
# it wrong makes the gate judge the WRONG DIFF while reporting green, and the
# charter reserves examiner changes to the founder. Escalated with options rather
# than either shipped inside a large PR or waved past. R-072.
ACCEPTED: dict[str, str] = {
    "extraction-exam-dispatch.yml":
        "HARNESS-BOUND, and the charter's own mechanism refused the fix. This file is "
        "in `ai/golden_exam.py`'s HARNESS_MANIFEST, so adding the guard changed the "
        "manifest hash and `trust_gate` failed with "
        "'harness has DRIFTED since the attended exam — extraction is uncertified "
        "against this tree'. Re-certifying needs a fresh ATTENDED EXAM RUN, which "
        "costs money: founder-crucial, and the same refusal that stopped an "
        "`ingest.yml` error-string edit earlier in this arc. The guard was written, "
        "measured against the gate, and REVERTED rather than argued with. R-078 "
        "carries it, with the next attended exam as its trigger.",
    "adversarial-review.yml":
        "The mandatory reviewer runs on EVERY PR, so a default-branch guard would "
        "disable the gate. Its fix is a `pull_request_target` conversion, which "
        "changes which ref supplies `pr.diff` — get that wrong and the mandatory "
        "examiner judges the wrong diff while reporting green, a worse failure than "
        "the one being closed. That makes it an examiner/gate-custody change, which "
        "CLAUDE.md reserves to the founder. R-072 carries the options and the "
        "trigger; this entry is an escalation, not a deferral.",
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
    # The guard must be in a JOB CONDITION, not merely present in the file. A
    # comment mentioning `default_branch` would have satisfied the old text scan —
    # prose is not a control, which is the whole lesson of this round (reviewer
    # nit, openai/absence-only, PR #80 r4).
    doc = yaml.safe_load(text)
    jobs = doc.get("jobs") or {}
    assert jobs, f"{path.name}: no jobs to guard"
    unguarded = [name for name, job in jobs.items()
                 if not _DEFAULT_BRANCH_GUARD.search(str(job.get("if", "")))]
    assert not unguarded, (
        f"{path.name} reads stored secret(s) {sorted(secrets)} and is reachable "
        f"from branch-owned trigger(s) {sorted(risky)}, which execute THIS BRANCH's "
        f"copy of the file. Job(s) {unguarded} have no default-branch guard in "
        f"their `if:` condition. Either guard them (compare github.ref_name to "
        f"github.event.repository.default_branch), move to pull_request_target so "
        f"the base copy runs, or add an entry to ACCEPTED explaining why not.")


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


_GUARDED_NOW = ("import_licensed.yml", "import_structured.yml", "ingest.yml",
                "dependency-hygiene.yml", "source-backfill.yml")


def test_the_dispatchable_secret_workflows_are_guarded_at_the_JOB_level():
    """`CLASS:accepted-secret-custody-gap` (both openai lenses, PR #80 r4).

    An earlier round listed these six in ACCEPTED with a reason. The reviewer was
    right that an allowlist entry is not a compensating control: the secret stayed
    reachable from YAML nobody reviewed. They are guarded now, at the documented
    cost of not being able to dispatch an UNMERGED importer.
    """
    for name in _GUARDED_NOW:
        path = _WORKFLOWS / name
        assert name not in ACCEPTED, \
            f"{name} was FIXED, not accepted — it must not reappear in ACCEPTED"
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        for job, body in (doc.get("jobs") or {}).items():
            cond = str(body.get("if", ""))
            assert _DEFAULT_BRANCH_GUARD.search(cond), \
                f"{name}:{job} has no default-branch guard: {cond!r}"
        # The SCHEDULED path must survive: GitHub only ever runs the default
        # branch's copy on a schedule, so the guard must not gate schedule runs off.
        cond = str(next(iter(doc["jobs"].values())).get("if", ""))
        assert "workflow_dispatch" in cond, (
            f"{name}: the guard must be scoped to the dispatch path, or the cron "
            f"stops running and the feed goes stale — a worse outcome than the "
            f"hole being closed")


def test_the_only_accepted_entries_are_the_two_a_gate_refused():
    """The allowlist must not grow back. Exactly two remain, and NEITHER is a
    convenience: one is the examiner itself (changing its trigger is a gate-custody
    decision the charter reserves to the founder), the other was WRITTEN, measured
    against `trust_gate`, and reverted because it drifted the certified exam harness
    and re-certifying costs money. Both are escalations with triggers, not deferrals.
    """
    assert set(ACCEPTED) == {"adversarial-review.yml",
                             "extraction-exam-dispatch.yml"}, (
        f"ACCEPTED grew or shrank unexpectedly: {sorted(ACCEPTED)}")
    assert "founder" in ACCEPTED["adversarial-review.yml"]
    assert "R-072" in ACCEPTED["adversarial-review.yml"]
    assert "escalation, not a deferral" in ACCEPTED["adversarial-review.yml"]
    exam = ACCEPTED["extraction-exam-dispatch.yml"]
    assert "HARNESS-BOUND" in exam and "R-078" in exam
    assert "founder-crucial" in exam
    # The claim that it is harness-bound must be TRUE, not asserted — otherwise this
    # entry is an excuse dressed as a mechanism.
    manifest = (_ROOT / "ai" / "golden_exam.py").read_text(encoding="utf-8")
    assert '".github/workflows/extraction-exam-dispatch.yml"' in manifest, (
        "the exemption claims this file is in HARNESS_MANIFEST; it is not, so the "
        "reason is false and the guard should simply be applied")


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
