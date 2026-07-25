"""Tests for the headless-render fetch fallback (worker/fetch/render_fetch.py).

Two layers, both hermetic (the sandbox has NO live network):

1. The trigger DECISION logic (`should_render`, `fetch_with_render`) — runs with
   no browser, no DB, no network. It proves that a plain fetch whose sensor
   reading flags a boilerplate-only JS shell re-fetches through the render seam,
   and that a healthy page (or a differently-bad input) does NOT pay for a
   browser. This layer is always exercised.

2. The real headless render (`render_html`) — proves JavaScript actually
   executes. It serves a local file whose <body> is EMPTY until an inline
   <script> computes and injects a marker that is NOT present as a literal in
   the page source, so a plain read could never contain it; only a real JS
   engine produces it. Guarded by `pytest.importorskip('playwright')` so the
   suite stays green wherever the optional package is absent
   (worker/requirements-render.txt).
"""
import os

import pytest

from worker.fetch.render_fetch import (
    RenderError,
    fetch_with_render,
    should_render,
)
from worker.sensors import SensorReading, assess_input


# --- Layer 1: trigger-decision logic (no browser / no network / no DB) --------

# A page that renders as a bare "please enable JavaScript" shell — exactly what
# a JS-widget venue calendar returns to a plain requests.get. The sensor flags
# it boilerplate-only; that flag is our render trigger.
_JS_SHELL = "Please enable JavaScript. Your browser is not supported."

# A real, substantive page the sensor passes — must NEVER trigger a render.
_REAL_PAGE = (
    "Tonight at The Mohawk: doors 8pm, The Reverberations live on the outdoor "
    "stage, plus a late set from DJ Cass. Tickets at the door, all ages welcome."
)


def test_should_render_true_only_on_boilerplate_shell():
    # The exact JS-shell case the fallback exists for.
    shell_reading = assess_input(text=_JS_SHELL, content_type="text/html")
    assert shell_reading.ok is False
    assert shell_reading.signals.get("boilerplate_only") is True
    assert should_render(shell_reading) is True


def test_should_render_false_on_healthy_page():
    ok_reading = assess_input(text=_REAL_PAGE, content_type="text/html")
    assert ok_reading.ok is True
    assert should_render(ok_reading) is False


def test_should_render_false_on_unrelated_rejection():
    # A too-short input is rejected, but a browser would not fix it — no render.
    short_reading = assess_input(text="hi", content_type="text/html")
    assert short_reading.ok is False
    assert short_reading.signals.get("boilerplate_only") is not True
    assert should_render(short_reading) is False


def _fake_ok_fetch(storage_ref):
    """Build a fake fetch_url that returns an 'ok' result pointing at a file."""

    def _fetch(*, source_id, url, user_agent):  # noqa: ARG001 — matches fetch_url kwargs
        return {
            "status": "ok",
            "url": url,
            "storage_ref": storage_ref,
            "content_type": "text/html",
        }

    return _fetch


def test_fetch_with_render_fires_render_on_shell(tmp_path):
    # Plain fetch yields a JS shell -> the fallback MUST re-fetch via render.
    shell_file = tmp_path / "shell.html"
    shell_file.write_text(_JS_SHELL, encoding="utf-8")

    render_calls = []

    def _fake_render(*, url, timeout_ms, wait_selector, user_agent):  # noqa: ARG001
        render_calls.append(url)
        return "<html><body>RENDERED-CALENDAR-CONTENT with 12 shows</body></html>"

    result = fetch_with_render(
        source_id="src-1",
        url="https://venue.example/calendar",
        _fetch_fn=_fake_ok_fetch(str(shell_file)),
        _render_fn=_fake_render,
    )

    assert render_calls == ["https://venue.example/calendar"], "render must fire exactly once on a shell"
    assert result["rendered"] is True
    assert "RENDERED-CALENDAR-CONTENT" in result["text"]
    assert result["plain_shell_reason"]  # audit trail records WHY we escalated


def test_fetch_with_render_skips_render_on_real_page(tmp_path):
    # A healthy page must be returned as-is, with NO browser cost.
    real_file = tmp_path / "real.html"
    real_file.write_text(_REAL_PAGE, encoding="utf-8")

    def _fail_render(**_kwargs):
        raise AssertionError("render must NOT be called for a healthy page")

    result = fetch_with_render(
        source_id="src-2",
        url="https://venue.example/real",
        _fetch_fn=_fake_ok_fetch(str(real_file)),
        _render_fn=_fail_render,
    )

    assert result["rendered"] is False
    assert result["text"] == _REAL_PAGE


def test_fetch_with_render_passes_through_non_ok_fetch():
    # A 304 / failed fetch has no content to render — returned unchanged.
    def _not_modified(*, source_id, url, user_agent):  # noqa: ARG001
        return {"status": "not_modified", "url": url}

    def _fail_render(**_kwargs):
        raise AssertionError("render must NOT be called when there is no content")

    result = fetch_with_render(
        source_id="src-3",
        url="https://venue.example/unchanged",
        _fetch_fn=_not_modified,
        _render_fn=_fail_render,
    )
    assert result["status"] == "not_modified"
    assert result["rendered"] is False


def test_render_error_propagates_not_swallowed(tmp_path):
    # A render failure must reach the caller (loud), never be swallowed into a
    # blank "nothing to extract" success.
    shell_file = tmp_path / "shell.html"
    shell_file.write_text(_JS_SHELL, encoding="utf-8")

    def _boom_render(**_kwargs):
        raise RenderError("headless render blew up")

    with pytest.raises(RenderError):
        fetch_with_render(
            source_id="src-4",
            url="https://venue.example/calendar",
            _fetch_fn=_fake_ok_fetch(str(shell_file)),
            _render_fn=_boom_render,
        )


# --- Layer 2: the real browser proves JS executes ----------------------------

# The marker is COMPUTED at runtime (string concat) so the literal never appears
# in the page source — a plain read cannot contain it, only executed JS can.
_MARKER = "READY_42"
_JS_INJECTS_MARKER = (
    "<!doctype html><html><head><title>t</title></head>"
    "<body></body>"
    "<script>document.body.textContent = 'READY_' + (6 * 7);</script>"
    "</html>"
)


def test_render_html_executes_javascript(tmp_path):
    playwright = pytest.importorskip(
        "playwright",
        reason="optional render dependency absent (worker/requirements-render.txt)",
    )
    del playwright  # only needed for the skip guard

    from worker.fetch.render_fetch import render_html, resolve_chromium_path

    if not os.path.exists(resolve_chromium_path()):
        pytest.skip(f"Chromium binary not present at {resolve_chromium_path()}")

    page_file = tmp_path / "js_shell.html"
    page_file.write_text(_JS_INJECTS_MARKER, encoding="utf-8")

    # Sanity: the marker is NOT a literal in the source, so a plain read fails.
    assert _MARKER not in page_file.read_text(encoding="utf-8")

    rendered = render_html(url=page_file.as_uri(), timeout_ms=15_000)

    # ...but the rendered DOM contains it — proof the inline script executed.
    assert _MARKER in rendered
