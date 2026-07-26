"""Every workflow `run:` block must be valid shell.

Gate gap, caught the expensive way on 2026-07-26: a `run:` step used
`python - <<'PY' || { ... }`, which puts the heredoc body inside the brace
group so the shell never sees its terminator. Nothing local flagged it —
YAML parsed fine, the Python inside was fine — and it failed only after a push,
inside a job that had already spent a minute fetching data.

`bash -n` parses without executing, so this costs milliseconds and catches the
whole class: unterminated heredocs, unbalanced quotes, missing `fi`/`done`.

It does NOT catch semantic errors, and deliberately so — running these steps
would need the secrets and network they exist to use.
"""
from __future__ import annotations

import pathlib
import re
import shutil
import subprocess

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((REPO / ".github" / "workflows").glob("*.yml"))


def _run_blocks(path: pathlib.Path) -> list:
    """(step name, shell script) for every `run:` in the workflow."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    blocks: list = []
    for job_name, job in (doc.get("jobs") or {}).items():
        for i, step in enumerate(job.get("steps") or []):
            script = step.get("run")
            if not isinstance(script, str):
                continue
            # Only bash-like steps; a `shell: python` step is not shell.
            shell = step.get("shell") or job.get("defaults", {}).get(
                "run", {}).get("shell") or "bash"
            if not str(shell).startswith(("bash", "sh")):
                continue
            blocks.append(
                (f"{job_name} step {i + 1} "
                 f"({step.get('name') or 'unnamed'})", script))
    return blocks


def test_there_are_workflows_to_check():
    """A glob that silently matches nothing would make every test below pass
    while checking exactly nothing."""
    assert WORKFLOWS, "no workflow files found — the glob is wrong"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_run_block_parses_as_shell(path):
    if not shutil.which("bash"):
        pytest.skip("bash unavailable")
    blocks = _run_blocks(path)
    failures: list = []
    for label, script in blocks:
        # GitHub expands ${{ }} before the shell sees it. Substitute a harmless
        # token so an unexpanded expression is not misread as a syntax error.
        cleaned = _strip_expressions(script)
        proc = subprocess.run(["bash", "-n"], input=cleaned,
                              capture_output=True, text=True)
        if proc.returncode != 0:
            failures.append(f"{label}: {proc.stderr.strip()}")
    assert not failures, (
        f"{path.name} has run block(s) that are not valid shell:\n  "
        + "\n  ".join(failures))


def _strip_expressions(script: str) -> str:
    """Replace ${{ ... }} with a literal, the way the runner would."""
    import re
    return re.sub(r"\$\{\{[^}]*\}\}", "EXPR", script)


def test_the_coverage_workflow_watches_every_script_it_runs():
    """A measurement that does not re-run when one of its own inputs changes is
    how a stale number survives a fix.

    `tools/fetch_tmo_venues.py` was added as denominator layer 3 and left out of
    the path filter, so editing it changed the measurement without re-measuring.
    """
    path = REPO / ".github" / "workflows" / "capcog-coverage.yml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    on = doc.get(True) or doc.get("on") or {}
    watched = set((on.get("push") or {}).get("paths") or [])
    assert watched, "the coverage workflow has no push path filter"

    run_text = "\n".join(
        step.get("run", "")
        for job in (doc.get("jobs") or {}).values()
        for step in (job.get("steps") or [])
        if isinstance(step.get("run"), str))
    invoked = set(re.findall(r"python (tools/[\w/]+\.py)", run_text))
    missing = sorted(s for s in invoked if s not in watched)
    assert not missing, (
        f"these scripts run in the coverage workflow but changing them does "
        f"NOT re-run the measurement: {missing}")


def test_the_check_actually_FAILS_on_the_defect_it_was_written_for():
    """A syntax check that cannot fail proves nothing. This is the exact shape
    that reached CI: the heredoc body ends up inside the brace group."""
    broken = "python - <<'PY' || {\n  echo nope\n  exit 1; }\nprint(1)\nPY\n"
    proc = subprocess.run(["bash", "-n"], input=broken,
                          capture_output=True, text=True)
    assert proc.returncode != 0, "bash -n should reject the unterminated heredoc"


def _coverage_workflow() -> dict:
    return yaml.safe_load(
        (REPO / ".github" / "workflows" / "capcog-coverage.yml")
        .read_text(encoding="utf-8"))


def test_the_coverage_SCORE_runs_on_the_push_path(tmp_path):
    """r1 blocker: the contract's done-criterion is that the fetch AND the
    score run on push, and the report step was dispatch-only — so "the number
    is never older than the last commit" was untrue on the one path that would
    have made it true. The previous test only checked that invoked scripts
    appeared in the path filter, which passed while the criterion was absent."""
    steps = [s for j in (_coverage_workflow().get("jobs") or {}).values()
             for s in (j.get("steps") or [])]
    scoring = [s for s in steps
               if "capcog_coverage.py" in (s.get("run") or "")]
    assert scoring, "no step runs the coverage tool at all"
    on_push = [s for s in scoring
               if "workflow_dispatch" not in str(s.get("if", ""))
               or "!=" in str(s.get("if", ""))]
    assert on_push, (
        "every coverage-scoring step is gated to workflow_dispatch — the score "
        "does not run on push, which is the contract's done-criterion")


def test_every_DB_SECRET_step_is_bound_to_a_protected_ref():
    """r1 blocker: `workflow_dispatch` alone still lets a dispatch be aimed at
    ANY ref, so the credential's custody rested on a human choosing a safe
    branch. A live database credential fails closed by construction or not at
    all."""
    steps = [s for j in (_coverage_workflow().get("jobs") or {}).values()
             for s in (j.get("steps") or [])]
    secret_steps = [s for s in steps
                    if "ONELIVE_DB_DSN" in str(s.get("env") or {})]
    assert secret_steps, "no step carries the DB secret — has it moved?"
    for s in secret_steps:
        cond = str(s.get("if", ""))
        assert "github.ref" in cond, (
            f"step {s.get('name')!r} exposes ONELIVE_DB_DSN without a ref "
            f"binding; its condition is {cond!r}")
        assert "refs/heads/master" in cond, (
            f"step {s.get('name')!r} is not bound to the protected ref")
