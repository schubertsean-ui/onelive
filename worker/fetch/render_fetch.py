"""Headless-render fetch — the JS-shell fallback for the fetch layer.

Why this exists: `worker.fetch.http_fetch.fetch_url` is a plain `requests.get`
(policy-safe by construction — no login/paywall/bot bypass). It cannot run
JavaScript, so venue calendars built on JS widgets (Squarespace, Wix,
Bandsintown, "The Events Calendar", etc.) return an empty chrome-only shell
whose real listings are injected client-side. The sensor layer
(`worker.sensors._is_boilerplate_only` — "enable javascript" / "your browser
is not supported") correctly flags that shell and today the pipeline REJECTS
it. That same detection becomes the TRIGGER here: on a boilerplate-only shell
we re-fetch the page through a headless Chromium that actually executes the
page's scripts, then hand the fully-rendered HTML back for parsing instead of
throwing the source away.

Cost discipline (CLAUDE.md "least costly method first"): the plain path stays
primary and is used for every source. Rendering is expensive (a browser
process) so it fires ONLY on the shell trigger — `should_render()` is the one
gate. Rendering is headless, blocks images/fonts/media to stay fast, and runs
under a bounded timeout so it can never hang a run.

Failure policy (OPERATING_RULES SS1, project precedent): loud, never swallowed.
A render that times out or errors raises `RenderError` with context — this
module never returns a partial/blank page as success. What the caller does
with that loud signal is the caller's policy: the ingestion loop
(worker/orchestrator.py) treats rendering as an OPTIONAL enhancement — it
logs the RenderError, records it on the replay fetch entry, and proceeds
with the un-rendered plain result (fail-open on availability, fail-closed on
trust: the plain text still faces the sensors). The loop also budgets
renders per run via ONELIVE_MAX_RENDERS_PER_RUN — see orchestrator.py.

This module deliberately does NOT import worker.promote or worker.gating: it
only fetches bytes, it has no opinion on corroboration or publishing.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict, Optional

from worker.fetch.http_fetch import fetch_url
from worker.sensors import SensorReading, assess_input

logger = logging.getLogger(__name__)

# A declared, honest User-Agent — the same identity the plain adapter presents
# (worker/fetch/http_fetch.py). We render our OWN request, we do not impersonate
# a consumer browser to defeat bot protection.
DEFAULT_USER_AGENT = "OneLiveBot/0.1 (+contact: ops@onelive.example)"

# Bounded by construction: a render must NEVER hang a scheduled run. Applied to
# navigation and to any content-selector wait. Overridable per call for a
# genuinely slow widget, but always finite.
DEFAULT_RENDER_TIMEOUT_MS = 20_000

# Resource types we refuse to download while rendering — they cost bandwidth
# and time but contribute nothing to the extractable text of an events
# calendar. Blocking them is the "stay fast" half of cost discipline.
_BLOCKED_RESOURCE_TYPES = frozenset({"image", "media", "font"})


class RenderError(RuntimeError):
    """A headless render failed (timeout, navigation error, missing browser).

    Raised — never swallowed — so the caller's per-source isolation records it
    as that source's loud failure instead of silently returning a blank page
    that would then look like "nothing to extract".
    """


def resolve_chromium_path() -> str:
    """Absolute path to the pre-installed Chromium binary.

    The environment ships Chromium under PLAYWRIGHT_BROWSERS_PATH with a stable
    `chromium` symlink to the real `chrome` executable (see the build image).
    We pass this to Playwright as `executable_path` explicitly rather than
    relying on Playwright's own lookup, because PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD
    is set and there is no per-package browser install to discover. An explicit
    override (ONELIVE_CHROMIUM_PATH) wins for non-standard images.
    """
    override = os.getenv("ONELIVE_CHROMIUM_PATH")
    if override:
        return override
    browsers_path = os.getenv("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
    return os.path.join(browsers_path, "chromium")


def render_html(
    *,
    url: str,
    timeout_ms: int = DEFAULT_RENDER_TIMEOUT_MS,
    wait_selector: Optional[str] = None,
    user_agent: str = DEFAULT_USER_AGENT,
    executable_path: Optional[str] = None,
) -> str:
    """Fetch `url` through a headless Chromium and return the rendered HTML.

    Navigates, waits for network-idle (and optionally for `wait_selector` to
    appear — a content anchor for widgets whose XHR settles after 'idle'), then
    returns the serialized post-JavaScript DOM. Headless, images/fonts/media
    blocked, everything under `timeout_ms`.

    Loud on every failure path: a missing Playwright package, a missing browser
    binary, a navigation timeout, or any Playwright error is re-raised as
    RenderError with context. Nothing is swallowed and no partial page is
    returned as if it were a success.
    """
    try:
        from playwright.sync_api import (  # noqa: PLC0415 — lazy: absent package must not break import
            Error as PlaywrightError,
            TimeoutError as PlaywrightTimeoutError,
            sync_playwright,
        )
    except ImportError as exc:
        raise RenderError(
            "the `playwright` Python package is not installed, so JS-shell "
            "rendering is unavailable — add `playwright` to worker/requirements.txt "
            "and install it (the Chromium binary is already present)."
        ) from exc

    exe = executable_path or resolve_chromium_path()
    if not os.path.exists(exe):
        raise RenderError(
            f"Chromium binary not found at {exe!r} — set ONELIVE_CHROMIUM_PATH or "
            "PLAYWRIGHT_BROWSERS_PATH to the pre-installed browser location."
        )

    def _block_heavy(route: Any) -> None:
        # Abort image/font/media requests to stay fast; let everything else
        # (documents, scripts, XHR/fetch the calendar needs) through.
        if route.request.resource_type in _BLOCKED_RESOURCE_TYPES:
            route.abort()
        else:
            route.continue_()

    logger.info("render: launching headless Chromium for %s (timeout=%dms)", url, timeout_ms)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                executable_path=exe,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            try:
                context = browser.new_context(user_agent=user_agent)
                page = context.new_page()
                page.route("**/*", _block_heavy)
                page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                if wait_selector:
                    page.wait_for_selector(wait_selector, timeout=timeout_ms)
                html = page.content()
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise RenderError(
            f"render timed out after {timeout_ms}ms for {url!r} "
            f"(wait_selector={wait_selector!r})"
        ) from exc
    except PlaywrightError as exc:
        raise RenderError(f"headless render failed for {url!r}: {exc}") from exc

    logger.info("render: %s produced %d chars of rendered HTML", url, len(html))
    return html


def screenshot_page(
    *,
    url: str,
    timeout_ms: int = DEFAULT_RENDER_TIMEOUT_MS,
    wait_selector: Optional[str] = None,
    user_agent: str = DEFAULT_USER_AGENT,
    full_page: bool = True,
    executable_path: Optional[str] = None,
) -> bytes:
    """Screenshot `url` through the SAME headless Chromium render_html uses and
    return PNG bytes — the input to the vision extractor (ai/vision_provider.py).

    This is the counterpart to render_html: render_html recovers TEXT and blocks
    images to stay fast; this recovers the PIXELS, so it does NOT block images —
    an event flyer IS the image. Same honest User-Agent, same bounded timeout,
    same loud failure policy: any Playwright/timeout error is re-raised as
    RenderError so the caller's per-source isolation records it as a visible
    failure, never a blank screenshot masquerading as success.

    Cost note (CLAUDE.md "least costly method first"): a screenshot + a vision
    model call is more expensive than a text fetch, so callers fire this only as
    a bounded fallback for image-only sources, never on every page.
    """
    try:
        from playwright.sync_api import (  # noqa: PLC0415 — lazy: absent package must not break import
            Error as PlaywrightError,
            TimeoutError as PlaywrightTimeoutError,
            sync_playwright,
        )
    except ImportError as exc:
        raise RenderError(
            "the `playwright` Python package is not installed, so screenshotting "
            "for vision extraction is unavailable — add `playwright` to "
            "worker/requirements.txt (the Chromium binary is already present)."
        ) from exc

    exe = executable_path or resolve_chromium_path()
    if not os.path.exists(exe):
        raise RenderError(
            f"Chromium binary not found at {exe!r} — set ONELIVE_CHROMIUM_PATH or "
            "PLAYWRIGHT_BROWSERS_PATH to the pre-installed browser location."
        )

    logger.info("screenshot: launching headless Chromium for %s (timeout=%dms)", url, timeout_ms)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                executable_path=exe,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            try:
                context = browser.new_context(user_agent=user_agent)
                page = context.new_page()
                # No route-blocking here: images are exactly what we want.
                page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                if wait_selector:
                    page.wait_for_selector(wait_selector, timeout=timeout_ms)
                png = page.screenshot(full_page=full_page, type="png")
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise RenderError(
            f"screenshot timed out after {timeout_ms}ms for {url!r} "
            f"(wait_selector={wait_selector!r})"
        ) from exc
    except PlaywrightError as exc:
        raise RenderError(f"headless screenshot failed for {url!r}: {exc}") from exc

    logger.info("screenshot: %s produced %d bytes of PNG", url, len(png))
    return png


def should_render(reading: SensorReading) -> bool:
    """Decide whether a plain fetch should be re-fetched through the browser.

    The trigger is deliberately narrow: ONLY a boilerplate-only shell — the
    exact "nav/cookie/consent chrome with no substantive content, or a page
    that requires JS the fetcher doesn't run" case flagged by
    `worker.sensors._is_boilerplate_only` (which owns the "enable javascript" /
    "your browser is not supported" markers). Every other sensor rejection
    (empty, too short, binary, mojibake, injection, truncated, error page) is a
    genuinely bad input that rendering would not fix, so it does NOT pay for a
    browser. A reading that already passed never renders.

    Reads the `boilerplate_only` provenance signal the sensor records, not the
    prose reason string, so the trigger can't drift if wording changes.
    """
    if reading.ok:
        return False
    return reading.signals.get("boilerplate_only") is True


def _read_fetched_text(fetch_result: Dict[str, Any]) -> str:
    """Decode the bytes fetch_url wrote to storage_ref as text.

    Mirrors worker.orchestrator._read_fetched_text: best-effort utf-8 with
    replacement, so a stray non-utf8 byte degrades to a sensor-detectable
    signal rather than raising here.
    """
    storage_ref = fetch_result["storage_ref"]
    with open(storage_ref, "rb") as f:
        raw = f.read()
    return raw.decode("utf-8", errors="replace")


def fetch_with_render(
    *,
    source_id: Optional[str],
    url: str,
    user_agent: str = DEFAULT_USER_AGENT,
    render_timeout_ms: int = DEFAULT_RENDER_TIMEOUT_MS,
    wait_selector: Optional[str] = None,
    etag: Optional[str] = None,
    last_modified: Optional[str] = None,
    _fetch_fn: Callable[..., Dict[str, Any]] = fetch_url,
    _render_fn: Callable[..., str] = render_html,
    _read_text: Callable[[Dict[str, Any]], str] = _read_fetched_text,
) -> Dict[str, Any]:
    """Plain-first fetch with a headless-render fallback for JS shells.

    Flow (cost-disciplined):
      1. Plain fetch via the normal adapter (cheap; the primary path).
      2. On a non-'ok' status (304 / failure), return it unchanged — nothing to
         render.
      3. Decode the fetched text and run the input-quality sensor.
      4. If the sensor flags a boilerplate-only shell (`should_render`),
         re-fetch the page through a headless browser and return the RENDERED
         HTML — the JS calendar is now readable instead of rejected.
      5. Otherwise return the plain text (a real page, or a bad input the sensor
         will reject downstream for a reason a browser wouldn't fix).

    Returns the plain fetch_result dict augmented with:
      - `text`:     the HTML to hand downstream (rendered when we rendered,
                    plain otherwise).
      - `rendered`: True iff the render fallback fired.
    On the rendered path it also carries `plain_shell_reason` (the sensor's
    reason for flagging the shell) so the audit trail records WHY we escalated
    to a browser.

    The private `_fetch_fn` / `_render_fn` / `_read_text` seams exist so the
    decision logic is unit-testable without a live DB, network, or browser;
    production callers use the real defaults.

    A render failure is NOT swallowed: RenderError propagates, and the caller's
    per-source isolation records it as that source's loud failure.
    """
    # Conditional-GET validators, forwarded straight through to the adapter:
    # the cheapest possible answer to "did this page change?" is the server
    # saying 304 before it sends a body. They are pass-through only — nothing
    # here interprets them, and an absent validator simply means an
    # unconditional GET, exactly as before this parameter existed.
    result = _fetch_fn(
        source_id=source_id, url=url, user_agent=user_agent,
        etag=etag, last_modified=last_modified,
    )

    if result.get("status") != "ok":
        # 304 / failure — no content to render.
        return {**result, "text": None, "rendered": False}

    text = _read_text(result)
    reading = assess_input(text=text, content_type=result.get("content_type"))

    if not should_render(reading):
        return {**result, "text": text, "rendered": False}

    logger.info(
        "render fallback: source %s at %s is a JS shell (%s) — re-fetching "
        "through headless Chromium",
        source_id, url, reading.reason,
    )
    rendered_html = _render_fn(
        url=url,
        timeout_ms=render_timeout_ms,
        wait_selector=wait_selector,
        user_agent=user_agent,
    )
    return {
        **result,
        "text": rendered_html,
        "rendered": True,
        "plain_shell_reason": reading.reason,
    }
