"""Scheduled workflows may never depend on a bare `github.event.inputs.*`.

Greppable summary: mechanical gate for the defect class "a cron that can never
run" — on a `schedule` event GitHub supplies NO `inputs` context, so every
`${{ github.event.inputs.X }}` resolves to the EMPTY STRING. A workflow that
both runs on a schedule and feeds such a value into a required precondition
(`: "${VAR:?...}"`, a regex bound, an `[ -n ]` check) fails closed on EVERY
scheduled run and imports/ingests nothing, forever, while looking like correct
fail-closed discipline in the diff.

This is not hypothetical. `import_structured.yml` shipped 2026-07-25 with
`LIMIT: ${{ github.event.inputs.limit }}` and its ONLY scheduled run (GitHub
run 30175059075, 2026-07-25T21:09:09Z) died at the precondition step with
"LIMIT: limit input missing — the fetch bound is required — failing closed"
BEFORE fetching anything. The deterministic local-moat feed therefore never
ran unattended even once. Nothing in the harness caught it: no test exercised
the schedule path's env resolution, and reviewers read the guard as a virtue.
Full write-up: docs/V1_AUDIT_2026-07-26.md (D1).

The rule this pins: in any workflow carrying `on.schedule`, a value the run
NEEDS must be supplied by an expression that is non-empty on the schedule path
— either `github.event_name == 'schedule' && '<literal>' || github.event.inputs.X`
(schedule side pinned, dispatch cannot raise it — ingest.yml's ceiling form) or
`github.event.inputs.X || '<default>'`. A bare inputs reference is allowed only
inside a step that is itself gated off the schedule path
(`if: github.event_name == 'workflow_dispatch'`), where it cannot fire on cron.

Static analysis, no network, no GitHub API: the workflow YAML on disk IS the
contract.
"""
from __future__ import annotations

import pathlib
import re

import pytest

WORKFLOWS = pathlib.Path(__file__).resolve().parent.parent / ".github" / "workflows"

# A bare inputs reference: `${{ github.event.inputs.X }}` with nothing else in
# the expression. Any `&&`, `||`, or `event_name` inside the braces means the
# author wrote a conditional/defaulted form, which is what we want.
_BARE_INPUT = re.compile(r"\$\{\{\s*github\.event\.inputs\.[A-Za-z0-9_]+\s*\}\}")
_SCHEDULE_BLOCK = re.compile(r"^on:.*?^\S", re.DOTALL | re.MULTILINE)


def _scheduled_workflows() -> list[pathlib.Path]:
    out = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        # `schedule:` at trigger-block indentation (two spaces under `on:`).
        if re.search(r"^\s{2}schedule:\s*$", text, re.MULTILINE):
            out.append(path)
    return out


def test_there_are_scheduled_workflows_to_check():
    """The scanner must not pass by finding nothing (the founding
    anti-pattern: "we failed" must never look like "there was nothing to
    do")."""
    found = _scheduled_workflows()
    assert found, (
        "no workflow with `on.schedule` was found under .github/workflows — "
        "either the repo lost its crons or this scanner's detection broke; "
        "both are defects, neither is a pass"
    )


@pytest.mark.parametrize(
    "workflow", _scheduled_workflows(), ids=lambda p: p.name
)
def test_scheduled_workflow_has_no_bare_input_reference(workflow: pathlib.Path):
    offenders = []
    for lineno, line in enumerate(
        workflow.read_text(encoding="utf-8").splitlines(), 1
    ):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if _BARE_INPUT.search(line):
            offenders.append(f"{workflow.name}:{lineno}: {stripped[:120]}")
    assert not offenders, (
        f"{workflow.name} runs on a schedule and reads a BARE "
        f"`github.event.inputs.*`, which is the empty string on every "
        f"scheduled run — the cron either fails closed and never does its "
        f"work, or silently proceeds with an empty value.\n"
        f"Fix with an expression that is non-empty on the schedule path:\n"
        f"  ${{{{ github.event_name == 'schedule' && '<literal>' || "
        f"github.event.inputs.X }}}}   (schedule side pinned — preferred)\n"
        f"  ${{{{ github.event.inputs.X || '<default>' }}}}\n"
        f"…or gate the step with `if: github.event_name == "
        f"'workflow_dispatch'` so it cannot fire on cron.\n"
        + "\n".join(offenders)
    )


def test_structured_import_limit_expression_is_identical_in_both_steps():
    """The bound is read twice (precondition + import). Two copies of a safety
    expression drift; pin them to each other so a future edit to one is a red
    test rather than a half-fixed cron."""
    text = (WORKFLOWS / "import_structured.yml").read_text(encoding="utf-8")
    exprs = re.findall(r"^\s*LIMIT:\s*(.+)$", text, re.MULTILINE)
    assert len(exprs) == 2, (
        f"expected exactly 2 LIMIT env bindings in import_structured.yml, "
        f"found {len(exprs)}: {exprs} — if the workflow legitimately grew "
        f"another, extend this pin deliberately"
    )
    assert exprs[0].strip() == exprs[1].strip(), (
        "the two LIMIT expressions differ — a scheduled run would validate "
        "one bound and import with another:\n"
        f"  {exprs[0].strip()}\n  {exprs[1].strip()}"
    )
    assert "github.event_name == 'schedule'" in exprs[0], (
        "import_structured.yml's LIMIT must pin the SCHEDULE side to a literal "
        "so the unattended path's ceiling is not caller-suppliable"
    )
