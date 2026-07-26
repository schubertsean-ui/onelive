"""Tests for tools/experience_thresholds.py — judging the experience users get.

v1 done-criterion 4 / BAR E1–E4, P2. The tool shipped with no caller and no
tests; three reviewer lenses on PR #80 blocked on it as the same finding — a
gate-shaped tool nothing runs is a claim, not a mechanism.

The property tested hardest: **an absent measurement is EXIT 2, never a pass.** A
judge reporting success over a metric it did not read is the false-confidence
class this repo keeps catching, and worse here because these numbers get quoted.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest
import yaml

_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "experience_thresholds", _ROOT / "tools" / "experience_thresholds.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ET = _load()


def _lh(**overrides: float | None) -> dict:
    """A Lighthouse report shaped like the real one, within bar by default."""
    values: dict[str, float | None] = {
        "largest-contentful-paint": 1500.0,
        "cumulative-layout-shift": 0.02,
        "total-blocking-time": 90.0,
    }
    values.update(overrides)
    return {"audits": {k: {"numericValue": v} for k, v in values.items()}}


def _axe(violations: list[dict] | None = None) -> list[dict]:
    return [{"violations": violations or []}]


def _write(tmp_path: pathlib.Path, name: str, payload: object) -> pathlib.Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _run(tmp_path: pathlib.Path, lighthouse: object, axe: object) -> int:
    return ET.main([
        "--lighthouse", str(_write(tmp_path, "lh.json", lighthouse)),
        "--axe", str(_write(tmp_path, "axe.json", axe)),
    ])


# ------------------------------------------------- the bar is the brief's number
def test_the_load_bar_is_the_briefs_2000ms_not_core_web_vitals_2500():
    """The stricter number wins. Widening it is founder-crucial, so the value is
    pinned here rather than left to a reviewer noticing a diff."""
    name, bar, unit, bar_row = ET.THRESHOLDS["largest-contentful-paint"]
    assert bar == 2000.0, "the brief's load bar is 2.0 s — 2500 would be a relaxation"
    assert unit == "ms" and "E1" in bar_row
    assert ET.THRESHOLDS["cumulative-layout-shift"][1] == 0.1
    assert ET.THRESHOLDS["total-blocking-time"][1] == 200.0
    assert ET.MAX_AXE_VIOLATIONS == 0, \
        "a bar that says WCAG 2.2 AA has no acceptable number of violations"


# --------------------------------------------------------- absent is never a pass
def test_a_missing_lighthouse_file_is_a_tool_error_not_a_pass(tmp_path):
    code = ET.main(["--lighthouse", str(tmp_path / "nope.json"),
                    "--axe", str(_write(tmp_path, "axe.json", _axe()))])
    assert code == 2


def test_a_missing_axe_file_is_a_tool_error_not_a_pass(tmp_path):
    code = ET.main(["--lighthouse", str(_write(tmp_path, "lh.json", _lh())),
                    "--axe", str(tmp_path / "nope.json")])
    assert code == 2


def test_unparseable_json_is_a_tool_error(tmp_path):
    bad = tmp_path / "lh.json"
    bad.write_text("{not json", encoding="utf-8")
    code = ET.main(["--lighthouse", str(bad),
                    "--axe", str(_write(tmp_path, "axe.json", _axe()))])
    assert code == 2


@pytest.mark.parametrize("metric", sorted(ET.THRESHOLDS))
def test_an_absent_metric_is_exit_2_never_a_silent_within_bar(tmp_path, metric):
    """A report lacking LCP must not be graded as fast — a fabricated measurement,
    and the convincing kind, because the other rows are real."""
    report = _lh()
    del report["audits"][metric]
    assert _run(tmp_path, report, _axe()) == 2


@pytest.mark.parametrize("metric", sorted(ET.THRESHOLDS))
def test_a_null_numeric_value_is_also_exit_2(tmp_path, metric):
    """Lighthouse emits the audit key with a null numericValue when a metric could
    not be gathered — present-but-unmeasured, which reads as measured."""
    assert _run(tmp_path, _lh(**{metric: None}), _axe()) == 2


def test_a_report_with_no_audits_object_is_exit_2(tmp_path):
    assert _run(tmp_path, {"categories": {}}, _axe()) == 2


def test_an_axe_report_of_an_unknown_shape_is_exit_2(tmp_path):
    """Refusing to grade a shape it does not understand, rather than reading zero
    violations out of it."""
    for shape in ({"results": []}, [{"url": "x"}], "a string", 42):
        assert _run(tmp_path, _lh(), shape) == 2, shape


def test_a_non_object_violation_entry_is_exit_2_not_a_crash(tmp_path):
    """`violation.get` on a string raises AttributeError, escaping as a traceback
    instead of the JudgeError this tool promises (PR #80)."""
    for bad in (["not-a-dict"], [42], [None], [["nested"]]):
        assert _run(tmp_path, _lh(), [{"violations": bad}]) == 2, bad
    # A non-list `violations` too.
    assert _run(tmp_path, _lh(), [{"violations": "many"}]) == 2


# ------------------------------------------------------------------- the verdicts
def test_everything_within_bar_exits_zero(tmp_path, capsys):
    assert _run(tmp_path, _lh(), _axe()) == 0
    out = capsys.readouterr().out
    assert "WITHIN BAR" in out and "OUTSIDE BAR" not in out
    assert "done-criterion 4" in out


@pytest.mark.parametrize("metric,value", [
    ("largest-contentful-paint", 2500.0),      # the CWV number, still over bar
    ("cumulative-layout-shift", 0.25),
    ("total-blocking-time", 400.0),
])
def test_a_metric_outside_bar_exits_one_and_names_it(tmp_path, capsys, metric, value):
    assert _run(tmp_path, _lh(**{metric: value}), _axe()) == 1
    out = capsys.readouterr().out
    assert "OUTSIDE BAR" in out
    human = ET.THRESHOLDS[metric][0]
    assert human in out, f"the failing metric must be named: {human}"


def test_a_metric_exactly_at_the_bar_is_within_it(tmp_path):
    """`<=`, not `<`. A bar of 2.0 s means 2.0 s passes; silently requiring
    better than the documented number is its own kind of dishonest gate."""
    assert _run(tmp_path, _lh(**{"largest-contentful-paint": 2000.0}), _axe()) == 0


def test_one_wcag_violation_fails_and_is_described(tmp_path, capsys):
    axe = _axe([{"id": "color-contrast", "impact": "serious",
                 "help": "Elements must meet minimum colour contrast",
                 "nodes": [{}, {}]}])
    assert _run(tmp_path, _lh(), axe) == 1
    out = capsys.readouterr().out
    assert "color-contrast" in out and "2 node(s)" in out
    assert "WCAG 2.2 AA violation" in out


def test_violations_across_multiple_pages_are_summed(tmp_path, capsys):
    axe = [{"violations": [{"id": "a", "nodes": []}]},
           {"violations": [{"id": "b", "nodes": []}]}]
    assert _run(tmp_path, _lh(), axe) == 1
    assert "| 2 |" in capsys.readouterr().out


def test_the_single_object_axe_shape_is_accepted(tmp_path):
    """The library emits one object; the CLI emits a list. Both are real."""
    assert _run(tmp_path, _lh(), {"violations": []}) == 0


def test_a_failing_run_refuses_to_offer_widening_as_a_remedy(tmp_path, capsys):
    """The remedy for a slow page is a faster page. A judge that suggests moving
    its own threshold is a gate arguing for its own relaxation."""
    _run(tmp_path, _lh(**{"largest-contentful-paint": 4000.0}), _axe())
    out = capsys.readouterr().out
    assert "Do not widen it" in out and "founder-crucial" in out


# ------------------------------------------------------------------ it is WIRED
def test_the_workflow_this_tool_names_actually_exists():
    """The blocker itself: the docstring named a workflow that was not in the tree,
    so the judge had nothing feeding it. Wire it or delete it (CLAUDE.md)."""
    named = ET.__doc__ or ""
    assert ".github/workflows/experience_metrics.yml" in named
    workflow = _ROOT / ".github" / "workflows" / "experience_metrics.yml"
    assert workflow.is_file(), \
        "the tool names this workflow as its caller — an absent caller is the " \
        "unwired-gate defect three reviewer lenses blocked on"


def test_the_workflow_invokes_this_tool_with_both_required_reports():
    text = (_ROOT / ".github" / "workflows" / "experience_metrics.yml").read_text(
        encoding="utf-8")
    assert "tools/experience_thresholds.py" in text
    assert "--lighthouse" in text and "--axe" in text
    assert "actions/checkout" in text, \
        "a step that runs a repo file needs the repo on the runner"


def test_the_workflow_lets_the_judge_decide_not_the_axe_exit_code():
    """`axe` exits non-zero on violations, so a bare invocation would end the job
    before the judge ran. The report's ABSENCE must still fail, though."""
    text = (_ROOT / ".github" / "workflows" / "experience_metrics.yml").read_text(
        encoding="utf-8")
    assert "|| true" in text
    assert "[ ! -s /tmp/axe.json ]" in text, \
        "swallowing axe's exit code without checking the report exists would " \
        "make 'axe crashed' look identical to 'axe found nothing'"
    assert "[ ! -s /tmp/lh.json ]" in text, \
        "the same check is needed for lighthouse, or a silent no-report run " \
        "reaches the judge as a missing file rather than a named failure"


def test_the_workflow_propagates_the_judges_exit_status():
    """A pipeline's exit status is its LAST command's, so piping the judge into
    `tee` would replace its verdict with tee's unconditional 0 — a blocking gate
    silently demoted to a report."""
    text = (_ROOT / ".github" / "workflows" / "experience_metrics.yml").read_text(
        encoding="utf-8")
    assert 'exit "$STATUS"' in text
    assert "experience_thresholds.py" in text
    judge_line = next(i for i, ln in enumerate(text.splitlines())
                      if "experience_thresholds.py" in ln and "python3" in ln)
    following = "\n".join(text.splitlines()[judge_line:judge_line + 4])
    assert "| tee" not in following, \
        "the judge's status must not be swallowed by a pipeline"
    assert "|| STATUS=$?" in following


def test_the_workflow_resolves_chromedriver_instead_of_assuming_an_env_var():
    """`$CHROMEWEBDRIVER` is runner-ambient, and depending on an ambient variable
    is the empty-env class this repo has hit four times — tools/workflow_env_lint.py
    failed this workflow for exactly that on its first run."""
    text = (_ROOT / ".github" / "workflows" / "experience_metrics.yml").read_text(
        encoding="utf-8")
    # The variable must not be CONSUMED. It is named in a comment explaining why
    # it is not consumed, which is the opposite of the defect — so the assertion
    # reads the code, not the prose around it.
    code = "\n".join(line for line in text.splitlines()
                     if not line.lstrip().startswith("#"))
    assert "CHROMEWEBDRIVER" not in code
    assert "command -v chromedriver" in code
    assert 'CHROMEDRIVER:?' in text, \
        "an absent chromedriver must fail closed, not skip the accessibility half"


def test_the_workflow_does_not_upload_the_raw_reports():
    """The bypass travels in the query string (the only form @axe-core/cli takes),
    so Lighthouse's report embeds it in `requestedUrl` — uploading that artefact
    would publish the secret to anyone who can read the run."""
    text = (_ROOT / ".github" / "workflows" / "experience_metrics.yml").read_text(
        encoding="utf-8")
    assert "upload-artifact" not in text
    assert "GITHUB_STEP_SUMMARY" in text, \
        "with no artefact, the step summary is the only record — it must exist"


def test_the_workflow_measures_the_FEED_not_the_redirect_stub():
    """`CLASS:missing-product-surface-verification` (PR #80). `/` is a 135-byte
    redirect; `/tonight` is the 6.6 kB page users read. Measuring the base URL
    would report E1-E4/P2 met with the real feed untested."""
    text = (_ROOT / ".github" / "workflows" / "experience_metrics.yml").read_text(
        encoding="utf-8")
    assert 'PAGE_PATH="/tonight"' in text
    assert '${BASE_URL}${PAGE_PATH}' in text, \
        "the measured target must include the page path, not just the base URL"
    # The step summary must name what was measured, or the recorded numbers are
    # ambiguous about which page produced them.
    assert '${BASE_URL}${PAGE_PATH}\\`' in text or "the feed surface" in text


def test_the_measuring_tools_are_version_pinned():
    """A Lighthouse minor can move LCP scoring, and this gate compares against a
    FIXED bar — unpinned, a bar met in July silently fails in August (PR #80)."""
    text = (_ROOT / ".github" / "workflows" / "experience_metrics.yml").read_text(
        encoding="utf-8")
    install = next(line for line in text.splitlines()
                   if "npm install" in line and "lighthouse" in line)
    assert "lighthouse@" in install, f"lighthouse must be pinned: {install!r}"
    assert "@axe-core/cli@" in install, f"axe must be pinned: {install!r}"


def test_the_workflow_parses_and_declares_the_triggers_it_claims():
    path = _ROOT / ".github" / "workflows" / "experience_metrics.yml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    triggers = doc.get("on", doc.get(True))
    assert set(triggers) == {"deployment_status", "workflow_dispatch"}
    assert triggers["workflow_dispatch"]["inputs"]["url"]["required"] is True
