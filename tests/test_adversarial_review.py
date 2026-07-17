"""Tests for tools/adversarial_review.py — the non-Claude evaluator gate.

Hermetic: no network, no OpenAI key. The transport (`_post_json`) is
monkeypatched; git interaction is avoided via --diff-file. Proves the verdict
parse is strict (ambiguity = hard failure, never a pass), the skip-without-key
path stays loud but non-blocking unless --require, and exit codes follow the
tools/README.md 0/1/2 convention.
"""
import importlib.util
import pathlib
import sys

import pytest

_TOOL_PATH = (
    pathlib.Path(__file__).resolve().parent.parent / "tools" / "adversarial_review.py"
)
_spec = importlib.util.spec_from_file_location("adversarial_review", _TOOL_PATH)
ar = importlib.util.module_from_spec(_spec)
sys.modules["adversarial_review"] = ar
_spec.loader.exec_module(ar)

_DIFF = "diff --git a/x.py b/x.py\n+print('hi')\n"


def _diff_file(tmp_path):
    p = tmp_path / "change.patch"
    p.write_text(_DIFF)
    return str(p)


def _fake_response(text):
    return {"choices": [{"message": {"content": text}}]}


def test_parse_verdict_approve_and_request_changes():
    assert ar.parse_verdict("looks good\nVERDICT: APPROVE") == ar.APPROVE
    assert (
        ar.parse_verdict("a.py:3 — bug\nVERDICT: REQUEST-CHANGES")
        == ar.REQUEST_CHANGES
    )


@pytest.mark.parametrize(
    "text",
    [
        "no verdict at all",
        "VERDICT: APPROVE\nVERDICT: REQUEST-CHANGES",  # two verdicts = ambiguous
        "VERDICT: MAYBE",
        # Evaluator finding (PR #11 round 1): the verdict must be the FINAL
        # line — trailing prose could contradict or launder it.
        "VERDICT: APPROVE\nbut actually I have grave concerns",
    ],
)
def test_parse_verdict_rejects_ambiguity(text):
    with pytest.raises(ValueError):
        ar.parse_verdict(text)


def test_require_mode_refuses_truncated_diff(tmp_path, monkeypatch, capsys):
    """Evaluator finding (PR #11 round 1): a partial diff is not a review —
    in --require (CI) mode an over-limit diff is a hard failure, never a
    silent truncation the reviewer can't see past."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        ar, "_post_json", lambda *a, **k: _fake_response("fine\nVERDICT: APPROVE")
    )
    big = tmp_path / "big.patch"
    big.write_text("x" * 500)
    args = ["--diff-file", str(big), "--max-diff-bytes", "100"]
    assert ar.main(args + ["--require"]) == 2
    assert "truncated" in capsys.readouterr().err
    # Without --require (local/advisory use) the same diff truncates and runs.
    assert ar.main(args) == 0


def test_build_review_input_includes_diff_logs_and_truncates():
    body = ar.build_review_input(_DIFF, [("pytest.log", "218 passed")])
    assert _DIFF in body and "pytest.log" in body and "218 passed" in body

    huge = "x" * 500
    truncated = ar.build_review_input(huge, [], max_diff_bytes=100)
    assert ar._TRUNCATION_MARKER.strip() in truncated
    assert "unverified code is a claim" in ar.build_review_input(_DIFF, [])


def test_missing_key_skips_loud_but_requires_flag_hard_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert ar.main(["--diff-file", _diff_file(tmp_path)]) == 0
    assert "SKIPPED-loud" in capsys.readouterr().err
    assert ar.main(["--diff-file", _diff_file(tmp_path), "--require"]) == 2
    assert "HARD FAIL" in capsys.readouterr().err


def test_exit_codes_follow_verdict(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        ar, "_post_json", lambda *a, **k: _fake_response("fine\nVERDICT: APPROVE")
    )
    assert ar.main(["--diff-file", _diff_file(tmp_path)]) == 0

    monkeypatch.setattr(
        ar,
        "_post_json",
        lambda *a, **k: _fake_response("x.py:1 — bad\nVERDICT: REQUEST-CHANGES"),
    )
    assert ar.main(["--diff-file", _diff_file(tmp_path)]) == 1


def test_unset_model_env_uses_default(tmp_path, monkeypatch):
    """Truly-UNSET model/base-url env means the documented defaults."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_REVIEW_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    sent = {}

    def _capture(url, payload, api_key, timeout=300):
        sent["url"] = url
        sent["model"] = payload["model"]
        return _fake_response("fine\nVERDICT: APPROVE")

    monkeypatch.setattr(ar, "_post_json", _capture)
    assert ar.main(["--diff-file", _diff_file(tmp_path)]) == 0
    assert sent["model"] == ar.DEFAULT_MODEL
    assert sent["url"].startswith(ar.DEFAULT_BASE_URL)


def test_empty_model_env_var_hard_fails(tmp_path, monkeypatch, capsys):
    """Fail-closed (supersedes the first-live-run fallback behavior): a
    PRESENT-but-empty OPENAI_REVIEW_MODEL is a misconfiguration on the
    trust-critical review path and must hard-fail, never silently mean the
    default. The workflow expresses 'unset' by not exporting the var."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    def _explode(*a, **k):
        raise AssertionError("no API call may happen on misconfigured env")

    monkeypatch.setattr(ar, "_post_json", _explode)
    for empty in ("", "   "):
        monkeypatch.setenv("OPENAI_REVIEW_MODEL", empty)
        assert ar.main(["--diff-file", _diff_file(tmp_path)]) == 2
        assert "set but empty" in capsys.readouterr().err
    monkeypatch.delenv("OPENAI_REVIEW_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    assert ar.main(["--diff-file", _diff_file(tmp_path)]) == 2


def test_generator_family_review_model_hard_fails(tmp_path, monkeypatch, capsys):
    """Trust invariant (charter §0.2), enforced at the reviewer's OWN entry
    point: a Claude/Anthropic model in OPENAI_REVIEW_MODEL means the generator
    would grade its own work — hard fail (exit 2) BEFORE any API call."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def _explode(*a, **k):
        raise AssertionError("no API call may happen with a generator-family model")

    monkeypatch.setattr(ar, "_post_json", _explode)
    for bad in ("claude-opus-4-8", "Claude-Sonnet-4-6", "anthropic/claude-haiku-4-5"):
        monkeypatch.setenv("OPENAI_REVIEW_MODEL", bad)
        assert ar.main(["--diff-file", _diff_file(tmp_path)]) == 2
        assert "write/grade separation" in capsys.readouterr().err


def test_http_error_body_is_surfaced(monkeypatch):
    """Regression (first live CI run): a bare 'HTTP Error 400' is undiagnosable;
    the API's error body must reach the failure message."""
    import io
    import urllib.error

    def _boom(req, timeout):
        raise urllib.error.HTTPError(
            "https://api.example/v1/chat/completions", 400, "Bad Request",
            hdrs=None, fp=io.BytesIO(b'{"error": {"message": "you must provide a model"}}'),
        )

    monkeypatch.setattr(ar.urllib.request, "urlopen", _boom)
    with pytest.raises(RuntimeError, match="you must provide a model"):
        ar._post_json("https://api.example/v1/chat/completions", {}, "k")


def test_ambiguous_verdict_and_empty_diff_are_hard_failures(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ar, "_post_json", lambda *a, **k: _fake_response("shrug"))
    assert ar.main(["--diff-file", _diff_file(tmp_path)]) == 2

    empty = tmp_path / "empty.patch"
    empty.write_text("   \n")
    assert ar.main(["--diff-file", str(empty)]) == 2


def test_attended_job_mirrors_review_job():
    """Key-custody shape of the reviewer workflow (PR #32 r5-r13), held
    mechanically:
      * subject-checks — SECRETLESS, the only job where PR code runs;
      * adversarial-review — keyed, base-owned (pull_request_target),
        executes base code only, consumes subject logs as an artifact;
      * attended-review — dispatch-only, environment-scoped key.
    Shared steps are byte-identical mirrors; every documented divergence
    is asserted for its specific safety property, never skipped."""
    import pathlib
    import shlex

    import yaml

    wf = yaml.safe_load(
        (pathlib.Path(__file__).resolve().parent.parent
         / ".github" / "workflows" / "adversarial-review.yml").read_text())
    assert set(wf["jobs"]) == {"subject-checks", "adversarial-review",
                               "attended-review"}
    # pull_request_target, never plain pull_request (the PR's workflow
    # copy must never run) — note: YAML 1.1 parses the bare `on` key as
    # boolean True.
    triggers = wf.get("on") or wf.get(True)
    assert "pull_request_target" in triggers and "pull_request" not in triggers

    def key(s):
        return s.get("name") or s.get("uses", "").split("@")[0]

    RANGE = "Resolve the base ref and diff range"
    PIN = "Pin the TRUSTED evaluator script from the base ref (or hard-fail)"
    DEPS = "Install worker + api deps"
    TESTS = "Test suite (log captured for the evaluator)"
    WEB = "Web checks + SCA when web/ is touched (log captured for the evaluator)"
    DIFF = "Extract the diff under review (lockfiles excluded by policy)"
    EVAL = "Independent evaluator (APPROVE required)"
    FETCH = ("Fetch the bound release-gate output for exam_head_sha "
             "(fail loud on ANY anomaly)")
    GUARD = ("Refuse to run off the default branch (attended reviews "
             "execute trusted code only)")
    SCOPE = "Enforce attended-review scope — data-only diffs (fail closed)"
    PROOF = ("Prove the attended-review environment's deployment-branch "
             "policy is ACTIVE (fail closed)")

    subj = wf["jobs"]["subject-checks"]
    rev = wf["jobs"]["adversarial-review"]
    att = wf["jobs"]["attended-review"]
    subj_steps = {key(s): s for s in subj["steps"]}
    rev_steps = {key(s): s for s in rev["steps"]}
    att_steps = {key(s): s for s in att["steps"]}

    assert [key(s) for s in subj["steps"]] == [
        "actions/checkout", "actions/setup-python", RANGE, DEPS, TESTS,
        WEB, "actions/upload-artifact"]
    assert [key(s) for s in rev["steps"]] == [
        "actions/checkout", "actions/setup-python", RANGE, PIN,
        "actions/download-artifact", DIFF, EVAL]
    assert [key(s) for s in att["steps"]] == [
        PROOF, "actions/checkout", "actions/setup-python", GUARD, RANGE,
        SCOPE, PIN, DEPS, TESTS, WEB, FETCH, DIFF, EVAL]

    # Byte-identical mirrors (each divergence below is asserted, not skipped)
    for k in (DEPS, TESTS):
        assert subj_steps[k] == att_steps[k], f"attended step drifted: {k}"
    for k in (PIN, DIFF):
        assert rev_steps[k] == att_steps[k], f"attended step drifted: {k}"

    # KEY CUSTODY — the load-bearing assertions:
    # 1. subject-checks: no secret of any kind beyond the ambient token.
    assert "OPENAI" not in str(subj), "subject-checks must stay secretless"
    # 2. the keyed review job runs NO PR code: no deps/tests/web steps,
    #    and its checkout takes no PR-head ref.
    for banned in (DEPS, TESTS, WEB):
        assert banned not in rev_steps, f"PR-executing step in keyed job: {banned}"
    assert "ref" not in (rev["steps"][0].get("with") or {}),         "keyed job checkout must be the base (no PR-head ref)"
    # 3. subject job checks out the PR head; keyed job only FETCHES it as data.
    assert "head.sha" in str(subj["steps"][0].get("with", {}).get("ref", ""))
    assert "fetch --no-tags origin" in rev_steps[RANGE]["run"]         and "head.sha" in rev_steps[RANGE]["run"]
    # 4. key placement: repo key only in the base-owned review job's
    #    evaluator step; environment key only in attended.
    assert rev_steps[EVAL].get("env", {}).get("OPENAI_API_KEY")         == "${{ secrets.OPENAI_API_KEY }}"
    assert att_steps[EVAL].get("env", {}).get("OPENAI_API_KEY")         == "${{ secrets.OPENAI_API_KEY_ATTENDED }}"
    assert att.get("environment") == "attended-review"
    # 5. review job gated on the subject job's success.
    assert rev.get("needs") == ["subject-checks"] and "success" in rev["if"]

    # attended divergences (asserted properties)
    assert "$EXAM_HEAD" in att_steps[RANGE]["run"]         and "origin/$DEFAULT_BRANCH...$EXAM_HEAD" in att_steps[RANGE]["run"]
    assert "Refusing to attach logs" in att_steps[WEB]["run"]         and "exit 1" in att_steps[WEB]["run"]
    assert "refs/heads/$DEFAULT_BRANCH" in att_steps[GUARD]["run"]         and "exit 1" in att_steps[GUARD]["run"]
    scope_run = att_steps[SCOPE]["run"]
    for needed in ("ai/prompts.py", "tools/routing_data.py", "docs/*",
                   "exit 1"):
        assert needed in scope_run
    assert "web/" not in scope_run.replace("web validation", "")

    # evaluator invocations compared structurally (r6: substring checks
    # green-lit a broken continuation once).
    def evaluator_argv(run_text):
        cmds = [l for l in run_text.splitlines() if l.strip()]
        argv = [a for a in shlex.split(run_text) if a.strip()]
        assert "\\" not in argv, f"broken line continuation in: {cmds}"
        assert argv[0] == "python" and argv[1] == "-I"
        return argv

    def attached_logs(argv):
        return [argv[i + 1] for i, a in enumerate(argv[:-1])
                if a == "--test-log"]

    rev_argv = evaluator_argv(rev_steps[EVAL]["run"])
    att_argv = evaluator_argv(att_steps[EVAL]["run"])
    assert attached_logs(rev_argv) == ["pytest.log", "web.log"]
    assert attached_logs(att_argv) == ["pytest.log", "web.log",
                                       "exam-evidence.log"]
    idx = att_argv.index("exam-evidence.log")
    assert att_argv[idx - 1] == "--test-log"
    assert att_argv[:idx - 1] + att_argv[idx + 1:] == rev_argv,         "attended evaluator invocation drifted beyond the evidence log"
