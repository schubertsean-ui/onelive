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


def test_panel_lenses_run_CONCURRENTLY_not_one_after_another():
    """Four large-diff model calls in series was 7-25 minutes per round — most
    of this project's review latency, and enough to distort what gets built.

    The lenses never see each other's output by design, so nothing about the
    review depends on their order. This pins that they actually overlap: each
    stub blocks until all of them have arrived, which can only complete if
    they run at the same time.
    """
    import threading
    started = threading.Barrier(4, timeout=10)

    def lens(ri, sp):
        started.wait()          # deadlocks (BrokenBarrier) if run serially
        return "ok\nVERDICT: APPROVE"

    verdict, _ = ar.run_panel(
        "input", "seed", openai_key="k", model="m", base_url="u",
        gemini_key="gk", request_openai=lens, request_gemini=lens)
    assert verdict == ar.APPROVE


def test_panel_output_order_is_STABLE_regardless_of_which_lens_finishes_first():
    """A transcript whose sections move between runs cannot be diffed, and the
    seat/lens order is how a reader finds a finding again."""
    import time

    def slow(ri, sp):
        time.sleep(0.05)        # openai seat finishes LAST
        return "slow\nVERDICT: APPROVE"

    def fast(ri, sp):
        return "fast\nVERDICT: APPROVE"

    _, outputs = ar.run_panel(
        "input", "seed", openai_key="k", model="m", base_url="u",
        gemini_key="gk", request_openai=slow, request_gemini=fast)
    seats = [line.split("/")[0].strip() for line in outputs
             if line.startswith("### SEAT")]
    assert seats == ["### SEAT openai", "### SEAT openai",
                     "### SEAT gemini", "### SEAT gemini"]


def test_a_lens_that_RAISES_still_hard_fails_the_panel_when_run_concurrently():
    """Concurrency must not turn a lens error into a swallowed result — a panel
    that loses a lens and still approves is a gate that stopped being one."""
    def boom(ri, sp):
        raise RuntimeError("upstream 500")

    def ok(ri, sp):
        return "ok\nVERDICT: APPROVE"

    with pytest.raises(RuntimeError, match="upstream 500"):
        ar.run_panel("input", "seed", openai_key="k", model="m", base_url="u",
                     gemini_key="gk", request_openai=boom, request_gemini=ok)


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


def test_the_workflow_NEVER_supplies_the_second_seat_model():
    # #72 r8 BLOCKER, the invariant that replaced a drift check: this
    # workflow file is PR-OWNED, so anything it sets is chosen by the diff
    # under review. Supplying GEMINI_REVIEW_MODEL let the subject pick the
    # model of the seat judging it. The earlier test compared the workflow
    # literal to the tool default — two PR-controlled copies — which
    # catches an accident and never an attacker, and worse, REQUIRED the
    # override to exist. The invariant now is absence: neither seat's
    # model may come from this file.
    import pathlib

    workflow = (pathlib.Path(ar.__file__).parent.parent / ".github" / "workflows"
                / "adversarial-review.yml").read_text()
    for line in workflow.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue  # prose explaining WHY it is absent is not a setting
        assert not stripped.startswith("GEMINI_REVIEW_MODEL:"), (
            "the PR-owned workflow must not set the second seat's model — "
            "the reviewed subject must not choose any input to the review "
            "judging it (class: self-weakenable-review-model)")
        assert not stripped.startswith("OPENAI_REVIEW_MODEL:"), (
            "same rule for the first seat (PR #14 r4)")


def test_second_seat_model_override_is_allowlisted_by_the_BASE_copy(monkeypatch):
    # #72 r8 BLOCKER (class: self-weakenable-review-model): the workflow
    # that sets GEMINI_REVIEW_MODEL is PR-owned, so without a base-owned
    # allowlist the diff under review could name the model that reviews
    # it — an attacker picks the weakest callable Gemini id and
    # self-certifies. An override may SELECT a blessed model, never
    # introduce one.
    blessed = sorted(ar.GEMINI_ALLOWED_MODELS)[0]
    monkeypatch.setenv("GEMINI_REVIEW_MODEL", blessed)
    assert ar._resolve_env_model("GEMINI_REVIEW_MODEL", ar.GEMINI_DEFAULT_MODEL,
                                 ar.GEMINI_ALLOWED_MODELS) == blessed

    monkeypatch.setenv("GEMINI_REVIEW_MODEL", "gemini-1.0-tiny-whatever")
    with pytest.raises(RuntimeError, match="NOT in the base-owned allowlist"):
        ar._resolve_env_model("GEMINI_REVIEW_MODEL", ar.GEMINI_DEFAULT_MODEL,
                              ar.GEMINI_ALLOWED_MODELS)


def test_the_shipped_default_is_itself_allowlisted():
    # A default outside its own allowlist would fail every unset run.
    assert ar.GEMINI_DEFAULT_MODEL in ar.GEMINI_ALLOWED_MODELS


def test_the_OPENAI_seat_model_is_NOT_overridable_in_CI():
    # The anchor property that bounds the r8 finding: the workflow
    # deliberately never sets OPENAI_REVIEW_MODEL (PR #14 r4), so the
    # first seat always runs the base-owned DEFAULT_MODEL at full
    # strength. Weakening the second seat therefore cannot make the gate
    # pass anything the first seat blocks — ANY-lens-red still holds.
    import pathlib

    workflow = (pathlib.Path(ar.__file__).parent.parent / ".github" / "workflows"
                / "adversarial-review.yml").read_text()
    assert "OPENAI_REVIEW_MODEL:" not in workflow


def test_every_floating_alias_in_the_allowlist_is_bound_to_an_OPEN_record():
    # #72 r8 HARDENING after the mutable-model-alias repeat-class alarm.
    # The r6 fix named the alias honestly and recorded it; naming is not a
    # mechanism, and the alarm was right that the class escaped. This is
    # the mechanism: a floating `*-latest` id may appear in the reviewer's
    # allowlist ONLY while docs/RECORD.md carries an OPEN row naming it —
    # so the compromise cannot outlive its own trigger, and adding a new
    # alias without recording it fails here rather than in review.
    import pathlib
    import re

    record = (pathlib.Path(ar.__file__).parent.parent / "docs"
              / "RECORD.md").read_text()
    open_rows = [line for line in record.splitlines()
                 if re.match(r"^\| R-\d+ ", line) and line.rstrip().endswith("| OPEN |")]
    aliases = [m for m in ar.GEMINI_ALLOWED_MODELS if m.endswith("-latest")]
    assert aliases, "if no alias remains, delete this test with the last one"
    for alias in aliases:
        assert any(alias in row for row in open_rows), (
            f"{alias!r} is a FLOATING alias in the reviewer allowlist with no "
            "OPEN docs/RECORD.md row naming it. An alias moves provider-side "
            "with no commit here, so it may only exist while a record carries "
            "its objective trigger to concretise it (class: mutable-model-alias)")
