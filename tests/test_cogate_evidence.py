"""Tests for tools/cogate_evidence.py — the review workflow's co-gate
evidence judgments (PR #37 r5: security-critical gate logic must be
tested code that can actually fail, not a shell one-liner).

Every acceptance ground is falsified independently: wrong conclusion,
second failed step (annotated or NOT — the r5 blocker), wrong failing
step, mixed annotations, empty annotations, and the surface-grammar
fail-closed branches."""
import json
import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from tools import cogate_evidence as ce

REFUSAL = ("##[error]This PR changes extraction HARNESS code that the "
           "attended exam does not execute, so prompt-swap evidence cannot "
           "certify it: tools/trust_gate.py. Split the harness change...")
GENERIC = "##[error]Process completed with exit code 1."


def _job(*steps):
    return {"steps": [{"name": n, "conclusion": c} for n, c in steps]}


def _refusal_job(extra=()):
    steps = [("Set up job", "success"),
             ("Install worker deps (for the BASE verifier's threshold imports)", "success"),
             (ce.CLASSIFY_STEP, "failure"),
             ("Lift subject expectations as data (BASE extractors, subject files)", "skipped")]
    steps.extend(extra)
    return _job(*steps)


def test_pure_designed_refusal_accepted():
    log = f"echo of script text\n{REFUSAL}\n{GENERIC}\n"
    assert ce.refusal_only(_refusal_job(), log, "failure") is True


def test_non_failure_conclusions_rejected():
    log = f"{REFUSAL}\n{GENERIC}\n"
    for concl in ("cancelled", "timed_out", "action_required",
                  "startup_failure", "success", "neutral", "none"):
        assert ce.refusal_only(_refusal_job(), log, concl) is False, concl


def test_second_failed_step_rejected_even_without_annotation():
    """The r5 blocker: a refusal annotation plus a second failing step
    whose failure wrote NO ##[error] line must still be rejected — step
    conclusions are the ground truth, not log text."""
    job = _refusal_job(extra=[("Authenticate the changed certification record against its attended run (BASE code, fail closed)", "failure")])
    log = f"{REFUSAL}\nTraceback (most recent call last):\n  boom\n{GENERIC}\n"
    assert ce.refusal_only(job, log, "failure") is False


def test_wrong_failing_step_rejected():
    job = _job(("Set up job", "success"),
               ("Verify attended exam evidence binds to this head (BASE verifier, fail closed)", "failure"))
    log = f"{REFUSAL}\n{GENERIC}\n"
    assert ce.refusal_only(job, log, "failure") is False


def test_mixed_annotations_rejected():
    log = (f"{REFUSAL}\n"
           "##[error]certification record REJECTED: run not found (fail closed)\n"
           f"{GENERIC}\n")
    assert ce.refusal_only(_refusal_job(), log, "failure") is False


def test_no_annotations_rejected():
    """A classify-step crash (traceback, no ::error:: refusal) fails."""
    log = f"Traceback (most recent call last):\n  boom\n{GENERIC}\n"
    assert ce.refusal_only(_refusal_job(), log, "failure") is False


def test_script_echo_of_rejection_text_does_not_false_positive():
    """The runner echoes step SOURCE into the log — literal REJECTED text
    inside echoed code must not disqualify a pure refusal."""
    log = ('\x1b[36;1mdie(f"::error::certification record REJECTED: {msg}")\x1b[0m\n'
           f"{REFUSAL}\n{GENERIC}\n")
    assert ce.refusal_only(_refusal_job(), log, "failure") is True


def test_missing_or_empty_steps_rejected():
    assert ce.refusal_only({}, REFUSAL, "failure") is False
    assert ce.refusal_only({"steps": []}, REFUSAL, "failure") is False


def test_surface_touched_grammar():
    pats = ["ai/**", "tools/trust_gate.py"]
    assert ce.surface_touched(pats, ["ai/golden/CERTIFIED_HARNESS.json"]) is True
    assert ce.surface_touched(pats, ["tools/trust_gate.py"]) is True
    assert ce.surface_touched(pats, ["docs/RECORD.md", "web/app.tsx"]) is False


def test_surface_grammar_fails_closed():
    with pytest.raises(ValueError):
        ce.surface_touched(["ai/**", "!ai/golden/**"], ["x"])
    with pytest.raises(ValueError):
        ce.surface_touched([], ["x"])
    with pytest.raises(ValueError):
        ce.surface_touched("ai/**", ["x"])


def test_cli_refusal_only(tmp_path, capsys):
    jp = tmp_path / "job.json"
    jp.write_text(json.dumps(_refusal_job()), encoding="utf-8")
    lp = tmp_path / "log.txt"
    lp.write_text(f"{REFUSAL}\n{GENERIC}\n", encoding="utf-8")
    assert ce.main(["refusal-only", str(jp), str(lp), "failure"]) == 0
    assert capsys.readouterr().out.strip() == "1"
    assert ce.main(["refusal-only", str(jp), str(lp), "cancelled"]) == 0
    assert capsys.readouterr().out.strip() == "0"
    assert ce.main(["refusal-only", str(tmp_path / "absent.json"), str(lp), "failure"]) == 1
    capsys.readouterr()


def test_cli_surface_touched(tmp_path, capsys):
    wf = tmp_path / "wf.yml"
    wf.write_text("on:\n  pull_request_target:\n    paths:\n      - \"ai/**\"\n",
                  encoding="utf-8")
    fl = tmp_path / "files.txt"
    fl.write_text("ai/golden/CERTIFIED_HARNESS.json\n", encoding="utf-8")
    assert ce.main(["surface-touched", str(wf), str(fl)]) == 0
    assert capsys.readouterr().out.strip() == "1"
    fl.write_text("docs/x.md\n", encoding="utf-8")
    assert ce.main(["surface-touched", str(wf), str(fl)]) == 0
    assert capsys.readouterr().out.strip() == "0"
