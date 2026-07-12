"""Security-hardening tests for tools/visual_regression.py.

These are DELIBERATELY NOT marked @pytest.mark.visual: unlike the pixel-diff
tests (which need a booted app + baseline images and are opt-in), these verify
pure-logic security invariants — no-shell-injection in capture_screenshot() and
secret redaction of tool stderr — that must run in EVERY default gate run. A
security regression that only surfaces under `-m visual` would itself be the
"looks covered but isn't" anti-pattern (OPERATING_RULES §1).
"""
import importlib.util
import pathlib
import sys

import pytest

_PATH = pathlib.Path(__file__).resolve().parent.parent / "tools" / "visual_regression.py"
_spec = importlib.util.spec_from_file_location("visual_regression", _PATH)
vr = importlib.util.module_from_spec(_spec)
sys.modules["visual_regression"] = vr
_spec.loader.exec_module(vr)


def test_capture_screenshot_no_shell_injection(tmp_path):
    """A URL containing shell metacharacters must NOT execute an injected
    command: {url}/{out} are substituted as whole argv elements and the command
    runs with shell=False. We use `cp` (on PATH) as the capture binary and pass
    a malicious URL that would create a sentinel file IF a shell interpreted it.
    The sentinel must never appear."""
    sentinel = tmp_path / "pwned"
    src = tmp_path / "src.png"
    src.write_bytes(b"x")
    out_path = tmp_path / "shot.png"
    malicious_url = f"{src}; touch {sentinel}"
    # cp will fail (the value isn't a single real filename), but the KEY
    # assertion is that no shell ran the `; touch` part.
    with pytest.raises(RuntimeError):
        vr.capture_screenshot("cp {url} {out}", malicious_url, out_path)
    assert not sentinel.exists(), "shell injection executed — command was run through a shell"


def test_redact_scrubs_query_and_tokens():
    dirty = "failed for https://x.io/p?token=abcSECRET&sig=deadbeef and key=hunter2"
    clean = vr._redact(dirty)
    assert "abcSECRET" not in clean
    assert "deadbeef" not in clean
    assert "hunter2" not in clean
    assert "redacted" in clean
