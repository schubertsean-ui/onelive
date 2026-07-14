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
