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


# ---- strict path grammar + candidate identity (PR #37 r6) ------------------

SUBJECT = "0123456789abcdef0123456789abcdef01234567"


def test_grammar_accepts_only_literal_and_dir_glob():
    assert ce._match_pattern("ai/**", "ai/golden/x.json") is True
    assert ce._match_pattern("ai/**", "ai") is True
    assert ce._match_pattern("ai/**", "aisle/x.json") is False
    assert ce._match_pattern("tools/trust_gate.py", "tools/trust_gate.py") is True
    for bad in ("ai/*.py", "**/x.py", "ai/**/y.py", "a?b", "a[0-9]"):
        with pytest.raises(ValueError):
            ce._match_pattern(bad, "anything")


def test_unsupported_pattern_fails_closed_even_when_other_patterns_hit():
    """Validation covers EVERY pattern — a hit on a good pattern must not
    mask an unsupported one riding in the same policy."""
    with pytest.raises(ValueError):
        ce.surface_touched(["ai/**", "ai/*.py"], ["ai/golden/x.json"])


def _run_obj(**overrides):
    run = {
        "path": ".github/workflows/extraction-eval.yml",
        "event": "pull_request_target",
        "head_sha": SUBJECT,
        "run_started_at": "2026-07-18T21:05:14Z",
        "pull_requests": [{"number": 37}],
    }
    run.update(overrides)
    return run


_EPOCH_BEFORE_RUN = 1784000000   # before the run_started_at above (1784408714)
_EPOCH_AFTER_RUN = 9999999999    # after it — i.e., base advanced later


def test_candidate_valid_accepts_matching_fresh_run():
    job = {"head_sha": SUBJECT}
    assert ce.candidate_valid(job, _run_obj(), SUBJECT, 37, _EPOCH_BEFORE_RUN) is True


def test_candidate_rejections():
    job = {"head_sha": SUBJECT}
    cases = [
        (_run_obj(path=".github/workflows/other.yml"), 37, _EPOCH_BEFORE_RUN),
        (_run_obj(event="pull_request"), 37, _EPOCH_BEFORE_RUN),
        (_run_obj(head_sha="e" * 40), 37, _EPOCH_BEFORE_RUN),
        (_run_obj(run_started_at=None), 37, _EPOCH_BEFORE_RUN),
        (_run_obj(run_started_at="not-a-time"), 37, _EPOCH_BEFORE_RUN),
        # Stale run: base head commit is NEWER than the run start (r6).
        (_run_obj(), 37, _EPOCH_AFTER_RUN),
        # Populated pull_requests without this PR's number.
        (_run_obj(pull_requests=[{"number": 99}]), 37, _EPOCH_BEFORE_RUN),
    ]
    for run, prn, epoch in cases:
        assert ce.candidate_valid(job, run, SUBJECT, prn, epoch) is False, run
    # job head mismatch
    assert ce.candidate_valid({"head_sha": "f" * 40}, _run_obj(), SUBJECT,
                              37, _EPOCH_BEFORE_RUN) is False
    # Empty pull_requests list is tolerated (API quirk) — other bindings hold.
    assert ce.candidate_valid({"head_sha": SUBJECT},
                              _run_obj(pull_requests=[]), SUBJECT,
                              37, _EPOCH_BEFORE_RUN) is True


def test_cli_candidate_valid(tmp_path, capsys):
    jp = tmp_path / "job.json"; jp.write_text(json.dumps({"head_sha": SUBJECT}), encoding="utf-8")
    rp = tmp_path / "run.json"; rp.write_text(json.dumps(_run_obj()), encoding="utf-8")
    assert ce.main(["candidate-valid", str(jp), str(rp), SUBJECT, "37",
                    str(_EPOCH_BEFORE_RUN)]) == 0
    assert capsys.readouterr().out.strip() == "1"
    assert ce.main(["candidate-valid", str(jp), str(rp), SUBJECT, "37",
                    str(_EPOCH_AFTER_RUN)]) == 0
    assert capsys.readouterr().out.strip() == "0"
    assert ce.main(["candidate-valid", str(jp), str(rp), SUBJECT,
                    "not-a-number", "0"]) == 1
    capsys.readouterr()
