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
`github.event.inputs.X || '<default>'`.

DELIBERATELY OVER-STRICT, and the docstring says so because an earlier draft of it
did not (PR #76 reviewer nit): a bare inputs reference inside a step gated
`if: github.event_name == 'workflow_dispatch'` genuinely cannot fire on cron and is
therefore safe, but this scanner still rejects it. Path-sensitive step analysis
would mean parsing step scopes and their `if:` conditions, and a scanner that has
to be right about scope is a scanner that can be wrong in the fail-OPEN direction.
The cost of the strict rule is one extra `github.event_name == 'schedule' &&`
clause; the cost of the clever one is a silent hole. Fail closed, and write the
defaulted form even where it is redundant.

COVERAGE, widened at the PR #76 review (both OpenAI lenses found the same class —
a gate claiming to cover "every scheduled workflow" that an attacker could step
around):
  * BOTH `*.yml` and `*.yaml` — GitHub accepts either, so globbing one extension
    let a renamed workflow keep the defect while this gate reported clean.
  * `schedule:` at ANY indentation, not exactly two spaces — alternate valid YAML
    formatting was invisible to the original pattern.
  * BOTH `${{ github.event.inputs.X }}` and the `${{ inputs.X }}` shorthand —
    both are empty on a schedule-triggered run, and only the long form was matched.

Static analysis, no network, no GitHub API: the workflow YAML on disk IS the
contract.
"""
from __future__ import annotations

import pathlib
import re

import pytest

WORKFLOWS = pathlib.Path(__file__).resolve().parent.parent / ".github" / "workflows"

# A bare inputs reference with nothing else in the expression. Any `&&`, `||`, or
# `event_name` inside the braces means the author wrote a conditional/defaulted
# form, which is what we want. BOTH spellings are matched: `github.event.inputs.X`
# and the `inputs.X` shorthand — both resolve to the empty string on a
# schedule-triggered run, so matching only the long form left half the class open.
_BARE_INPUT = re.compile(
    r"\$\{\{\s*(?:github\.event\.)?inputs\.[A-Za-z0-9_-]+\s*\}\}"
)
# `schedule:` as a trigger key at ANY indentation. Pinning it to exactly two
# spaces meant valid alternate YAML formatting silently excluded a workflow from
# the scan — an under-trigger, which is this gate's only real failure mode.
_SCHEDULE_KEY = re.compile(r"^\s+schedule:\s*$", re.MULTILINE)

# GitHub accepts both extensions for workflow files. Globbing one of them let a
# rename carry the defect past a gate that claimed to cover every workflow.
_WORKFLOW_GLOBS = ("*.yml", "*.yaml")


def _workflow_files() -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    for pattern in _WORKFLOW_GLOBS:
        found.extend(WORKFLOWS.glob(pattern))
    return sorted(set(found))


def _scheduled_workflows() -> list[pathlib.Path]:
    return [
        path for path in _workflow_files()
        if _SCHEDULE_KEY.search(path.read_text(encoding="utf-8"))
    ]


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


def test_scanner_detects_every_evasion_the_review_found():
    """The scanner's own coverage, asserted directly rather than trusted.

    Each case below is an evasion path that the FIRST version of this gate could
    not see, found by the independent review on PR #76. They are asserted against
    the patterns rather than against fixture files on disk, so the test states the
    rule instead of depending on a workflow happening to be shaped a certain way.
    """
    # 1. The `inputs.X` shorthand — equally empty on a schedule run, and invisible
    #    to a pattern that only matched the `github.event.` prefix.
    assert _BARE_INPUT.search("LIMIT: ${{ inputs.limit }}"), (
        "the inputs.X shorthand must be caught — it is empty on schedule runs too"
    )
    assert _BARE_INPUT.search("LIMIT: ${{ github.event.inputs.limit }}")

    # 2. The defaulted and schedule-pinned forms must NOT trip it, or the gate
    #    becomes noise and gets disabled.
    assert not _BARE_INPUT.search("LIMIT: ${{ inputs.limit || '40' }}")
    assert not _BARE_INPUT.search(
        "LIMIT: ${{ github.event_name == 'schedule' && '40' || inputs.limit }}"
    )

    # 3. `schedule:` at indentations other than exactly two spaces — all valid
    #    YAML, all previously excluded from the scan entirely, which is the
    #    under-trigger this gate cannot afford.
    for indent in (" ", "  ", "    ", "\t"):
        assert _SCHEDULE_KEY.search(f"on:\n{indent}schedule:\n"), (
            f"schedule: at indent {indent!r} must still put the workflow in scope"
        )

    # 4. Both workflow extensions GitHub accepts. A rename must not shed the gate.
    assert set(_WORKFLOW_GLOBS) == {"*.yml", "*.yaml"}


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
