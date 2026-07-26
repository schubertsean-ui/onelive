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


def test_the_check_actually_FAILS_on_the_defect_it_was_written_for():
    """A syntax check that cannot fail proves nothing. This is the exact shape
    that reached CI: the heredoc body ends up inside the brace group."""
    broken = "python - <<'PY' || {\n  echo nope\n  exit 1; }\nprint(1)\nPY\n"
    proc = subprocess.run(["bash", "-n"], input=broken,
                          capture_output=True, text=True)
    assert proc.returncode != 0, "bash -n should reject the unterminated heredoc"
