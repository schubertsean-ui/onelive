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


# --- v2 lens panel, po battery, scorecard (Contract #26) ----------------------

def test_po_provocations_are_deterministic_and_seed_varying():
    # Founder-directed: rotating seed, auditable. Same seed = same battery;
    # different seed = different (the head SHA rotates it per run).
    assert ar.po_provocations("seedA") == ar.po_provocations("seedA")
    assert ar.po_provocations("seedA") != ar.po_provocations("deadbeef")
    prov = ar.po_provocations("abc123")
    assert len(prov) == 3 and all(p.startswith("[") for p in prov)


def test_panel_requires_a_po_seed(tmp_path, capsys, monkeypatch):
    # A panel without a printed seed is a misconfiguration, not a default.
    # monkeypatch, not raw os.environ (#71 r6 nit): the rest of this suite
    # is hermetic by construction rather than by a finally block.
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    rc = ar.main(["--panel", "--diff-file", _diff_file(tmp_path)])
    assert rc == 2
    assert "requires --po-seed" in capsys.readouterr().err


def test_panel_any_lens_red_is_red():
    # Verdict physics: a strict tightening of v1 — one red lens reddens the
    # panel even if every other lens approves.
    def all_approve(ri, sp):
        return "fine\nVERDICT: APPROVE"

    def one_red(ri, sp):
        return "CLASS:x a.py:1 — bug\nVERDICT: REQUEST-CHANGES" if "ABSENCE" in sp else "ok\nVERDICT: APPROVE"

    verdict, outputs = ar.run_panel(
        "input", "seed", openai_key="k", model="gpt-5.5", base_url="u",
        gemini_key=None, request_openai=one_red, request_gemini=None)
    assert verdict == ar.REQUEST_CHANGES
    verdict2, _ = ar.run_panel(
        "input", "seed", openai_key="k", model="gpt-5.5", base_url="u",
        gemini_key=None, request_openai=all_approve, request_gemini=None)
    assert verdict2 == ar.APPROVE


def test_panel_absent_gemini_seat_is_explicit_never_silent():
    def approve(ri, sp):
        return "ok\nVERDICT: APPROVE"

    verdict, outputs = ar.run_panel(
        "input", "seed", openai_key="k", model="m", base_url="u",
        gemini_key=None, request_openai=approve, request_gemini=None)
    joined = "\n".join(outputs)
    assert "SEAT gemini: EMPTY" in joined  # printed, not skipped silently
    assert verdict == ar.APPROVE  # never fails a PR for an unminted key


def test_panel_gemini_seat_runs_when_key_present():
    calls = {"openai": 0, "gemini": 0}

    def oa(ri, sp):
        calls["openai"] += 1
        return "ok\nVERDICT: APPROVE"

    def gm(ri, sp):
        calls["gemini"] += 1
        return "ok\nVERDICT: APPROVE"

    verdict, outputs = ar.run_panel(
        "input", "seed", openai_key="k", model="m", base_url="u",
        gemini_key="gk", request_openai=oa, request_gemini=gm)
    assert calls == {"openai": 2, "gemini": 2}  # two lenses per seat
    assert verdict == ar.APPROVE


def test_panel_unparseable_lens_is_hard_failure():
    def hedged(ri, sp):
        return "maybe\nVERDICT: MAYBE"  # not a valid verdict

    with pytest.raises(ValueError, match="ambiguous"):
        ar.run_panel("input", "seed", openai_key="k", model="m", base_url="u",
                     gemini_key=None, request_openai=hedged, request_gemini=None)


def test_v2_prompt_encodes_the_ratified_escape_hatch_and_class_mandate():
    p = ar.V2_DISCIPLINE
    assert "MUST block, in any round" in p  # the invariant obligation
    assert "why it was not findable in round 1" in p  # structured discretion
    assert "CLASS:<kebab-token>" in p  # sibling-enumeration mandate
    assert "RECOMMEND-RECORD" in p  # scope -> record, not blocker


def test_single_lens_path_keeps_the_v1_prompt_unpolluted():
    # #71 r3 blocker: the bootstrap/fallback story claims "--panel absent
    # = v1 unchanged". The v2 discipline must therefore live OUTSIDE
    # SYSTEM_PROMPT and reach the model only through lens composition.
    assert "REVIEW DISCIPLINE" not in ar.SYSTEM_PROMPT
    assert "CLASS:<kebab-token>" not in ar.SYSTEM_PROMPT
    assert ar.SYSTEM_PROMPT.rstrip().endswith("VERDICT: REQUEST-CHANGES")


def test_panel_lens_prompts_carry_v1_plus_discipline_plus_lens():
    seen = []

    def fake(review_input, system_prompt):
        seen.append(system_prompt)
        return "finding\nVERDICT: APPROVE"

    verdict, _ = ar.run_panel("diff", "seed", "k", "m", "u", None,
                              request_openai=fake, request_gemini=fake)
    assert verdict == ar.APPROVE
    assert seen, "no lens ran"
    for prompt in seen:
        assert prompt.startswith(ar.SYSTEM_PROMPT)      # v1 bar intact
        assert "REVIEW DISCIPLINE" in prompt            # v2 discipline added
        assert "FORCED LENS" in prompt                  # method constraint added


def test_env_model_resolver_fails_closed_on_claude_and_empty(monkeypatch):
    monkeypatch.setenv("GEMINI_REVIEW_MODEL", "")
    with pytest.raises(RuntimeError, match="empty"):
        ar._resolve_env_model("GEMINI_REVIEW_MODEL", "gemini-2.5-pro")
    monkeypatch.setenv("GEMINI_REVIEW_MODEL", "claude-3")
    with pytest.raises(RuntimeError, match="non-Claude"):
        ar._resolve_env_model("GEMINI_REVIEW_MODEL", "gemini-2.5-pro")
    monkeypatch.delenv("GEMINI_REVIEW_MODEL", raising=False)
    assert ar._resolve_env_model("GEMINI_REVIEW_MODEL", "gemini-2.5-pro") == "gemini-2.5-pro"


def test_panel_prints_its_own_po_seed_and_provocations():
    # #71 r10 nit: the CLI contract says the po seed is auditable, so the
    # TOOL must emit it — relying on the caller's workflow to echo it
    # makes the audit trail depend on something outside the tool.
    _, outputs = ar.run_panel(
        "input", "deadbeef", openai_key="k", model="gpt-5.5", base_url="u",
        gemini_key=None,
        request_openai=lambda ri, sp: "ok\nVERDICT: APPROVE",
        request_gemini=None)
    header = outputs[0]
    assert "PO SEED: deadbeef" in header
    for provocation in ar.po_provocations("deadbeef"):
        assert provocation in header


def test_workflow_second_seat_model_matches_the_tools_default():
    # #72 r2, hardening the workflow-tool-version-skew fix after it
    # RECURRED past its first marker. That first fix hardened CLI FLAGS
    # only (feature-detect --panel); the class is broader — ANY value a
    # PR changes in the BASE-owned reviewer is invisible to the run
    # judging that PR, constants included. The workflow literal is the
    # PR-owned compensation, which introduces a second place holding the
    # same value. This pins them together so the pair can never drift:
    # change one, this test names the other.
    import pathlib as _pathlib
    import re as _re

    workflow = (_pathlib.Path(ar.__file__).parent.parent / ".github"
                / "workflows" / "adversarial-review.yml").read_text()
    match = _re.search(r"^\s*GEMINI_REVIEW_MODEL:\s*(\S+)\s*$", workflow,
                       _re.MULTILINE)
    assert match, ("the workflow must pin the second seat's model explicitly — "
                   "without it the base-owned copy's older default silently wins")
    assert match.group(1) == ar.GEMINI_DEFAULT_MODEL, (
        f"workflow pins {match.group(1)!r} but the tool defaults to "
        f"{ar.GEMINI_DEFAULT_MODEL!r} — these move together, in one PR")
