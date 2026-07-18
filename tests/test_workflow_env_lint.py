"""Tests for tools/workflow_env_lint.py — the env-contract linter (R-019).

The empty-env class fix must itself be able to fail: every rule has a fixture
that trips it and a fixture that satisfies it, plus a live run over the real
.github/workflows tree (which must be clean — a regression there is a real
finding, not a test artifact).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tools.workflow_env_lint import lint_workflow_text

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "workflow_env_lint.py"


def _wf(steps: str, extra: str = "") -> str:
    return f"""
name: fixture
on: push
{extra}
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
{steps}
"""


def test_undeclared_env_var_is_a_finding():
    text = _wf("""
      - name: gate
        run: |
          curl -H "Authorization: $SECRET_TOKEN" https://example.com
""")
    findings = lint_workflow_text(text, "f.yml")
    assert any("SECRET_TOKEN" in f and "no visible source" in f for f in findings)


def test_step_env_declaration_satisfies_r1():
    text = _wf("""
      - name: gate
        env:
          SECRET_TOKEN: ${{ secrets.SECRET_TOKEN }}
        run: |
          curl -H "Authorization: $SECRET_TOKEN" https://example.com
""")
    assert lint_workflow_text(text, "f.yml") == []


def test_workflow_and_job_env_satisfy_r1():
    text = _wf(
        """
      - name: gate
        run: echo "$TOP_LEVEL and $JOB_LEVEL"
""",
        extra="env:\n  TOP_LEVEL: x",
    ).replace("runs-on: ubuntu-latest", "runs-on: ubuntu-latest\n    env:\n      JOB_LEVEL: y")
    assert lint_workflow_text(text, "f.yml") == []


def test_github_env_export_from_earlier_step_satisfies_r1():
    text = _wf("""
      - name: produce
        run: echo "MY_DSN=abc" >> "$GITHUB_ENV"
      - name: consume
        run: psql "$MY_DSN"
""")
    assert lint_workflow_text(text, "f.yml") == []


def test_export_in_later_step_does_not_cover_earlier_consumption():
    text = _wf("""
      - name: consume-too-early
        run: psql "$MY_DSN"
      - name: produce
        run: echo "MY_DSN=abc" >> "$GITHUB_ENV"
""")
    findings = lint_workflow_text(text, "f.yml")
    assert any("MY_DSN" in f for f in findings)


def test_script_local_assignment_and_loop_vars_are_not_findings():
    text = _wf("""
      - name: local
        run: |
          MY_LOCAL=5
          echo "$MY_LOCAL"
          for ITEM_NAME in a b; do echo "$ITEM_NAME"; done
""")
    assert lint_workflow_text(text, "f.yml") == []


def test_runner_ambient_names_are_not_findings():
    text = _wf("""
      - name: ambient
        run: echo "$GITHUB_SHA on $RUNNER_OS at $HOME"
""")
    assert lint_workflow_text(text, "f.yml") == []


def test_vars_context_in_value_is_banned():
    text = _wf("""
      - name: gate
        env:
          MODEL: ${{ vars.REVIEW_MODEL }}
        run: echo "$MODEL"
""")
    findings = lint_workflow_text(text, "f.yml")
    assert any("vars." in f and "forbidden" in f for f in findings)


def test_vars_context_in_comment_is_not_banned():
    text = _wf("""
      - name: gate
        # never use ${{ vars.ANYTHING }} here — documented ban
        run: echo ok
""")
    assert lint_workflow_text(text, "f.yml") == []


def test_github_expressions_are_not_shell_vars():
    # ${{ steps.x.outputs.y }} resolves before the shell sees it.
    text = _wf("""
      - name: expr
        run: git diff "${{ steps.range.outputs.range }}" -- .
""")
    assert lint_workflow_text(text, "f.yml") == []


def test_unparseable_yaml_fails_loud():
    with pytest.raises(ValueError):
        lint_workflow_text("jobs: [unclosed", "broken.yml")


def test_real_workflow_tree_is_clean():
    proc = subprocess.run(
        [sys.executable, str(TOOL)], capture_output=True, text=True, cwd=REPO_ROOT
    )
    assert proc.returncode == 0, proc.stderr


def test_cli_missing_dir_fails_closed():
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--dir", "no/such/dir"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 2
